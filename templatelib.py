"""The template library (3.22.0): everything collected from templates and Word documents that can inform a template,
kept as format data on this PC.

Collect reads a .dotx, .dotm (as XML only; macros never run) or .docx once, never writing it, and lists what it carries
as items on shelves: styles (each with its whole definition, hidden text included), page setups, headers and footers,
heading numbering, list numbering, Word table styles, table looks by row role, the TOC, covers, back covers, Quick
Parts and fonts. The person confirms, renames or skips each item and tags the lot (use case, proposal type, program
type, customer); what they keep is saved at once, so a collection can stop and resume.

An item is saved as its values (a style's definition, a page setup's margins) or, for page designs and Quick Parts, as
the kept source file with the part's name, so its fields, pictures and anchored tables stay whole. The same values
already in the library match without asking; the same name with other values is kept as a variant, tagged; nothing is
overwritten. Items go into a standard being edited (Use in this standard), and a standard's template is built from them.

Kept in <config>\\template_library (index.json, items\\<id>.json and sources\\ for kept files): the team's data, never
in the program folder or the code, and carried by the Our data file. Nothing leaves the PC."""
import copy, datetime, getpass, hashlib, json, os, re, shutil, uuid

FOLDER = "template_library"
SHELVES = (("style", "Styles"), ("page_setup", "Page setups"), ("hf", "Headers and footers"), ("heading_numbering", "Heading numbering"),
           ("list_numbering", "List numbering"), ("table_style", "Word table styles"), ("table_look", "Table looks"),
           ("toc", "Table of contents"), ("cover", "Covers"), ("backer", "Back covers"), ("quickpart", "Quick Parts"), ("font", "Fonts"),
           ("theme", "Themes (colors and fonts)"), ("hf_design", "Header and footer designs (whole)"),
           ("variables", "Base fonts and sizes"), ("part", "Part designs"))
THEME_SLOTS = ("dk1", "lt1", "dk2", "lt2", "accent1", "accent2", "accent3", "accent4", "accent5", "accent6", "hlink", "folHlink")
THEME_NAMES = {"dk1": "Text dark 1", "lt1": "Background light 1", "dk2": "Text dark 2", "lt2": "Background light 2",
               "accent1": "Accent 1", "accent2": "Accent 2", "accent3": "Accent 3", "accent4": "Accent 4", "accent5": "Accent 5",
               "accent6": "Accent 6", "hlink": "Hyperlink", "folHlink": "Followed hyperlink"}
SHELF = dict(SHELVES)
USES = ("RFP", "Page-limited RFP", "RFI", "Program document", "Customer document")


