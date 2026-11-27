"""4.84.0 offscreen (step I2; Nicholas 2026-11-27 13:29 "go"): Add documents says, once for every file from the customer,
what the files are Part of (the package) and what they Arrived as (a dated release that numbers itself); a row can say
otherwise or Not said; the release is kept on each version and is its label; Documents groups by release with its date,
and right-click > Arrived as (was Package) lists the releases; files whose release was said are not asked again; the
solicitation number is left out when names are matched; a package the team names is kept; the strip is not shown for
our own files or in a program. An effort from before 4.84.0 reads as it did (qt_packages4254). Fictional (Heron)."""
import os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import docintake as DI, docpackages as DP, docversions as DV, effort as E, workspace as W, pdfmini
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme, docgroups as DG, releasestrip as RS
from skqt.intakedialog import IntakeDialog, COLS, C_ARRIVED
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


# ---- the rules, no window
check("a release's name: an amendment has four digits, a draft its number, the rest their own name",
      DP.release_name("Amendment", 2) == "Amendment 0002" and DP.release_name("Draft RFP", 2) == "Draft RFP 2"
      and DP.release_name("Final RFP", 3) == "Final RFP" and DP.kind_of_name("Q&A set 1") == ("Q&A set", 1))


class _Lib:
    all, extra = [], {}


check("read from the names: an amendment and its number", DP.guess(_Lib(), ["Heron_Amendment_0003_SF30.pdf"]) == ("Solicitation", "Amendment", 3),
      DP.guess(_Lib(), ["Heron_Amendment_0003_SF30.pdf"]))
check("... a draft RFP", DP.guess(_Lib(), ["Heron DRFP2 Section L.pdf"]) == ("Solicitation", "Draft RFP", 2), DP.guess(_Lib(), ["Heron DRFP2 Section L.pdf"]))
check("... an RFI is Pre-RFP", DP.guess(_Lib(), ["Heron_RFI.pdf"])[:2] == ("Pre-RFP (RFI / Sources Sought)", "RFI"))
check("... and with nothing to go on, the Solicitation's Final RFP", DP.guess(_Lib(), ["Heron Section L.pdf", "SOW.pdf"]) == ("Solicitation", "Final RFP", None))
check("the solicitation number is left out of the name when matching, however it is written",
      DV.name_similarity("W912DY24R0001_Section_L.pdf", "Section L.pdf", ["W912DY-24-R-0001"]) == 1.0
      and DV.name_similarity("W912DY24R0001_Section_L.pdf", "Section L.pdf") < 1.0
      and DV.stem("w912dy_24_r_0001 SOW Amd 0002.docx", ["W912DY-24-R-0001"]) == "sow")
check("... a number too short to strip safely is not used", DV.number_pattern("R-01") is None)


def wait(page):
    t0 = time.time()
    while page.worker is not None and time.time() - t0 < 120:
        app.processEvents(); time.sleep(0.02)
    app.processEvents()


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Heron"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Heron_Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST, customer_dir=CD, solicitation="W912DY-24-R-0001")
ws = W.Workspace(W.data_dir_for(LIST), "Heron")
SAMP = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk")


def copy(src, name):
    p = os.path.join(tmp, name); shutil.copy2(os.path.join(SAMP, src), p); return p


SEC_L = ["L.1 GENERAL", "The offeror shall submit three volumes.", "L.2 VOLUME I", "Volume I shall not exceed 50 pages.",
         "L.3 VOLUME II", "Volume II shall describe the management approach.", "L.4 VOLUME III", "Volume III is the price."]


def pdf(name, lines):
    p = os.path.join(tmp, name); pdfmini.write(p, [lines], size=9); return p


app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.open_effort("Heron"); app.processEvents()
w.go("library"); app.processEvents()
lp = w.library_page

# ---- the first add: the Final RFP
F_L = pdf("W912DY24R0001_Section_L.pdf", SEC_L)
F_SOW = pdf("W912DY24R0001_SOW.pdf", ["C.1 SCOPE", "The contractor shall operate the ground segment.", "C.2 TASKS", "Task 1 is operations."])
F_NOTE = os.path.join(tmp, "Heron capture notes.txt")
open(F_NOTE, "w", encoding="utf-8").write("Our own notes for the capture team. Nothing in here is a requirement.\n")
lib = DV.Library(ws.p("documents")).load()
lib.numbers = DP.numbers(lib, "W912DY-24-R-0001")
plan = DI.plan(lib, [F_L, F_SOW, F_NOTE], DI.read)
for e in plan:
    if e["path"] == F_NOTE:
        e["category"] = "ours"
dlg = IntakeDialog(lp, plan, lib, lp.effort_rec())
st = dlg.strip
check("the default Name leaves the solicitation number out", plan[0]["name"] == "Section L", plan[0]["name"])
check("the strip: Part of the Solicitation, Arrived as the Final RFP, today", st.isVisibleTo(dlg) and st.part_name() == "Solicitation"
      and st.release() == "Final RFP" and st.day() == QDate.currentDate().toString("yyyy-MM-dd") and not st.num.isVisibleTo(dlg),
      (st.part_name(), st.release()))
