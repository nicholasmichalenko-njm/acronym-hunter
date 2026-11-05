"""Technical Edit's edited copy (3.54.0, decision 5): the accepted findings written into a dated copy of the draft as tracked
changes, each with a comment naming the rule, so the author accepts or rejects them in Word (Review > Accept). The
original is only read. A finding with no replacement (a long sentence, a claim to prove) becomes a comment alone.

write(src, findings, out_path, author="Technical Edit", when=None) -> {"changes": n, "comments": n, "skipped": n}
copy_path(src, when) -> "<name> - edited <date time>.docx" beside the source. Nothing leaves the PC."""
import copy as _copy, datetime, os, re, zipfile

from lxml import etree

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % NS_W
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
CT_COMMENTS = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
REL_COMMENTS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
NO_FIX = ("Split it", "Fill it in", "Check the spelling, or add it to a dictionary", "Say who does it", "Rewrite",
          "Say what is better, with a number", "Say what the reader gets from it", "This effort's name", "Close it",
          "Use spacing before and after instead", "Accept or remove them before the copy goes out")


def _parser():
    return etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, huge_tree=False, remove_blank_text=False)


def copy_path(src, when=None):
    when = when or datetime.datetime.now()
    stem = os.path.splitext(os.path.basename(src))[0]
    return os.path.join(os.path.dirname(src), f"{stem} - edited {when.strftime('%Y-%m-%d %H%M')}.docx")


def replaces(f):
    """True when a finding carries replacement words (not advice)."""
    return bool(f.get("fix")) and f["fix"] not in NO_FIX and f.get("end", 0) > f.get("start", 0)


def _runs_text(p):
    """[(run element, its text start, its text)] for the runs directly holding text in the paragraph (hyperlinks included)."""
    out, pos = [], 0
    for r in p.iter(W + "r"):
        if any(a.tag in (W + "del", W + "ins") for a in r.iterancestors()):
            continue
        t = "".join(x.text or "" for x in r.findall(W + "t"))
        if not r.findall(W + "t"):
            continue
        out.append((r, pos, t))
        pos += len(t)
    return out


def _clone_run(r, text, tag="t"):
    n = etree.Element(W + "r")
    rpr = r.find(W + "rPr")
    if rpr is not None:
        n.append(_copy.deepcopy(rpr))
    t = etree.SubElement(n, W + tag)
    t.text = text
    t.set(XML_SPACE, "preserve")
    return n


def _split(p, at):
    """Splits the run holding character position at so a run boundary falls there."""
    for r, s, t in _runs_text(p):
        if s < at < s + len(t):
            a, b = _clone_run(r, t[:at - s]), _clone_run(r, t[at - s:])
            parent = r.getparent()
            i = parent.index(r)
            parent.remove(r)
            parent.insert(i, b); parent.insert(i, a)
            return True
    return False


def _change(p, start, end, new, rid, author, date, cid):
    """Deletes [start, end) and inserts new as tracked changes, wrapped in comment cid. Returns False when the place moved."""
    if end > start:
        _split(p, start); _split(p, end)
    runs = [(r, s, t) for r, s, t in _runs_text(p) if s >= start and s + len(t) <= end and t]
    if end > start and (not runs or runs[0][1] != start or runs[-1][1] + len(runs[-1][2]) != end):
        return False
    first = runs[0][0] if runs else None
    if first is None:                                    # a comment on a place with no words to change
        _split(p, start)
        rs = _runs_text(p)
        anchor = next((r for r, s, _t in rs if s >= start), None)
        if anchor is None and rs:
            anchor = rs[-1][0]
        if anchor is None:
            return False
        first = anchor
    parent = first.getparent()
    i = parent.index(first)
    cs = etree.Element(W + "commentRangeStart"); cs.set(W + "id", str(cid))
    parent.insert(i, cs)
    last = first
    if runs:
        d = etree.Element(W + "del"); d.set(W + "id", str(rid)); d.set(W + "author", author); d.set(W + "date", date)
        parent.insert(parent.index(first), d)
        for r, _s, t in runs:
            r.getparent().remove(r)
            dr = _clone_run(r, t, "delText")
            d.append(dr)
        last = d
        if new:
            ins = etree.Element(W + "ins"); ins.set(W + "id", str(rid + 1)); ins.set(W + "author", author); ins.set(W + "date", date)
            ins.append(_clone_run(runs[0][0], new))
            parent.insert(parent.index(d) + 1, ins)
            last = ins
    ce = etree.Element(W + "commentRangeEnd"); ce.set(W + "id", str(cid))
    parent.insert(parent.index(last) + 1, ce)
    ref = etree.Element(W + "r")
    rpr = etree.SubElement(ref, W + "rPr"); rs = etree.SubElement(rpr, W + "rStyle"); rs.set(W + "val", "CommentReference")
    cr = etree.SubElement(ref, W + "commentReference"); cr.set(W + "id", str(cid))
    parent.insert(parent.index(ce) + 1, ref)
    return True


