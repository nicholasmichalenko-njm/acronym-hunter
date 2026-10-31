"""Tables: give every row a role, then apply the role's look. Works on a w:tbl element (lxml), so the same code
serves a closed file (engine + unit guard) and the document open in Word (table XML read and written back in
one undo step).

classify(tbl, std, table_type)  -> [RowDecision]   (nothing is changed)
apply(tbl, decisions, std, table_type, style_ids) -> report  (changes the table in place)

Rules (decided 2026-10-29):
- A row already in a row type's tag style keeps that role (that is how manual choices persist).
- Position decides only the caption row (row 1, or the last row of a figure table), the header row (the row
  after the caption) and a second header row (also marked to repeat).
- Every other role comes from an explicit rule in std["row_rules"]; a rule with sure=False becomes a question,
  grouped by pattern so one answer covers every row of that pattern. Nothing is guessed silently.
- apply() never changes cell text, never deletes a row or cell, never changes column widths. It merges a
  caption or note row into one cell only when the other cells are empty, so no text can be lost.
"""
import re
from dataclasses import dataclass, field

from lxml import etree
from prodengine.engine.pkg import W, NS
from prodengine.engine.ordered import ensure, remove, q
from prodengine.engine.fingerprint import visible_text
from prodengine.pe import rules as R

WR, WP, WT = q("r"), q("p"), q("t")
DIRECT_RUN = ("rFonts", "sz", "szCs", "b", "bCs", "i", "iCs", "color")
CAPTION_RX = re.compile(r"^(Table|Figure|Exhibit|Chart)\s*[\dA-Z]", re.I)


@dataclass
class RowDecision:
    index: int                    # 0-based row index
    role: str
    status: str                   # "sure" | "ask" | "tagged" | "manual"
    rule: str                     # rule key or "tag" / "position"
    why: str
    group: str = ""               # questions with the same group get one answer
    first_text: str = ""
    cells: int = 0
    options: list = field(default_factory=list)


# ---------------------------------------------------------------- reading a row
def rows(tbl):
    return tbl.findall("w:tr", NS)


def grid_cols(tbl):
    return len(tbl.findall("w:tblGrid/w:gridCol", NS))


def cells(tr):
    return tr.findall("w:tc", NS)


def span(tc):
    gs = tc.find("w:tcPr/w:gridSpan", NS)
    return int(gs.get(q("val"))) if gs is not None else 1


def own_paras(tc):
    """Paragraphs of the cell itself, not of a table nested in it."""
    return [p for p in tc.iter(WP) if next(p.iterancestors(q("tc"))) is tc]


def text_of(tc):
    return " ".join(visible_text(p).replace("¶", " ").strip() for p in own_paras(tc)).strip()


def row_texts(tr):
    return [text_of(tc) for tc in cells(tr)]


def fill_of(tr):
    fills = {(s.get(q("fill")) or "").upper() for tc in cells(tr) for s in tc.findall("w:tcPr/w:shd", NS)}
    fills.discard(""); fills.discard("AUTO"); fills.discard("FFFFFF")
    return fills.pop() if len(fills) == 1 else (None if not fills else "MIXED")


def all_bold(tr):
    runs = [r for tc in cells(tr) for p in own_paras(tc) for r in p.findall("w:r", NS) if r.find("w:t", NS) is not None
            and (r.find("w:t", NS).text or "").strip()]
    if not runs:
        return False
    def b(r):
        el = r.find("w:rPr/w:b", NS)
        return el is not None and el.get(q("val")) not in ("0", "false")
    return all(b(r) for r in runs)


def repeats(tr):
    h = tr.find("w:trPr/w:tblHeader", NS)
    return h is not None and h.get(q("val")) not in ("0", "false")


def has_seq(tr):
    return any("SEQ" in (t.text or "") for t in tr.iter(q("instrText"))) or \
        any("SEQ" in (f.get(q("instr")) or "") for f in tr.iter(q("fldSimple")))


def pstyles(tr, style_names):
    """Names of the paragraph styles used in the row's own paragraphs."""
    out = set()
    for tc in cells(tr):
        for p in own_paras(tc):
            ps = p.find("w:pPr/w:pStyle", NS)
            if ps is not None:
                out.add(style_names.get(ps.get(q("val")), ps.get(q("val"))))
    return out


def single_merged(tr, ncols):
    cs = cells(tr)
    return ncols > 1 and len(cs) == 1 and span(cs[0]) >= ncols


