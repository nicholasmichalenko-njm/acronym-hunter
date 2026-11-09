"""In our drafts (3.92.0; claude/stationkeeper-acronyms-on-the-page-3.92.md): one volume's Word draft checked against the
effort's acronym list, and the fixes written as tracked changes into a copy. The draft itself is only read.

check(path, entries) -> {"findings": [...], "table": {...}, "use": {term: count}}
  a finding: {"term", "definition", "kind", "first": (para, start, end), "spelled": [(para, start, end)], "where": text}
  kinds: "before"  used before it is spelled out (or never spelled out): the first use gets the words, a later
                   spelled-out place loses them
         "again"   spelled out again after its first spelled-out use: those places lose the words
         "unlisted" an acronym used in the draft that is not in the list (said, not fixed)
  table: the volume's Acronyms table (a table whose first row says Acronym): {"rows", "listed_not_used", "used_not_listed"}
fix(path, out_path, findings, author) -> out_path    a copy with each finding's fix as tracked changes (insertions and
                                                       deletions Word shows with Track Changes; accept or reject there)
Rules only (No AI); nothing leaves the PC."""
import copy, datetime, io, os, re, zipfile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
_ACR = re.compile(r"(?<![A-Za-z0-9&-])([A-Z][A-Z0-9&]{1,7}(?:-[A-Z0-9&]{1,7})*)(?![A-Za-z0-9&])")
_SKIP = {"I", "II", "III", "IV", "VI", "VII", "VIII", "IX", "XI", "XII", "OK", "TBD", "NOTE", "AND", "OR", "THE", "SHALL", "WILL"}


def _w(t):
    return f"{{{W}}}{t}"


# ---------------------------------------------------------------- reading
def _atoms(p):
    """[(run, t element, start, end)] for the visible text of a paragraph (deleted text left out)."""
    out, pos = [], 0
    for r in p.iter(_w("r")):
        if any(a.tag == _w("del") for a in r.iterancestors()):
            continue
        for t in r:
            if t.tag == _w("t"):
                s = t.text or ""
            elif t.tag == _w("tab"):
                s = "\t"
            else:
                continue
            out.append((r, t, pos, pos + len(s)))
            pos += len(s)
    return out


def _text(p):
    return "".join(((t.text or "") if t.tag == _w("t") else "\t") for _r, t, _a, _b in _atoms(p))


def _paras(root):
    body = root.find("w:body", NS)
    return list(body.iter(_w("p"))) if body is not None else []


def _acr_table(root):
    """The volume's Acronyms table: its rows [(term, definition)] and the paragraphs inside it."""
    for tbl in root.iter(_w("tbl")):
        rows = tbl.findall("w:tr", NS)
        if not rows:
            continue
        head = " ".join(_text(p) for p in rows[0].iter(_w("p"))).casefold()
        if "acronym" not in head and "abbreviation" not in head:
            continue
        out = []
        for tr in rows[1:]:
            cells = [" ".join(_text(p) for p in tc.iter(_w("p"))).strip() for tc in tr.findall("w:tc", NS)]
            if cells and cells[0]:
                out.append((cells[0], cells[1] if len(cells) > 1 else ""))
        return out, set(tbl.iter(_w("p")))
    return [], set()


def _term_rx(term):
    return re.compile(r"(?<![A-Za-z0-9&])" + re.escape(term) + r"(?![A-Za-z0-9&])")


def _spelled_rx(term, definition):
    words = r"\s+".join(re.escape(w) for w in definition.split())
    return re.compile(words + r"\s*\(\s*" + re.escape(term) + r"\s*\)", re.I)


def check(path, entries):
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"))
    paras = _paras(root)
    table_rows, in_table = _acr_table(root)
    texts = [("" if p in in_table else _text(p)) for p in paras]
    listed = {t: (dfn or "") for t, dfn in entries if t}
    findings, use = [], {}
    for term, dfn in sorted(listed.items(), key=lambda x: x[0].casefold()):
        rx = _term_rx(term)
        hits = [(i, m.start(), m.end()) for i, tx in enumerate(texts) for m in rx.finditer(tx)]
        if not hits:
            continue
        use[term] = len(hits)
        if not dfn.strip():
            continue
        srx = _spelled_rx(term, dfn)
        spelled = [(i, m.start(), m.end()) for i, tx in enumerate(texts) for m in srx.finditer(tx)]
        first = hits[0]
        inside = lambda h, s: h[0] == s[0] and s[1] <= h[1] and h[2] <= s[2]
        where = texts[first[0]][max(0, first[1] - 50): first[2] + 50].strip()
        if not spelled or not inside(first, spelled[0]):
            findings.append({"term": term, "definition": dfn, "kind": "before", "first": first, "spelled": spelled[:1],
                             "where": where, "para": first[0] + 1})
        if len(spelled) > 1 or (spelled and not inside(first, spelled[0]) and len(spelled) > 1):
            extra = spelled[1:]
            if extra:
                findings.append({"term": term, "definition": dfn, "kind": "again", "first": first, "spelled": extra,
                                 "where": texts[extra[0][0]][max(0, extra[0][1] - 20): extra[0][2] + 20].strip(),
                                 "para": extra[0][0] + 1})
    seen = {}
    for i, tx in enumerate(texts):
        for m in _ACR.finditer(tx):
            t = m.group(1)
            if t not in listed and t not in _SKIP and len(t) >= 2:
                seen.setdefault(t, (i, m.start(), m.end()))
    for t, at in sorted(seen.items()):
        findings.append({"term": t, "definition": "", "kind": "unlisted", "first": at, "spelled": [],
                         "where": texts[at[0]][max(0, at[1] - 40): at[2] + 40].strip(), "para": at[0] + 1})
    tab = {"rows": table_rows, "listed_not_used": [], "used_not_listed": []}
    if table_rows:
        in_tab = {t for t, _d in table_rows}
        tab["listed_not_used"] = sorted(t for t in in_tab if t not in use and t not in seen)
        tab["used_not_listed"] = sorted(t for t in use if t not in in_tab)
    return {"findings": findings, "table": tab, "use": use}


