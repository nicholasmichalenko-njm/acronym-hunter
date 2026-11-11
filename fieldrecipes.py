"""Field recipes (3.66.0): the team's exact field codes, kept as data you write, change and remove in the app (Rules >
Field recipes), never in the program. Each recipe: a name, where it is used, its field code or codes (a caption is
STYLEREF then SEQ, with the text between), the bookmark it needs and what that bookmark must span, the style it reads,
and a note. Starters come in editable. An effort can set its own code for a recipe (Effort Formatting). Every check
reads the current list: Read a template lists a file's fields, and check() says which match a recipe, which differ
and which have none.

Kept in the team's config folder (field_recipes.json), carried by a team pack; an effort's own codes in its workspace
("field_recipe_codes"). claude/stationkeeper-studio-decisions-2026-11-06.md. Rules only; nothing leaves the PC."""
import json, os, re, uuid, zipfile

WHERE = ("Table of contents", "Caption", "Header or footer", "Cross-reference", "Page number", "Other")
FILE = "field_recipes.json"
STARTERS = (
    {"name": "Response table of contents", "where": "Table of contents", "codes": ['TOC \\o "1-3" \\h \\z \\b Response'],
     "bookmark": "Response", "spans": "The response body, from the first heading to the end of the last section",
     "style": "Heading 1 to 3", "note": "Lists only what the Response bookmark holds."},
    {"name": "Appendices table of contents", "where": "Table of contents", "codes": ['TOC \\o "7-8" \\h \\z \\b Appendices'],
     "bookmark": "Appendices", "spans": "From the first appendix heading to the end of the last appendix",
     "style": "Heading 7 and 8", "note": "Appendices use Heading 7 to 9 on the same list as the body headings."},
    {"name": "Table caption", "where": "Caption", "codes": ["STYLEREF 1 \\s", "SEQ Table \\* ARABIC \\s 1"], "between": "-",
     "style": "Heading 1 (numbered)", "note": "Numbers restart in each chapter: Table 2-1."},
    {"name": "Figure caption", "where": "Caption", "codes": ["STYLEREF 1 \\s", "SEQ Figure \\* ARABIC \\s 1"], "between": "-",
     "style": "Heading 1 (numbered)", "note": "Numbers restart in each chapter: Figure 2-1."},
    {"name": "Appendix table caption", "where": "Caption", "codes": ["STYLEREF 7 \\s", "SEQ Table \\* ARABIC \\s 7"], "between": "-",
     "style": "Heading 7 (Appendix A)", "note": "Numbers restart in each appendix: Table A-1."},
    {"name": "Appendix figure caption", "where": "Caption", "codes": ["STYLEREF 7 \\s", "SEQ Figure \\* ARABIC \\s 7"], "between": "-",
     "style": "Heading 7 (Appendix A)", "note": "Numbers restart in each appendix: Figure A-1."},
    {"name": "Section title in the header", "where": "Header or footer", "codes": ["STYLEREF 1"],
     "style": "Heading 1", "note": "STYLEREF by its level number works in every language version of Office; "
                                    "STYLEREF \"Heading 1\" does the same in English."},
    {"name": "Page number", "where": "Page number", "codes": ["PAGE"],
     "note": "Each part's section sets its own format and restart (Template Studio > Parts and numbering)."},
)
_SW = re.compile(r"^\\[A-Za-z*#@!]$")


def _path(config_dir):
    return os.path.join(config_dir, FILE)


def _new_id():
    return uuid.uuid4().hex[:8]


def _clean(r):
    codes = r.get("codes") or ([r["code"]] if r.get("code") else [])
    if isinstance(codes, str):
        codes = [c for c in codes.splitlines()]
    return {"id": r.get("id") or _new_id(), "name": " ".join(str(r.get("name") or "").split()) or "A recipe",
            "where": r.get("where") if r.get("where") in WHERE else "Other",
            "codes": [" ".join(str(c).split()) for c in codes if str(c).strip()],
            "between": str(r.get("between") or ""), "bookmark": " ".join(str(r.get("bookmark") or "").split()),
            "spans": str(r.get("spans") or "").strip(), "style": str(r.get("style") or "").strip(),
            "note": str(r.get("note") or "").strip(), "starter": bool(r.get("starter")),
            "use_case": str(r.get("use_case") or "").strip(), "depends": str(r.get("depends") or "").strip(),   # 4.7.0: the Fields sheet
            "sample": str(r.get("sample") or "").strip(), "extra": dict(r.get("extra") or {})}


