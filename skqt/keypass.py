"""Shred in passes, the Submission Formatting Requirements pass on the screen (4.82.0; step K1 of
claude/stationkeeper-key-dates-and-the-submission-formatting-pass-direction-2026-11-25.md). The Shred page in the
pass's own mode (the Compliance pass's page and bar, skqt/comppass.py), with its buttons on 1 to 4 in the agreed order:
How to Submit, Submission Formatting Requirement, Page Limit Requirement, Key Date. In K1 only 4, Key Date, is built,
so only it is shown (decision 187: no control that cannot be used).

Key Date (4, or D): the bar shows the date, time and time zone the app read from the words, editable, and asks one
thing: the kind, with the app's reading as the suggestion Enter takes (1 to 7 pick while it asks). Proposal due and
Questions due fill Customer information; the other kinds go on the calendar. A one-date kind already holding another
date asks once on the bar: Replace (Enter) or Keep the earlier. The same key on a marked piece takes the mark off.
Rules only; nothing leaves the PC."""
from PySide6.QtWidgets import QLabel, QLineEdit

import diag
import keydatemark as KM
from . import design as D

KEY = "subpass"
NUMBER = 4                       # Key Date's place among the pass's four buttons


def _who():
    try:
        import effort as E
        return E.user_name()
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return None


def _later(page):
    __import__("skqt.shredselbar", fromlist=["x"]).later(page)


def _fit(lab):
    """A wrapped line keeps to the pass's margin, so the bar never runs past the window's edge."""
    from . import comppass as CP
    from .shredselbar import GAP
    lab.setWordWrap(True); lab.setMaximumWidth(CP.WIDE - 2 * GAP - 12)
    return lab


def asking(page, rows):
    """The Key Date question open for exactly the selected piece, or None."""
    a = getattr(page, "_key_ask", None)
    return a if a and len(rows) == 1 and a["ids"] == [rows[0]["id"]] else None


def _when_line(v):
    return KM.when_text(v) if v else ""


def buttons(page, f, rows, M, it, one, col):
    """The pass's own buttons on the bar beside the piece. Returns "ask" when the bar holds only the question."""
    from . import comppass as CP
    f.kinds, f.keyd, f.cal_link, f.cal_line, f.before, f.reads = {}, None, None, None, None, None
    f.key_edit, f.key_kinds, f.key_name, f.key_ok, f.replace, f.keep = None, {}, None, None, None, None
    a = asking(page, rows)
    if a and a.get("stage") == "replace":
        cur = a["cur"]
        lab = QLabel(f"{KM.NAME[a['key']]} is already {cur['text']}" + (f" ({cur['from']})" if cur.get("from") else "")
                     + f". Replace it with {_when_line(a['v'])}?"); _fit(lab)
        col.addWidget(lab)
        f.replace = D.button("Replace  Enter", "primary", lambda: take(page, replace=True), "The newer date is the one shown; the calendar says what it replaced")
        f.keep = D.button("Keep the earlier", None, lambda: take(page, replace=False), "The earlier date stays; this piece is marked a key date all the same")
        col.addWidget(f.replace); col.addWidget(f.keep)
        col.addWidget(D.button("Cancel  Esc", "ghost", lambda: cancel(page)))
        return "ask"
    if a and a.get("stage") == "name":
        lab = QLabel("Other. What is it?"); _fit(lab)
        col.addWidget(lab)
        f.key_name = QLineEdit(a.get("name", ""))
        f.key_name.setPlaceholderText("Pre-proposal conference, Award, ...")
        f.key_name.textChanged.connect(lambda t, a=a: a.__setitem__("name", t))
        f.key_name.returnPressed.connect(lambda: take(page))
        col.addWidget(f.key_name)
        for n, name in enumerate(KM.own_names(CP.rec_of(page))[:5]):     # names given to Other before, in this effort
            b = D.button(name, "ghost", lambda _c=False, x=name: name_pick(page, x), "Given to Other before in this effort")
            b.setStyleSheet("text-align:left;")
            col.addWidget(b)
        f.key_ok = D.button("Add to the calendar  Enter", "primary", lambda: take(page), "On the effort's calendar at once")
        col.addWidget(f.key_ok)
        col.addWidget(D.button("Cancel  Esc", "ghost", lambda: cancel(page)))
        f.key_name.setFocus()
        return "ask"
    if a:
        lab = QLabel("Key Date. The date:"); _fit(lab)
        col.addWidget(lab)
        f.key_edit = QLineEdit(a.get("typed", _when_line(a.get("v"))))
        f.key_edit.setPlaceholderText("Mar 1, 2027, 2:00 p.m. ET")
        f.key_edit.setToolTip("The date, time and time zone the app read from the words. Change it if it read them wrong; "
                              "a date it could not read is typed here")
        f.key_edit.textChanged.connect(lambda t, a=a: a.__setitem__("typed", t))    # what is typed outlives a redraw of the bar
        f.key_edit.returnPressed.connect(lambda: take(page))
        col.addWidget(f.key_edit)
        col.addWidget(QLabel("Its kind:"))
        for n, (key, name) in enumerate(KM.KINDS, 1):
            lead = key == a.get("sugg")
            b = D.button(f"{n}   {name}" + ("  Enter" if lead else ""), "primary" if lead else None,
                         lambda _c=False, k=key: pick(page, k), f"{name} ({n})" + (": the app's reading. Enter takes it" if lead else ""))
            b.setStyleSheet("text-align:left;")
            col.addWidget(b); f.key_kinds[key] = b
        col.addWidget(D.button("Cancel  Esc", "ghost", lambda: cancel(page)))
        return "ask"
    d = KM.of_piece(M, it) if one else None
    f.keyd = D.button(f"{NUMBER}   Key Date", None, lambda: start(page), "A date the customer sets: say its kind and it is on the calendar at once (4 or D)")
    f.keyd.setCheckable(True); f.keyd.setChecked(d is not None); f.keyd.setProperty("sk_switch", True)
    f.keyd.setStyleSheet("text-align:left;")
    col.addWidget(f.keyd); f.kinds["keydate"] = f.keyd
    if d is not None:
        name = d.get("name") or KM.NAME.get(d.get("kind"), "Key date")
        if d.get("eid") == "fact":
            where = "Customer information"
        elif d.get("eid"):
            where = "the calendar"
        else:
            where = "kept the earlier date"
        txt = f"{name}, {_when_line(d)}: " + ("on the calendar and in Customer information" if where == "Customer information"
                                             else "on the calendar" if where == "the calendar" else "the earlier date was kept")
        f.cal_line = _fit(QLabel(txt + "."))
        col.addWidget(f.cal_line)
        f.cal_link = D.button("Open the calendar", "ghost", lambda _c=False, x=dict(d): open_calendar(page, x), "Opens the calendar on that day")
        f.cal_link.setStyleSheet("text-align:left;")
        col.addWidget(f.cal_link)
    elif one and KM.older(M, it):
        f.before = _fit(QLabel("Marked Key Date before, kind not said. Press 4 to say its kind."))
        col.addWidget(f.before)
    elif one:
        v = KM.read(it.get("text", ""))
        if v:
            f.reads = QLabel(f"Reads as a date: {KM.when_text(v)}" + (f", {KM.NAME[v['kind']]}" if v.get("kind") else "")
                             + ". Enter or 4 to mark it."); _fit(f.reads)
            f.reads.setStyleSheet(f"color:{D.tokens()['muted']};")
            col.addWidget(f.reads)
    return f


