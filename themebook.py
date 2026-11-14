"""4.10.0: the Theme sheet of Global Standards.xlsx (morning answer 12). Word's theme holds twelve colors (text and
background, six accents, the two hyperlink colors) and two fonts (headings and body). The standard keeps the theme as
Word's own XML (std["theme"]["xml"]); this sheet shows those fourteen values as rows and writes edits back into the XML,
so everything else in the theme stays as Word wrote it. A standard with no theme starts from BASE, the Office colors
and fonts, when someone fills the sheet in."""
import re

import templatelib as TL

SHEET = "Theme"
COLS = ("Name", "Value", "Notes")
FONTS = (("major", "Headings font"), ("minor", "Body font"))
NOTE_COLOR = "A color as six hex digits, such as 1F3864 (# is fine)"
NOTE_FONT = "A font name, such as Calibri"
HEX = re.compile(r"^#?([0-9A-Fa-f]{6})$")

BASE = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Office Theme"><a:themeElements>'
        '<a:clrScheme name="Office"><a:dk1><a:sysClr val="windowText" lastClr="000000"/></a:dk1>'
        '<a:lt1><a:sysClr val="window" lastClr="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="44546A"/></a:dk2>'
        '<a:lt2><a:srgbClr val="E7E6E6"/></a:lt2><a:accent1><a:srgbClr val="4472C4"/></a:accent1>'
        '<a:accent2><a:srgbClr val="ED7D31"/></a:accent2><a:accent3><a:srgbClr val="A5A5A5"/></a:accent3>'
        '<a:accent4><a:srgbClr val="FFC000"/></a:accent4><a:accent5><a:srgbClr val="5B9BD5"/></a:accent5>'
        '<a:accent6><a:srgbClr val="70AD47"/></a:accent6><a:hlink><a:srgbClr val="0563C1"/></a:hlink>'
        '<a:folHlink><a:srgbClr val="954F72"/></a:folHlink></a:clrScheme>'
        '<a:fontScheme name="Office"><a:majorFont><a:latin typeface="Calibri Light"/><a:ea typeface=""/><a:cs typeface=""/>'
        '</a:majorFont><a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>'
        '</a:fontScheme><a:fmtScheme name="Office"><a:fillStyleLst>'
        + '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>' * 3 +
        '</a:fillStyleLst><a:lnStyleLst>'
        + '<a:ln w="6350" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
          '<a:prstDash val="solid"/><a:miter lim="800000"/></a:ln>' * 3 +
        '</a:lnStyleLst><a:effectStyleLst>' + '<a:effectStyle><a:effectLst/></a:effectStyle>' * 3 +
        '</a:effectStyleLst><a:bgFillStyleLst>' + '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>' * 3 +
        '</a:bgFillStyleLst></a:fmtScheme></a:themeElements><a:objectDefaults/><a:extraClrSchemeLst/></a:theme>')


def rows(std):
    """The sheet's rows from the standard: the twelve colors, then the two fonts. Values are blank when the standard
    has no theme (the base is not written into a workbook until someone fills it in)."""
    t = TL.read_theme((std.get("theme") or {}).get("xml") or "") or {"colors": {}, "major": "", "minor": ""}
    out = [{"Name": TL.THEME_NAMES[s], "Value": t["colors"].get(s, ""), "Notes": NOTE_COLOR} for s in TL.THEME_SLOTS]
    out += [{"Name": lab, "Value": t.get(k, ""), "Notes": NOTE_FONT} for k, lab in FONTS]
    return out


def _set_color(xml, slot, hexv):
    """The slot's color as srgbClr (a sysClr is replaced: a color typed in is a fixed color)."""
    pat = re.compile(rf"(<a:{slot}>)\s*<a:(?:srgbClr|sysClr)\b[^>]*/>\s*(</a:{slot}>)")
    new, n = pat.subn(lambda m: f'{m.group(1)}<a:srgbClr val="{hexv}"/>{m.group(2)}', xml, count=1)
    return new if n else xml


def _set_font(xml, kind, name):
    tag = "majorFont" if kind == "major" else "minorFont"
    pat = re.compile(rf'(<a:{tag}>\s*<a:latin typeface=")[^"]*(")')
    return pat.sub(lambda m: m.group(1) + name.replace('"', "").replace("<", "").replace("&", "and") + m.group(2), xml, count=1)


def apply(std, sheet_rows):
    """The theme the sheet says. Returns (new theme dict or None when nothing changed, [problems], [changed names])."""
    cur = (std.get("theme") or {}).get("xml") or ""
    xml = cur or BASE
    have = TL.read_theme(cur) or {"colors": {}, "major": "", "minor": ""}
    by_name = {TL.THEME_NAMES[s].casefold(): ("color", s) for s in TL.THEME_SLOTS}
    by_name.update({lab.casefold(): ("font", k) for k, lab in FONTS})
    problems, changed = [], []
    for r in sheet_rows or []:
        name = " ".join(str(r.get("Name") or "").split())
        what = by_name.get(name.casefold())
        if what is None:
            if name:
                problems.append(f"Theme, {name}: not one of the theme's colors or fonts; left out.")
            continue
        v = " ".join(str(r.get("Value") if r.get("Value") is not None else "").split())
        kind, key = what
        if not v:
            continue                                     # blank: the theme keeps what it has
        if kind == "color":
            m = HEX.match(v)
            if not m:
                problems.append(f"Theme, {name}: \"{v}\" is not a color (six hex digits); kept as it was.")
                continue
            hexv = m.group(1).upper()
            if hexv != have["colors"].get(key):
                xml = _set_color(xml, key, hexv)
                changed.append(name)
        else:
            if v != have.get(key):
                xml = _set_font(xml, key, v)
                changed.append(name)
    if not changed:
        return None, problems, []
    t = dict(std.get("theme") or {})
    t["xml"] = xml
    t.setdefault("name", (TL.read_theme(xml) or {}).get("name", "Theme"))
    return t, problems, changed
