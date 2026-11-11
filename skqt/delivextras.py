"""Deliverables page extras (3.62.0): open one deliverable's page, Format groups..., and Arrange (drag to set the
team's order). Kept apart from custdocs.py, which is at its size limit."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QDialogButtonBox, QHBoxLayout, QHeaderView, QInputDialog, QListWidget,
                               QListWidgetItem, QTableWidget, QTableWidgetItem, QVBoxLayout)
import diag
import deliverables as DL
import delivmore as DM
from . import design as D


def install(page):
    """Wraps the page's board and list in a stack with the deliverable's own page; adds the buttons."""
    from PySide6.QtWidgets import QStackedWidget, QWidget, QVBoxLayout as V
    from .delivpage import DeliverableView
    lay = page.layout()
    page.all_box = QWidget(); av = V(page.all_box); av.setContentsMargins(0, 0, 0, 0)
    for w in (page.sugg, page.board_split, page.list_box):
        lay.removeWidget(w); av.addWidget(w, 1 if w is not page.sugg else 0)
    page.stack = QStackedWidget(); page.stack.addWidget(page.all_box)
    page.one = DeliverableView(page); page.stack.addWidget(page.one)
    lay.addWidget(page.stack, 1)
    page.view.addItem("Arrange")
    from PySide6.QtWidgets import QComboBox
    top = lay.itemAt(0).layout()
    page.order_mode = QComboBox(); page.order_mode.addItems(["Needs attention first", "Your order"])
    page.order_mode.currentIndexChanged.connect(lambda _i: page.refresh())
    top.insertWidget(1, page.order_mode)
    top.insertWidget(top.count() - 1, D.button("Format groups...", None, lambda: page.groups_window()))
    page.arrange_box = arrange_list(page); av.addWidget(page.arrange_box, 1); page.arrange_box.hide()
    from . import delivdelete as DD                                  # 4.12.0: delete, with Undo
    DD.install(page)


def arrange_list(page):
    from PySide6.QtWidgets import QWidget
    w = QWidget(); v = QVBoxLayout(w); v.setContentsMargins(0, 0, 0, 0)
    v.addWidget(D.label("Drag the deliverables into the order the team works in. The board and the list follow it; the "
                        "board can still put the ones needing attention first.", "muted"))
    page.order_list = QListWidget(); page.order_list.setDragDropMode(QAbstractItemView.InternalMove)
    page.order_list.model().rowsMoved.connect(lambda *_a: save_order(page))
    v.addWidget(page.order_list, 1)
    return w


def fill_order(page):
    page.order_list.blockSignals(True)
    page.order_list.clear()
    for d in DL.items(page.ctx.rec) if page.ctx is not None else []:
        it = QListWidgetItem(f"{d['name']}    ({d.get('kind') or 'Deliverable'}, {d.get('owner') or 'no owner'})")
        it.setData(Qt.UserRole, d["id"])
        page.order_list.addItem(it)
    page.order_list.blockSignals(False)


def save_order(page, ids=None):
    ids = ids or [page.order_list.item(i).data(Qt.UserRole) for i in range(page.order_list.count())]
    out = DM.arrange(page.ctx.rec, ids)
    diag.activity("deliverables_arranged")
    page.refresh()
    return out


def show_view(page, i):
    page.board_split.setVisible(i == 0); page.list_box.setVisible(i == 1); page.arrange_box.setVisible(i == 2)
    if i == 2:
        fill_order(page)


def open_one(page, did, tab=None):
    if page.ctx is None or DL.get(page.ctx.rec, did) is None:
        return False
    page.stack.setCurrentWidget(page.one)
    return page.one.show(did, tab)


def close_one(page):
    page.stack.setCurrentWidget(page.all_box)
    page.refresh()
    return True


def groups_window(page, run=True):
    """Format groups: one row per group, one column per field; type in a cell to set the group's value."""
    rec = page.ctx.rec
    dlg = QDialog(page); dlg.setWindowTitle("Format groups"); dlg.resize(980, 460)
    v = QVBoxLayout(dlg)
    v.addWidget(D.label("Set the formatting and submission once for deliverables of the same kind (for example Written "
                        "volumes, Forms, Slides). A deliverable in a group takes its values unless it sets its own.", "muted"))
    t = QTableWidget(0, 1 + len(DM.FIELDS)); t.setHorizontalHeaderLabels(["Group"] + [lab for _k, lab in DM.FIELDS])
    t.verticalHeader().setVisible(False); t.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    v.addWidget(t, 1)
    state = {"loading": False}

    def fill():
        state["loading"] = True
        gs = DM.groups(rec)
        t.setRowCount(len(gs))
        for i, g in enumerate(gs):
            a = QTableWidgetItem(g["name"]); a.setData(Qt.UserRole, g["id"]); t.setItem(i, 0, a)
            for j, (k, _lab) in enumerate(DM.FIELDS, 1):
                t.setItem(i, j, QTableWidgetItem(g["values"].get(k, "")))
        state["loading"] = False

    def changed(it):
        if state["loading"]:
            return
        gid = t.item(it.row(), 0).data(Qt.UserRole)
        if it.column() == 0:
            DM.rename_group(rec, gid, it.text())
        else:
            DM.set_group_value(rec, gid, DM.FIELDS[it.column() - 1][0], it.text())
    t.itemChanged.connect(changed)

    def add(name=None):
        if name is None:
            name, ok = QInputDialog.getText(dlg, "New format group", "Name (for example Written volumes):")
            if not ok:
                return None
        gid = DM.add_group(rec, name)
        fill()
        return gid

    def remove():
        r = t.currentRow()
        if r >= 0:
            DM.remove_group(rec, t.item(r, 0).data(Qt.UserRole))
            fill()
    row = QHBoxLayout(); v.addLayout(row)
    row.addWidget(D.button("+ Group...", "primary", lambda: add()))
    row.addWidget(D.button("Remove", "danger", lambda: remove()))
    row.addStretch(1)
    bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(dlg.reject); bb.accepted.connect(dlg.accept); row.addWidget(bb)
    dlg.table, dlg.add, dlg.remove, dlg.fill = t, add, remove, fill
    fill()
    if run:
        dlg.exec()
        page.refresh()
        if page.stack.currentWidget() is page.one:
            page.one.fill_tab()
    return dlg
