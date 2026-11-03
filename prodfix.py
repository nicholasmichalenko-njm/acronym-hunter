"""Fix a Copy (3.6.0): check an Office file against the production standard, let the person choose every fix, then
make a dated copy and run the chosen fixes on the copy only, one guarded write each, and check the copy again.

check(path, std)        -> Check     read only: findings by area and rule, tables with row roles and questions,
                                     list restarts to answer, styles report, what each fix would change
default_plan(check)     -> plan      every fix that has work, switched on; nothing that needs a decision
run(path, folder, std, plan, ...) -> Job   copy, mark, fixes in a fixed order, optional Word field update, re-check

Each fix is one engine operation that declares exactly what it may change; the engine refuses anything else, and a
refused fix leaves the copy as it was before that fix. The original file is never opened for writing (prodcopy).
"""
import copy, datetime, os, time
from collections import Counter, OrderedDict

import prodcopy as PCY
import prodrules as PRL
from prodengine.engine.pkg import Package, Refused
from prodengine.engine.ops import word_ops as WO
from prodengine.engine.ops import merge as MG
from prodengine.engine.ordered import q
from prodengine.pe import docmap as D, fixes as X, fixes2 as X2, fonts as Fo, hf as H, lists as L, sections as S
from prodengine.pe import tables as T, terms as TM, listnum as LN, tablestyles as TS

AREAS = OrderedDict([
    ("styles", "Styles"), ("fonts", "Fonts"), ("tables", "Tables"), ("captions", "Captions and numbering"),
    ("toc", "Table of contents and lists of tables and figures"), ("xrefs", "Cross-references and bookmarks"),
    ("pages", "Pages, sections, headers and footers"), ("lists", "Bulleted and numbered lists"), ("terms", "Terms"),
    ("sheets", "Excel sheets"), ("slides", "PowerPoint slides"),                     # 3.11.0: check only
    ("graphics", "Graphics"),                                                        # 3.17.0: check only
])
AREA_OF = {"bookmarks": "xrefs", "headings": "captions"}
OFFICE_AREAS = ("sheets", "slides")

RULE_TEXT = {
    "C1": "Caption number typed, not a field", "C2": "Caption in the wrong numbering list", "C3": "Caption chapter part wrong",
    "C4": "Caption number reads differently after an update", "C5": "Caption separator differs from the rule",
    "C6": "What follows the caption number differs from the rule", "C7": "Caption above or below the wrong way",
    "T1": "No table of contents", "T2": "TOC switches the rule never uses", "T3": "TOC levels differ from the rule",
    "T4": "TOC missing a switch", "T5": "List scoped by a bookmark", "T6": "List collects captions nobody uses",
    "T7": "TOC lines typed by hand", "B1": "Response bookmark in the wrong place", "B2": "Appendix bookmark in the wrong place",
    "B3": "Hidden cross-reference target not used", "X1": "Cross-reference to a target that is gone",
    "X2": "Cross-reference shows an error", "X3": "Cross-reference shows old text", "X4": "Cross-reference keeps MERGEFORMAT",
    "H1": "Body headings after the first appendix",
    "P1": "Page number format", "P2": "Page number restart", "P3": "Chapter heading inside a section", "P4": "Header names another volume",
    "P5": "PAGE field with a format switch", "P6": "No page number field", "P7": "Page number where the scheme has none",
    "P8": "Placed landscape page with its own header or footer", "P9": "Margins or page size off the page setup",
    "P10": "Restriction marking missing", "P11": "Header value not set (volume name, solicitation)",
    "L1": "Typed bullets", "L2": "Typed numbers or letters", "L3": "Numbering pasted from another document",
    "L4": "Hand indents on list paragraphs", "L5": "List continues the numbering before it", "L5?": "List restart to decide",
    "L6": "Typed number inside a numbered heading", "L9": "List numbering differs from the volume standard",
    "R5": "Word table style differs from the volume standard", "P12": "Cover built differently from the volume standard's",
    "P13": "Back cover built differently from the volume standard's", "R6": "Table does not use its type's Word table style", "L7": "Typed list in a table cell", "L8": "Unused list definitions",
    "W1": "Banned word or phrase", "W2": "Known misspelling", "W3": "Trademark or registered mark missing", "W4": "Name one letter off",
    "F1": "Font or size typed over the style", "F2": "Font or size typed over the style", "F1s": "Style breaks the font rule",
    "F2s": "Style breaks the size rule",
    "S1": "Style not on the allowed list", "S2": "Custom style not used", "S3": "Built-in style shown but not used",
    "S4": "Style differs from the standard", "S7": "Style the standard defines is not in the file", "S5": "Heading numbering differs from the standard",
    "S6": "Style takes heading numbers it should not",
    "R0": "Table rows to format by role", "R1": "Table rows waiting for your answer",
}


