"""2.85.0 Change review in Compare, offscreen: each change shows in its place in both versions (struck red, new green)
and on a strip of where the changes are; every change gets decisions that land where people work: Updates a
requirement (new wording, old in its history, owner to confirm; the dashboard counts it; the owner confirms in Assign
or in Requirement history), New requirement (into a section), Context for a requirement (on its card), Removes a
requirement (marked, never deleted), Task, Question, Note, No action with a reason; Compare counts what is decided,
filters what is not, and marks the version reviewed when every change is decided; a decision taken off undoes itself;
decisions stay with the change when the versions are compared again."""
import os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, effortrec as RR, docversions as DV, workspace as W, office_pdf as OP, changereview as CR, ctxdocs as CX
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
from test_docversions import amend

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); CDIR = os.path.join(EDIR, "Customer documents"); os.makedirs(CDIR)
RFP = os.path.join(A.BASE_DIR, "test_samples", "rfp")
shutil.copy2(os.path.join(RFP, "Kestrel_RFP_Sections_C_L_M.docx"), CDIR)
INBOX = os.path.join(tmp, "inbox"); os.makedirs(INBOX)
AMD = amend(os.path.join(RFP, "Kestrel_RFP_Sections_C_L_M.docx"), os.path.join(INBOX, "Kestrel_RFP_Sections_C_L_M_Amd1.docx"),
            [("exceed 50 pages", "exceed 40 pages"), ("the five highest", "the ten highest")])
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CDIR)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Management")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.read_page.read([os.path.join(CDIR, "Kestrel_RFP_Sections_C_L_M.docx")], os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
t = time.time()
while w.review is None and time.time() - t < 60:
    app.processEvents(); time.sleep(0.02)
M = w.review.M
pl = next(it for it in M.items if "exceed 50 pages" in it["text"])
w.review.req([pl], "1.1 Technical Approach"); w.changed(); w.save_now()
w.go("docs"); app.processEvents()
dp = w.docs_page
dp.add(dp.ctx.unadded(), choices=[{}])
d, v = dp.add([AMD], choices=[{}])[0]
# Compare
w.go("compare"); app.processEvents()
cp = w.compare_page
rows = cp.show(d["id"], None, v["id"])
ch = [i for i, r in enumerate(rows) if r["kind"] != "same"]
check("two changes, both to decide", len(ch) == 2 and "0 of 2 decided" in cp.p_dec.text() and cp.table.item(0, 4).text() == "to decide", cp.p_dec.text())
hit = next(i for i in ch if "40 pages" in rows[i]["new"])
cp.select_index(hit); app.processEvents()
L_html, R_html = cp.sbs.left.toHtml(), cp.sbs.right.toHtml()
check("side by side: the old words struck in red, the new in green, around the change", "line-through" in L_html and "50" in L_html
      and "40" in R_html and "WAS: ORIGINAL" in cp.sbs.l_title.text() and "NOW: AMENDMENT 1" in cp.sbs.r_title.text())
check("the strip marks every change", len(cp.strip.marks()) == 2)
# 2.85.0 one Changes page: the summary of what the version touches, changes tagged, filtered by a click
check("each change says what it touches", "rule" in cp.tags[hit] and "req" in cp.tags[hit], cp.tags[hit])
chips = list(cp.strip_sum.chips)
check("the summary strip: requirements, submission rules, to decide", "req" in chips and "rule" in chips and "open" in chips, chips)
cp.strip_sum.chips["rule"].click(); app.processEvents()
check("a click on submission rules filters the list", cp.shown == [hit], cp.shown)
cp.set_tag_filter("all"); app.processEvents()
cp.select_index(hit); app.processEvents()
check("a rule change offers Updates a submission rule", cp.decide_panel.btns["rule"].isVisibleTo(cp.decide_panel))
dec_rule = cp.decide_panel.decide("rule")
rr = {r["key"]: r for r in cp.ctx.reg.rows()}
pk_rule = next(k for k, r in rr.items() if r["kind"] == "Page limit" and "40" in r["value"])
check("Updates a submission rule: the rule is no longer waiting", dec_rule and not rr[pk_rule]["to_review"])
w.go("requirements"); app.processEvents()
sr = w.requirements_page
sr.select(pk_rule); app.processEvents()
html = sr.now_html(sr.rows[pk_rule])
check("Submission rules shows Was and Now in the row", html and "line-through" in html and "50" in html and "40" in html)
check("and opens the change in Changes", sr.open_change(pk_rule) and w.stack.currentWidget() is cp and cp.current_index() == hit)
bd = cp.author_briefs(run=False)
check("author briefs from the Changes page", bd is not None or w.impact_page.r is not None)
w.go("docs"); app.processEvents()
check("Customer versions and Impact review still open (from Library and Changes), off the rail", w.stack.currentWidget() is w.docs_page
      and "docs" not in w.step_btns and "impact" not in w.step_btns)
