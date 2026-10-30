"""Reading customer documents into the compliance review, without any screen (2.59.0): used by both editions of the
app (tkinter and Qt). Moved out of compliance_ui so the Qt edition reads exactly as the tkinter one does.

- read_files(paths, chunks_of): PDFs are read in their page form (pagesent: headers and footers left out, every
  sentence with its exact place); a PDF with a scanned page, and Word, Excel and PowerPoint files, through the
  program's reader (chunks_of, app_gui.rfp_chunks). Returns (items, headings, sources, empty files).
  2.82.0: progress and Stop; a file that cannot be read stops the read and names the file.
- new_matrix(...): a compliance matrix from a read, with the starting outline.
- text_check(M) and add_missing(M, results): nothing missed; any line not in the review goes in, in its place.
Rules only (No AI); nothing leaves the PC.
"""
import datetime, hashlib, os, re
import diag
import compliance as C
import pagesent as PS


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class Stopped(Exception):
    """2.82.0: the person pressed Stop; nothing was read into the matrix."""


class ReadFailed(Exception):
    """2.82.0: one file could not be read; nothing was read into the matrix. .name: the file; .cause: the error."""

    def __init__(self, name, cause):
        super().__init__(f"{name}: {type(cause).__name__}")
        self.name, self.cause = name, cause


_PAGE = re.compile(r"page (\d+)/(\d+)", re.I)


def _takes_say(fn):
    try:
        import inspect
        return len(inspect.signature(fn).parameters) >= 2
    except (TypeError, ValueError):
        return False


def read_files(paths, chunks_of, progress=None, stop=None, page_copy=None):
    """(items, headings, sources, empty): the review sentences of the files, in order.
    2.82.0: progress(fraction, text) as it goes (each file, its pages when the reader reports them, then finding the
    requirements); stop() True between files raises Stopped; a file that cannot be read raises ReadFailed naming it."""
    fc, src, places = [], [], {}
    n = len(paths) + 1                               # the last step: finding the requirements
    say = progress or (lambda _f, _t: None)
    for k, p in enumerate(paths):
        if stop is not None and stop():
            raise Stopped()
        name = os.path.basename(p)
        head = f"File {k + 1} of {len(paths)}: {name}"
        say(k / n, head)
        try:
            pg = None
            pc = None
            if page_copy is not None:                   # 2.96.0: a picture or scanned PDF: its copy with words
                try:
                    pc = page_copy(p, lambda msg, k=k, head=head: say(k / n, f"{head} ({msg})"))
                except Exception:
                    diag.swallowed()
                    pc = None
            if pc:
                try:
                    pg = PS.chunks_for(pc, name)
                except Exception:
                    diag.swallowed()
                    pg = None
            if pg is None and p.lower().endswith(".pdf"):
                try:
                    pg = PS.chunks_for(p, name)          # 2.57.0: sentences cut from the page, headers and footers left out
                except Exception:
                    diag.swallowed()
                    pg = None
            if pg is not None:
                fc.append((name, pg[0]))
                places[name] = pg[1]
            elif progress is not None and _takes_say(chunks_of):
                def pages(msg, k=k, head=head):
                    m = _PAGE.search(msg or "")
                    if m and int(m.group(2)):
                        a, b = int(m.group(1)), int(m.group(2))
                        say((k + min(a, b) / b) / n, f"{head} (page {a} of {b})")
                fc.append((name, chunks_of(p, pages)))   # 2.47.0: scanned pages too
            else:
                fc.append((name, chunks_of(p)))
            src.append([name, sha256(p), datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), os.path.abspath(p)])
        except Stopped:
            raise
        except Exception as ex:
            diag.swallowed()
            raise ReadFailed(name, ex)
    if stop is not None and stop():
        raise Stopped()
    say(len(paths) / n, "Finding the requirements in every sentence")
    heads = []
    items = C.extract(fc, heads)
    for name, pl in places.items():
        try:
            PS.place([it for it in items if it.get("file") == name], pl)
        except Exception:
            diag.swallowed()
    empty = [n_ for n_, ch in fc if not any(t for _l, t in ch)]
    say(1.0, "Read")
    return items, heads, src, empty


def new_matrix(path, items, heads, src, outline_text=""):
    """A compliance matrix from a read: the outline typed when the effort started, else the RFP's Section L headings,
    else any numbered headings."""
    M = C.Matrix(path, os.path.splitext(os.path.basename(path))[0].replace("_Compliance_Matrix", ""))
    M.items, M.headings, M.sources = items, heads, src
    typed = (outline_text or "").strip()
    M.outline = C.parse_outline(typed) if typed else (C.outline_from_headings(heads, "L") or C.outline_from_headings(heads, ""))
    M.log("matrix", f"read {len(src)} RFP file(s): {len(items)} candidates")
    M.pending = True
    return M