def _fix(key, area, label, op, allowed, args, rules=(), kind="all", help=""):
    return {"key": key, "area": area, "label": label, "op": op, "allowed": tuple(allowed), "args": args,
            "rules": set(rules), "kind": kind, "help": help}


def _heading_levels(std):
    return [(l["style"], l["fmt"], l["text"], float(l["number_at"]), float(l["text_at"]), l.get("restart"))
            for l in std["heading_numbering"]["levels"]]


PROP_TEXT = {"font": "font", "size": "size", "bold": "bold", "italic": "italic", "underline": "underline", "caps": "all caps",
             "small_caps": "small caps", "color": "color", "jc": "alignment", "before": "space before", "after": "space after",
             "line": "line spacing", "line_rule": "line spacing rule", "left": "left indent", "right": "right indent",
             "first": "first line indent", "hanging": "hanging indent", "keep_next": "keep with next",
             "keep_lines": "keep lines together", "page_break_before": "page break before", "widow": "widow control",
             "based_on": "based on", "next": "next style", "hidden": "hidden text"}


def _show(v):
    if v is True:
        return "on"
    if v is False:
        return "off"
    if v is None:
        return "not set"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


# The fixes, in the order they run. The order matters: styles before the things that use them, tables before
# captions (a caption row's style), sections before headers and footers, fields last.
import prodoffice as _PO
RULE_TEXT.update(_PO.RULES)                                                       # 3.11.0: Excel and PowerPoint
import prodgraphics as _PG                                                           # noqa: E402
RULE_TEXT.update(_PG.RULES)                                                       # 3.17.0: graphics, check only


