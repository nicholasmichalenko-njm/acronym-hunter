"""3.62.0 the deliverable page, offscreen: double-click a deliverable (card or list row) to open its page; Overview saves
the type (a customer file too), owner, due date, overview and guidelines; a volume deliverable becomes its Structure
volume and its sections are its parts; format groups set values once and a deliverable's own value wins; parts of its
own; attachments from the customer or ours; references; the discussion board (dated, the writer's name, filter by
person, pin, in the timeline); its dates on the effort's calendar; Arrange sets the team's order; People: add a person
once from any picker. Fictional content."""
import datetime, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, effortrec as RR, workspace as W, deliverables as DL, delivmore as DM, office_pdf as OP
OP.available = lambda: False
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


today = datetime.date.today()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
ws0 = W.Workspace(W.data_dir_for(LIST), "Kestrel")
rec = RR.Record(ws0.root)
vol = DL.add(rec, "Volume I Technical", "Volume", owner="A. Lee")
form = DL.add(rec, "Attachment J-4 Pricing Workbook", "Attachment")
slides = DL.add(rec, "Oral presentation slides", "Presentation")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.authors.add("A. Lee") if hasattr(w.authors, "add") else None
w.go("deliverables"); app.processEvents()
pg = w.deliverables_page
check("the page lists the deliverables on the board", len(pg.board.cards) == 3)
card = pg.board.cards[vol]
ev = QMouseEvent(QMouseEvent.MouseButtonDblClick, card.rect().center(), card.mapToGlobal(card.rect().center()), Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)
QApplication.sendEvent(card, ev); app.processEvents(); app.processEvents()
check("double-click a card: the deliverable's own page", pg.stack.currentWidget() is pg.one and pg.one.did == vol
      and pg.one.title.text() == "Volume I Technical")
one = pg.one
check("its page has the tabs: overview, format and submission, parts and people, requirements, attachments, discussion, dates",
      [one.tabs.tabText(i) for i in range(one.tabs.count())] == list(__import__("skqt.delivpage", fromlist=["TABS"]).TABS))
due = (today + datetime.timedelta(days=12)).isoformat()
one.save_overview({"name": "Volume I Technical", "kind": "Volume", "status": "Drafting", "owner": "A. Lee", "due": due,
                   "source": "Named by the customer", "about": "The technical approach for the ground system.",
                   "guidelines": "30 pages; address each PWS task."})
d = DL.get(RR.Record(ws0.root), vol)
check("Overview saves the status, due date, overview and guidelines", d["status"] == "Drafting" and d["due"] == due
      and d["guidelines"].startswith("30 pages") and one.state_pill.text() == "Drafting")
one.close() if False else None
pg.close_deliverable(); app.processEvents()
check("< All deliverables goes back to the board", pg.stack.currentWidget() is pg.all_box)
pg.view.setCurrentIndex(1); app.processEvents()
pg.table.cellDoubleClicked.emit(pg.ids.index(form), 0); app.processEvents()
check("double-click a row in the list opens its page too", pg.stack.currentWidget() is pg.one and pg.one.did == form)
pg.one.save_overview({"name": "Attachment J-4 Pricing Workbook", "kind": "Customer file", "status": "Not started", "owner": "",
                      "due": "", "source": "Named by the customer", "about": "", "guidelines": ""})
check("a deliverable can be the customer's own file (its type)", DL.get(pg.ctx.rec, form)["kind"] == "Customer file")
# format groups
dlg = pg.groups_window(run=False)
gid = dlg.add("Written volumes")
DM.set_group_value(pg.ctx.rec, gid, "font", "Times New Roman 12")
DM.set_group_value(pg.ctx.rec, gid, "margins", "1 inch")
dlg.fill()
check("Format groups: a group with its values, one row each", dlg.table.rowCount() == 1 and dlg.table.item(0, 0).text() == "Written volumes"
      and DM.group(pg.ctx.rec, gid)["values"]["font"] == "Times New Roman 12")
pg.open_deliverable(vol, "Format and submission"); app.processEvents()
pg.one.set_group(gid)
eff = {k: (v, wh) for k, _l, v, wh in DM.effective(pg.ctx.rec, DL.get(pg.ctx.rec, vol))}
check("a deliverable in the group takes its values", eff["font"] == ("Times New Roman 12", "group Written volumes"))
pg.one.set_own("font", "Arial 11")
eff = {k: (v, wh) for k, _l, v, wh in DM.effective(pg.ctx.rec, DL.get(pg.ctx.rec, vol))}
check("its own value wins; the rest still come from the group", eff["font"] == ("Arial 11", "this deliverable") and eff["margins"][1] == "group Written volumes")
pg.one.set_own("font", "")
check("clearing its own value gives the field back to the group", DM.value(pg.ctx.rec, DL.get(pg.ctx.rec, vol), "font") == "Times New Roman 12")
check("the tab shows each value with where it comes from", pg.one.fmt.rowCount() == len(DM.FIELDS)
      and any(pg.one.fmt.item(i, 2).text() == "group Written volumes" for i in range(pg.one.fmt.rowCount())))