w.go("compare"); app.processEvents()
rows = cp.show(d["id"], None, v["id"]); cp.select_index(hit); app.processEvents()
dpnl = cp.decide_panel
check("the touched requirement is offered first", dpnl.req.currentData() == pl["id"], dpnl.req.currentText())
dec = dpnl.decide("updates")
pl2 = w.review.item(pl["id"])
check("Updates a requirement: the new wording, owner to confirm", dec and "exceed 40 pages" in pl2["text"] and pl2["new"].endswith("owner to confirm"))
rv = CR.Review(w.ws.root).load()
check("the old wording is in its history", rv.history(pl["id"])[0]["old"].count("50 pages") == 1 and pl["id"] in rv.awaiting())
check("Compare counts it", "1 of 2 decided" in cp.p_dec.text(), cp.p_dec.text())
w.go("dashboard"); app.processEvents()
check("the dashboard counts changes to decide and owners to confirm", "awaiting the owner" in w.dash_page.tiles["review"].caption.text(),
      w.dash_page.tiles["review"].caption.text())
w.go("assign"); w.assign_page.files.setCurrentText(pl2["file"]); app.processEvents(); w.assign_page.select(pl["id"]); app.processEvents()
check("Assign's card shows the history, awaiting the owner", w.assign_page.hist_labels and "Awaiting the owner" in w.assign_page.hist_labels[0].text())
check("the owner confirms it there", w.assign_page.confirm_change(pl["id"]) and pl["id"] not in CR.Review(w.ws.root).load().awaiting()
      and pl2["new"].endswith("owner confirmed"))
# the other change: several decisions, then undo one
w.go("compare"); app.processEvents()
rows = cp.show(d["id"], None, v["id"])
other = next(i for i in ch if i != hit)
cp.select_index(other); app.processEvents()
dpnl.decide("new", target="1.2 Management")
newid = CR.Review(w.ws.root).load().decisions(cp.pk, rows[other]["key"])[0]["ref"]
it = w.review.item(newid)
check("New requirement: into the section, from the new version", it and it["decision"] == "Keep" and it["map"] == "1.2 Management"
      and "ten highest" in it["text"] and "Amendment 1" in it["new"])
dpnl.decide("context", target=pl["id"])
check("Context for a requirement: on its card", CX.Store(w.ws.root).load().for_requirement(pl["id"]))
n0 = len(RR.Record(w.ws.root).data["notes"])
dpnl.decide("question")
check("Question: in the effort record, quoting the change", len(RR.Record(w.ws.root).data["notes"]) == n0 + 1
      and "Amendment 1" in RR.Record(w.ws.root).data["notes"][-1]["text"])
check("every change decided: the version is marked reviewed", DV.Library(w.ws.p("documents")).load().counts()["unreviewed"] == 0
      and "2 of 2 decided" in cp.p_dec.text())
decs = CR.Review(w.ws.root).load().decisions(cp.pk, rows[other]["key"])
new_dec = next(x for x in decs if x["kind"] == "new")
cp.select_index(other); app.processEvents()
check("a decision taken off undoes itself", dpnl.undo(new_dec["id"]) and w.review.item(newid)["decision"] == "")
cp.undec.setChecked(True); app.processEvents()
check("Only undecided", cp.shown == [])
cp.undec.setChecked(False)
# compared again: the decisions stay with the change
rows2 = cp.show(d["id"], None, v["id"])
check("compared again, the decisions stay", "2 of 2 decided" in cp.p_dec.text() and "Updates a requirement" in cp.decided_text(rows2[hit]["key"]))
# removal and no action, directly on the review rules
rv = CR.Review(w.ws.root).load()
e = CR.apply_remove(M, rv, newid, d["name"], "Amendment 1")
check("Removes a requirement: marked, never deleted, with its history", w.review.item(newid)["new"].startswith("Removed by") and e
      and newid in rv.awaiting())
dlg = cp.history_dialog(run=False)
check("Requirement history lists them, awaiting the owner", dlg.fill() >= 3 and "awaiting the owner" in dlg.count.text())
dlg.only.setCurrentIndex(1)
check("filtered to awaiting the owner, and confirmed there", dlg.fill() >= 1 and dlg.confirm(newid))
dpnl.decide("none", why="", i=hit)
check("No action keeps a reason (editorial by default)", any(x["kind"] == "none" and x["why"] == "editorial"
                                                               for x in CR.Review(w.ws.root).load().decisions(cp.pk, rows2[hit]["key"])))
w.close()
n = sum(checks)
print(f"QT CHANGE PASS ({n}/{len(checks)})" if n == len(checks) else f"QT CHANGE FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