FIXES = [
    _fix("styles_merge", "styles", "Bring in the styles of the standard's template", MG.op_merge_styles, (),
         lambda std, plan: {"template_path": std["styles"]["template"]}, help="Every style in the template replaces the "
         "document's style of the same name (Word's Organizer); the document keeps its own text and style names."),
    _fix("styles_apply", "styles", "Set every style the standard defines (fonts, sizes, spacing, indents, keeps, based on)",
         WO.op_styles, WO.OP_STYLES_ALLOWED,
         lambda std, plan: {"spec": {k: v for k, v in PRL.style_spec(std).items() if k not in set(plan.get("style_skip") or ())}},
         rules=("S4", "S7")),
    _fix("unnumber_inheriting", "styles", "Stop styles based on a heading from taking heading numbers (for example TOC Heading)",
         WO.op_unnumber_inheriting, WO.OP_STYLES_ALLOWED, lambda std, plan: {"names": plan.get("unnumber") or None}, rules=("S6",),
         help="A style based on Heading 1 with no numbering of its own takes Heading 1's number: the Table of Contents title "
         "then reads as chapter 1 and every chapter and caption number after it is off by one."),
    _fix("heading_numbering", "styles", "Set heading numbering from the standard", WO.op_heading_numbering, (),
         lambda std, plan: {"levels": _heading_levels(std)}, rules=("S5",)),
    _fix("font_styles", "fonts", "Fix the styles that break the font rules", Fo.op_font_styles, Fo.FONTS_ALLOWED,
         lambda std, plan: {"std": std}, rules=("F1s", "F2s")),
    _fix("fonts", "fonts", "Remove fonts and sizes typed over the styles", Fo.op_fonts, Fo.FONTS_ALLOWED,
         lambda std, plan: {"std": std}, rules=("F1", "F2")),
    _fix("table_styles", "tables", "Set the Word table styles from the volume standard", TS.op_table_styles, TS.TABLE_STYLES_ALLOWED,
         lambda std, plan: {"std": std}, rules=("R5",)),
    _fix("tables", "tables", "Format tables by row role", T.op_fix_tables,
         ("pstyles", "para_format", "table_format", "direct_run_format", "tables"),
         lambda std, plan: {"std": std, "table_types": plan.get("table_types") or None, "answers": plan.get("table_answers") or None,
                            "roles": plan.get("table_roles") or None, "only": plan.get("table_only") or None, "skip_asked": True},
         rules=("R0", "R6"), kind="tables"),
    _fix("list_numbering", "lists", "Set list numbering from the volume standard (bullets and numbers by level)", LN.op_list_numbering,
         LN.LIST_ALLOWED, lambda std, plan: {"std": std}, rules=("L9",)),
    _fix("lists", "lists", "Turn typed bullets and numbers into the team's list styles", L.op_lists, L.LISTS_ALLOWED,
         lambda std, plan: {"std": std, "answers": plan.get("list_answers") or None}, rules=("L1", "L2", "L3", "L4", "L5", "L6")),
    _fix("caption_typed", "captions", "Turn typed caption numbers into fields", X2.op_caption_typed, X2.CAPTION_TYPED_ALLOWED,
         lambda std, plan: {"std": std}, rules=("C1",)),
    _fix("caption_fields", "captions", "Correct caption fields (list, chapter part, separator)", X.op_caption_fields,
         X.CAPTION_ALLOWED, lambda std, plan: {"std": std}, rules=("C2", "C3", "C5")),
    _fix("caption_after", "captions", "Put a tab after the caption number", X.op_caption_after, X.AFTER_ALLOWED,
         lambda std, plan: {"std": std}, rules=("C6",)),
    _fix("toc_field", "toc", "Set the TOC field from the standard", X.op_toc_field, X.TOC_ALLOWED, lambda std, plan: {"std": std},
         rules=("T2", "T3", "T4")),
    _fix("toc_styles", "toc", "Set the TOC entry styles (number and text positions, tab leader)", X.op_toc_styles,
         X.STYLES_ALLOWED, lambda std, plan: {"std": std}),
    _fix("toc_list_identifiers", "toc", "Collect lists of tables and figures by caption list, not bookmark",
         X2.op_toc_list_identifiers, X2.LIST_ALLOWED, lambda std, plan: {"std": std}, rules=("T5", "T6")),
    _fix("xref_switches", "xrefs", "Cross-references keep their formatting (CHARFORMAT)", X.op_xref_switches, X.XREF_ALLOWED,
         lambda std, plan: {"std": std}, rules=("X4",)),
    _fix("xref_relink", "xrefs", "Point broken cross-references at the targets you chose", X2.op_xref_relink, X2.RELINK_ALLOWED,
         lambda std, plan: {"std": std, "mapping": plan.get("xref_mapping") or {}}, rules=("X1",), kind="choose"),
    _fix("scope_reset", "xrefs", "Reset the Response and Appendices bookmarks", X.op_scope_reset, X.SCOPE_ALLOWED,
         lambda std, plan: {"std": std}, rules=("B1", "B2")),
    _fix("chapter_breaks", "pages", "Start each chapter in its own section", S.op_chapter_breaks, S.CHAPTER_ALLOWED,
         lambda std, plan: {"std": std}, rules=("P3",)),
    _fix("page_numbers", "pages", "Set page number format and restarts from the page scheme", S.op_page_numbers,
         S.NUMBERS_ALLOWED, lambda std, plan: {"std": std}, rules=("P1", "P2")),
    _fix("page_setup", "pages", "Set paper, orientation and margins from the page setups", S.op_page_setup, S.SETUP_ALLOWED,
         lambda std, plan: {"std": std}, rules=("P9",)),
    _fix("page_field_clean", "pages", "Remove format switches from PAGE fields", S.op_page_field_clean, S.PAGE_FIELD_ALLOWED,
         lambda std, plan: {}, rules=("P5",)),
    _fix("hf_build", "pages", "Build headers and footers from the layouts (cover, front matter, body, appendices, back cover)",
         H.op_hf_build, H.HF_ALLOWED, lambda std, plan: {"std": std}, rules=("P4", "P6", "P7", "P8", "P10")),
    _fix("terms", "terms", "Fix misspellings and add trademark and registered marks", TM.op_terms, TM.TERMS_ALLOWED,
         lambda std, plan: {"std": std, "accept": tuple(plan.get("term_rules") or ("W2", "W3")),
                            "hit_ids": plan.get("term_hits") or None}, rules=("W2", "W3")),
    _fix("styles_remove_unused", "styles", "Remove custom styles nobody uses", WO.op_remove_unused_styles, WO.OP_STYLES_ALLOWED,
         lambda std, plan: {"names": plan.get("styles_unused") or []}, rules=("S2",)),
    _fix("styles_hide", "styles", "Hide built-in styles nobody uses from the style gallery", WO.op_hide_styles, WO.OP_STYLES_ALLOWED,
         lambda std, plan: {"names": plan.get("styles_hide") or []}, rules=("S3",)),
]
FIX = {f["key"]: f for f in FIXES}
WORD_STEP = {"key": "word_update", "area": "", "label": "Update fields in Word: page numbers, caption numbers, the TOC and "
             "the lists of tables and figures (Word on this PC, hidden; the copy only)"}


