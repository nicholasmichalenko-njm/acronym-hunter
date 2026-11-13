"""Styles (3.94.0; claude/stationkeeper-libraries-and-sets.md, canvas "Libraries and Sets" boards 1 and 3): the one
place styles are brought in, made and grouped. One row per style version: its name, version and where it came from,
the sets it is in (colored chips); its font; its paragraph treatment; its characters; the rest; and a large preview on
real text. The sets are on the left: Every style, then each set with its color and count; drag rows onto a set to add
them. A set shown has a notice when a style it uses has a newer version (Move this set, or Keep). Bring in from a
document... reads only the styles of a Word file (styleimport). New style makes a simple one here. Rules only (No AI);
nothing leaves the PC."""
from PySide6.QtCore import QMimeData, Qt
from PySide6.QtGui import QColor, QDrag, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFontComboBox,
                               QFormLayout, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMenu, QPushButton, QVBoxLayout, QWidget)

import diag
import stylelib as SL
import templatelib as TL
from . import design as D
from .adaptive import FlowLayout
from .commandbar import CommandBar

MIME = "application/x-sk-style-ids"
SAMPLE_PARA = "Our ground segment hands each pass between the two sites in under 90 seconds."
SAMPLE_HEAD = "2.1  Telemetry, Tracking and Command"
SAMPLE_CHAR = "shall describe"
COLS = (210, 120, 190, 150, 140)          # 3.94.0's widths; 4.28.1: the name keeps its width, the details share the rest
NAME_W, BOX, SIZE_W = 210, (300, 58), 64   # 4.28.1 (answer 22): every preview box is one size; the style is drawn in it at true size
NAMED = (("Black", ""), ("Red", "C00000"), ("Dark red", "8B0000"), ("Purple", "7030A0"), ("Blue", "2E74B5"), ("Navy", "1F3864"),
         ("Green", "00B050"), ("Brown", "B45309"), ("Gray", "808080"))


def dot(color, size=12):
    pm = QPixmap(size, size); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing); p.setBrush(QColor(color)); p.setPen(Qt.NoPen)
    p.drawEllipse(0, 0, size, size); p.end()
    return QIcon(pm)


def sample_of(v, name=""):
    if v.get("type") == "character":
        return SAMPLE_CHAR
    if str(name).lower().startswith(("heading", "title")) or (v.get("size") or 0) >= 13:
        return SAMPLE_HEAD
    return SAMPLE_PARA


def preview(v, text=None, name=""):
    """A white strip with the text in the style's look (hidden text on a dotted band, as on the setup screen)."""
    lab = QLabel(text or sample_of(v, name))
    f = QFont(str(v.get("font") or "Calibri"))
    f.setPointSizeF(max(6.0, float(v.get("size") or 11)))
    f.setBold(bool(v.get("bold"))); f.setItalic(bool(v.get("italic"))); f.setUnderline(bool(v.get("underline")))
    f.setCapitalization(QFont.AllUppercase if v.get("caps") else QFont.MixedCase)
    lab.setFont(f)
    col = str(v.get("color") or "AUTO").lstrip("#").upper()
    col = "#111111" if col in ("AUTO", "") or len(col) != 6 else "#" + col
    band = "border-bottom:2px dotted #9CA3AF;" if v.get("hidden") else ""
    lab.setStyleSheet(f"QLabel{{background:#FFFFFF;color:{col};padding:8px 12px;border-radius:4px;{band}}}")
    lab.setWordWrap(True)
    lab.setMinimumWidth(0)
    from PySide6.QtWidgets import QSizePolicy
    lab.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
    lab.setObjectName("stylePreview")
    return lab


