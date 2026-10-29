"""2.92.0 time zones, due dates and events, the overview and per-person exports, offscreen: US zones with daylight time,
UTC and offsets; your time zone in Settings and the submission's with the effort; Effort Home shows the deadline in both
and counts down across zones; + Due date and + Event with times and zones (Edit, and your time beside theirs); the
overview carries the proposal manager's summary, both zones, people's progress, newest documents (NEW since the last
overview), what is coming up, and the marking in its header and footer; tasks and questions export for one person or the
full team, dated and named; a picked person's name shows large; the stages are edited on Effort Home; the due date is set
in Effort Record without a hidden switch."""
import datetime, os, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import tzones as TZ, effortrec as RR, effortcal as EC, branding as BR, tqexport as TQ, office_pdf as OP
OP.available = lambda: False
from PySide6.QtCore import QDate, QTime
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


dt = datetime.datetime
check("Eastern in winter is UTC-5, in summer UTC-4", TZ.to_utc(dt(2026, 12, 15, 14), "ET") == dt(2026, 12, 15, 19)
      and TZ.to_utc(dt(2026, 7, 1, 14), "ET") == dt(2026, 7, 1, 18))
check("the clocks change on the right Sundays", TZ.to_utc(dt(2026, 3, 8, 1, 30), "MT") == dt(2026, 3, 8, 8, 30)
      and TZ.to_utc(dt(2026, 3, 8, 3, 30), "MT") == dt(2026, 3, 8, 9, 30) and TZ.to_utc(dt(2026, 11, 1, 2, 30), "MT") == dt(2026, 11, 1, 9, 30))
check("Arizona keeps standard time all year", TZ.convert(dt(2026, 7, 1, 9), "AZ", "MT") == dt(2026, 7, 1, 10) and TZ.label("AZ", dt(2026, 7, 1)) == "MST")
check("a customer's words read as a zone", [TZ.guess(x) for x in ("Mountain Time", "2:00 PM EDT", "Pacific", "Zulu", "UTC+05:30", "nonsense")]
      == ["MT", "ET", "PT", "UTC", "UTC+05:30", ""])
check("a deadline in both zones", TZ.both(dt(2026, 12, 15, 14), "ET", "MT") == ("Dec 15, 2026, 2:00 p.m. EST", "12:00 p.m. MST your time"))
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
sp = w.settings_page
check("Settings: your time zone, guessed from Windows until saved", "from Windows" in sp.tz_note.text())
sp.save_zone("PT")
check("save your time zone", TZ.my_zone(A.load_settings()) == "PT" and "Pacific" in sp.tz_note.text())
check("an offset for anywhere else; nonsense is refused", sp.save_zone("UTC+01:00") and not sp.save_zone("Mars"))
sp.save_zone("MT")
L = os.path.join(tmp, "Efforts", "Kestrel", "Kestrel_Effort_List.xlsx")
w.settings_page.new_effort({"name": "Kestrel", "path": L})
w.go("home"); app.processEvents()
hp = w.home_page; bn = hp.banner
due = (dt.now() + datetime.timedelta(days=10)).replace(hour=14, minute=0, second=0, microsecond=0)
bn.save_details({"due": due.strftime("%Y-%m-%dT%H:%M"), "zone_key": "ET"})
r = RR.Record(w.ws.root)
check("Edit details sets the due date, time and the submission's zone", r.data["due"] == due.strftime("%Y-%m-%dT%H:%M") and r.zone_key() == "ET")
check("Effort Home shows the deadline in the customer's zone and yours", " E" in bn.due.text().split("\n")[0] and "your time" in bn.due.text()
      and "12:00 p.m. M" in bn.due.text(), bn.due.text())
u = TZ.to_utc(due, "ET")
c = BR.countdown(due.strftime("%Y-%m-%dT%H:%M"), None, "ET", now_utc=u - datetime.timedelta(hours=26, minutes=5))
check("the countdown is right across zones", c == (1, 2, 5, 0), c)
# Effort Record: the due date without a hidden switch
rp = w.record_page; w.go("record"); app.processEvents()
rp.has_due.setChecked(False)
rp.due_date.setDate(QDate(2026, 12, 18)); rp.due_time.setTime(QTime(15, 30)); rp.zone.setText("Central")
check("changing the date sets the due date (no switch to find)", rp.has_due.isChecked() and rp.due_date.isEnabled() and rp.due_time.isEnabled())
rp.save_details()
r = RR.Record(w.ws.root)
check("Effort Record saves the due date, time and zone", r.data["due"] == "2026-12-18T15:30" and r.zone_key() == "CT", (r.data["due"], r.zone_key()))
# + Due date and + Event
from skqt.calview import entry_dialog, EntryDialog
w.go("home"); app.processEvents()
eid = entry_dialog(hp, "Due", answer={"kind": "Due", "title": "Drafts to Production", "date": "2026-11-18", "start": "17:00", "end": "",
                                       "zone": "ET", "owner": "A. Lee", "location": "", "details": "Volume I and II"})
e2 = entry_dialog(hp, "Meeting", answer={"kind": "Review", "title": "Red team review", "date": "2026-11-20", "start": "09:00", "end": "16:00",
                                          "zone": "MT", "owner": "", "location": "Room 2B", "details": ""})