# ------------------------------------------------------------------ the check
class Check:
    def __init__(self, path):
        self.path = path
        self.findings = []        # dicts: area, rule, severity, what, where, near, fix
        self.tables = []          # {"index", "type", "caption", "rows": [...], "questions": {...}, "counts"}
        self.list_blocks = []     # [{"id", "why", "first"}] lists waiting for restart or continue
        self.broken_refs = []     # [{"target", "para", "near"}]
        self.bookmarks = []       # targets a broken reference can point to
        self.styles = {}          # {"in_use": [...], "unused_custom": [...], "hide": [...], "not_allowed": [...]}
        self.would = {}           # fix key -> count of changes the fix would make (dry run)
        self.hf_sources = []      # cover paragraph styles the headers can read through STYLEREF (PE Volume Name...)
        self.missing = []         # volume tokens the layouts use that have no value and no cover paragraph
        self.style_diffs = {}     # 3.7.0: style -> {prop: {"have", "want"}} or {"missing": True}
        self.office = ""          # 3.11.0: "excel" or "powerpoint" for a workbook or a deck (check only)
        self.stats = {}
        self.error = ""
        self.seconds = 0.0

    def by_area(self):
        out = OrderedDict((a, Counter()) for a in AREAS)
        for f in self.findings:
            out.setdefault(f["area"], Counter())[f["rule"]] += 1
        return out

    def count(self, area=None):
        return sum(1 for f in self.findings if area is None or f["area"] == area)


def _near(dm, para):
    """The heading a paragraph sits under, for 'where'."""
    if dm is None or para is None or para < 0:
        return ""
    head = ""
    for h in dm.headings:
        if h.i <= para:
            head = h.text
        else:
            break
    return head[:80]


def _add(chk, area, rule, sev, what, where, fix, near=""):
    chk.findings.append({"area": AREA_OF.get(area, area), "rule": rule, "severity": sev, "what": what, "where": where,
                         "near": near, "fix": fix})


def _fix_for(rule, fix_name):
    for f in FIXES:
        if rule in f["rules"]:
            return f["key"]
    if fix_name in ("update_fields",):
        return "word_update"
    return ""


def _dry(raw, fx, std, plan):
    """How much a fix would change, run on a copy in memory (nothing is written anywhere)."""
    try:
        pkg = Package.from_bytes(raw)
        rep = fx["op"](pkg, **fx["args"](std, plan)) or {}
    except Exception:
        return 0
    from prodengine.engine.safewrite import same_xml
    from prodengine.engine.pkg import parse_xml
    for n in list(pkg.dirty):         # a part that serializes to what it was read from is not a change (as the engine)
        if n in pkg.raw_at_load and n in pkg.trees and same_xml(pkg.trees[n], parse_xml(pkg.raw_at_load[n], n)):
            pkg.dirty.discard(n)
    if not pkg.dirty:
        return 0
    for k in ("rewritten", "changed", "fixed", "removed", "hidden", "created", "made", "styles"):
        v = rep.get(k)
        if isinstance(v, (list, tuple, set, dict)) and v:
            return len(v)
        if isinstance(v, int) and v:
            return v
    return 1


def styles_report(pkg, std):
    root = WO.styles_root(pkg)
    used_ids = WO.styles_in_use(pkg)
    out = {"in_use": [], "unused_custom": [], "hide": [], "not_allowed": []}
    allowed = {WO.norm(a) for a in (std.get("styles") or {}).get("allowed") or []}
    tag_styles = {WO.norm(rt["tag_style"]) for rt in std["row_types"].values()}
    for s in root.findall("w:style", WO.NS):
        n = s.find("w:name", WO.NS)
        if n is None:
            continue
        name = n.get(q("val"))
        sid = s.get(q("styleId"))
        custom = s.get(q("customStyle")) in ("1", "true")
        in_use = sid in used_ids or s.get(q("default")) in ("1", "true")
        if in_use:
            out["in_use"].append(name)
            if allowed and WO.norm(name) not in allowed and WO.norm(name) not in tag_styles:
                out["not_allowed"].append(name)
        elif custom:
            out["unused_custom"].append(name)
        elif s.find("w:qFormat", WO.NS) is not None and s.find("w:semiHidden", WO.NS) is None:
            out["hide"].append(name)
    return out