def folder(config_dir):
    return os.path.join(config_dir, FOLDER)


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _hash(values):
    """What makes two items the same: their values, without where a copy is kept (a kept file is named by its content,
    and a page design and a Quick Part carry their content's fingerprint)."""
    v = {k: x for k, x in values.items() if not str(k).startswith("_") and k not in ("source", "file")} if isinstance(values, dict) else values
    return hashlib.sha256(json.dumps(v, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:16]


class Library:
    def __init__(self, config_dir):
        self.config_dir = config_dir
        self.root = folder(config_dir)
        self.items = []
        self.kits = []
        self.load()

    def load(self):
        try:
            with open(os.path.join(self.root, "index.json"), encoding="utf-8") as f:
                d = json.load(f) or {}
            self.items = [i for i in d.get("items", []) if isinstance(i, dict) and i.get("id") and i.get("kind")]
            self.kits = [k for k in d.get("kits", []) if isinstance(k, dict) and k.get("id") and k.get("name")]
        except (OSError, ValueError):
            self.items, self.kits = [], []
        return self

    def save(self):
        os.makedirs(os.path.join(self.root, "items"), exist_ok=True)
        p = os.path.join(self.root, "index.json")
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump({"format": 1, "items": self.items, "kits": self.kits}, f, indent=1, ensure_ascii=False)
        os.replace(p + ".tmp", p)

    # ------------------------------------------------------------ items
    def values(self, item):
        try:
            with open(os.path.join(self.root, "items", item["id"] + ".json"), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def get(self, iid):
        return next((i for i in self.items if i["id"] == iid), None)

    def shelf(self, kind, use=None):
        return [i for i in self.items if i["kind"] == kind and (use is None or use in (i.get("tags") or {}).get("use", []))]

    def match(self, kind, name, values):
        """('same', item) when the library holds these values already; ('variant', item) for the same name with other
        values; ('new', None) otherwise."""
        h = _hash(values)
        same = next((i for i in self.items if i["kind"] == kind and i.get("hash") == h), None)
        if same:
            return "same", same
        var = next((i for i in self.items if i["kind"] == kind and i["name"].casefold() == (name or "").casefold()), None)
        return ("variant", var) if var else ("new", None)

    def add(self, kind, name, values, tags=None, source="", summary="", who=None):
        """Keeps an item, or returns the one already holding these values. A name taken with other values becomes a
        variant ('Heading 1 (2)'), tagged. Returns (item, state)."""
        state, hit = self.match(kind, name, values)
        if state == "same":
            t = hit.setdefault("tags", {})                      # the same item met again: its tags grow
            for k, v in (tags or {}).items():
                if isinstance(v, list):
                    t[k] = sorted(set(t.get(k, [])) | set(v))
                elif v and not t.get(k):
                    t[k] = v
            self.save()
            return hit, "same"
        shown = name
        if state == "variant":
            n = 2
            while any(i["kind"] == kind and i["name"].casefold() == f"{name} ({n})".casefold() for i in self.items):
                n += 1
            shown = f"{name} ({n})"
        item = {"id": uuid.uuid4().hex[:12], "kind": kind, "name": shown, "base_name": name, "hash": _hash(values),
                "tags": copy.deepcopy(tags or {}), "source": os.path.basename(source or ""), "summary": (summary or "")[:300],
                "variant_of": hit["id"] if state == "variant" else "", "at": _now(), "by": who or getpass.getuser()}
        os.makedirs(os.path.join(self.root, "items"), exist_ok=True)
        p = os.path.join(self.root, "items", item["id"] + ".json")
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump(values, f, indent=1, ensure_ascii=False)
        os.replace(p + ".tmp", p)
        self.items.append(item)
        self.save()
        return item, state

    def update(self, iid, values):
        """New values for an item (its edit); the item keeps its name, tags and id."""
        i = self.get(iid)
        if i is None or not isinstance(values, dict):
            return False
        p = os.path.join(self.root, "items", iid + ".json")
        with open(p + ".tmp", "w", encoding="utf-8") as f:
            json.dump(values, f, indent=1, ensure_ascii=False)
        os.replace(p + ".tmp", p)
        i["hash"] = _hash(values)
        i["edited"] = _now()
        if i["kind"] == "style":
            i["summary"] = _summary_style(values)
        self.save()
        return True

    def set_pages(self, iid, pages, how="typed"):
        """3.32.0: a Quick Part's pages, measured by Word on this PC or typed. Kept on the item (not its values, so the
        same Quick Part met again still matches). pages None takes them off."""
        i = self.get(iid)
        if i is None:
            return False
        if pages is None:
            for k in ("pages", "pages_how", "pages_at"):
                i.pop(k, None)
        else:
            i["pages"] = max(1, int(pages))
            i["pages_how"] = "measured" if how == "measured" else "typed"
            i["pages_at"] = _now()
        self.save()
        return True

    def pages_of(self, iid=None, name=None, kind="quickpart"):
        """The pages of a library item by id, or by name on its shelf; None when not measured or typed."""
        i = self.get(iid) if iid else next((x for x in self.items if x["kind"] == kind and x["name"].casefold() == str(name or "").casefold()), None)
        return int(i["pages"]) if i is not None and i.get("pages") else None

    def rename(self, iid, name):
        i = self.get(iid)
        if i is None or not " ".join(str(name).split()):
            return False
        i["name"] = " ".join(str(name).split())[:80]
        self.save()
        return True

    def tag(self, iid, **tags):
        i = self.get(iid)
        if i is None:
            return False
        i.setdefault("tags", {}).update({k: v for k, v in tags.items()})
        self.save()
        return True

    def remove(self, iid):
        i = self.get(iid)
        if i is None:
            return False
        self.items.remove(i)
        for k in self.kits:
            k["items"] = [x for x in k["items"] if x != iid]
        try:
            os.remove(os.path.join(self.root, "items", iid + ".json"))
        except OSError:
            pass
        self.save()
        return True

    # ------------------------------------------------------------ 3.23.0 kits
    def add_kit(self, name, item_ids, tags=None, categories=None):
        """A named set of items ("Space Force page-limited RFP"): start a standard from it and change only what the
        effort needs. categories: {Quick Part item id: category}. Returns the kit."""
        name = " ".join(str(name or "").split())[:80]
        ids = [i for i in item_ids if self.get(i)]
        if not name or not ids:
            return None
        k = next((x for x in self.kits if x["name"].casefold() == name.casefold()), None)
        if k is None:
            k = {"id": uuid.uuid4().hex[:12], "name": name, "items": [], "tags": {}, "categories": {}, "at": _now()}
            self.kits.append(k)
        k["items"] = list(dict.fromkeys(k["items"] + ids))
        k["tags"].update(tags or {})
        k["categories"].update({a: b for a, b in (categories or {}).items() if a in k["items"]})
        self.save()
        return k

    def kit(self, kid):
        return next((k for k in self.kits if k["id"] == kid), None)

    def remove_kit(self, kid):
        n = len(self.kits)
        self.kits = [k for k in self.kits if k["id"] != kid]
        self.save()
        return len(self.kits) < n

    def keep_file(self, path_or_bytes, name):
        """A kept copy of a source file or a page design (content-named, once). Returns its file name in sources."""
        b = path_or_bytes if isinstance(path_or_bytes, (bytes, bytearray)) else open(path_or_bytes, "rb").read()
        stem = re.sub(r"[^A-Za-z0-9_-]+", "_", os.path.splitext(name)[0])[:40] or "part"
        ext = os.path.splitext(name)[1].lower() or ".docx"
        fn = f"{stem}_{hashlib.sha256(b).hexdigest()[:10]}{ext}"
        d = os.path.join(self.root, "sources")
        os.makedirs(d, exist_ok=True)
        if not os.path.isfile(os.path.join(d, fn)):
            with open(os.path.join(d, fn), "wb") as f:
                f.write(b)
        return fn

    def source_path(self, fn):
        return os.path.join(self.root, "sources", fn)


# ------------------------------------------------------------------ collecting from a file
def _summary_style(d):
    bits = []
    if d.get("font"):
        bits.append(str(d["font"]))
    if d.get("size"):
        bits.append(f"{d['size']:g} pt" if isinstance(d["size"], (int, float)) else f"{d['size']} pt")
    for k, t in (("bold", "bold"), ("italic", "italic"), ("caps", "all caps"), ("hidden", "hidden text")):
        if d.get(k):
            bits.append(t)
    if d.get("color") and str(d["color"]).upper() not in ("AUTO", "000000"):
        bits.append(f"color {d['color']}")
    if d.get("before") or d.get("after"):
        bits.append(f"{d.get('before') or 0:g} pt before, {d.get('after') or 0:g} pt after" if isinstance(d.get("before") or 0, (int, float))
                    and isinstance(d.get("after") or 0, (int, float)) else "spacing set")
    if d.get("based_on"):
        bits.append(f"based on {d['based_on']}")
    return ", ".join(bits) or "defined"


def fonts_of(style_defs, path=None, data=None):
    """Every font named by the styles and the file's font table."""
    out = {str(d.get("font")) for d in style_defs.values() if d.get("font") and not str(d.get("font")).startswith("+")}
    try:
        import zipfile, io
        z = zipfile.ZipFile(io.BytesIO(data) if data is not None else path)
        if "word/fontTable.xml" in z.namelist():
            out |= set(re.findall(r'<w:font w:name="([^"]+)"', z.read("word/fontTable.xml").decode("utf-8", "replace")))
    except Exception:                                   # noqa: BLE001  a font table that cannot be read adds nothing
        pass
    return sorted(f for f in out if f and len(f) < 64)


def read_theme(xml):
    """{"name", "colors": {slot: hex}, "major", "minor", "xml"} from a theme part (theme1.xml), or None."""
    if not xml or "clrScheme" not in xml:
        return None
    colors = {}
    for slot in THEME_SLOTS:
        m = re.search(rf"<a:{slot}>\s*<a:(?:srgbClr val|sysClr val=\"[^\"]*\" lastClr)=\"([0-9A-Fa-f]{{6}})\"", xml)
        if m:
            colors[slot] = m.group(1).upper()
    nm = re.search(r'<a:theme [^>]*name="([^"]*)"', xml)
    maj = re.search(r"<a:majorFont>\s*<a:latin typeface=\"([^\"]*)\"", xml)
    mnr = re.search(r"<a:minorFont>\s*<a:latin typeface=\"([^\"]*)\"", xml)
    return {"name": nm.group(1) if nm else "Theme", "colors": colors, "major": maj.group(1) if maj else "",
            "minor": mnr.group(1) if mnr else "", "xml": xml}


def theme_of_file(path=None, data=None):
    """The theme a .thmx, template or document carries (read once), or None."""
    import io, zipfile
    try:
        z = zipfile.ZipFile(io.BytesIO(data) if data is not None else path)
        names = z.namelist()
        part = next((n for n in ("theme/theme/theme1.xml", "word/theme/theme1.xml") if n in names), None)
        part = part or next((n for n in names if re.match(r"(word/)?theme/(theme/)?theme\d*\.xml$", n)), None)
        return read_theme(z.read(part).decode("utf-8", "replace")) if part else None
    except Exception:                                   # noqa: BLE001  not a package
        return None


def theme_summary(t):
    return (f"headings {t['major'] or '(none)'}, body {t['minor'] or '(none)'}; "
            + ", ".join(f"{THEME_NAMES[k]} #{v}" for k, v in t["colors"].items() if k.startswith("accent")))


class Card:
    """One group of found items to confirm: [{"kind", "name", "values", "summary", "state", "match", "keep"}]."""

    def __init__(self, key, title, items, note=""):
        self.key, self.title, self.items, self.note = key, title, items, note


def collect(path, std, lib, installed_fonts=None):
    """Reads the file once (never writing it) and returns ([Card], error). Each item says whether the library has it
    already (same), has the name with other values (variant) or not (new); 'keep' starts ticked for new and variant."""
    import prodlearn as PL
    import prodquickparts as QP
    if path.lower().endswith(".thmx"):                  # a theme file: its colors and fonts only
        t = theme_of_file(path)
        if not t:
            return [], "That file holds no theme."
        st, hit = lib.match("theme", t["name"], t)
        return [Card("theme", "Theme: colors and fonts", [{"kind": "theme", "name": t["name"], "values": t, "summary": theme_summary(t),
                                                           "state": st, "match": hit["name"] if hit else "", "keep": st != "same"}],
                     "Word's 12 theme colors (the palette in every color picker) and the heading and body theme fonts.")], ""
    tmp_parts = os.path.join(lib.root, "_collecting")
    shutil.rmtree(tmp_parts, ignore_errors=True)
    os.makedirs(tmp_parts, exist_ok=True)
    raw = open(path, "rb").read()
    ln = PL.learn(path, std, data=raw, parts_dir=tmp_parts)
    if ln.error:
        return [], ln.error
    cards = []

    def item(kind, name, values, summary):
        st, hit = lib.match(kind, name, values)
        return {"kind": kind, "name": name, "values": values, "summary": summary, "state": st,
                "match": hit["name"] if hit else "", "keep": st != "same"}

    layer = {k: a["layer"] for k, a in ln.areas.items()}
    sd = (layer.get("styles") or {}).get("style_defs") or {}
    groups = (("Headings", lambda n: n.lower().startswith("heading") or n.lower() == "title"),
              ("Captions and TOC", lambda n: n.lower().startswith(("caption", "toc", "table of figures"))),
              ("Hidden text", lambda n: bool(sd[n].get("hidden"))),
              ("Lists", lambda n: "list" in n.lower()),
              ("Headers and footers", lambda n: n.lower() in ("header", "footer")),
              ("Body and the rest", lambda n: True))
    placed = set()
    for title, test in groups:
        names = [n for n in sorted(sd) if n not in placed and test(n)]
        placed |= set(names)
        if names:
            cards.append(Card("styles:" + title, f"Styles: {title.lower()} ({len(names)})",
                              [item("style", n, sd[n], _summary_style(sd[n])) for n in names]))
    va = {k: v for k, v in ((layer.get("variables") or {}).get("variables") or {}).items() if v not in (None, "")}
    if va:
        cards.append(Card("variables", "Base fonts and sizes", [item("variables", f"{os.path.splitext(os.path.basename(path))[0]} fonts and sizes", va,
                          ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in list(va.items())[:8]))],
                          "The body, table and caption fonts and sizes, spacing and margins that drive the styles."))
    ps = (layer.get("pages") or {}).get("page_setups") or {}
    if ps:
        cards.append(Card("pages", f"Page setups ({len(ps)})", [item("page_setup", k, v, ", ".join(f"{a} {b}" for a, b in v.items()))
                                                               for k, v in ps.items()]))
    hf = (layer.get("headers") or {}).get("hf_layouts") or {}
    if hf:
        cards.append(Card("headers", f"Headers and footers ({len(hf)} parts)",
                          [item("hf", k, v, f"header: {v.get('header') or 'empty'}; footer: {v.get('footer') or 'empty'}") for k, v in hf.items()],
                          "Each is a design: the number style comes from the pagination structure, so one footer serves every part."))
    hn = (layer.get("heading_numbering") or {}).get("heading_numbering")
    if hn:
        cards.append(Card("heading_numbering", "Heading numbering", [item("heading_numbering", "Heading numbering", hn,
                          "; ".join(f"{l['style']} {l['text']}" for l in hn.get("levels", [])[:4]))]))
    lnn = (layer.get("list_numbering") or {}).get("list_numbering")
    if lnn:
        cards.append(Card("list_numbering", f"List numbering ({len(lnn.get('lists', []))})",
                          [item("list_numbering", l["name"], l, ", ".join(f"{v['style']} {v['text']}" for v in l["levels"][:3])) for l in lnn.get("lists", [])]))
    ts = (layer.get("table_styles") or {}).get("table_styles") or {}
    if ts:
        cards.append(Card("table_styles", f"Word table styles ({len(ts)})", [item("table_style", k, v, "Word table style, whole") for k, v in ts.items()]))
    rt = (layer.get("tables") or {}).get("row_types") or {}
    if rt:
        cards.append(Card("tables", "Table looks by row role", [item("table_look", "Table looks", layer["tables"],
                          "; ".join(f"{r}: fill {lk.get('fill') or 'none'}" for r, lk in rt.items()))],
                          "Caption row, header, body, notes row and the rest, each with its fill, text and borders."))
    toc = (layer.get("toc") or {}).get("toc")
    if toc:
        cards.append(Card("toc", "Table of contents", [item("toc", "Table of contents", toc, " ".join(toc.get("switches", [])))]))
    pp = (layer.get("page_parts") or {}).get("page_parts") or {}
    pages = []
    for where, fn in pp.items():
        b = open(os.path.join(tmp_parts, fn), "rb").read()
        h = hashlib.sha256(b).hexdigest()[:16]
        pages.append(item("cover" if where == "cover" else "backer", f"{os.path.splitext(os.path.basename(path))[0]} {where}",
                          {"file": fn, "sha": h, "_tmp": os.path.join(tmp_parts, fn)},
                          "the page as built: pictures, tables over them, text boxes and placeholders kept whole"))
    if pages:
        cards.append(Card("pages_design", "Cover and back cover", pages))
    try:
        qps = QP.read(path)
    except Exception:                                   # noqa: BLE001
        qps = []
    if qps:
        h = hashlib.sha256(raw).hexdigest()[:10]
        cards.append(Card("quickparts", f"Quick Parts ({len(qps)})",
                          [item("quickpart", e["name"], {"entry": e["name"], "category": e["category"] or "", "gallery": e["gallery"] or "",
                                                         "source_sha": h, "description": e.get("description") or ""},
                                f"{e['category'] or 'no category'} / {QP.gallery_name(e['gallery'])}"
                                + (f", {e['pictures']} picture(s)" if e["pictures"] else "") + (f": {e['text'][:80]}" if e.get("text") else ""))
                           for e in qps],
                          "Copied whole when used: field codes, content controls, pictures and the styles they use."))
    try:                                                # 3.24.0: each part's header and footer, kept whole
        from prodengine.engine.pkg import Package
        from prodengine.pe import hf as H
        des = H.designs_of(Package.from_bytes(raw, os.path.basename(path)), std)
    except Exception:                                   # noqa: BLE001
        des = {}
    if des:
        stem = os.path.splitext(os.path.basename(path))[0]
        cards.append(Card("hf_designs", f"Header and footer designs, whole ({len(des)} parts)",
                          [item("hf_design", f"{stem} {k}", dict(v, part=k),
                                f"{k}: header and footer as built (tables at their inch widths, tab stops, pictures, fields)")
                           for k, v in des.items()],
                          "Kept exactly as built. The page numbers' style comes from the pagination structure, so a design serves any part."))
    th = theme_of_file(data=raw)
    if th:
        cards.append(Card("theme", "Theme: colors and fonts", [item("theme", th["name"], th, theme_summary(th))],
                          "Word's 12 theme colors (the palette in every color picker) and the heading and body theme fonts."))
    fonts = fonts_of(sd, data=raw)
    if fonts:
        inst = {f.casefold() for f in (installed_fonts or [])}
        cards.append(Card("fonts", f"Fonts ({len(fonts)})", [item("font", f, {"font": f}, ("installed on this PC" if f.casefold() in inst else
                          "NOT installed on this PC") if installed_fonts is not None else "") for f in fonts]))
    return cards, ""


def save_collected(lib, path, cards, tags=None, who=None, quickparts=None):
    """Keeps the ticked items of the cards (names as the person left them). Returns {"new", "same", "variant"}.
    quickparts (3.32.0): a list that gets the ids of the Quick Parts kept, to measure their pages."""
    counts = {"new": 0, "same": 0, "variant": 0}
    kept_source = None
    for c in cards:
        for it in c.items:
            if not it.get("keep"):
                continue
            values = dict(it["values"])
            if it["kind"] in ("cover", "backer"):
                values["file"] = lib.keep_file(values.pop("_tmp"), values["file"])
            if it["kind"] == "quickpart":
                kept_source = kept_source or lib.keep_file(path, os.path.basename(path))
                values["source"] = kept_source
            _item, st = lib.add(it["kind"], it["name"], values, tags=tags, source=path, summary=it.get("summary", ""), who=who)
            counts[st] += 1
            if quickparts is not None and it["kind"] == "quickpart" and not _item.get("pages"):
                quickparts.append(_item["id"])
    return counts


def cleanup(lib):
    """The work folder of a collection, taken away when it closes."""
    shutil.rmtree(os.path.join(lib.root, "_collecting"), ignore_errors=True)


# ------------------------------------------------------------------ into a standard
def use_kit(lib, kid, work):
    """Every item of a kit into the standard being edited, in the order kept. Returns what it changed, in words."""
    k = lib.kit(kid)
    if k is None:
        return []
    out = []
    for iid in k["items"]:
        s = use_in_standard(lib, iid, work, (k.get("categories") or {}).get(iid, ""))
        if s:
            out.append(s)
    return out


def use_in_standard(lib, iid, work, category=""):
    """Puts a library item into a standard being edited (a layer dict). Returns what it changed, in words."""
    it = lib.get(iid)
    v = lib.values(it) if it else None
    if v is None:
        return ""
    return use_values(lib.config_dir, it["kind"], it.get("base_name") or it["name"], v, work, category,
                      file_path=lib.source_path)


def use_values(config_dir, k, name, v, work, category="", file_path=None, src=""):
    """3.25.0: puts one item's values into a standard being edited, from the library or straight from a file being
    imported (file_path finds a kept cover's file; src is the file a Quick Part comes from). Returns what it changed."""
    v = dict(v) if isinstance(v, dict) else v
    if k == "style":
        work.setdefault("style_defs", {})[name] = {x: y for x, y in v.items()}
        return f"style {name}"
    if k == "part":                                     # 3.26.0: a part design onto the part named by category
        import partdesigns as PD
        key = category or v.get("part", "body")
        pf = ""
        if v.get("page_file") and key in ("cover", "backer"):
            import prodparts as PP
            pdir = PP.parts_dir(config_dir)
            os.makedirs(pdir, exist_ok=True)
            if not os.path.isfile(os.path.join(pdir, v["page_file"])):
                shutil.copyfile(file_path(v["page_file"]), os.path.join(pdir, v["page_file"]))
            pf = v["page_file"]
        return PD.apply_design(work, v, key, pf)
    if k == "variables":
        work.setdefault("variables", {}).update({x: y for x, y in v.items() if y not in (None, "")})
        return "base fonts and sizes"
    if k == "page_setup":
        work.setdefault("page_setups", {})[name] = v
        return f"page setup {name}"
    if k == "hf":
        work.setdefault("hf_layouts", {})[name] = v
        return f"headers and footers for {name}"
    if k == "heading_numbering":
        work["heading_numbering"] = v
        return "heading numbering"
    if k == "list_numbering":
        ln = work.setdefault("list_numbering", {"on": False, "lists": []})
        ln["lists"] = [l for l in ln.get("lists", []) if l.get("name") != v.get("name")] + [v]
        return f"list {v.get('name')}"
    if k == "table_style":
        work.setdefault("table_styles", {})[name] = v
        return f"table style {name}"
    if k == "table_look":                       # 3.32.1: each role's look goes over what the standard has, not in its place
        import prodrules as PRL
        for top, val in v.items():
            if isinstance(val, dict) and isinstance(work.get(top), dict):
                for role, look in val.items():
                    have = work[top].get(role)
                    work[top][role] = dict(copy.deepcopy(have), **look) if isinstance(have, dict) and isinstance(look, dict) else copy.deepcopy(look)
            else:
                work[top] = copy.deepcopy(val)
        PRL.repair_rows(work)
        return "table looks"
    if k == "toc":
        work["toc"] = v
        return "table of contents"
    if k in ("cover", "backer"):
        import prodparts as PP
        pdir = PP.parts_dir(config_dir)
        os.makedirs(pdir, exist_ok=True)
        if not os.path.isfile(os.path.join(pdir, v["file"])):
            shutil.copyfile(v.get("_tmp") or file_path(v["file"]), os.path.join(pdir, v["file"]))
        work.setdefault("page_parts", {})[k] = v["file"]
        return f"{'cover' if k == 'cover' else 'back cover'} {name}"
    if k == "hf_design":
        part = category or v.get("part", "body")
        work.setdefault("hf_designs", {})[part] = {x: v[x] for x in ("header", "footer", "header_media", "footer_media") if x in v}
        return f"header and footer design for {part}"
    if k == "theme":
        work["theme"] = {"name": v.get("name", ""), "xml": v.get("xml", "")}
        return f"theme {v.get('name', '')}"
    if k == "quickpart":
        import prodparts as PP
        pdir = PP.parts_dir(config_dir)
        os.makedirs(pdir, exist_ok=True)
        if not v.get("source") and src:
            import prodquickparts as QP
            v["source"] = QP.keep_source(config_dir, src)
        if not os.path.isfile(os.path.join(pdir, v["source"])):
            shutil.copyfile(file_path(v["source"]), os.path.join(pdir, v["source"]))
        qp = work.setdefault("quick_parts", {"one_gallery": True, "entries": []})
        e = {"name": v["entry"], "category": category or v.get("category", ""), "gallery": v.get("gallery", ""),
             "description": v.get("description", ""), "source": v["source"]}
        qp["entries"] = [x for x in qp.get("entries", []) if not (x.get("name") == e["name"] and x.get("source") == e["source"])] + [e]
        return f"Quick Part {v['entry']}"
    return ""
