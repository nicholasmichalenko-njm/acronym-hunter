"""3.74.0 offscreen: Setup is one page (decision 12) and follows the eight rules. One command bar (Make the setup, Bring in
a file..., Use a template file..., Add elements..., + Volume; More; Export); with no sections only the card to bring
them in; the sections are the Structure Builder's tree with Lead and Due; the selected section's lead, contributors,
due date, pages and PM direction in its panel; the right-click menu does what the style buttons did; the Structure
Builder's menu item and its links open Setup. Fictional content (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import compliance as C, effort as E, setupmake as SM
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt import mainwin as MW
from skqt.commandbar import MAX
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
check("the menu: Setup in Plan, no Structure Builder of its own", [k for k, _t in MW.TABS["setups"]] == ["setups", "effortfmt"] and MW.RAIL_OF["storyboards"] == "setups")
w.go("structure"); app.processEvents()
sp = w.setups_page
check("the Structure Builder's links open Setup", w.stack.currentWidget() is sp and w.page_title.text() == "Setup")
bar = sp.bar
check("one command bar: Make the setup is the one main button, four more commands",
      [b.text() for b in bar.commands] == ["Bring in a file...", "Use a template file...", "Add elements...", "+ Volume", "Make the setup"]
      and bar.main.text() == "Make the setup" and len(bar.commands) <= MAX, [b.text() for b in bar.commands])
check("More holds the rest, Export every file", all(bar.action(t) for t in ("Edit as text / Start from", "Sort in document order",
      "Show what is placed", "What fills each section...", "Setup styles...", "Outline versions...", "Outline layouts..."))
      and all(bar.action(t) for t in ("Plain setup...", "Changes for authors...", "Kickoff packets...", "Strip setup...")))
check("no sections: one card to bring them in, the sections area hidden, Make the setup off",
      sp.start_card.isVisibleTo(w) and not sp.builder.isVisibleTo(w) and not sp.b_make.isEnabled())
M = sp.use_headings("Volume I Technical\n  1 Ground Segment\n    1.1 Antenna Sites\n  2 Mission Operations")
app.processEvents()
b = sp.builder
node = lambda lab: next(iter(b.btree.findItems(lab, Qt.MatchExactly | Qt.MatchRecursive, 0)), None)
check("sections: the builder's tree in Setup, with Lead and Due columns", sp.builder.isVisibleTo(w) and not sp.start_card.isVisibleTo(w)
      and node("1.1 Antenna Sites") is not None and b.btree.headerItem().text(5) == "Lead" and b.btree.headerItem().text(6) == "Due")
check("the style buttons and the old toolbar are gone from view", not b.style_bar.isVisibleTo(w) and not any(x.isVisibleTo(w) for x in b.top_btns))
b.btree.setCurrentItem(node("1.1 Antenna Sites")); app.processEvents()
check("the selected section's panel holds lead, contributors, due, pages and PM direction", sp.cur == "1.1 Antenna Sites"
      and sp.who.isVisibleTo(w) and sp.f_lead.isVisibleTo(w) and sp.f_dir.isVisibleTo(w))
sp.f_lead.setText("R. Diaz"); sp.f_due.setText("2026-12-04"); sp.f_pages.setText("3"); sp.f_dir.setPlainText("Lead with the second site.")
check("Save this section", sp.save_section())
app.processEvents()
check("... the tree shows the lead and due date", node("1.1 Antenna Sites").text(5) == "R. Diaz" and node("1.1 Antenna Sites").text(6) == "2026-12-04",
      [node("1.1 Antenna Sites").text(i) for i in range(7)])
check("... and the panel stays after the tree is drawn again", sp.who.isVisibleTo(w) and sp.f_lead.text() == "R. Diaz")
m = b.menu("1.1 Antenna Sites")
names = [a.text() for a in m.actions()]
check("right-click: rename, make it, Word section, add, move, delete", all(any(t in n for n in names) for t in
      ("Rename", "Make it", "Word section", "+ Below", "+ Under", "Level down", "Level up", "Delete")), names)
bar.action("Show what is placed").trigger(); app.processEvents()
check("More > Show what is placed follows the builder", b.show_items.isChecked() == bar.action("Show what is placed").isChecked())
check("What it prints in the panel", "R. Diaz" in sp.prev.text() and "second site" in sp.prev.text(), sp.prev.text())
bar.action("What fills each section...").trigger(); app.processEvents()
check("More > What fills each section... opens the layers", sp.layers.isVisibleTo(w) and "What fills each section" in sp.fills.text())
sp.layer_boxes["pm"].setChecked(False)
check("... a layer off leaves the line and what it prints", "Management guidance" not in sp.fills.text().split(":", 1)[1]
      and "Management guidance" not in sp.prev.text(), sp.fills.text())
sp.layer_boxes["pm"].setChecked(True)
n0 = len(M.outline)
b.add_volume("Management"); app.processEvents()
check("+ Volume (from the bar) adds a volume", len(M.outline) == n0 + 1 and any(C.outline_label(o) == "Volume II Management" for o in M.outline))
paths = sp.plain(os.path.join(tmp, "plain"))
check("Export > Plain setup writes one file per volume", paths and all(os.path.isfile(p) for p in paths), paths)
check("the frame: one Sections area at a time and the count says the sections", sp.p_secs.text().startswith(str(len(SM.sections(M)))))
b.show_text(True); app.processEvents()
check("Edit as text: the text, and the way back", b.text_panel.isVisibleTo(w) and b.text_btn.isVisibleTo(w) and b.text_btn.text() == "Back to the sections")
b.show_text(False); app.processEvents()
check("... back to the sections", not b.text_panel.isVisibleTo(w) and not b.text_btn.isVisibleTo(w) and b.split.isVisibleTo(w))
import roleaccess as RA
check("every role that had the Structure Builder has Setup", all("setups" in tools for tools in RA.TOOLS.values() if "structure" in tools))

print(f"QT SETUP 374 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