def check(path, std, data=None):
    """Read the file (once, into memory) and check it against the standard. Never writes."""
    chk = Check(path)
    t0 = time.perf_counter()
    try:
        raw = data if data is not None else open(path, "rb").read()
        ext = os.path.splitext(path)[1].lower()
        import prodoffice as PO
        if ext in PO.EXCEL_EXT + PO.PPT_EXT:          # 3.11.0: Excel and PowerPoint, read only
            return _check_office(chk, raw, ext, std, t0)
        pkg = Package.from_bytes(raw, os.path.basename(path))
        if not pkg.is_word:
            raise Refused("Fix a Copy reads Word, Excel and PowerPoint files.")
    except Refused as e:
        chk.error = str(e)
        return chk
    except OSError as e:
        chk.error = f"The file could not be read ({type(e).__name__})."
        return chk
    std = PRL.engine_ready(copy.deepcopy(std))
    dm = None
    try:
        dm = D.build(pkg, std)
        chk.stats = dict(dm.stats)
        for f in D.audit(dm, std):
            _add(chk, f.area, f.rule, f.severity, f.what, f.where, _fix_for(f.rule, f.fix), _near(dm, f.where))
        chk.bookmarks = sorted(b for b, bm in dm.bookmarks.items() if not b.startswith("_GoBack"))
        for x in dm.xrefs:
            if x.status == "broken":
                chk.broken_refs.append({"target": x.target, "para": x.para, "near": _near(dm, x.para), "kind": x.kind})
    except Exception as e:  # noqa: BLE001  one area failing must not hide the others
        chk.error += f" Captions and references could not be read ({type(e).__name__})."
    try:
        chk.hf_sources = sorted(H._sources(pkg, std))
    except Exception:  # noqa: BLE001
        chk.hf_sources = []
    chk.missing = PRL.missing_values(std, chk.hf_sources)
    if chk.missing:
        _add(chk, "pages", "P11", "warning", "Headers and footers are not built until these are set: "
             + ", ".join(PRL.HF_TOKENS[k] for k in chk.missing) + " (the volume name on this page; the solicitation in the "
             "effort's basics)", -1, "")
    try:
        sm = S.map_sections(pkg, std)
        chk.stats["sections"] = len(sm.sections)
        chk.sections = [{"i": s.i, "part": s.part, "first": s.first_style, "orient": s.orient, "shows": s.shows} for s in sm.sections]
        for f in S.audit(sm, std):
            _add(chk, f.area, f.rule, f.severity, f.what, f.where, _fix_for(f.rule, f.fix), f"Section {f.where + 1}" if isinstance(f.where, int) else "")
    except Exception as e:  # noqa: BLE001
        chk.error += f" Pages and sections could not be read ({type(e).__name__})."
    try:
        lm = L.scan(pkg, std)
        for f in L.audit(lm, std):
            _add(chk, f.area, f.rule, f.severity, f.what, f.where, _fix_for(f.rule, f.fix), _near(dm, f.where))
        for b in lm.blocks:
            if b.restart == "ask":
                chk.list_blocks.append({"id": b.id, "why": b.why, "first": (b.items[0].text if b.items else "")[:70],
                                        "near": _near(dm, b.items[0].para if b.items else -1)})
    except Exception as e:  # noqa: BLE001
        chk.error += f" Lists could not be read ({type(e).__name__})."
    try:
        runs = Fo.scan(pkg, std)
        for f in Fo.audit(runs, std):
            _add(chk, f.area, f.rule, f.severity, f.what, f.where, _fix_for(f.rule, f.fix), _near(dm, f.where))
    except Exception as e:  # noqa: BLE001
        chk.error += f" Fonts could not be read ({type(e).__name__})."
    try:                                             # 3.17.0: pictures, charts, drawings and text boxes; check only
        _PG.check_word(raw, std, lambda rule, what, where: _add(chk, "graphics", rule, "warning", what, -1, "", near=where),
                       ocr=_PG.ocr_estimate if (std.get("graphics") or {}).get("ocr_text") else None)
    except Exception as e:  # noqa: BLE001
        chk.error += f" Graphics could not be read ({type(e).__name__})."
    try:
        hits = TM.scan(pkg, std)
        chk.term_hits = [{"id": h.id, "rule": h.rule, "found": h.found, "suggest": h.suggest, "context": h.context} for h in hits]
        for f in TM.audit(hits):
            _add(chk, f.area, f.rule, f.severity, f.what, f.where, _fix_for(f.rule, f.fix), _near(dm, f.where))
    except Exception as e:  # noqa: BLE001
        chk.error += f" Terms could not be read ({type(e).__name__})."
    try:
        root = pkg.tree(pkg.main)
        names = T.style_name_map(pkg.tree(pkg.word_part("/styles")))
        idx = 0
        for tbl in root.iter(q("tbl")):
            if any(True for _ in tbl.iterancestors(q("tbl"))):
                continue
            idx += 1
            ttype = "fig" if T.is_figure_table(tbl) else "std"
            decs = T.classify(tbl, std, ttype, names)
            qs = T.questions(decs)
            counts = Counter(d.status for d in decs)
            cap = next((d.first_text for d in decs if d.role == "caption"), "")
            chk.tables.append({"index": idx, "type": ttype, "caption": cap, "rows": [
                {"i": d.index, "role": d.role, "status": d.status, "why": d.why, "text": d.first_text, "group": d.group,
                 "options": list(getattr(d, "options", []) or [])} for d in decs], "questions": qs, "counts": dict(counts)})
            ws_name = (std["table_types"].get(ttype) or {}).get("word_style")
            if ws_name:                              # 3.10.0: the type's Word table style
                ts = tbl.find("w:tblPr/w:tblStyle", T.NS)
                cur_name = names.get(ts.get(q("val")), ts.get(q("val"))) if ts is not None else ""
                if WO.norm(cur_name) != WO.norm(ws_name):
                    _add(chk, "tables", "R6", "warning", f"Table {idx}: uses {'the style ' + cur_name if cur_name else 'no table style'}; "
                         f"its type uses {ws_name}", idx, "tables")
            todo = sum(1 for d in decs if d.status in ("sure", "manual"))
            if todo:
                _add(chk, "tables", "R0", "warning", f"Table {idx} {('(' + cap + ')') if cap else ''}: {todo} row(s) to format by role",
                     idx, "tables")
            if qs:
                _add(chk, "tables", "R1", "warning", f"Table {idx}: {sum(len(g['rows']) for g in qs.values())} row(s) wait for your "
                     "answer (left as they are until answered)", idx, "")
    except Exception as e:  # noqa: BLE001
        chk.error += f" Tables could not be read ({type(e).__name__})."
    try:
        chk.styles = styles_report(Package.from_bytes(raw), std)
        st = std.get("styles") or {}
        for n in chk.styles["not_allowed"]:
            _add(chk, "styles", "S1", "warning", f"{n} is used but is not on the allowed list", -1, "")
        if st.get("remove_unused_custom"):
            for n in chk.styles["unused_custom"]:
                _add(chk, "styles", "S2", "info", f"{n} is a custom style nobody uses", -1, "styles_remove_unused")
        used = set(chk.styles["in_use"])
        for _s, nm in WO.inheriting_heading_styles(WO.styles_root(Package.from_bytes(raw))):
            if nm in used:
                _add(chk, "styles", "S6", "error", f"{nm} is based on a heading and takes its number (it shows as a numbered "
                     "chapter, and the chapters and captions after it are numbered one too high)", -1, "unnumber_inheriting")
        if st.get("hide_unused_builtin"):
            for n in chk.styles["hide"]:
                _add(chk, "styles", "S3", "info", f"{n} shows in the style gallery but nobody uses it", -1, "styles_hide")
    except Exception as e:  # noqa: BLE001
        chk.error += f" Styles could not be read ({type(e).__name__})."
    # fixes with no audit of their own: count what they would change on a copy in memory
    plan0 = {"styles_unused": chk.styles.get("unused_custom", []), "styles_hide": chk.styles.get("hide", [])}
    st = std.get("styles") or {}
    try:
        spkg = Package.from_bytes(raw)
        sroot, theme = WO.styles_root(spkg), WO.theme_fonts(spkg)
        absent = []
        for name, props in PRL.style_spec(std).items():
            s_ = WO.find_style(sroot, name)
            if s_ is None:
                absent.append(name)
                chk.style_diffs[name] = {"missing": True}
                continue
            need = {k: v for k, v in WO.style_needs(sroot, s_, props, theme).items() if k in WO.STYLE_PROPS}
            if need:
                chk.style_diffs[name] = {k: {"have": WO.effective(sroot, s_, k, theme), "want": v} for k, v in need.items()}
                _add(chk, "styles", "S4", "warning", f"{name}: " + "; ".join(
                    f"{PROP_TEXT.get(k, k)} {_show(chk.style_diffs[name][k]['have'])} (standard {_show(v)})" for k, v in need.items()),
                    -1, "styles_apply")
        if absent:
            _add(chk, "styles", "S7", "info", f"{len(absent)} style(s) the standard defines are not in the file (the fix adds "
                 "them): " + ", ".join(absent), -1, "styles_apply")
    except Exception as e:  # noqa: BLE001
        chk.error += f" Style definitions could not be compared ({type(e).__name__})."
    try:                                             # 3.10.0: the profile's cover and back cover, by design (never changed)
        import prodparts as PP
        for where, rule, label in (("cover", "P12", "cover"), ("backer", "P13", "back cover")):
            fname = (std.get("page_parts") or {}).get(where)
            pdir = std.get("_parts_dir") or ""
            if not fname or not os.path.isfile(os.path.join(pdir, fname)):
                continue
            want = PP.part_signature(open(os.path.join(pdir, fname), "rb").read())
            have = PP.signature(raw, where, std)
            if have is None:
                _add(chk, "pages", rule, "warning", f"The draft has no {label}; the volume standard has one (Make a template has it)", -1, "")
            elif want is not None and have != want:
                _add(chk, "pages", rule, "info", f"The {label} is built differently from the volume standard's: paragraph styles "
                     f"{', '.join(have[0][:6]) or 'none'} (standard: {', '.join(want[0][:6]) or 'none'}); {have[1]} table(s), "
                     f"{have[2]} picture(s) (standard: {want[1]}, {want[2]}). Review it by hand.", -1, "")
    except Exception as e:  # noqa: BLE001
        chk.error += f" The cover could not be compared ({type(e).__name__})."
    try:
        for name, what in TS.differences(Package.from_bytes(raw), std):
            _add(chk, "tables", "R5", "warning", f"Table style {name}: {what}", -1, "table_styles")
    except Exception as e:  # noqa: BLE001
        chk.error += f" Table styles could not be read ({type(e).__name__})."
    try:
        for style, what in LN.differences(Package.from_bytes(raw), std):
            _add(chk, "lists", "L9", "warning", f"{style}: {what}", -1, "list_numbering")
    except Exception as e:  # noqa: BLE001
        chk.error += f" List numbering could not be read ({type(e).__name__})."
    if (std.get("heading_numbering") or {}).get("on"):
        n = _dry(raw, FIX["heading_numbering"], std, plan0)
        if n:
            chk.would["heading_numbering"] = n
            _add(chk, "styles", "S5", "warning", "Heading numbering differs from the standard", -1, "heading_numbering")
    if st.get("template") and os.path.isfile(st["template"]):
        chk.would["styles_merge"] = _dry(raw, FIX["styles_merge"], std, plan0)
    n = _dry(raw, FIX["toc_styles"], std, plan0)
    if n:
        chk.would["toc_styles"] = n
    chk.raw_sha = PCY.sha256_bytes(raw)
    chk.seconds = time.perf_counter() - t0
    return chk


