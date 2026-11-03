"""The template's validation report (3.23.0): what would bite an author later, read from the finished template.

  styles     a style used (body, headers, footers, Quick Parts) but not defined
  quickparts direct formatting inside a Quick Part (it overrides the style); a Quick Part's style the part's own copy
             defines differently from the template
  fonts      a font named anywhere that this PC does not have
  fields     STYLEREF to a style that is not defined; DOCPROPERTY to a property the file does not hold; a field that
             carries MERGEFORMAT or CHARFORMAT (it keeps old formatting instead of the formatting where it sits)
  numbering  a list number reference with no definition
  hidden     the hidden text styles (for reference: they disappear with Show/Hide off)

Read-only: the file is opened from bytes and never written. Returns a Report; Report.text() is the report in words.
Rules only; nothing leaves the PC."""
import io, re, zipfile
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
FIELD_RE = re.compile(r'^\s*(STYLEREF|DOCPROPERTY)\s+(?:"([^"]+)"|(\S+))', re.I)
DIRECT = ("rFonts", "sz", "color", "b", "i", "u", "highlight", "caps")


def _w(t):
    return f"{{{W}}}{t}"


class Report:
    def __init__(self, path):
        self.path = path
        self.items = []                    # {"area", "severity" (problem|warning|note), "what", "where"}
        self.stats = {}

    def add(self, area, severity, what, where=""):
        self.items.append({"area": area, "severity": severity, "what": what, "where": where})

    def problems(self):
        return [i for i in self.items if i["severity"] == "problem"]

    def warnings(self):
        return [i for i in self.items if i["severity"] == "warning"]

    def text(self):
        import os
        lines = [f"Validation report: {os.path.basename(self.path)}",
                 f"{len(self.problems())} problem(s), {len(self.warnings())} warning(s). "
                 + ", ".join(f"{k} {v}" for k, v in self.stats.items()), ""]
        for sev, title in (("problem", "Problems (fix before authors use it)"), ("warning", "Warnings"), ("note", "Notes")):
            its = [i for i in self.items if i["severity"] == sev]
            if its:
                lines.append(title)
                lines += [f"  [{i['area']}] {i['what']}" + (f" ({i['where']})" if i["where"] else "") for i in its]
                lines.append("")
        if not self.items:
            lines.append("Nothing to report.")
        return "\n".join(lines)


def _xml(z, n):
    try:
        return etree.fromstring(z.read(n))
    except (KeyError, etree.XMLSyntaxError):
        return None


def _styles(root):
    out = {}
    if root is None:
        return out
    for s in root.findall("w:style", NS):
        nm = s.find("w:name", NS)
        out[s.get(_w("styleId"))] = (nm.get(_w("val")) if nm is not None else s.get(_w("styleId")), s)
    return out


def _instrs(root):
    """Every field instruction in a part (simple and complex fields)."""
    out = [f.get(_w("instr")) or "" for f in root.iter(_w("fldSimple"))]
    cur = None
    for el in root.iter(_w("fldChar"), _w("instrText")):
        if el.tag == _w("fldChar"):
            t = el.get(_w("fldCharType"))
            if t == "begin":
                cur = ""
            elif t in ("separate", "end") and cur is not None:
                out.append(cur); cur = None
        elif cur is not None:
            cur += el.text or ""
    return [i.strip() for i in out if i and i.strip()]


