"""3.21.0 bins in Review, offscreen: Objective (O) and Key point (K) put the picked words in a bin, verbatim with where
they sit; sentences that are not next to each other make one excerpt; every capture keeps an excerpt (a submission rule
with its value and key); a written formatting rule is checked by phrase or on Final Checks; the effort's own bins (New
bin..., Alt+1); the margin names the bins; the card lists a sentence's excerpts to edit or take out; Every excerpt
lists them by bin; Bins of this effort shares one with the team."""
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

# ---------------------------------------------------------------- an objective, mapped to sections
a = by("The Offeror shall describe its technical approach")
pg.select(a["id"]); app.processEvents()
labels = pg.R.labels()
xo = pg.do_bin("objective", answer={"bin": "objective", "value": "", "note": "", "sections": labels[1:2]})
x = EX.get(rec(), xo)
check("Objective: the sentence's words, verbatim, with where they sit", x is not None and EX.text_of(x) == a["text"]
      and x["parts"][0]["doc"] == "Section_L_print.pdf" and x["parts"][0]["page"] and x["parts"][0]["num"] == a.get("section", ""), x)
check("... mapped to the section that answers it", x["sections"] == labels[1:2], (x["sections"], labels[:3]))
check("the margin names the bin", "OBJECTIVE" in PM.text(pg.marks.get(a["id"], []), pg.bin_names), pg.marks.get(a["id"]))

# ---------------------------------------------------------------- a key point from words dragged across
s0 = a["text"].index("technical approach")
pg.grab = {"iid": a["id"], "a": 0, "b": 0, "s": s0, "e": s0 + 18, "text": "technical approach"}
xk = pg.do_bin("keypoint", answer={"bin": "keypoint", "value": "", "note": "Lead with the test campaign"})
check("Key point: only the words dragged across, with a note", EX.text_of(EX.get(rec(), xk)) == "technical approach"
      and EX.get(rec(), xk)["note"] == "Lead with the test campaign")
pg.clear_grab()

# ---------------------------------------------------------------- sentences not next to each other: one excerpt
others = [it for it in M.items if it.get("file") == "Section_L_print.pdf" and it["id"] in pg.view.boxes and it["id"] != a["id"]]
far = others[-1]
pg.select(a["id"]); pg.view.boxes[far["id"]].setSelected(True); app.processEvents()
xm = pg.do_bin("keypoint", answer={"bin": "keypoint", "value": "", "note": ""})
xx = EX.get(rec(), xm)
check("two sentences far apart make one excerpt, each part keeping its place", xx is not None and len(xx["parts"]) == 2
      and [p["sid"] for p in xx["parts"]] == [a["id"], far["id"]] and " ... " in EX.text_of(xx), xx and [p["sid"] for p in xx["parts"]])

# ---------------------------------------------------------------- every capture keeps an excerpt
pg.select(a["id"]); app.processEvents()
keys = pg.do_capture("submit", answer=([("Due", "Proposal", "December 15, 2026 2:00 PM ET")], None))
xs = [x for x in EX.of_sentence(rec(), a["id"]) if x["bin"] == "submit"]
check("a submission capture keeps its excerpt, with the rule's value and key", keys and xs and "December 15, 2026" in xs[0]["value"]
      and EX.for_rule(rec(), keys[0]), xs)

# ---------------------------------------------------------------- formatting: written
xw = pg.do_bin("format", answer={"bin": "format", "value": "", "note": "", "check": "final"})
check("a formatting excerpt with no value is a written rule, checked on Final Checks", EX.get(rec(), xw)["sub"] == "written"
      and EX.get(rec(), xw)["check"] == "final")

# ---------------------------------------------------------------- the effort's own bins
bid = pg.new_bin({"name": "Transition risk", "color": "", "feeds": ["setup", "truth"], "about": "", "share": False})
check("New bin: the effort's own, on Alt+1 and in the Bins menu", bid and any(a_.text().startswith("Transition risk")
      and "Alt+1" in a_.text() for a_ in pg.fill_bins_menu().actions()))
xc = pg.do_bin(bid, answer={"bin": bid, "value": "", "note": "CM raised it at kickoff"})
check("words in the custom bin, named in the margin", EX.get(rec(), xc)["bin"] == bid
      and "TRANSITION RISK" in PM.text(pg.marks.get(a["id"], []), pg.bin_names))

# ---------------------------------------------------------------- the card lists and edits
pg.select(a["id"]); pg.show_card(pg.selected()); app.processEvents()
check("the card lists the sentence's excerpts", {xo, xk, xm, xw, xc} <= set(pg.excerpt_rows), list(pg.excerpt_rows))
pg.edit_excerpt(xw, {"bin": "format", "value": "12 pt Times New Roman", "note": "", "sections": [], "check": ""})
check("Edit: a value makes the formatting rule measured", EX.get(rec(), xw)["sub"] == "measured" and EX.get(rec(), xw)["value"] == "12 pt Times New Roman")
check("Take out", pg.remove_excerpt(xk) and EX.get(rec(), xk) is None)

# ---------------------------------------------------------------- every excerpt, and the bins
d = pg.all_excerpts(run=False)
check("Every excerpt lists them all, by bin", d.fill() == len(EX.excerpts(rec())) and d.filter.findData(bid) >= 0)
d.filter.setCurrentIndex(d.filter.findData("objective"))
check("... filtered to one bin", d.t.rowCount() == 1 and "OBJECTIVE" not in d.t.item(0, 0).text() and d.t.item(0, 2).text() == labels[1])
d.t.setCurrentCell(0, 0)
check("Show in Review selects its sentence", d.show_it() and pg.selected() and pg.selected()[0]["id"] == a["id"])
bd = pg.manage_bins(run=False)
n_bins = bd.fill(); bd.list.setCurrentRow(0)
check("Bins of this effort: share one with the team", n_bins == 1 and bd.share() and [b["name"] for b in EX.team_bins(cfg)] == ["Transition risk"])

# ---------------------------------------------------------------- Submission Rules show the words
pg.select(a["id"]); app.processEvents()
xo2 = pg.do_bin("other", answer={"bin": "other", "value": "", "note": "Ask the CO whether a cover letter counts"})
w.go("requirements"); app.processEvents()
rp = w.requirements_page
rp.refresh(); app.processEvents()
from PySide6.QtWidgets import QLabel as _QL
rp.select(keys[0]); app.processEvents()
texts = [l.text() for l in rp.card.findChildren(_QL)]
check("Submission Rules: a rule shows the customer's words, verbatim, and where they sit", any(a["text"] in t for t in texts)
      and any("Section_L_print.pdf" in t and "p.1" in t for t in texts))
check("Other submission detail lists the excerpts that need no rule", "x:" + xo2 in rp.excerpts and rp.select("x:" + xo2))
rp.edit_excerpt(xo2, {"bin": "other", "value": "Cover letter: 1 page", "note": ""})
check("... with a value added later", EX.get(rec(), xo2)["value"] == "Cover letter: 1 page")

print(f"QT BINS {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
w.close()
sys.stdout.flush(); os._exit(0 if all(checks) else 1)
