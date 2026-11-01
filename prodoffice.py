"""Excel and PowerPoint against the profile (3.11.0): read only. Each file is read once into memory and never written;
findings use the same Check as Word drafts, in two areas of their own (sheets, slides). There is no fix for these
files in this release: what Check finds is fixed in Excel or PowerPoint by hand.

The profile's values (std["excel"], std["powerpoint"]); blank or None means not checked:
  excel:       font, size (the table font and size by default), header {bold, fill, color}, freeze_header,
               print {orientation, fit_width, repeat_header, footer_page, marking}
  powerpoint:  fonts (allowed, comma list; blank: the profile's body and table fonts), min_size, title_min_size,
               slide_size ("16:9", "4:3" or ""), marking (the restriction marking on every slide), titles (every
               slide has a title)
Rules:
  X1 font or size off the profile   X2 header row look            X3 header row not frozen
  X4 print setup (orientation, fit to one page wide, header row repeated, page number, marking)
  X5 one column holds numbers in more than one format                X6 hidden sheets, rows or columns
  X7 a formula shows an error (#REF!, #DIV/0!...)
  D1 slide size                     D2 font not allowed           D3 text smaller than the profile allows
  D4 something off the slide        D5 marking missing            D6 placeholder left empty      D7 slide without a title
"""
import io, re
from collections import Counter, defaultdict

EXCEL_EXT = (".xlsx", ".xlsm")
PPT_EXT = (".pptx", ".pptm")
ERRORS = ("#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!")
RULES = {"X1": "Font or size off the profile", "X2": "Header row look", "X3": "Header row not frozen", "X4": "Print setup",
         "X5": "Numbers in more than one format in a column", "X6": "Hidden sheets, rows or columns", "X7": "Formula error",
         "D1": "Slide size", "D2": "Font not allowed", "D3": "Text too small", "D4": "Off the slide", "D5": "Marking missing",
         "D6": "Placeholder left empty", "D7": "Slide without a title"}


def defaults(std):
    v = std.get("variables") or {}
    ex = {"font": "", "size": None, "header": {"bold": True, "fill": "", "color": ""}, "freeze_header": True,
          "print": {"orientation": "", "fit_width": True, "repeat_header": True, "footer_page": True, "marking": False}}
    ex.update({k: val for k, val in (std.get("excel") or {}).items() if k not in ("header", "print")})
    ex["header"].update((std.get("excel") or {}).get("header") or {})
    ex["print"].update((std.get("excel") or {}).get("print") or {})
    if not ex["font"]:
        ex["font"] = v.get("table_font") or ""
    if not ex["size"]:
        ex["size"] = v.get("table_size")
    pp = {"fonts": "", "min_size": 12, "title_min_size": None, "slide_size": "", "marking": False, "titles": True}
    pp.update(std.get("powerpoint") or {})
    if not pp["fonts"]:
        pp["fonts"] = ", ".join(x for x in {v.get("body_font") or "", v.get("table_font") or ""} if x)
    return ex, pp


def _hex(c):
    try:
        if c is None or c.type != "rgb" or not c.rgb or not isinstance(c.rgb, str):
            return ""
        return c.rgb[-6:].upper()
    except Exception:  # noqa: BLE001
        return ""


def _refs(cells, n=4):
    return ", ".join(cells[:n]) + (f" and {len(cells) - n} more" if len(cells) > n else "")