def is_caption_row(tr):
    t = " ".join(x for x in row_texts(tr) if x)
    return bool(CAPTION_RX.match(t)) and (has_seq(tr) or bool(re.match(r"^\w+\s+[\dA-Z]+[\-.\d]*", t)))


def has_content(tr):
    """Text, a picture, an object or a nested table: anything a person put in the row."""
    return any(row_texts(tr)) or tr.find(".//w:drawing", NS) is not None or tr.find(".//w:pict", NS) is not None \
        or tr.find(".//w:object", NS) is not None or tr.find(".//w:tbl", NS) is not None


def is_figure_table(tbl):
    return grid_cols(tbl) == 1 and tbl.find(".//w:drawing", NS) is not None


# ---------------------------------------------------------------- classify
def _first_text(texts):
    return next((t for t in texts if t), "")


def _match(rule, tr, i, n, ncols, texts):
    kind, val = rule["kind"], rule.get("value")
    first = _first_text(texts)
    if kind == "fill_in":
        f = fill_of(tr)
        return f is not None and f in {v.upper() for v in val}
    if kind == "first_cell_starts":
        return any(re.match(r"^" + re.escape(v) + r"(\b|\W|$)", first, re.I) for v in val)
    if kind == "first_cell_contains_word":
        return any(re.search(r"\b" + re.escape(v) + r"\b", first, re.I) for v in val)
    if kind == "last_row_merged":
        return i == n - 1 and single_merged(tr, ncols)
    if kind == "single_merged_cell":
        return single_merged(tr, ncols)
    if kind == "bold_row":
        return all_bold(tr)
    if kind == "empty_row":
        return not any(texts)
    if kind == "other":
        return True
    return False


def _group(rule, texts):
    """Rows that ask the same question share a group: the rule plus the first word, normalized."""
    first = _first_text(texts)
    word = re.split(r"[\s,\-:]+", first.strip())[0].lower() if first else ""
    word = re.sub(r"\d", "#", word)
    return f"{rule['key']}:{word}"


def classify(tbl, std, table_type="std", style_names=None):
    style_names = style_names or {}
    tag_to_role = {}
    for role in std["row_types"]:
        look = R.row_look(std, role, table_type)
        tag_to_role[look["tag_style"].lower()] = role
    trs = rows(tbl)
    n, ncols = len(trs), grid_cols(tbl)
    figure = std["table_types"].get(table_type, {}).get("caption_position") == "below" or is_figure_table(tbl)
    out = []
    header_seen = 0
    for i, tr in enumerate(trs):
        texts = row_texts(tr)
        d = None
        tagged = {s.lower() for s in pstyles(tr, style_names)} & set(tag_to_role)
        if len(tagged) == 1:
            role = tag_to_role[tagged.pop()]
            d = RowDecision(i, role, "tagged", "tag", "Already in the " + R.row_look(std, role, table_type)["tag_style"] + " style")
        elif (i == 0 and not figure or figure and i == n - 1) and is_caption_row(tr):
            d = RowDecision(i, "caption", "sure", "R10", "Caption: a Table or Figure label with its number")
        elif not figure and i == 0 and not any(texts):
            d = None
        elif not figure and i == 0:
            d = RowDecision(i, "header", "ask", "R21", "This table has no caption row; is row 1 the header?",
                            group="R21:nocaption", options=["header", "caption", "body"])
        elif not figure and out and out[0].role == "caption" and i == 1:
            d = RowDecision(i, "header", "sure", "R20", "The row right after the caption row")
            header_seen = 1
        elif not figure and header_seen and i == 2 and repeats(tr) and not single_merged(tr, ncols):
            d = RowDecision(i, "header2", "sure", "R25", "Under the header and marked to repeat on each page")
        else:
            for rule in std["row_rules"]:
                if rule["kind"] in ("caption_row", "header_row", "header_row2"):
                    continue
                if _match(rule, tr, i, n, ncols, texts):
                    status = "sure" if rule.get("sure") else "ask"
                    d = RowDecision(i, rule["role"], status, rule["key"], rule["why"],
                                    group=_group(rule, texts) if status == "ask" else "")
                    if status == "ask":
                        d.options = _options(rule["role"])
                    break
        if d is None or (not any(texts) and not has_content(tr) and d.role not in ("caption",)):
            d = RowDecision(i, "keep", "ask", "R00", "An empty row: keep it, or remove it after the fix",
                            group="R00:empty", options=["keep", "body"])
        d.first_text = _first_text(texts)[:80]
        d.cells = len(cells(tr))
        out.append(d)
    allowed = set(std["table_types"].get(table_type, {}).get("roles", R.ROLES))
    for d in out:
        if d.role not in allowed and d.role != "keep" and d.status in ("sure", "ask"):
            d.status, d.why = "ask", d.why + f" (this table type has no {d.role} row)"
            d.group = d.group or f"notallowed:{d.role}"
            d.options = sorted(allowed)
    return out


