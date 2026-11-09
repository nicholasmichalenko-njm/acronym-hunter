"""What Verify decided (3.84.0): each block's role, each caption's link, which pages are verified and by whom, the
corrected readings of scanned lines, the menu, and the page each document was left on. Kept in verify.json in the
effort's working folder, one entry per document (by its file name, so a new version starts fresh only where its pages
changed).

Store(folder): doc(name) / set_role(name, keys, role) / set_link(name, caption, obj, confirmed) / verify(name, page, who)
    / reopen(name, page, who, why) / set_last(name, page) / set_reading(name, page, line, text) / save()
    3.90.0: a role, link or reading set stamps the document's "changed"; changed_after(store, name, when) says whether
    Verify changed what the reader reads after that time (Review's "read it again" line)
view(pdf, store, name, n) -> [block with "role", "decided", "flags", "link"]   (the page as Verify shows it)
page_flags(view) / can_verify(view) / status(pdf, store, name) -> ["verified"|"look"|"notyet"] per page
next_to_look(pdf, store, name, after) / section_of(view, key) / counts(pdf, store, name)
overrides(pdf, store, name) -> (lines to leave out, {(page index, line index): heading or not}) for the reader
Warn, never block: only a page's own Verified mark waits on its flags. Rules only; nothing leaves the PC."""
import datetime, os

import verifyblocks as VB
import verifyroles as VR

FILE = "verify.json"
FORMAT = 1
UNSURE = 0.80                     # a scanned line the reader is less sure of than this is a flag (a setting)


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _who(who=None):
    if who:
        return who
    try:
        import getpass
        return getpass.getuser()
    except Exception:  # noqa: BLE001
        return ""


class Store:
    def __init__(self, folder):
        self.folder = folder
        self.path = os.path.join(folder, FILE) if folder else ""
        self.data = {"format": FORMAT, "docs": {}, "menu": None, "unsure": UNSURE}
        if self.path:
            import workspace as W
            d = W.read_json(self.path, None)
            if isinstance(d, dict):
                self.data.update({k: v for k, v in d.items() if k in ("docs", "menu", "unsure")})
                self.data["docs"] = self.data.get("docs") or {}

    def save(self):
        if self.path:
            import workspace as W
            os.makedirs(self.folder, exist_ok=True)
            W.write_json(self.path, dict(self.data, format=FORMAT))

    def doc(self, name):
        d = self.data["docs"].setdefault(name, {})
        for k in ("roles", "links", "verified", "reopened", "readings", "splits"):
            d.setdefault(k, {})
        d.setdefault("last", 1)
        return d

    def menu(self, config_dir=None):
        return VR.menu(self.data.get("menu"), VR.load_team(config_dir) if config_dir else None)

    def set_menu(self, m):
        self.data["menu"] = VR.clean(m)
        self.save()

    def unsure(self):
        try:
            return float(self.data.get("unsure", UNSURE))
        except (TypeError, ValueError):
            return UNSURE

    # ------------------------------------------------------------ decisions
    def set_role(self, name, keys, role):
        d = self.doc(name)
        for k in keys:
            d["roles"][k] = role
        d["changed"] = _now()
        self.save()
        return len(keys)

    def set_link(self, name, cap, obj, confirmed=True):
        d = self.doc(name)
        if obj:
            d["links"][cap] = {"to": obj, "ok": bool(confirmed)}
        else:
            d["links"].pop(cap, None)
        d["changed"] = _now()
        self.save()

    def verify(self, name, page, who=None):
        d = self.doc(name)
        d["verified"][str(page)] = {"by": _who(who), "at": _now()}
        d["reopened"].pop(str(page), None)
        self.save()

    def unverify(self, name, page):
        d = self.doc(name)
        d["verified"].pop(str(page), None)
        self.save()

    def reopen(self, name, page, who=None, why=""):
        """A spot check reopens a verified page: amber on the strip, with who and why."""
        d = self.doc(name)
        d["reopened"][str(page)] = {"by": _who(who), "at": _now(), "why": (why or "").strip()}
        self.save()

    def set_last(self, name, page):
        d = self.doc(name)
        if d["last"] != page:
            d["last"] = page
            self.save()

    def set_split(self, name, key, head):
        """3.92.1: the heading at the start of a block, split off its text; "" says the block has none (the suggestion
        is put away). None takes the decision back."""
        d = self.doc(name)
        if head is None:
            d["splits"].pop(key, None)
        else:
            d["splits"][key] = " ".join(str(head).split())
        d["changed"] = _now()
        self.save()
        return d["splits"].get(key)

    def set_reading(self, name, page, line, text):
        """A scanned line's reading, confirmed (text as read) or corrected."""
        d = self.doc(name)
        d["readings"][f"{page}:{line}"] = " ".join((text or "").split())
        d["changed"] = _now()
        self.save()


def changed_after(store, name, when):
    """3.90.0: did Verify change this document's roles, links or readings after `when` ("YYYY-MM-DD HH:MM" or ISO)?
    Returns the time it changed, or ""."""
    d = (store.data.get("docs") or {}).get(name) or {}
    ch = (d.get("changed") or "").replace("T", " ")[:16]
    w = (when or "").replace("T", " ")[:16]
    return ch if ch and (not w or ch > w) else ""


