"""3.39.0 data calls and comment disposition, offscreen, on an effort read from the fictional RFP. Data calls: a tab
beside Customer Q&A; a call says what is needed, the section and requirement it serves, how much, an example, owner and
due date; Send Word files makes one file per person (calls become Sent); an answer typed into the returned file reads
back onto its call by its code (Answered); Place in the section puts it into the response structure as context for the
section's author (Placed); overdue calls show; the Author drafts gate goal follows. Comment disposition: a review packet
read back gives each reviewer comment a row to disposition; Word comments in the drafts come in under their heading;
Reject needs a reason; owners and due dates are kept; the recovery gate goal holds until every comment has one; the
disposition log exports. Fictional content only."""
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
import effort as E, workspace as W, office_pdf as OP, setupdoc as SD, effortrec as RR, effortstate as ES, effortfolders as EF
import datacalls as DC, dispositions as DP, reviewpkt as RP, kickoff as KO
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
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf", "SOW.pdf")]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Kestrel")
w.read_page.read(PDFS, os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page)
M, Rv = w.review.M, w.review
TA = "1.1 Technical Approach"
a = next(it for it in M.items if it["text"].startswith("The Offeror shall describe its technical approach"))
Rv.req([a], TA); SD.set_lm(M, [a], "L")

# ---------------------------------------------------------------- data calls
check("Data calls is a tab beside Customer Q&A", ("datacalls", "Data calls") in TABS["library"])
w.go("datacalls"); app.processEvents()
pg = w.datacalls_page
check("the page opens, empty", w.stack.currentWidget() is pg and pg.empty.isVisible() and "No data calls" in pg.summary.text())
check("the sections offered are the response structure's", TA in pg.sections())
c1 = pg.add({"question": "Give the thermal vacuum test history of the Kestrel bus: dates, cycles, anomalies.", "section": TA,
             "req": "L.4.2", "words": "150 to 250 words", "example": "Three TVAC campaigns since 2024, each 8 cycles...",
             "owner": "Dana Ruiz", "due": "2026-01-02"})
c2 = pg.add({"question": "Name the key personnel for integration and test.", "section": "1.2 Risk", "owner": "A. Lee", "due": "2099-12-31"})
check("a call is added with a code that never changes", c1 and c2 and [DC.code_of(c) for c in DC.items(pg.rec())] == ["DC-1", "DC-2"])
check("an empty call is refused", pg.add({"question": "  "}) is None)
check("a call past its due date with no answer shows as overdue", [c["id"] for c in DC.overdue(pg.rec())] == [c1]
      and "1 overdue" in pg.summary.text(), pg.summary.text())
pg.filter.setCurrentText("Overdue"); app.processEvents()
check("Show: Overdue lists only those", len(pg.rows) == 1 and pg.rows[0]["id"] == c1)
pg.filter.setCurrentText("All"); app.processEvents()
out = pg.send(folder=os.path.join(tmp, "calls"))
check("Send Word files makes one file per person; the calls become Sent", sorted(o for o, _p in out) == ["A. Lee", "Dana Ruiz"]
      and all(c["status"] == "Sent" for c in DC.items(pg.rec())))
dana = dict(out)["Dana Ruiz"]
with zipfile.ZipFile(dana) as z:
    doc = z.read("word/document.xml").decode()
check("Dana's file holds her call: what, for, how much, the example, the due date and an answer box", "DC-1" in doc and "DC-2" not in doc
      and "thermal vacuum" in doc and "L.4.2" in doc and "150 to 250 words" in doc and "Three TVAC campaigns" in doc and "Your answer" in doc)
ret = os.path.join(tmp, "returned.docx")
with zipfile.ZipFile(dana) as zi, zipfile.ZipFile(ret, "w") as zo:
    for i in zi.infolist():
        b = zi.read(i.filename)
        if i.filename == "word/document.xml":
            from lxml import etree
            NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
            root = etree.fromstring(b)
            for tr in root.iter(NS + "tr"):
                cells = tr.findall(NS + "tc")
                if len(cells) == 2 and "Your answer" in "".join(t.text or "" for t in cells[0].iter(NS + "t")):
                    p = cells[1].find(NS + "p")
                    r = etree.SubElement(p, NS + "r"); t = etree.SubElement(r, NS + "t")
                    t.text = "Three TVAC campaigns since 2024, 8 cycles each, no anomalies."
            b = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
        zo.writestr(i, b)
got = pg.read([ret])
c = DC.get(pg.rec(), c1)
check("an answer typed in the returned file reads back onto its call by its code (Answered)", got["answered"] == 1
      and c["status"] == "Answered" and c["answer"].startswith("Three TVAC campaigns"), (got, c["status"]))
check("reading the same file again changes nothing", pg.read([ret])["answered"] == 0)
pg.select_id(c1)
xid = pg.place()
S = SD.setup_of(M)
ctx = next((x for x in S["context"] if x["id"] == xid), None)
check("Place in the section puts the answer into the structure as context under its section (Placed)", ctx is not None
      and ctx["text"].startswith("Three TVAC") and ctx["map"] == TA and DC.get(pg.rec(), c1)["status"] == "Placed")
check("the section's author sees it: it is placed in the section", xid in SD.placed_in(M)[TA])
pg.select_id(c2)
check("a call with no answer cannot be placed", pg.place() == "")
check("the Author drafts gate goal follows the calls (not met: DC-2 is open)", ES.checks_of(pg.rec()).get("datacalls_answered") is False)