def _check_office(chk, raw, ext, std, t0):
    """3.11.0: an Excel workbook or a PowerPoint deck against the volume standard (prodoffice); findings only, no fixes."""
    import prodoffice as PO
    std = PRL.engine_ready(copy.deepcopy(std))
    chk.office = "excel" if ext in PO.EXCEL_EXT else "powerpoint"

    def add(area, rule, severity, what, where):
        _add(chk, area, rule, severity, what, -1, "", near=where if isinstance(where, str) else "")
    try:
        chk.stats = (PO.check_excel if chk.office == "excel" else PO.check_powerpoint)(raw, std, add)
        if chk.office == "powerpoint":                # 3.17.0: the deck's pictures and charts
            _PG.check_powerpoint(raw, std, lambda rule, what, where: _add(chk, "graphics", rule, "warning", what, -1, "", near=where),
                                 ocr=_PG.ocr_estimate if (std.get("graphics") or {}).get("ocr_text") else None)
    except Exception as e:  # noqa: BLE001
        chk.error = f"The file could not be read ({type(e).__name__}). It may be damaged or protected with a password."
    chk.raw_sha = PCY.sha256_bytes(raw)
    chk.seconds = time.perf_counter() - t0
    return chk


def default_plan(chk):
    """Every fix that has findings (or would change something) switched on, except those that need a decision
    (relinking references). Tables: sure rows only; asked rows stay as they are."""
    on = set()
    for f in chk.findings:
        if f["fix"] and f["fix"] in FIX and FIX[f["fix"]]["kind"] != "choose":
            on.add(f["fix"])
    for k, n in chk.would.items():
        if n and k not in ("styles_merge",):
            on.add(k)
    if getattr(chk, "missing", None):
        on.discard("hf_build")            # never type a blank volume name or solicitation into headers
    return {"on": [f["key"] for f in FIXES if f["key"] in on], "word_update": any(f["fix"] == "word_update" for f in chk.findings) or
            bool(on & {"caption_typed", "caption_fields", "toc_field", "toc_list_identifiers", "page_numbers", "chapter_breaks", "hf_build",
                       "unnumber_inheriting", "heading_numbering", "list_numbering"}),
            "table_answers": {}, "table_roles": {}, "table_types": {}, "list_answers": {}, "xref_mapping": {},
            "styles_unused": list(chk.styles.get("unused_custom", [])), "styles_hide": list(chk.styles.get("hide", []))}