def start(page):
    """4 or D: on a marked piece the mark comes off; otherwise the bar asks the kind, the app's reading suggested."""
    from . import comppass as CP
    M = CP.M_of(page)
    rows = page.selected() if M is not None and page.cx is None else []
    if len(rows) != 1:
        page.host.status("Select the one piece that holds the date." if rows else "Select the piece that holds the date first.")
        return None
    it = rows[0]
    if KM.of_piece(M, it) is not None:
        out = KM.unmark(CP.rec_of(page), M, it)
        _changed(page)
        CP.done(page, "The key date is off. Customer information keeps the value: change it there." if out == "fact"
                else "The key date is off, and off the calendar.")
        return "off"
    v = KM.read(it.get("text", ""))
    page._key_ask = {"ids": [it["id"]], "v": v, "sugg": (v or {}).get("kind", ""), "stage": "kind"}
    if v is None:
        page.host.status("No date was read in these words: type it on the bar.")
    _later(page)
    return "ask"


def name_pick(page, name):
    a = getattr(page, "_key_ask", None)
    if a:
        a["name"] = name
        return take(page)
    return None


def pick(page, key):
    """A kind's button, or its number while the bar asks."""
    a = getattr(page, "_key_ask", None)
    if not a or a.get("stage") != "kind":
        return None
    a["key"] = key
    if key == "other":
        a["stage"], a["name"] = "name", a.get("name", "")
        _later(page)
        return "name"
    return take(page)


def _typed(page, a):
    """The date as the bar holds it: what was typed, else what was read."""
    f = getattr(page, "sel_bar", None)
    if f is not None and getattr(f, "key_edit", None) is not None:
        a["typed"] = f.key_edit.text()
    if "typed" in a and " ".join(a["typed"].split()) != _when_line(a.get("v")):
        return KM.when_of(a["typed"])
    return a.get("v")


def _changed(page):
    try:
        page.R.M.pending = True
        page.host.changed()
    except Exception:  # noqa: BLE001
        diag.swallowed()


def take(page, replace=None):
    """Enter: the suggested kind (or the one picked), then the name for Other, then Replace or Keep when asked."""
    from . import comppass as CP
    M = CP.M_of(page)
    rows = page.selected() if M is not None else []
    a = asking(page, rows)
    if not a:
        return None
    if a.get("stage") == "kind":
        a["v"] = _typed(page, a)
        if not a.get("v"):
            page.host.status("No date there: write it like Mar 1, 2027, 2:00 PM ET.")
            return None
        a["key"] = a.get("key") or a.get("sugg")
        if not a["key"]:
            page.host.status("Say its kind: press 1 to 7.")
            return None
        if a["key"] == "other":
            a["stage"] = "name"
            _later(page)
            return "name"
    if a.get("stage") == "name":
        f = getattr(page, "sel_bar", None)
        if f is not None and getattr(f, "key_name", None) is not None:
            a["name"] = f.key_name.text()
        if not " ".join((a.get("name") or "").split()):
            page.host.status("Give it a name: what is on that date?")
            return None
    if a.get("stage") == "replace" and replace is None:
        replace = True
    return _file(page, M, rows[0], a, replace)