check("... with the three packages every effort has and New package...", [st.part.itemText(k) for k in range(st.part.count())]
      == ["Solicitation", "Pre-RFP (RFI / Sources Sought)", "Discussions & FPR", "New package..."])
check("... and the releases the direction names", [st.kind.itemText(k) for k in range(st.kind.count())] == list(DP.KINDS))
check("the table has an Arrived as column after Version", COLS.index("Arrived as") == COLS.index("Version") + 1 and not dlg.table.isColumnHidden(C_ARRIVED))
r_note = [e["path"] for e in plan].index(F_NOTE)
r_l = [e["path"] for e in plan].index(F_L)
check("each customer row follows the strip; our own file shows nothing there",
      dlg.rows[r_l]["arrived"].currentText() == "Solicitation: Final RFP" and dlg.rows[r_l]["cells"][C_ARRIVED].control.isVisibleTo(dlg)
      and not dlg.rows[r_note]["cells"][C_ARRIVED].control.isVisibleTo(dlg), dlg.rows[r_l]["arrived"].currentText())
st.date.setDate(QDate(2026, 11, 2)); app.processEvents()
out = dlg.result_plan()
got = {os.path.basename(e["path"]): (e.get("part_of"), e.get("arrived_as"), e.get("arrived_on")) for e in out}
check("Add carries Part of, Arrived as and the date for the customer's files, nothing for ours",
      got["W912DY24R0001_Section_L.pdf"] == ("Solicitation", "Final RFP", "2026-11-02") and got["Heron capture notes.txt"] == (None, None, None), got)
made = DI.apply(lib, out, CD)
lib = DV.Library(ws.p("documents")).load()
dL = next(d for d in lib.all if d["versions"][0]["file"] == "W912DY24R0001_Section_L.pdf")
v0 = dL["versions"][0]
check("kept on the version, and it is the version's label (was Original)", v0.get("part_of") == "Solicitation" and v0.get("arrived_as") == "Final RFP"
      and v0.get("arrived_on") == "2026-11-02" and v0.get("label") == "Final RFP", v0)
lp.refresh(); app.processEvents()
rows = [lp.table.item(r, 0).text() for r in range(lp.table.rowCount())]
check("Documents groups by the release, with its date and count", any(x.startswith("Solicitation: Final RFP   ·   2026-11-02   ·   2 documents") for x in rows), rows)
check("... and our own file under Internal", any(x.startswith("Internal") for x in rows), rows)
iL = next(r for r in range(lp.table.rowCount()) if lp.table.item(r, 0).data(0x0100) == dL["id"])
check("the Version column reads the release and when it was added", lp.table.item(iL, 3).text().startswith("Final RFP"), lp.table.item(iL, 3).text())

# ---- the second add: an amendment re-posts Section L, with a new attachment and the SF 30
F_L2 = pdf("W912DY24R0001_Section_L_Amd_0001.pdf", SEC_L[:3] + ["Volume I shall not exceed 40 pages."] + SEC_L[4:])
F_ATT = pdf("Heron_Wage_Determination.pdf", ["WAGE DETERMINATION", "Rates by labor category for the site."])
lib = DV.Library(ws.p("documents")).load()
lp.lib = lib
lib.numbers = DP.numbers(lib, "W912DY-24-R-0001")
plan = DI.plan(lib, [F_L2, F_ATT], DI.read)
dlg = IntakeDialog(lp, plan, lib, lp.effort_rec())
dlg.show(); app.processEvents()
st = dlg.strip
check("the next add: Arrived as an amendment, numbered from the file's name", st.part_name() == "Solicitation" and st.release() == "Amendment 0001"
      and st.num.isVisibleTo(dlg) and st.num.text() == "0001", (st.release(), st.num.text()))
r2 = [e["path"] for e in plan].index(F_L2)
check("... Section L's new file is matched to Section L, the solicitation number left out", dlg.kind(r2) == "version"
      and dlg.rows[r2]["what"].currentData() == ("version", dL["id"]), dlg.rows[r2]["what"].currentText())
items = [dlg.rows[r2]["arrived"].itemText(k) for k in range(dlg.rows[r2]["arrived"].count())]
check("a row can pick an earlier release or Not said", items == ["Solicitation: Amendment 0001", "Solicitation: Final RFP", "Not said"], items)
st.num.setValue(2); app.processEvents()
check("change the number: every row follows", dlg.rows[r2]["arrived"].currentText() == "Solicitation: Amendment 0002")
rA = [e["path"] for e in plan].index(F_ATT)
dlg.rows[rA]["arrived"].setCurrentIndex(dlg.rows[rA]["arrived"].findText("Not said"))
out = dlg.result_plan()
check("a row set to Not said carries no release", "arrived_as" not in out[rA] and out[r2]["arrived_as"] == "Amendment 0002")
made = DI.apply(lib, out, CD)
lib = DV.Library(ws.p("documents")).load()
dL = lib.doc(dL["id"])
check("the new version arrived as Amendment 0002 and is labelled so; the first keeps Final RFP",
      [v.get("label") for v in dL["versions"]] == ["Final RFP", "Amendment 0002"] and dL["versions"][1].get("arrived_as") == "Amendment 0002",
      [v.get("label") for v in dL["versions"]])
