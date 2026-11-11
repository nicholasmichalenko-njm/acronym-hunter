"""4.4.0 Drafts > Status by volume (claude/stationkeeper-drafts-plan-4.4.md, steps 1, 2 and 4), offscreen, on an effort read
from the fictional RFP with a two-volume outline: Volume folders keeps one folder per volume with the effort; each
volume's draft is the newest Word file in its folder (Word's ~$ lock files ignored); Read the drafts reads both, the table
shows each volume's file, when it was saved and its counts, each read is kept in the record, and a volume clicked shows
its sections. A volume with no folder says so. Drafts' tabs are Status, Acronyms and Edit. Fictional content only."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, workspace as W, office_pdf as OP, setupdoc as SD, effortrec as RR, setupread as SR, docxw, draftvols as DV
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow, TABS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk\n"
                                                 "Volume II Management\n2.1 Management Plan")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf", "SOW.pdf")]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


check("Drafts' tabs: Status, Acronyms, Edit (Color Reviews and Wall of Truth set aside)",
      [k for k, _t in TABS["drafts"]][:3] == ["drafts", "draftacr", "techedit"], TABS["drafts"])
w.open_effort("Kestrel")
w.read_page.read(PDFS, os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page)
M = w.review.M
vols = DV.volumes(M)
check("two volumes from the outline", len(vols) == 2 and vols[0].startswith("Volume I") and vols[1].startswith("Volume II"), vols)


def draft(path, vol, secs, words):
    doc = docxw.Doc()
    doc.heading(vol, 1)
    for lab in secs:
        doc.heading(lab, 2)
        doc.rich([(" ".join(["kestrel"] * words), None)])
    doc.save(path)
    return path


F1, F2 = os.path.join(tmp, "lib1"), os.path.join(tmp, "lib2"); os.makedirs(F1); os.makedirs(F2)
old = draft(os.path.join(F1, "Tech v1.docx"), vols[0], ["1.1 Technical Approach", "1.2 Risk"], 10)
new = draft(os.path.join(F1, "Tech v2.docx"), vols[0], ["1.1 Technical Approach", "1.2 Risk"], 200)
os.utime(old, (time.time() - 3600, time.time() - 3600))
open(os.path.join(F1, "~$ch v2.docx"), "wb").write(b"lock")
os.utime(os.path.join(F1, "~$ch v2.docx"), None)
check("the newest Word file in the folder, lock files ignored", DV.newest(F1) == new, DV.newest(F1))
check("an empty folder has no draft", DV.newest(F2) is None)

w.go("drafts"); app.processEvents()
pg = w.drafts_page
check("Status: one main button, Read the drafts", pg.bar.main is pg.b_read and pg.b_read.text() == "Read the drafts")
check("the volumes table lists each volume before any folder", pg.v_table.rowCount() == 2
      and "No folder yet" in pg.v_table.item(1, 1).text(), [pg.v_table.item(i, 1).text() for i in range(pg.v_table.rowCount())])
got = pg.edit_folders({vols[0]: F1, vols[1]: F2})
check("Volume folders keeps one folder per volume with the effort", W.Workspace(W.data_dir_for(LIST), "Kestrel").get(DV.KEY)
      == {vols[0]: F1, vols[1]: F2} and got == {vols[0]: F1, vols[1]: F2})
check("... the table names each volume's newest file", pg.v_table.item(0, 1).text() == "Tech v2.docx"
      and pg.v_table.item(0, 2).text() and "No Word file" in pg.v_table.item(1, 1).text())
mgmt = draft(os.path.join(F2, "Mgmt.docx"), vols[1], ["2.1 Management Plan"], 0)
rows = pg.read_all(); app.processEvents()
check("Read the drafts reads every volume's newest draft", [r["file"] for r in rows] == [new, mgmt]
      and all(r["rep"] and r["rep"]["matched"] for r in rows), [(r["file"], r["said"]) for r in rows])
check("... the table: not started, under way, over budget, removed",
      pg.v_table.item(1, 3).text() == "2" and pg.v_table.item(0, 4).text() == "2" and pg.v_table.item(0, 5).text() == "0"
      and pg.v_table.item(0, 6).text() == "0",
      [[pg.v_table.item(i, c).text() for c in range(7)] for i in range(2)])
check("... each read kept in the record", {x["file"] for x in SR.latest(RR.Record(w.ws.root))} >= {new, mgmt})
pg.v_table.setCurrentCell(1, 0); app.processEvents()
check("a volume clicked shows its sections", pg.rep is rows[1]["rep"] and pg.s_table.rowCount() == len(rows[1]["rep"]["sections"])
      and pg.s_table.item(0, 1).text() == "Not started" and pg.sum.text().startswith(vols[1]), pg.sum.text())
pg.edit_folders({vols[1]: ""}); rows = pg.read_all()
check("a volume with no folder says so", rows[1]["rep"] is None and "No folder yet" in rows[1]["said"], rows[1]["said"])
check("the drift report sees the volumes' drafts", new in pg.drafts())
w.close()
n = sum(checks)
print(f"QT DRAFTS 440 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
