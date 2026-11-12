"""The PDF's comments written into the Word copy (4.16.0; claude/stationkeeper-pdf-comments-plan-4.16.html).

apply(copy, comments, stream, paras): each pinned comment (pdfcomments.pin) the Word way, under the reviewer's name and
date:
- a cross-out: a tracked deletion of exactly the struck letters (a whole word takes one space with it);
- an insert (a caret with the reviewer's words): a tracked insertion at that letter, a space added where words meet;
- Acrobat's Replace text (a cross-out and an insert joined by RT /Group): a tracked deletion and insertion in one place;
- a highlight, underline or squiggly: a Word comment on exactly those words (its note, or "Highlighted" when it has
  none or only repeats the words);
- a sticky note, text box, callout, shape, stamp or attachment: a Word comment on the words it was pinned to;
- a reply: a Word reply under its comment; a review status: Completed marks the comment done, another status is a
  reply line.
The PDF's words are found in the copy through the word-for-word alignment Check uses (difflib on the words). Returns
the list of what each comment became, for the sidecar and Check. Rules only (No AI); nothing leaves the PC."""
import copy as _copy, datetime, difflib, os, re, zipfile

from lxml import etree

NS_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS_W14 = "http://schemas.microsoft.com/office/word/2010/wordml"
NS_W15 = "http://schemas.microsoft.com/office/word/2012/wordml"
NS_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
W, W14, W15 = "{%s}" % NS_W, "{%s}" % NS_W14, "{%s}" % NS_W15
XS = "{http://www.w3.org/XML/1998/namespace}space"
RELS = "http://schemas.openxmlformats.org/package/2006/relationships"
REL_C = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments"
REL_CX = "http://schemas.microsoft.com/office/2011/relationships/commentsExtended"
CT_C = "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml"
CT_CX = "application/vnd.openxmlformats-officedocument.wordprocessingml.commentsExtended+xml"
SAID = {"highlight": "Highlighted", "underline": "Underlined", "squiggly": "Squiggly underline", "strike": "Cross-out",
        "caret": "Insert here", "note": "Note", "textbox": "Text box", "shape": "Shape", "stamp": "Stamp",
        "attachment": "Attachment"}


def _norm(s):
    return " ".join((s or "").split()).casefold()


class Para:
    """A paragraph's original text: its w:t and w:delText (a tab or break is one space), runs inside w:ins left out."""
    def __init__(self, p):
        self.p = p

    def atoms(self):
        pos, out = 0, []
        for el in self.p.iter(W + "t", W + "delText", W + "tab", W + "br"):
            if any(a.tag == W + "ins" for a in el.iterancestors()):
                continue
            if el.getparent() is None or el.getparent().tag != W + "r":
                continue
            n = len(el.text or "") if el.tag in (W + "t", W + "delText") else 1
            out.append((el, pos, pos + n))
            pos += n
        return out

    def text(self):
        return "".join((el.text or "") if el.tag in (W + "t", W + "delText") else " " for el, _a, _b in self.atoms())

    def split(self, off):
        for el, a, b in self.atoms():
            if a < off < b and el.tag in (W + "t", W + "delText"):
                run = el.getparent()
                kids = list(run)
                i = kids.index(el)
                right = _copy.deepcopy(run)
                rk = list(right)
                for k in kids[i + 1:]:
                    run.remove(k)
                for k in rk[:i]:
                    if k.tag != W + "rPr":
                        right.remove(k)
                t = el.text or ""
                el.text = t[:off - a]; el.set(XS, "preserve")
                rk[i].text = t[off - a:]; rk[i].set(XS, "preserve")
                run.addnext(right)
                return

    def runs(self, s, e):
        """The runs holding letters s..e-1, splitting runs at s and e first."""
        self.split(s); self.split(e)
        out = []
        for el, a, b in self.atoms():
            if a >= s and b <= e and b > a:
                r = el.getparent()
                if not out or out[-1] is not r:
                    out.append(r)
        return out

    def top(self, el):
        while el.getparent() is not None and el.getparent() is not self.p:
            el = el.getparent()
        return el


