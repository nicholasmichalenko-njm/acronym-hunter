"""3.83.0 the shared parts, offscreen: the section panel (Management guidance with its grey placeholder, saved as typed;
references and notes for authors, acted on the row; the section's notes and context copied into the guidance or sent
to the authors; the tray and Point at), the split view's lines for the selection only with an arrow at the edge for
one scrolled away, the bar placed beside the selection and never over it and closed by a click on blank space, and
the Setup page using the panel. Fictional content (the Kestrel set)."""
import datetime, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QLabel, QListWidget, QPushButton, QWidget
import effortrec as RR, meetings as MT, quicknote as QN, sectionnotes as SN
from skqt import design as D
from skqt.sectionpanel import PLACEHOLDER, SectionPanel
from skqt import splitlines as SL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


app = QApplication([]); D.apply(app)


def spin(ms=0):
    t = time.time()
    while True:
        app.processEvents()
        if time.time() - t >= ms / 1000:
            break
        time.sleep(0.01)


class M:
    def __init__(self):
        self.items, self.setup, self.pending = [], None, False


class Review:
    def __init__(self):
        self.snaps = 0

    def snap(self):
        self.snaps += 1


class Host:
    def __init__(self):
        self.review, self.n, self.effort_path = Review(), 0, ""

    def changed(self):
        self.n += 1


tmp = tempfile.mkdtemp()
rec, m, host = RR.Record(tmp), M(), Host()
p = SectionPanel(host, lambda: m, lambda: RR.Record(tmp)); p.resize(420, 700); p.show()
p.show_section("3.1"); spin()
check("the guidance box says Add Management Guidance Text in grey until typed", p.guide.placeholderText() == PLACEHOLDER
      and PLACEHOLDER == "Add Management Guidance Text" and p.guide.toPlainText() == "")
p.guide.setFocus(); p.guide.insertPlainText("Lead with the transition plan.")
check("typing says it is saving", p.saved.text() == "Saving...")
spin(1000)
check("... and saves on its own, with no button", SN.guidance(m, "3.1") == "Lead with the transition plan." and p.saved.text() == "Saved.")
check("one undo step for the run of typing", host.review.snaps == 1 and host.n == 1, (host.review.snaps, host.n))
check("the panel has no Save button", not any(b.text().startswith("Save") for b in p.findChildren(QPushButton)))
p.guide.insertPlainText(" Then the risks.")
p.show_section("3.2")
check("leaving the section saves what was typed", SN.guidance(m, "3.1").endswith("Then the risks."))
check("the next section's box is empty, with its placeholder", p.guide.toPlainText() == "")
p.show_section("3.1")
check("coming back shows its guidance", p.guide.toPlainText().endswith("Then the risks."))

# references
check("one Add a reference button, with a menu", p.b_add.menu() is not None
      and [a.text() for a in p.b_add.menu().actions()] == ["From the Effort Library...", "Add files...", "A note for the authors..."])
check("files from the Effort Library become references", p.add_files(library=True, files=[os.path.join(tmp, "Kestrel Staffing Plan.docx")]) == 1)
check("a note for the authors", p.add_note("Use the 30-60-90 day framing.") is not None and p.refs.count() == 2)
p.refs.setCurrentRow(0)
menu = [a.text() for a in p.ref_menu(run=False).actions() if a.text()]
check("act on the row: where to look, the note, take it out", menu == ["Where to look...", "Edit the note...", "Take it out"], menu)
rid = p.refs.item(0).data(Qt.UserRole)
check("where to look shows on the row", p.edit_ref(rid, "where", "pages 4 to 6") and "pages 4 to 6" in p.refs.item(0).text())
check("the reference reads as a Word comment", SN.comment_text(SN.refs(m, "3.1")[0]) == "Reference: Kestrel Staffing Plan.docx (pages 4 to 6)")
check("a reference comes out", p.remove_ref(p.refs.item(1).data(Qt.UserRole)) and p.refs.count() == 1)

# notes and context
SN.note_on(rec, "3.1", "The customer asked about weekend coverage.")
mid = MT.add_meeting(rec, "Kickoff", datetime.date.today().isoformat())
MT.add_topic(RR.Record(tmp), mid, "Show the staffing ramp by month.", target="3.1")
p.fill()
check("the section's note and topic show, with a count", p.ctx.count() == 2 and p.ctx_head.text().endswith("(2)"), p.ctx_head.text())
check("nothing-yet line hides when there is context", not p.ctx_empty.isVisible())
row = next(i for i in range(p.ctx.count()) if "weekend" in p.ctx.item(i).text())
p.ctx.setCurrentRow(row)
check("act on the row: copy into guidance, send to authors, keep as context",
      [a.text() for a in p.ctx_menu(run=False).actions()] == ["Copy into guidance", "Send to authors", "Keep as context"])
