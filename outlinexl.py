"""The setup from an outline workbook (3.71.0; claude/stationkeeper-outline-setup-decisions-2026-11-06.md). The team's
outline is an Excel sheet: one row per requirement under its response section, with the section's number and name, the
RFP reference, the requirement, supporting RFP content, authors and management guidance. Cells can mix kinds of text by
their formatting (black italic is supporting RFP text to include; other text is customer requirement text to address).

read(path) -> {"headers", "rows": [[runs per cell]], "header_row"}   a run: (text, look); look "B?I?color"
guess(headers) -> {header: role}        looks(book, header) -> [{"look", "count", "sample"}]
parse(book, profile) -> {"sections": [{"num", "title", "level", "authors", "blocks": [{"kind", "text", "ref", "row"}]}],
                         "problems": [str]}
apply(M, parsed, file_name) -> counts   the structure, kept requirements placed in their sections (the RFPL number as
                                         their reference), customer and supporting text beside them, guidance as each
                                         requirement's note (or the section's direction), authors as the section's lead
Profiles (column roles and the kind for each look) are the team's: config outline_profiles.json. The workbook is only
read. Rules only; nothing leaves the PC."""
import json, os, re

ROLES = (("section_number", "Section number"), ("section_name", "Section name"), ("reference", "RFP reference"),
         ("requirement", "Requirement"), ("support", "Supporting RFP content"), ("guidance", "Management guidance"),
         ("authors", "Authors"),
         # 3.90.0 (decision 13): a workbook with Section L and Section M side by side, or a column saying which
         ("requirement_l", "Section L requirement"), ("requirement_m", "Section M requirement"),
         ("reference_l", "Section L reference"), ("reference_m", "Section M reference"), ("lm", "L or M"),
         ("ignore", "Not used"))
ROLE = dict(ROLES)
TEXT_ROLES = ("requirement", "support", "guidance", "requirement_l", "requirement_m")    # columns of text, each look its own kind
STRUCT_ROLES = ("section_number", "section_name", "reference", "authors", "reference_l", "reference_m", "lm")
# the setup kinds the text goes to (setuptemplate's): what each column's text is when no formatting rule says otherwise
DEFAULT_KIND = {"requirement": "rfp", "support": "support", "guidance": "pm", "requirement_l": "rfp_l", "requirement_m": "rfp_m"}
KINDS = (("rfp", "Compliance requirement"), ("rfp_l", "Section L requirement (instruction)"),
         ("rfp_m", "Section M requirement (evaluation)"), ("customer", "Customer requirement text"),
         ("support", "Supporting RFP text"), ("pm", "Management guidance"), ("skip", "Leave out"))
RFP_KINDS = {"rfp": "", "rfp_l": "L", "rfp_m": "M"}         # 3.90.0: every kind that is a compliance requirement, and its L or M
KIND = dict(KINDS)
GUESS = (("reference_l", r"solicitation\s*requirements?\s*\(?\s*section\s*l\b|section\s*l\s*(ref|reference|number|no|para)|^l\s*(ref|reference|para)"),
         ("reference_m", r"evaluation\s*section|section\s*m\s*(ref|reference|number|no|para)|^m\s*(ref|reference|para)"),
         ("requirement_l", r"section\s*l\s*(content|text|requirement|instruction)|^l\s*(content|text|requirement)"),
         ("requirement_m", r"evaluation\s*(content|text|criteria)|section\s*m\s*(content|text|requirement|criteria)|^m\s*(content|text|requirement)"),
         ("lm", r"^(l\s*/\s*m|l\s*(&|and|n|or)\s*m|lnm|lm|section\s*l\s*/\s*m|l\s*or\s*m\s*\??)$"),
         ("section_number", r"(section|sec)\.?\s*(number|no|num|#)|^number$|^no\.?$"), ("section_name", r"(section|heading)\s*(name|title)|^title$|^name$"),
         ("reference", r"rfp\s*l?\s*(number|no|ref|reference)|^ref(erence)?$|rfp\s*para|l\s*number|source\s*ref|^sources?$|source\s*(info|information|location)"),   # 3.91.0: Source
         ("requirement", r"compliance\s*req|requirement"), ("support", r"support|rfp\s*content|context"),
         ("guidance", r"management|guidance|direction|pm\s*note"), ("authors", r"author|writer|owner|lead"))
