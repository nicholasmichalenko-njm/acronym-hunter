"""2.99.0 more of the review in Assign, offscreen: More captures files an evaluation factor (and a subfactor under it) with
its importance, a page limit (the effort becomes page-limited; the rule shows in Submission rules), a deliverable onto
the board, an effort detail into Effort details, and a hot button; Effort Home shows Evaluation and hot buttons; a task
and a team question on a sentence show on its card and in the effort record; the readable copy has them; the Compliance
pages sit near the top of the menu."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W, effortrec as RR, office_pdf as OP, pdfmini, custfocus as F, branding as BR, readable as RD
import deliverables as DL, docversions as DV, subreq as SR
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme
from skqt.mainwin import MainWindow, RAIL
from skqt import captureview as CV

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Osprey"); os.makedirs(EDIR)
LINES = ["M.2 EVALUATION FACTORS",
         "Factor 1: Technical Approach. Technical is significantly more important than Past Performance.",
         "Subfactor 1.1 Systems Engineering will be evaluated for soundness and realism.",
         "The Government places strong emphasis on schedule realism and launch readiness.",
         "Volume II Technical shall not exceed 20 pages.",
         "The contractor shall deliver the Integrated Master Schedule (CDRL A003) monthly.",
         "The NAICS code for this acquisition is 336414 with a size standard of 1,250 employees."]
PDF = os.path.join(tmp, "Section_M.pdf"); pdfmini.write(PDF, [LINES], size=9)
LIST = os.path.join(EDIR, "Osprey_Effort_List.xlsx")
L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Osprey").set("outline_text", "Volume I Executive Summary\n1.1 Overview\nVolume II Technical\n2.1 Technical Approach")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


check("the Compliance pages come right after Effort in the menu", [g for g, _i in RAIL][:3] == ["Home", "Effort", "Compliance"])
w.open_effort("Osprey")
w.read_page.read([PDF], os.path.join(EDIR, "Osprey_Compliance_Matrix.xlsx"))
check("read", wait(lambda: w.review is not None))
M = w.review.M
pg = w.assign_page
w.go("assign"); app.processEvents()
by = lambda s: next(it for it in M.items if s in it["text"])
check("More captures: five, in a menu", list(pg.more_actions) == ["factor", "pagelimit", "deliverable", "detail", "hot"])
rec = lambda: RR.Record(w.ws.root)
# evaluation factor, then a subfactor under it
pg.select(by("Factor 1")["id"]); app.processEvents()
d = CV.factor_dialog(pg, pg.capture_source()[0], pg._factors())
v = d.values(); d.deleteLater()
check("Factor: the name is read, offered as a factor of its own", v["name"] == "Technical Approach" and v["under"] == "(a factor of its own)", v)
both = CV.factor_dialog(pg, by("Factor 1")["text"] + " Technical is significantly more important than Past Performance.", [])
check("... and its importance, when the words say it", both.values()["importance"] == "Significantly more important"); both.deleteLater()
pg.do_capture("factor", answer=dict(v, importance="Significantly more important"))
pg.select(by("Subfactor 1.1")["id"]); app.processEvents()
d = CV.factor_dialog(pg, pg.capture_source()[0], pg._factors())
v = d.values(); d.deleteLater()
check("Subfactor: offered under the factor filed", v["name"] == "Systems Engineering" and v["under"] == "Technical Approach", v)
pg.do_capture("factor", answer=v)
fs = F.factors(rec())
check("... filed in order, the subfactor under its factor, with the document", [f["name"] for f in fs] == ["Technical Approach", "Systems Engineering"]
      and fs[1]["parent"] == fs[0]["id"] and fs[0]["doc"] == "Section_M.pdf")
# page limit
pg.select(by("shall not exceed 20 pages")["id"]); app.processEvents()
d = CV.page_limit_dialog(pg, pg.capture_source()[0], pg._limit_targets())
v = d.values(); d.deleteLater()
check("Page limit: the volume and the limit are read", v["target"] == "Volume II Technical" and v["limit"] == "20 pages", v)
pg.do_capture("pagelimit", answer=v)
rows = SR.Register(DV.Library(w.ws.p("documents")).load()).rows()
check("... a submission rule, and the effort is page-limited", any(r.get("kind") == "Page limit" and "20 pages" in r.get("value", "") for r in rows)
      and rec().data.get("page_limited") == "yes", [(r.get("kind"), r.get("value")) for r in rows][:5])
# deliverable
pg.select(by("CDRL A003")["id"]); app.processEvents()
d = CV.deliverable_dialog(pg, pg.capture_source()[0])
v = d.values(); d.deleteLater()
check("Deliverable: the name is read", v["name"].startswith("CDRL A003") or "Schedule" in v["name"], v)
pg.do_capture("deliverable", answer=dict(v, name="CDRL A003 Integrated Master Schedule"))
check("... on the deliverables board, with the customer's words", any(x["name"] == "CDRL A003 Integrated Master Schedule" and "Section_M.pdf" in x.get("notes", "")
                                                                     for x in DL.items(rec())))
# effort detail
pg.select(by("NAICS")["id"]); app.processEvents()
d = CV.detail_dialog(pg, pg.capture_source()[0])
v = d.values(); d.deleteLater()
check("Effort detail: NAICS 336414", v == {"label": "NAICS", "value": "336414"}, v)
pg.do_capture("detail", answer=v)
check("... in Effort details with where it came from", any(f["label"] == "NAICS" and f["value"].startswith("336414 (Section_M.pdf")
                                                          for f in BR.identity(rec())["fields"]))
# hot button
pg.select(by("strong emphasis")["id"]); app.processEvents()
d = CV.hot_dialog(pg, pg.capture_source()[0])
v = d.values(); d.deleteLater()
pg.do_capture("hot", answer=v)
check("Hot button: what the customer stresses, quoting them", F.hot_buttons(rec())[0]["text"] == "schedule realism and launch readiness"
      and F.hot_buttons(rec())[0]["quote"].startswith("The Government places"))
# a task and a team question on a sentence
it = by("Subfactor 1.1")
pg.select(it["id"]); app.processEvents()
tid = pg.add_work("task", it["id"], answer={"text": "Draft the SE approach", "owner": "J. Garcia", "due": "2026-11-30"})
nid = pg.add_work("question", it["id"], answer={"text": "Do we show the MBSE tool chain here?", "owner": "M. Chen"})
labels = " | ".join(l.text() for l in pg.work_labels)
check("a task and a team question show on the sentence's card", tid and nid and "TASK  Draft the SE approach" in labels
      and "QUESTION  Do we show the MBSE tool chain here?" in labels and "for M. Chen" in labels, labels)
r = rec()
check("... and are in the effort record", r.task(tid)["owner"] == "J. Garcia" and any(n["id"] == nid and n["question"] for n in r.data["notes"]))
# Effort Home and the readable copy
w.go("home"); app.processEvents()
hp = w.home_page
check("Effort Home: Evaluation and hot buttons", "custfocus" in hp.shown and hp.focus_now["factors"] == ["Technical Approach", "Systems Engineering"]
      and hp.focus_now["hot"] == ["schedule realism and launch readiness"])
files = RD.more(rec(), None, w.ws.root, {})
check("the readable copy has the factors and hot buttons", files["Evaluation factors.csv"][1][1][:3] == ["Systems Engineering", "Technical Approach", "Not stated"]
      and files["Hot buttons.csv"][1][0][0] == "schedule realism and launch readiness")
if os.environ.get("SHOT_DIR"):
    w.go("assign"); pg.select(it["id"]); app.processEvents()
    w.grab().save(os.path.join(os.environ["SHOT_DIR"], "more_captures.png"))
w.close_effort()
n = sum(checks)
print(f"QT MORE {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