def starters():
    return [_clean(dict(r, id=f"s{n + 1}", starter=True)) for n, r in enumerate(STARTERS)]


def load(config_dir):
    """The team's recipes; the starters until the list is first saved."""
    try:
        with open(_path(config_dir), encoding="utf-8") as f:
            data = json.load(f)
        lst = data.get("recipes") if isinstance(data, dict) else None
        if isinstance(lst, list):
            return [_clean(r) for r in lst if isinstance(r, dict)]
    except (OSError, ValueError):
        pass
    return starters()


def save(config_dir, recipes):
    os.makedirs(config_dir, exist_ok=True)
    tmp = _path(config_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "recipes": [_clean(r) for r in recipes]}, f, indent=1)
    os.replace(tmp, _path(config_dir))
    try:                                               # 4.7.0: the Fields sheet follows
        import teamlib
        teamlib.mark_dirty(config_dir)
    except Exception:  # noqa: BLE001
        pass
    return True


def add(config_dir, recipe):
    lst = load(config_dir)
    r = _clean(dict(recipe, id=None, starter=False))
    lst.append(r)
    save(config_dir, lst)
    return r["id"]


def update(config_dir, rid, **fields):
    lst = load(config_dir)
    for i, r in enumerate(lst):
        if r["id"] == rid:
            lst[i] = _clean(dict(r, **fields, id=rid))
            save(config_dir, lst)
            return True
    return False


def remove(config_dir, rid):
    lst = load(config_dir)
    new = [r for r in lst if r["id"] != rid]
    if len(new) == len(lst):
        return False
    save(config_dir, new)
    return True


def restore_starters(config_dir):
    """Put back any starter that was taken out (one changed stays as it is)."""
    lst = load(config_dir)
    have = {r["id"] for r in lst}
    lst += [s for s in starters() if s["id"] not in have]
    save(config_dir, lst)
    return lst


# ------------------------------------------------------------------ an effort's own codes
def effective(config_dir, ws=None):
    """The team's recipes with this effort's own codes in place of the team's where it set one."""
    own = (ws.get("field_recipe_codes", {}) if ws is not None else {}) or {}
    out = []
    for r in load(config_dir):
        if isinstance(own.get(r["id"]), list) and own[r["id"]]:
            r = dict(r, codes=[" ".join(c.split()) for c in own[r["id"]] if c.strip()], effort_own=True)
        out.append(r)
    return out


def set_effort_codes(ws, rid, codes):
    """This effort's own codes for a recipe ([] gives it back to the team's)."""
    own = dict(ws.get("field_recipe_codes", {}) or {})
    codes = [" ".join(c.split()) for c in (codes or []) if c and c.strip()]
    if codes:
        own[rid] = codes
    else:
        own.pop(rid, None)
    ws.set("field_recipe_codes", own)
    return True


# ------------------------------------------------------------------ fields in a file
def normal(code):
    """A field code as Word reads it: spaces collapsed, the field name and switches in capitals, the rest as written."""
    toks = re.findall(r'"[^"]*"|\S+', (code or "").strip())
    out = []
    for n, t in enumerate(toks):
        out.append(t.upper() if n == 0 or _SW.match(t) else t)
    return " ".join(out)


def same(code):
    """normal() with STYLEREF "Heading N" read as STYLEREF N (the two do the same in English Word)."""
    return re.sub(r'^STYLEREF "HEADING ([1-9])"', r"STYLEREF \1", normal(code), flags=re.I)


def kind(code):
    """What a field is, for matching it to a recipe: ('TOC', bookmark) / ('SEQ', identifier) / ('STYLEREF', '') / (name, '')."""
    toks = re.findall(r'"[^"]*"|\S+', normal(code))
    if not toks:
        return ("", "")
    name = toks[0]
    if name == "TOC":
        b = next((toks[i + 1] for i, t in enumerate(toks[:-1]) if t == "\\B"), "")
        return ("TOC", b.strip('"'))
    if name == "SEQ" and len(toks) > 1:
        return ("SEQ", toks[1].strip('"').casefold())
    return (name, "")