FILE = "outline_profiles.json"


# ---------------------------------------------------------------- reading the workbook
def _hex(color):
    rgb = getattr(color, "rgb", None) if color is not None else None
    if isinstance(rgb, str) and len(rgb) >= 6 and getattr(color, "type", "rgb") == "rgb":
        h = rgb[-6:].upper()
        return "auto" if h == "000000" else h
    return "auto"                                           # theme or automatic: the text color (black)


def look_of(font):
    """'BI7030A0', '-I auto' style keys: bold, italic, color."""
    if font is None:
        return "--auto"
    b = bool(getattr(font, "b", None) or getattr(font, "bold", None))
    i = bool(getattr(font, "i", None) or getattr(font, "italic", None))
    return ("B" if b else "-") + ("I" if i else "-") + _hex(getattr(font, "color", None))


COLOR_WORDS = ("black", "gray", "red", "orange", "yellow", "green", "blue", "purple")


def color_word(col):
    """The plain name of a hex color ("C00000" is red), or black for the automatic color (3.73.0)."""
    c = str(col or "auto").lstrip("#").upper()
    if c in ("AUTO", "") or len(c) != 6:
        return "black"
    try:
        r, g, b = (int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return "black"
    hi, lo = max(r, g, b), min(r, g, b)
    if hi < 0.25:
        return "black"
    if hi - lo < 0.15 or (hi - lo) / hi < 0.2:
        return "gray"
    d = hi - lo
    h = (60 * ((g - b) / d) % 360) if hi == r else (60 * ((b - r) / d + 2)) if hi == g else (60 * ((r - g) / d + 4))
    for top, word in ((15, "red"), (45, "orange"), (70, "yellow"), (170, "green"), (260, "blue"), (345, "purple"), (361, "red")):
        if h < top:
            return word
    return "red"


def look_words(look):
    """A look in plain words: "italic black", "bold red (#C00000)"."""
    bits = [w for w, on in (("bold", look[0] == "B"), ("italic", look[1] == "I")) if on]
    col = look[2:]
    bits.append("black" if col == "auto" else f"{color_word(col)} (#{col})")
    return " ".join(bits)


def _runs(cell):
    v = cell.value
    if v is None:
        return []
    try:
        from openpyxl.cell.rich_text import CellRichText, TextBlock
    except ImportError:                                     # an older openpyxl: the cell's own look
        CellRichText = TextBlock = ()
    base = look_of(cell.font)
    if CellRichText and isinstance(v, CellRichText):
        out = []
        for part in v:
            if TextBlock and isinstance(part, TextBlock):
                f = part.font
                # a run that sets nothing takes the cell's look for what it leaves out
                b = f.b if getattr(f, "b", None) is not None else base[0] == "B"
                i = f.i if getattr(f, "i", None) is not None else base[1] == "I"
                c = _hex(f.color) if getattr(f, "color", None) is not None else base[2:]
                out.append((part.text, ("B" if b else "-") + ("I" if i else "-") + c))
            else:
                out.append((str(part), base))
        return [(t, lk) for t, lk in out if t]
    return [(str(v), base)]


def read(path, sheet=None, known=None):
    from openpyxl import load_workbook
    wb = load_workbook(path, rich_text=True, data_only=True)
    try:
        ws = wb[sheet] if sheet else wb.worksheets[0]
        rows = [list(r) for r in ws.iter_rows()]
    finally:
        wb.close()
    hi = 0
    for n, r in enumerate(rows[:20]):                       # the header row: the first with three or more words that read as headings
        words = [str(c.value).strip() for c in r if c.value not in (None, "") and isinstance(c.value, str)]
        kn = known or set()                                 # 3.73.0: the headings the outline layouts name count too
        if len(words) >= 3 and sum(1 for w in words if guess_one(w) != "ignore" or " ".join(w.casefold().split()).rstrip(":.") in kn) >= 2:
            hi = n
            break
    headers = [" ".join(str(c.value or "").split()) for c in rows[hi]] if rows else []
    body = []
    for r in rows[hi + 1:]:
        cells = [_runs(c) for c in r]
        if any(cells):
            body.append({"row": r[0].row if r else 0, "cells": cells})
    return {"headers": headers, "rows": body, "header_row": hi + 1, "file": os.path.basename(path)}


def guess_one(header):
    h = " ".join(str(header or "").lower().split())
    for role, rx in GUESS:
        if re.search(rx, h):
            return role
    return "ignore"


def guess(headers):
    out, taken = {}, set()
    for h in headers:
        if not h:
            continue
        r = guess_one(h)
        if r != "ignore" and r in taken and r not in ("support",):
            r = "ignore"
        out[h] = r
        taken.add(r)
    return out


def looks(book, header):
    """Every distinct look in a column, with how often and a sample, most used first."""
    if header not in book["headers"]:
        return []
    i = book["headers"].index(header)
    seen = {}
    for r in book["rows"]:
        for t, lk in (r["cells"][i] if i < len(r["cells"]) else []):
            if not t.strip():
                continue
            s = seen.setdefault(lk, {"look": lk, "count": 0, "sample": ""})
            s["count"] += 1
            s["sample"] = s["sample"] or " ".join(t.split())[:80]
    return sorted(seen.values(), key=lambda x: -x["count"])


# ---------------------------------------------------------------- profiles
def load_profiles(config_dir):
    try:
        with open(os.path.join(config_dir, FILE), encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        d = {}
    return d if isinstance(d, dict) else {}


def save_profile(config_dir, name, profile):
    d = load_profiles(config_dir)
    d[name] = {"columns": dict(profile.get("columns") or {}), "rules": {k: dict(v) for k, v in (profile.get("rules") or {}).items()}}
    os.makedirs(config_dir, exist_ok=True)
    p = os.path.join(config_dir, FILE)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
    os.replace(p + ".tmp", p)
    return d[name]


def profile_for(config_dir, headers):
    """The saved profile whose columns are this workbook's headings, else a new one from the guesses."""
    hs = {h for h in headers if h}
    for name, p in load_profiles(config_dir).items():
        if set(p.get("columns") or {}) == hs:
            return dict(p, name=name)
    return {"name": "", "columns": guess(headers), "rules": {}}


# ---------------------------------------------------------------- L or M (3.90.0)
_BOTH = re.compile(r"^(l\s*(/|&|\+|and|n)\s*m|m\s*(/|&|\+|and|n)\s*l|lnm|lm|both)$", re.I)


def lm_of_cell(t):
    """An "L or M" cell: "L", "M", or "LM" for both (L/M, L&M, L and M, LNM, both); "" otherwise."""
    t = " ".join((t or "").split()).strip(" .:").replace("Section ", "").replace("section ", "")
    if not t:
        return ""
    if _BOTH.match(t):
        return "LM"
    u = t.upper()
    return u if u in ("L", "M") else ""


def lm_of_ref(ref):
    """L, M or LM from an RFP reference: L.3.5 is L; M.2.1 is M; "L.3.5; M.2.1" or "Section L 3.5 / M 2" is both."""
    r = " ".join((ref or "").split())
    if re.match(r"^\s*(lnm|l\s*[/&]\s*m)\b", r, re.I):
        return "LM"
    sides = {m.group(1).upper() for m in re.finditer(r"(?:^|[\s,;/(])(?:Section\s+)?([LM])(?:[.\s-]\d|\s*$|[.\s-]*[A-Z0-9]*\.?\d)", r, re.I)}
    if sides == {"L", "M"}:
        return "LM"
    return sides.pop() if len(sides) == 1 else ""


# ---------------------------------------------------------------- parsing
def _level(num):
    n = str(num or "").strip().rstrip(".")
    return n.count(".") + 1 if n else 1


def _num_key(num):
    return [int(p) if p.isdigit() else p for p in re.split(r"[.]", str(num).strip().rstrip("."))]


def _text(runs):
    return " ".join("".join(t for t, _lk in runs).split())


def _pieces(runs, column, rules, default):
    """A cell's runs as [(kind, text)]: each run's kind by its look's rule, runs of one kind joined; new lines split."""
    out = []
    for t, lk in runs:
        k = (rules.get(column) or {}).get(lk, default)
        for n, part in enumerate(t.split("\n")):
            if n and out:
                out.append((None, None))                       # a line break ends a block
            if out and out[-1][0] == k:
                out[-1] = (k, out[-1][1] + part)
            else:
                out.append((k, part))
    return [(k, " ".join(t.split())) for k, t in out if k and k != "skip" and t and t.strip()]


def parse(book, profile):
    cols = profile.get("columns") or {}
    rules = profile.get("rules") or {}
    idx = {role: i for i, h in enumerate(book["headers"]) for r_, role in [(h, cols.get(h))] if role and role != "ignore"}
    sections, problems, cur, unruled = [], [], None, set()
    for r in book["rows"]:
        cells = r["cells"]

        def cell(role):
            i = idx.get(role)
            return cells[i] if i is not None and i < len(cells) else []
        num, name = _text(cell("section_number")), _text(cell("section_name"))
        if num or name:
            if cur is None or num != cur["num"] or (name and name != cur["title"]):
                again = next((x for x in sections if x["num"] == num and x["title"] == (name or num)), None)
                if again is not None:                     # the same section again later: its rows join it
                    problems.append(f"Row {r['row']}: section {num or name} again after {cur['num'] or cur['title']}; its rows join "
                                    f"the first {num or name}")
                    cur = again
                else:
                    cur = {"num": num, "title": name or num, "level": _level(num), "authors": [], "blocks": [], "row": r["row"]}
                    sections.append(cur)
        if cur is None:
            cur = {"num": "", "title": "(No section)", "level": 1, "authors": [], "blocks": [], "row": r["row"]}
            sections.append(cur)
            problems.append(f"Row {r['row']}: text before any section; it sits under (No section)")
        for a in re.split(r"[;,\n]", _text(cell("authors"))):
            if a.strip() and a.strip() not in cur["authors"]:
                cur["authors"].append(a.strip())
        ref = _text(cell("reference"))
        side_ref = {"L": _text(cell("reference_l")), "M": _text(cell("reference_m"))}
        row_lm = lm_of_cell(_text(cell("lm")))
        for i, h in enumerate(book["headers"]):                # every column of text, left to right (3.73.0)
            role = cols.get(h)
            if role not in TEXT_ROLES or i >= len(cells):
                continue
            for t, lk in cells[i]:
                if role in ("support",) and lk not in (rules.get(h) or {}) and t.strip():
                    unruled.add((h, lk))
            for kind, text in _pieces(cells[i], h, rules, DEFAULT_KIND[role]):
                if kind in RFP_KINDS:                          # 3.90.0: L or M from the kind, the L or M column, the reference
                    lm = RFP_KINDS[kind] or {"requirement_l": "L", "requirement_m": "M"}.get(role, "") or row_lm
                    rf = (side_ref.get(lm) if lm in ("L", "M") else "") or ref or side_ref["L"] or side_ref["M"]
                    cur["blocks"].append({"kind": "rfp", "text": text, "ref": rf, "row": r["row"], "lm": lm or lm_of_ref(rf)})
                    continue
                cur["blocks"].append({"kind": kind, "text": text, "ref": "", "row": r["row"]})
        ref = ref or side_ref["L"] or side_ref["M"]
        if ref and not any(b["kind"] == "rfp" and b["row"] == r["row"] for b in cur["blocks"]):
            problems.append(f"Row {r['row']}: an RFP reference ({ref}) with no requirement text")
        for b in cur["blocks"]:
            if b["kind"] == "rfp" and b["row"] == r["row"] and not b["ref"]:
                problems.append(f"Row {r['row']}: a requirement with no RFP reference")
    nums = [s["num"] for s in sections if s["num"]]
    for a, b in zip(nums, nums[1:]):
        try:
            if _num_key(b) <= _num_key(a):
                problems.append(f"Section {b} comes after {a}: out of order or repeated")
        except TypeError:
            pass
    for h, lk in sorted(unruled, key=lambda x: (str(x[0]), x[1])):
        problems.append(f"{h}: text in {look_words(lk)} has no rule of its own; it is treated as {KIND[DEFAULT_KIND['support']]}")
    return {"sections": sections, "problems": problems}


# ---------------------------------------------------------------- into the effort
def apply(M, parsed, file_name, who=None):
    """The structure and its blocks into the compliance matrix and the setup. Items an earlier import of this workbook
    made are replaced; requirements from anywhere else stay (unplaced if their section is gone). Returns counts."""
    import compliance as C
    import setupdoc as SD
    S = SD.setup_of(M)
    old = {it["id"] for it in M.items if it.get("src") == "outline" and it.get("file") == file_name}
    for lab, txt in ((S.get("outline_import") or {}).get(file_name, {}).get("mgmt") or {}).items():   # 3.73.0: its own guidance
        if " ".join((S["mgmt"].get(lab) or "").split()) == " ".join((txt or "").split()):              # out first, not twice
            S["mgmt"].pop(lab, None)
    M.items = [it for it in M.items if it["id"] not in old]
    for lab in list(S["order"]):
        S["order"][lab] = [i for i in S["order"][lab] if i not in old]
    for i in old:
        S["notes"].pop(i, None); S["refs"].pop(i, None)
    M.outline = [{"num": s["num"], "title": s["title"], "level": max(1, min(s["level"], 12))} for s in parsed["sections"]]
    used = {it["id"] for it in M.items}
    n = {"sections": len(M.outline), "requirements": 0, "customer": 0, "support": 0, "guidance": 0}
    stem = re.sub(r"[^A-Za-z0-9]+", "", os.path.splitext(file_name)[0])[:8] or "OUT"

    def new_id():
        k = 1
        while f"OL{stem}-{k:03d}" in used:
            k += 1
        used.add(f"OL{stem}-{k:03d}")
        return f"OL{stem}-{k:03d}"

    def item(text, ref, row, decision, typ, **extra):
        it = {"id": new_id(), "file": file_name, "loc": f"Row {row}", "page": "", "text": text, "lead": "", "section": ref,
              "section_title": "", "actor": "", "type": typ, "strength": "", "suggest": decision, "modal": "", "xrefs": "",
              "compound": False, "key": C.text_key(text), "decision": decision, "map": "", "owner": "", "status": "", "notes": "",
              "response_page": "", "links": "", "new": "", "learned": "", "src": "outline"}
        it.update(extra)
        M.items.append(it)
        return it
    for s, o in zip(parsed["sections"], M.outline):
        lab = C.outline_label(o)
        if s["authors"]:
            S["owners"][lab] = {"lead": s["authors"][0], "with": ", ".join(s["authors"][1:])}
        last = None
        for b in s["blocks"]:
            if b["kind"] == "rfp":
                lm = b.get("lm") or ""                          # 3.90.0: the workbook says L, M or both
                extra = {"lm": "L" if lm == "LM" else lm, "lm_both": True} if lm == "LM" else ({"lm": lm} if lm in ("L", "M") else {})
                it = item(b["text"], b["ref"], b["row"], "Keep", "Requirement", **extra)
                if b["ref"]:
                    S["refs"][it["id"]] = b["ref"]
                SD.place(M, it["id"], lab)
                last = it
                n["requirements"] += 1
            elif b["kind"] == "customer":
                it = item(b["text"], "", b["row"], "Customer", "Context")
                SD.place(M, it["id"], lab)
                n["customer"] += 1
            elif b["kind"] == "support":
                it = item(b["text"], "", b["row"], "Context", "Context", context_for=last["id"] if last else "", kind="context")
                SD.place(M, it["id"], lab)
                n["support"] += 1
            elif b["kind"] == "pm":
                if last is not None and last.get("loc") == f"Row {b['row']}":
                    S["notes"][last["id"]] = (S["notes"].get(last["id"], "") + "\n" + b["text"]).strip()
                else:
                    S["mgmt"][lab] = (S["mgmt"].get(lab, "") + "\n" + b["text"]).strip()
                n["guidance"] += 1
    mg = {C.outline_label(o): S["mgmt"][C.outline_label(o)] for o in M.outline if S["mgmt"].get(C.outline_label(o))}
    S.setdefault("outline_import", {})[file_name] = {"sections": n["sections"], "requirements": n["requirements"], "who": who or "",
                                                     "mgmt": mg}
    return n