class PreviewBox(QWidget):
    """4.28.1 (answer 22): a white box, the same size on every row, with the style drawn in it at its true size. A style
    too big for the box is cut off at the box's edge; its real size is written beside the box."""

    def __init__(self, v, text=None, name=""):
        super().__init__()
        self.setObjectName("stylePreview")
        self.v, self.words = dict(v), text or sample_of(v, name)
        self.setFixedSize(*BOX)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setToolTip(f"{self.words}\n{size_words(v)}, drawn at its true size")

    def font_of(self):
        v = self.v
        f = QFont(str(v.get("font") or "Calibri"))
        f.setPointSizeF(max(1.0, float(v.get("size") or 11)))
        f.setBold(bool(v.get("bold"))); f.setItalic(bool(v.get("italic"))); f.setUnderline(bool(v.get("underline")))
        f.setCapitalization(QFont.AllUppercase if v.get("caps") else QFont.MixedCase)
        return f

    def cut_off(self):
        """True when the style at its true size is taller than the box. (A long sample always runs past the right edge.)"""
        from PySide6.QtGui import QFontMetricsF
        return QFontMetricsF(self.font_of()).height() > BOX[1] - 4

    def paintEvent(self, _e):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QFontMetricsF, QPen
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setRenderHint(QPainter.TextAntialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(QPen(QColor("#C9CED6"), 1)); p.setBrush(QColor("#FFFFFF")); p.drawRoundedRect(r, 4, 4)
        p.setClipRect(r.adjusted(1, 1, -1, -1))
        f = self.font_of(); p.setFont(f)
        fm = QFontMetricsF(f)
        col = str(self.v.get("color") or "AUTO").lstrip("#").upper()
        p.setPen(QColor("#111111" if col in ("AUTO", "") or len(col) != 6 else "#" + col))
        y = (self.height() - fm.height()) / 2 + fm.ascent() if fm.height() <= self.height() - 4 else 3 + fm.ascent()
        p.drawText(8, int(round(y)), self.words)
        if self.v.get("hidden"):                          # hidden text on a dotted band, as on the setup screen
            pen = QPen(QColor("#9CA3AF"), 2); pen.setStyle(Qt.DotLine); p.setPen(pen)
            p.drawLine(4, self.height() - 4, self.width() - 4, self.height() - 4)
        p.end()


def size_words(v):
    """The style's real size, written beside its box: "11 pt", or "As its base" when the style sets none."""
    return f"{SL._n(v['size'])} pt" if v.get("size") else "As its base"


def calm(w):
    """4.28.1: a row's words do not take the mouse, so a press anywhere on a row selects it and a drag carries every
    selected row (the version tabs still click)."""
    for c in w.findChildren(QWidget):
        if not isinstance(c, QPushButton) and not c.findChildren(QPushButton):
            c.setAttribute(Qt.WA_TransparentForMouseEvents)
    return w


class Rows(QListWidget):
    """The style rows; drag selected rows out (onto a set)."""
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setDragEnabled(True); self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda pos: page.row_menu(self.mapToGlobal(pos)))
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)          # the preview wraps; the rows never scroll sideways
        self.setResizeMode(QListWidget.Adjust)

    def startDrag(self, _actions):
        ids = self.page.selected_ids()
        if not ids:
            return
        md = QMimeData(); md.setData(MIME, ",".join(ids).encode())
        dr = QDrag(self); dr.setMimeData(md)
        dr.exec(Qt.CopyAction)


class SetList(QListWidget):
    """Every style, then the sets; rows dropped on a set go into it."""
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.setAcceptDrops(True); self.setDropIndicatorShown(True)
        self.setMinimumWidth(210); self.setMaximumWidth(260); self.setSpacing(3)

    def dragEnterEvent(self, e):
        e.acceptProposedAction() if e.mimeData().hasFormat(MIME) else e.ignore()

    def dragMoveEvent(self, e):
        it = self.itemAt(e.position().toPoint())
        ok = e.mimeData().hasFormat(MIME) and it is not None and it.data(Qt.UserRole)
        e.acceptProposedAction() if ok else e.ignore()

    def dropEvent(self, e):
        it = self.itemAt(e.position().toPoint())
        sid = it.data(Qt.UserRole) if it is not None else None
        if not sid:
            return e.ignore()
        ids = bytes(e.mimeData().data(MIME)).decode().split(",")
        self.page.add_to_set(sid, ids)
        e.acceptProposedAction()


class StylesPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.lib = TL.Library(host.config_dir)
        self.sid = None
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"])
        self.count = D.label("", "muted", wrap=False); top.addWidget(self.count, 1)
        self.find = QLineEdit(); self.find.setPlaceholderText("Find a style"); self.find.setClearButtonEnabled(True)
        self.find.setMinimumWidth(220); self.find.textChanged.connect(lambda _t: self.fill_rows())
        top.addWidget(self.find)
        from . import styleedit as SE                         # 4.30.1: paragraph or character styles; double-click a row
        SE.add_kind_filter(self, top)
        self.bar = CommandBar(self)
        self.b_new = self.bar.add("New style", lambda: self.new_style(), "A simple style made here: font, size, color, bold, italic, "
                                  "underline, hidden")
        self.b_bring = self.bar.primary("Bring in from a document...", lambda: self.bring_in(),
                                        "Only the styles of a Word file or template: tick the ones you keep (the file is only read)")
        self.bar.more("New set...", lambda: self.new_set())
        self.bar.more("Rename this set...", lambda: self.rename_set())
        self.bar.more("Take this set away", lambda: self.remove_set())
        self.bar.more_sep()                                   # 4.7.0: the values as a workbook, edited in Excel or here
        self.bar.more("Open the Company Standards workbook", lambda: __import__("skqt.teamlibview", fromlist=["x"])._open(
            __import__("teamlib").book_path(self.host.config_dir)), "Company Standards.xlsx in the team library, in Excel")
        top.addWidget(self.bar)
        v.addLayout(top)
        body = QHBoxLayout(); body.setSpacing(D.SPACE["l"])
        left = QVBoxLayout(); left.setSpacing(D.SPACE["s"])
        left.addWidget(D.label("SETS", "faint", wrap=False))
        self.sets = SetList(self)
        self.sets.currentItemChanged.connect(lambda cur, _p: self.pick_set(cur.data(Qt.UserRole) if cur is not None else None))
        left.addWidget(self.sets, 1)
        left.addWidget(D.label("Drag styles onto a set to add them. A style can be in many sets, one version in each.", "muted"))
        body.addLayout(left)
        mid = QVBoxLayout(); mid.setSpacing(D.SPACE["s"])
        self.notice = QFrame(); self.notice.setObjectName("pinStrip")
        nh = QHBoxLayout(self.notice); nh.setContentsMargins(D.SPACE["m"], 6, D.SPACE["m"], 6)
        self.notice_lab = D.label("", None); nh.addWidget(self.notice_lab, 1)
        self.b_move = D.button("Move this set", "primary", lambda: self.move_newer())
        self.b_keep = D.button("Keep", None, lambda: self.keep_newer())
        nh.addWidget(self.b_move); nh.addWidget(self.b_keep)
        self.notice.hide(); mid.addWidget(self.notice)
        head = QHBoxLayout(); head.setContentsMargins(8, 0, 8, 0)
        for t, w in (("Style", NAME_W), ("How it looks, at its true size", BOX[0] + 12), ("Size", SIZE_W)):     # 4.28.1
            lab = D.label(t, "label", wrap=False); lab.setFixedWidth(w); head.addWidget(lab)
        for t in ("Font", "Paragraph", "Characters", "Other"):
            head.addWidget(D.label(t, "label", wrap=False), 1)
        mid.addLayout(head)
        self.rows = Rows(self)
        self.rows.itemDoubleClicked.connect(lambda li: self.review(li.data(Qt.UserRole)))    # 4.30.1: review or change it here
        mid.addWidget(self.rows, 1)
        self.empty = D.EmptyState("No styles yet", "Bring in the styles of a Word file or template you already use: each one is "
                                  "kept with Word's own definition, and you choose which come in.", "Bring in from a document...",
                                  lambda: self.bring_in())
        mid.addWidget(self.empty)
        body.addLayout(mid, 1)
        v.addLayout(body, 1)
        self.kept_newer = set()
        self.shown_ver = {}                                # {style family: the version its row shows}

    # ------------------------------------------------------------ filling
    def refresh(self):
        self.lib.fresh()
        self.fill_sets()
        self.fill_rows()

    def fill_sets(self):
        keep = self.sid
        self.sets.blockSignals(True)
        self.sets.clear()
        n_all = len({i.get("family") or i["id"] for i in self.lib.items if i["kind"] == "style"})   # styles, not versions
        it = QListWidgetItem(f"Every style    {n_all}"); it.setData(Qt.UserRole, None)
        self.sets.addItem(it)
        for k in SL.sets(self.lib):
            x = QListWidgetItem(dot(k.get("color") or "#64748B"), f"{k['name']}    {len(k['items'])}")
            x.setData(Qt.UserRole, k["id"])
            self.sets.addItem(x)
        self.sets.setCurrentRow(next((i for i in range(self.sets.count()) if self.sets.item(i).data(Qt.UserRole) == keep), 0))
        self.sets.blockSignals(False)

    def pick_set(self, sid):
        self.sid = sid
        self.shown_ver = {}                              # a set's rows open on the versions it uses
        self.fill_rows()

    def fill_rows(self):
        rows = __import__("skqt.styleedit", fromlist=["x"]).keep_kind(self, SL.rows(self.lib, self.sid, self.find.text(), self.shown_ver))
        self.rows.clear()
        self.row_ids = []
        for r in rows:
            it = self.lib.get(r["shown"])
            v = self.lib.values(it) or {}
            w = self.row_widget(it, v, r["versions"])
            li = QListWidgetItem(); li.setData(Qt.UserRole, it["id"]); li.setSizeHint(w.sizeHint())
            self.rows.addItem(li); self.rows.setItemWidget(li, w)
            self.row_ids.append(it["id"])
        has = any(i["kind"] == "style" for i in self.lib.items)
        self.rows.setVisible(has); self.empty.setVisible(not has)
        k = SL.get_set(self.lib, self.sid) if self.sid else None
        self.count.setText((f"{k['name']}: {len(rows)} style(s)" if k else f"{len(rows)} style(s) · {len(SL.sets(self.lib))} set(s)")
                           if has else "")
        items = rows
        self.fill_notice()
        return items

    def row_widget(self, it, v, versions=None):
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(8, 6, 8, 6); h.setSpacing(0)
        c0 = QWidget(); c0.setFixedWidth(NAME_W); cv = QVBoxLayout(c0); cv.setContentsMargins(0, 0, 8, 0); cv.setSpacing(3)
        nm = D.label(f"<b>{self.lib.base_of(it)}</b>", None, wrap=False); nm.setTextFormat(Qt.RichText); cv.addWidget(nm)
        if versions and len(versions) > 1:                # 3.94.0 (19:16): the versions are tabs on the row
            tabs = QWidget(); tf = FlowLayout(tabs, 3)
            t = D.tokens()
            for x in versions:
                b = QPushButton(f"v{x['version']}" + (f" {x['label']}" if x.get("label") else "")); b.setCheckable(True)
                b.setChecked(x["id"] == it["id"]); b.setObjectName("verTab")
                b.setStyleSheet(f"QPushButton#verTab{{border:1px solid {t['border_strong']};border-radius:4px;padding:0 6px;font-size:11px;"
                                f"background:{t['surface']};color:{t['text']}}}QPushButton#verTab:checked{{border:2px solid {t['accent']};"
                                f"background:{t['accent_soft']};color:{t['accent']};font-weight:600}}")
                b.clicked.connect(lambda _c=False, f=x.get("family"), i=x["id"]: self.show_version(f, i))
                tf.addWidget(b)
            cv.addWidget(tabs)
            self.ver_tabs = getattr(self, "ver_tabs", {}); self.ver_tabs[it.get("family")] = tabs
        kind = D.label(("Character" if SL.kind_of(v) == "character" else "Paragraph") + " style", "faint", wrap=False)   # 4.30.1
        kind.setObjectName("styleKind"); cv.addWidget(kind)
        cv.addWidget(D.label(SL.version_words(self.lib, it, v), "muted"))
        chips = QWidget(); cf = FlowLayout(chips, 4)
        for k in SL.sets_of(self.lib, it["id"]):
            ch = QLabel(k["name"]); ch.setObjectName("setChip")
            ch.setStyleSheet(f"QLabel#setChip{{border:1px solid {k.get('color') or '#64748B'};border-radius:9px;padding:0 7px;font-size:11px}}")
            cf.addWidget(ch)
        cv.addWidget(chips)
        h.addWidget(c0)
        box = PreviewBox(v, name=self.lib.base_of(it))                # 4.28.1: beside the style, one size on every row
        bw = QWidget(); bw.setFixedWidth(BOX[0] + 12); bl = QVBoxLayout(bw); bl.setContentsMargins(0, 0, 12, 0); bl.addWidget(box); bl.addStretch(1)
        h.addWidget(bw)
        sz = D.label(size_words(v) + ("\ncut off" if box.cut_off() else ""), "muted", wrap=False); sz.setObjectName("styleSize"); sz.setFixedWidth(SIZE_W)
        sz.setAlignment(Qt.AlignTop | Qt.AlignLeft); h.addWidget(sz)
        d = SL.describe(v)
        for key in ("font", "paragraph", "characters", "other"):       # the details across the width, each with a share of it
            lab = D.label(d[key], None if key == "font" else "muted"); lab.setContentsMargins(0, 0, 10, 0); lab.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            if key == "font":
                fam = str(v.get("font") or "").replace('"', "").replace(";", "")       # the font named in itself
                lab.setStyleSheet(f'font-family:"{fam}";' if fam else "")
            lab.setMinimumWidth(60); h.addWidget(lab, 1)
        return calm(w)

    def fill_notice(self):
        nv = [(a, b) for a, b in (SL.newer(self.lib, self.sid) if self.sid else []) if (self.sid, a["id"], b["id"]) not in self.kept_newer]
        self.newer_now = nv[0] if nv else None
        if not nv:
            self.notice.hide()
            return None
        a, b = nv[0]
        self.notice_lab.setText(f"A newer version: {self.lib.base_of(b)} v{b['version']} came in ({SL.version_words(self.lib, b)}). "
                                f"This set uses v{a['version']}." + (f" ({len(nv) - 1} more)" if len(nv) > 1 else ""))
        self.b_move.setText(f"Move this set to v{b['version']}"); self.b_keep.setText(f"Keep v{a['version']}")
        self.notice.show()
        return nv

    def show_version(self, family, iid):
        """A version tab clicked: the row shows that version (its preview, values and sets)."""
        self.shown_ver[family] = iid
        self.fill_rows(); self.select(iid)
        return iid

    # ------------------------------------------------------------ selection and the row's menu
    def selected_ids(self):
        return [self.rows.item(i).data(Qt.UserRole) for i in range(self.rows.count()) if self.rows.item(i).isSelected()]

    def select(self, iid):
        for i in range(self.rows.count()):
            if self.rows.item(i).data(Qt.UserRole) == iid:
                self.rows.setCurrentRow(i)
                return True
        return False

    def row_menu(self, pos=None, run=True):
        ids = self.selected_ids()
        if not ids:
            return None
        m = QMenu(self)
        add = m.addMenu("Add to set")
        for k in SL.sets(self.lib):
            a = add.addAction(dot(k.get("color") or "#64748B"), k["name"])
            a.triggered.connect(lambda _c=False, sid=k["id"]: self.add_to_set(sid, ids))
        add.addSeparator()
        add.addAction("New set...").triggered.connect(lambda: self.new_set(ids))
        if self.sid:
            m.addAction("Take out of this set").triggered.connect(lambda: self.take_out(ids))
        if len(ids) == 1:
            m.addAction("See or change...").triggered.connect(lambda: self.review(ids[0]))        # 4.30.1; a double-click too
            m.addAction("Duplicate...").triggered.connect(lambda: self.duplicate(ids[0]))
            m.addAction("Name this version...").triggered.connect(lambda: self.label_version(ids[0]))
            m.addAction("Every value...").triggered.connect(lambda: self.every_value(ids[0]))      # 3.98.0
        m.addSeparator()
        m.addAction("Remove from the library").triggered.connect(lambda: self.remove(ids))
        if run and pos is not None:
            m.exec(pos)
        return m

    # ------------------------------------------------------------ sets
    def new_set(self, ids=None, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "New set", "Name of the set (what it is for: RFP volume, Page-limited RFP, Setup):")
            if not ok:
                return None
        k = SL.new_set(self.lib, name)
        if k is None:
            self.host.status("A set needs a name that no other set has.")
            return None
        if ids:
            SL.add_to_set(self.lib, k["id"], ids)
        diag.activity("style_set_new")
        self.fill_sets(); self.fill_rows()
        return k

    def rename_set(self, name=None):
        k = SL.get_set(self.lib, self.sid) if self.sid else None
        if k is None:
            self.host.status("Pick a set on the left first.")
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
            self.host.status("Pick a set on the left first.")
            return False
        SL.remove_set(self.lib, k["id"])
        self.host.toast(f"{k['name']} taken away; its styles stay in the library.")
        self.sid = None
        self.fill_sets(); self.fill_rows()
        return True

    def add_to_set(self, sid, ids):
        gone = SL.add_to_set(self.lib, sid, ids)
        k = SL.get_set(self.lib, sid)
        diag.activity("style_set_added", n=len(ids))
        self.host.toast(f"{len(ids)} style(s) in {k['name']}" + (f"; {len(gone)} other version(s) of them taken out" if gone else ""))
        self.fill_sets(); self.fill_rows()
        return gone

    def take_out(self, ids):
        n = SL.take_out(self.lib, self.sid, ids)
        self.fill_sets(); self.fill_rows()
        return n

    def move_newer(self):
        if not self.newer_now:
            return False
        a, b = self.newer_now
        ok = SL.move(self.lib, self.sid, a["id"], b["id"])
        self.host.toast(f"This set now uses {self.lib.base_of(b)} v{b['version']}.")
        self.fill_sets(); self.fill_rows()
        return ok

    def keep_newer(self):
        if not self.newer_now:
            return False
        a, b = self.newer_now
        self.kept_newer.add((self.sid, a["id"], b["id"]))
        self.fill_notice()
        return True

    # ------------------------------------------------------------ styles
    def new_style(self, name=None, typ="paragraph", look=None, marks=""):
        if name is None:
            dlg = StyleForm(self)
            if dlg.exec() != QDialog.Accepted:
                return None
            name, typ, look, marks = dlg.result_values()
        it, st = SL.new_style(self.lib, name, typ, look or {}, marks)
        if it is None:
            self.host.status("A style needs a name.")
            return None
        if self.sid and st != "same":
            SL.add_to_set(self.lib, self.sid, [it["id"]])
        self.host.toast({"new": f"{name}: made", "variant": f"{name}: a new version", "same": f"{name}: the library has this look already"}[st])
        diag.activity("style_made")
        self.fill_sets(); self.fill_rows(); self.select(it["id"])
        return it

    def change_look(self, iid, look=None):
        it = self.lib.get(iid)
        if it is None:
            return None
        v = self.lib.values(it) or {}
        if look is None:
            dlg = StyleForm(self, self.lib.base_of(it), v, change=True)
            if dlg.exec() != QDialog.Accepted:
                return None
            _n, _t, look, _m = dlg.result_values()
        new, st = SL.change_style(self.lib, iid, look)
        self.shown_ver[new.get("family")] = new["id"]
        self.host.toast(f"{self.lib.base_of(it)} v{new['version']}: " + ("kept beside the others" if st == "version" else "the same look as a version you have"))
        self.fill_sets(); self.fill_rows(); self.select(new["id"])
        return new

    def review(self, iid, values=None):
        """4.30.1: the style's own form: its font, size, characters and paragraph, to read or change. A new version."""
        from . import styleedit as SE
        return SE.review(self, iid, values)

    def duplicate(self, iid, name=None, values=None):
        """4.30.1: a new style under its own name with this one's values."""
        from . import styleedit as SE
        return SE.duplicate(self, iid, name, values)

    def label_version(self, iid, label=None):
        if label is None:
            label, ok = QInputDialog.getText(self, "Name this version", "A short name for what it is for (compact, page-limited):")
            if not ok:
                return False
        self.lib.set_label(iid, label)
        self.fill_rows(); self.select(iid)
        return True

    def every_value(self, iid):
        """3.98.0: every value of the style (spacing, keeps, numbering, borders...) on Formatting, opened on it."""
        self.host.go("formatstd")
        return self.host.formatstd_page.select(iid)

    def remove(self, ids):
        used = [i for i in ids if SL.sets_of(self.lib, i)]
        if used:
            self.host.status(f"{len(used)} of these are in a set: take them out of their sets first.")
            return 0
        for i in ids:
            self.lib.remove(i)
        self.fill_sets(); self.fill_rows()
        return len(ids)

    def bring_in(self, path=None, run=True):
        from .styleimport import bring_in
        return bring_in(self, path, run)


