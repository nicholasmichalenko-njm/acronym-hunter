"""3.30.0 the Structure Builder in Qt, offscreen: its own place in the menu (Review keeps Coverage); volume tabs; the
structure with a tag for each section; the toolbar sets Heading 1 to 9, unnumbered, divider, placeholder and a Word
section, adds below and under, changes levels and moves; Enter, Tab and Shift+Tab work like an outline; a drop moves a
section; Add elements puts the kit in; library items are placed in a section and reordered; what is not placed yet goes
into a section; the section's contents (Response Setup) are reordered and taken out; Settings > Response elements keeps
the team's changes and kits; the setup documents carry it all."""
import os, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W, office_pdf as OP, outline_ops as O, responseelements as RE, setupdoc as SD
import structparts as SP, templatelib as TL, excerpts as EX, effortrec as RR, compliance as C
OP.available = lambda: False
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow, RAIL, TABS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")]
lib = TL.Library(cfg)
qp, _st = lib.add("quickpart", "Org chart block", {"entry": "Org chart block", "category": "", "gallery": "Quick Parts"})
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1600, 980); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


check("the menu: Structure Builder is its own place under Compliance; Review keeps Coverage",
      ("structure", "Structure Builder") in dict(RAIL)["Compliance"] and [k for k, _t in TABS["assign"]] == ["assign", "prove"])
w.open_effort("Kestrel")
w.read_page.read(PDFS, os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
check("read", wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page))
M = w.review.M
R = w.review
pg = w.assign_page
vol = O.add_volume(M, "Technical")
t1 = O.add(M, "Technical Approach", parent=vol)
O.add(M, "Systems Engineering", parent=t1)
O.add(M, "Management", after=t1)
b = w.structure_page
w.go("structure"); app.processEvents()
check("the Builder opens on the volume, its sections tagged", w.stack.currentWidget() is b and b.vol_tabs.count() >= 1
      and b.btree.topLevelItemCount() >= 1)
node = lambda lab: next(iter(b.btree.findItems(lab, Qt.MatchExactly | Qt.MatchRecursive, 0)), None)
check("tags: H1 for a section, H2 under it", node("1 Technical Approach").text(1) == "H1" and node("1.1 Systems Engineering").text(1) == "H2",
      (node("1 Technical Approach").text(1), node("1.1 Systems Engineering").text(1)))
b.btree.setCurrentItem(node("1.1 Systems Engineering")); app.processEvents()
check("selecting a section lights its button, like Bold", b.tools["H2"].isChecked() and not b.tools["H1"].isChecked())
new = b.make_level(1)
check("Heading 1: it moves up a level, renumbered", new == "2 Systems Engineering" and node("2 Systems Engineering").text(1) == "H1", new)
new = b.make_level(2)
check("Heading 2 again: under the section before it", new == "1.1 Systems Engineering", (new, O.labels(M)))
new = b.make_kind("unnumbered")
check("Unnumbered: no number, tag UN", new == "Systems Engineering" and node("Systems Engineering").text(1) == "UN" and b.tools["kind:unnumbered"].isChecked())
new = b.make_kind("unnumbered")
check("... a second click takes it off", new == "1.1 Systems Engineering")
b.make_break("landscape")
check("Word section: landscape, tag SEC", node("1.1 Systems Engineering").text(1) == "H2 SEC" and b.tools["brk"].isChecked())
b.make_break(None)
b.answer = "Risk Management"
new = b.add_below()
check("+ Below: a new section at its level, numbered", new == "1.2 Risk Management", new)
b.answer = "Risk Register"
new = b.add_under()
check("+ Under: one level down", new == "1.2.1 Risk Register")
b.btree.setCurrentItem(node("1.2.1 Risk Register")); app.processEvents()
b.btree.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Backtab, Qt.ShiftModifier)); app.processEvents()
check("Shift+Tab: one level up", b.sel == "1.3 Risk Register", b.sel)
b.btree.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Tab, Qt.NoModifier)); app.processEvents()
check("Tab: one level down again", b.sel == "1.2.1 Risk Register", b.sel)
b.answer = "Deliverables"
b.btree.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Return, Qt.NoModifier)); app.processEvents()
check("Enter: a new section below", b.sel == "1.2.2 Deliverables", b.sel)
new = b.drop("2 Management", "1 Technical Approach", "before")
check("a drop before another: moved and renumbered", new == "1 Management" and "2 Technical Approach" in O.labels(M), O.labels(M))
new = b.drop("1 Management", "2 Technical Approach", "into")
check("a drop into another: it goes under it, last", new == "1.3 Management", new)
w.do_undo() if hasattr(w, "do_undo") else w.undo_here(); app.processEvents()
check("Undo puts the drop back", "1 Management" in O.labels(M), O.labels(M))
b.refresh()
new = b.rename("1 Management", "Program Management")
check("Rename (F2 or a double-click)", new == "1 Program Management", new)
deep = "2.1 Systems Engineering"
for n in range(3, 11):
    b.select(deep); b.answer = f"Level {n}"
    deep = b.add_under()