def validate(path=None, data=None, installed_fonts=None):
    """The report for a template or document (read once)."""
    rep = Report(path or "template")
    z = zipfile.ZipFile(io.BytesIO(data) if data is not None else path)
    names = set(z.namelist())
    sroot = _xml(z, "word/styles.xml")
    styles = _styles(sroot)
    by_name = {v[0].casefold(): k for k, v in styles.items()}
    stories = [n for n in sorted(names) if re.match(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml$", n)]
    gl = "word/glossary/document.xml" if "word/glossary/document.xml" in names else None
    gstyles = _styles(_xml(z, "word/glossary/styles.xml")) if "word/glossary/styles.xml" in names else {}
    # styles used but not defined
    used = {}
    for n in stories + ([gl] if gl else []):
        root = _xml(z, n)
        if root is None:
            continue
        for tag in ("pStyle", "rStyle", "tblStyle"):
            for el in root.iter(_w(tag)):
                used.setdefault(el.get(_w("val")), set()).add(n.split("/")[-1])
    for sid, where in sorted(used.items()):
        if sid and sid not in styles and sid not in gstyles:
            rep.add("styles", "problem", f"style {sid} is used but not defined", ", ".join(sorted(where)))
    rep.stats["styles"] = len(styles)
    # Quick Parts: direct formatting, and style copies that disagree
    if gl:
        g = _xml(z, gl)
        nparts = 0
        for dp in g.iter(_w("docPart")):
            nparts += 1
            nm = dp.find("w:docPartPr/w:name", NS)
            name = nm.get(_w("val")) if nm is not None else "(no name)"
            body = dp.find("w:docPartBody", NS)
            if body is None:
                continue
            n = sum(1 for rpr in body.iter(_w("rPr")) if any(rpr.find(f"w:{t}", NS) is not None for t in DIRECT)
                    and rpr.getparent() is not None and rpr.getparent().tag == _w("r"))
            if n:
                rep.add("quickparts", "warning", f"Quick Part {name}: {n} run(s) carry direct formatting that overrides their style")
            for el in body.iter(_w("pStyle"), _w("rStyle")):
                sid = el.get(_w("val"))
                if sid in styles and sid in gstyles and etree.tostring(styles[sid][1]) != etree.tostring(gstyles[sid][1]):
                    rep.add("quickparts", "warning", f"Quick Part {name}: its copy of {styles[sid][0]} differs from the template's")
        rep.stats["quick parts"] = nparts
    # fields
    props = set()
    for n in ("docProps/custom.xml",):
        if n in names:
            props |= set(re.findall(r'name="([^"]+)"', z.read(n).decode("utf-8", "replace")))
    core = z.read("docProps/core.xml").decode("utf-8", "replace") if "docProps/core.xml" in names else ""
    app = z.read("docProps/app.xml").decode("utf-8", "replace") if "docProps/app.xml" in names else ""
    for p, tag, src in (("Title", "dc:title", core), ("Subject", "dc:subject", core), ("Author", "dc:creator", core),
                        ("Company", "Company", app), ("Manager", "Manager", app)):
        if re.search(rf"<{tag}>[^<]+</{tag}>", src):
            props.add(p)
    nfields = 0
    for n in stories + ([gl] if gl else []):
        root = _xml(z, n)
        if root is None:
            continue
        for ins in _instrs(root):
            nfields += 1
            where = n.split("/")[-1]
            if re.search(r"\\\*\s*(MERGEFORMAT|CHARFORMAT)", ins, re.I):
                rep.add("fields", "warning", f"{ins.split()[0]} field keeps old formatting (MERGEFORMAT or CHARFORMAT)", where)
            m = FIELD_RE.match(ins)
            if not m:
                continue
            kind, arg = m.group(1).upper(), (m.group(2) or m.group(3) or "").strip()
            if kind == "STYLEREF" and not arg.isdigit() and arg.casefold() not in by_name:
                rep.add("fields", "problem", f'STYLEREF "{arg}" points at a style that is not defined', where)
            if kind == "DOCPROPERTY" and arg not in props:
                rep.add("fields", "problem", f'DOCPROPERTY "{arg}" reads a property the file does not hold', where)
    rep.stats["fields"] = nfields
    # numbering
    nroot = _xml(z, "word/numbering.xml")
    nums = {n.get(_w("numId")) for n in nroot.findall("w:num", NS)} if nroot is not None else set()
    for n in stories + ([gl] if gl else []):
        root = _xml(z, n)
        if root is None:
            continue
        for el in root.iter(_w("numId")):
            v = el.get(_w("val"))
            if v not in (None, "0") and v not in nums:
                rep.add("numbering", "problem", f"list number {v} has no definition", n.split("/")[-1])
                break
    # fonts
    fonts = set()
    if sroot is not None:
        for rf in sroot.iter(_w("rFonts")):
            fonts |= {rf.get(_w(a)) for a in ("ascii", "hAnsi") if rf.get(_w(a))}
    th = next((n for n in names if n.startswith("word/theme/") and n.endswith(".xml")), None)
    if th:
        fonts |= set(re.findall(r'<a:(?:major|minor)Font>\s*<a:latin typeface="([^"]+)"', z.read(th).decode("utf-8", "replace")))
    fonts = {f for f in fonts if f and not f.startswith("+")}
    rep.stats["fonts"] = len(fonts)
    if installed_fonts is not None:
        have = {f.casefold() for f in installed_fonts}
        for f in sorted(fonts):
            if f.casefold() not in have:
                rep.add("fonts", "warning", f"{f} is not installed on this PC")
    # hidden text styles, for reference
    for sid, (name, el) in styles.items():
        v = el.find("w:rPr/w:vanish", NS)
        if v is not None and v.get(_w("val")) not in ("0", "false"):
            rep.add("hidden", "note", f"{name} is hidden text (shows with Show/Hide on)")
    return rep
