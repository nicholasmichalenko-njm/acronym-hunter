"""2.63.0 the effort record in Qt, stage gates and color team review packets: effort details, team, stages with planned
dates and gates; a soft gate logs moving on with open goals, a hard gate holds the move until a reason is given; the
effort status report, the package and Back up now; a review packet is built, filled in by a reviewer (a verdict, a
comment, a Word comment), read back onto each requirement's sentence card, and scored by section."""
import datetime, os, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
import app_gui as A
import compliance as C, effort as E, effortrec as RR, effortstate as ES, reviewpkt as RP, setupdoc as SD, workspace as W, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
from lxml import etree

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


today = datetime.date.today()
tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
ws0 = W.Workspace(W.data_dir_for(LIST), "Kestrel")
ws0.set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Management\nVolume II Past Performance")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
check("the rail: Effort home, Dashboard, Effort record, Reviews", list(w.step_btns)[:4] == ["home", "dashboard", "record", "reviews"])
w.open_effort("Kestrel")
B = os.path.join(A.BASE_DIR, "test_samples", "rfp")
w.read_page.read([os.path.join(B, "Kestrel_RFP_Sections_C_L_M.docx")], os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
t = time.time()
while w.review is None and time.time() - t < 60:
    app.processEvents(); time.sleep(0.02)
M = w.review.M
by = lambda s: next(it for it in M.items if s in it["text"])
R = w.review
a, b = by("thermal design"), by("Integrated Master Schedule")
R.req([a], "1.1 Technical Approach"); R.req([b], "1.2 Management")
SD.set_people(M, "1.1 Technical Approach", lead="A. Lee")
w.changed(); w.save_now()

# effort record
w.go("record"); app.processEvents()
rp = w.record_page
rp.client.setText("USSF SSC"); rp.sol.setText("FA8810-26-R-0042")
rp.has_due.setChecked(True); rp.due_date.setDate(today + datetime.timedelta(days=30)); rp.zone.setText("MT")
check("Save details", rp.save_details())
L2 = E.EffortList(LIST).load()
r = RR.Record(ws0.root)
check("details are kept in the acronym list and the record", L2.client == "USSF SSC" and L2.solicitation == "FA8810-26-R-0042"
      and r.data["due"].startswith((today + datetime.timedelta(days=30)).isoformat()) and r.data["zone"] == "MT", (L2.client, r.data["due"]))
w.authors.merge([("A. Lee", None), ("R. Reviewer", None), ("Z. Other", None)], default=["Osprey"])   # 2.77.0: the author list
rp.choose_team(answer=["A. Lee", "R. Reviewer"])
rp.team_table.item(0, 1).setText("Volume lead"); rp.team_table.item(1, 1).setText("Red team reviewer")
rp.save_team()
check("the team: names from the author list that show in this effort, with roles", [m["name"] for m in RR.Record(ws0.root).team()] == ["A. Lee", "R. Reviewer"]
      and rp.team_table.rowCount() == 2 and "Z. Other" not in w.people())
check("the stage table lists every stage with a gate box", rp.stage_table.rowCount() == len(r.stages) and rp.stage_table.cellWidget(0, 3) is not None)
rp.stage_table.item(0, 1).setText((today - datetime.timedelta(days=3)).strftime("%b %d, %Y"))
rp.stage_table.cellWidget(0, 3).setCurrentIndex(rp.stage_table.cellWidget(0, 3).findData("hard"))
rp.stage_table.cellWidget(1, 3).setCurrentIndex(rp.stage_table.cellWidget(1, 3).findData("soft"))
rp.add_stage("Pink team")
rp.stage_table.setCurrentCell(rp.stage_table.rowCount() - 1, 0); rp.move_row(-1)
check("Save stages: dates, gates, a new stage", rp.save_stages())
r = RR.Record(ws0.root)
check("gates and planned dates are kept", r.gate_of(r.stages[0]) == "hard" and r.gate_of(r.stages[1]) == "soft"
      and r.stages[0]["planned"] == (today - datetime.timedelta(days=3)).isoformat()
      and [s["name"] for s in r.stages][-2] == "Pink team", [s["name"] for s in r.stages])
rp.stage_table.item(1, 1).setText("someday")
check("a date that is not understood is refused", not rp.save_stages())
rp.refresh()
# the gates
w.go("home"); app.processEvents()
hp = w.home_page
check("the stage track names the gate", any("hard gate" in l.text() for i in range(hp.track_row.count())
                                             for l in hp.track_row.itemAt(i).widget().findChildren(type(hp.due).__mro__[1])))
dlg = hp.move_dialog(run=False)
check("the move dialog warns of the hard gate", "Hard gate" in dlg.api["gate"].text() and dlg.api["reason"].isVisibleTo(dlg), dlg.api["gate"].text())
dlg.deleteLater()
nxt = r.stages[1]["id"]
check("a hard gate holds the move without a reason", hp.move_stage(nxt) is None and RR.Record(ws0.root).index() == 0)
check("the proposal manager overrides it with a reason", hp.move_stage(nxt, reason="Kickoff moved to Monday") is True)
ev = RR.Record(ws0.root).events(kinds=("gate",))
check("the override is in the timeline with the open goals and the reason", ev and "Hard gate overridden" in ev[0]["text"]
      and "Kickoff moved to Monday" in ev[0]["text"], ev[:1])
check("a soft gate lets the move through and logs it", hp.move_stage(RR.Record(ws0.root).stages[2]["id"]) is True
      and "Soft gate passed" in RR.Record(ws0.root).events(kinds=("gate",))[0]["text"])
r = RR.Record(ws0.root)
check("moving back is never held", r.gate_check(r.stages[0]["id"])["blocked"] is False)
# the classic window's move respects a hard gate set here
r.set_gate(r.data["stage"], "hard")
try:
    r.move_to(r.stages[r.index() + 1]["id"])
    held = False
except RR.GateClosed:
    held = True
check("the record holds a hard gate for either program", held)
# status, package, backup
w.go("record"); app.processEvents()
p = rp.status_export(os.path.join(tmp, "status.docx"))
check("Effort status (Word) is written from the shared snapshot", p and zipfile.is_zipfile(p)
      and "USSF SSC" in zipfile.ZipFile(p).read("word/document.xml").decode("utf-8"))
p2 = rp.status_export(os.path.join(tmp, "summary.docx"), final=True)
check("Effort summary (Word) with the history", p2 and "Hard gate overridden" in zipfile.ZipFile(p2).read("word/document.xml").decode("utf-8"))
man = rp.save_package(os.path.join(tmp, "Kestrel.skpkg"))
check("Save effort package", man and os.path.isfile(man["path"]) and any(f.endswith("record.json") for f in man["files"]), man and len(man["files"]))
out = rp.backup_now(os.path.join(tmp, "backups"))
check("Back up now writes the latest and today's copy", out and os.path.isfile(out["latest"]) and os.path.isfile(out["dated"]))
# review packets
w.go("reviews"); app.processEvents()
rv = w.review_page
rv.stage.setCurrentText("Red team")
check("reviewers default to the team's reviewers", rv.reviewers.text() == "R. Reviewer", rv.reviewers.text())
res = rv.build(os.path.join(tmp, "packet.docx"))
check("the packet lists each requirement under its section", res and res["rows"] == 2 and res["sections"] == 2, res)
# a reviewer fills it in: a verdict and a comment in the table, and a Word comment on the other row
Wn = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
z = zipfile.ZipFile(res["path"]); parts = {n: z.read(n) for n in z.namelist()}; z.close()
root = etree.fromstring(parts["word/document.xml"])


def cell_text(tc, text):
    p = tc.find(f"{{{Wn}}}p")
    r_ = etree.SubElement(p, f"{{{Wn}}}r"); t_ = etree.SubElement(r_, f"{{{Wn}}}t"); t_.text = text


for tr in root.iter(f"{{{Wn}}}tr"):
    tcs = tr.findall(f"{{{Wn}}}tc")
    first = "".join(x.text or "" for x in tcs[0].iter(f"{{{Wn}}}t"))
    if first == a["id"]:
        cell_text(tcs[4], "Not compliant"); cell_text(tcs[5], "The thermal margin is not stated.")
    if first == b["id"]:
        cell_text(tcs[4], "Partly")
        p = tcs[2].find(f"{{{Wn}}}p")
        p.insert(0, etree.Element(f"{{{Wn}}}commentRangeStart", {f"{{{Wn}}}id": "0"}))
parts["word/document.xml"] = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
parts["word/comments.xml"] = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:comments xmlns:w="{Wn}">'
                              f'<w:comment w:id="0" w:author="R. Reviewer"><w:p><w:r><w:t>Show the IMS baseline date.</w:t></w:r></w:p>'
                              '</w:comment></w:comments>').encode()
