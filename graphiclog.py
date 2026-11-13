"""The graphics log (4.25.5; Nicholas's recording 2026-11-12 10:00 to 11:15; the Documents board, step E): one row per
graphic, the customer's and ours, so "did we read its words and sweep its acronyms, on this version" is answered at a
glance. The rows come from three places that already exist: a document that is a picture (or filed as a graphic), a
picture the scan found terms in inside a document, and a graphic need tagged in Shred. Two marks per row: its words read
(a person confirms the reading) and its acros and abs swept (the page's Page done mark from Acros & Abs). Both are kept
by the file's name, so a new version, which is a new file, starts with neither. Standard library only; rules only."""
import os

WORDS_KEY = "graphic_words_ok"
PICTURE_EXTS = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp", ".svg", ".emf", ".wmf")
CUSTOMER_SIDE = ("customer", "bidders", "qa")
INSIDE_MARKS = (", image ", ", vector ")
COLUMNS = ["Graphic", "In", "Source", "Version", "Owner", "Status", "Words read", "Acronyms"]
FILTERS = (("", "Every graphic"), ("customer", "Customer"), ("ours", "Internal"), ("need", "Needs"), ("todo", "Left to do"))


def is_graphic(d):
    """A document that is a graphic: filed as one, or its newest file is a picture."""
    vs = d.get("versions") or []
    ext = os.path.splitext(vs[-1].get("file", ""))[1].lower() if vs else ""
    return d.get("category") == "graphics" or ext in PICTURE_EXTS


def words_ok(ws):
    return set((ws.get(WORDS_KEY, []) if ws is not None else []) or [])


def set_words_ok(ws, keys, on=True):
    s = words_ok(ws)
    for k in keys:
        (s.add if on else s.discard)(k)
    if ws is not None:
        ws.set(WORDS_KEY, sorted(s))
    return s


def _acros(pages, scanned, done, file):
    """(text, state, the keys its mark is kept under): swept, to decide, decided, none found, not scanned."""
    keys = [p["key"] for p in pages] or [file]
    left = sum(p["to_decide"] for p in pages)
    if all(k in done for k in keys):
        return "Swept", "swept", keys
    if pages:
        return (f"{left} to decide" if left else "Decided, not marked swept"), ("decide" if left else "decided"), keys
    return ("None found, not marked swept", "none", keys) if scanned else ("Not scanned", "not", keys)


def rows(lib, pages=(), scanned=(), done=(), confirmed=(), needs=()):
    """Every row of the log. pages: acrpages.pages(results); scanned: the file names of the last scan; done: the Page
    done marks; confirmed: the words-read marks; needs: graphics.items(rec)."""
    done, confirmed, scanned = set(done or ()), set(confirmed or ()), {os.path.basename(str(x)) for x in (scanned or ())}
    by_file = {}
    for p in pages or ():
        by_file.setdefault(p["name"], []).append(p)
    out, seen_files = [], set()
    docs = list(lib.all) if lib is not None else []
    for d in docs:
        vs = d.get("versions") or []
        if not vs or d.get("withdrawn") or not is_graphic(d):
            continue
        f = vs[-1].get("file", "")
        seen_files.add(f)
        text, state, keys = _acros(by_file.get(f, []), f in scanned, done, f)
        read = bool(by_file.get(f)) or f in scanned
        out.append({"kind": "file", "id": "doc:" + d["id"], "doc": d["id"], "name": d.get("name") or f, "where": "A file of its own",
                    "side": "customer" if d.get("category", "customer") in CUSTOMER_SIDE else "ours",
                    "version": vs[-1].get("label") or "", "versions": len(vs), "owner": "", "status": "",
                    "words": "Confirmed" if all(k in confirmed for k in keys) else ("Read, not confirmed" if read else "Not read"),
                    "words_ok": all(k in confirmed for k in keys), "acros": text, "acros_state": state, "keys": keys,
                    "page": (by_file.get(f) or [{}])[0].get("key", ""), "file": f})
    for d in docs:
        vs = d.get("versions") or []
        if not vs or d.get("withdrawn"):
            continue
        f = vs[-1].get("file", "")
        if f in seen_files:
            continue
        for p in by_file.get(f, []):
            if not any(m in p["key"] for m in INSIDE_MARKS):
                continue
            k = p["key"]
            left = p["to_decide"]
            out.append({"kind": "inside", "id": "page:" + k, "doc": d["id"], "name": p["label"], "where": d.get("name") or f,
                        "side": "customer" if d.get("category", "customer") in CUSTOMER_SIDE else "ours",
                        "version": vs[-1].get("label") or "", "versions": len(vs), "owner": "", "status": "",
                        "words": "Confirmed" if k in confirmed else "Read, not confirmed", "words_ok": k in confirmed,
                        "acros": "Swept" if k in done else (f"{left} to decide" if left else "Decided, not marked swept"),
                        "acros_state": "swept" if k in done else ("decide" if left else "decided"), "keys": [k], "page": k, "file": f})
    for g in needs or ():
        out.append({"kind": "need", "id": "need:" + g.get("id", ""), "doc": "", "name": g.get("concept", ""),
                    "where": g.get("section") or g.get("doc") or "", "side": "ours", "version": "", "versions": 0,
                    "owner": g.get("owner", ""), "status": g.get("status", "Needed"), "words": "", "words_ok": True,
                    "acros": "", "acros_state": "", "keys": [], "page": "", "file": "", "need": g.get("id", ""),
                    "type": g.get("kind", "")})
    return out


def todo(r):
    """The row still needs someone: a need not done, words not confirmed, or acros and abs not swept."""
    if r["kind"] == "need":
        return r["status"] != "Done"
    return not r["words_ok"] or r["acros_state"] != "swept"


def shown(rs, flt="", text=""):
    t = (text or "").casefold().strip()
    out = []
    for r in rs:
        if flt == "need" and r["kind"] != "need":
            continue
        if flt in ("customer", "ours") and (r["side"] != flt or r["kind"] == "need"):
            continue
        if flt == "todo" and not todo(r):
            continue
        if t and t not in (r["name"] + " " + r["where"] + " " + r["owner"]).casefold():
            continue
        out.append(r)
    return out


def counts(rs):
    """(graphics, words still to confirm, still to sweep, needs open)."""
    gs = [r for r in rs if r["kind"] != "need"]
    return (len(gs), sum(1 for r in gs if not r["words_ok"]), sum(1 for r in gs if r["acros_state"] != "swept"),
            sum(1 for r in rs if r["kind"] == "need" and r["status"] != "Done"))