class Writer:
    def __init__(self, root):
        self.root = root
        self.next_id = 1 + max([int(x) for el in root.iter(W + "ins", W + "del", W + "commentRangeStart")
                                for x in [el.get(W + "id") or ""] if x.isdigit()] or [0])
        self.comments = []                         # (id, author, date, text, parent id or None, done)

    def nid(self):
        self.next_id += 1
        return str(self.next_id - 1)

    def delete(self, para, s, e, author, date):
        n = 0
        for r in para.runs(s, e):
            if r.getparent().tag == W + "del":
                continue
            d = etree.Element(W + "del"); d.set(W + "id", self.nid()); d.set(W + "author", author); d.set(W + "date", date)
            r.addprevious(d); d.append(r)
            for t in r.iter(W + "t"):
                t.tag = W + "delText"
            n += 1
        return n

    def insert(self, para, off, text, author, date):
        para.split(off)
        left = None
        for el, a, b in para.atoms():
            if b == off and b > a:
                left = el.getparent()
        ref = left
        if ref is None:
            for el, a, b in para.atoms():
                if a == off:
                    ref = el.getparent(); break
        r = etree.Element(W + "r")
        if ref is not None and ref.find(W + "rPr") is not None:
            r.append(_copy.deepcopy(ref.find(W + "rPr")))
        t = etree.SubElement(r, W + "t"); t.text = text; t.set(XS, "preserve")
        ins = etree.Element(W + "ins"); ins.set(W + "id", self.nid()); ins.set(W + "author", author); ins.set(W + "date", date)
        ins.append(r)
        if left is not None:
            para.top(left).addnext(ins)
        elif ref is not None:
            para.top(ref).addprevious(ins)
        else:
            ppr = para.p.find(W + "pPr")
            para.p.insert(list(para.p).index(ppr) + 1 if ppr is not None else 0, ins)
        return 1

    def comment(self, start, end, author, date, text, parent=None):
        """A Word comment from (Para, letter) start to (Para, letter) end; parent: the comment it replies to."""
        cid = self.nid()
        (p1, s), (p2, e) = start, end
        if p1 is p2:
            p1.runs(s, e)
        else:
            p1.split(s); p2.split(e)
        first = next((el.getparent() for el, a, b in p1.atoms() if a >= s and b > a), None)
        last = None
        for el, a, b in p2.atoms():
            if b <= e and b > a:
                last = el.getparent()
        rs = etree.Element(W + "commentRangeStart"); rs.set(W + "id", cid)
        re_ = etree.Element(W + "commentRangeEnd"); re_.set(W + "id", cid)
        if first is not None:
            p1.top(first).addprevious(rs)
        else:
            p1.p.append(rs)
        if last is not None:
            p2.top(last).addnext(re_)
        else:
            p2.p.append(re_)
        ref = etree.Element(W + "r")
        rpr = etree.SubElement(ref, W + "rPr"); etree.SubElement(rpr, W + "rStyle").set(W + "val", "CommentReference")
        etree.SubElement(ref, W + "commentReference").set(W + "id", cid)
        re_.addnext(ref)
        self.comments.append([cid, author, date, text, parent, False])
        return cid

    def parts(self):
        """comments.xml and commentsExtended.xml for the comments written."""
        croot = etree.Element(W + "comments", nsmap={"w": NS_W, "w14": NS_W14, "mc": NS_MC})
        croot.set("{%s}Ignorable" % NS_MC, "w14")
        xroot = etree.Element(W15 + "commentsEx", nsmap={"w15": NS_W15, "mc": NS_MC})
        xroot.set("{%s}Ignorable" % NS_MC, "w15")
        para_of = {}
        for k, (cid, author, date, text, parent, done) in enumerate(self.comments):
            c = etree.SubElement(croot, W + "comment")
            c.set(W + "id", cid); c.set(W + "author", author); c.set(W + "date", date)
            c.set(W + "initials", "".join(x[0] for x in author.split()[:3]).upper() or "R")
            lines = (text or "").splitlines() or [""]
            for i, ln in enumerate(lines):
                p = etree.SubElement(c, W + "p")
                ppr = etree.SubElement(p, W + "pPr"); etree.SubElement(ppr, W + "pStyle").set(W + "val", "CommentText")
                if i == 0:
                    r0 = etree.SubElement(p, W + "r"); rp = etree.SubElement(r0, W + "rPr")
                    etree.SubElement(rp, W + "rStyle").set(W + "val", "CommentReference")
                    etree.SubElement(r0, W + "annotationRef")
                r = etree.SubElement(p, W + "r"); t = etree.SubElement(r, W + "t"); t.text = ln; t.set(XS, "preserve")
            pid = "%08X" % (0x10000000 + 0x101 * (k + 1))
            p.set(W14 + "paraId", pid); p.set(W14 + "textId", "77777777")
            para_of[cid] = pid
            x = etree.SubElement(xroot, W15 + "commentEx"); x.set(W15 + "paraId", pid)
            if parent:
                x.set(W15 + "paraIdParent", para_of.get(parent, pid))
            x.set(W15 + "done", "1" if done else "0")
        dump = lambda r: etree.tostring(r, xml_declaration=True, encoding="UTF-8", standalone=True)   # noqa: E731
        return dump(croot), dump(xroot)


