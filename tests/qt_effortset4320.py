"""4.32.0, Standards step 3, offscreen: an effort's own set of standards on screen. A standards page says which set a
change goes to; a change with the effort open stays in the effort; Effort Formatting carries the Effort Standards card;
Review... shows what the Global Standards would change and what the effort changed, each acted on by name. Fictional."""
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
check("no effort open: a standards page says a change is a Global change", w.page_sub.text().startswith("Global Standards. A change here waits"), w.page_sub.text())
lib_page = TL.Library(cfg)                                      # a library held from before the effort opened, as the pages hold one
w.go("home"); app.processEvents()
f = w.home_page.start; f.name.setText("Osprey"); f.create(); app.processEvents()
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
check("nothing offered yet", ep.es_offer.isHidden())
check("the card's words: no publish, no draft, no Company Standards",
      not any(x in (ep.es_line.text() + ep.es_card.title.text()).lower() for x in ("publish", "draft", "company standards")))
with ES.as_global():
    d = PRL.load(cfg); d["company"]["variables"]["table_font"] = "Global Table"; PRL.save(cfg, d)
ep.refresh(); app.processEvents()
check("a Global change is offered on the card, and nothing is taken", not ep.es_offer.isHidden() and "have changed since this effort took its set" in ep.es_offer.text()
      and PRL.load(cfg)["company"]["variables"]["table_font"] != "Global Table", ep.es_offer.text())
dlg = EV.review(ep, run=False)
rows = [(dlg.t_offer.item(r, 1).text(), dlg.t_offer.item(r, 3).text()) for r in range(dlg.t_offer.rowCount())]
check("Review... lists each value the Global Standards would change", ("company.variables.table_font", "Global Table") in rows
      and ("company.variables.body_font", "Global One") in rows, rows)
check("... and what this effort changed", dlg.t_mine.rowCount() == 1 and dlg.t_mine.item(0, 1).text() == "production_standards.json")
check("the two actions are named for what they do", dlg.b_take.text() == "Take for this effort" and dlg.b_give.text() == "Send to the Global Standards")
dlg.b_give.click(); app.processEvents()
with ES.as_global():
    check("Send to the Global Standards: the effort's file waits in the Global Standards on this PC", font() == "Osprey Font")
check("then the effort has changed nothing and nothing is offered", dlg.t_mine.rowCount() == 0 and dlg.t_offer.rowCount() == 0 and not dlg.b_take.isEnabled()
      and not dlg.b_give.isEnabled())
with ES.as_global():
    set_font("Global Two")
dlg.fill()
check("a later Global change is offered again", dlg.t_offer.rowCount() == 1 and font() == "Osprey Font")
dlg.b_take.click(); app.processEvents()
check("Take for this effort takes it", font() == "Global Two" and dlg.t_offer.rowCount() == 0 and ep.es_offer.isHidden())
w.close_effort(); app.processEvents()
check("closed: the Global Standards are in use again", ES.active() == "" and font() == "Global Two")
w.go("effortfmt"); app.processEvents()
check("with no effort open the page shows its one way in", not ep.empty.isHidden())
w.close()
print(f"QT EFFORTSET 4320 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
