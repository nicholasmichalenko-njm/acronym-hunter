"""4.50.0 Programs in the window, offscreen: All Efforts has three views and Programs starts empty with its empty state;
+ New program with a name makes the program and opens it on its Overview (the program panel, no page tabs); the menu
leaves out the effort's steps, the Calendar and Tasks and reads THE PROGRAM; an effort opened afterwards brings its steps
and words back; the Working on box lists efforts, a line, then programs; the start form no longer offers Program
deliverables while Effort types... still lists it; an effort of that type is offered the move, can be kept as an effort
(its card's menu still offers it), made a program with its documents and files where they were, and made an effort
again; Tasks across efforts and My Work leave programs out. Fictional (Kestrel, Heron, Osprey)."""
import datetime, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
A.CONFIG_DIR = os.path.join(A.DATA_DIR, "config"); os.makedirs(A.CONFIG_DIR, exist_ok=True)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effortrec as RR, programs as PG, docversions as DV, mywork as MW, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D, programsview as PV, starteffort as SE
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = A.CONFIG_DIR
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
toasts = []
_toast = w.toast
w.toast = lambda t: (toasts.append(t), _toast(t))


def pump():
    for _ in range(5):
        app.processEvents(); time.sleep(0.01)


base = os.path.join(A.DATA_DIR, "Efforts")
hp = w.efforts_page
hp.add_effort({"name": "Heron", "path": os.path.join(base, "Heron", "Heron_Effort_List.xlsx")})
w.go("efforts"); pump()
check("All Efforts has three views", [b.text() for b in (hp.show_live, hp.show_prog, hp.show_arch)] == ["Efforts (1)", "Programs (0)", "Archived (0)"]
      and all(b.isCheckable() for b in (hp.show_live, hp.show_prog, hp.show_arch)))
hp.show_prog.setChecked(True); pump()
check("Programs starts empty, with its empty state and + New program", hp.prog_empty.isVisibleTo(w) and not hp.empty.isVisibleTo(w)
      and not hp.cards and hp.add_btn.text() == "+ New program" and not hp.imp_btn.isVisibleTo(w) and not hp.folder_btn.isVisibleTo(w)
      and hp.count.text() == "" and not hp.show_arch.isChecked() and not hp.show_live.isChecked())
hp.show_arch.setChecked(True); pump()
check("the views are one choice: Archived leaves Programs", hp.show_arch.isChecked() and not hp.show_prog.isChecked() and hp.add_btn.text() == "+ Add an Effort")
hp.show_live.click(); pump()
check("Efforts as before", not hp.show_arch.isChecked() and not hp.show_prog.isChecked() and hp.imp_btn.isVisibleTo(w)
      and list(hp.cards) == ["Heron"] and hp.add_btn.text() == "+ Add an Effort")
hp.show_prog.setChecked(True); pump()
check("a name that cannot be used is refused, with the reason", PV.new_program(w, "heron") is None and PG.names(w.efforts) == [])
got = PV.new_program(w, "Kestrel Fleet"); pump()
check("+ New program with a name makes the program and opens it", got == "Kestrel Fleet" and w.effort_name == "Kestrel Fleet"
      and PG.is_program(w.efforts, "Kestrel Fleet") and PV.is_open(w))
check("it opens on its Overview, with the program panel and no page tabs", w.stack.currentWidget() is w.overview_page
      and w.overview_page.program.isVisibleTo(w) and not w.overview_page.body.isVisibleTo(w) and not w.overview_page.banner.isVisibleTo(w)
      and not w.page_tabs_box.isVisibleTo(w) and w.overview_page.program.count.text() == "No program documents yet"
      and w.overview_page.program.name.text() == "Kestrel Fleet")
op = w.overview_page.program
check("the panel: Add documents, and the doors a program has (4.52.0)", op.add_btn.text() == "Add documents" and list(op.doors.btns) == ["acronyms", "check"])
vis = {k for k, b in w.step_btns.items() if not b.isHidden()}
check("the menu leaves out the steps, the Calendar and Tasks", not (vis & set(PG.OUT)), vis & set(PG.OUT))
check("and shows Overview, Documents, Formatting, Quick tools, Settings", {"home", "library", "templates", "tools", "settings"} <= vis
      and not w.group_heads["Formatting"].isHidden(), vis)
check("the head reads THE PROGRAM; Documents has no number; the switcher says Program", w.group_heads["Effort"].text() == "THE PROGRAM"
      and w.step_btns["library"].circle.isHidden() and w.rail_effort.stage.text() == "Program" and w.rail_effort.cap.text() == "Program"
      and not any(b.stage_dot.isVisibleTo(w) for b in w.step_btns.values()))
w.go("acronyms"); pump()                                 # 4.52.0: the panel's Acronyms is a door (it asks for a file)
check("Acronyms opens the acronyms page with no Shred stepper, tabs or title", w.stack.currentWidget() is w.acronym_page
      and not w.stepper.isVisibleTo(w) and not w.page_tabs_box.isVisibleTo(w) and w.page_title.text() != "Shred", w.page_title.text())
op.add_btn.click(); pump()
check("Add documents opens Documents", w.stack.currentWidget() is w.library_page)
w.go("efforts"); pump()
check("its card in the Programs view", list(hp.cards) == ["Kestrel Fleet"] and hp.count.text() == "1 program"
      and hp.show_prog.text() == "Programs (1)" and hp.cards["Kestrel Fleet"].more is None)