filled = os.path.join(tmp, "packet_back.docx")
with zipfile.ZipFile(filled, "w") as z:
    for n, data in parts.items():
        z.writestr(n, data)
back = RP.read_back(filled, M)
check("read back: the stage, both rows, the verdicts and the Word comment", back["stage"] == "Red team" and len(back["findings"]) == 2
      and {f["verdict"] for f in back["findings"]} == {"Not compliant", "Partly"}
      and any(f["word_comments"] == [("R. Reviewer", "Show the IMS baseline date.")] for f in back["findings"]), back)
out = rv.read_back(filled)
check("Read back puts each comment on its requirement", out["verdicts"] == 2 and out["notes"] == 2
      and RP.review_notes(RR.Record(ws0.root), a["id"]) and "thermal margin" in RP.review_notes(RR.Record(ws0.root), a["id"])[0]["text"])
sc = RP.score(M, "Red team")
check("the score by section", sc["Not compliant"] == 1 and sc["Partly"] == 1 and rv.tiles["Not compliant"].value.text() == "1"
      and rv.table.rowCount() == 2, sc)
check("the comments read back are listed", rv.notes.rowCount() == 2)
rv.open_row(0); app.processEvents()
ap = w.assign_page
check("double-click opens the requirement in Assign, its card shows the review comments",
      w.stack.currentWidget() is ap and getattr(ap, "review_labels", []) and "Red team review:" in ap.review_labels[0].text())
w.save_now()
check("verdicts are kept with the matrix", RP.score(C.Matrix(M.path).load(), "Red team")["Not compliant"] == 1)
w.go("dashboard"); app.processEvents()
check("the dashboard shows the latest review", "Red team review: 0 compliant, 1 partly, 1 not compliant" in w.dash_page.comp_text.text(),
      w.dash_page.comp_text.text())
w.close()
n = sum(checks)
print(f"QT RECORD PASS ({n}/{len(checks)})" if n == len(checks) else f"QT RECORD FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