def read_fields(path):
    """[(part, code)] every field in a Word file or template: complex fields (their instrText joined) and simple ones,
    in the body, headers and footers. Nested fields are listed one by one."""
    out = []
    try:
        z = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile):
        return out
    with z:
        parts = [n for n in z.namelist() if re.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$", n)]
        for n in sorted(parts, key=lambda x: (x != "word/document.xml", x)):
            xml = z.read(n).decode("utf-8", "replace")
            label = {"word/document.xml": "Body"}.get(n, os.path.splitext(os.path.basename(n))[0].replace("header", "Header ").replace("footer", "Footer ").strip())
            for m in re.finditer(r'<w:fldSimple\b[^>]*w:instr="([^"]*)"', xml):
                out.append((label, _unxml(m.group(1)).strip()))
            stack = []
            for m in re.finditer(r'<w:fldChar\b[^>]*w:fldCharType="(begin|separate|end)"|<w:instrText\b[^>]*>([^<]*)</w:instrText>', xml):
                if m.group(1) == "begin":
                    stack.append([])
                elif m.group(1) in ("separate", "end"):
                    if stack and stack[-1] is not None:
                        code = "".join(stack[-1]).strip()
                        if code:
                            out.append((label, _unxml(code)))
                        if m.group(1) == "separate":
                            stack[-1] = None
                    if m.group(1) == "end" and stack:
                        stack.pop()
                elif stack and stack[-1] is not None:
                    stack[-1].append(m.group(2) or "")
    return out


def _unxml(s):
    return s.replace("&quot;", '"').replace("&apos;", "'").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def check(fields, recipes):
    """[{part, code, status, recipe, expected}] for each field: "matches" (a recipe has it exactly), "differs" (a recipe
    for that kind of field exists and its code is not this one), "no recipe". Fields that need no recipe (PAGE when no
    recipe names it, MERGEFORMAT-only changes...) still show, so nothing is hidden."""
    by_code, by_kind = {}, {}
    for r in recipes:
        for c in r["codes"]:
            by_code.setdefault(same(c), r)
            by_kind.setdefault(kind(c), []).append((r, c))
    out = []
    for part, code in fields:
        nc = same(code)
        r = by_code.get(nc)
        if r is not None:
            out.append({"part": part, "code": code, "status": "matches", "recipe": r["name"], "expected": ""})
            continue
        cands = by_kind.get(kind(code)) or (by_kind.get((kind(code)[0], "")) if kind(code)[0] not in ("TOC", "SEQ") else None)
        if cands:
            mine = set(nc.split())
            hf = part.startswith(("Header", "Footer"))
            r, c = max(cands, key=lambda rc: (len(mine & set(same(rc[1]).split())),
                                              (rc[0]["where"] == "Header or footer") == hf))   # the closest recipe of that kind
            out.append({"part": part, "code": code, "status": "differs", "recipe": r["name"], "expected": c})
        else:
            out.append({"part": part, "code": code, "status": "no recipe", "recipe": "", "expected": ""})
    return out


def summary(rows):
    n = {"matches": 0, "differs": 0, "no recipe": 0}
    for r in rows:
        n[r["status"]] += 1
    return n


def bookmarks(path):
    """The bookmark names in a Word file (to see that a TOC's \\b bookmark exists)."""
    try:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8", "replace")
    except (OSError, KeyError, zipfile.BadZipFile):
        return []
    return list(dict.fromkeys(re.findall(r'<w:bookmarkStart\b[^>]*w:name="([^"]+)"', xml)))


def missing_bookmarks(path, recipes):
    """The bookmarks the recipes need that the file does not have (only for recipes whose fields the file uses)."""
    have = set(bookmarks(path))
    used = {kind(c) for _p, c in read_fields(path)}
    need = [r["bookmark"] for r in recipes if r.get("bookmark") and any(kind(c) in used for c in r["codes"])]
    return [b for b in dict.fromkeys(need) if b not in have]
