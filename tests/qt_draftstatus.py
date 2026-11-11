"""3.43.0 Writing > Draft Status, offscreen, on an effort read from the fictional RFP: the setup's plain export is filled
the way an author does (words under one heading, a requirement's text deleted, a pasted style), then read back: each
section's status, words and pages against its budget, the removed requirement, the style brought in; the words a page
setting is kept with the effort; the record keeps a line; Export writes the workbook; a draft with none of the
structure's headings says so. Fictional content only."""
import os, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SHRED_CLASSIC"] = "1"           # 4.5.0: tests the machinery under the focused Shred screen
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, workspace as W, office_pdf as OP, setupdoc as SD, effortrec as RR, pagebudget as PB, setupread as SR, docxw
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow, RAIL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf", "SOW.pdf")]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


check("Draft Status is the Drafts step's Status (4.0.0)", ("drafts", "Status") in __import__("skqt.mainwin", fromlist=["x"]).TABS["drafts"])
w.open_effort("Kestrel")
w.read_page.read(PDFS, os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page)
M, Rv = w.review.M, w.review
TA, RK = "1.1 Technical Approach", "1.2 Risk"
a = next(it for it in M.items if it["text"].startswith("The Offeror shall describe its technical approach"))
b = next(it for it in M.items if it is not a and SD.kind_of(it) == "Requirement" and len(SD._norm(it["text"])) > 40)
Rv.req([a], TA); Rv.req([b], RK)
PB.set_pages(M, TA, 1)

# a filled draft: the headings, an author's words, b's text deleted, a pasted style
doc = docxw.Doc()
doc.heading("Volume I Technical", 1)
for lab, body, keep in ((TA, " ".join(["kestrel"] * 300), a), (RK, "", None)):
    doc.heading(lab, 2)
    if keep is not None:
        doc.rich([(keep["text"], None)])
    if body:
        doc.rich([(body, None)])
path = os.path.join(tmp, "Volume I Technical.docx"); doc.save(path)
z = zipfile.ZipFile(path); names = SR.style_names(z)
check("the draft is written with heading styles (the read finds sections by them)", any(n.startswith("Heading") or n.startswith("heading") for n in names.values()),
      names)

w.go("drafts"); app.processEvents()
pg = w.drafts_page
check("the page opens on the effort", pg.isEnabled())
pg.pick(path)
pg.wpp.setValue(400)
rep = pg.read()
by = {r["section"]: r for r in (rep or {}).get("sections", [])}
check("Technical Approach: 300 words of a one-page budget is Near budget", by.get(TA, {}).get("status") == "Near budget"
      and by[TA]["words"] == 300, by.get(TA))
check("Risk: no words is Not started, and its requirement is listed as removed", by.get(RK, {}).get("status") == "Not started"
      and [x["id"] for x in by[RK]["removed"]] == [b["id"]], by.get(RK))
check("the sections table shows them", pg.s_table.rowCount() == len(rep["sections"])
      and any(pg.s_table.item(i, 1).text() == "Near budget" for i in range(pg.s_table.rowCount())))
check("the removed requirement is listed below", pg.r_table.rowCount() == 1 and pg.r_table.item(0, 1).text() == "Removed")
check("the summary says it in a sentence", "near budget" in pg.sum.text() and "removed" in pg.sum.text(), pg.sum.text())
check("the words a page setting is kept with the effort", w.ws.get("readback_wpp") == 400)
check("the effort record keeps a line of the read", SR.latest(RR.Record(w.ws.root))[0]["file"] == path)
xl = pg.export(os.path.join(tmp, "status.xlsx"))
check("Export writes the workbook", xl and os.path.isfile(xl))
# 3.46.0: My Work, the dashboard and the gate goal
import mywork as MW, datacalls as DCS, effortstate as ESS
SD.set_people(M, TA, lead="Dana Ruiz"); SD.set_people(M, RK, lead="Dana Ruiz"); M.save()
rec = RR.Record(w.ws.root)
DCS.add(rec, "Give the TVAC test history of the bus.", section=TA, owner="Dana Ruiz", due="2026-01-02")
st = SR.section_status(RR.Record(w.ws.root))
check("each section's status is kept from the newest read", st.get(TA, {}).get("status") == "Near budget" and st.get(RK, {}).get("status") == "Not started", st)
check("the gate goal Every section drafted holds while a section is not started", SR.all_drafted(RR.Record(w.ws.root)) is False
      and ESS.checks_of(RR.Record(w.ws.root))["sections_drafted"] is False and "sections_drafted" in RR.DEFAULT_GOALS["Author drafts"])
info = w.efforts.get(w.effort_name) or {}
mw = MW.for_effort(w.effort_name, info, "Dana Ruiz")
kinds = {i["kind"]: i for i in mw["items"]}
check("My Work lists the data call Dana owes, with its code", "datacall" in kinds and kinds["datacall"]["text"].startswith("DC-1:"), mw["items"])
check("... and the section not started, with its removed requirement", "draft" in kinds and RK in kinds["draft"]["text"]
      and "removed" in kinds["draft"]["text"], kinds.get("draft"))
check("... and each section Dana leads says its draft status", any(x["label"] == TA and x["draft"] == "Near budget" for x in mw["sections"]), mw["sections"])
w.go("dashboard"); app.processEvents()
dp = w.dash_page
txt = " ".join(l.text() for l in dp.draft_labels)
check("the Effort Dashboard shows the drafts and the data calls", "1 near budget" in txt and "Not started: " + RK in txt
      and "1 data call(s)" in txt and "Overdue: DC-1" in txt, txt)
memo = docxw.Doc(); memo.rich([("A Kestrel memo with no structure in it.", None)]); mp = os.path.join(tmp, "memo.docx"); memo.save(mp)
pg.pick(mp); pg.read()
check("a draft with none of the headings says so", "No heading" in pg.sum.text(), pg.sum.text())

w.close()
n = sum(checks)
print(f"QT DRAFT STATUS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