# the Structure volume
pg.one.tabs.setCurrentIndex(0); app.processEvents()
if w.review is not None:
    lab = pg.one.make_volume()
    check("Make it a Structure volume: a volume in the Structure Builder, linked", lab and DL.get(pg.ctx.rec, vol)["volume"] == lab
          and lab in pg.volume_heads())
else:
    check("with no review yet the page says how it links to Structure", pg.one.e_vol.count() >= 1)
# parts
pg.one.tabs.setCurrentIndex(2); app.processEvents()
pid = pg.one.add_part("Cost narrative", "A. Lee")
check("a part of its own with its owner", pid and DL.get(pg.ctx.rec, vol)["parts"][0]["owner"] == "A. Lee" and pg.one.part_table.rowCount() == 1)
check("everyone on it: the owner and the parts' people", "A. Lee" in DM.people(DL.get(pg.ctx.rec, vol)))
# attachments and references
pg.open_deliverable(slides, "Attachments and files"); app.processEvents()
pg.one.add_attachment("Speaker resumes", "Ours")
pg.one.add_attachment("Slide template from the customer", "Customer")
check("attachments from the customer or ours", [a["source"] for a in DL.get(pg.ctx.rec, slides)["attachments"]] == ["Ours", "Customer"]
      and pg.one.att_table.rowCount() == 2)
pg.one.add_reference("Past orals deck", "Library: Orals 2025", "Same panel format")
check("a reference with why it matters", DL.get(pg.ctx.rec, slides)["references"][0]["note"] == "Same panel format")
pg.one.remove_attachment(0)
check("remove an attachment", len(DL.get(pg.ctx.rec, slides)["attachments"]) == 1)
# discussion
pg.open_deliverable(slides, "Discussion"); app.processEvents()
e1 = pg.one.post("Panel wants 20 minutes, not 30.", who="K. Park")
e2 = pg.one.post("Rehearsal booked for Thursday.", who="A. Lee")
pg.one.toggle_pin(e1)
items = [pg.one.posts.item(i).text() for i in range(pg.one.posts.count())]
check("the discussion: dated notes with the writer's name, pinned first", len(items) == 2 and items[0].startswith("[Pinned]") and "K. Park" in items[0])
check("filter by person", pg.one.filter_person("A. Lee") == 1 and "Rehearsal" in pg.one.posts.item(0).text())
pg.one.filter_person("")
check("each note is in the effort's timeline", any("Discussion on Oral presentation slides" in e["text"] for e in RR.Record(ws0.root).data.get("timeline", [])))
# dates on the calendar
pg.open_deliverable(slides, "Dates"); app.processEvents()
dd = (today + datetime.timedelta(days=3)).isoformat()
pg.one.add_date(dd, "Dry run")
import effortstate as ES
st = ES.State(w.ws, w.effort_path, w.review.M if w.review is not None else None)
cal = st.calendar(first=today, last=today + datetime.timedelta(days=20))
txt = [t for v in cal.values() for _k, t in v]
check("its due date and its own dates are on the effort's calendar", "Due: Volume I Technical" in txt and "Oral presentation slides: Dry run" in txt, txt)
# arrange
pg.close_deliverable()
pg.view.setCurrentIndex(2); app.processEvents()
check("Arrange lists every deliverable to drag", pg.order_list.count() == 3)
from skqt import delivextras as DX
DX.save_order(pg, [slides, form, vol])
check("the team's order is kept", [d["id"] for d in DL.items(RR.Record(ws0.root))] == [slides, form, vol])
pg.order_mode.setCurrentIndex(1); app.processEvents()
check("the board can follow the team's order", [c["id"] for c in pg.cards] == [slides, form, vol])
# a volume deliverable and its Structure volume are one (the rules, with a matrix of its own)
import compliance as C, setupdoc as SD


class _R:
    def __init__(self, M):
        self.M = M

    def snap(self, *_a):
        pass


M = C.Matrix(os.path.join(tmp, "m.xlsx"), "m")
r2 = RR.Record(ws0.root)
dv = DL.get(r2, vol)
dv["volume"] = ""
lab = DM.make_volume(_R(M), dv)
import outline_ops as O
sec = O.add(M, "Ground Architecture", parent=lab)
SD.set_people(M, sec, lead="A. Lee", with_="K. Park")
check("Make it a Structure volume: the volume is added and linked, named without its number", lab and dv["volume"] == lab
      and lab.endswith("Technical") and lab.count("Volume") == 1, lab)
check("its Structure sections are its parts, with their leads and contributors",
      DM.structure_parts(dv, M) == [(sec, "A. Lee", "K. Park")] and "K. Park" in DM.people(dv, M))
# people: add once from any picker
from skqt import people as PP
cb = PP.name_combo(w, "")
check("every picker ends with Add a person...", cb.itemData(cb.count() - 1) == PP.ADD_KEY)
cb.setCurrentIndex(cb.count() - 1)
got = PP._add_from(w, cb, answer="M. Chen")
check("Add a person...: the name joins the effort's people and is chosen", got == "M. Chen" and PP.combo_name(cb) == "M. Chen"
      and "M. Chen" in w.authors.for_effort("Kestrel"))
cb2 = PP.name_combo(w, "")
check("... and every picker after offers it", cb2.findData("M. Chen") >= 0)

print(f"QT DELIV 362 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