# ---------------------------------------------------------------- writing tracked changes
class _Ids:
    def __init__(self, root):
        ids = [int(x) for x in root.xpath("//@w:id", namespaces=NS) if str(x).lstrip("-").isdigit()]
        self.n = max(ids + [0]) + 1000

    def next(self):
        self.n += 1
        return str(self.n)


def _split(p, at):
    """A run boundary at character `at` of the paragraph's visible text. Returns the atom list after the split."""
    for r, t, a, b in _atoms(p):
        if a < at < b and t.tag == _w("t"):
            head, tail = (t.text or "")[: at - a], (t.text or "")[at - a:]
            new = etree.Element(_w("r"))
            rpr = r.find("w:rPr", NS)
            if rpr is not None:
                new.append(copy.deepcopy(rpr))
            nt = etree.SubElement(new, _w("t")); nt.text = tail; nt.set(XML_SPACE, "preserve")
            after = list(r)[list(r).index(t) + 1:]
            for x in after:                                      # what came after the text in the run moves with it
                new.append(x)
            t.text = head; t.set(XML_SPACE, "preserve")
            r.addnext(new)
            break
    return _atoms(p)


def _mark(tag, ids, author, when):
    el = etree.Element(_w(tag))
    el.set(_w("id"), ids.next()); el.set(_w("author"), author); el.set(_w("date"), when)
    return el


def insert(p, at, text, ids, author, when):
    """Tracked insertion of text at character `at`, in the look of the run there."""
    atoms = _split(p, at)
    after = next(((r, t) for r, t, a, _b in atoms if a == at), None)
    before = next(((r, t) for r, t, _a, b in atoms if b == at), None)
    host = (after or before or (None, None))[0]
    ins = _mark("ins", ids, author, when)
    r = etree.SubElement(ins, _w("r"))
    rpr = host.find("w:rPr", NS) if host is not None else None
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    t = etree.SubElement(r, _w("t")); t.text = text; t.set(XML_SPACE, "preserve")
    if after is not None:
        _outer(after[0]).addprevious(ins)
    elif before is not None:
        _outer(before[0]).addnext(ins)
    else:
        p.append(ins)
    return ins


def _outer(r):
    """The run, or the tracked insertion holding it (so a new mark sits beside it, never inside it)."""
    par = r.getparent()
    return par if par is not None and par.tag == _w("ins") else r


def delete(p, a, b, ids, author, when):
    """Tracked deletion of characters a to b."""
    _split(p, a)
    atoms = _split(p, b)
    runs = []
    for r, t, s, e in atoms:
        if s >= a and e <= b and r not in runs:
            runs.append(r)
    for r in runs:
        d = _mark("del", ids, author, when)
        r.addprevious(d)
        d.append(r)
        for t in r.findall("w:t", NS):
            t.tag = _w("delText")
    return len(runs)


def fix(path, out_path, findings, author="Stationkeeper"):
    """A copy of the draft with each finding's fix as tracked changes; the draft itself is only read."""
    with zipfile.ZipFile(path) as zin:
        names = zin.namelist()
        root = etree.fromstring(zin.read("word/document.xml"))
        parts = {n: zin.read(n) for n in names}
        infos = zin.infolist()
    paras = _paras(root)
    ids = _Ids(root)
    when = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    edits = []                                                   # (para, at, kind, payload), done right to left
    for f in findings:
        term, dfn = f["term"], f["definition"]
        if f["kind"] == "before":
            i, s, e = f["first"]
            edits.append((i, e, "ins", ")"))
            edits.append((i, s, "ins", f"{dfn} ("))
            for (j, a, b) in f["spelled"]:                         # the later spelled-out place keeps the acronym alone
                edits += _strip_spelled(paras[j], j, a, b, term)
        elif f["kind"] == "again":
            for (j, a, b) in f["spelled"]:
                edits += _strip_spelled(paras[j], j, a, b, term)
    for i, at, kind, payload in sorted(edits, key=lambda x: (x[0], x[1]), reverse=True):
        if kind == "ins":
            insert(paras[i], at, payload, ids, author, when)
        else:
            delete(paras[i], at, payload, ids, author, when)
    parts["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for i in infos:
            z.writestr(i, parts[i.filename])
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    tmp = out_path + ".part"
    with open(tmp, "wb") as fh:
        fh.write(out.getvalue())
    os.replace(tmp, out_path)
    return out_path


def _strip_spelled(p, j, a, b, term):
    """The deletions that leave "TERM" from "Definition words (TERM)" between a and b."""
    tx = _text(p)[a:b]
    k = tx.rfind("(")
    m = re.search(re.escape(term), tx[k:]) if k >= 0 else None
    if k < 0 or m is None:
        return []
    ts = a + k + m.start()
    te = ts + len(term)
    return [(j, te, "del", b), (j, a, "del", ts)]