# ------------------------------------------------------------------ the run
def run(path, folder, std, plan, word=None, progress=None, open_list=PCY._ASK, when=None, before=None):
    """Make the copy and run the plan on it. word: callable(copy path) -> {"ok", ...} that updates fields in Word
    (prodword.update_fields), or None to skip. Returns the Job with steps, before and after checks."""
    std = PRL.engine_ready(copy.deepcopy(std))
    say = progress or (lambda *a: None)
    say("Making the copy")
    job = PCY.make_copy(path, folder, when=when, open_list=open_list)
    job.started = datetime.datetime.now()
    job.std_name = std.get("name", "")
    # the check the person just reviewed stands for the copy when the copy is the same bytes (it always is, unless the
    # file was saved in between: then the copy is checked again)
    job.before_check = before if (before is not None and getattr(before, "raw_sha", None) == job.before["sha256"]) else check(job.copy, std)
    PCY.mark_properties(job)
    for fx in FIXES:
        if fx["key"] not in (plan.get("on") or []):
            continue
        if fx["key"] == "styles_merge" and not os.path.isfile((std.get("styles") or {}).get("template") or ""):
            job.steps.append({"step": fx["label"], "key": fx["key"], "changed": False, "refused": "The standard's template file is not there."})
            continue
        if fx["key"] == "hf_build":
            gone = PRL.missing_values(std, getattr(job.before_check, "hf_sources", []))
            if gone:
                job.steps.append({"step": fx["label"], "key": fx["key"], "changed": False, "refused": "Not set: " +
                                  ", ".join(PRL.HF_TOKENS[k] for k in gone) + ". Headers and footers were left as they were."})
                continue
        say(fx["label"])
        rec = PCY.run_step(job, fx["label"], fx["op"], fx["allowed"], fx["args"](std, plan))
        rec["key"] = fx["key"]
    if plan.get("word_update") and word is not None:
        say("Updating fields in Word")
        try:
            r = word(job.copy) or {}
        except Exception as e:  # noqa: BLE001
            r = {"ok": False, "why": f"{type(e).__name__}"}
        job.steps.append({"step": WORD_STEP["label"], "key": "word_update", "changed": bool(r.get("ok")), "report": r,
                          **({} if r.get("ok") else {"refused": r.get("why", "Word could not update the fields.")})})
    say("Checking the copy")
    job.after_check = check(job.copy, std)
    job.original_ok = job.original_unchanged()
    job.finished = datetime.datetime.now()
    return job