def _docx_words(paras):
    """The copy's words in order: [(word, Para, start, end)], from paragraphs with text (as Check reads them)."""
    out = []
    for pa in paras:
        t = pa.text()
        if not t.strip():
            continue
        for m in re.finditer(r"\S+", t):
            out.append((m.group(0), pa, m.start(), m.end()))
    return out


def _align(a, b):
    """Index map from list a to list b: equal runs exactly; inside a difference, the nearest equal word before it."""
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    m, exact = {}, set()
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            m[blk.a + k] = blk.b + k; exact.add(blk.a + k)
    out, last = [], (-1, -1)
    for i in range(len(a)):
        if i in m:
            last = (i, m[i]); out.append(m[i])
        else:
            out.append(min(len(b) - 1, max(0, last[1] + (i - last[0]))))
    return out, exact


def apply(copy, comments, stream, paras_src=None, now=None):
    """Write the pinned comments into the copy (a .docx made by redlinecopy). Returns one record per comment."""
    with zipfile.ZipFile(copy) as z:
        names = z.namelist()
        data = {n: z.read(n) for n in names}
    root = etree.fromstring(data["word/document.xml"])
    paras = [Para(p) for p in root.iter(W + "p")]
    dw = _docx_words(paras)
    amap, exact = _align(stream.words, [w for w, *_ in dw])
    wr = Writer(root)
    stamp = (now or datetime.datetime.utcnow()).strftime("%Y-%m-%dT%H:%M:%SZ")

    def at(wi, ci):
        """(Para, letter) in the copy for letter ci of stream word wi."""
        if not dw:
            return None
        j = amap[wi] if wi < len(amap) else len(dw) - 1
        w, pa, s, e = dw[j]
        return pa, s + max(0, min(ci, e - s))

    by = {(c["page"], c["n"]): c for c in comments}
    replies, groups, status = {}, {}, {}
    for c in comments:
        rt = c.get("reply_to")
        if not rt or rt not in by:
            continue
        par = by[rt]
        if c.get("group") or par.get("group"):
            groups[rt] = c; c["_in_group"] = True
        elif c.get("state"):
            status.setdefault(rt, []).append(c); c["_status"] = True
        else:
            replies.setdefault(rt, []).append(c); c["_reply"] = True
    head = _headings(stream, paras_src)
    out, made = [], {}
    order = sorted((c for c in comments if not (c.get("_in_group") or c.get("_status") or c.get("_reply"))),
                   key=lambda c: (c["page"], c["n"]))
    for c in order:
        author, date = c.get("author") or "PDF reviewer", c.get("date") or stamp
        rec = {"page": c["page"], "kind": c["kind"], "author": author, "date": date, "note": c.get("note") or "",
               "marked": c.get("marked") or "", "how": c.get("how") or "not placed", "became": "", "heading": "",
               "in_copy": ""}
        p = c.get("pin")
        if not p or not dw:
            rec["became"] = "listed only"; out.append(rec); continue
        w0, c0, w1, c1 = p
        rec["heading"] = head[w0] if head and w0 < len(head) else ""
        if w0 not in exact or w1 not in exact:
            rec["how"] = rec["how"] if rec["how"] != "words" else "nearby words"
        a, b = at(w0, c0), at(w1, c1)
        rec["in_copy"] = _between(a, b)
        note = (c.get("note") or "").strip()
        own = note and _norm(note) != _norm(c.get("marked"))
        grp = groups.get((c["page"], c["n"]))
        kids = replies.get((c["page"], c["n"]), []) + status.get((c["page"], c["n"]), [])
        cid = None
        if c["kind"] == "strike" or (c["kind"] == "caret" and grp is not None and grp["kind"] == "strike"):
            strike, caret = (c, grp) if c["kind"] == "strike" else (grp, c)
            if strike is not c:
                sp = strike.get("pin") or p
                a, b = at(sp[0], sp[1]), at(sp[2], sp[3])
                rec["in_copy"] = _between(a, b)
                rec["marked"] = strike.get("marked") or ""
            new = ((caret or {}).get("note") or "").strip() if caret is not None else ""
            if caret is not None and new:
                wr.delete(a[0], a[1], b[1], author, date) if a[0] is b[0] else _delete_across(wr, a, b, author, date)
                wr.insert(b[0], b[1], new, (caret.get("author") or author), (caret.get("date") or date))
                rec["became"], rec["note"], rec["kind"] = "replacement", new, "replace"
            else:
                a2, b2 = _with_space(a, b) if a[0] is b[0] and _whole(a, b) else (a, b)
                wr.delete(a[0], a2[1], b2[1], author, date) if a[0] is b[0] else _delete_across(wr, a, b, author, date)
                rec["became"] = "deletion"
                if own:
                    cid = wr.comment(a, b, author, date, note)
        elif c["kind"] == "caret":
            pt = a if c.get("point", "before") == "before" else b
            if note:
                wr.insert(pt[0], pt[1], _spaced(pt, note), author, date)
                rec["became"] = "insertion"
            else:
                e = at(w1, len(stream.words[w1]))
                s = at(w0, 0)
                cid = wr.comment(s, e, author, date, "New paragraph here" if c.get("sy") == "P" else SAID["caret"])
                rec["became"] = "comment"
        else:
            text = note if own else (f"Stamp: {c.get('name') or c.get('subject') or 'stamp'}".replace("#20", " ")
                                     if c["kind"] == "stamp" and not note else (SAID.get(c["kind"], "Comment") if not note or not own else note))
            cid = wr.comment(a, b, author, date, text)
            rec["became"], rec["note"] = "comment", text
        if kids:
            if cid is None:
                cid = wr.comment(a, b, author, date, SAID.get(c["kind"], "Comment"))
            for k in sorted(kids, key=lambda x: (x.get("date") or "", x["n"])):
                if k.get("state") == "Completed":
                    for row in wr.comments:
                        if row[0] == cid:
                            row[5] = True
                    rec["done"] = True
                    continue
                txt = (k.get("note") or "").strip()
                if k.get("state") and _norm(txt) in ("", _norm(k["state"])):
                    txt = f"Marked {k['state']}"
                wr.comment(a, b, k.get("author") or "PDF reviewer", k.get("date") or stamp, txt, parent=cid)
                rec.setdefault("replies", []).append({"author": k.get("author") or "", "note": txt})
        out.append(rec)
    if wr.comments:
        cx, cxx = wr.parts()
        data["word/comments.xml"], data["word/commentsExtended.xml"] = cx, cxx
        _package(data, names)
    data["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    tmp = copy + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in names:
            zout.writestr(n, data[n])
    os.replace(tmp, copy)
    return out


def _package(data, names):
    rels = etree.fromstring(data["word/_rels/document.xml.rels"])
    have = {r.get("Type") for r in rels}
    ids = {r.get("Id") for r in rels}
    for typ, target in ((REL_C, "comments.xml"), (REL_CX, "commentsExtended.xml")):
        if typ in have:
            continue
        k = 1
        while f"rIdSKC{k}" in ids:
            k += 1
        ids.add(f"rIdSKC{k}")
        r = etree.SubElement(rels, "{%s}Relationship" % RELS)
        r.set("Id", f"rIdSKC{k}"); r.set("Type", typ); r.set("Target", target)
    data["word/_rels/document.xml.rels"] = etree.tostring(rels, xml_declaration=True, encoding="UTF-8", standalone=True)
    ct = data["[Content_Types].xml"].decode("utf-8")
    for part, typ in (("/word/comments.xml", CT_C), ("/word/commentsExtended.xml", CT_CX)):
        if part not in ct:
            ct = ct.replace("</Types>", f'<Override PartName="{part}" ContentType="{typ}"/></Types>')
    data["[Content_Types].xml"] = ct.encode("utf-8")
    for n in ("word/comments.xml", "word/commentsExtended.xml"):
        if n not in names:
            names.append(n)


def _between(a, b):
    if a is None or b is None:
        return ""
    if a[0] is b[0]:
        return a[0].text()[a[1]:b[1]]
    return a[0].text()[a[1]:] + " ... " + b[0].text()[:b[1]]


def _whole(a, b):
    t = a[0].text()
    return (a[1] == 0 or t[a[1] - 1].isspace()) and (b[1] >= len(t) or t[b[1]].isspace())


def _with_space(a, b):
    """A whole-word deletion takes the space after it (or before it at a paragraph's end)."""
    t = a[0].text()
    if b[1] < len(t) and t[b[1]] == " ":
        return a, (b[0], b[1] + 1)
    if a[1] > 0 and t[a[1] - 1] == " ":
        return (a[0], a[1] - 1), b
    return a, b


def _delete_across(wr, a, b, author, date):
    """A deletion that runs over more than one paragraph (two table cells, two lines kept apart): each part on its own."""
    ids = list(a[0].p.getroottree().getroot().iter(W + "p"))
    i, j = ids.index(a[0].p), ids.index(b[0].p)
    for k in range(i, j + 1):
        pa = Para(ids[k])
        s = a[1] if k == i else 0
        e = b[1] if k == j else len(pa.text())
        if e > s:
            wr.delete(pa, s, e, author, date)
    return 1


def _spaced(pt, text):
    """An insert's words with a space where they meet a word: before them after a word or closing mark, after them
    before a word. Inside a word (letters on both sides) they go in as typed."""
    t = pt[0].text()
    off = pt[1]
    before = t[off - 1] if off > 0 else " "
    after = t[off] if off < len(t) else " "
    if not text or text != text.strip() or (before.isalnum() and after.isalnum()):
        return text
    out = text
    if not before.isspace() and before not in "([{\u201c\"'/-" and text[0].isalnum():
        out = " " + out
    if after.isalnum() and (text[-1].isalnum() or text[-1] in ",;:.)"):
        out = out + " "
    return out


def _headings(stream, paras_src):
    if not paras_src:
        return []
    out, head, last = [], "", -1
    for wi, pi in enumerate(stream.para):
        if pi != last:
            p = paras_src[pi]
            if p.get("kind") == "heading":
                head = p.get("text", "")
            last = pi
        out.append(head)
    return out


def read_back(path):
    """What a Word file holds: {"accepted": [paragraph text with every change taken], "rejected": [... every change
    undone], "comments": [{"id", "author", "text", "parent", "done", "range", "para" (where its words start)}], "deleted": [(author, text)],
    "inserted": [(author, text)]}. Adjacent deletions or insertions by one reviewer read as one."""
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"))
        croot = etree.fromstring(z.read("word/comments.xml")) if "word/comments.xml" in z.namelist() else None
        xroot = etree.fromstring(z.read("word/commentsExtended.xml")) if "word/commentsExtended.xml" in z.namelist() else None
    acc, rej = [], []
    for p in root.iter(W + "p"):
        a, r = [], []
        for el in p.iter(W + "t", W + "delText"):
            ins = any(x.tag == W + "ins" for x in el.iterancestors())
            if el.tag == W + "t":
                a.append(el.text or "")
                if not ins:
                    r.append(el.text or "")
            else:
                r.append(el.text or "")
        acc.append("".join(a)); rej.append("".join(r))
    open_, ranges, where = {}, {}, {}
    pindex = {p: i for i, p in enumerate(root.iter(W + "p"))}
    for el in root.iter(W + "commentRangeStart", W + "commentRangeEnd", W + "t", W + "delText"):
        if el.tag == W + "commentRangeStart":
            open_[el.get(W + "id")] = []
            par = next((a for a in el.iterancestors() if a.tag == W + "p"), None)
            where[el.get(W + "id")] = pindex.get(par, -1)
        elif el.tag == W + "commentRangeEnd":
            ranges[el.get(W + "id")] = "".join(open_.pop(el.get(W + "id"), []))
        else:
            for v in open_.values():
                v.append(el.text or "")
    runs = {"del": [], "ins": []}
    for tag in ("del", "ins"):
        last = None
        for el in root.iter(W + tag):
            txt = "".join(x.text or "" for x in el.iter(W + "t", W + "delText"))
            prev = el.getprevious()
            if last is not None and prev is not None and prev.tag == W + tag and prev.get(W + "author") == el.get(W + "author"):
                last[1] += txt
            else:
                last = [el.get(W + "author"), txt]
                runs[tag].append(last)
    comments = []
    if croot is not None:
        pid = {}
        if xroot is not None:
            for x in xroot.iter(W15 + "commentEx"):
                pid[x.get(W15 + "paraId")] = (x.get(W15 + "paraIdParent"), x.get(W15 + "done") == "1")
        by_para = {}
        for c in croot.iter(W + "comment"):
            ps = list(c.iter(W + "p"))
            last_pid = ps[-1].get(W14 + "paraId") if ps else None
            if last_pid:
                by_para[last_pid] = c.get(W + "id")
            comments.append({"id": c.get(W + "id"), "author": c.get(W + "author"), "date": c.get(W + "date"),
                             "text": "\n".join("".join(t.text or "" for t in p.iter(W + "t")) for p in ps),
                             "_pid": last_pid, "range": ranges.get(c.get(W + "id"), ""),
                             "para": where.get(c.get(W + "id"), -1)})
        for c in comments:
            par, done = pid.get(c.pop("_pid"), (None, False))
            c["parent"], c["done"] = (by_para.get(par) if par else None), done
    return {"accepted": acc, "rejected": rej, "comments": comments,
            "deleted": [tuple(x) for x in runs["del"]], "inserted": [tuple(x) for x in runs["ins"]]}
