"""One deliverable's own page (3.62.0): double-click a deliverable on the board or in the list. Overview, format and
submission (its format group, its own values), parts and people (its Structure sections and its own parts),
requirements, attachments and files, discussion, and its dates. The rules are deliverables' and delivmore's."""
import html
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, QPlainTextEdit, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget, QHeaderView, QListWidget, QListWidgetItem)
import diag
import deliverables as DL
import delivmore as DM
from . import design as D
from .adaptive import FlowLayout

TABS = ("Overview", "Format and submission", "Parts and people", "Requirements", "Attachments and files", "Discussion", "Dates")


def _clear(lay):
    while lay.count():
        it = lay.takeAt(0)
        if it.widget() is not None:
            it.widget().setParent(None)
        elif it.layout() is not None:
            _clear(it.layout())


def _table(cols, rows, stretch=0):
    t = QTableWidget(len(rows), len(cols)); t.setHorizontalHeaderLabels(cols)
    t.verticalHeader().setVisible(False); t.setEditTriggers(QTableWidget.NoEditTriggers)
    t.setSelectionBehavior(QTableWidget.SelectRows); t.setSelectionMode(QTableWidget.SingleSelection)
    t.horizontalHeader().setSectionResizeMode(stretch, QHeaderView.Stretch)
    for i, r in enumerate(rows):
        for j, v in enumerate(r):
            t.setItem(i, j, QTableWidgetItem(str(v or "")))
    t.setMinimumHeight(min(320, 44 + 28 * max(2, len(rows))))
    return t