# ------------------------------------------------------------------ Excel
def check_excel(raw, std, add):
    """add(area, rule, severity, what, where) for each finding."""
    from openpyxl import load_workbook
    ex, _pp = defaults(std)
    wb = load_workbook(io.BytesIO(raw), data_only=False)
    try:
        wbv = load_workbook(io.BytesIO(raw), data_only=True)
    except Exception:  # noqa: BLE001
        wbv = None
    marking = ((std.get("variables") or {}).get("marking") or "")[:40]
    stats = {"sheets": 0, "cells": 0}
    for ws in wb.worksheets:
        stats["sheets"] += 1
        tag = f"Sheet {ws.title}"
        if ws.sheet_state != "visible":
            add("sheets", "X6", "info", f"{tag} is hidden", tag)
            continue
        hidden_r = [str(i) for i, d in ws.row_dimensions.items() if d.hidden]
        hidden_c = [k for k, d in ws.column_dimensions.items() if d.hidden]
        if hidden_r or hidden_c:
            add("sheets", "X6", "info", f"{tag}: hidden " + ", ".join(x for x in (f"rows {_refs(hidden_r)}" if hidden_r else "",
                                                                                  f"columns {_refs(hidden_c)}" if hidden_c else "") if x), tag)
        header = None
        bad_font, bad_size = [], []
        col_formats = defaultdict(Counter)
        for row in ws.iter_rows():
            for c in row:
                if c.value is None or (isinstance(c.value, str) and not c.value.strip()):
                    continue
                stats["cells"] += 1
                if header is None:
                    header = c.row
                f = c.font
                if ex["font"] and f is not None and f.name and f.name.lower() != str(ex["font"]).lower():
                    bad_font.append(c.coordinate)
                if ex["size"] and f is not None and f.sz and abs(float(f.sz) - float(ex["size"])) > 0.01 and c.row != header:
                    bad_size.append(c.coordinate)
                if isinstance(c.value, (int, float)) and not isinstance(c.value, bool) and c.row != header:
                    col_formats[c.column_letter][c.number_format] += 1
        if bad_font:
            add("sheets", "X1", "warning", f"{tag}: {len(bad_font)} cell(s) not in {ex['font']} ({_refs(bad_font)})", tag)
        if bad_size:
            add("sheets", "X1", "warning", f"{tag}: {len(bad_size)} cell(s) not {float(ex['size']):g} pt ({_refs(bad_size)})", tag)
        if header is not None:
            h = ex["header"]
            cells = [c for c in ws[header] if c.value not in (None, "")]
            off = []
            if h.get("bold") is not None and any(bool(c.font.b) != bool(h["bold"]) for c in cells):
                off.append("bold" if h["bold"] else "not bold")
            if h.get("fill") and any(_hex(c.fill.fgColor) != str(h["fill"]).upper() for c in cells if c.fill is not None):
                off.append(f"fill {h['fill']}")
            if h.get("color") and any(_hex(c.font.color) != str(h["color"]).upper() for c in cells):
                off.append(f"text color {h['color']}")
            if off:
                add("sheets", "X2", "warning", f"{tag}: the header row (row {header}) is not " + ", ".join(off), tag)
            if ex.get("freeze_header"):
                fp = ws.freeze_panes
                frozen_row = int(re.sub(r"[A-Z]+", "", fp)) - 1 if fp else 0
                if frozen_row < header:
                    add("sheets", "X3", "warning", f"{tag}: the header row (row {header}) does not stay on screen (freeze panes)", tag)
        pr = ex["print"]
        probs = []
        if pr.get("orientation") and (ws.page_setup.orientation or "portrait") != pr["orientation"]:
            probs.append(f"{pr['orientation']} pages")
        if pr.get("fit_width") and not (ws.sheet_properties.pageSetUpPr is not None and ws.sheet_properties.pageSetUpPr.fitToPage
                                        and (ws.page_setup.fitToWidth or 1) == 1):
            probs.append("fit to one page wide")
        if pr.get("repeat_header") and header is not None and not ws.print_title_rows:
            probs.append("the header row repeated on every page")
        foot = " ".join(x.text or "" for x in (ws.oddFooter.left, ws.oddFooter.center, ws.oddFooter.right))
        head = " ".join(x.text or "" for x in (ws.oddHeader.left, ws.oddHeader.center, ws.oddHeader.right))
        if pr.get("footer_page") and "&P" not in foot and "&P" not in head:
            probs.append("a page number in the footer")
        if pr.get("marking") and marking and marking not in foot and marking not in head:
            probs.append("the restriction marking")
        if probs and stats["cells"]:
            add("sheets", "X4", "warning", f"{tag}: print setup lacks " + ", ".join(probs), tag)
        for col, fmts in col_formats.items():
            if len(fmts) > 1 and sum(fmts.values()) >= 3:
                add("sheets", "X5", "info", f"{tag}: column {col} holds numbers in {len(fmts)} formats ("
                    + ", ".join(f"{k} x{v}" for k, v in fmts.most_common(3)) + ")", tag)
        if wbv is not None:
            errs = [c.coordinate for row in wbv[ws.title].iter_rows() for c in row if isinstance(c.value, str) and c.value in ERRORS]
            if errs:
                add("sheets", "X7", "error", f"{tag}: {len(errs)} formula(s) show an error ({_refs(errs)})", tag)
    return stats


