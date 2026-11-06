"""3.65.0 Sort II, offscreen: suggestions from each topic's words (keywords count most; each shows why; never filed until
taken); Sort > Structure: our fit per topic, the response made from the topics (an RFI: a Response volume, a section
per topic, subtopics under them), Map to it, Make subsections under it, Place their requirements (kept ones go to their
home topic's first section), and what the structure still misses. Fictional content."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import compliance as C, effort as E, effortrec as RR, workspace as W, topics as TP, outline_ops as O, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
M = C.Matrix(os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"), "Kestrel")
M.items = C.extract([("Kestrel_RFI.docx", [("Page 1", "Respondents should describe how they retain security logs in a SIEM. "
                      "Respondents should describe their approach to transition from the incumbent. "
                      "Respondents should describe network operations staffing. "
                      "Respondents should describe their quality assurance approach.")])])
for it in M.items:
    if it.get("type") not in ("Heading", "Context"):
        it["decision"] = "Keep"
M.save(); W.Workspace(W.data_dir_for(LIST), "Kestrel").set("compliance_path", M.path)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.go("sort"); app.processEvents()
sp = w.sort_page
items = w.review.M.items
sp.seed("starter")
r = sp.rec()
cyber, trans = TP.find(r, "Cybersecurity")["id"], TP.find(r, "Transition")["id"]
sp.showing = cyber; sp.refresh()
sp.keywords("SIEM, security logs")
sg = TP.suggest(sp.rec(), items)
logs = next(it for it in items if "SIEM" in it.get("text", ""))
tr = next(it for it in items if "transition" in it.get("text", ""))
check("suggestions: keywords point at a topic, with the words that matched", sg.get(logs["id"], (None,))[0] == cyber
      and "SIEM" in sg[logs["id"]][1], sg.get(logs["id"]))
check("a topic's own name points too (Transition)", sg.get(tr["id"], (None,))[0] == trans)
check("nothing is filed until a suggestion is taken", TP.primary(sp.rec(), logs["id"]) is None)
sp.showing = "__unsorted__"; sp.refresh(); app.processEvents()
check("Unsorted shows each suggestion beside the requirement", any("Cybersecurity (matched: SIEM" in (sp.table.item(i, 5).text() or "")
                                                                   for i in range(sp.table.rowCount())))
n = sp.take_suggestions([logs, tr])
check("Take the suggestions files them under their suggested topics", n == 2 and TP.primary(sp.rec(), logs["id"])["id"] == cyber
      and TP.primary(sp.rec(), tr["id"])["id"] == trans)
# Structure
sp.view.setCurrentIndex(2); app.processEvents()
sv = sp.struct
check("Sort > Structure lists every topic with its requirements and what it fills", sv.table.rowCount() == len(TP.topics(sp.rec()))
      and "topic(s) with requirements and no section" in sv.gaps.text(), sv.gaps.text())
sv.rate("Strong", [cyber]); sv.rate("Gap", [trans])
check("our fit per topic", TP.get(sp.rec(), cyber)["fit"] == "Strong" and TP.get(sp.rec(), trans)["fit"] == "Gap")
got = sv.response_from_topics()
vol = got["volume"]
secs = [lab for lab in O.labels(w.review.M) if lab != vol]
check("Make the response from the topics: a Response volume, a section per topic", vol and "Response" in vol
      and len(got["made"]) == len(TP.roots(sp.rec())) and TP.get(sp.rec(), cyber)["sections"][0] in secs, (vol, secs))
n = sv.place()
check("Place their requirements: each kept requirement goes to its home topic's section", n == 2
      and next(i for i in w.review.M.items if i["id"] == logs["id"]).get("map") == TP.get(sp.rec(), cyber)["sections"][0])
qa = TP.find(sp.rec(), "Quality")["id"]
qtext = next(it for it in w.review.M.items if "quality" in it.get("text", "").lower())
TP.file_under(sp.rec(), [qtext["id"]], qa)
TP.update(sp.rec(), qa, sections=[])
sp.refresh()
check("what the structure still misses: a topic with requirements and no section", "Quality" in sv.gaps_now["no_section"])
target = TP.get(sp.rec(), cyber)["sections"][0]
sv.map_selected(target, [qa])
check("Map to it: a topic fills a section", target in TP.get(sp.rec(), qa)["sections"] and "Quality" not in sv.gaps_now["no_section"])
TP.update(sp.rec(), qa, sections=[])
sub = TP.add(sp.rec(), "Audits"); TP.set_parent(sp.rec(), sub, qa)
made = sv.make_subsections(target, [qa])
check("Make subsections under it: the topic's section under the one chosen, its subtopics under that", made.get(qa) and made.get(sub)
      and O.parent_of(w.review.M, O.index_of(w.review.M, made[sub])) is not None, made)
sv.place()
check("... and its requirements follow", next(i for i in w.review.M.items if i["id"] == qtext["id"]).get("map") == made[qa])
sp.view.setCurrentIndex(1); app.processEvents()
check("Overview shows our fit", any(sp.over.item(i, 8).text() == "Strong" for i in range(sp.over.rowCount())))

print(f"QT SORT 365 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
