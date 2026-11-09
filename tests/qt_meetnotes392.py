"""3.92.1 offscreen: notes on a calendar event. A meeting put on the Effort Dashboard's calendar gets Notes beside it in
the day's list; the first click makes its notes from the event (title, date, times, who); the notes save as typed; the
Action, Decision and Topic lines are offered as topics and kept; the button then says Notes with the topic count; Effort
Record > Meetings lists the same meeting; notes never rewrite the calendar entry's details. Fictional content (Kestrel)."""
import datetime, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
import effortrec as RR, effortcal as EC, meetings as MT
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
from skqt import meetnotes as MN

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
L = os.path.join(tmp, "Efforts", "Kestrel", "Kestrel_Effort_List.xlsx")
w.settings_page.new_effort({"name": "Kestrel", "path": L})
w.go("home"); app.processEvents()
hp = w.home_page
day = datetime.date.today() + datetime.timedelta(days=2)
r = RR.Record(w.ws.root)
eid = EC.add_entry(r, kind="Meeting", date=day.isoformat(), start="10:00", end="11:00", title="Kickoff: the setup to authors",
                   details="Participants: R. Diaz, J. Okafor, S. Patel\nBring the outline.")
hp.refresh() if hasattr(hp, "refresh") else None
hp.pick_day(day); app.processEvents()
labels = [b.text() for b in hp.findChildren(QPushButton) if b.isVisibleTo(hp)]
check("Notes is beside the meeting in the day's list", "Notes" in labels, labels)
dlg = MN.open_notes(hp, hp.rec, eid, run=False)
m = MT.of_event(hp.rec, eid)
check("the first click makes the notes from the event", m is not None and m["title"] == "Kickoff: the setup to authors"
      and m["start"] == "10:00" and m["participants"] == ["R. Diaz", "J. Okafor", "S. Patel"], m)
check("and the event keeps one meeting (a second click opens the same notes)", MT.for_event(hp.rec, eid) == m["id"])
dlg.notes.setPlainText("Walked the authors through the setup.\nAction: S. Patel drafts 1.2 by Nov 18\nDecision: lead 1.1 with the failover")
dlg.save(); app.processEvents()
check("the notes are saved", MT.get(RR.Record(w.ws.root), m["id"])["notes"].startswith("Walked the authors"))
check("the Action and Decision lines are offered as topics", dlg.offers.count() == 2, [dlg.offers.item(i).text() for i in range(dlg.offers.count())])
dlg.offers.setCurrentRow(0); dlg.keep_current()
check("a topic is kept and leaves the offers", dlg.topics.count() == 1 and dlg.offers.count() == 1)
dlg.topics.setCurrentRow(0); dlg.set_done()
check("a topic can be marked done", "Done" in dlg.topics.item(0).text())
ev = next(e for e in RR.Record(w.ws.root).data["events"] if e["id"] == eid)
check("notes never rewrite the calendar entry's details", "Bring the outline." in ev["details"], ev["details"])
check("the button says Notes with the topic count", MN.mark(hp.rec, eid) == "Notes · 1 topic")
dlg.close_save()
check("Effort Record > Meetings lists the same meeting", any(x["id"] == m["id"] for x in MT.meetings(RR.Record(w.ws.root))))
print(f"QT MEETING NOTES 392 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