def _source(page, it):
    try:
        _t, src = page.capture_source()
    except Exception:  # noqa: BLE001
        diag.swallowed(); src = {}
    return {"doc": (src or {}).get("doc", "") or it.get("file", "") or page.file, "page": (src or {}).get("page", ""),
            "loc": (src or {}).get("loc", ""), "sid": it["id"]}


def _file(page, M, it, a, replace):
    from . import comppass as CP
    from . import sharedfacts as SF
    import custinfo as CI
    key, v, rec = a["key"], a["v"], CP.rec_of(page)
    src = _source(page, it)
    name = " ".join((a.get("name") or "").split())
    if key in KM.FACT:
        label = KM.FACT[key]
        out = SF.set_fact(page.host, label, KM.fact_value(v), "captured", src, replace)
        if isinstance(out, dict):
            cur = out["ask"]
            a.update({"stage": "replace", "cur": {"text": cur.get("value", ""), "from": CI.where(cur)}})
            _later(page)
            return "replace"
        if out in SF.MESSAGES:
            return None
        if replace is False:
            KM.mark(M, it, key, v, eid="")
            msg = f"{label}: the earlier date is kept. This piece is marked a key date."
        else:
            was = a.get("cur", {}).get("text", "") if replace else ""
            if was:
                rec = CP.rec_of(page)
                (rec.data.get("customer_facts") or {}).setdefault(label, {})["was"] = was
                rec.save()
            KM.mark(M, it, key, v, eid="fact", was=was)
            msg = f"{label}, {KM.when_text(v)}: on the calendar and in Customer information."
    else:
        e = KM.earlier(rec, key, it["id"])
        if e is not None and replace is None and (e.get("date"), e.get("start", ""), e.get("zone", "")) != (v["date"], v.get("start", ""), v.get("zone", "")):
            a.update({"stage": "replace", "cur": {"text": KM.when_text(e), "from": e.get("key_doc", "")}})
            _later(page)
            return "replace"
        if e is not None and (replace is False or (e.get("date"), e.get("start", ""), e.get("zone", "")) == (v["date"], v.get("start", ""), v.get("zone", ""))):
            KM.mark(M, it, key, v, name, eid="")
            msg = f"{KM.NAME[key]}: the date already on the calendar is kept. This piece is marked a key date."
        else:
            eid = KM.file_event(rec, M, it, key, v, name, src, replace=e if replace else None, who=_who())
            if not eid:
                page.host.status("Not on the calendar: the date could not be read. Write it like Mar 1, 2027, 2:00 PM ET.")
                return None
            KM.mark(M, it, key, v, name, eid=eid, was=KM.when_text(e) if (e is not None and replace) else "")
            msg = f"{name or KM.NAME[key]}, {KM.when_text(v)}: on the calendar."
    page._key_ask = None
    diag.activity("key_date_marked")
    _changed(page)
    CP.done(page, msg)
    page.view.setFocus()
    return key


def cancel(page):
    page._key_ask = None
    _later(page)
    page.view.setFocus()


def number(page, n):
    """1 to 7 while the bar asks pick a kind; otherwise 4 is Key Date and 1 to 3 are not built yet."""
    a = getattr(page, "_key_ask", None)
    if a and a.get("stage") == "kind" and 0 <= n < len(KM.KINDS):
        return pick(page, KM.KINDS[n][0])
    if n == NUMBER - 1:
        return start(page)
    page.host.status("Key Date (4) is the one button of this pass for now.")
    return None


def enter(page):
    """Enter: the question's answer while the bar asks; on a piece whose words hold a date and that is not marked, Key
    Date with the app's reading; otherwise the next piece with a date."""
    from . import comppass as CP
    M = CP.M_of(page)
    rows = page.selected() if M is not None else []
    if getattr(page, "_key_ask", None):
        if asking(page, rows):
            return take(page)
        page._key_ask = None
    if len(rows) == 1 and KM.of_piece(M, rows[0]) is None and rows[0].get("id") not in KM.marks(M) \
            and (KM.reads_like(rows[0]) or KM.older(M, rows[0])):
        return start(page)
    return CP.go_next(page)


def open_calendar(page, d):
    """The bar's line under a marked piece: the calendar, on that day."""
    import datetime
    h = page.host
    h.go("calendar")
    try:
        h.calendar_page.pick(datetime.date.fromisoformat(d.get("date", "")))
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return d.get("date", "")


def open_source(host, src):
    """The calendar's way back: Shred > Submission Formatting Requirements, on the piece the date came from."""
    host.go(KEY)
    try:
        host.assign_page.select(src["sid"])
    except Exception:  # noqa: BLE001
        diag.swallowed()
        return False
    return True