class StyleForm(QDialog):
    """A simple style: name, paragraph or character, what it marks, font, size, color, bold, italic, underline, hidden,
    with its look as you set it."""
    def __init__(self, parent, name="", v=None, change=False):
        super().__init__(parent)
        v = v or {"type": "paragraph", "font": "Calibri", "size": 11}
        self.setWindowTitle("Make a copy to change" if change else "New style")
        f = QFormLayout(self)
        if change:
            f.addRow(D.label("Saved as a new version; the version you started from stays, and so do the sets that use it.", "muted"))
        self.name = QLineEdit(name); self.name.setEnabled(not change); f.addRow("Name", self.name)
        self.kind = QComboBox(); self.kind.addItem("Paragraph style", "paragraph"); self.kind.addItem("Character style", "character")
        self.kind.setCurrentIndex(1 if v.get("type") == "character" else 0); self.kind.setEnabled(not change)
        f.addRow("Kind", self.kind)
        self.marks = QLineEdit(v.get("_marks", "")); self.marks.setPlaceholderText("What it marks (Compliance language, Guidance...)")
        f.addRow("What it marks", self.marks)
        self.font = QFontComboBox(); self.font.setCurrentFont(QFont(str(v.get("font") or "Calibri"))); f.addRow("Font", self.font)
        self.size = QDoubleSpinBox(); self.size.setRange(5, 72); self.size.setSingleStep(0.5); self.size.setValue(float(v.get("size") or 11))
        f.addRow("Size", self.size)
        self.color = QComboBox()
        for t, hx in NAMED:
            self.color.addItem(dot("#" + hx if hx else "#111111"), t, hx)
        cur = str(v.get("color") or "").lstrip("#").upper()
        i = self.color.findData("" if cur in ("AUTO", "") else cur)
        if i < 0 and cur:
            self.color.addItem(dot("#" + cur), f"#{cur}", cur); i = self.color.count() - 1
        self.color.setCurrentIndex(max(0, i)); f.addRow("Color", self.color)
        row = QHBoxLayout()
        self.bold, self.italic, self.under, self.hidden = (QCheckBox(t) for t in ("Bold", "Italic", "Underline", "Hidden"))
        for cb, k in ((self.bold, "bold"), (self.italic, "italic"), (self.under, "underline"), (self.hidden, "hidden")):
            cb.setChecked(bool(v.get(k))); row.addWidget(cb)
        f.addRow("Look", row)
        self.sample_box = QVBoxLayout(); f.addRow("How it looks", self.sample_box)
        self.sample = None
        for w in (self.font, self.size, self.color, self.bold, self.italic, self.under, self.hidden, self.kind):
            sig = getattr(w, "currentIndexChanged", None) or getattr(w, "valueChanged", None) or getattr(w, "toggled", None)
            sig.connect(lambda *_a: self.redraw())
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Save the style")
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject); f.addRow(bb)
        self.redraw()

    def look(self):
        return {"font": self.font.currentFont().family(), "size": self.size.value(), "color": self.color.currentData() or "",
                "bold": self.bold.isChecked(), "italic": self.italic.isChecked(), "underline": self.under.isChecked(),
                "hidden": self.hidden.isChecked()}

    def redraw(self):
        if self.sample is not None:
            self.sample.hide(); self.sample.setParent(None)
        v = dict(self.look(), type=self.kind.currentData())
        self.sample = preview(v, name=self.name.text())
        self.sample_box.addWidget(self.sample)

    def result_values(self):
        return self.name.text(), self.kind.currentData(), self.look(), self.marks.text()
