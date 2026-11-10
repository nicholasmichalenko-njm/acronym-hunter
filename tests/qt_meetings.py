"""3.20.0 meetings, offscreen: a meeting with its date, participants and notes (on the calendar too); topics added by
hand and from the notes' bullet lines; a topic pointing at a requirement shows on its Review card; open topics on the
Effort Dashboard and in My Work for their owner; Considered and Not needed keep who and when; the gate goal follows;
Export to Word; delete takes the calendar entry too."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, workspace as W, office_pdf as OP, compliance as C, pagemarks as PM, suggestrules as SR
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Heron"); os.makedirs(ED)
LIST = os.path.join(ED, "Heron_Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Heron").set("outline_text", "Volume I Technical\n1.1 Technical Approach")
PDF = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Heron")
w.read_page.read([PDF], os.path.join(ED, "Heron_Compliance_Matrix.xlsx"))
wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page)
pg = w.assign_page
M = w.review.M
pg.files.setCurrentText("Section_L_print.pdf"); app.processEvents()


import meetings as MT, effortrec as R_, effortstate as ES, mywork as MW, zipfile
rows = [it for it in M.items if it.get("file") == "Section_L_print.pdf" and not it.get("decision") and it["id"] in pg.view.boxes]
pg.select(rows[0]["id"]); pg.do_lm("L"); app.processEvents()
req = rows[0]["id"]
w.authors.add("Dana Ruiz") if hasattr(w.authors, "add") else None
w.go("meetings"); app.processEvents()
mp = w.meetings_page
check("Meetings is a tab of the Dashboard (3.96.0)", w.stack.currentWidget() is mp
      and w.page_tabs.tabText(w.page_tabs.currentIndex()) == "Meetings")
mid = mp.new_meeting("Pink team debrief", "2026-11-03", participants=["Dana Ruiz", "A. Lee"])
rec = R_.Record(w.ws.root)
m = MT.get(rec, mid)
check("a meeting with its date and participants, on the calendar too", m and m["participants"] == ["Dana Ruiz", "A. Lee"]
      and any(e["id"] == m["event"] and e["kind"] == "Meeting" for e in rec.data.get("events", [])))
mp.notes.setPlainText("Discussed the approach.\n- Use the Phase 2 test data in the approach\nTopic: confirm the page limit\nNothing else.")
mp.save_fields()
check("notes are kept", "Phase 2" in MT.get(R_.Record(w.ws.root), mid)["notes"])
n = mp.from_notes(picked=["Use the Phase 2 test data in the approach", "confirm the page limit"])
check("Topics from notes: the bullet and Topic: lines become topics", n == 2 and mp.topics.rowCount() == 2
      and MT.topics_from_notes(MT.get(R_.Record(w.ws.root), mid)["notes"]) == ["Use the Phase 2 test data in the approach", "confirm the page limit"])
tid = mp.add_topic("Add the test lab photo to the approach", target=req, owner="Dana Ruiz")
check("+ Topic points at a requirement with an owner", tid and mp.topics.rowCount() == 3)
w.go("assign"); app.processEvents(); pg.select(req); app.processEvents()
check("the requirement's card shows the open topic", any("test lab photo" in l.text() for l in getattr(pg, "topic_labels", [])))
w.go("home"); app.processEvents()
check("the Effort Dashboard lists the open topics", w.dash_page.fill_topics() == 3
      and any("Phase 2" in l.text() for l in w.dash_page.topic_labels))
mine = MW.for_effort("Heron", w.efforts.get("Heron"), "Dana Ruiz")
check("My Work lists the topic for its owner", any(x["kind"] == "topic" and "test lab photo" in x["text"] for x in mine["items"]), mine["items"])
w.go("meetings"); app.processEvents()
mp.show(mid); mp.topics.selectRow(2); mp.mark("considered")
t = MT.topic(R_.Record(w.ws.root), mid, tid)
check("Considered keeps who and when", t["status"] == "considered" and t["by"] and t["at"])
check("the gate goal: not all considered yet", ES.checks_of(R_.Record(w.ws.root))["topics_considered"] is False)
mp.topics.selectRow(0); mp.mark("not_needed", why="Already in the draft")
mp.topics.selectRow(1); mp.mark("considered")
check("... and met once every topic is considered or not needed", ES.checks_of(R_.Record(w.ws.root))["topics_considered"] is True
      and "every topic considered" in mp.summary.text())
mp.topics.selectRow(1); mp.mark("open")
check("Reopen puts a topic back", MT.open_count(R_.Record(w.ws.root)) == 1)
out = os.path.join(tmp, "meeting.docx")
got = mp.export(out)
xml = zipfile.ZipFile(got).read("word/document.xml").decode("utf-8", "replace") if got else ""
check("Export to Word: the meeting, notes and topics with their status", "Pink team debrief" in xml and "Phase 2" in xml
      and "Not needed" in xml and "Already in the draft" in xml)
mp.open_only.setChecked(True); app.processEvents()
check("Show only meetings with open topics", mp.list.count() == 1)
check("Delete takes the meeting and its calendar entry out", mp.delete(confirm=True) and not MT.meetings(R_.Record(w.ws.root))
      and not any(e.get("kind") == "Meeting" for e in R_.Record(w.ws.root).data.get("events", [])))
w.close()
n = sum(checks)
print(f"QT MEETINGS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
