"""Parts (3.95.0; claude/stationkeeper-libraries-and-sets.md, canvas "Libraries and Sets" boards 4, 7 and 8): the one
place covers, marking (CUI) pages, title pages, front matter (contents, acronyms, units), back covers and Quick Parts
are brought in, kept and grouped. Each kind is a tab with its count. One row per part: its picture, its name with its
versions as tabs, where it came from, and the part sets it is in (colored chips). The part sets are on the left; drag
rows onto a set to add them (a set holds one version of each part). The selected part shows on the right: the page,
what fills it, the text other pages read and the check. Act on the row: Open in Word, Bring back as a new version...,
Name this version..., Add to set, Remove. Rules: partlib, sectiondesigns. Nothing leaves the PC."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidgetItem, QMenu, QPushButton, QTabBar,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

import diag
import partlib as PT
import sectiondesigns as SDZ
import stylelib as SL
import templatelib as TL
from . import design as D
from .adaptive import FlowLayout
from .commandbar import CommandBar
from .stylespage import Rows, SetList, dot

THUMB = (84, 108)
ONE = {"covers": "cover", "marking": "marking page", "titles": "title page", "front": "front matter page", "back": "back cover",
       "quick": "Quick Part", "tables": "table", "callouts": "callout", "hf": "header or footer"}


def _count_words(n, kind):
    one = ONE.get(kind, "part")
    return f"{n} {one}" if n == 1 else f"{n} {one}s"


class PartsPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.lib = TL.Library(host.config_dir)
        self.sid = None
        self.kind = "covers"
        self.cur = None
        self.shown_ver = {}
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"])
        self.count = D.label("", "muted", wrap=False); top.addWidget(self.count, 1)
        self.find = QLineEdit(); self.find.setPlaceholderText("Find a part"); self.find.setClearButtonEnabled(True)
        self.find.setMinimumWidth(220); self.find.textChanged.connect(lambda _t: self.fill_rows())
        top.addWidget(self.find)
        self.bar = CommandBar(self)
        self.bar.primary("Bring in from a document...", lambda: self.bring_in(),
                         "The pages of a Word file (one per Word section: a cover, a CUI page, a title page...) and its Quick "
                         "Parts gallery; tick the ones you keep (the file is only read)")
        self.bar.more("New part set...", lambda: self.new_set())
        self.bar.more("Rename this set...", lambda: self.rename_set())
        self.bar.more("Take this set away", lambda: self.remove_set())
        top.addWidget(self.bar)
        v.addLayout(top)
        self.tabs = QTabBar(); self.tabs.setDrawBase(False); self.tabs.setExpanding(False)
        for k, t, _s in PT.KINDS:
            self.tabs.addTab(t); self.tabs.setTabData(self.tabs.count() - 1, k)
        self.tabs.currentChanged.connect(lambda i: self.pick_kind(self.tabs.tabData(i)))
        v.addWidget(self.tabs)
        body = QHBoxLayout(); body.setSpacing(D.SPACE["l"])
        left = QVBoxLayout(); left.setSpacing(D.SPACE["s"])
        left.addWidget(D.label("PART SETS", "faint", wrap=False))
        self.sets = SetList(self)
        self.sets.currentItemChanged.connect(lambda cur, _p: self.pick_set(cur.data(Qt.UserRole) if cur is not None else None))
        left.addWidget(self.sets, 1)
        left.addWidget(D.label("Drag parts onto a set to add them. Make templates picks a set for its gallery and its pages.", "muted"))
        body.addLayout(left)
        mid = QVBoxLayout(); mid.setSpacing(D.SPACE["s"])
        self.rows = Rows(self)
        self.rows.currentItemChanged.connect(lambda cur, _p: self.show_part(cur.data(Qt.UserRole) if cur is not None else None))
        self.rows.itemDoubleClicked.connect(lambda _it: self.open_word(self.cur))
        mid.addWidget(self.rows, 1)
        self.empty = D.EmptyState("No parts yet", "Bring in a Word file that holds your covers, CUI page, title page or front "
                                  "matter, or a template with your Quick Parts: each page is kept whole, exactly as built in Word, "
                                  "and you choose which come in.", "Bring in from a document...", lambda: self.bring_in())
        mid.addWidget(self.empty)
        body.addLayout(mid, 3)
        side = QWidget(); sv = QVBoxLayout(side); sv.setContentsMargins(0, 0, 0, 0); sv.setSpacing(D.SPACE["s"])
        self.title = D.label("", "title"); sv.addWidget(self.title)
        self.thumb = QLabel(); self.thumb.setFixedSize(230, 300); self.thumb.setAlignment(Qt.AlignCenter); self.thumb.setWordWrap(True)
        D.themed(self.thumb, lambda t: "QLabel { border: 1px solid %s; background: white; color: #111111; padding: 8px; }" % t["border"])
        self.thumb_note = D.label("", "muted")
        sv.addWidget(self.thumb); sv.addWidget(self.thumb_note)
        self.fills_lab = D.label("What fills it", "label"); sv.addWidget(self.fills_lab)
        self.fills = QTableWidget(0, 3); self.fills.setHorizontalHeaderLabels(["Paragraph", "Style", "Fill-in (blank: as written)"])
        self.fills.horizontalHeader().setStretchLastSection(True); self.fills.verticalHeader().setVisible(False)
        self.fills.itemChanged.connect(self.fill_changed)
        sv.addWidget(self.fills, 1)
        self.others_lab = D.label("Text other pages read", "label"); sv.addWidget(self.others_lab)
        self.others = D.label("", "muted"); sv.addWidget(self.others)
        self.problems = D.label("", None); sv.addWidget(self.problems)
        self.filler = QWidget(); sv.addWidget(self.filler, 1)          # keeps a Quick Part's picture at the top
        side.setMinimumWidth(380); side.setMaximumWidth(520)
        self.side = side
        body.addWidget(side, 2)
        v.addLayout(body, 1)
        self._guard = False

    def cfg(self):
        return self.host.config_dir

    # ------------------------------------------------------------ filling
    def refresh(self):
        self.lib.fresh()
        try:                                       # 3.90.0: covers, title pages and back covers kept in Layout come here
            got = SDZ.adopt(self.cfg(), self.lib)
            if got:
                self.host.status(f"{got} cover, title page or back cover design{'s' if got != 1 else ''} moved here from Layout.")
        except Exception:  # noqa: BLE001
            diag.swallowed()
        self.fill_tabs(); self.fill_sets(); self.fill_rows()

    def fill_tabs(self):
        for i in range(self.tabs.count()):
            k = self.tabs.tabData(i)
            n = PT.count(self.cfg(), k, self.lib)
            self.tabs.setTabText(i, PT.KIND[k][0] + (f"  {n}" if n else ""))

    def fill_sets(self):
        keep = self.sid
        self.sets.blockSignals(True)
        self.sets.clear()
        n_all = sum(PT.count(self.cfg(), k, self.lib) for k, _t, _s in PT.KINDS)
        it = QListWidgetItem(f"Every part    {n_all}"); it.setData(Qt.UserRole, None)
        self.sets.addItem(it)
        for k in SL.sets(self.lib, "part"):
            x = QListWidgetItem(dot(k.get("color") or "#64748B"), f"{k['name']}    {len(k['items'])}")
            x.setData(Qt.UserRole, k["id"])
            self.sets.addItem(x)
        self.sets.setCurrentRow(next((i for i in range(self.sets.count()) if self.sets.item(i).data(Qt.UserRole) == keep), 0))
        self.sets.blockSignals(False)

    def pick_kind(self, kind):
        self.kind = kind or "covers"
        self.fill_rows()

    def pick_set(self, sid):
        self.sid = sid
        self.shown_ver = {}                              # a set's rows open on the versions it uses
        self.fill_rows()

    def part_rows(self):
        rows = PT.rows(self.cfg(), self.kind, self.lib, self.shown_ver, self.find.text())
        k = SL.get_set(self.lib, self.sid) if self.sid else None
        if k is None:
            return rows
        out = []
        for r in rows:
            inset = [p for p in r["versions"] if p in k["items"]]
            if inset:
                out.append(dict(r, shown=self.shown_ver.get(r["family"]) if self.shown_ver.get(r["family"]) in r["versions"] else inset[0]))
        return out

    def fill_rows(self):
        keep = self.cur
        rows = self.part_rows()
        self.rows.blockSignals(True)
        self.rows.clear()
        self.row_ids = []
        for r in rows:
            w = self.row_widget(r)
            li = QListWidgetItem(); li.setData(Qt.UserRole, r["shown"]); li.setSizeHint(w.sizeHint())
            self.rows.addItem(li); self.rows.setItemWidget(li, w)
            self.row_ids.append(r["shown"])
        self.rows.blockSignals(False)
        has = any(PT.count(self.cfg(), k, self.lib) for k, _t, _s in PT.KINDS)
        self.rows.setVisible(has); self.empty.setVisible(not has); self.side.setVisible(has)
        k = SL.get_set(self.lib, self.sid) if self.sid else None
        word = _count_words(len(rows), self.kind)
        ns = len(SL.sets(self.lib, "part"))
        self.count.setText((f"{k['name']}: {word}" if k else f"{word} · {ns} part set{'' if ns == 1 else 's'}") if has else "")
        if not (keep in self.row_ids and self.select(keep)):
            if self.row_ids:
                self.rows.setCurrentRow(0)
            else:
                self.show_part(None)
        return rows

    # ------------------------------------------------------------ one row
    def info(self, pid):
        """(name, kind words, where it came from, its version, its label) for a part id ('d:...' or 'q:...')."""
        if pid and pid.startswith("d:"):
            x = SDZ.get(self.cfg(), pid[2:])
            if x:
                return {"name": x["name"], "what": PT.PAGE_WORDS.get(x["shelf"], x["shelf"]), "from": x.get("from", ""),
                        "at": (x.get("added") or "")[:10], "version": PT.version(x), "label": x.get("label", ""), "x": x}
        if pid and pid.startswith("q:"):
            it = self.lib.get(pid[2:])
            if it:
                v = self.lib.values(it) or {}
                return {"name": self.lib.base_of(it), "what": f"Quick Part · {v.get('category') or 'no category'}",
                        "from": it.get("source", ""), "at": (it.get("at") or "")[:10], "version": int(it.get("version") or 1),
                        "label": it.get("label", ""), "it": it, "values": v}
        return None

    def row_widget(self, r):
        inf = self.info(r["shown"]) or {"name": "?", "what": "", "from": "", "at": "", "version": 1, "label": ""}
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(8, 6, 8, 6); h.setSpacing(D.SPACE["m"])
        h.addWidget(self.small_thumb(r["shown"], inf))
        c = QWidget(); cv = QVBoxLayout(c); cv.setContentsMargins(0, 0, 0, 0); cv.setSpacing(3)
        nm = D.label(f"<b>{inf['name']}</b>", None, wrap=False); nm.setTextFormat(Qt.RichText); cv.addWidget(nm)
        if len(r["versions"]) > 1:                        # the versions are tabs on the row (19:16)
            tabs = QWidget(); tf = FlowLayout(tabs, 3)
            t = D.tokens()
            for pid in r["versions"]:
                vi = self.info(pid) or {"version": "?", "label": ""}
                b = QPushButton(f"v{vi['version']}" + (f" {vi['label']}" if vi.get("label") else "")); b.setCheckable(True)
                b.setChecked(pid == r["shown"]); b.setObjectName("verTab")
                b.setStyleSheet(f"QPushButton#verTab{{border:1px solid {t['border_strong']};border-radius:4px;padding:0 6px;font-size:11px;"
                                f"background:{t['surface']};color:{t['text']}}}QPushButton#verTab:checked{{border:2px solid {t['accent']};"
                                f"background:{t['accent_soft']};color:{t['accent']};font-weight:600}}")
                b.clicked.connect(lambda _c=False, f=r["family"], i=pid: self.show_version(f, i))
                tf.addWidget(b)
            cv.addWidget(tabs)
        words = inf["what"] + (f" · v{inf['version']}" if len(r["versions"]) > 1 else "") + (f" · from {inf['from']}" if inf["from"] else "") \
            + (f" · {inf['at']}" if inf["at"] else "")
        cv.addWidget(D.label(words, "muted"))
        chips = QWidget(); cf = FlowLayout(chips, 4)
        for k in PT.sets_of(self.lib, r["shown"]):
            ch = QLabel(k["name"]); ch.setObjectName("setChip")
            ch.setStyleSheet(f"QLabel#setChip{{border:1px solid {k.get('color') or '#64748B'};border-radius:9px;padding:0 7px;font-size:11px}}")
            cf.addWidget(ch)
        cv.addWidget(chips)
        h.addWidget(c, 1)
        return w

    def png_of(self, path):
        import wordpreview as WP
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            return ""
        return WP.cached(SDZ._root(self.cfg()), data) or ""

    def small_thumb(self, pid, inf):
        lab = QLabel(); lab.setFixedSize(*THUMB); lab.setAlignment(Qt.AlignTop | Qt.AlignLeft); lab.setWordWrap(True)
        lab.setStyleSheet("QLabel { border: 1px solid %s; background: white; color: #111111; padding: 4px; font-size: 7px; }"
                          % D.tokens()["border"])
        if inf.get("x"):
            path = SDZ.path_of(self.cfg(), inf["x"])
            png = self.png_of(path)
            if png:
                from PySide6.QtGui import QPixmap
                lab.setPixmap(QPixmap(png).scaled(lab.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return lab
            try:
                lines = [p["text"] for p in SDZ.read(path)["paragraphs"] if p["text"].strip()][:7]
            except Exception:  # noqa: BLE001
                lines = []
            lab.setText("\n".join(t[:22] for t in lines))
        elif inf.get("it"):
            lab.setText((inf["it"].get("summary") or inf["name"])[:90])
        return lab

    def show_version(self, family, pid):
        """A version tab clicked: the row shows that version (its picture, where it came from and its sets)."""
        self.shown_ver[family] = pid
        self.cur = pid
        self.fill_rows(); self.select(pid)
        return pid

    # ------------------------------------------------------------ the selected part
    def show_part(self, pid):
        self.cur = pid
        inf = self.info(pid) if pid else None
        self._guard = True
        self.fills.setRowCount(0)
        page = bool(inf and inf.get("x"))
        for w in (self.fills_lab, self.fills, self.others_lab, self.others):
            w.setVisible(page)
        self.filler.setVisible(not page)
        self.problems.setText(""); self.problems.setVisible(False)
        if inf is None:
            self.title.setText(""); self.thumb.clear(); self.thumb_note.setText("")
            self._guard = False
            return None
        self.title.setText(f"{inf['name']}" + (f" v{inf['version']}" if len(self.versions(pid)) > 1 else "")
                           + (f": {inf['label']}" if inf.get("label") else "") + f"  ·  {inf['what']}")
        if not page:
            v = inf["values"]
            self.thumb.setText(inf["it"].get("summary") or "")
            import prodquickparts as QP
            self.thumb_note.setText(f"In Word's {QP.gallery_name(v.get('gallery') or '')} gallery. Right-click: Change it... (the style "
                                    "first, Make a variant, or in Word); Details for its category and the pages it fills.")
            self._guard = False
            return inf
        x = inf["x"]
        path = SDZ.path_of(self.cfg(), x)
        try:
            info = SDZ.read(path)
        except Exception:  # noqa: BLE001
            diag.swallowed()
            self.problems.setText("This part's file could not be read."); self.problems.setVisible(True)
            self._guard = False
            return inf
        for p in info["paragraphs"]:
            if not p["text"].strip():
                continue
            r = self.fills.rowCount(); self.fills.insertRow(r)
            a = QTableWidgetItem(p["text"][:80]); a.setFlags(Qt.ItemIsEnabled); a.setData(Qt.UserRole, str(p["i"]))
            b = QTableWidgetItem(p["style"]); b.setFlags(Qt.ItemIsEnabled)
            c = QTableWidgetItem(x["map"].get(str(p["i"]), ""))
            self.fills.setItem(r, 0, a); self.fills.setItem(r, 1, b); self.fills.setItem(r, 2, c)
        png = self.png_of(path)
        if png:
            from PySide6.QtGui import QPixmap
            self.thumb.setPixmap(QPixmap(png).scaled(self.thumb.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.thumb_note.setText("Drawn by Word.")
        else:
            lines = [p["text"] for p in info["paragraphs"] if p["text"].strip()][:14]
            self.thumb.setText("\n\n".join(t[:34] for t in lines))
            self.thumb_note.setText("A sketch. Right-click the part: Draw with Word shows the exact page.")
        src = SDZ.other_pages(path)
        self.others.setText("\n".join(f"{s['style']}: {s['where'] or '(no paragraph in this style)'}"
                                      + ("  (in a text box)" if s["in_textbox"] else "") for s in src)
                            or "No header, footer or field here reads text from this part.")
        probs = SDZ.check(path)
        self.problems.setText("\n".join(probs)); self.problems.setVisible(bool(probs))
        self._guard = False
        return inf

    def versions(self, pid):
        if pid and pid.startswith("d:"):
            return ["d:" + y["id"] for y in PT.versions_of(self.cfg(), pid[2:])]
        it = self.lib.get(pid[2:]) if pid else None
        return ["q:" + i["id"] for i in self.lib.family(it["id"])] if it else []

    def fill_changed(self, item):
        if self._guard or item.column() != 2 or not (self.cur or "").startswith("d:"):
            return
        did = self.cur[2:]
        m = dict(SDZ.get(self.cfg(), did)["map"])
        m[self.fills.item(item.row(), 0).data(Qt.UserRole)] = item.text().strip()
        SDZ.set_map(self.cfg(), did, m)

    # ------------------------------------------------------------ selection and the row's menu
    def selected_ids(self):
        return [self.rows.item(i).data(Qt.UserRole) for i in range(self.rows.count()) if self.rows.item(i).isSelected()]

    def select(self, pid):
        for i in range(self.rows.count()):
            if self.rows.item(i).data(Qt.UserRole) == pid:
                self.rows.setCurrentRow(i)
                return True
        return False

    def row_menu(self, pos=None, run=True):
        ids = self.selected_ids()
        if not ids:
            return None
        m = QMenu(self)
        one = ids[0] if len(ids) == 1 else None
        if one and one.startswith("d:"):
            m.addAction("Open in Word").triggered.connect(lambda: self.open_word(one))
            m.addAction("Draw with Word").triggered.connect(lambda: self.draw(one))
            m.addAction("Bring back as a new version...").triggered.connect(lambda: self.new_version(one))
        if one and one.startswith("q:"):                     # 3.98.0: change a Quick Part, three ways
            m.addAction("Change it...").triggered.connect(lambda: self.change(one))
            m.addAction("Open in Word").triggered.connect(lambda: self.change(one, run=False).open_word())
            m.addAction("Bring back as a new version...").triggered.connect(lambda: self.change(one, run=False).bring_back())
            m.addAction("Details: category, gallery, pages it fills...").triggered.connect(lambda: self.quick_details(one))
        if one:
            m.addAction("Name this version...").triggered.connect(lambda: self.label_version(one))
        add = m.addMenu("Add to set")
        for k in SL.sets(self.lib, "part"):
            a = add.addAction(dot(k.get("color") or "#64748B"), k["name"])
            a.triggered.connect(lambda _c=False, sid=k["id"]: self.add_to_set(sid, ids))
        add.addSeparator()
        add.addAction("New part set...").triggered.connect(lambda: self.new_set(ids))
        if self.sid:
            m.addAction("Take out of this set").triggered.connect(lambda: self.take_out(ids))
        m.addSeparator()
        m.addAction("Remove from the library").triggered.connect(lambda: self.remove(ids))
        if run and pos is not None:
            m.exec(pos)
        return m

    # ------------------------------------------------------------ acting on a part
    def open_word(self, pid):
        if not (pid or "").startswith("d:"):
            return None
        p = SDZ.path_of(self.cfg(), SDZ.get(self.cfg(), pid[2:]))
        if os.environ.get("AH_TEST"):
            return p
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl.fromLocalFile(p))
        self.host.status("Opened in Word. Save your changes as a new file, then Bring back as a new version.")
        return p

    def draw(self, pid, runner=None):
        """Word lays out the part's first page (on demand; once until the file changes)."""
        import wordpreview as WP
        p = SDZ.path_of(self.cfg(), SDZ.get(self.cfg(), pid[2:]))
        with open(p, "rb") as f:
            data = f.read()
        res = WP.draw(SDZ._root(self.cfg()), data, runner=runner)
        if res.get("ok"):
            self.fill_rows(); self.select(pid)
        else:
            self.host.status(res.get("why", "Word could not draw the page."))
        return res

    def new_version(self, pid, path=None, label=None):
        from PySide6.QtWidgets import QFileDialog
        if path is None:
            path, _f = QFileDialog.getOpenFileName(self, "The changed Word file", "", "Word (*.docx *.dotx)")
            if not path:
                return None
        if label is None:
            label, ok = QInputDialog.getText(self, "Name this version", "A short name for what it is for (optional: CUI, compact...):")
            label = label if ok else ""
        y = PT.new_version(self.cfg(), pid[2:], path, label=label)
        if y is None:
            return None
        nid = "d:" + y["id"]
        self.shown_ver["d:" + PT.family(y)] = nid
        self.cur = nid
        diag.activity("part_version")
        self.host.toast(f"{y['name']} v{y['version']}: kept beside the others. Sets and setups that use an older one keep it.")
        self.fill_tabs(); self.fill_sets(); self.fill_rows(); self.select(nid)
        return y

    def label_version(self, pid, label=None):
        if label is None:
            label, ok = QInputDialog.getText(self, "Name this version", "A short name for what it is for (CUI, compact, page-limited):")
            if not ok:
                return False
        ok = PT.set_label(self.cfg(), pid[2:], label) if pid.startswith("d:") else bool(self.lib.set_label(pid[2:], label) or True)
        self.fill_rows(); self.select(pid)
        return ok

    def change(self, pid, run=True):
        from .partchange import change
        return change(self, pid[2:], run)

    def after_change(self, it, st, what):
        """A changed part: its row shows the new version (the one before stays)."""
        self.lib.fresh()
        nid = "q:" + it["id"]
        self.shown_ver["q:" + (it.get("family") or it["id"])] = nid
        self.cur = nid
        self.fill_tabs(); self.fill_sets(); self.fill_rows(); self.select(nid)
        self.host.toast({"same": "The library has this version already: it is shown."}.get(st, f"{self.lib.base_of(it)} v{it.get('version')}: "
                        "kept beside the others. Sets that use an older one keep it."))
        return nid

    def quick_details(self, pid):
        self.host.go("qpstd")
        return self.host.qpstd_page.select(pid[2:])

    def remove(self, ids):
        used = [i for i in ids if PT.sets_of(self.lib, i)]
        if used:
            self.host.status(f"{len(used)} of these are in a part set: take them out of their sets first.")
            return 0
        for i in ids:
            if i.startswith("d:"):
                SDZ.remove(self.cfg(), i[2:])
            else:
                self.lib.remove(i[2:])
        self.cur = None
        self.fill_tabs(); self.fill_sets(); self.fill_rows()
        return len(ids)

    # ------------------------------------------------------------ part sets
    def new_set(self, ids=None, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "New part set", "Name of the set (what it is for: RFP volume, Page-limited RFP, CUI):")
            if not ok:
                return None
        k = SL.new_set(self.lib, name, kind="part")
        if k is None:
            self.host.status("A set needs a name that no other part set has.")
            return None
        if ids:
            PT.add_to_set(self.cfg(), self.lib, k["id"], ids)
        diag.activity("part_set_new")
        self.fill_sets(); self.fill_rows()
        return k

    def rename_set(self, name=None):
        k = SL.get_set(self.lib, self.sid) if self.sid else None
        if k is None:
            self.host.status("Pick a part set on the left first.")
            return False
        if name is None:
            name, ok = QInputDialog.getText(self, "Rename the set", "New name:", text=k["name"])
            if not ok:
                return False
        ok = SL.rename_set(self.lib, k["id"], name=name)
        if not ok:
            self.host.status("Another set has that name.")
        self.fill_sets(); self.fill_rows()
        return ok

    def remove_set(self):
        k = SL.get_set(self.lib, self.sid) if self.sid else None
        if k is None:
            self.host.status("Pick a part set on the left first.")
            return False
        SL.remove_set(self.lib, k["id"])
        self.host.toast(f"{k['name']} taken away; its parts stay in the library.")
        self.sid = None
        self.fill_sets(); self.fill_rows()
        return True

    def add_to_set(self, sid, ids):
        gone = PT.add_to_set(self.cfg(), self.lib, sid, ids)
        k = SL.get_set(self.lib, sid)
        diag.activity("part_set_added", n=len(ids))
        self.host.toast(f"{len(ids)} part(s) in {k['name']}" + (f"; {len(gone)} other version(s) of them taken out" if gone else ""))
        self.fill_sets(); self.fill_rows()
        return gone

    def take_out(self, ids):
        n = SL.take_out(self.lib, self.sid, ids)
        self.fill_sets(); self.fill_rows()
        return n

    def bring_in(self, path=None, run=True):
        from .partimport import bring_in
        return bring_in(self, path, run)
