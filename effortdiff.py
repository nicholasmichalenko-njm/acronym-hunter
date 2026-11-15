"""Where an effort's standards differ from the Global Standards (4.36.0; Nicholas's ST8, ST11 and ST20 of 2026-11-14).
The effort's own value is the one in use; on each row the person can choose the Global value instead, and choose back.
Choosing Global never throws the effort's value away: it is kept beside the choice (a value) or in the item's history
(a style, a Quick Part, any library item), so every choice is made and unmade in one step.

    rows(config_dir, root)        every difference, one row each:
        {"key", "kind" ("value" | "item" | "file"), "part", "what", "mine", "theirs",
         "state" ("differs" | "only_here" | "only_theirs"), "using" ("effort" | "theirs"), "can"}
        A row the person switched to Global stays in the list, with "using": "theirs", so it can be switched back.
    use_global(config_dir, root, key)     the effort uses the Global value on that row
    use_mine(config_dir, root, key)       the effort uses its own value again
    counts(rows)                          {"differs", "only_here", "only_theirs", "theirs"}

Standard library only. Rules only (No AI); nothing leaves the PC."""
import copy, json, os, shutil

import effortset as ES
import globalstd as GS

SWITCHES = "switches.json"                      # in the effort's set folder: what the effort had on a row switched to Global
LIB = "template_library"
MOST = 400                                      # rows; past it the list says so
SKIP_TOP = {"version"}                          # a file's own format number is not a standard
_MISSING = object()


def _json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _write(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)


RESOLVED = "production_standards.json"         # kept as changes from the built-in values: compared as it is read, whole


def _read(m, path, where):
    """A file's values as the program reads them: {} for a file that is not a JSON object."""
    if m == RESOLVED:
        import prodrules as PRL
        return PRL.load(where)
    d = _json(path)
    return d if isinstance(d, dict) else None


def _store(m, path, where, d):
    if m == RESOLVED:
        import prodrules as PRL
        PRL.save(where, d)
    else:
        _write(path, d)


def _switches(root):
    d = _json(os.path.join(ES.set_dir(root), SWITCHES))
    return d if isinstance(d, dict) else {}


def _save_switches(root, d):
    _write(os.path.join(ES.set_dir(root), SWITCHES), d)


def _step(node, part):
    """One step down a value's path: a dict key, or a list entry by its name, id or place."""
    if isinstance(node, dict):
        return node.get(part, _MISSING)
    if isinstance(node, list):
        for x in node:
            if isinstance(x, dict) and part in (x.get("name"), x.get("id")):
                return x
        if isinstance(part, int) and 0 <= part < len(node):
            return node[part]
    return _MISSING


def _leaves(d, path=()):
    """{path (a tuple of dict keys and list entries' names): value} for every plain value in a JSON object."""
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            if (not path and k in SKIP_TOP) or str(k).startswith("_"):
                continue
            out.update(_leaves(v, path + (k,)))
    elif isinstance(d, list):
        names = [x.get("name") or x.get("id") if isinstance(x, dict) else None for x in d]
        named = all(isinstance(n, str) and n for n in names) and len(set(names)) == len(names)
        if named:
            for n, v in zip(names, d):
                out.update(_leaves(v, path + (n,)))
        else:
            out[path] = d                                        # a plain list is one value (a tab list, a list of words)
    else:
        out[path] = d
    return out


def _get(d, path):
    for part in path:
        d = _step(d, part)
        if d is _MISSING:
            return _MISSING
    return d


def _set(d, path, value):
    """Put a value at a path that exists down to its last step. Returns True when it was put."""
    node = d
    for part in path[:-1]:
        node = _step(node, part)
        if node is _MISSING:
            return False
    if isinstance(node, dict):
        if value is _MISSING:
            node.pop(path[-1], None)
        else:
            node[path[-1]] = value
        return True
    return False


def _say(v):
    if v is _MISSING or v is None:
        return "(not set)"
    if v is True:
        return "on"
    if v is False:
        return "off"
    if isinstance(v, (list, dict)):
        s = json.dumps(v, ensure_ascii=False)
        return s if len(s) <= 80 else s[:77] + "..."
    return str(v) if str(v) != "" else "(empty)"


def _label(path):
    return " > ".join(str(p).replace("_", " ") for p in path)


def _files(config_dir, root):
    """({file: path} in the effort's set, {file: path} in the Global Standards), the library left out."""
    mine = {m: p for m, p in ES._members(ES.set_dir(root)).items() if not m.startswith(LIB + "/")}
    with ES.as_global():
        glob = {m: p for m, p in ES._members(config_dir).items() if not m.startswith(LIB + "/")}
    return mine, glob