check("Copy into guidance puts the words in the box", p.use(p.ctx.item(row).data(Qt.UserRole), "guidance")
      and p.guide.toPlainText().endswith("weekend coverage.") and SN.guidance(m, "3.1").endswith("weekend coverage."))
check("the row says it was used", "copied into the guidance" in next(p.ctx.item(i).text() for i in range(p.ctx.count())
                                                                      if "weekend" in p.ctx.item(i).text()))
trow = next(i for i in range(p.ctx.count()) if "ramp" in p.ctx.item(i).text())
check("Send to authors adds a note for the authors", p.use(p.ctx.item(trow).data(Qt.UserRole), "authors") and p.refs.count() == 2)

# the tray
check("no tray without waiting notes", not p.tray.isVisible())
qid = QN.add(RR.Record(tmp), "Ask the pricing lead about the option years.")
p.fill()
check("a waiting note shows in the tray", p.tray.isVisible() and p.tray.count() == 1 and "(1)" in p.tray_head.text())
p.tray.setCurrentRow(0)
check("act on the row: Point at this section", [a.text() for a in p.tray_menu(run=False).actions()] == ["Point at 3.1"])
check("Point at moves it under the section", p.point_here(qid) and not p.tray.isVisible()
      and any("option years" in p.ctx.item(i).text() for i in range(p.ctx.count())))

# the lines and the bar
check("a point in view is in view", SL.ends(50, 0, 100) == (50, 0))
check("above the pane: at the top edge, pointing up", SL.ends(-40, 0, 100) == (0, -1))
check("below the pane: at the bottom edge, pointing down", SL.ends(400, 0, 100) == (100, 1))
area = (0, 0, 800, 600)
for t in ((100, 300, 200, 20), (100, 10, 200, 20), (100, 0, 200, 600), (0, 0, 800, 600), (600, 590, 300, 10)):
    x, y = SL.place_bar((240, 32), t, area)
    if t == (0, 0, 800, 600):
        continue                                      # a selection that fills the whole area: the bar sits at its edge
    check(f"the bar never covers the selection {t}", not SL.overlaps((x, y, 240, 32), t), (x, y))
check("the bar goes above when there is room", SL.place_bar((240, 32), (100, 300, 200, 20), area) == (100, 300 - SL.GAP - 32))
check("... below when there is none above", SL.place_bar((240, 32), (100, 10, 200, 20), area) == (100, 10 + 20 + SL.GAP))
check("the bar stays inside the area", SL.place_bar((240, 32), (700, 300, 50, 20), area)[0] == 800 - 240)
left, right = QListWidget(), QListWidget()
for i in range(60):
    left.addItem(f"Customer sentence {i}"); right.addItem(f"Section {i}")
links = []
v = SL.SplitView(left, right, lambda: links); v.resize(700, 400); v.show(); spin(50)
check("no selection, no lines", v.gutter.compute() == [])
links[:] = [(left.visualItemRect(left.item(2)), right.visualItemRect(right.item(3)))]
got = v.gutter.compute()
check("one line for the selection, both ends in view", len(got) == 1 and got[0][1] == 0 and got[0][3] == 0, got)
r2 = right.viewport().mapTo(v, right.visualItemRect(right.item(3)).center())
check("the line meets the right pane at its row", abs(got[0][2] - v.gutter.mapFrom(v, r2).y()) <= 1, (got, r2))
check("... and the left pane at its row", got[0][0] < got[0][2])
links[:] = [(left.visualItemRect(left.item(2)), right.visualItemRect(right.item(55)))]
got = v.gutter.compute()
check("a target scrolled away is an arrow at the pane's bottom edge", got and got[0][3] == 1, got)
right.scrollToItem(right.item(55)); spin(20)
links[:] = [(left.visualItemRect(left.item(2)), right.visualItemRect(right.item(55)))]
check("scrolled to, it is in view again", v.gutter.compute()[0][3] == 0)
v.gutter.repaint()
vp = QWidget(); vp.resize(600, 400); vp.show()
bar = QLabel("Requirement  Context  Customer  Not this"); bh = SL.BarHost(bar, vp)
sel = QRect(50, 200, 300, 24)
bx, by = bh.show_for(sel)
check("the bar opens beside the selection", bar.isVisible() and not bar.geometry().intersects(sel))


def press(pt):
    e = QMouseEvent(QMouseEvent.MouseButtonPress, QPoint(*pt), vp.mapToGlobal(QPoint(*pt)), Qt.LeftButton, Qt.LeftButton,
                    Qt.NoModifier)
    QApplication.sendEvent(vp, e)


press((60, 210))
check("a click on the selection keeps the bar", bar.isVisible())
press((500, 380))
check("a click on blank space closes it", not bar.isVisible())

print(f"QT SHARED 383 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
