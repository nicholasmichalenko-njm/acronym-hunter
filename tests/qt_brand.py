"""2.88.0 branded Effort home and the effort calendar as a file, offscreen: Title Case menu; company logos at the top of
the menu (up to three, in order) and the Stationkeeper mark at its foot; the effort banner (picture, name, client,
solicitation, proposal manager, sensitivity, the effort's own spots, the due date with a live countdown), all kept in the
effort so packages carry them; the CUI or proprietary strip on every page; Customize Home (a role's layout, show, hide,
order), kept per person and never in the effort; My work for an author; the calendar template, import with a preview
(the due date to the minute, stage dates, tasks, reviews and meetings; again updates instead of copying; undo), and
export to Excel (imports back) and Outlook (.ics, imports back)."""
import datetime, json, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, effortrec as RR, workspace as W, branding as BR, effortcal as EC, effortpkg as PK
from PIL import Image
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel", client="USSF SSC", solicitation="FA8810-26-R-0042"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
pics = []
for i, col in enumerate(((200, 30, 40), (20, 90, 160), (30, 140, 60), (90, 90, 90))):
    p = os.path.join(tmp, f"logo{i}.png"); Image.new("RGB", (1600, 400), col).save(p); pics.append(p)
patch = os.path.join(tmp, "patch.jpg"); Image.new("RGB", (2000, 2000), (15, 30, 70)).save(patch)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
# ---- the menu
texts = [b.text() for b in w.step_btns.values()]
check("the menu is in Title Case", texts[1:6] == ["Effort Home", "Deliverables", "Dashboard", "Effort Record", "Color Reviews"]
      and "Response Setup" in texts and "Lists to Submit" in texts and "L/M Crosswalk" in texts, texts)
from PySide6.QtWidgets import QLabel
heads = [l.text() for l in w.findChildren(QLabel) if l.objectName() == "railhead"]
check("menu groups are in Title Case", heads[:4] == ["Home", "Effort", "Compliance", "Documents"] and "Response Quality" in heads, heads)
check("the Stationkeeper mark and name at the foot of the menu", w.rail_footer.word.text() == "Stationkeeper" and A.APP_VERSION in w.rail_footer.sub.text())
# ---- logos
check("no logo yet: a quiet prompt to add one", w.rail_brand.add.isVisibleTo(w) and not w.rail_brand.plate.isVisibleTo(w))
w.go_branding(); app.processEvents()
bc = w.settings_page.branding_card
check("Add your company logo opens Settings > Branding", w.stack.currentWidget() is w.settings_page)
for p in pics[:3]:
    bc.add_logo(p)
check("up to three logos, kept small, shown at the top of the menu", len(BR.logos(cfg)) == 3 and w.rail_brand.plate.isVisibleTo(w)
      and max(Image.open(BR.logos(cfg)[0]).size) <= 600 and len(w.rail_brand.paths) == 3)
check("a fourth logo is refused", not bc.add_logo(pics[3]) and len(BR.logos(cfg)) == 3)
first = BR.logos(cfg)[0]; c0 = Image.open(first).getpixel((5, 5))
bc.move(first, 1)
check("logos change order", Image.open(BR.logos(cfg)[1]).getpixel((5, 5)) == c0)
bc.remove(BR.logos(cfg)[2])
check("a logo can be removed", len(BR.logos(cfg)) == 2 and len(w.rail_brand.paths) == 2)
# ---- the banner
w.open_effort("Kestrel")
w.go("home"); app.processEvents()
hp = w.home_page; bn = hp.banner
check("the page title is Effort Home", w.page_title.text() == "Effort Home")
check("the banner: the effort's name, client and solicitation", bn.name.text() == "Kestrel" and "USSF SSC" in bn.sub.text()
      and "FA8810-26-R-0042" in bn.sub.text())