def _value_rows(config_dir, root, sw):
    mine, glob = _files(config_dir, root)
    rows = []
    for m in sorted(set(mine) | set(glob)):
        part = ES._part_of(m)
        if m in mine and m in glob and m.endswith(".json"):
            a = _read(m, mine[m], ES.set_dir(root))
            with ES.as_global():
                b = _read(m, glob[m], config_dir)
            if isinstance(a, dict) and isinstance(b, dict):
                la, lb = _leaves(a), _leaves(b)
                for path in sorted(set(la) | set(lb), key=lambda p: [str(x) for x in p]):
                    key = "v|" + m + "|" + json.dumps(list(path))
                    va, vb = la.get(path, _MISSING), lb.get(path, _MISSING)
                    held = sw.get(key)
                    if va == vb:
                        if held is not None and "mine" in held and _unpack(held["mine"]) != vb:
                            rows.append({"key": key, "kind": "value", "part": part, "what": _label(path), "mine": _say(_unpack(held["mine"])),
                                         "theirs": _say(vb), "state": "differs", "using": "theirs", "can": True})
                        continue
                    state = "only_here" if vb is _MISSING else "only_theirs" if va is _MISSING else "differs"
                    rows.append({"key": key, "kind": "value", "part": part, "what": _label(path), "mine": _say(va), "theirs": _say(vb),
                                 "state": state, "using": "effort", "can": _get(a, path[:-1]) is not _MISSING and isinstance(_get(a, path[:-1]) if path[:-1] else a, dict)})
                continue
        if m in mine and m in glob and GS._sha_file(mine[m]) == GS._sha_file(glob[m]):
            key = "f|" + m
            if key in sw:                                        # switched to Global: the effort's own copy is kept beside it
                rows.append({"key": key, "kind": "file", "part": part, "what": os.path.basename(m), "mine": "this effort's own file",
                             "theirs": "the Global Standards' file", "state": "differs", "using": "theirs", "can": True})
            continue
        state = "only_here" if m not in glob else "only_theirs" if m not in mine else "differs"
        rows.append({"key": "f|" + m, "kind": "file", "part": part, "what": os.path.basename(m),
                     "mine": "this effort's own file" if m in mine else "(not in this effort)",
                     "theirs": "the Global Standards' file" if m in glob else "(not in the Global Standards)",
                     "state": state, "using": "effort", "can": True})
    return rows


def _pack(v):
    return {"none": True} if v is _MISSING else {"v": v}


def _unpack(d):
    return _MISSING if d.get("none") else d.get("v")


def _libs(config_dir, root):
    """The effort's library, and what the Global Standards' library holds: {(family, line): (item, values)}."""
    import stylehistory as SH, templatelib as TL
    lib = TL.Library(config_dir)                                 # the effort's (its set is the one in use)
    with ES.as_global():
        g = TL.Library(config_dir)
        tops = {}
        for it in g.items:
            t = SH.top(g, it["id"])
            tops[(it.get("family"), SH.line_of(it))] = t
        glob = {k: (dict(t), g.values(t) or {}) for k, t in tops.items()}
        gsets = {k: [s["name"] for s in g.kits if t["id"] in (s.get("items") or [])] for k, t in tops.items()} if hasattr(g, "kits") else {}
    return lib, glob, gsets


def _item_rows(config_dir, root, sw):
    import stylehistory as SH, stylelib as SL, templatelib as TL
    if ES.active() != ES.set_dir(root):
        return []                                                # the library is read through the set in use: the effort must be open
    lib, glob, _gsets = _libs(config_dir, root)
    mine = {}
    for it in lib.items:
        mine[(it.get("family"), SH.line_of(it))] = SH.top(lib, it["id"])
    rows = []
    for k in sorted(set(mine) | set(glob), key=lambda k: (str((mine.get(k) or glob[k][0]).get("kind")), lib.base_of(mine[k]) if k in mine else glob[k][0].get("base_name") or glob[k][0].get("name", ""))):
        key = "i|" + str(k[0]) + "|" + str(k[1])
        a = mine.get(k)
        gb = glob.get(k)
        kind = (a or gb[0]).get("kind")
        shelf = TL.SHELF.get(kind, kind)
        name = lib.base_of(a) if a else (gb[0].get("base_name") or gb[0].get("name", ""))
        sets = [s["name"] for s in SL.sets_of(lib, a["id"], kind="style" if kind == "style" else "part")] if a else []
        what = f"{name}" + (f"  [{', '.join(sets)}]" if sets else "")
        if a and gb:
            held = sw.get(key)
            if a.get("hash") == gb[0].get("hash"):
                if held and held.get("mine") and lib.get(held["mine"]) is not None and lib.get(held["mine"]).get("hash") != gb[0].get("hash"):
                    rows.append({"key": key, "kind": "item", "part": shelf, "what": what, "mine": _item_say(lib, lib.get(held["mine"]), gb[1], kind),
                                 "theirs": "version " + str(gb[0].get("version", 1)), "state": "differs", "using": "theirs", "can": True})
                continue
            rows.append({"key": key, "kind": "item", "part": shelf, "what": what, "mine": _item_say(lib, a, gb[1], kind),
                         "theirs": "as the Global Standards have it", "state": "differs", "using": "effort", "can": True})
        elif a:
            rows.append({"key": key, "kind": "item", "part": shelf, "what": what, "mine": "made in this effort", "theirs": "(not in the Global Standards)",
                         "state": "only_here", "using": "effort", "can": False})
        else:
            rows.append({"key": key, "kind": "item", "part": shelf, "what": what, "mine": "(not in this effort)", "theirs": "in the Global Standards",
                         "state": "only_theirs", "using": "effort", "can": False})
    return rows