def summary(job):
    """Counts by area before and after, for the page and the report."""
    b, a = job.before_check.by_area(), job.after_check.by_area()
    return [{"area": AREAS.get(k, k), "before": sum(b.get(k, Counter()).values()), "after": sum(a.get(k, Counter()).values())}
            for k in AREAS if k not in OFFICE_AREAS]     # 3.11.0: a copy is only ever made of a Word file


def write_report(job, effort=""):
    """The report beside the copy: what was fixed, what was refused, what is left, and the proof the original is unchanged."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    head = lambda ws: [setattr(c, "font", Font(bold=True, color="FFFFFF")) or setattr(c, "fill", PatternFill("solid", fgColor="1E3A8A")) for c in ws[1]]  # noqa: E731
    ws = wb.active
    ws.title = "Summary"
    ws.append(["Item", "Value"])
    for row in (("Original", os.path.basename(job.original)), ("Copy", os.path.basename(job.copy)),
                ("Standard", getattr(job, "std_name", "")), ("Effort", effort),
                ("Made", job.started.strftime("%Y-%m-%d %H:%M") if hasattr(job, "started") else ""),
                ("Original unchanged (SHA-256, size and date compared)", "Yes" if job.original_ok else "NO: it changed while Stationkeeper "
                 "worked. Stationkeeper never opened it for writing; someone else saved it."),
                ("Original SHA-256", job.before["sha256"]), ("Found before", job.before_check.count()), ("Left after", job.after_check.count()),
                ("Pages (Word) and the page limit", getattr(job, "page_note", "") or "No page limit on the Deliverables board, or Word did not count pages")):
        ws.append(list(row))
    head(ws)
    ws2 = wb.create_sheet("Fixes")
    ws2.append(["Fix", "Result", "Detail"])
    for s in job.steps:
        res = "Refused: copy kept as it was before this fix" if "refused" in s else ("Changed" if s.get("changed") else "Nothing to change")
        ws2.append([s["step"], res, s.get("refused", "")])
    head(ws2)
    ws3 = wb.create_sheet("By area")
    ws3.append(["Area", "Found before", "Left after"])
    for r in summary(job):
        ws3.append([r["area"], r["before"], r["after"]])
    head(ws3)
    ws4 = wb.create_sheet("Left after")
    ws4.append(["Area", "Rule", "What", "Where", "Fix"])
    for f in job.after_check.findings:
        ws4.append([AREAS.get(f["area"], f["area"]), f"{f['rule']} {RULE_TEXT.get(f['rule'], '')}", f["what"], f["near"],
                    FIX[f["fix"]]["label"] if f["fix"] in FIX else ("Update fields in Word" if f["fix"] == "word_update" else "Review by hand")])
    head(ws4)
    for w in (ws, ws2, ws3, ws4):
        for col, width in zip("ABCDE", (48, 46, 90, 40, 50)):
            w.column_dimensions[col].width = width
        for row in w.iter_rows(min_row=2):
            for c in row:
                c.alignment = Alignment(wrap_text=True, vertical="top")
    wb.properties.title = f"Stationkeeper fix report: {os.path.basename(job.original)}"
    path = job.report_path
    if os.path.exists(path):
        raise PCY.NotAllowed("A report with that name is already there.")
    PCY.check_write(job.copy)            # the report goes only beside a Stationkeeper copy in the output folder
    wb.save(path)
    return path