hp.open("Heron"); pump()
vis = {k for k, b in w.step_btns.items() if not b.isHidden()}
check("an effort opened afterwards brings the steps and the effort's words back", {"assign", "matrix", "calendar", "tasks"} <= vis
      and w.group_heads["Effort"].text() == "THE EFFORT'S PATH" and not w.step_btns["library"].circle.isHidden()
      and w.rail_effort.cap.text() == "Effort" and not PV.is_open(w), vis)
box = [w.effort_box.itemText(i) for i in range(w.effort_box.count())]
check("the Working on box: efforts, a line, then programs", box[-2:] == ["", "Kestrel Fleet"] and box.index("Heron") < box.index(""), box)
from skqt.frame import effort_menu
acts = [a.text() for a in effort_menu(w).actions()]
check("the switcher: Switch to each, the programs after a line", "Switch to Kestrel Fleet" in acts
      and acts[acts.index("Switch to Kestrel Fleet") - 1] == "", acts)
# the start form
sd = SE.StartDialog(w); fm = sd.form
names = [fm.etype.itemText(i) for i in range(fm.etype.count())]
td = fm.manage_types(run=False)
check("the start form does not offer Program deliverables; Effort types... still lists it", "Program deliverables" not in names
      and "RFP response" in names and any(td.list.item(i).data(0x0100) == "program" for i in range(td.list.count())), names)
# an effort of the old type
w.close_effort()
hp.add_effort({"name": "Osprey", "path": os.path.join(base, "Osprey", "Osprey_Effort_List.xlsx"), "effort_type": "program"}); pump()
check("an effort started with the type Program deliverables is a candidate", w.effort_name == "Osprey" and PG.candidates(w.efforts) == ["Osprey"])
toasts.clear()
w.open_effort("Heron"); w.open_effort("Osprey"); pump()
check("opening it says once where the offer is", toasts.count(PV.OFFER) == 1 and w.stack.currentWidget() is not w.overview_page, toasts)
r = RR.Record(w.ws.root); r.add_task("Send the Osprey plan", owner="A. Lee", due="2020-01-01")
lib = DV.Library(w.ws.p("documents")).load()
doc = os.path.join(os.path.dirname(w.effort_path), "Plan.txt"); open(doc, "w").write("Osprey plan")
lib.add(doc, [{"x": "Osprey plan"}]); lib.save()
w.save_now()
check("before the move, the work across efforts has Osprey's task", [x["effort"] for x in MW.collect(w.efforts, "A. Lee")] == ["Osprey"])
w.go("efforts"); hp.view("prog"); pump()
check("its row in the Programs view", list(hp.offer_btns) == ["Osprey"] and hp.offer_box.isVisibleTo(w)
      and [b.text() for b in hp.offer_btns["Osprey"]] == ["Make it a program...", "Keep it as an effort"])
PV.keep(w, "Osprey"); pump()
check("Keep it as an effort: the row leaves", hp.offer_btns == {} and not hp.offer_box.isVisibleTo(w) and PG.candidates(w.efforts) == [])
hp.view("live"); pump()
check("the card's menu still offers it", "Make it a program..." in [a.text() for a in hp.card_menu("Osprey").actions()]
      and "Make it a program..." not in [a.text() for a in hp.card_menu("Heron").actions()])


def listing(p):
    out = []
    for d, _s, fs in os.walk(os.path.dirname(p)):
        out += [os.path.relpath(os.path.join(d, f), os.path.dirname(p)) for f in fs if f not in ("lock.json", "qt_view.json")]
    return sorted(out)


opath = w.efforts.get("Osprey")["path"]
w.close_effort()
before = listing(opath)
check("Make it a program... with No changes nothing", not PV.make_program(w, "Osprey", answer=False) and not PG.is_program(w.efforts, "Osprey"))
w.open_effort("Osprey"); pump()
check("Make it a program... with Yes", PV.make_program(w, "Osprey", answer=True) and PG.is_program(w.efforts, "Osprey")
      and w.ws is None and "Osprey is a program now." in toasts)
check("its documents count is intact and no file moved", PG.summary(w.efforts, "Osprey")["documents"] == 1
      and w.efforts.get("Osprey")["path"] == opath and set(before) <= set(listing(opath)), (before, listing(opath)))
check("it left Efforts for Programs", "Osprey" not in hp.cards and hp.show_prog.text() == "Programs (2)")
w.mywork_page.who.clear(); w.mywork_page.who.addItem("A. Lee")
check("My Work leaves programs out", w.mywork_page.load(wait=True) == [])
tp = w.tasks_page
tp.who.clear(); tp.who.addItem("A. Lee"); tp.view = "mine"; tp.fill()
check("Tasks' Mine, across efforts leaves programs out", not any(x and isinstance(x, dict) and x.get("effort") == "Osprey" for x in tp.rows), tp.rows)
hp.view("prog"); pump()
card = hp.cards.get("Osprey")
check("its card: Program, its count, and More with Make it an effort again...", card is not None and card.more is not None
      and [a.text() for a in card.menu().actions()] == ["Open", "Make it an effort again..."])
PV.open_program(w, "Osprey"); pump()
check("it opens as a program, on its Overview", PV.is_open(w) and w.stack.currentWidget() is w.overview_page
      and w.overview_page.program.count.text() == "1 program document")
check("Make it an effort again...", PV.make_effort(w, "Osprey", answer=True) and not PG.is_program(w.efforts, "Osprey")
      and "Osprey" in PG.effort_names(w.efforts) and set(before) <= set(listing(opath)))
hp.view("live"); pump()
check("back in Efforts", "Osprey" in hp.cards)
n = sum(checks)
print(f"QT PROGRAMS 4.50.0 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
