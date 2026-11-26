"""4.78.0 (E1): Effort Settings in four plain groups, kept as each field is changed, with Customer, Solicitation number
and Proposal due one value each with Customer information. Fictional (Kestrel)."""
import datetime, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
import app_gui as A
import custinfo as CI, effort as E, effortrec as RR, workspace as W
from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.open_effort("Kestrel"); app.processEvents()
rp, cp = w.record_page, w.custinfo_page
w.go("record"); app.processEvents()
heads = [l.text() for l in rp.findChildren(QLabel) if l.property("role") == "h3" and l.isVisibleTo(rp)]
check("four plain groups: Effort, People, Stages and reviews, Files and sources", heads == ["Effort", "People", "Stages and reviews", "Files and sources"], heads)
check("no Save button on the page; the bar keeps only Export", not [b for b in rp.findChildren(QPushButton) if b.text().startswith("Save") and b.isVisibleTo(rp)]
      and "Save details" not in rp.bar.labels() and "Save stages" not in rp.bar.labels(), rp.bar.labels())
check("an empty field reads Not set", rp.client.placeholderText() == "Not set" and rp.sol.placeholderText() == "Not set"
      and rp.due_date.text() == "Not set", rp.due_date.text())
check("Saved in shows the effort's folder", rp.saved_in.text() == ED, rp.saved_in.text())

# typed on Effort Settings: kept at once, and the same value on Customer information
rp.client.setText("Office of Orbital Logistics"); rp.client.editingFinished.emit()
rp.sol.setText("FA8811-26-R-0099"); rp.sol.editingFinished.emit()
rp.internal.setText("A-1234"); rp.internal.editingFinished.emit()
L2 = E.EffortList(LIST).load()
check("Customer, Solicitation number and A number are kept as typed (no Save)", (L2.client, L2.solicitation, L2.internal_no) ==
      ("Office of Orbital Logistics", "FA8811-26-R-0099", "A-1234"), (L2.client, L2.solicitation, L2.internal_no))
rec = RR.Record(w.ws.root)
check("... Customer information shows the same values", CI.fact(rec, "Customer", L2)["value"] == "Office of Orbital Logistics"
      and CI.fact(rec, "Solicitation number", L2)["value"] == "FA8811-26-R-0099")
check("... and Customer is the first fact on Customer information", CI.LABELS[0] == "Customer")
w.go("custinfo"); app.processEvents()
row = lambda lab: next(r for r in range(cp.facts.rowCount()) if cp.facts.item(r, 0).text() == lab)
check("... on the page itself", cp.facts.item(row("Solicitation number"), 1).text() == "FA8811-26-R-0099"
      and cp.facts.item(row("Customer"), 1).text() == "Office of Orbital Logistics")

# typed on Customer information: Effort Settings and the effort list follow
cp.set_value("Solicitation number", "FA8811-26-R-0100"); app.processEvents()
L3 = E.EffortList(LIST).load()
check("typed on Customer information: the effort list holds it", L3.solicitation == "FA8811-26-R-0100", L3.solicitation)
w.go("record"); app.processEvents()
check("... and Effort Settings shows it", rp.sol.text() == "FA8811-26-R-0100", rp.sol.text())
check("... the effort registry knows it too", (E.Registry(os.path.join(cfg, "efforts.json")).get("Kestrel") or {}).get("solicitation") == "FA8811-26-R-0100")

# Proposal due: one value
w.go("custinfo"); app.processEvents()
cp.set_value("Proposal due", "December 15, 2026, 2:00 p.m. Eastern Time"); app.processEvents()
rec = RR.Record(w.ws.root)
check("Proposal due typed on Customer information sets the effort's due date and zone", rec.data["due"] == "2026-12-15T14:00"
      and rec.data["zone"] == "ET", (rec.data["due"], rec.data["zone"]))
check("... and reads back as the same value", cp.facts.item(row("Proposal due"), 1).text() == RR.due_text("2026-12-15T14:00", "ET"),
      cp.facts.item(row("Proposal due"), 1).text())
cp.set_value("Proposal due", "sometime next month"); app.processEvents()
check("... words with no date change nothing", RR.Record(w.ws.root).data["due"] == "2026-12-15T14:00")
w.go("record"); app.processEvents()
check("Effort Settings shows that due date", rp.due_date.date() == QDate(2026, 12, 15) and rp.due_time.time() == QTime(14, 0) and rp.zone.text() == "ET")
rp.due_date.setDate(QDate(2026, 12, 18)); rp.flush()
check("changing the date on Effort Settings is kept a moment later", RR.Record(w.ws.root).data["due"] == "2026-12-18T14:00")
w.go("custinfo"); app.processEvents()
check("... and Customer information shows the new date", cp.facts.item(row("Proposal due"), 1).text() == RR.due_text("2026-12-18T14:00", "ET"))

# stages: kept without Save stages
w.go("record"); app.processEvents()
n = rp.stage_table.rowCount()
rp.add_stage("Pink team"); rp.flush()
r = RR.Record(w.ws.root)
check("a stage added is kept without a Save button", len(r.stages) == n + 1 and r.stages[-1]["name"] == "Pink team", [s["name"] for s in r.stages])
rp.set_stage(rp.stage_table.rowCount() - 1, start=("2026-12-01", ""), gate="soft"); rp.flush()
r = RR.Record(w.ws.root)
check("... its date and gate are kept, and no second copy is made", len(r.stages) == n + 1 and r.stages[-1]["planned"] == "2026-12-01"
      and r.gate_of(r.stages[-1]) == "soft", [(s["name"], s.get("planned")) for s in r.stages])
rp.set_stage(rp.stage_table.rowCount() - 1, start=("2026-12-05", ""), end=("2026-12-01", "")); rp.flush()
check("a stage that ends before it starts is not kept, and the line says why", RR.Record(w.ws.root).stages[-1]["planned"] == "2026-12-01"
      and "ends before it starts" in rp.stage_note.text(), rp.stage_note.text())

w.close(); app.processEvents()
print(f"QT EFFORT SETTINGS 4780 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
