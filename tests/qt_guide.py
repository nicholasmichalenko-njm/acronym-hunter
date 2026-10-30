"""3.0.2 the Guide, offscreen: every page in the menu has a topic; F1 opens the Guide at the page you are on; search
narrows the topics; Go to this page goes there; Previous and Next walk the topics; Help and support opens it at the
start; a topic reads well with or without its picture; the words follow the house style (no em dashes)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme, guide as GD
from skqt.mainwin import MainWindow, RAIL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Osprey"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Osprey_Effort_List.xlsx")
L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1400, 900); w.show()
w.open_effort("Osprey")

keys = [k for _g, items in RAIL for k, _l in items]
missing = [k for k in keys if k not in GD.TOPIC]
check("every page in the menu has a Guide topic", not missing, missing)
check("... in the menu's order", [t[0] for t in GD.TOPICS if t[0] in keys] == keys)
words = " ".join(" ".join([t[2], t[3], t[4], *t[5], *t[6]]) for t in GD.TOPICS)
check("the words follow the house style: no em dashes", "—" not in words and "--" not in words)
check("each topic says what the page is for and when to use it", all(t[3] and t[4] for t in GD.TOPICS))

w.go("custqa")
g = GD.open_guide(w)
app.processEvents()
check("F1 opens the Guide at the page you are on", g.key == "custqa" and "Customer Q&A" in g.view.toPlainText())
check("... with the steps", "Capture > Question" in g.view.toPlainText())
g.search.setText("amendment instructions")
app.processEvents()
shown = g.shown()
check("search narrows the topics", "library" in shown and len(shown) < len(GD.TOPICS), shown)
g.search.setText("")
g.show_topic("prove")
g._go(); app.processEvents()
check("Go to this page goes there", w.stack.currentWidget() is w.pages["prove"])
g._step(1)
check("Next walks to the next topic", g.key == "crosswalk")
g._step(-1); g._step(-1)
check("... and Previous back", g.key == "assign")
g.show_topic("start")
check("the start topic has no page to go to", not g.go_btn.isVisibleTo(g) and g.prev.isEnabled() is False)
g.show_topic("keys")
check("the shortcuts are a topic, F1 among them", "The Guide, open at the page you are on" in g.view.toPlainText())
check("a topic with no picture still reads: no broken image", ("<img" not in GD.topic_html("safe")) or bool(GD.shot_path("safe")))
from skqt import helpcenter as HC
card = HC.support_card(w)
btns = [b.text() for b in card.findChildren(type(HC.D.button("x", None, None)))]
check("Help and support has a Guide button", "Guide" in btns, btns)
w.close_effort()
n = sum(checks)
print(f"QT GUIDE {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