check("no picture yet: a spot to add one", "Effort image" in bn.pic.text())
bn.choose_picture(patch)
check("the effort picture is kept in the effort, made smaller", BR.has_picture(w.ws.root) and max(Image.open(BR.picture_path(w.ws.root)).size) <= 800
      and not bn.pic.icon().isNull())
due = (datetime.datetime.now() + datetime.timedelta(days=12, hours=3)).replace(second=0, microsecond=0)
RR.Record(w.ws.root).set_due(due.strftime("%Y-%m-%dT%H:%M"), "MT")
bn.save_details({"pm": "Dana Ruiz", "sensitivity": "CUI", "fields": [{"label": "Capture manager", "value": "Sam Ortiz"},
                                                                      {"label": "Contract vehicle", "value": "SpEC OTA"}]})
app.processEvents()
ident = json.load(open(os.path.join(w.ws.root, "record.json")))["identity"]
check("details are saved in the effort's record", ident["pm"] == "Dana Ruiz" and ident["sensitivity"] == "CUI" and len(ident["fields"]) == 2)
spots = dict(bn.spots)
check("the banner shows the proposal manager and the effort's own spots", spots.get("PROPOSAL MANAGER") == "Dana Ruiz"
      and spots.get("CAPTURE MANAGER") == "Sam Ortiz" and spots.get("CONTRACT VEHICLE") == "SpEC OTA", spots)
check("the countdown: days and a ticking clock to the minute", bn.days.text() == "12 days" and bn.clock.text().count(":") == 2
      and bn.timer.isActive(), (bn.days.text(), bn.clock.text()))
bn.tick(now=due - datetime.timedelta(days=1, hours=2, minutes=3, seconds=4))
check("the countdown reads the time left", bn.days.text() == "1 day" and bn.clock.text() == "02:03:04", (bn.days.text(), bn.clock.text()))
bn.tick(now=due + datetime.timedelta(days=2))
check("after the due time it says so", bn.days.text() == "Passed" and "2 day" in bn.clock.text())
check("CUI marks every page with a strip", w.marking.isVisibleTo(w) and w.marking.text() == "CUI")
w.go("assign"); app.processEvents()
check("the strip stays on every page", w.marking.isVisibleTo(w))
bn.save_details({"sensitivity": "Not CUI"})
check("Not CUI: no strip", not w.marking.isVisibleTo(w))
bn.save_details({"sensitivity": "Proprietary"})
check("Proprietary: its own strip", w.marking.isVisibleTo(w) and w.marking.text() == "Proprietary")
bn.save_details({"client": "SSC Space Systems Command", "solicitation": "FA8810-26-R-0042"})
check("the client set on the banner goes to the effort list", E.EffortList(LIST, "Kestrel").load().client == "SSC Space Systems Command")
pl = PK.plan(LIST, w.ws.root)
check("an effort package carries the picture and the details", "effort picture.png" in str(pl) and "record.json" in str(pl))
w.close_effort()
check("closing the effort takes its strip away", not w.marking.isVisibleTo(w))
w.open_effort("Kestrel"); w.go("home"); app.processEvents()
check("opening it again brings the strip back", w.marking.text() == "Proprietary" and w.marking.isVisibleTo(w))
# ---- Customize Home
check("the default home is the proposal manager's", hp.lay["role"] == "Proposal Manager" and hp.shown[0] == "stage" and "mywork" not in hp.shown)
import setupdoc as SD
hp.customize({"role": "Author", "order": BR.preset("Author")["order"], "hidden": BR.preset("Author")["hidden"], "me": "A. Lee"})
st = json.load(open(A.SETTINGS_FILE))
check("an author's home: My work first, kept in the person's settings", hp.shown[0] == "mywork" and hp.mywork.isVisibleTo(w)
      and not hp.info.isVisibleTo(w) and st["home_layout"]["role"] == "Author" and st["my_name"] == "A. Lee")
