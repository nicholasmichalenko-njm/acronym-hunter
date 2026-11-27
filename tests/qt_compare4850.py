"""4.85.0 offscreen (step I3; Nicholas 2026-11-27 14:47 "Go"): compare at intake. In Add documents a New version of a
customer document says Compare with, ticked, and the version it is compared with. After the add one summary says what it
brought ("3 files: 1 new version, 1 new document, 1 already added."), in place of a What changed card per new version:
each new version with what it changed, Review the N in What changed opening the first with a line that links the next; and
the package's documents this release did not replace, in force unless ticked. A ticked one is marked no longer in force
(kept; it stops building the matrix) and right-click > Back in force undoes it. Not shown in a program, nor for a first
release with nothing before it. Timings of the summary are printed for E2. Fictional (Heron)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import docintake as DI, docpackages as DP, docversions as DV, effort as E, workspace as W, pdfmini
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme, docgroups as DG, intakesummary as IS
from skqt.intakedialog import IntakeDialog, COLS, C_COMPARE, C_ARRIVED
from skqt.mainwin import MainWindow
import hangguard

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def wait(page):
    t0 = time.time()
    while page.worker is not None and time.time() - t0 < 120:
        app.processEvents(); time.sleep(0.02)
    app.processEvents()


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Heron"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST, customer_dir=CD, solicitation="W912DY-24-R-0001")
ws = W.Workspace(W.data_dir_for(LIST), "Heron")


def pdf(name, lines):
    p = os.path.join(tmp, name); pdfmini.write(p, [lines], size=9); return p


SEC_L = ["L.1 GENERAL", "The offeror shall submit three volumes.", "L.2 VOLUME I", "Volume I shall not exceed 50 pages.",
         "L.3 VOLUME II", "Volume II shall describe the management approach.", "L.4 VOLUME III", "Volume III is the price."]
SOW = ["C.1 SCOPE", "The contractor shall operate the ground segment.", "C.2 TASKS", "Task 1 is operations."]
PWS = ["PWS 1", "The contractor shall staff the help desk.", "PWS 2", "Hours are 0700 to 1900."]

app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.open_effort("Heron"); app.processEvents()
w.go("library"); app.processEvents()
lp = w.library_page

# ---- the Final RFP: a first release, nothing before it, so no summary
F_L, F_SOW, F_PWS = pdf("Section_L.pdf", SEC_L), pdf("SOW.pdf", SOW), pdf("PWS.pdf", PWS)
FINAL = {"part_of": "Solicitation", "arrived_as": "Final RFP", "arrived_on": "2026-11-02"}
lp.add(paths=[F_L, F_SOW, F_PWS], choices={"Section_L.pdf": dict(FINAL, initial="L", type="Section L"),
                                           "SOW.pdf": dict(FINAL, initial="C", type="SOW"),
                                           "PWS.pdf": dict(FINAL, initial="P", type="PWS")})
wait(lp)
check("a first release with nothing before it shows no summary", getattr(lp, "last_summary", "x") is None, getattr(lp, "last_summary", "x"))
lib = DV.Library(ws.p("documents")).load()
dL = next(d for d in lib.all if d["name"] == "Section L")
dS = next(d for d in lib.all if d["name"] == "SOW")
dP = next(d for d in lib.all if d["name"] == "PWS")

# ---- the window: Compare on a new version
F_L2 = pdf("Section_L_Amd_0001.pdf", SEC_L[:3] + ["Volume I shall not exceed 40 pages."] + SEC_L[4:])
F_ATT = pdf("Wage_Determination.pdf", ["WAGE DETERMINATION", "Rates by labor category for the site."])
lib.numbers = DP.numbers(lib, "W912DY-24-R-0001")
plan = DI.plan(lib, [F_L2, F_ATT, F_SOW], DI.read)
dlg = IntakeDialog(lp, plan, lib, lp.effort_rec())
dlg.show(); app.processEvents()
names = [os.path.basename(e["path"]) for e in plan]
r2, rA, rS = names.index("Section_L_Amd_0001.pdf"), names.index("Wage_Determination.pdf"), names.index("SOW.pdf")
check("Compare with sits after Arrived as", COLS.index("Compare with") == C_ARRIVED + 1 == C_COMPARE)
box = dlg.rows[r2]["cmp"]
check("a new version says Compare with, ticked, with the version it is compared with", dlg.kind(r2) == "version" and not dlg.table.isColumnHidden(C_COMPARE)
      and box.isVisibleTo(dlg) and box.isChecked() and box.text() == "Final RFP", (dlg.kind(r2), box.text()))
check("... a new document and the same file show nothing there", not dlg.rows[rA]["cmp"].isVisibleTo(dlg) and not dlg.rows[rS]["cmp"].isVisibleTo(dlg))
dlg.rows[r2]["what"].setCurrentIndex(0); app.processEvents()
check("make it a New document: the Compare column goes", dlg.table.isColumnHidden(C_COMPARE))
wt = dlg.rows[r2]["what"]
wt.setCurrentIndex(next(k for k in range(wt.count()) if wt.itemData(k) == ("version", dL["id"]))); app.processEvents()
check("... and comes back with New version of", not dlg.table.isColumnHidden(C_COMPARE) and box.isVisibleTo(dlg))
dlg.grab().save(os.path.join(tmp, "add.png"))
out = dlg.result_plan()
check("Add carries the tick", out[r2].get("compare") is True and out[rA].get("compare") is False, (out[r2].get("compare"), out[rA].get("compare")))
plan_p = DI.plan(lib, [F_L2], DI.read)
dlg_p = IntakeDialog(lp, plan_p, lib, None)
check("in a program (no effort record): no Compare with", dlg_p.table.isColumnHidden(C_COMPARE) and dlg_p.result_plan()[0].get("compare") is False)
dlg.reject(); dlg_p.reject()

# ---- the add: Amendment 0001 re-posts Section L, with a new attachment; the SOW again is the same file
AMD = {"part_of": "Solicitation", "arrived_as": "Amendment 0001", "arrived_on": "2026-11-20"}
t0 = time.time()
lp.add(paths=[F_L2, F_ATT, F_SOW], choices={"Section_L_Amd_0001.pdf": dict(AMD, choice="version", doc=dL["id"], compare=True),
                                            "Wage_Determination.pdf": dict(AMD, initial="WD", type="Attachment")})
wait(lp)
print(f"TIMING add with the summary of one new version: {time.time() - t0:.2f} s (offscreen, small fictional PDFs)")
dlg = getattr(lp, "last_summary", None)
check("after the add: one summary", isinstance(dlg, IS.SummaryDialog), dlg)
lab = [x.text() for x in dlg.findChildren(QLabel)] if dlg else []
check("... its line counts what the add brought", "3 files: 1 new version, 1 new document, 1 already added." in lab, lab)
check("... its title names the release", dlg.windowTitle() == "Added: Solicitation: Amendment 0001", dlg.windowTitle())
it = dlg.versions.item(0)
check("... each new version with what it changed, ticked", dlg.versions.count() == 1 and it.checkState() == Qt.Checked
      and it.text().startswith("Section L   Final RFP to Amendment 0001") and "changed" in it.text(), it.text())
check("... no What changed card is left to show one by one", w.last_changes and len(w.last_changes) == 1)
conf = [dlg.confirm.item(i).text() for i in range(dlg.confirm.count())]
check("... the documents the amendment did not replace, in force unless ticked", len(conf) == 2 and conf[0].startswith("PWS")
      and conf[1].startswith("SOW") and all(dlg.confirm.item(i).checkState() == Qt.Unchecked for i in range(2))
      and "Not in Amendment 0001" in lab, conf)
check("... the new attachment and Section L are not asked about", not any(x.startswith(("Section L", "Wage")) for x in conf))
check("Review in What changed is the main button", dlg.b_compare.isVisibleTo(dlg) and dlg.b_compare.text() == "Review it in What changed" and dlg.b_compare.isDefault())
it.setCheckState(Qt.Unchecked); app.processEvents()
check("untick it: Done is the one button", not dlg.b_compare.isVisibleTo(dlg) and dlg.b_done.isDefault())
it.setCheckState(Qt.Checked)
m = dlg.version_menu(dlg.versions.visualItemRect(it).center(), run=False)
check("right-click a version: Show on the page", m is not None and [a.text() for a in m.actions()] == ["Show on the page"])
dlg.show(); app.processEvents()
dlg.grab().save(os.path.join(tmp, "summary.png"))
dlg.confirm.item(0).setCheckState(Qt.Checked)                  # the PWS is no longer in force
rows = dlg.compare_now()
app.processEvents()
lib = DV.Library(ws.p("documents")).load()
dPn = lib.doc(dP["id"])
check("it opens What changed on the new version", w.compare_page.isVisible() and w.compare_page.sel[0] == dL["id"]
      and w.compare_page.cur[2]["label"] == "Amendment 0001", w.compare_page.sel)
check("a ticked document is no longer in force: kept, marked with the release, no longer building the matrix",
      DP.no_longer(dPn) == "Amendment 0001" and lib.role_of(dPn) == "reference" and dPn["withdrawn"]["role"] == "matrix", dPn.get("withdrawn"))
check("... the SOW, not ticked, stays in force", not lib.doc(dS["id"]).get("withdrawn"))
check("... and it stays in its release group", DP.of(lib, dPn) == DP.release_key("Solicitation", "Final RFP"))
w.go("library"); app.processEvents()
lp.lib = lib; lp.refresh(); app.processEvents()
txt = [lp.table.item(r, 0).text() + " | " + lp.table.item(r, 5).text() for r in range(lp.table.rowCount())]
lp.grab().save(os.path.join(tmp, "documents.png"))
check("Documents says so on its row", any(x.startswith("PWS") and x.endswith("| No longer in force with Amendment 0001") for x in txt), txt)
mm = QMenu(); DG.menu(lp, mm, lib.doc(dP["id"]))
acts = [a.text() for a in mm.actions()]
check("right-click: Back in force", "Back in force" in acts, acts)
check("Back in force undoes it, with the purpose it had", DG.back_in_force(lp, dP["id"]) and not DV.Library(ws.p("documents")).load().doc(dP["id"]).get("withdrawn")
      and DV.Library(ws.p("documents")).load().role_of(DV.Library(ws.p("documents")).load().doc(dP["id"])) == "matrix")

# ---- Amendment 0002 re-posts the SOW and the PWS: Compare the 2, one after the other
F_S2 = pdf("SOW_Amd_0002.pdf", SOW[:3] + ["Task 1 is operations and maintenance."])
F_P2 = pdf("PWS_Amd_0002.pdf", PWS[:3] + ["Hours are 0600 to 1800."])
AMD2 = {"part_of": "Solicitation", "arrived_as": "Amendment 0002", "arrived_on": "2026-11-25"}
lp.add(paths=[F_S2, F_P2], choices={"SOW_Amd_0002.pdf": dict(AMD2, choice="version", doc=dS["id"], compare=True),
                                    "PWS_Amd_0002.pdf": dict(AMD2, choice="version", doc=dP["id"], compare=True)})
wait(lp)
dlg = lp.last_summary
check("two new versions: Review the 2 in What changed", dlg is not None and dlg.versions.count() == 2 and dlg.b_compare.text() == "Review the 2 in What changed")
conf = [dlg.confirm.item(i).text() for i in range(dlg.confirm.count())]
check("... and the documents still in force not in it: Section L and the attachment", [c.split("   ")[0] for c in conf] == ["Section L", "Wage Determination"], conf)
dlg.compare_now(); app.processEvents()
cp = w.compare_page
check("What changed says which of the new versions this is, and links the next", cp.qline.isVisibleTo(cp) and cp.qline.text().startswith("1 of 2 new versions from Amendment 0002")
      and "Next: " in cp.qline.text(), cp.qline.text())
first = cp.sel[0]
cp.next_in_queue(); app.processEvents()
check("... Next opens the second, and the line has no next", cp.sel[0] != first and cp.qline.text().startswith("2 of 2") and "Next" not in cp.qline.text(), cp.qline.text())
cv = getattr(getattr(cp, "cards", None), "versions", None)
check("... the list of new versions beside the cards picks it too", cv is None or cv.currentItem().data(Qt.UserRole) == cp.sel)
cp.grab().save(os.path.join(tmp, "compare.png"))
cp.show(dL["id"]); app.processEvents()
check("... another pair picked: the line goes", not cp.qline.isVisibleTo(cp))

# ---- the rules alone
check("the line of an add", IS.line({"files": 12, "new": 3, "versions": 7, "same": 2, "replaced": 0}) == "12 files: 7 new versions, 3 new documents, 2 already added.")
check("the release of an add is the one most of its files arrived as", DP.release_of_add([dict(AMD, choice="new"), dict(AMD, choice="version"),
      dict(FINAL, choice="new"), {"choice": "new"}]) == ("Solicitation", "Amendment 0001") and DP.release_of_add([{"choice": "new"}]) is None)
w.close()
print(f"QT COMPARE 4850 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
print("PICTURES", tmp)
hangguard.end(0 if all(checks) else 1)