# ---------------------------------------------------------------- comment disposition
w.go("reviews"); app.processEvents()
rp = w.review_page
rp.stage.setCurrentText("Red team")
pkt = os.path.join(tmp, "packet.docx")
rp.build(pkt)
res = {"stage": "Red team", "findings": [{"id": a["id"], "verdict": "Partly", "verdict_text": "Partly",
                                           "comment": "Approach lacks test schedule.", "word_comments": [("G. Park", "Add the TVAC dates.")]}],
       "unknown": [], "file": "packet.docx"}
out2 = RP.apply(M, RR.Record(w.ws.root), res, "Red team")
rp.fill(); app.processEvents()
check("a packet read back gives each reviewer comment a row to disposition", out2["comments"] == 2
      and rp.dt.rowCount() == 2 and "0 of 2 comments dispositioned" in rp.disp_sum.text(), rp.disp_sum.text())
check("each comment is placed at its requirement and section", TA in rp.dt.item(0, 0).text())
check("reading the same packet again keeps each comment once", RP.apply(M, RR.Record(w.ws.root), res, "Red team")["comments"] == 0)
# a draft with Word comments under headings
draft = os.path.join(EF.folder(w.effort_path, "volumes"), "Volume I Technical.docx")
os.makedirs(os.path.dirname(draft), exist_ok=True)
NSD = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
body = (f'<w:document {NSD}><w:body>'
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>1.1 Technical Approach</w:t></w:r></w:p>'
        '<w:p><w:commentRangeStart w:id="0"/><w:r><w:t>Our approach is proven.</w:t></w:r><w:commentRangeEnd w:id="0"/>'
        '<w:r><w:commentReference w:id="0"/></w:r></w:p>'
        '<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>1.2 Risk</w:t></w:r></w:p>'
        '<w:p><w:commentRangeStart w:id="1"/><w:r><w:t>Risks are low.</w:t></w:r><w:commentRangeEnd w:id="1"/>'
        '<w:r><w:commentReference w:id="1"/></w:r></w:p></w:body></w:document>')
comments = (f'<w:comments {NSD}><w:comment w:id="0" w:author="G. Park"><w:p><w:r><w:t>Proven how? Cite the flight.</w:t></w:r></w:p></w:comment>'
            '<w:comment w:id="1" w:author="R. Diaz"><w:p><w:r><w:t>Which risks? Add the top three.</w:t></w:r></w:p></w:comment></w:comments>')
styles = f'<w:styles {NSD}><w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/></w:style></w:styles>'
with zipfile.ZipFile(draft, "w") as z:
    z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
    z.writestr("word/document.xml", body); z.writestr("word/comments.xml", comments); z.writestr("word/styles.xml", styles)
check("Word comments in a draft are read, each under the heading it sits beneath",
      DP.read_word_comments(draft) == [("1.1 Technical Approach", "G. Park", "Proven how? Cite the flight."),
                                      ("1.2 Risk", "R. Diaz", "Which risks? Add the top three.")], DP.read_word_comments(draft))
got = rp.read_drafts()
check("Read Word comments from the drafts adds them to the stage", got["added"] == 2 and rp.dt.rowCount() == 4)
ids = [rp.dt.item(i, 0).data(0x0100) for i in range(rp.dt.rowCount())]
check("Reject needs a reason", rp.set_disp(ids[0], "Reject") and DP.get(RR.Record(w.ws.root), ids[0])["disposition"] == "")
check("Reject with a reason is kept", rp.set_disp(ids[0], "Reject", reason="The schedule is in Volume III") == ""
      and DP.get(RR.Record(w.ws.root), ids[0])["disposition"] == "Reject")
rp.set_disp(ids[1], "Accept", owner="Dana Ruiz", due="2026-12-01")
k = DP.get(RR.Record(w.ws.root), ids[1])
check("Accept with an owner and a due date is kept", k["disposition"] == "Accept" and k["owner"] == "Dana Ruiz" and k["due"] == "2026-12-01")
check("the recovery gate goal is not met while comments are open", DP.all_dispositioned(RR.Record(w.ws.root), "Red team") is False)
for cid in ids[2:]:
    rp.set_disp(cid, "Done")
check("every comment dispositioned meets the gate goal", DP.all_dispositioned(RR.Record(w.ws.root), "Red team") is True
      and ES.checks_of(RR.Record(w.ws.root)).get("comments_dispositioned") is True
      and "4 of 4 comments dispositioned" in rp.disp_sum.text(), rp.disp_sum.text())
rp.open_only.setChecked(True); app.processEvents()
check("Open only hides the dispositioned ones", rp.dt.rowCount() == 0)
rp.open_only.setChecked(False)
log = rp.export_disp(os.path.join(tmp, "log.xlsx"))
from openpyxl import load_workbook
rows = list(load_workbook(log)["Comments"].values)
check("the disposition log exports one row per comment", len(rows) == 5 and rows[0][5] == "Disposition"
      and any(r[5] == "Reject" and r[6] == "The schedule is in Volume III" for r in rows[1:]))
import effortrec as R2
check("the recovery stages' default goal is every comment dispositioned", "comments_dispositioned" in R2.DEFAULT_GOALS["Red team recovery"]
      and "datacalls_answered" in R2.DEFAULT_GOALS["Author drafts"] and "comments_dispositioned" in R2.AUTO)

w.close()
n = sum(checks)
print(f"QT DATA CALLS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