check("the layout is never in the effort", "home_layout" not in open(os.path.join(w.ws.root, "record.json")).read())
order = ["calendar"] + [k for k in BR.preset("Author")["order"] if k != "calendar"]
hp.customize({"role": "Author", "order": order, "hidden": ["info", "timeline"]})
check("show, hide and order the sections", hp.shown[0] == "calendar" and "goals" in hp.shown and "timeline" not in hp.shown
      and "customized" in hp.role_pill.text())
me, reqs, tasks, qs = hp.my_items()
check("My work is for the named person", me == "A. Lee")
hp.customize({"role": "Proposal Manager", "order": BR.preset("Proposal Manager")["order"], "hidden": BR.preset("Proposal Manager")["hidden"]})
check("back to a role's layout", not hp.lay["custom"] and hp.shown[0] == "stage")
# ---- the calendar file
tpl = hp.calfiles.template(os.path.join(tmp, "tpl.xlsx"))
check("the calendar template: the columns and a guide", EC.read_rows(tpl) == [] and len(EC.COLUMNS) == 10)
import openpyxl
wb = openpyxl.load_workbook(tpl); ws = wb["Calendar"]
ws.append(["12/15/2026", "2:30 PM", "", "Mountain Time", "Proposal due", "Final proposal due", "", "", "", ""])
ws.append(["11/20/2026", "9:00 AM", "4:00 PM", "MT", "Review", "Red team review", "Dana Ruiz", "Red team", "Room 2B", "Bring the packet"])
ws.append(["11/18/2026", "", "", "", "Stage start", "", "", "Red team", "", ""])
ws.append(["11/21/2026", "", "", "", "Stage end", "", "", "Red team", "", ""])
ws.append(["11/10/2026", "", "", "", "Task", "Draft the management volume", "A. Lee", "", "", "Use the outline"])
ws.append(["", "", "", "", "Meeting", "No date here", "", "", "", ""])
ws.append(["11/25/2026", "", "", "", "Stage start", "", "", "Blue team", "", ""])
ws.append(["12/01/2026", "noon", "", "MT", "Orals", "Orals dry run", "", "", "Studio", ""])
wb.save(os.path.join(tmp, "cal.xlsx"))
pl = hp.calfiles.import_file(os.path.join(tmp, "cal.xlsx"), apply=False)
acts = [p["action"] for p in pl]
check("the preview says what each row does", acts == ["due", "add event", "stage start", "stage end", "add task", "skip", "skip", "add event"], acts)
check("skipped rows say why", "No date" in pl[5]["why"] and "Blue team" in pl[6]["why"])
check("nothing changes until Apply", RR.Record(w.ws.root).data["due"] == due.strftime("%Y-%m-%dT%H:%M"))
hp.calfiles.import_file(os.path.join(tmp, "cal.xlsx"), apply=True)
r = RR.Record(w.ws.root)
check("Proposal due sets the due date to the minute, with its zone", r.data["due"] == "2026-12-15T14:30" and r.data["zone"] == "MT" and r.zone_key() == "MT")
check("the banner countdown follows it", "Dec 15, 2026, 2:30 p.m. MST" in bn.due.text(), bn.due.text())
rt = r.stage(next(s["id"] for s in r.stages if s["name"] == "Red team"))
check("stage rows set the stage's planned start and end", rt["planned"] == "2026-11-18" and rt["planned_end"] == "2026-11-21")
t = next((t for t in r.data["tasks"] if t["title"] == "Draft the management volume"), None)
check("a task row adds a task with its owner and due date", t and t["owner"] == "A. Lee" and t["due"] == "2026-11-10" and t["notes"] == "Use the outline")
ev = {e["title"]: e for e in r.data["events"]}
e = ev.get("Red team review", {})
check("reviews and meetings go on the calendar with times, place and details", e.get("start") == "09:00" and e.get("end") == "16:00"
      and e.get("location") == "Room 2B" and ev.get("Orals dry run", {}).get("start") == "12:00")