def text_check(M):
    """[result] of textcheck.check for each RFP file of the matrix (a file no longer on this PC is marked gone)."""
    import textcheck as TC
    out = []
    for s in M.sources:
        name = s[0] if s else ""
        path = s[3] if len(s) > 3 else ""
        if not path or not os.path.isfile(path):
            out.append({"file": name, "words": 0, "in_review": 0, "in_headings": 0, "missing": 0, "pct": 0, "lines": [], "gone": True})
            continue
        try:
            r = TC.check(path, [it for it in M.items if it.get("file") == name], M.headings)
        except Exception:
            diag.swallowed()
            r = {"file": name, "words": 0, "in_review": 0, "in_headings": 0, "missing": 0, "pct": 0, "lines": [], "error": True}
        r["path"] = path
        out.append(r)
    return out


def text_check_line(results):
    miss = sum(r["missing"] for r in results)
    words = sum(r["words"] for r in results)
    if not results:
        return ""
    if not miss:
        return f"Text check: all {words} words of the RFP files are in the review."
    return f"Text check: {miss} of {words} words in {sum(1 for r in results if r['missing'])} file(s) are not in the review yet."


def add_missing(M, results):
    """Add the text check's missing lines as sentences to assign, each where it is in the document (after the sentence
    before it, under the same RFP section, with its page). Returns the added rows."""
    import textcheck as TC
    added = []
    paths = {s[0]: s[3] for s in M.sources if s and len(s) > 3}
    for r in results:
        lines = [(where, line) for where, line, kind in r.get("lines", []) if kind == "missing"]
        if not lines:
            continue
        path = r.get("path") or paths.get(r["file"], "")
        pos, new_pos = {}, [None] * len(lines)
        if path and os.path.isfile(path):
            try:
                pos, new_pos = TC.positions(path, [it for it in M.items if it.get("file") == r["file"]], [ln for _w, ln in lines])
            except Exception:
                diag.swallowed()
        for (where, line), npos in zip(lines, new_pos):
            it = C.context_item(line, "", ("", ""), "")
            if not it:
                if not line.strip():
                    continue
                it = {"text": " ".join(line.split()), "lead": "", "section": "", "section_title": "", "actor": "",
                      "type": "Context", "strength": "", "suggest": "Context", "modal": "", "xrefs": "", "compound": False}
            pm = re.match(r"p\.(\d+)$", where or "")
            it.update({"file": r["file"], "loc": f"{r['file']} ({where}, added by the text check)", "page": int(pm.group(1)) if pm else None,
                       "context": line[:700], "key": C.text_key(line), "decision": "", "map": "", "owner": "", "status": "", "notes": "",
                       "response_page": "", "links": "", "new": "Added by the text check", "learned": "", "context_for": ""})
            at = TC.insert_at(M.items, r["file"], pos, npos)
            prev = M.items[at - 1] if at > 0 and M.items[at - 1].get("file") == r["file"] else None
            if prev is not None:
                it["section"], it["section_title"] = prev.get("section", ""), prev.get("section_title", "")
            it["id"] = f"__new{len(added)}"
            if npos is not None:
                pos[it["id"]] = npos
            M.items.insert(at, it)
            added.append(it)
    if added:
        for it in added:
            it["id"] = ""
        C.assign_ids(M.items)
        for it in added:
            M.log(it["id"], "added by the text check")
        M.pending = True
    return added


def complete(M):
    """Nothing missed: the text check's missing lines go into the review in place. Returns how many."""
    if M is None or not M.items:
        return 0
    try:
        res = text_check(M)
        if any(r["missing"] for r in res):
            return len(add_missing(M, res))
    except Exception:
        diag.swallowed()
    return 0


def add_read(M, items, heads, src):
    """More customer documents into an open matrix: a new file whole, and of a file already read only the sentences
    not in the review yet; decisions are kept. Returns the rows added."""
    have = {(it["file"], it["key"]) for it in M.items}
    known = {it["file"] for it in M.items}
    add = [it for it in items if it["file"] not in known or (it["file"], it["key"]) not in have]
    for it in add:
        it["id"] = ""
    M.items += add
    C.assign_ids(M.items)
    C.link_items(M.items)
    M.headings += heads
    M.sources += src
    M.log("matrix", f"added {len(src)} file(s): {len(add)} candidates")
    M.pending = True
    return add


def unread_docs(M, docs):
    """Of [(name, label, path)] the customer documents not in the matrix yet."""
    read = {os.path.normcase(r[3]) for r in M.sources if len(r) > 3 and r[3]}
    names = {r[0] for r in M.sources if r}
    return [x for x in docs if os.path.normcase(x[2]) not in read and os.path.basename(x[2]) not in names]


def effort_docs(ws):
    """The effort's customer documents (latest version of each) from Customer Documents: [(name, label, path)]."""
    import docversions as DV
    if ws is None:
        return []
    lib = DV.Library(ws.p("documents")).load()
    out = []
    for d in lib.docs:
        if d["versions"]:
            v = d["versions"][-1]
            p = v.get("path", "")
            if p and os.path.isfile(p) and p.lower().endswith((".docx", ".pdf", ".xlsx", ".pptx")):
                out.append((d["name"], v["label"], p))
    return out