def _comment(cid, author, date, text):
    c = etree.Element(W + "comment", nsmap={"w": NS_W})
    c.set(W + "id", str(cid)); c.set(W + "author", author); c.set(W + "date", date); c.set(W + "initials", "TE")
    p = etree.SubElement(c, W + "p")
    r = etree.SubElement(p, W + "r")
    t = etree.SubElement(r, W + "t"); t.text = text; t.set(XML_SPACE, "preserve")
    return c


def write(src, findings, out_path, author="Technical Edit", when=None):
    """Writes the copy. findings: the accepted ones (from techedit.review). Returns counts."""
    import filesafety as FS
    FS.guard(out_path, src)                      # 3.57.0: never over the draft it read
    when = when or datetime.datetime.now()
    date = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    zin = zipfile.ZipFile(src)
    names = zin.namelist()
    root = etree.fromstring(zin.read("word/document.xml"), parser=_parser())
    paras = list(root.iter(W + "p"))
    if "word/comments.xml" in names:
        croot = etree.fromstring(zin.read("word/comments.xml"), parser=_parser())
        cid = 1 + max([int(c.get(W + "id") or 0) for c in croot.iter(W + "comment")] or [0])
    else:
        croot, cid = etree.Element(W + "comments", nsmap={"w": NS_W}), 1
    rid = 9000
    done = {"changes": 0, "comments": 0, "skipped": 0}
    # right to left inside each paragraph, so earlier positions stay where they were
    for f in sorted(findings, key=lambda f: (f["para"], -f["start"], -f["end"])):
        if not (0 <= f["para"] < len(paras)):
            done["skipped"] += 1
            continue
        p = paras[f["para"]]
        text = "".join(x.text or "" for x in p.iter(W + "t") if not any(a.tag == W + "del" for a in x.iterancestors()))
        if f["end"] > f["start"] and text[f["start"]:f["end"]] != f["hit"]:
            done["skipped"] += 1                       # the draft changed since the review
            continue
        new = f["fix"] if replaces(f) else None
        note = f"{f.get('title', f['rule'])}. {f.get('why', '')}".strip()
        if not new and f.get("fix"):
            note += f" Suggested: {f['fix']}."
        ok = _change(p, f["start"], f["end"] if new else f["start"], new, rid, author, date, cid)
        if not ok:
            done["skipped"] += 1
            continue
        croot.append(_comment(cid, author, date, note))
        cid += 1; rid += 2
        done["changes" if new else "comments"] += 1
    body = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    cxml = etree.tostring(croot, xml_declaration=True, encoding="UTF-8", standalone=True)
    tmp = out_path + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            data = zin.read(n)
            if n == "word/document.xml":
                data = body
            elif n == "word/comments.xml":
                data = cxml
            elif n == "[Content_Types].xml" and "word/comments.xml" not in names:
                s = data.decode("utf-8")
                s = s.replace("</Types>", f'<Override PartName="/word/comments.xml" ContentType="{CT_COMMENTS}"/></Types>')
                data = s.encode("utf-8")
            elif n == "word/_rels/document.xml.rels" and "word/comments.xml" not in names:
                s = data.decode("utf-8")
                ids = [int(x) for x in re.findall(r'Id="rId(\d+)"', s)] or [0]
                s = s.replace("</Relationships>", f'<Relationship Id="rId{max(ids) + 1}" Type="{REL_COMMENTS}" Target="comments.xml"/></Relationships>')
                data = s.encode("utf-8")
            zout.writestr(n, data)
        if "word/comments.xml" not in names:
            zout.writestr("word/comments.xml", cxml)
    zin.close()
    os.replace(tmp, out_path)
    return done