def _options(role):
    return {"subtotal": ["subtotal", "total", "body", "keep"], "note": ["note", "body", "keep"],
            "subhead": ["subhead", "body", "keep"]}.get(role, [role, "body", "keep"])


def questions(decisions):
    """One question per group: {group: {"rows": [...], "suggested": role, "why": ..., "options": [...]}}."""
    qs = {}
    for d in decisions:
        if d.status != "ask":
            continue
        g = qs.setdefault(d.group, {"rows": [], "suggested": d.role, "why": d.why, "options": d.options,
                                    "example": d.first_text})
        g["rows"].append(d.index)
    return qs


def answer(decisions, group, role):
    for d in decisions:
        if d.status == "ask" and d.group == group:
            d.role, d.status, d.why = role, "manual", d.why + " (you chose)"
    return decisions


def set_role(decisions, indexes, role):
    for d in decisions:
        if d.index in indexes:
            d.role, d.status, d.why = role, "manual", "Set by you"
    return decisions


def learn_rule(std, group, role):
    """Turn an answered question into a sure rule (first_cell_starts on the group's first word), placed before
    the asking rules. Returns the new rule or None when the group has no first word."""
    key, word = group.split(":", 1)
    if key in ("R00", "R21") or group.startswith("notallowed"):
        return None                       # empty rows and a missing caption are decided per table, never learned
    n = len([r for r in std["row_rules"] if r["key"].startswith("L")]) + 1
    if word and word.isalpha():
        rule = {"key": f"L{n:02d}", "kind": "first_cell_starts", "value": [word.capitalize()], "role": role,
                "sure": True, "why": f"First text cell starts with {word.capitalize()} (learned)"}
    else:                                 # no usable first word (for example "3.0 total"): the asking rule, made sure
        base = next((r for r in std["row_rules"] if r["key"] == key), None)
        if base is None:
            return None
        rule = dict(base, key=f"L{n:02d}", role=role, sure=True, why=base["why"].split(";")[0] + f": {role} (learned)")
    at = next((i for i, r in enumerate(std["row_rules"]) if not r.get("sure")), len(std["row_rules"]) - 1)
    std["row_rules"].insert(at, rule)
    return rule


# ---------------------------------------------------------------- apply
def _edge_xml(tcb, side, spec):
    remove(tcb, side)
    el = ensure(tcb, side)
    if spec:
        width, color = spec
        el.set(q("val"), "single"); el.set(q("sz"), str(int(round(float(width) * 8))))
        el.set(q("space"), "0"); el.set(q("color"), color.upper())
    else:
        el.set(q("val"), "nil")


def _merge_if_empty(tr, ncols, mark=lambda el: None):
    """Merge a row into one cell only when every cell but the first is empty. Returns True when merged."""
    cs = cells(tr)
    if len(cs) <= 1 or any(text_of(tc) for tc in cs[1:]):
        return False
    if any(tc.find(".//w:drawing", NS) is not None or tc.find(".//w:tbl", NS) is not None for tc in cs[1:]):
        return False
    first = cs[0]
    total = sum(span(tc) for tc in cs)
    for tc in cs[1:]:
        for el in tc.iter():
            mark(el)
        tr.remove(tc)
    tcpr = first.find("w:tcPr", NS)
    if tcpr is None:
        tcpr = etree.Element(q("tcPr")); first.insert(0, tcpr)
    ensure(tcpr, "gridSpan", {"val": total})
    return True


