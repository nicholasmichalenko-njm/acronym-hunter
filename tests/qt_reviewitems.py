"""3.29.0 Settings > Review: decisions and captures, offscreen: every decision and capture renamed, re-keyed,
recolored, hidden, moved between the bar and More, in the team's order; Review follows at once (buttons, keys, legend,
page colors); keys used twice are named; an RFI effort shows Interest and hides L, M and SOW, with Show every decision;
the team's own captures sit on the bar beside the built-in ones; the Captured list is its own button; back to the
built-in values."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import compliance as C, effort as E, setupdoc as SD, workspace as W, office_pdf as OP
OP.available = lambda: False
from PySide6.QtCore import Qt, QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
reg = E.Registry(os.path.join(cfg, "efforts.json")); reg.put("Kestrel", path=LIST)
ws0 = W.Workspace(W.data_dir_for(LIST), "Kestrel")
ws0.set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk\nVolume II Management\n2.1 Program Management")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf", "SOW.pdf")]

app = QApplication([])
theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION)
w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


check("the effort opens and is held", w.open_effort("Kestrel") and W.read_json(ws0.p("lock.json"), {}).get("pid") == os.getpid())
check("no matrix yet: Read RFP is the step", w.stack.currentWidget() is w.read_page)
out = os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx")
w.read_page.read(PDFS, out)
check("Read runs in the background and starts the matrix", wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page))
M = w.review.M
pg = w.assign_page
pg.files.setCurrentText("Section_L_print.pdf"); app.processEvents()
by = lambda s: next(it for it in M.items if it["text"].startswith(s))
import effortrec as RR, excerpts as EX, pagemarks as PM
from PySide6.QtGui import QShortcut
rec = lambda: RR.Record(w.ws.root)

check("3.29.0: Objective and Key point sit on the capture bar, More... beside them, with their keys", all(k in pg.cap_keys for k in ("objective", "keypoint", "more"))
      and {"O", "K", "B", "Alt+1", "Alt+9"} <= {s.key().toString() for s in pg.findChildren(QShortcut)})

import reviewitems as RI
from skqt import design as D
keys_now = lambda: {s.key().toString() for s in pg.findChildren(QShortcut) if s.isEnabled()}
check("one capture bar: the built-in ones, then More...; no Bins button", "contact" in pg.cap_keys and "more" in pg.cap_keys
      and "bins" not in pg.cap_keys and pg.more_btn.text() == "More...")
check("the Captured list is a button of its own", "Captured list" in pg.captured_btn.text() and pg.captured_btn.isVisibleTo(w))
dl = pg.all_excerpts(run=False)
check("... it opens everything captured", dl.windowTitle().startswith("Captured list"))
dl.reject()
sp = w.settings_page
check("Settings has Review: decisions and captures", sp.ri_card.title.text() == "Review: decisions and captures")
d = sp.review_items(run=False)
codes = [c for c, *_r in RI.DECISIONS]
row = lambda code: codes.index(code)
d.dt.cellWidget(row("L"), 0).setText("Section L"); d.dt.cellWidget(row("M"), 2).setText("Y")
d.dt.cellWidget(row("L"), 3).setText("#123456"); d.dt.cellWidget(row("ignore"), 4).setChecked(False)
crow = lambda key: d.data["order"].index(key)
d.ct.cellWidget(crow("contact"), 0).setText("POC")
d.ct.cellWidget(crow("keypoint"), 4).setCurrentIndex(1)
d.ct.cellWidget(crow("acronym"), 3).setChecked(False)
d.read()
check("no key used twice yet", d.show_clash() == [])
d.ct.cellWidget(crow("contact"), 1).setText("L"); d.read()
check("a key used twice is named", any(k == "L" for k, _n in d.show_clash()), d.show_clash())
d.ct.cellWidget(crow("contact"), 1).setText(""); d.read()
d.save()
check("Review follows: the renamed decision", pg.keys["L"].text().startswith("Section L"))
check("... its new key, and the old one gone", "Y" in keys_now() and "E" not in keys_now())
check("... a hidden decision is not offered", "Ignore" not in pg.keys and "X" not in keys_now())
check("... the page color and the legend", D.PAGE_LM["L"] == "#123456" and "Section L" in pg.legend.text())
check("... a renamed capture", pg.cap_keys["contact"].text().startswith("POC"))
check("... one moved to More", "keypoint" not in pg.cap_keys and "keypoint" in pg.more_actions and "K" in keys_now())
check("... and one hidden", "acronym" not in pg.cap_keys and "acronym" not in pg.more_actions)
check("kept on this PC, only what differs", os.path.isfile(os.path.join(cfg, RI.FILE)) and set(RI.load(cfg)["decisions"]["L"].items()) >= {("name", "Section L")})
# the team's own capture
d2 = sp.review_items(run=False)
d2.add_team("Transition risk")
d2.save()
check("the team's own capture sits on the bar", any(b.text().startswith("Transition risk") for b in pg.cap_keys.values()))
# an RFI effort
eff = dict(w.ws.get("prod_std", {}) or {}); eff["effort_type"] = "rfi"; w.ws.set("prod_std", eff)
pg.apply_items(); app.processEvents()
check("an RFI effort: Interest shows, L, M and SOW are hidden", "Interest" in pg.keys and "L" not in pg.keys and "M" not in pg.keys
      and "Requirement" not in pg.keys and "I" in keys_now())
check("... Show every decision says how many are hidden", pg.dec_all.isVisibleTo(w) and "hidden" in pg.dec_all.text())
pg.dec_all.setChecked(True); app.processEvents()
check("... and shows them all when ticked", "L" in pg.keys and "Interest" in pg.keys)
pg.dec_all.setChecked(False)
eff["effort_type"] = ""; w.ws.set("prod_std", eff)
d3 = sp.review_items(run=False)
d3.reset()
check("Back to the built-in values", pg.keys["L"].text().startswith("L (Instructions)") and "Ignore" in pg.keys and "E" in keys_now()
      and "acronym" in pg.cap_keys and not os.path.isfile(os.path.join(cfg, RI.FILE)))
# the card: what was decided and captured, first, and only about the sentence
pg.dec_all.setChecked(False); pg.apply_items()
x = M.items[5]
pg.select(x["id"]); pg.do_lm("L"); app.processEvents()
pg.select(x["id"]); pg.do_bin("keypoint", answer={"bin": "keypoint", "value": "", "note": "theme", "sections": []}); app.processEvents()
pg.select(x["id"]); app.processEvents()
txt = " ".join(pg.decided_lines)
check("the card says the decision first, as the team names it", pg.kind_label.text().startswith("L (Instructions) requirement")
      and "Decision:</b> L (Instructions) requirement" in txt, txt)
check("... and what was captured from it", "Captured:</b> " in txt and "Key point" in txt, txt)
labels = " ".join(l.text() for l in pg.card.findChildren(QLabel) if l.isVisibleTo(pg.card))
check("... and nothing that is not about the sentence (no general help)", "To split it" not in labels and "None yet" not in labels
      and "keys L, E, R" not in labels and "no initial and type yet" not in labels)
y = M.items[6]
pg.select(y["id"]); app.processEvents()
check("an undecided sentence says so", "Not decided yet" in " ".join(pg.decided_lines))
# 3.30.0: a capture made twice in a row (More... was deleted after the first one rebuilt the bar)
import shiboken6
from PySide6.QtCore import QCoreApplication, QEvent
sel = pg.selected()
x1 = pg.do_bin("keypoint", answer={"bin": "keypoint", "value": "", "note": "one", "sections": []})
app.processEvents(); QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete); app.processEvents()
ok_more = shiboken6.isValid(pg.more_btn)
err = None
try:
    x2 = pg.do_bin("keypoint", answer={"bin": "keypoint", "value": "", "note": "two", "sections": []})
    app.processEvents(); QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete); app.processEvents()
    x3 = pg.do_bin("keypoint", answer={"bin": "keypoint", "value": "", "note": "three", "sections": []})
except RuntimeError as e:
    err = str(e)
check("3.30.0: captures made one after another: More... stays, no problem window", ok_more and err is None
      and shiboken6.isValid(pg.more_btn) and pg.cap_keys.get("more") is pg.more_btn, err)
w.close()
n = sum(checks)
print(f"QT REVIEW ITEMS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