# ------------------------------------------------------------------ the page as Verify shows it
def scan_lines(pdf, n):
    """The reader's lines on a scanned page: [{"line", "box", "text", "conf"}] (from the page copy's readings)."""
    try:
        import ocrpdf
        got = ocrpdf.readings_of(pdf).get(str(n)) or []
    except Exception:  # noqa: BLE001
        return []
    return [dict(r, line=i) for i, r in enumerate(got)]


def _over(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def view(pdf, store, name, n, m=None):
    m = m or store.menu()
    roles_m = VR.by_id(m)
    pages = VB.blocks(pdf)["pages"]
    if not (1 <= n <= len(pages)):
        return []
    d = store.doc(name)
    decided = d["roles"]
    roles = {b["key"]: decided.get(b["key"], b["suggest"]) for p in pages[max(0, n - 1):n + 1] for b in p["blocks"]}
    nxt = pages[n]["blocks"] if n < len(pages) else []
    unsure = [r for r in scan_lines(pdf, n) if float(r.get("conf", 1)) < store.unsure()
              and f"{n}:{r['line']}" not in d["readings"]]
    out = []
    for b in pages[n - 1]["blocks"]:
        role = roles[b["key"]]
        x = dict(b, role=role, decided=b["key"] in decided, flags=[], link=None)
        if not x["decided"] and not b["sure"]:
            x["flags"].append("Check this suggestion: " + b["why"])
        r = roles_m.get(role, {})
        if r.get("acts") == "caption":
            got = d["links"].get(b["key"])
            if got:
                x["link"] = {"to": got["to"], "ok": got["ok"]}
            else:
                sug = VB.nearest_object(pages[n - 1]["blocks"], b, r.get("object", "figure"), roles, nxt)
                x["link"] = {"to": sug, "ok": False} if sug else None
            if not x["link"]:
                x["flags"].append("Link this caption to its figure or table")
            elif not x["link"]["ok"]:
                x["flags"].append("Confirm what this caption names")
        import verifysplit as SPL                             # 3.92.1: a heading on the same line as its text
        x["split"] = d["splits"].get(b["key"])
        if x["split"] is None and VR.acts(m, role) in ("text", "bullet"):
            sug = SPL.runin(b.get("text", ""))
            if sug:
                x["split_suggest"] = sug
                x["flags"].append(f"Heading on the same line as its text? {sug}")
        for u in unsure:
            if b["lines"] and _over(b["box"], u["box"]):
                x["flags"].append(f"Check the reading: {u['text']}")
        out.append(x)
    return out


def page_flags(v):
    return [(b["key"], f) for b in v for f in b["flags"]]


def can_verify(v):
    return not page_flags(v)


def status(pdf, store, name, m=None):
    d = store.doc(name)
    out = []
    for p in VB.blocks(pdf)["pages"]:
        k = str(p["n"])
        if k in d["verified"] and k not in d["reopened"]:
            out.append("verified")
        elif k in d["reopened"] or page_flags(view(pdf, store, name, p["n"], m)):
            out.append("look")
        else:
            out.append("notyet")
    return out


def next_to_look(pdf, store, name, after, m=None):
    """The next page with something to look at after this one (wrapping round), or None."""
    st = status(pdf, store, name, m)
    order = list(range(after, len(st))) + list(range(0, after))
    for i in order:
        if st[i] == "look":
            return i + 1
    return None


def counts(pdf, store, name, m=None):
    st = status(pdf, store, name, m)
    return {"pages": len(st), "verified": st.count("verified"), "look": st.count("look"), "notyet": st.count("notyet")}


def section_of(v, key, m=None):
    """Select all text in this section: every Text and Bullet block under the nearest heading above the block (to the
    next heading)."""
    m = m or VR.defaults()
    keys = [b["key"] for b in v]
    if key not in keys:
        return []
    i = keys.index(key)
    start = 0
    for j in range(i, -1, -1):
        if VR.acts(m, v[j]["role"]) == "heading":
            start = j + 1
            break
    out = []
    for b in v[start:]:
        a = VR.acts(m, b["role"])
        if a == "heading":
            break
        if a in ("text", "bullet"):
            out.append(b["key"])
    return out


def splits(pdf, store, name):
    """3.92.1: {(page index, line index): heading text} for the blocks whose heading was split off its text."""
    d = store.data["docs"].get(name) or {}
    sp = {k: v for k, v in (d.get("splits") or {}).items() if v}
    if not sp:
        return {}
    out = {}
    for p in VB.blocks(pdf)["pages"]:
        for b in p["blocks"]:
            if b["key"] in sp and b["lines"]:
                out[(p["n"] - 1, b["lines"][0])] = sp[b["key"]]
    return out


def overrides(pdf, store, name, m=None):
    """What the reader does with Verify's decisions: lines to leave out (Running, Not needed, a figure or a table) and
    lines whose heading or not was decided. Only decided roles count; the reader's own rules do the rest."""
    m = m or store.menu()
    d = store.data["docs"].get(name) or {}
    roles = d.get("roles") or {}
    if not roles:
        return set(), {}
    skip, force = set(), {}
    for p in VB.blocks(pdf)["pages"]:
        for b in p["blocks"]:
            if b["key"] not in roles or not b["lines"]:
                continue
            a = VR.acts(m, roles[b["key"]])
            ls = [(p["n"] - 1, li) for li in b["lines"]]
            if a in ("running", "skip", "object"):
                skip.update(ls)
            else:
                for x in ls:
                    force[x] = a == "heading"
    return skip, force
