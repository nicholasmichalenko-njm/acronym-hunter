"""4.32.0, Standards step 3, offscreen: an effort's own set of standards on screen. A standards page says which set a
change goes to; a change with the effort open stays in the effort; Effort Formatting carries the Effort Standards card;
4.36.0: the card lists each difference from the Global Standards in color, with This effort or Global chosen on the row. Fictional."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_THEME"] = "light"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effortset as ES, globalstd as GS, prodrules as PRL, templatelib as TL
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D, effortsetview as EV
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def font():
    return PRL.load(cfg)["company"]["variables"]["body_font"]


def set_font(name):
    d = PRL.load(cfg); d["company"]["variables"]["body_font"] = name; PRL.save(cfg, d)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
set_font("Global One")
w.go("prodstd"); app.processEvents()
check("no effort open: a standards page says a change is a Global change", w.page_sub.text().startswith("Global Standards. A change here is saved for everyone."), w.page_sub.text())
lib_page = TL.Library(cfg)                                      # a library held from before the effort opened, as the pages hold one
w.go("home"); app.processEvents()
f = w.home_page.start; f.name.setText("Osprey"); f.saved.choose(tmp); f.create(); app.processEvents()
root = w.ws.root
check("a new effort has its own set as it opens", ES.has(root) and ES.active() == ES.set_dir(root))
w.go("prodstd"); app.processEvents()
check("effort open: the page says the change is this effort's own", w.page_sub.text().startswith("Effort Standards: Osprey. A change here is this effort's own."), w.page_sub.text())
w.go("home"); app.processEvents()
check("a page that is not a standards page keeps its line and the effort's name", w.page_sub.text().endswith("Osprey") and "Effort Standards" not in w.page_sub.text(), w.page_sub.text())
check("a library held from before reads the effort's set now", lib_page.root == os.path.join(ES.set_dir(root), TL.FOLDER), lib_page.root)
set_font("Osprey Font")
with ES.as_global():
    check("a change with the effort open leaves the Global Standards as they were", font() == "Global One")
w.go("effortfmt"); app.processEvents()
ep = w.effortfmt_page
check("Effort Formatting carries the Effort Standards card with where the set came from and what the effort changed",
      not ep.es_card.isHidden() and "its own set" in ep.es_line.text() and "changed 1 file" in ep.es_line.text(), ep.es_line.text())
# 4.36.0 (ST8, ST20): the differences on the card, in color, with the value in use chosen on the row
from PySide6.QtWidgets import QPushButton
cell = lambda r, c: ep.es_table.item(r, c).text()
whats = lambda: [cell(r, 1) for r in range(ep.es_table.rowCount())]
check("the effort's own change is a row: what, this effort's value, the Global value", "company > variables > body font" in whats()
      and [cell(whats().index("company > variables > body font"), c) for c in (2, 3, 4)] == ["Differs", "Osprey Font", "Global One"], whats())
check("the card says how many things differ", "1 thing differs from the Global Standards." in ep.es_count.text(), ep.es_count.text())
check("there is no See the changes, Take or Send (ST7, ST20)", not hasattr(EV, "review") and not hasattr(EV, "give") and not hasattr(ep, "es_offer")
      and not [b for b in ep.es_card.findChildren(QPushButton) if b.text() in ("See the changes...", "Use every Global value...")])
check("the card's words: no publish, no draft, no Company Standards",
      not any(x in (ep.es_line.text() + ep.es_card.title.text() + ep.es_count.text()).lower() for x in ("publish", "draft", "company standards")))
with ES.as_global():
    d = PRL.load(cfg); d["company"]["variables"]["table_font"] = "Global Table"; PRL.save(cfg, d)
ep.refresh(); app.processEvents()
r_font, r_tab = whats().index("company > variables > body font"), whats().index("company > variables > table font")
check("a Global change since is a row too, and nothing is taken", cell(r_tab, 4) == "Global Table" and PRL.load(cfg)["company"]["variables"]["table_font"] != "Global Table"
      and "2 things differ" in ep.es_count.text(), ep.es_count.text())
sw = lambda r: (ep.es_table.cellWidget(r, 5).findChild(QPushButton, "useMine"), ep.es_table.cellWidget(r, 5).findChild(QPushButton, "useGlobal"))
mine, glob = sw(r_font)
check("each row has the two choices, This effort pressed", mine.text() == "This effort" and glob.text() == "Global Standards" and mine.isChecked() and not glob.isChecked())
check("a row is colored by what it is", ep.es_table.item(r_font, 1).background().color().name().lower() == D.tokens()["warn_soft"].lower())
glob.click(); app.processEvents()
r_font = whats().index("company > variables > body font")
mine, glob = sw(r_font)
check("Global on the row: the effort uses the Global value, the row stays with Global pressed and its own value still shown", font() == "Global One"
      and glob.isChecked() and not mine.isChecked() and cell(r_font, 3) == "Osprey Font" and "1 uses the Global Standards' value by your choice" in ep.es_count.text(), ep.es_count.text())
with ES.as_global():
    check("the Global Standards are untouched by the choice", font() == "Global One" and PRL.load(cfg)["company"]["variables"]["table_font"] == "Global Table")
mine.click(); app.processEvents()
check("This effort on the row: its own value is back, in one click", font() == "Osprey Font" and sw(whats().index("company > variables > body font"))[0].isChecked())
r_tab = whats().index("company > variables > table font")
sw(r_tab)[1].click(); app.processEvents()
check("a Global value is taken the same way, on its row", PRL.load(cfg)["company"]["variables"]["table_font"] == "Global Table")
with ES.as_global():
    set_font("Global Two")
ep.refresh(); app.processEvents()
sw(whats().index("company > variables > body font"))[1].click(); app.processEvents()
w.close_effort(); app.processEvents()
check("closed: the Global Standards are in use again", ES.active() == "" and font() == "Global Two")
w.go("effortfmt"); app.processEvents()
check("with no effort open the page shows its one way in", not ep.empty.isHidden())
w.close()
print(f"QT EFFORTSET 4320 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
