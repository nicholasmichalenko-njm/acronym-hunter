"""Effort Formatting (3.36.0): this effort's formatting on top of the Global Standards, on a page of its own under
Effort. The values efforts change most are up front (body, table and caption fonts and sizes, headings, paper and
margins, header and footer), each with the Global Standards value beside it, what the RFP says with Use it, Reset, and Make it
global. Changes apply to every volume of the effort or to one. Every setting opens the full Production Standards
editor on this effort's layer. Nothing here changes the Global Standards except Make it global. Rules only."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem,
                               QMenu, QScrollArea, QTableWidget, QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)
import diag
import effortformat as EFM
import prodrules as PRL
from . import design as D

FONTS = ("Arial", "Calibri", "Cambria", "Garamond", "Georgia", "Helvetica", "Segoe UI", "Times New Roman", "Verdana")
PAPERS = (("Letter", "Letter"), ("A4", "A4"), ("Legal", "Legal"), ("Tabloid", "Tabloid (11 x 17)"))
ONOFF = ((True, "On"), (False, "Off"))


def _show(v):
    if v is None or v == "":
        return "not set"
    if isinstance(v, bool):
        return "On" if v else "Off"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


class EffortFormatPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.rows, self._loading, self.rfp_map = {}, False, {}
        outer = QVBoxLayout(self); outer.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"])
        self.empty = D.EmptyState("Open an effort", "Effort Formatting holds one effort's formatting on top of the Global "
                                  "Standards. Open an effort from All Efforts.")
        outer.addWidget(self.empty)
        self.body = QWidget(); outer.addWidget(self.body, 1)
        bv = QVBoxLayout(self.body); bv.setContentsMargins(0, 0, 0, 0); bv.setSpacing(D.SPACE["m"])
        __import__("skqt.effortsetview", fromlist=["x"]).add_card(self, bv)   # 4.32.0: the effort's own set
        top = D.Card("Effort Formatting", "This effort's formatting. It starts from this effort's standards (Production "
                     "Standards) and keeps its own changes here, for every volume or for one.",
                     actions=[D.button("Every setting...", "primary", lambda: self.every_setting(),
                                       "The full Production Standards editor on this effort's formatting: every value, table and part")])
        self.band = QLabel(""); self.band.setTextFormat(Qt.RichText); self.band.setWordWrap(True); top.add(self.band)
        r1 = QHBoxLayout(); r1.setSpacing(D.SPACE["s"])
        r1.addWidget(D.label("This effort's type", "label", wrap=False))
        self.etype = QComboBox(); self.etype.setMinimumWidth(200); self.etype.activated.connect(lambda _i: self.set_etype())
        r1.addWidget(self.etype)
        r1.addWidget(D.label("Default volume", "label", wrap=False))
        self.dvol = QComboBox(); self.dvol.setMinimumWidth(200); self.dvol.activated.connect(lambda _i: self.set_dvol())
        r1.addWidget(self.dvol)
        r1.addWidget(D.label("Response type", "label", wrap=False))                   # 3.38.0 Rule 4
        self.resp = QComboBox(); self.resp.setMinimumWidth(170); self.resp.activated.connect(lambda _i: self.set_resp())
        self.resp.setToolTip("Rule 4: style names follow the response type (a style named with RFP is named RFI in an RFI)")
        r1.addWidget(self.resp)
        r1.addWidget(D.label("Changes apply to", "label", wrap=False))
        self.scope = QComboBox(); self.scope.setMinimumWidth(200); self.scope.activated.connect(lambda _i: self.fill())
        self.scope.setToolTip("Every volume of this effort, or one volume (the cost volume's tables, say)")
        r1.addWidget(self.scope); r1.addStretch(1)
        top.body.addLayout(r1)
        self.inherits = D.label("", "muted"); top.add(self.inherits)
        bv.addWidget(top)
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setFrameShape(QFrame.NoFrame); bv.addWidget(sc, 1)
        sc.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget(); sc.setWidget(inner)
        iv = QVBoxLayout(inner); iv.setContentsMargins(0, 0, 0, 0); iv.setSpacing(D.SPACE["m"])
        vals = D.Card("The values efforts change most", "The Global Standards value is in grey. Set this effort's own; Reset takes "
                      "it back to the Global Standards value. Where the RFP has a rule, it shows beside the value, in red when the value breaks it.")
        self.grid = QGridLayout(); self.grid.setHorizontalSpacing(D.SPACE["m"]); self.grid.setVerticalSpacing(D.SPACE["xs"])
        for c, h in enumerate(("", "Global Standards", "This effort", "The RFP says", "", "")):
            if h:
                self.grid.addWidget(D.label(h, "label", wrap=False), 0, c)
        r = 1
        last = None
        for key, group, label, _path, kind in EFM.FIELDS:
            if group != last:
                g = D.label(group, "label", wrap=False); g.setStyleSheet("padding-top:6px")
                self.grid.addWidget(g, r, 0, 1, 6); r += 1; last = group
            self.add_row(r, key, label, kind); r += 1
        for c, wd in ((0, 150), (1, 150), (2, 240)):
            self.grid.setColumnMinimumWidth(c, wd); self.grid.setColumnStretch(c, 0)
        self.grid.setColumnStretch(3, 1)
        vals.body.addLayout(self.grid)
        iv.addWidget(vals)
        ch = D.Card("Changed for this effort", "Everything this effort sets at this scope, with the Global Standards value.",
                    actions=[D.button("Open this effort's workbook", None, lambda: self.open_book(),     # 4.7.0
                                      "This effort's changes as a workbook beside its list: edit it in Excel; a blank cell means the default"),
                             D.button("Reset all", "ghost", lambda: self.reset_all(), "Every value at this scope back to the Global Standards value"),
                             D.button("Undo the last Make it a standard", "ghost", lambda: self.undo_keep(),
                                      "Put the Global Standards back as they were before the last Make it a standard")])
        self.changes = QLabel(""); self.changes.setTextFormat(Qt.RichText); self.changes.setWordWrap(True); ch.add(self.changes)
        iv.addWidget(ch)
        lp = D.Card("Library items this effort uses", "Covers, headers and footers, numbering, table looks: the Global Standards' "
                    "pinned version, a version this effort chose, or this effort's own copy (kept in the effort, never added "
                    "to the library unless you save it there).",
                    actions=[D.button("Choose versions or this effort's own...", None, lambda: self.every_setting(section="profile_parts"),
                                      "Every setting > Template profile > Parts and versions, on this effort")])
        self.parts = QTableWidget(0, 2); self.parts.setHorizontalHeaderLabels(["Part", "Comes from"])
        self.parts.verticalHeader().setVisible(False); self.parts.setEditTriggers(QTableWidget.NoEditTriggers)
        self.parts.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.parts.horizontalHeader().setStretchLastSection(True); self.parts.setMinimumHeight(220)
        lp.add(self.parts)
        iv.addWidget(lp)
        # 3.38.0: the one place an effort departs from a production rule
        rc = D.Card("Rules this effort follows", "The production rules (Team > Rules). Untick a rule this effort "
                    "departs from: Audit and Fix a Copy stop reporting it, for this effort only. A rule turned off for every "
                    "effort shows greyed.")                         # 3.75.0: the menu opens the Rules page
        self.rules_list = QListWidget(); self.rules_list.setMinimumHeight(260)
        self.rules_list.itemChanged.connect(lambda it: self.rule_ticked(it))
        rc.add(self.rules_list)
        iv.addWidget(rc)
        iv.addStretch(1)

    # ------------------------------------------------------------ one row
    def add_row(self, r, key, label, kind):
        self.grid.addWidget(D.label(label, None, wrap=False), r, 0)
        team = D.label("", "muted", wrap=False); team.setMaximumWidth(200); self.grid.addWidget(team, r, 1)
        if kind == "font":
            ed = QComboBox(); ed.setEditable(True); ed.addItem(""); ed.addItems(FONTS); ed.setMinimumWidth(180)
            ed.activated.connect(lambda _i, k=key: self.edited(k))
            ed.lineEdit().editingFinished.connect(lambda k=key: self.edited(k))
        elif kind in ("size", "inches"):
            ed = QDoubleSpinBox(); ed.setRange(0, 400 if kind == "size" else 5); ed.setDecimals(1 if kind == "size" else 2)
            ed.setSingleStep(0.5 if kind == "size" else 0.25); ed.setSpecialValueText("Standard"); ed.setMinimumWidth(110)
            ed.editingFinished.connect(lambda k=key: self.edited(k))
        elif kind in ("spacing", "position", "paper", "onoff"):
            ed = QComboBox(); ed.setMinimumWidth(160)
            ed.addItem("Standard", None)
            for v, t in {"spacing": EFM.SPACING, "position": EFM.POSITION, "paper": PAPERS, "onoff": ONOFF}[kind]:
                ed.addItem(t, v)
            ed.activated.connect(lambda _i, k=key: self.edited(k))
        else:
            ed = QLineEdit(); ed.setMinimumWidth(240); ed.editingFinished.connect(lambda k=key: self.edited(k))
            ed.setToolTip("Words and fields; Insert a field puts one where the cursor is")
        ed.setFixedWidth(240)
        if kind == "text" and key != "marking":         # 3.48.0: header and footer boxes get the field menu
            from .fieldpicker import FieldButton
            holder = QWidget(); hb = QHBoxLayout(holder); hb.setContentsMargins(0, 0, 0, 0); hb.setSpacing(D.SPACE["xs"])
            hb.addWidget(ed)
            fb = FieldButton(lambda: self.std_now(), [ed], text="Field")
            hb.addWidget(fb)
            self.grid.addWidget(holder, r, 2)
        else:
            self.grid.addWidget(ed, r, 2)
        rfp = D.label("", "muted"); rfp.setWordWrap(True); rfp.setMinimumWidth(160); self.grid.addWidget(rfp, r, 3)
        use = D.button("Use it", "ghost", lambda _=False, k=key: self.use_rfp(k), "This effort takes the RFP's value")
        reset = D.button("Reset", "ghost", lambda _=False, k=key: self.reset(k), "Back to the Global Standards value")
        box = QHBoxLayout(); box.setSpacing(D.SPACE["xs"]); box.addWidget(use); box.addWidget(reset)
        wbox = QWidget(); wbox.setLayout(box); self.grid.addWidget(wbox, r, 4)
        keep = QToolButton(); keep.setText("Make it a standard"); keep.setPopupMode(QToolButton.InstantPopup)
        keep.setToolTip("Write this effort's value into the Global Standards, for every effort that uses them")
        menu = QMenu(keep); keep.setMenu(menu)
        menu.aboutToShow.connect(lambda k=key, m=menu: self.fill_keep_menu(k, m))
        self.grid.addWidget(keep, r, 5)
        self.rows[key] = {"kind": kind, "team": team, "ed": ed, "rfp": rfp, "use": use, "reset": reset, "keep": keep}

    def tid(self):
        return self.scope.currentData() or None

    def std_now(self):
        """This effort's standard for the volume shown (the field menu lists its fill-ins)."""
        try:
            return EFM.effort_std(self.host.config_dir, self.host.ws, self.tid())
        except Exception:  # noqa: BLE001  the menu still lists the built-in fields
            return {}

    def read(self, key):
        row = self.rows[key]
        ed, kind = row["ed"], row["kind"]
        if kind == "font":
            return ed.currentText().strip() or None
        if kind in ("size", "inches"):
            v = ed.value()
            return None if v == ed.minimum() else round(v, 2)
        if kind in ("spacing", "position", "paper", "onoff"):
            return ed.currentData()
        return ed.text() if ed.text().strip() else None

    def show_row(self, key):
        row = self.rows[key]
        g = EFM.get(self.host.config_dir, self.host.ws, key, self.tid())
        ed, kind = row["ed"], row["kind"]
        ed.blockSignals(True)
        if kind == "font":
            ed.setEditText(g["effort"] or "")
            ed.lineEdit().setPlaceholderText(_show(g["team"]))
        elif kind in ("size", "inches"):
            try:
                ed.setValue(float(g["effort"]) if g["effort"] not in (None, "") else ed.minimum())
            except (TypeError, ValueError):
                ed.setValue(ed.minimum())
        elif kind in ("spacing", "position", "paper", "onoff"):
            ed.setItemText(0, f"Standard ({self._label(kind, g['team'])})")
            i = ed.findData(g["effort"]) if g["effort"] is not None else 0
            ed.setCurrentIndex(max(0, i))
        else:
            ed.setText(g["effort"] or "")
            ed.setPlaceholderText(_show(g["team"]))
        ed.blockSignals(False)
        row["team"].setText(self._label(kind, g["team"]))
        f = ed.font(); f.setBold(g["effort"] is not None); ed.setFont(f)
        rv = self.rfp_map.get(key)
        bad = EFM.breaks(g["shown"], key, self.rfp_map)
        t = D.tokens()
        if rv:
            row["rfp"].setText(f"<span style='color:{t['crit'] if bad else t['muted']}'>{rv[1]}"
                               + (" (this value breaks it)" if bad else "") + "</span>")
            row["rfp"].setTextFormat(Qt.RichText)
        else:
            row["rfp"].setText("")
        row["use"].setVisible(bool(rv) and str(rv[0]) != str(g["shown"]))
        row["reset"].setVisible(g["effort"] is not None)       # 3.75.0: only on a value this effort changed (house rule 8)
        row["keep"].setVisible(g["effort"] is not None)
        row["bad"] = bad

    def _label(self, kind, v):
        pairs = {"spacing": EFM.SPACING, "position": EFM.POSITION, "paper": PAPERS, "onoff": ONOFF}.get(kind)
        if pairs:
            return dict(pairs).get(v, _show(v))
        return _show(v)

    # ------------------------------------------------------------ changes
    def edited(self, key, value=...):
        """This effort's value for a field (value: tests). Returns what is in force."""
        if self._loading or self.host.ws is None:
            return None
        v = self.read(key) if value is ... else value
        cur = EFM.get(self.host.config_dir, self.host.ws, key, self.tid())
        if v == cur["effort"] or (v is not None and cur["effort"] is None and v == cur["team"] and self.rows[key]["kind"] not in ("text",)):
            self.show_row(key)
            return cur["shown"]
        g = EFM.set_value(self.host.config_dir, self.host.ws, key, v, self.tid())
        diag.activity("effort_format_set")
        self.after()
        return g["shown"]

    def use_rfp(self, key):
        rv = self.rfp_map.get(key)
        if rv:
            return self.edited(key, rv[0])
        return None

    def reset(self, key):
        return self.edited(key, None)

    def open_book(self):
        """4.7.0: this effort's formatting workbook (written now if it is not there yet)."""
        import teamlib as T
        h = self.host
        if h.ws is None or not getattr(h, "effort_path", ""):
            return None
        p = T.effort_book_path(h.effort_path, h.effort_name)
        if not __import__("os").path.isfile(p) or (h.ws.get("effort_book") or {}).get("dirty"):
            T.write_effort_book(h.ws, h.effort_path, h.effort_name)
        return __import__("skqt.teamlibview", fromlist=["x"])._open(p)

    def reset_all(self):
        if self.host.ws is None:
            return
        EFM.reset_all(self.host.ws, self.tid())
        diag.activity("effort_format_reset_all")
        self.after()

    def fill_keep_menu(self, key, menu):
        menu.clear()
        for target, words in EFM.targets(self.host.config_dir, self.host.ws, self.tid()):
            menu.addAction(words, lambda t=target, k=key: self.keep(k, t))

    def keep(self, key, target):
        """Make it global: this effort's value into a global layer. Returns the history entry."""
        if self.host.ws is None:
            return None
        e = EFM.keep_for_team(self.host.config_dir, self.host.ws, key, target, self.tid())
        if e:
            diag.activity("effort_format_kept_for_team")
            self.host.toast(f"Made a standard: {e['what']} is {_show(e['now'])}")
        self.after()
        return e

    def undo_keep(self):
        h = EFM.undo_last(self.host.config_dir)
        if h:
            self.host.toast(f"Put back: {h['what']} is {_show(h['was'])} in the standards again")
        else:
            self.host.status("Nothing made a standard to put back.")
        self.after()
        return h

    def after(self):
        self.fill()
        try:
            self.host.changed()
        except Exception:  # noqa: BLE001
            diag.swallowed()

    def every_setting(self, section=None):
        if self.host.ws is None:
            return False
        ok = self.host.prodstd_page.edit_effort(self.tid())
        if ok and section:
            try:
                import skqt.prodstdpage as PS
                keys = [k for k, _t in PS.SECTIONS]
                self.host.prodstd_page.show_section(keys.index(section))
            except Exception:  # noqa: BLE001
                diag.swallowed()
        return ok

    # ------------------------------------------------------------ the effort's type and volumes
    def set_etype(self, eid=None):
        if self.host.ws is None:
            return
        data = PRL.load(self.host.config_dir)
        eff = EFM.eff_of(self.host.ws)
        eff["effort_type"] = self.etype.currentData() or "" if eid is None else eid
        et = PRL.effort_type_of(data, eff["effort_type"])
        if et and eff.get("type") not in et["profiles"]:
            eff["type"] = et["default_profile"]
        self.host.ws.set("prod_std", eff)
        self.after()

    def set_resp(self):
        if self.host.ws is None:
            return
        eff = EFM.eff_of(self.host.ws)
        rt = self.resp.currentData() or ""
        if rt:
            eff["response_type"] = rt
        else:
            eff.pop("response_type", None)
        self.host.ws.set("prod_std", eff)
        self.after()

    def rule_ticked(self, it):
        if self._loading or self.host.ws is None:
            return
        import rulebook as RB
        RB.set_effort_on(self.host.ws, it.data(Qt.UserRole), it.checkState() == Qt.Checked)
        self.after()

    def fill_rules(self, data, eid):
        import rulebook as RB
        et = PRL.effort_type_of(data, eid)
        from_type = (et or {}).get("response_type") or PRL.STARTER_RESPONSE.get((et or {}).get("id"), "")
        eff = EFM.eff_of(self.host.ws)
        self.resp.clear()
        self.resp.addItem(f"From the effort type ({from_type})" if from_type else "Not set", "")
        for rt in RB.response_types():
            self.resp.addItem(rt, rt)
        self.resp.setCurrentIndex(max(0, self.resp.findData(eff.get("response_type") or "")))
        mine = set(RB.effort_off(self.host.ws))
        self.rules_list.clear()
        for r in RB.rules(self.host.config_dir):
            it = QListWidgetItem(f"{r['label']}  {r['text']}  ({RB.KEPT_NAME[r['kept']]})")
            it.setData(Qt.UserRole, r["id"])
            if not r["on"]:
                it.setFlags(it.flags() & ~Qt.ItemIsEnabled)
                it.setText(it.text() + "  Off for every effort")
                it.setCheckState(Qt.Unchecked)
            else:
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Unchecked if r["id"] in mine else Qt.Checked)
            self.rules_list.addItem(it)

    def set_dvol(self):
        if self.host.ws is None:
            return
        eff = EFM.eff_of(self.host.ws)
        eff["type"] = self.dvol.currentData()
        self.host.ws.set("prod_std", eff)
        self.after()

    # ------------------------------------------------------------ fill
    def refresh(self):
        on = self.host.ws is not None
        self.empty.setVisible(not on); self.body.setVisible(on)
        if not on:
            return
        try:
            from .custdocs import Ctx
            self.rfp_map = EFM.rfp(Ctx(self.host).reg.rows())
        except Exception:  # noqa: BLE001
            diag.swallowed()
            self.rfp_map = {}
        self.fill(); __import__("skqt.effortsetview", fromlist=["x"]).show(self)

    def fill(self):
        if self.host.ws is None:
            return
        self._loading = True
        try:
            data, eid, default, vols = EFM.ids(self.host.config_dir, self.host.ws)
            t = D.tokens()
            self.band.setText(f"<div style='background:{t['warn_soft']};color:{t['text']};padding:6px 10px;border-radius:6px'>"
                              f"<b>Formatting for {self.host.effort_name} only.</b> Nothing here changes the Global Standards or "
                              f"the template library, unless you choose Make it a standard.</div>")
            self.etype.clear(); self.etype.addItem("None (volumes only)", "")
            for e in data.get("effort_types", []):
                self.etype.addItem(e["name"], e["id"])
            self.etype.setCurrentIndex(max(0, self.etype.findData(eid or "")))
            self.fill_rules(data, eid)
            self.dvol.clear()
            for pid in vols:
                self.dvol.addItem(PRL.type_of(data, pid)["name"], pid)
            self.dvol.setCurrentIndex(max(0, self.dvol.findData(default)))
            cur = self.scope.currentData()
            self.scope.clear(); self.scope.addItem("Every volume", "")
            for pid in vols:
                self.scope.addItem(PRL.type_of(data, pid)["name"], pid)
            self.scope.setCurrentIndex(max(0, self.scope.findData(cur or "")))
            et = PRL.effort_type_of(data, eid)
            prof = PRL.type_of(data, self.tid() or default)["name"]
            self.inherits.setText("Starts from: the Global Standards > the " + prof + " profile"
                                  + (f" > the {et['name']} effort type" if et else "")
                                  + (" > this effort's values for every volume" if self.tid() else "") + ".")
            for key in self.rows:
                self.show_row(key)
            ch = EFM.changed(self.host.config_dir, self.host.ws, self.tid())
            if ch:
                self.changes.setText("".join(f"<div style='margin:2px 0'><b>{_esc(w)}</b>: Global Standards {_esc(_show(a))}, "
                                             f"this effort's <b>{_esc(_show(b))}</b></div>" for w, a, b in ch[:60])
                                     + (f"<div>and {len(ch) - 60} more</div>" if len(ch) > 60 else ""))
            else:
                self.changes.setText(f"<span style='color:{t['muted']}'>Nothing yet: every value is the Global Standards one.</span>")
            pr = EFM.parts(self.host.config_dir, self.host.ws, self.tid())
            self.parts.setRowCount(len(pr))
            for i, (_slot, what, src) in enumerate(pr):
                self.parts.setItem(i, 0, QTableWidgetItem(what))
                it = QTableWidgetItem(src)
                if src.startswith("This effort"):
                    f = it.font(); f.setBold(True); it.setFont(f)
                self.parts.setItem(i, 1, it)
        except Exception:  # noqa: BLE001
            diag.swallowed()
        finally:
            self._loading = False


def _esc(x):
    s = str(x)
    s = s if len(s) < 90 else s[:87] + "..."
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