def apply(tbl, decisions, std, table_type, style_ids, skip_asked=True, mark=lambda el: None, merge=False):
    """Apply the look of each decided row. style_ids: tag style name -> styleId (styles must exist).
    Returns a report with counts and what was left alone."""
    tt = std["table_types"].get(table_type, {})
    ncols = grid_cols(tbl)
    trs = rows(tbl)
    rep = {"rows": len(trs), "styled": 0, "left_alone": [], "merged": 0, "should_merge": [], "repeat_rows": 0}
    before = [row_texts(tr) for tr in trs]
    lead = True
    for d, tr in zip(decisions, trs):
        if (d.status == "ask" and skip_asked) or d.role == "keep":
            rep["left_alone"].append(d.index)
            lead = False
            continue
        look = R.row_look(std, d.role, table_type)
        if look.get("merge") is True and len(cells(tr)) > 1:
            if merge and _merge_if_empty(tr, ncols, mark):
                rep["merged"] += 1
            else:
                rep["should_merge"].append(d.index)   # its own step (op_merge_rows): it removes empty cells
        trpr = tr.find("w:trPr", NS)
        want_repeat = bool(look.get("repeat")) and lead
        if want_repeat:
            if trpr is None:
                trpr = etree.Element(q("trPr")); tr.insert(0 if tr.find("w:tblPrEx", NS) is None else 1, trpr)
            if trpr.find("w:tblHeader", NS) is None:
                etree.SubElement(trpr, q("tblHeader"))
            rep["repeat_rows"] += 1
        else:
            lead = False
            if trpr is not None:
                remove(trpr, "tblHeader")
        cs = cells(tr)
        for ci, tc in enumerate(cs):
            tcpr = tc.find("w:tcPr", NS)
            if tcpr is None:
                tcpr = etree.Element(q("tcPr")); tc.insert(0, tcpr)
            tcb = ensure(tcpr, "tcBorders")
            e = look.get("edges") or {}
            _edge_xml(tcb, "top", e.get("top"))
            _edge_xml(tcb, "bottom", e.get("bottom"))
            _edge_xml(tcb, "left", e.get("left") if ci == 0 else e.get("inside_v"))
            _edge_xml(tcb, "right", e.get("right") if ci == len(cs) - 1 else e.get("inside_v"))
            remove(tcpr, "shd")
            if look.get("fill"):
                ensure(tcpr, "shd", {"val": "clear", "color": "auto", "fill": look["fill"].upper()})
            ensure(tcpr, "vAlign", {"val": look.get("valign") or "top"})
            for p in own_paras(tc):
                ppr = p.find("w:pPr", NS)
                if ppr is None:
                    ppr = etree.Element(q("pPr")); p.insert(0, ppr)
                ensure(ppr, "pStyle", {"val": style_ids[look["tag_style"]]})
                remove(ppr, "spacing", "ind", "jc")           # the style holds these values
                mark = ppr.find("w:rPr", NS)
                if mark is not None:
                    remove(mark, *DIRECT_RUN)
                for r in p.findall("w:r", NS) + [r for h in p.findall("w:hyperlink", NS) for r in h.findall("w:r", NS)]:
                    rpr = r.find("w:rPr", NS)
                    if rpr is not None:
                        remove(rpr, *DIRECT_RUN)
                        if len(rpr) == 0:
                            r.remove(rpr)
        rep["styled"] += 1
    tblpr = tbl.find("w:tblPr", NS)
    if tblpr is None:
        tblpr = etree.Element(q("tblPr")); tbl.insert(0, tblpr)
    if tt.get("width_pct"):
        ensure(tblpr, "tblW", {"w": int(tt["width_pct"] * 50), "type": "pct"})
    if tt.get("align"):
        ensure(tblpr, "jc", {"val": tt["align"]})
    b = ensure(tblpr, "tblBorders")                           # cell borders carry the look; no table grid
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        ensure(b, side, {"val": "nil"})
    m = tt.get("cell_margins")
    if m:
        cm = ensure(tblpr, "tblCellMar")
        for side in ("top", "left", "bottom", "right"):
            ensure(cm, side, {"w": int(round(m[side] * 20)), "type": "dxa"})
    after = [row_texts(tr) for tr in rows(tbl)]
    # text proof: the same words in the same order, row by row (a merge only removes empty cells)
    rep["text_same"] = [" ".join(x for x in a if x) for a in before] == [" ".join(x for x in a if x) for a in after]
    rep["rows_same"] = len(after) == len(before)
    return rep