check("subheadings as deep as needed: Heading 10 here", O.heading_level(M, deep) == 10 and node(deep).text(1) == "H10", (deep, node(deep).text(1)))
m = b.menu("2 Technical Approach")
check("right-click a section: its menu", [a.text() for a in m.actions() if a.text()][:2] == ["Rename... (F2)", "Make it"])
# ---------------------------------------------------------------- elements
b.select(vol)
b.add_elements(ids=RE.kit(RE.load(cfg)) + ["appendices"])
labs = O.in_volume(M, vol)
check("Add elements: the kit in the volume, in its parts", labs[1:6] == ["Cover", "Table of Contents", "List of Figures", "List of Tables",
                                                                          "Acronyms and Abbreviations"] and labs[-1] == "Appendices", labs)
check("... tagged EL", node("Table of Contents").text(1) == "EL")
b.add_elements(ids=["toc", "appendices"])
check("unticked ones come out", "List of Figures" not in O.labels(M) and "Table of Contents" in O.labels(M))
# ---------------------------------------------------------------- the library and the section's contents
b.select("2 Technical Approach")
b.fill_library()
row = next(i for i in range(b.lib_list.count()) if (b.lib_list.item(i).data(Qt.UserRole) or {}).get("id") == qp["id"])
b.lib_list.setCurrentRow(row)
b.place_selected()
check("the library shelf: a Quick Part placed in the section", [x["name"] for x in O.lib_items(M, "2 Technical Approach")] == ["Org chart block"])
by = lambda s: next(it for it in M.items if it["text"].startswith(s))
a = by("The Offeror shall describe its technical approach")
R.req([a], "2 Technical Approach")
b.refresh()
kinds = [k for k, _key, _t in b.contents("2 Technical Approach")]
check("in this section, in order: the library item, then the requirement", kinds[:2] == ["lib", "item"], kinds)
b.move_content(1, ("lib", 0))
check("... reordered: library items keep their own order", [k for k, _key, _t in b.contents("2 Technical Approach")][:2] == ["lib", "item"])
b.take_out(("lib", 0))
check("... a library item taken out", not O.lib_items(M, "2 Technical Approach"))
b.take_out(("item", a["id"]))
check("... and a requirement taken out of the section", a["id"] not in SD.placed_in(M).get("2 Technical Approach", []))
# not placed yet
c = by("Each volume shall be written")
R.req([c], "")
b.refresh()
check("Not placed yet lists a requirement with no section", any((b.unp_list.item(i).data(Qt.UserRole) or ("", ""))[1] == c["id"]
                                                                for i in range(b.unp_list.count())))
b.select("1 Program Management")
n = b.place_unplaced([("item", c["id"])])
check("... Into the selected section", n and M.items[M.items.index(c)]["map"] == "1 Program Management")
# ---------------------------------------------------------------- Settings > Response elements
d = w.settings_page.response_elements(run=False)
e = d.add("Small business plan")
d.t.cellWidget(d.t.rowCount() - 1, 0).setText("Small business plan") if False else None
d.et.setCurrentIndex(0)
it = next(d.kit.item(i) for i in range(d.kit.count()) if d.kit.item(i).data(Qt.UserRole) == "uom")
it.setCheckState(Qt.Checked)
d.save()
data = RE.load(cfg)
check("Settings > Response elements: the team's own element and the kit kept", RE.get(data, e["id"]) is not None and "uom" in RE.kit(data))
# ---------------------------------------------------------------- the setup documents carry it
O.place_lib(M, "2 Technical Approach", {"id": qp["id"], "kind": "quickpart", "name": "Org chart block"})
O.set_break(M, "2 Technical Approach", "landscape")
out = os.path.join(tmp, "setup"); os.makedirs(out)
paths = w.setup_page.export(out)
xml = " ".join(zipfile.ZipFile(p_).read("word/document.xml").decode("utf-8") for p_ in paths)
check("the setup carries elements, Word sections and library items", "Element: TOC" in xml and "Starts a new Word section (landscape)" in xml
      and "Library: Org chart block (quickpart) goes here." in xml)
check("... and Heading 9, with deeper levels as bold run-in paragraphs", "Heading9" in xml and "Level 10" in xml)
w.go("setup"); app.processEvents()
check("Response Setup opens the Builder", w.stack.currentWidget() is b)
b.select("2 Technical Approach"); app.processEvents()
w.grab().save(os.environ.get("SK_SHOT") or os.path.join(tmp, "builder.png"))
w.close()
n = sum(checks)
print(f"QT BUILDER {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