cal = r.calendar(first=datetime.date(2026, 11, 20), last=datetime.date(2026, 11, 20))
check("the calendar shows the review on its day, with its time", any(k == "meeting" and "9:00 a.m. MST to 4:00 p.m. Red team review (Room 2B)" == x
                                                                     for k, x in cal.get(datetime.date(2026, 11, 20), [])), cal)
hp.pick_day(datetime.date(2026, 11, 20)); app.processEvents()
pl2 = hp.calfiles.import_file(os.path.join(tmp, "cal.xlsx"), apply=False)
check("importing the same file again changes nothing", all(p["action"] in ("same", "skip") for p in pl2), [p["action"] for p in pl2])
ws.cell(7, 2).value = "10:00 AM"; wb.save(os.path.join(tmp, "cal.xlsx"))
hp.calfiles.import_file(os.path.join(tmp, "cal.xlsx"), apply=True)
r = RR.Record(w.ws.root)
check("a changed row updates its entry instead of adding a copy", len([e for e in r.data["events"] if e["title"] == "Red team review"]) == 1
      and next(e for e in r.data["events"] if e["title"] == "Red team review")["start"] == "10:00")
check("Undo import is offered", hp.calfiles.undo_btn.isVisibleTo(w))
hp.calfiles.undo()
r = RR.Record(w.ws.root)
check("Undo import puts the calendar back as before the last import", next(e for e in r.data["events"] if e["title"] == "Red team review")["start"] == "09:00")
# export, and back
x = hp.calfiles.export("xlsx", os.path.join(tmp, "out.xlsx"))
rows = EC.read_rows(x)
kinds = {row["Kind"] for row in rows}
check("Export: the whole calendar with its details", {"Proposal due", "Stage start", "Stage end", "Task", "Review", "Orals"} <= kinds
      and any(row["Details"] == "Bring the packet" for row in rows), kinds)
check("an export imports back unchanged", all(p["action"] in ("same",) for p in EC.plan(rows, RR.Record(w.ws.root))),
      [(p["kind"], p["action"], p["why"]) for p in EC.plan(rows, RR.Record(w.ws.root)) if p["action"] != "same"])
ics = hp.calfiles.export("ics", os.path.join(tmp, "out.ics"))
txt = open(ics, encoding="utf-8").read()
check("Outlook export: one event per date, times to the minute", txt.count("BEGIN:VEVENT") == len(rows) and "DTSTART:20261215T213000Z" in txt
      and "LOCATION:Room 2B" in txt)
back = EC.read_rows(ics, "Kestrel")
check("an Outlook export imports back unchanged", all(p["action"] == "same" for p in EC.plan(back, RR.Record(w.ws.root))),
      [(p["kind"], p["title"], p["action"], p["why"]) for p in EC.plan(back, RR.Record(w.ws.root)) if p["action"] != "same"])
outlook = os.path.join(tmp, "outlook.ics")
open(outlook, "w").write("BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\nDTSTART;TZID=Mountain Standard Time:20261203T130000\r\n"
                         "DTEND;TZID=Mountain Standard Time:20261203T140000\r\nSUMMARY:Pink team review kickoff\r\n"
                         "LOCATION:Teams\r\nDESCRIPTION:Agenda\\, roles\r\nEND:VEVENT\r\nEND:VCALENDAR\r\n")
p3 = EC.plan(EC.read_rows(outlook), RR.Record(w.ws.root))
check("an Outlook calendar file imports: its kind from its wording", p3[0]["kind"] == "Review" and p3[0]["start"] == "13:00"
      and p3[0]["zone"] == "MT" and p3[0]["details"] == "Agenda, roles", p3[0])
check("times read every common way", [EC.parse_time(v) for v in ("2:00 PM", "14:00", "2 p.m.", "1400", "noon", "9am", "25:00")]
      == ["14:00", "14:00", "14:00", "14:00", "12:00", "09:00", None])
w.close()
n = sum(checks)
print(f"QT BRAND PASS ({n}/{len(checks)})" if n == len(checks) else f"QT BRAND FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