def _item_say(lib, it, global_values, kind):
    """What the effort's item has that the Global one does not, in words."""
    import stylehistory as SH
    if kind == "style":
        ch = SH.changes(global_values, lib.values(it) or {})
        if ch:
            return "; ".join(f"{w}: {b}" + (f" (Global Standards: {a})") for w, a, b in ch[:4]) + (f"; {len(ch) - 4} more" if len(ch) > 4 else "")
    return "this effort's own values"


def rows(config_dir, root):
    """Every difference between the effort's standards and the Global Standards (at most MOST), values first."""
    sw = _switches(root)
    out = _value_rows(config_dir, root, sw)
    try:
        out += _item_rows(config_dir, root, sw)
    except Exception:  # noqa: BLE001  a library that cannot be read lists no item rows; the values still show
        pass
    return out[:MOST]


def counts(rws):
    c = {"differs": 0, "only_here": 0, "only_theirs": 0, "theirs": 0}
    for r in rws:
        c[r["state"]] += 1
        c["theirs"] += r["using"] == "theirs"
    return c


def _row(config_dir, root, key):
    return next((r for r in rows(config_dir, root) if r["key"] == key), None)


def use_global(config_dir, root, key):
    """The effort uses the Global value on this row; its own value is kept so the choice can be unmade. Returns True
    when it was done."""
    r = _row(config_dir, root, key)
    if r is None or not r["can"] or r["using"] == "theirs":
        return False
    sw = _switches(root)
    mine, glob = _files(config_dir, root)
    kind, rest = key.split("|", 1)
    if kind == "v":
        m, raw = rest.split("|", 1)
        path = tuple(json.loads(raw))
        a = _read(m, mine[m], ES.set_dir(root))
        with ES.as_global():
            b = _read(m, glob[m], config_dir)
        was, new = _get(a, path), _get(b, path)
        if not _set(a, path, new if new is _MISSING else copy.deepcopy(new)):
            return False
        _store(m, mine[m], ES.set_dir(root), a)
        sw[key] = {"mine": _pack(was)}
    elif kind == "f":
        dst = os.path.join(ES.set_dir(root), rest.replace("/", os.sep))
        keep = os.path.join(ES.set_dir(root), "_mine", rest.replace("/", os.sep))
        if os.path.isfile(dst):
            os.makedirs(os.path.dirname(keep), exist_ok=True)
            shutil.copyfile(dst, keep)
        if rest in glob:
            ES._copy(glob[rest], dst)
        elif os.path.isfile(dst):
            os.remove(dst)
        sw[key] = {"had": os.path.isfile(keep)}
    else:
        import stylehistory as SH
        fam, line = rest.split("|", 1)
        lib, globd, _s = _libs(config_dir, root)
        top = next((SH.top(lib, i["id"]) for i in lib.items if i.get("family") == fam and SH.line_of(i) == line), None)
        g = globd.get((fam, line))
        if top is None or g is None:
            return False
        new = SH._on_top(lib, top, g[1], note="The Global Standards' version")
        new["hash"] = g[0].get("hash", new.get("hash")); lib.save()
        SH._move(lib, fam, new["id"])
        sw[key] = {"mine": top["id"]}
    _save_switches(root, sw)
    return True


def use_mine(config_dir, root, key):
    """The effort uses its own value on this row again. Returns True when it was done."""
    sw = _switches(root)
    held = sw.get(key)
    if held is None:
        return False
    mine, _glob = _files(config_dir, root)
    kind, rest = key.split("|", 1)
    if kind == "v":
        m, raw = rest.split("|", 1)
        a = _read(m, mine[m], ES.set_dir(root))
        v = _unpack(held["mine"])
        if a is None or not _set(a, tuple(json.loads(raw)), v if v is _MISSING else copy.deepcopy(v)):
            return False
        _store(m, mine[m], ES.set_dir(root), a)
    elif kind == "f":
        dst = os.path.join(ES.set_dir(root), rest.replace("/", os.sep))
        keep = os.path.join(ES.set_dir(root), "_mine", rest.replace("/", os.sep))
        if held.get("had") and os.path.isfile(keep):
            ES._copy(keep, dst)
            os.remove(keep)
        elif os.path.isfile(dst):
            os.remove(dst)
    else:
        import stylehistory as SH, templatelib as TL
        lib = TL.Library(config_dir)
        if lib.get(held.get("mine") or "") is None:
            return False
        new, _sets = SH.restore(lib, held["mine"])
        if new is not None:
            new["note"] = "This effort's own version again"; lib.save()
    sw.pop(key, None)
    _save_switches(root, sw)
    return True
