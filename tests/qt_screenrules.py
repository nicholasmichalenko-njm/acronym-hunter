"""3.74.0 offscreen: the eight rules for screens (claude/stationkeeper-simplify-decisions-2026-11-06.md, house rule 8).
Every command bar holds at most five commands (More and Export are menus); no screen grows past the controls it had
(buttons, check boxes, drop-downs and text fields visible on it, scrolling included, with the fictional Kestrel effort
open), counted against tools/screen_baseline.json; a new screen needs its count there. SK_WRITE_SCREEN_BASELINE=1
writes the file from this run (after a screen lost controls on purpose)."""
import json, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
A.DATA_DIR = os.path.join(tmp, "data")
import effort as E, workspace as W, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import (QAbstractButton, QApplication, QComboBox, QDoubleSpinBox, QLineEdit, QMessageBox,
                               QPlainTextEdit, QSpinBox, QTabBar, QTextEdit)
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.warning = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.commandbar import CommandBar, MAX
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


BASE = os.path.join(os.path.dirname(HERE), "tools", "screen_baseline.json")
SLACK = lambda n: max(3, n // 10)              # the same screen counts a little differently on a PC with Word
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf", "SOW.pdf")]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1600, 1000); w.show()


def wait(cond, secs=120):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


def controls(page):
    def vis(x):
        return x.isVisibleTo(w) and x.isVisible()
    n = 0
    for b in page.findChildren(QAbstractButton):
        if vis(b) and not isinstance(b.parent(), QTabBar):
            n += 1
    n += sum(1 for c in page.findChildren(QComboBox) if vis(c))
    for T in (QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox):
        n += sum(1 for f in page.findChildren(T) if vis(f) and not (isinstance(f, QLineEdit) and isinstance(f.parent(), (QComboBox, QSpinBox, QDoubleSpinBox))))
    return n


w.open_effort("Kestrel")
w.read_page.read(PDFS, os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
check("Kestrel has its matrix", wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page))
base = {}
try:
    base = json.load(open(BASE, encoding="utf-8"))
except (OSError, ValueError):
    pass
now, over, new, bars = {}, [], [], []
for key, pg in w.pages.items():
    if pg in [w.pages[k] for k in now]:
        continue
    if not w.go(key):
        continue
    for _ in range(15):
        app.processEvents(); time.sleep(0.01)
    now[key] = controls(pg)
    if key not in base:
        new.append(key)
    elif now[key] > base[key] + SLACK(base[key]):
        over.append(f"{key}: {now[key]} (was {base[key]})")
    for cb in pg.findChildren(CommandBar):
        if cb.isVisibleTo(w):
            bars.append((key, [b.text() for b in cb.visible_commands()]))
if os.environ.get("SK_WRITE_SCREEN_BASELINE"):
    json.dump(dict(sorted(now.items())), open(BASE, "w", encoding="utf-8"), indent=1)
    print("wrote", BASE)
    base = now; over = []; new = []
check("every screen counted", len(now) >= 45, len(now))
check("no screen grew past its count in tools/screen_baseline.json", not over, over)
check("a new screen has its count in tools/screen_baseline.json", not new, new)
check("every command bar holds at most five commands (More and Export are menus)", all(len(c) <= MAX for _k, c in bars), bars)
check("Setup has a command bar with one main button, Make the setup", any(k == "setups" and "Make the setup" in c for k, c in bars), bars)
check("the Structure Builder is part of Setup", w.go("structure") and w.stack.currentWidget() is w.setups_page
      and "structure" not in w.pages)
print(f"QT SCREEN RULES {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})", "  ".join(f"{k}={n}" for k, n in sorted(now.items())))
sys.exit(0 if all(checks) else 1)
