"""Production > Template Studio (3.66.0): one volume's template in one place, read from where its parts live (never a
second copy). Anatomy: each part of the profile (cover, title page, headers and footers per part, table of contents,
fonts, theme, heading numbering, pagination, table looks) with the library item it uses, this effort's own formatting,
and the RFP's formatting rules beside them; each opens the screen that owns it. Parts and numbering: the volume's parts
in order with their page numbers, restarts, chapter style, header and footer, orientation, paper and what counts toward
the limit (Final Check reads it). Read back (3.67.0): a made file against the plan. Field recipes open in Rules. claude/stationkeeper-studio-decisions-2026-11-06.md"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFormLayout, QHBoxLayout, QHeaderView, QLineEdit, QSpinBox, QTableWidget, QTableWidgetItem,
                               QTabWidget, QVBoxLayout, QWidget)
import diag
import effortrec as R
import partplan as PP
from . import design as D


class StudioPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.parts, self.slots = [], []
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"]); v.addLayout(top)
        top.addWidget(D.label("Volume", None, wrap=False))
        self.vol = QComboBox(); self.vol.setMinimumWidth(220); self.vol.activated.connect(lambda _i: self.fill())
        top.addWidget(self.vol)
        top.addWidget(D.label("Profile", None, wrap=False))
        self.prof = QComboBox(); self.prof.setMinimumWidth(240); self.prof.activated.connect(lambda _i: self.fill_anatomy())
        top.addWidget(self.prof, 1)
        top.addWidget(D.button("Field recipes", "ghost", lambda: self.open_recipes(), "Rules > Field recipes: your field codes"))
        v.addWidget(D.label("Everything that makes this volume's template, read from where it lives: the libraries, the "
                            "effort type's profile and this effort's formatting. Change a part where it lives; Parts and "
                            "numbering is set here and Final Check reads it.", "muted"))
        self.tabs = QTabWidget(); v.addWidget(self.tabs, 1)
        # ---- anatomy
        aw = QWidget(); al = QVBoxLayout(aw); al.setContentsMargins(0, D.SPACE["s"], 0, 0)
        self.anat = QTableWidget(0, 4); self.anat.setHorizontalHeaderLabels(["Part", "What", "Uses", "Where it lives"])
        self.anat.verticalHeader().setVisible(False); self.anat.setEditTriggers(QTableWidget.NoEditTriggers)
        self.anat.setSelectionBehavior(QTableWidget.SelectRows); self.anat.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.anat.cellDoubleClicked.connect(lambda r, _c: self.open_owner(r))
        al.addWidget(self.anat, 2)
        al.addWidget(D.label("Double-click a row to open the screen that owns it.", "muted"))
        al.addWidget(D.SectionTitle("This effort's own formatting"))
        self.own = D.label("", None); al.addWidget(self.own)
        al.addWidget(D.SectionTitle("What the RFP says about formatting"))
        self.rfp = QTableWidget(0, 3); self.rfp.setHorizontalHeaderLabels(["Rule", "The RFP says", "From"])
        self.rfp.verticalHeader().setVisible(False); self.rfp.setEditTriggers(QTableWidget.NoEditTriggers)
        self.rfp.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        al.addWidget(self.rfp, 1)
        self.tabs.addTab(aw, "Anatomy")
        # ---- parts and numbering
        pw = QWidget(); pl = QVBoxLayout(pw); pl.setContentsMargins(0, D.SPACE["s"], 0, 0)
        self.ptab = QTableWidget(0, 6)
        self.ptab.setHorizontalHeaderLabels(["Part", "Kind", "Page numbers", "Header and footer", "Paper", "Toward the limit"])
        self.ptab.verticalHeader().setVisible(False); self.ptab.setEditTriggers(QTableWidget.NoEditTriggers)
        self.ptab.setSelectionBehavior(QTableWidget.SelectRows); self.ptab.setSelectionMode(QTableWidget.SingleSelection)
        self.ptab.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.ptab.itemSelectionChanged.connect(self.show_part)
        pl.addWidget(self.ptab, 1)
        br = QHBoxLayout(); pl.addLayout(br)
        br.addWidget(D.button("+ Part", None, lambda: self.add_part()))
        br.addWidget(D.button("Up", "ghost", lambda: self.move(-1))); br.addWidget(D.button("Down", "ghost", lambda: self.move(1)))
        br.addWidget(D.button("Remove", "danger", lambda: self.remove()))
        br.addWidget(D.button("Use the usual parts", "ghost", lambda: self.usual(), "Cover, front matter in i, the response in 1, appendices A-1 on Heading 7"))
        br.addStretch(1)
        f = QFormLayout(); f.setSpacing(D.SPACE["s"]); pl.addLayout(f)
        self.e_name = QLineEdit(); f.addRow("Part", self.e_name)
        self.e_kind = QComboBox(); self.e_kind.addItems(PP.KINDS); f.addRow("Kind", self.e_kind)
        nr = QHBoxLayout()
        self.e_fmt = QComboBox()
        for k in PP.FORMATS:
            self.e_fmt.addItem(PP.FORMAT_SAYS[k], k)
        nr.addWidget(self.e_fmt, 2)
        self.e_restart = QComboBox(); self.e_restart.addItems(["Continues from the part before", "Restarts at"]); nr.addWidget(self.e_restart, 2)
        self.e_start = QSpinBox(); self.e_start.setRange(1, 999); nr.addWidget(self.e_start)
        f.addRow("Page numbers", nr)
        cr = QHBoxLayout()
        self.e_chapter = QComboBox(); self.e_chapter.setEditable(True); self.e_chapter.addItems(["", "Heading 1", "Heading 7", "Heading 8", "Heading 9"])
        cr.addWidget(self.e_chapter, 2)
        self.e_sep = QComboBox(); self.e_sep.setEditable(True); self.e_sep.addItems(["-", ".", ":", " "]); cr.addWidget(self.e_sep)
        f.addRow("Chapter style and separator (A-1)", cr)
        self.e_header = QComboBox(); self.e_header.addItems(PP.HEADERS); f.addRow("Header and footer", self.e_header)
        orow = QHBoxLayout()
        self.e_orient = QComboBox(); self.e_orient.addItems(PP.ORIENT); orow.addWidget(self.e_orient)
        self.e_paper = QComboBox(); self.e_paper.addItems(PP.PAPER); orow.addWidget(self.e_paper)
        f.addRow("Orientation and paper", orow)
        crow = QHBoxLayout()
        self.e_counts = QComboBox(); self.e_counts.addItems(PP.COUNTS); crow.addWidget(self.e_counts)
        crow.addWidget(D.label("an 11x17 sheet counts as", None, wrap=False))
        self.e_fold = QSpinBox(); self.e_fold.setRange(1, 4); crow.addWidget(self.e_fold)
        crow.addWidget(D.label("page(s); blank pages", None, wrap=False))
        self.e_blanks = QComboBox(); self.e_blanks.addItems(["Do not count", "Count"]); crow.addWidget(self.e_blanks)
        f.addRow("Toward the limit", crow)
        sr = QHBoxLayout(); pl.addLayout(sr)
        sr.addWidget(D.button("Save the part", "primary", lambda: self.save_part()))
        sr.addStretch(1)
        self.sample = D.label("", "muted"); pl.addWidget(self.sample)
        self.tabs.addTab(pw, "Parts and numbering")
        from .readbackview import ReadBackView           # 3.67.0
        self.readback = ReadBackView(self); self.tabs.addTab(self.readback, "Read back")

    # ------------------------------------------------------------ the effort
    def rec(self):
        return R.Record(self.host.ws.root) if self.host.ws is not None else None

    def volumes(self):
        out = []
        R_ = self.host.review
        if R_ is not None:
            try:
                import outline_ops as O
                out = list(O.volume_heads(R_.M))
            except Exception:  # noqa: BLE001
                diag.swallowed()
        r = self.rec()
        if r is not None:
            import deliverables as DL
            out += [d["name"] for d in DL.items(r) if d.get("kind") == "Volume" and d.get("volume", "") not in out and d["name"] not in out]
            out += [k for k in (r.data.get("part_plans") or {}) if k not in out]
        return out

    def refresh(self):
        r = self.rec()
        self.setEnabled(r is not None)
        if r is None:
            return
        cur = self.vol.currentText()
        self.vol.clear(); self.vol.addItems(self.volumes() or ["The proposal"])
        if cur:
            self.vol.setCurrentText(cur)
        cp = self.prof.currentData()
        self.prof.clear()
        try:
            import prodrules as PRL, effortprofiles as EP
            self.std_data = PRL.load(self.host.config_dir)
            for p in EP.profiles(self.std_data):
                self.prof.addItem(f"{p['ename']}: {p['pname']}", (p["eid"], p["pid"]))
        except Exception:  # noqa: BLE001
            diag.swallowed(); self.std_data = {}
        if cp is not None:
            self.prof.setCurrentIndex(max(0, self.prof.findData(cp)))
        else:
            self._guess_profile()
        self.fill()

    def _guess_profile(self):
        v = self.vol.currentText().casefold()
        for i in range(self.prof.count()):
            if any(w in v for w in self.prof.itemText(i).split(": ", 1)[-1].casefold().split() if len(w) > 3 and w != "volume"):
                self.prof.setCurrentIndex(i)
                return

    def fill(self):
        self.fill_anatomy()
        self.fill_parts()

    # ------------------------------------------------------------ anatomy
    def fill_anatomy(self):
        rows = []
        pp = self.prof.currentData()
        try:
            import effortprofiles as EP, templateprofile as TP, templatelib as TL
            lib = TL.Library(self.host.config_dir)
            for slot, part, what, _k in TP.SLOTS:
                stt = EP.slot_state(self.std_data, pp[0], pp[1], lib, slot) if pp else {"item": None, "newer": None, "pin": None}
                it = stt.get("item")
                uses = (f"{it.get('name', '')} v{it.get('version', 1)}" if it else ("the profile's own values" if pp else "no profile picked"))
                if stt.get("newer") is not None:
                    uses += f" (v{stt['newer'].get('version')} is newer)"
                rows.append((part, what, uses, "Effort Profiles", "profiles"))
        except Exception:  # noqa: BLE001
            diag.swallowed()
        r = self.rec()
        if r is not None:
            n = len([x for x in PP.plan_of(r, self.vol.currentText())])
            rows.append(("Whole volume", "Parts and numbering", f"{n} part(s): " + ", ".join(p["name"] for p in PP.plan_of(r, self.vol.currentText())),
                         "Template Studio", "studio:parts"))
        try:
            import fieldrecipes as FR
            rs = FR.effective(self.host.config_dir, self.host.ws)
            rows.append(("Whole volume", "Field recipes", f"{len(rs)} recipe(s)" + (f", {sum(1 for x in rs if x.get('effort_own'))} this effort's own"
                                                                                    if any(x.get("effort_own") for x in rs) else ""),
                         "Rules > Field recipes", "recipes"))
        except Exception:  # noqa: BLE001
            diag.swallowed()
        self.slots = rows
        self.anat.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row[:4]):
                self.anat.setItem(i, j, QTableWidgetItem(val))
        try:
            import effortformat as EF
            ch = EF.changed(self.host.config_dir, self.host.ws) if self.host.ws is not None else []
            self.own.setText((f"{len(ch)} value(s) set for this effort only: " + "; ".join(w for w, _g, _m in ch[:6]) + (" ..." if len(ch) > 6 else ""))
                             if ch else "None: this effort uses the global standards.")
        except Exception:  # noqa: BLE001
            diag.swallowed(); self.own.setText("")
        rows2 = []
        try:
            from .custdocs import Ctx
            for x in Ctx(self.host).reg.rows():
                if x.get("kind") in ("Format", "Page limit", "File") and not x.get("hidden"):
                    rows2.append((x.get("subject", ""), x.get("value", ""), x.get("doc", "")))
        except Exception:  # noqa: BLE001
            diag.swallowed()
        self.rfp.setRowCount(len(rows2))
        for i, row in enumerate(rows2):
            for j, val in enumerate(row):
                self.rfp.setItem(i, j, QTableWidgetItem(str(val)))
        self.anatomy_now = rows

    def open_owner(self, row):
        if not (0 <= row < len(self.slots)):
            return None
        where = self.slots[row][4]
        if where == "studio:parts":
            self.tabs.setCurrentIndex(1)
        elif where == "recipes":
            self.open_recipes()
        else:
            self.host.go(where)
        return where

    def open_recipes(self):
        self.host.go("rules")
        try:
            self.host.rules_page.show_family(2)
        except Exception:  # noqa: BLE001
            diag.swallowed()
        return True

    # ------------------------------------------------------------ parts and numbering
    def fill_parts(self, keep=None):
        r = self.rec()
        if r is None:
            return
        keep = keep or self.current_part()
        self.parts = PP.plan_of(r, self.vol.currentText())
        self.ptab.setRowCount(len(self.parts))
        for i, p in enumerate(self.parts):
            nums = PP.FORMAT_SAYS[p["format"]] + (f", restarts at {PP.page_label(p, 1)}" if p["restart"] and p["format"] != "none" else "")
            if p["format"] == "A-1":
                nums += f" ({p['chapter']})"
            cnt = p["counts"] + (f"; 11x17 as {p['foldout']}" if p["paper"] == "11x17" else "")
            for j, val in enumerate((p["name"], p["kind"], nums, p["header"], f"{p['orient']} {p['paper']}", cnt)):
                self.ptab.setItem(i, j, QTableWidgetItem(val))
        ids = [p["id"] for p in self.parts]
        if keep in ids:
            self.ptab.selectRow(ids.index(keep))
        elif ids:
            self.ptab.selectRow(0)
        self.sample.setText("  |  ".join(PP.says(p) for p in self.parts))

    def current_part(self):
        i = self.ptab.currentRow()
        return self.parts[i]["id"] if 0 <= i < len(self.parts) else None

    def show_part(self):
        p = next((x for x in self.parts if x["id"] == self.current_part()), None)
        if p is None:
            return
        self.e_name.setText(p["name"]); self.e_kind.setCurrentText(p["kind"])
        self.e_fmt.setCurrentIndex(max(0, self.e_fmt.findData(p["format"])))
        self.e_restart.setCurrentIndex(1 if p["restart"] else 0); self.e_start.setValue(int(p["start"]))
        self.e_chapter.setCurrentText(p["chapter"]); self.e_sep.setCurrentText(p["sep"])
        self.e_header.setCurrentText(p["header"]); self.e_orient.setCurrentText(p["orient"]); self.e_paper.setCurrentText(p["paper"])
        self.e_counts.setCurrentText(p["counts"]); self.e_fold.setValue(int(p["foldout"])); self.e_blanks.setCurrentText(p["blanks"])

    def part_values(self):
        return {"name": self.e_name.text(), "kind": self.e_kind.currentText(), "format": self.e_fmt.currentData(),
                "restart": self.e_restart.currentIndex() == 1, "start": self.e_start.value(), "chapter": self.e_chapter.currentText(),
                "sep": self.e_sep.currentText() or "-", "header": self.e_header.currentText(), "orient": self.e_orient.currentText(),
                "paper": self.e_paper.currentText(), "counts": self.e_counts.currentText(), "foldout": self.e_fold.value(),
                "blanks": self.e_blanks.currentText()}

    def save_part(self, values=None, pid=None):
        pid = pid or self.current_part()
        r = self.rec()
        if r is None or not pid:
            return False
        PP.update_part(r, self.vol.currentText(), pid, **(values or self.part_values()))
        diag.activity("studio_part_saved")
        self.fill_parts(pid); self.fill_anatomy()
        return True

    def add_part(self, name="A new part", kind="Body"):
        pid = PP.add_part(self.rec(), self.vol.currentText(), name, kind, after=self.current_part())
        self.fill_parts(pid)
        return pid

    def remove(self):
        pid = self.current_part()
        if pid:
            PP.remove_part(self.rec(), self.vol.currentText(), pid)
        self.fill_parts()
        return bool(pid)

    def move(self, step):
        pid = self.current_part()
        ok = PP.move_part(self.rec(), self.vol.currentText(), pid, step) if pid else False
        self.fill_parts(pid)
        return ok

    def usual(self):
        PP.set_plan(self.rec(), self.vol.currentText(), PP.default_parts())
        self.fill_parts()
        return True