dW = next(d for d in lib.all if d["versions"][0]["file"] == "Heron_Wage_Determination.pdf")
check("the file left Not said is labelled as before", dW["versions"][0].get("label") == "Original" and not DP.first_release(dW))
check("Section L stays in the release that brought it", DP.of(lib, dL) == DP.release_key("Solicitation", "Final RFP"))
check("the releases, oldest first", [r["name"] for r in DP.releases(lib)] == ["Final RFP", "Amendment 0002"], DP.releases(lib))
check("the next amendment would be 0003", DP.next_number(lib, "Solicitation", "Amendment") == 3)

# ---- Documents: right-click > Arrived as
lp.lib = lib; lp.refresh(); app.processEvents()
m = QMenu(); pm = DG.menu(lp, m, lib.doc(dW["id"]))
acts = [(a.text(), a.isChecked()) for a in pm.actions()] if pm else None
check("right-click > Arrived as (was Package) lists As issued and each release, the current one ticked",
      pm is not None and pm.title() == "Arrived as" and acts == [("As issued", True), ("Solicitation: Final RFP", False), ("Solicitation: Amendment 0002", False)], acts)
n = DG.set_package(lp, DP.release_key("Solicitation", "Amendment 0002"), [dW["id"]])
lib2 = DV.Library(ws.p("documents")).load()
check("pick a release: it is kept on the document's first version", n == 1 and DP.first_release(lib2.doc(dW["id"]))[:2] == ("Solicitation", "Amendment 0002"))
check("... and files whose release is said are not asked about again (4.29.1's question)", DG.new_in(lib2, [(lib2.doc(dW["id"]), None)]) == [])
DG.set_package(lp, DP.ISSUED, [dW["id"]])
check("As issued takes the release off again", not DP.first_release(DV.Library(ws.p("documents")).load().doc(dW["id"])))

# ---- a package the team names
lib = DV.Library(ws.p("documents")).load()
plan = DI.plan(lib, [copy("SOW.pdf", "Heron TO12 PWS.pdf")], DI.read)
dlg = IntakeDialog(lp, plan, lib, lp.effort_rec())
st = dlg.strip
st.part.setCurrentIndex(st.part.findText(RS.NEW_PACKAGE)); st._part_changed(name="Task Order 12", number="TO12-HER-0001")
check("New package...: named, picked, and its first release is a Final RFP", st.part_name() == "Task Order 12" and st.release() == "Final RFP")
dlg.accept()
lib = DV.Library(ws.p("documents")).load()
check("... kept with Documents on Add, its number used when names are matched",
      "Task Order 12" in DP.package_names(lib) and "TO12-HER-0001" in DP.numbers(lib, "W912DY-24-R-0001"), lib.extra)

# ---- the page itself gives the matcher the effort's solicitation number
seen = []
real_plan = DI.plan
DI.plan = lambda lib, *a, **k: (seen.append(tuple(lib.numbers)), real_plan(lib, *a, **k))[1]
lp.add(paths=[pdf("Heron_Site_Map.pdf", ["SITE MAP", "The ground station."])], choices={"Heron_Site_Map.pdf": {"initial": "Map", "type": "Attachment"}})
wait(lp)
DI.plan = real_plan
check("Documents > Add reads the effort's solicitation number and the packages' own", seen and "W912DY-24-R-0001" in seen[0] and "TO12-HER-0001" in seen[0], seen)

# ---- not shown for our own files, or in a program
plan = DI.plan(lib, [F_NOTE.replace("notes", "notes 2")] if shutil.copy2(F_NOTE, F_NOTE.replace("notes", "notes 2")) else [], DI.read)
for e in plan:
    e["category"] = "ours"
dlg = IntakeDialog(lp, plan, lib, lp.effort_rec())
check("only our own files: no strip, no column", not dlg.strip.isVisibleTo(dlg) and dlg.table.isColumnHidden(C_ARRIVED))
plan = DI.plan(lib, [copy("SOW.pdf", "Heron Program PWS.pdf")], DI.read)
dlg = IntakeDialog(lp, plan, lib, None)
check("in a program (no effort record): no strip, and nothing carried", not dlg.strip.isVisibleTo(dlg) and "arrived_as" not in dlg.result_plan()[0])
w.close()
print(f"QT ARRIVED 4840 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
