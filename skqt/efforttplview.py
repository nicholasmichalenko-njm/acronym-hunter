"""An effort type's templates on screen (4.41.0; ST27 step 5). Effort types... > Templates...: for the selected effort
type, one row per profile with the template it starts with. The start form says what the chosen effort type brings.
Setup's Templates for the volumes offers the effort type's templates for the volumes with none picked. efforttemplates
holds the rules; nothing leaves the PC."""
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QHeaderView, QTableWidget, QTableWidgetItem,
                               QVBoxLayout)

import diag
import efforttemplates as ET
import namedtemplates as NT
import prodrules as PRL
from . import design as D

NONE = "No template: the effort's own formatting"


class TemplatesOfType(QDialog):
    """The templates one effort type starts with: a row for each of its profiles."""

    def __init__(self, parent, config_dir, eid):
        super().__init__(parent)
        self.cfg, self.eid = config_dir, eid
        e = PRL.effort_type_of(PRL.load(config_dir), eid) or {"name": ""}
        self.setWindowTitle(f"Templates for {e['name']}"); self.resize(720, 380)
        v = QVBoxLayout(self)
        self.note = D.label(f"An effort of the type {e['name']} starts with these templates: each brings its style sets, its Quick "
                            "Part set and its starting pages. Setup still lets one volume pick another.", "muted")
        v.addWidget(self.note)
        self.t = QTableWidget(0, 3); self.t.setHorizontalHeaderLabels(["Profile", "Its volumes", "Template"])
        self.t.verticalHeader().setVisible(False); self.t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t.setColumnWidth(0, 200); self.t.setColumnWidth(1, 200); self.t.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.t.verticalHeader().setDefaultSectionSize(34); self.t.setProperty("sk_rows_fixed", True)
        v.addWidget(self.t, 1)
        bb = QDialogButtonBox(QDialogButtonBox.Close); bb.rejected.connect(self.accept); bb.accepted.connect(self.accept); v.addWidget(bb)
        self.boxes = {}
        self.fill()

    def fill(self):
        every = NT.every(self.cfg)
        self.t.setRowCount(0); self.boxes = {}
        for r in ET.brings(self.cfg, self.eid):
            i = self.t.rowCount(); self.t.insertRow(i)
            self.t.setItem(i, 0, QTableWidgetItem(r["profile"])); self.t.setItem(i, 1, QTableWidgetItem(", ".join(r["volumes"])))
            cb = QComboBox(); cb.addItem(NONE, "")
            for t in every:
                cb.addItem(t["name"] + ("" if NT.state(self.cfg, t)[0] != NT.NEW else "  (not made yet)"), t["id"])
            cb.setCurrentIndex(max(0, cb.findData(r["tid"])))
            cb.activated.connect(lambda _i, p=r["pid"], c=cb: self.pick(p, c.currentData()))
            self.t.setCellWidget(i, 2, cb); self.boxes[r["pid"]] = cb
        if not every:
            self.note.setText("No template is named yet. Name one in Templates > Template, then come back.")

    def pick(self, pid, tid):
        ok = ET.put(self.cfg, self.eid, pid, tid or "")
        diag.activity("effort_type_template", n=int(bool(tid)))
        self.fill()
        return ok


def templates(parent, config_dir, eid, run=True):
    """Effort types... > Templates...: returns the dialog, or None with no effort type selected."""
    if not eid:
        return None
    dlg = TemplatesOfType(parent, config_dir, eid)
    if run:
        dlg.exec()
    return dlg


def start_words(config_dir, eid):
    """The start form's line under Effort type ('' for None)."""
    return ET.words(ET.brings(config_dir, eid)) if eid else ""


def offer_words(host, volumes):
    """(the sentence, how many) for Templates for the volumes: what the effort type would pick."""
    eid = ((host.ws.get("prod_std") or {}) if host.ws is not None else {}).get("effort_type") or ""
    off = ET.offer(host.config_dir, eid, volumes, NT.picks(host.ws)) if eid else []
    if not off:
        return "", 0
    return " The effort type names a template for " + ", ".join(f"{v} ({t['name']})" for v, t in off[:4]) + (" and more" if len(off) > 4 else "") + ".", len(off)


def use_type(dlg):
    """Templates for the volumes > Use the effort type's templates: picks them for the volumes with none."""
    host = dlg.host
    eid = ((host.ws.get("prod_std") or {}) if host.ws is not None else {}).get("effort_type") or ""
    M = dlg.page._M()
    done = ET.apply(M, host.ws, host.config_dir, eid, dlg.page.volume_names(), host.effort_path or "") if (M is not None and eid) else []
    if done:
        diag.activity("volume_templates_from_type", n=len(done))
        dlg.page.changed()
        host.toast(f"{len(done)} volume{'' if len(done) == 1 else 's'} now use{'s' if len(done) == 1 else ''} the effort type's template.")
    dlg.fill()
    return done