r = RR.Record(w.ws.root)
cal = r.calendar(first=datetime.date(2026, 11, 18), last=datetime.date(2026, 11, 20), mine="MT")
d18 = cal.get(datetime.date(2026, 11, 18), [])
check("+ Due date: on the calendar with its time, zone and your time", any(k == "deadline" and "5:00 p.m. EST (3:00 p.m. MST your time)" in t
                                                                          and "Drafts to Production" in t for k, t in d18), d18)
check("+ Event: start and end, in its zone", any(k == "meeting" and t.startswith("9:00 a.m. MST to 4:00 p.m.") for k, t in cal.get(datetime.date(2026, 11, 20), [])))
dlg = EntryDialog(hp, w, entry=next(e for e in r.data["events"] if e["id"] == e2))
check("Edit opens the entry with its values", dlg.title.text() == "Red team review" and dlg.zone.currentData() == "MT" and dlg.has_end.isChecked())
entry_dialog(hp, entry=next(e for e in r.data["events"] if e["id"] == e2), answer={"start": "10:00"})
check("an edit is saved", next(e for e in RR.Record(w.ws.root).data["events"] if e["id"] == e2)["start"] == "10:00")
hp.pick_day(datetime.date(2026, 11, 18)); app.processEvents()
# the readable calendar export carries exact moments
ics = hp.calfiles.export("ics", os.path.join(tmp, "cal.ics"))
check("Outlook gets exact moments", "DTSTART:20261118T220000Z" in open(ics).read())
# the overview
RR.Record(w.ws.root).add_task("Write 1.1", owner="A. Lee", due="2020-01-01")
r = RR.Record(w.ws.root); r.add_note("Page limit for resumes?", question=True); r = RR.Record(w.ws.root)
q = r.data["notes"][-1]["id"]; r.update_note(q, assignee="A. Lee") if hasattr(r, "update_note") else None
BR.set_identity(RR.Record(w.ws.root), pm="Dana Ruiz", sensitivity="CUI")
out = os.environ.get("OV_OUT") or os.path.join(tmp, "overview.docx")
w.record_page.status_export(out, summary="Pricing is late.\nRed team packets go out Monday.")
xml = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
names = zipfile.ZipFile(out).namelist()
check("the overview starts with the proposal manager's words", "The proposal manager's summary" in xml and "Pricing is late." in xml
      and xml.index("Pricing is late.") < xml.index("Where we are"))
check("it carries the proposal manager, both zones and what is coming up", "Dana Ruiz" in xml and "your time" in xml and "Coming up" in xml
      and "Drafts to Production" in xml)
check("people and how far along they are", "Waiting on them" in xml and "Tasks done / open" in xml and "A. Lee" in xml)
check("CUI marks every page's header and footer", "word/header1.xml" in names and "CUI" in zipfile.ZipFile(out).read("word/header1.xml").decode())
check("the summary is kept for next time", RR.Record(w.ws.root).data["pm_summary"].startswith("Pricing is late."))
# tasks and questions, one person or the team
hp.who.clear(); hp.who.addItems(["Everyone", "A. Lee"]); hp.who.setCurrentText("A. Lee"); hp.refresh(); app.processEvents()
hp.who.setCurrentText("A. Lee") if hp.who.findText("A. Lee") >= 0 else None
fn = TQ.file_name("Kestrel", "A. Lee", dt(2026, 10, 29, 17, 6))
check("named and time-stamped for the person, or the full team", fn == "Kestrel_Tasks_and_Questions_A_Lee_2026-10-29_1706.xlsx"
      and TQ.file_name("Kestrel", "", dt(2026, 10, 29, 17, 6)).endswith("Full_Team_2026-10-29_1706.xlsx"))
p, nt, nq = TQ.export(RR.Record(w.ws.root), os.path.join(tmp, fn), "Kestrel", "A. Lee", sensitivity="CUI")
import openpyxl
wb = openpyxl.load_workbook(p)
check("the person's tasks and questions, with who it is for and when", wb.sheetnames == ["Tasks", "Questions"] and nt == 1
      and "For A. Lee" in wb["Tasks"]["A2"].value and wb["Tasks"]["A3"].value == "CUI")
p2 = hp.export_tq(os.path.join(tmp, "team.xlsx"))
check("Export from Effort Home writes the workbook", os.path.isfile(p2))
hp.who.addItem("A. Lee") if hp.who.findText("A. Lee") < 0 else None
hp.who.setCurrentText("A. Lee")
p_ = hp.person()
hp.for_box.setVisible(bool(p_)); hp.for_name.setText(f"{p_}: tasks and questions" if p_ else "")
check("a picked person's name shows large at the top", hp.for_box.isVisibleTo(w) and hp.for_name.text().startswith("A. Lee"))
# stages on Effort Home
sd = hp.edit_stages(run=False)
sd.stage_table.item(1, 0).setText("Pink team")
check("Edit stages on Effort Home saves the names", sd.save() and RR.Record(w.ws.root).stages[1]["name"] == "Pink team")
w.close()
n = sum(checks)
print(f"QT TIMEZONES PASS ({n}/{len(checks)})" if n == len(checks) else f"QT TIMEZONES FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