# ---------------------------------------------------------------- styles for the row types
def ensure_tag_styles(styles_root, std, table_type):
    """Create or update the tag style of every role of the table type. Returns {tag style name: styleId}."""
    from prodengine.engine.ops.word_ops import find_style, new_style, set_run_props, set_para_props
    ids = {}
    for role in std["row_types"]:          # every role: a person may give any row any role
        look = R.row_look(std, role, table_type)
        s = find_style(styles_root, look["tag_style"])
        if s is None:
            s = new_style(styles_root, look["tag_style"])
        rpr = ensure(s, "rPr")
        set_run_props(rpr, font=look.get("font"), size=look.get("size"), bold=look.get("bold"),
                      italic=look.get("italic", False), color=look.get("color") or "000000")
        ppr = ensure(s, "pPr")
        set_para_props(ppr, before=look.get("before"), after=look.get("after"), line=1.0,
                       jc={"left": "left", "center": "center", "right": "right"}.get(look.get("align") or "left"),
                       keep_next=role in ("caption", "header", "header2", "subhead"))
        ids[look["tag_style"]] = s.get(q("styleId"))
    return ids


def style_name_map(styles_root):
    out = {}
    for s in styles_root.findall("w:style", NS):
        n = s.find("w:name", NS)
        if n is not None:
            out[s.get(q("styleId"))] = n.get(q("val"))
    return out


# ---------------------------------------------------------------- file mode op (engine + unit guard)
def op_fix_tables(pkg, std, table_types=None, answers=None, skip_asked=True, only=None, roles=None):
    """Fix every top-level table of the main story (or the 1-based indexes in only). table_types: {index: key},
    default std. answers: {group: role}. roles (3.6.0): {table index: {row index: role}} set by hand, applied last.
    Returns per-table decisions and reports."""
    sp = pkg.word_part("/styles")
    pkg.touch(sp)
    sroot = pkg.tree(sp)
    pkg.touch(pkg.main)
    root = pkg.tree(pkg.main)
    names = style_name_map(sroot)
    out = {"tables": []}
    ids_by_type = {}
    idx = 0
    for tbl in list(root.iter(q("tbl"))):
        if any(True for _ in tbl.iterancestors(q("tbl"))):
            continue
        idx += 1
        if only and idx not in only:
            continue
        tkey = (table_types or {}).get(idx) or ("fig" if is_figure_table(tbl) else "std")
        if tkey not in ids_by_type:
            ids_by_type[tkey] = ensure_tag_styles(sroot, std, tkey)
            names = style_name_map(sroot)
        decs = classify(tbl, std, tkey, names)
        for g, role in (answers or {}).items():
            answer(decs, g, role)
        for ri, role in ((roles or {}).get(idx) or {}).items():
            set_role(decs, {int(ri)}, role)
        rep = apply(tbl, decs, std, tkey, ids_by_type[tkey], skip_asked=skip_asked, mark=pkg.mark)
        for el in [tbl] + list(tbl.iter()):
            if el.tag in (WP, q("tblPr"), q("tblGrid"), q("trPr"), q("tcPr"), q("tblPrEx")):
                pkg.mark(el)
        out["tables"].append({"index": idx, "type": tkey, "decisions": decs, "report": rep,
                              "questions": questions(decs)})
    for s in sroot.findall("w:style", NS):
        pkg.mark(s)
    out["checks"] = []
    return out


def op_merge_rows(pkg, targets):
    """Merge rows into one cell where every cell but the first is empty. targets: {table index (1-based): [row
    indexes]}. Its own step because it removes (empty) cells and their empty paragraphs; the words of the document
    are proven identical before and after."""
    pkg.touch(pkg.main)
    root = pkg.tree(pkg.main)
    words_before = " ".join(visible_text(root).replace("\u00b6", " ").split())
    idx, merged = 0, 0
    for tbl in list(root.iter(q("tbl"))):
        if any(True for _ in tbl.iterancestors(q("tbl"))):
            continue
        idx += 1
        if idx not in targets:
            continue
        trs = rows(tbl)
        for r in targets[idx]:
            tr = trs[r]
            for el in tr.iter():
                pkg.mark(el)
            if _merge_if_empty(tr, grid_cols(tbl), pkg.mark):
                merged += 1
    words_after = " ".join(visible_text(root).replace("\u00b6", " ").split())
    if words_before != words_after:
        raise ValueError("merging would change the words of the document")
    return {"merged": merged, "checks": []}


MERGE_ALLOWED = ("paragraphs", "text", "text_len", "tables", "para_format", "table_format")