# ------------------------------------------------------------------ PowerPoint
SIZES = {"16:9": (12192000, 6858000), "4:3": (9144000, 6858000)}


def _theme_fonts(prs):
    from lxml import etree
    out = {}
    try:
        master = prs.slide_masters[0]
        for rel in master.part.rels.values():
            if rel.reltype.endswith("/theme"):
                root = etree.fromstring(rel.target_part.blob)
                a = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
                for kind in ("major", "minor"):
                    el = root.find(f".//{a}{kind}Font/{a}latin")
                    if el is not None:
                        out[kind] = el.get("typeface")
    except Exception:  # noqa: BLE001
        pass
    return out


def check_powerpoint(raw, std, add):
    from pptx import Presentation
    from pptx.util import Emu
    _ex, pp = defaults(std)
    prs = Presentation(io.BytesIO(raw))
    W_, H_ = prs.slide_width, prs.slide_height
    stats = {"slides": len(prs.slides)}
    if pp.get("slide_size") in SIZES:
        want = SIZES[pp["slide_size"]]
        if abs(W_ / H_ - want[0] / want[1]) > 0.01:
            add("slides", "D1", "warning", f"Slides are {W_ / 914400:.2f} x {H_ / 914400:.2f} in; the profile uses {pp['slide_size']}", "Deck")
    allowed = {x.strip().lower() for x in str(pp.get("fonts") or "").split(",") if x.strip()}
    theme = _theme_fonts(prs)
    for k, t in theme.items():
        if allowed and t and t.lower() not in allowed:
            add("slides", "D2", "warning", f"The theme's {('heading' if k == 'major' else 'body')} font is {t}; the profile allows "
                f"{pp['fonts']}", "Theme")
    marking = ((std.get("variables") or {}).get("marking") or "")[:40]
    for n, slide in enumerate(prs.slides, 1):
        tag = f"Slide {n}"
        fonts, small, texts = Counter(), [], []
        title = None
        for shp in slide.shapes:
            try:
                if shp.left is not None and shp.width is not None and (shp.left < -Emu(10000) or shp.top < -Emu(10000)
                                                                       or shp.left + shp.width > W_ + 10000 or shp.top + shp.height > H_ + 10000):
                    add("slides", "D4", "warning", f"{tag}: {shp.name} reaches past the slide edge", tag)
            except Exception:  # noqa: BLE001
                pass
            if shp.is_placeholder:
                try:
                    pt = shp.placeholder_format.type
                    if "TITLE" in str(pt):
                        title = shp
                except Exception:  # noqa: BLE001
                    pass
                if shp.has_text_frame and not shp.text_frame.text.strip() and "PICTURE" not in str(getattr(shp.placeholder_format, "type", "")):
                    add("slides", "D6", "info", f"{tag}: the placeholder {shp.name} is empty (its prompt text shows in the editor)", tag)
            if not shp.has_text_frame:
                continue
            texts.append(shp.text_frame.text)
            for p in shp.text_frame.paragraphs:
                for r in p.runs:
                    if not r.text.strip():
                        continue
                    if r.font.name:
                        fonts[r.font.name] += 1
                    if r.font.size is not None:
                        limit = pp.get("title_min_size") if (shp is title and pp.get("title_min_size")) else pp.get("min_size")
                        if limit and r.font.size.pt < float(limit) - 0.01:
                            small.append(f"{r.font.size.pt:g} pt")
        bad = [f for f in fonts if allowed and f.lower() not in allowed]
        if bad:
            add("slides", "D2", "warning", f"{tag}: text in {', '.join(bad)} (the profile allows {pp['fonts']})", tag)
        if small:
            add("slides", "D3", "warning", f"{tag}: {len(small)} run(s) smaller than the profile allows ({', '.join(sorted(set(small)))})", tag)
        if pp.get("titles") and (title is None or not title.text_frame.text.strip()):
            add("slides", "D7", "info", f"{tag} has no title (screen readers and the slide list use it)", tag)
        if pp.get("marking") and marking and not any(marking in t for t in texts):
            add("slides", "D5", "warning", f"{tag}: the restriction marking is not on the slide", tag)
    return stats
