"""4.25.4 offscreen: packages (Documents board 2026-11-12, step D). With no amendment the list is as it was. With one,
the list is in groups (As issued, the amendment, Internal); a document's earlier versions sit under it; Package on the
row moves a document; the choice is saved as one optional key and an Internal document takes none. Fictional (Osprey)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import docintake as DI, docversions as DV, docpackages as DP, effort as E, workspace as W, pdfmini
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
from skqt import design as D
from skqt import docgroups as DG
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Osprey"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)


def pdf(name, lines):
    p = os.path.join(CD, name); pdfmini.write(p, [lines], size=9); return p


P1 = pdf("Osprey_Section_L.pdf", ["L.3 VOLUMES", "Volume I shall not exceed 50 pages."])
P2 = pdf("Osprey_Section_L_Amd1.pdf", ["L.3 VOLUMES", "Volume I shall not exceed 40 pages."])
PS = pdf("Osprey_SOW.pdf", ["C.1 SCOPE", "The contractor shall operate the ground segment."])
PA = pdf("Osprey_Amendment_1.pdf", ["AMENDMENT 1", "Section L is replaced."])
PF = pdf("Osprey_Pricing_Form.pdf", ["PRICING FORM", "Enter the rates."])
PN = os.path.join(ED, "notes.pdf"); pdfmini.write(PN, [["Our notes", "Call the teammate."]], size=9)
LIST = os.path.join(ED, "Osprey_Effort_List.xlsx"); L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Osprey")
lib = DV.Library(ws.p("documents")).load()
dL, _v = lib.add(P1, DI.read(P1), doc_name="Section L", role="matrix", initial="Sec L", dtype="Section L")
dS, _v = lib.add(PS, DI.read(PS), doc_name="Statement of Work", role="context", initial="SOW", dtype="SOW")
dN, _v = lib.add(PN, DI.read(PN), doc_name="Notes", category="ours")
check("no amendment: no groups, every customer document is As issued, an Internal one is in none",
      not DP.has_groups(lib) and DP.of(lib, dL) == DP.ISSUED and DP.of(lib, dN) == "" and DP.packages(lib) == [(DP.ISSUED, "As issued")])

app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Osprey"); app.processEvents()
w.go("library"); app.processEvents()
pg = w.library_page
t = pg.table


def col0():
    return [t.item(r, 0).text() for r in range(t.rowCount())]


check("... and the list has one line per document, as before", t.rowCount() == 3 and not any("As issued" in x for x in col0()), col0())

lib = pg.lib
dA, _v = lib.add(PA, DI.read(PA), doc_name="Amendment 1", role="matrix", initial="Amd1", dtype="Amendment")
dF, _v = lib.add(PF, DI.read(PF), doc_name="Pricing Form", role="reference", initial="Att", dtype="Attachment")
lib.add(P2, DI.read(P2), doc_id=dL["id"], label="Amd1")
pg.fill(); app.processEvents()
rows = col0()
check("an amendment arrives: the list is in groups, As issued, the amendment, Internal",
      [x.split("   ")[0] for x in rows if "document" in x and "·" in x] == ["As issued", "Amendment 1", "Internal"], rows)
check("... each group's line counts its documents", rows[0].endswith("3 documents") and any(x.startswith("Amendment 1") and x.endswith("1 document") for x in rows), rows)
check("... the amendment is in its own package", DP.of(lib, lib.doc(dA["id"])) == dA["id"])
iL = next(r for r in range(t.rowCount()) if t.item(r, 0).data(Qt.UserRole) == dL["id"])
check("a document with two versions shows the earlier one on a line under it",
      t.item(iL + 1, 0).text().strip().startswith("earlier:") and t.item(iL + 1, 0).data(Qt.UserRole) == dL["id"], rows)
t.selectRow(iL + 1); app.processEvents()
check("... a click on that line selects the document", pg.current_id() == dL["id"] and pg.selected_ids() == [dL["id"]])
t.selectRow(0)
check("a group's line selects nothing", pg.selected_ids() == [], pg.selected_ids())

pg.select(dF["id"])
m = QMenu(); pm = DG.menu(pg, m, lib.doc(dF["id"]))
check("right-click a customer document: Package lists As issued and the amendment, the current one ticked",
      pm is not None and [(a.text(), a.isChecked()) for a in pm.actions()] == [("As issued", True), ("Amendment 1", False)],
      [(a.text(), a.isChecked()) for a in pm.actions()] if pm else None)
check("... not offered on the amendment itself or on an Internal document",
      DG.menu(pg, QMenu(), lib.doc(dA["id"])) is None and DG.menu(pg, QMenu(), lib.doc(dN["id"])) is None)
n = DG.set_package(pg, dA["id"])
rows = col0()
iA = next(r for r in range(t.rowCount()) if t.item(r, 0).text().startswith("Amendment 1   "))
check("pick the amendment: the document moves under it, after the amendment", n == 1 and rows[iA].endswith("2 documents")
      and "Amendment 1" in rows[iA + 1] and "Pricing Form" in rows[iA + 2], rows)
lib2 = DV.Library(ws.p("documents")).load()
check("... saved as one key on the document; the others carry none", lib2.doc(dF["id"]).get("package") == dA["id"]
      and "package" not in lib2.doc(dS["id"]) and "package" not in lib2.doc(dA["id"]))
check("an Internal document and the amendment itself cannot be moved", DP.set_package(lib, [dN["id"], dA["id"]], DP.ISSUED) == 0)
DG.set_package(pg, DP.ISSUED, [dF["id"]])
check("back to As issued: the key is removed", "package" not in DV.Library(ws.p("documents")).load().doc(dF["id"]))
DP.set_package(lib, [dF["id"]], dA["id"]); lib.doc(dA["id"])["withdrawn"] = {"when": "2026-11-12T10:00", "who": "t"}; lib.save()
check("the amendment is withdrawn: its documents read As issued again, nothing is lost", DP.of(lib, lib.doc(dF["id"])) == DP.ISSUED
      and lib.doc(dF["id"]).get("package") == dA["id"])
lib.doc(dA["id"]).pop("withdrawn"); lib.save()
pg.search.setText("pricing"); pg.fill(); app.processEvents()
check("with Find in use the groups are off: the hits read as one list", not any("   ·   " in x for x in col0()) and any("Pricing Form" in x for x in col0()), col0())
pg.search.setText(""); pg.fill(); app.processEvents()
pg.type_f.setCurrentIndex(pg.type_f.findData("use:shred")); app.processEvents()
check("a filter keeps the groups and counts what it shows", any(x.startswith("As issued") and x.endswith("1 document") for x in col0()), col0())
# ---- 4.29.1 (answer 5 of 2026-11-13): files added after an amendment is in: asked once which package brought them
pg.type_f.setCurrentIndex(0); pg.fill(); app.processEvents()
from PySide6.QtWidgets import QInputDialog
PQ = pdf("Osprey_Wage_Table.pdf", ["WAGE TABLE", "Rates by labor category."])
PR2 = pdf("Osprey_Site_Map.pdf", ["SITE MAP", "The ground station."])
lib = pg.lib
dQ, vQ = lib.add(PQ, DI.read(PQ), doc_name="Wage Table", role="reference", initial="Att2", dtype="Attachment")
dR, vR = lib.add(PR2, DI.read(PR2), doc_name="Site Map", role="reference", initial="Att3", dtype="Attachment")
_d, vL3 = lib.add(pdf("Osprey_Section_L_Amd2.pdf", ["L.3 VOLUMES", "Volume I shall not exceed 45 pages."]), DI.read(P2), doc_id=dL["id"], label="later")
made = [(dQ, vQ), (dR, vR), (lib.doc(dL["id"]), vL3)]
check("what is asked about: the customer's new documents; a new version of one already in keeps its package",
      [d["name"] for d in DG.new_in(lib, made)] == ["Wage Table", "Site Map"], [d["name"] for d in DG.new_in(lib, made)])
asked = []
QInputDialog.getItem = staticmethod(lambda parent, title, text, names, cur, edit: (asked.append((title, text, list(names), names[cur])) or (names[cur], True)))
n = DG.ask_package(pg, made)
check("one question for the whole add, naming how many, the latest amendment offered first", len(asked) == 1 and "2 documents are new" in asked[0][1]
      and asked[0][2] == ["As issued", "Amendment 1"] and asked[0][3] == "Amendment 1", asked)
check("... both go in the package picked", n == 2 and DP.of(pg.lib, pg.lib.doc(dQ["id"])) == dA["id"] and DP.of(pg.lib, pg.lib.doc(dR["id"])) == dA["id"])
check("... asked once: nothing left to ask about", DG.ask_package(pg, made) == 0 and len(asked) == 1)
PT = pdf("Osprey_Travel_Rules.pdf", ["TRAVEL", "Travel is reimbursed at cost."])
dT, vT = pg.lib.add(PT, DI.read(PT), doc_name="Travel Rules", role="reference", initial="Att4", dtype="Attachment")
QInputDialog.getItem = staticmethod(lambda *a: ("", False))
check("Cancel leaves it As issued", DG.ask_package(pg, [(dT, vT)]) == 0 and DP.of(pg.lib, pg.lib.doc(dT["id"])) == DP.ISSUED)
check("an Internal file is never asked about", DG.new_in(pg.lib, [(pg.lib.doc(dN["id"]), None)]) == [])
w.close()
print(f"QT PACKAGES 4254 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