class DeliverableView(QWidget):
    def __init__(self, page):
        super().__init__()
        self.page, self.host = page, page.host
        self.did = None
        v = QVBoxLayout(self); v.setContentsMargins(0, 0, 0, 0); v.setSpacing(D.SPACE["s"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        self.back = D.button("< All deliverables", "ghost", lambda: page.close_deliverable())
        top.addWidget(self.back)
        self.title = D.label("", "title"); top.addWidget(self.title, 1)
        self.kind_pill = D.Pill("", "accent"); top.addWidget(self.kind_pill)
        self.state_pill = D.Pill("", "ok"); top.addWidget(self.state_pill)
        self.delete_btn = D.button("Delete this deliverable...", "ghost", lambda: page.remove(self.did),
                                   "Delete it, with its parts, attachments, dates and discussion (Undo puts it back)")
        top.addWidget(self.delete_btn)                                  # 4.12.0
        self.tabs = QTabWidget(); v.addWidget(self.tabs, 1)
        self.panes = {}
        from PySide6.QtWidgets import QScrollArea, QFrame
        for name in TABS:
            sa = QScrollArea(); sa.setWidgetResizable(True); sa.setFrameShape(QFrame.NoFrame)
            w = QWidget(); lay = QVBoxLayout(w); lay.setAlignment(Qt.AlignTop); lay.setSpacing(D.SPACE["s"])
            sa.setWidget(w)
            self.tabs.addTab(sa, name)
            self.panes[name] = lay
        self.tabs.currentChanged.connect(lambda _i: self.fill_tab())

    # ------------------------------------------------------------ data
    @property
    def rec(self):
        return self.page.ctx.rec if self.page.ctx is not None else None

    @property
    def M(self):
        return self.host.review.M if self.host.review is not None else None

    def d(self):
        return DL.get(self.rec, self.did) if self.rec is not None and self.did else None

    def show(self, did, tab=None):
        self.did = did
        d = self.d()
        if d is None:
            return False
        self.title.setText(d["name"])
        self.kind_pill.setText(d.get("kind") or "Deliverable")
        self.state_pill.setText(d.get("status") or "Not started")
        if tab:
            self.tabs.setCurrentIndex(TABS.index(tab))
        self.fill_tab()
        diag.activity("deliverable_page_opened")
        return True

    def tab(self):
        return TABS[self.tabs.currentIndex()]

    def fill_tab(self):
        d = self.d()
        if d is None:
            return
        name = self.tab()
        lay = self.panes[name]
        _clear(lay)
        getattr(self, "_" + name.split()[0].lower())(lay, d)

    def saved(self, tab=None):
        self.page.refresh()
        self.show(self.did, tab)

    # ------------------------------------------------------------ Overview
    def _overview(self, lay, d):
        f = QFormLayout(); f.setSpacing(D.SPACE["s"]); lay.addLayout(f)
        self.e_name = QLineEdit(d["name"]); f.addRow("Name", self.e_name)
        self.e_kind = QComboBox(); self.e_kind.addItems(DL.KINDS); self.e_kind.setCurrentText(d.get("kind") or "Other"); f.addRow("Type", self.e_kind)
        self.e_status = QComboBox(); self.e_status.addItems(DL.STATUSES); self.e_status.setCurrentText(d.get("status") or "Not started")
        f.addRow("Status", self.e_status)
        from .people import name_combo
        self.e_owner = name_combo(self.host, d.get("owner", "")); f.addRow("Owner", self.e_owner)
        self.e_due = QLineEdit((d.get("due") or "")[:10]); self.e_due.setPlaceholderText("YYYY-MM-DD"); f.addRow("Due", self.e_due)
        self.e_source = QComboBox(); self.e_source.addItems(["", "Named by the customer", "Ours"])
        self.e_source.setCurrentText(d.get("source") or ("Named by the customer" if d.get("req_key") else "")); f.addRow("Where it comes from", self.e_source)
        self.e_about = QPlainTextEdit(d.get("about", "")); self.e_about.setPlaceholderText("What it is and what it must do"); self.e_about.setMaximumHeight(90)
        f.addRow("Overview", self.e_about)
        self.e_guide = QPlainTextEdit(d.get("guidelines", "")); self.e_guide.setPlaceholderText("The customer's instructions for it, and ours")
        self.e_guide.setMaximumHeight(110); f.addRow("Guidelines", self.e_guide)
        row = QHBoxLayout(); lay.addLayout(row)
        row.addWidget(D.button("Save", "primary", lambda: self.save_overview()))
        row.addStretch(1)
        # the customer's words that apply
        rows = self.page.ctx.reg.rows() if self.page.ctx is not None else []
        vols = self.page.ctx.volumes() if self.page.ctx is not None else []
        app = [r for r in rows if not r.get("hidden") and DL._applies(r.get("subject", ""), d, vols)][:12]
        if app:
            lay.addWidget(D.SectionTitle("What the customer documents say about it"))
            for r in app:
                lay.addWidget(D.label(f"<b>{html.escape(r['subject'])}</b>: {html.escape(r['value'])}  "
                                      f"<span style='color:{D.tokens()['muted']}'>({html.escape(r.get('doc', ''))})</span>"))
        import custfocus as CF                                          # 3.63.0: the factors that judge it
        fs = CF.factors_for(self.rec, d["id"])
        lay.addWidget(D.SectionTitle("Evaluation factors that judge it"))
        lay.addWidget(D.label(", ".join(f"{f['name']} ({f.get('importance', 'Not stated')})" for f in fs) if fs else
                              "None tied yet (Shred > Evaluation > Deliverables it judges...).", None if fs else "muted"))
        # the Structure volume
        lay.addWidget(D.SectionTitle("In the response structure"))
        heads = self.page.volume_heads()
        vr = QHBoxLayout(); lay.addLayout(vr)
        self.e_vol = QComboBox(); self.e_vol.addItem("(not a Structure volume)", "")
        for h in heads:
            self.e_vol.addItem(h, h)
        self.e_vol.setCurrentIndex(max(0, self.e_vol.findData(d.get("volume", ""))))
        self.e_vol.activated.connect(lambda _i: self.link_volume(self.e_vol.currentData()))
        vr.addWidget(self.e_vol, 1)
        if not d.get("volume") and self.host.review is not None:
            vr.addWidget(D.button("Make it a Structure volume", None, lambda: self.make_volume(),
                                  "A new volume in Setup named for this deliverable; its sections become its parts"))
        lay.addWidget(D.label("A volume deliverable and its Structure volume are one thing: its sections are its parts, and its "
                              "requirements are the ones placed there.", "muted"))

    def save_overview(self, values=None):
        from .people import combo_name
        v = values or {"name": self.e_name.text(), "kind": self.e_kind.currentText(), "status": self.e_status.currentText(),
                       "owner": combo_name(self.e_owner), "due": self.e_due.text().strip(), "source": self.e_source.currentText(),
                       "about": self.e_about.toPlainText(), "guidelines": self.e_guide.toPlainText()}
        DL.update(self.rec, self.did, **v)
        diag.activity("deliverable_page_saved")
        self.host.toast("Saved")
        self.saved("Overview")
        return True

    def link_volume(self, vol):
        DL.update(self.rec, self.did, volume=vol or "")
        self.saved("Overview")
        return vol

    def make_volume(self, title=None):
        lab = DM.make_volume(self.host.review, self.d(), title)
        if lab:
            self.rec.save()
            self.host.changed()
            diag.activity("deliverable_volume_made")
            self.host.toast(f"{lab} is in Setup")
        self.saved("Overview")
        return lab

    # ------------------------------------------------------------ Format and submission
    def _format(self, lay, d):
        r = QHBoxLayout(); lay.addLayout(r)
        r.addWidget(D.label("Format group", None, wrap=False))
        self.e_group = QComboBox(); self.e_group.addItem("(none)", "")
        for g in DM.groups(self.rec):
            self.e_group.addItem(g["name"], g["id"])
        self.e_group.setCurrentIndex(max(0, self.e_group.findData(d.get("group", ""))))
        self.e_group.activated.connect(lambda _i: self.set_group(self.e_group.currentData()))
        r.addWidget(self.e_group, 1)
        r.addWidget(D.button("Format groups...", "ghost", lambda: self.page.groups_window()))
        lay.addWidget(D.label("Values come from the group; type one here to set this deliverable's own. Clear it to use the "
                              "group's again.", "muted"))
        eff = DM.effective(self.rec, d)
        self.fmt = QTableWidget(len(eff), 3); self.fmt.setHorizontalHeaderLabels(["", "Value", "From"])
        self.fmt.verticalHeader().setVisible(False); self.fmt.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._loading = True
        for i, (k, lab, val, where) in enumerate(eff):
            a = QTableWidgetItem(lab); a.setFlags(a.flags() & ~Qt.ItemIsEditable); a.setData(Qt.UserRole, k)
            b = QTableWidgetItem(val)
            c = QTableWidgetItem(where or "not set"); c.setFlags(c.flags() & ~Qt.ItemIsEditable)
            if where.startswith("group"):
                b.setForeground(D.color("muted"))
            for j, it in enumerate((a, b, c)):
                self.fmt.setItem(i, j, it)
        self._loading = False
        self.fmt.setMinimumHeight(44 + 30 * len(eff))
        self.fmt.itemChanged.connect(self._fmt_changed)
        lay.addWidget(self.fmt)

    def _fmt_changed(self, it):
        if self._loading or it.column() != 1:
            return
        k = self.fmt.item(it.row(), 0).data(Qt.UserRole)
        self.set_own(k, it.text())

    def set_own(self, field, value):
        DM.set_own(self.rec, self.did, field, value)
        self.saved("Format and submission")
        return DM.value(self.rec, self.d(), field)

    def set_group(self, gid):
        DM.set_group(self.rec, self.did, gid)
        self.saved("Format and submission")
        return True

    # ------------------------------------------------------------ Parts and people
    def _parts(self, lay, d):
        sp = DM.structure_parts(d, self.M)
        if d.get("volume"):
            lay.addWidget(D.SectionTitle(f"Sections of {d['volume']} ({len(sp)})"))
            self.sec_table = _table(["Section", "Lead", "Contributors"], [(a, b or "nobody yet", c) for a, b, c in sp])
            lay.addWidget(self.sec_table)
            r = QHBoxLayout(); lay.addLayout(r)
            r.addWidget(D.button("Set leads in Setup", None, lambda: self.host.go("setups"), "Plan > Setup: each section's lead and contributors"))
            r.addWidget(D.button("Open in Setup", "ghost", lambda: self.host.go("setups")))
            r.addStretch(1)
        lay.addWidget(D.SectionTitle("Parts of its own"))
        lay.addWidget(D.label("For a deliverable outside the Structure (a form, a plan, slides), or work inside a volume that is "
                              "not a section: name the part and who has it.", "muted"))
        ps = d.get("parts", [])
        self.part_table = _table(["Part", "Owner", "With", "Section"], [(p["name"], p["owner"], p["with"], p["section"]) for p in ps])
        lay.addWidget(self.part_table)
        from .people import name_combo, combo_name
        add = QHBoxLayout(); lay.addLayout(add)
        self.p_name = QLineEdit(); self.p_name.setPlaceholderText("Part (for example Cost narrative)"); add.addWidget(self.p_name, 2)
        self.p_owner = name_combo(self.host, ""); add.addWidget(self.p_owner, 1)
        self.p_sec = QComboBox(); self.p_sec.addItem("(no section)", "")
        for lab, _l, _w in sp:
            self.p_sec.addItem(lab, lab)
        add.addWidget(self.p_sec, 1)
        add.addWidget(D.button("Add part", None, lambda: self.add_part(self.p_name.text(), combo_name(self.p_owner), self.p_sec.currentData() or "")))
        add.addWidget(D.button("Remove", "danger", lambda: self.remove_part()))
        lay.addWidget(D.SectionTitle("Everyone on it"))
        lay.addWidget(D.label(", ".join(DM.people(d, self.M)) or "Nobody yet."))

    def add_part(self, name, owner="", section=""):
        pid = DM.add_part(self.rec, self.did, name, owner, section=section)
        self.saved("Parts and people")
        return pid

    def remove_part(self, row=None):
        d = self.d()
        row = self.part_table.currentRow() if row is None else row
        ps = d.get("parts", [])
        if 0 <= row < len(ps):
            DM.remove_part(self.rec, self.did, ps[row]["id"])
            self.saved("Parts and people")
            return True
        return False

    # ------------------------------------------------------------ Requirements
    def _requirements(self, lay, d):
        self._solicitation(lay, d)                                      # 4.12.0: the pieces Shred attached
        c = next((x for x in self.page.cards if x["id"] == d["id"]), None) or {}
        rr = c.get("req_rows") or []
        if not d.get("volume"):
            lay.addWidget(D.label("Requirements show here once it is a Structure volume (Overview) and requirements are placed in "
                                  "its sections.", "muted"))
            return
        lay.addWidget(D.label(f"{len(rr)} requirement(s) placed in {d['volume']}. Double-click one to open it in Review.", "muted"))
        self.req_table = _table(["ID", "Section", "Author", "The customer's words"],
                                [(x["id"], x["section"], x["owner"] or "no author", x["text"]) for x in rr], stretch=3)
        self.req_table.cellDoubleClicked.connect(lambda r, _c, rr=rr: self.page.open_requirement(rr[r]["id"]))
        lay.addWidget(self.req_table)

    def _solicitation(self, lay, d):
        ps = d.get("pieces") or []
        lay.addWidget(D.SectionTitle("From the solicitation"))
        if not ps:
            lay.addWidget(D.label("No pieces yet. On Shred, a piece typed Deliverable picks this deliverable under Which deliverable.",
                                  "muted"))
            self.piece_table = None
            return
        lay.addWidget(D.label(f"{len(ps)} piece(s) of the customer's documents describe it. Double-click one to open it in Shred.",
                              "muted"))
        self.piece_table = _table(["ID", "Document", "Page", "The customer's words"],
                                  [(p.get("sid", ""), p.get("doc", ""), p.get("page", ""), p.get("text", "")) for p in ps], stretch=3)
        self.piece_table.cellDoubleClicked.connect(lambda r, _c, ps=ps: self.page.open_requirement(ps[r]["sid"]))
        lay.addWidget(self.piece_table)

    # ------------------------------------------------------------ Attachments and files
    def _attachments(self, lay, d):
        lay.addWidget(D.SectionTitle("Attachments"))
        lay.addWidget(D.label("The named files it carries: the customer's (a form, a pricing sheet) or ours (a resume, a letter).", "muted"))
        xs = d.get("attachments", [])
        self.att_table = _table(["Attachment", "From", "File", "Note"], [(a["name"], a["source"], a["file"], a["note"]) for a in xs])
        lay.addWidget(self.att_table)
        add = QHBoxLayout(); lay.addLayout(add)
        self.a_name = QLineEdit(); self.a_name.setPlaceholderText("Name (for example Attachment J-4 Pricing)"); add.addWidget(self.a_name, 2)
        self.a_src = QComboBox(); self.a_src.addItems(DM.SOURCES); add.addWidget(self.a_src)
        self.a_file = QLineEdit(); self.a_file.setPlaceholderText("File (optional)"); add.addWidget(self.a_file, 2)
        add.addWidget(D.button("Choose...", "ghost", lambda: self._pick(self.a_file)))
        add.addWidget(D.button("Add", None, lambda: self.add_attachment(self.a_name.text(), self.a_src.currentText(), self.a_file.text())))
        add.addWidget(D.button("Remove", "danger", lambda: self.remove_attachment()))
        lay.addWidget(D.SectionTitle("Our file and the customer's form"))
        lay.addWidget(D.label(f"Our working file: {d.get('file') or 'none yet'}"))
        fr = QHBoxLayout(); lay.addLayout(fr)
        self.f_file = QLineEdit(d.get("file", "")); fr.addWidget(self.f_file, 1)
        fr.addWidget(D.button("Choose...", "ghost", lambda: self._pick(self.f_file)))
        fr.addWidget(D.button("Save", None, lambda: self.set_file(self.f_file.text())))
        lay.addWidget(D.SectionTitle("References"))
        lay.addWidget(D.label("Documents or items that matter to it, from the Library or this PC, with why.", "muted"))
        rs = d.get("references", [])
        self.ref_table = _table(["Reference", "Where", "Why"], [(r["label"], r["where"], r["note"]) for r in rs])
        lay.addWidget(self.ref_table)
        ar = QHBoxLayout(); lay.addLayout(ar)
        self.r_label = QLineEdit(); self.r_label.setPlaceholderText("What it is"); ar.addWidget(self.r_label, 2)
        self.r_where = QLineEdit(); self.r_where.setPlaceholderText("File or Library item"); ar.addWidget(self.r_where, 2)
        self.r_note = QLineEdit(); self.r_note.setPlaceholderText("Why it matters"); ar.addWidget(self.r_note, 2)
        ar.addWidget(D.button("Add", None, lambda: self.add_reference(self.r_label.text(), self.r_where.text(), self.r_note.text())))
        ar.addWidget(D.button("Remove", "danger", lambda: self.remove_reference()))

    def _pick(self, edit):
        p, _ = QFileDialog.getOpenFileName(self, "Choose a file")
        if p:
            edit.setText(p)

    def add_attachment(self, name, source="Ours", file=""):
        aid = DM.add_attachment(self.rec, self.did, name, source, file)
        self.saved("Attachments and files")
        return aid

    def remove_attachment(self, row=None):
        xs = self.d().get("attachments", [])
        row = self.att_table.currentRow() if row is None else row
        if 0 <= row < len(xs):
            DM.remove_attachment(self.rec, self.did, xs[row]["id"])
            self.saved("Attachments and files")
            return True
        return False

    def set_file(self, path):
        DL.update(self.rec, self.did, file=path)
        self.saved("Attachments and files")
        return True

    def add_reference(self, label, where="", note=""):
        rid = DM.add_reference(self.rec, self.did, label, where, note)
        self.saved("Attachments and files")
        return rid

    def remove_reference(self, row=None):
        xs = self.d().get("references", [])
        row = self.ref_table.currentRow() if row is None else row
        if 0 <= row < len(xs):
            DM.remove_reference(self.rec, self.did, xs[row]["id"])
            self.saved("Attachments and files")
            return True
        return False

    # ------------------------------------------------------------ Discussion
    def _discussion(self, lay, d):
        lay.addWidget(D.label("Notes on this deliverable, dated with the writer's name. Each one also goes in the effort's "
                              "timeline. Pin the ones everyone needs to see.", "muted"))
        self.post_box = QPlainTextEdit(); self.post_box.setPlaceholderText("Write a note"); self.post_box.setMaximumHeight(80)
        lay.addWidget(self.post_box)
        r = QHBoxLayout(); lay.addLayout(r)
        r.addWidget(D.button("Post", "primary", lambda: self.post(self.post_box.toPlainText())))
        r.addStretch(1)
        r.addWidget(D.label("Show", None, wrap=False))
        self.who_filter = QComboBox(); self.who_filter.addItem("Everyone", "")
        for n in DM.writers(d):
            self.who_filter.addItem(n, n)
        self.who_filter.setCurrentIndex(max(0, self.who_filter.findData(getattr(self, "_who", ""))))
        self.who_filter.activated.connect(lambda _i: self.filter_person(self.who_filter.currentData()))
        r.addWidget(self.who_filter)
        self.posts = QListWidget(); self.posts.setWordWrap(True); self.posts.setMinimumHeight(220)
        for e in DM.discussion(d, getattr(self, "_who", "")):
            it = QListWidgetItem(("[Pinned]  " if e.get("pinned") else "") + f"{e['at'].replace('T', ' ')}  {e['by']}\n{e['text']}")
            it.setData(Qt.UserRole, e["id"])
            self.posts.addItem(it)
        lay.addWidget(self.posts)
        pr = QHBoxLayout(); lay.addLayout(pr)
        pr.addWidget(D.button("Pin or unpin", None, lambda: self.toggle_pin()))
        pr.addWidget(D.button("Remove", "danger", lambda: self.remove_post()))
        pr.addStretch(1)

    def post(self, text, who=None):
        eid = DM.post(self.rec, self.did, text, who)
        if eid:
            diag.activity("deliverable_note_posted")
        self.saved("Discussion")
        return eid

    def filter_person(self, name):
        self._who = name or ""
        self.fill_tab()
        return self.posts.count()

    def _post_id(self):
        it = self.posts.currentItem()
        return it.data(Qt.UserRole) if it is not None else None

    def toggle_pin(self, eid=None):
        eid = eid or self._post_id()
        e = next((x for x in self.d().get("discussion", []) if x["id"] == eid), None)
        if e is None:
            return False
        DM.pin(self.rec, self.did, eid, not e.get("pinned"))
        self.saved("Discussion")
        return True

    def remove_post(self, eid=None):
        eid = eid or self._post_id()
        ok = DM.remove_post(self.rec, self.did, eid) if eid else False
        self.saved("Discussion")
        return ok

    # ------------------------------------------------------------ Dates
    def _dates(self, lay, d):
        lay.addWidget(D.label("Its due date (Overview) and its own dates show on the effort's calendar, with its owner.", "muted"))
        rows = ([((d.get("due") or "")[:10], "Due")] if d.get("due") else []) + [(x["date"], x["what"]) for x in sorted(d.get("dates", []), key=lambda x: x["date"])]
        self.date_table = _table(["Date", "What"], rows, stretch=1)
        lay.addWidget(self.date_table)
        r = QHBoxLayout(); lay.addLayout(r)
        self.d_date = QLineEdit(); self.d_date.setPlaceholderText("YYYY-MM-DD"); r.addWidget(self.d_date)
        self.d_what = QLineEdit(); self.d_what.setPlaceholderText("What happens (for example Pink team)"); r.addWidget(self.d_what, 1)
        r.addWidget(D.button("Add date", None, lambda: self.add_date(self.d_date.text(), self.d_what.text())))
        r.addWidget(D.button("Remove", "danger", lambda: self.remove_date()))

    def add_date(self, date, what):
        xid = DM.add_date(self.rec, self.did, date.strip(), what)
        if xid is None:
            self.host.status("Type the date as YYYY-MM-DD and what happens.")
        self.saved("Dates")
        return xid

    def remove_date(self, row=None):
        d = self.d()
        xs = sorted(d.get("dates", []), key=lambda x: x["date"])
        row = self.date_table.currentRow() if row is None else row
        row -= 1 if d.get("due") else 0
        if 0 <= row < len(xs):
            DM.remove_date(self.rec, self.did, xs[row]["id"])
            self.saved("Dates")
            return True
        return False
