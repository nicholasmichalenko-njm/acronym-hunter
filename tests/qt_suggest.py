"""3.18.0 suggestions in Review, offscreen: Suggest shows what each sentence most likely is (rules, not AI), dashed on
the page in its category's color with its reason on the card; nothing is decided until the person accepts (Enter, the
clear ones, or all shown); accepted ones stay marked until checked; changing or rejecting a suggestion is counted, and
Make a rule... teaches it (the rule applies at once and to every later read); the score counts kept, changed, not
right and missed; rules for the team and for one effort, kept and taken out."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, workspace as W, office_pdf as OP, suggestrules as SR
OP.available = lambda: False
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Heron"); os.makedirs(ED)
LIST = os.path.join(ED, "Heron_Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Heron").set("outline_text", "Volume I Technical\n1.1 Technical Approach")
PDF = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Heron")
w.read_page.read([PDF], os.path.join(ED, "Heron_Compliance_Matrix.xlsx"))
wait(lambda: w.review is not None and w.stack.currentWidget() is w.assign_page)
pg = w.assign_page
M = w.review.M
pg.files.setCurrentText("Section_L_print.pdf"); app.processEvents()
undecided0 = sum(1 for it in M.items if not it.get("decision"))
check("nothing is suggested until asked", not pg.sg_on and not pg.sg_strip.isVisibleTo(pg)
      and not any(b.sg for b in pg.view.boxes.values()))
pg.sg_btn.click(); app.processEvents()
shown = pg.shown_here()
check("Suggest shows suggestions on the page, dashed, and decides nothing", pg.sg_on and pg.sg_strip.isVisibleTo(pg) and len(shown) > 5
      and any(b.sg and b.pen().style() == Qt.DashLine for b in pg.view.boxes.values())
      and sum(1 for it in M.items if not it.get("decision")) == undecided0, len(shown))
cats = {pg.sg[it["id"]]["cat"] for it in shown}
check("... in categories: L, M and the customer's among them", {"L", "M"} <= cats or {"L", "cust"} <= cats, cats)
shall = next(it for it in shown if pg.sg[it["id"]]["cat"] == "L" and pg.sg[it["id"]]["clear"])
check("... each with its reason, from the rules (no AI)", "shall" in pg.sg[shall["id"]]["why"].lower() or "offeror" in pg.sg[shall["id"]]["why"].lower(),
      pg.sg[shall["id"]]["why"])
pg.select(shall["id"]); app.processEvents()
from PySide6.QtWidgets import QLabel
txt = " ".join(x.text() for x in pg.card.findChildren(QLabel))
check("the card says what was suggested and why", pg.sg_box is not None and "Suggested" in txt and "Why:" in txt)
pg.accept_suggestions(rows=pg.selected()); app.processEvents()
check("Enter accepts one: it is decided as suggested, marked from a suggestion, not checked yet",
      shall["decision"] == "Keep" and shall.get("lm") == "L" and pg.sg[shall["id"]]["state"] == "accepted" and pg.sg[shall["id"]]["unchecked"])
clear = pg.shown_here(True)
n = pg.accept_suggestions(clear_only=True); app.processEvents()
check("Accept the clear ones: only the clear ones; the rest stay waiting for you", n == len(clear) and pg.shown_here(True) == []
      and all(pg.sg[it["id"]]["state"] == "accepted" for it in clear), (n, len(clear)))
left = pg.shown_here()
check("... the unclear ones are still shown, undecided", all(not it.get("decision") for it in left))
# a person changes an accepted one: counted as changed, and the card offers a rule
x = clear[0] if clear else shall
pg.select(x["id"]); app.processEvents()
pg.do_ctx(); app.processEvents()
check("changing a suggestion counts as changed, and counts as looked at", pg.sg[x["id"]]["state"] == "changed"
      and not pg.sg[x["id"]].get("unchecked"))
from PySide6.QtWidgets import QPushButton
btns = [b.text() for b in pg.sg_box.findChildren(QPushButton)] if pg.sg_box else []
check("... the card offers Make a rule...", "Make a rule..." in btns, btns)
# not right
y = left[0] if left else None
if y is not None:
    pg.select(y["id"]); app.processEvents()
    pg.reject_suggestion(); app.processEvents()
    check("Not right: the suggestion goes, the sentence stays undecided", pg.sg[y["id"]]["state"] == "rejected" and not y.get("decision")
          and not pg.view.boxes[y["id"]].sg)
# a miss: a sentence with no suggestion made a requirement
miss = next((it for it in M.items if not it.get("decision") and not (pg.sg.get(it["id"]) or {}).get("cat")
             and it.get("file") == "Section_L_print.pdf"), None)
if miss is not None:
    pg.select(miss["id"]); app.processEvents(); pg.do_lm("L"); app.processEvents()
c = SR.score(M.items, pg.sg)
check("the score counts kept, changed, not right and missed", c["agreed"] >= 1 and c["changed"] >= 1 and c["rejected"] >= (1 if y else 0)
      and c["missed"] >= (1 if miss else 0) and c["right_pct"] is not None and "right" in pg.sg_text.text(), c)
# checked
pg.select_unchecked(); app.processEvents()
sel = pg.selected()
check("Select unchecked finds the accepted ones nobody checked", sel and all(pg.sg[it["id"]].get("unchecked") for it in sel), len(sel))
pg.check_suggestion(sel); app.processEvents()
check("... Checked clears the mark", not any(r.get("unchecked") for r in pg.sg.values()))
# teach it: a rule from a sentence
z = next((it for it in M.items if not it.get("decision") and pg.sg.get(it["id"]) and pg.sg[it["id"]].get("state") == "shown"), None)
if z is not None:
    phrase = " ".join(z["text"].split()[:4])
    r = pg.make_rule(z, answer=(phrase, "ctx", "team"))
    check("Make a rule: it applies at once to what is still waiting", r and pg.sg[z["id"]]["cat"] == "ctx"
          and "team rule" in pg.sg[z["id"]]["why"], pg.sg[z["id"]])
    check("... kept for the team on this PC", any(SR.norm(x["phrase"]) == SR.norm(phrase) for x in SR.team_rules(cfg)))
    r2 = pg.make_rule(z, answer=(phrase, "ignore", "effort"))
    check("... a rule for this effort wins over the team's", pg.sg[z["id"]]["cat"] == "ignore" and "this effort rule" in pg.sg[z["id"]]["why"])
    d = pg.rules_dialog(run=False)
    t = d._api["table"]
    check("Rules... lists both, with who and when", t.rowCount() == 2 and {t.item(i, 2).text() for i in range(2)} == {"Team", "This effort"})
    t.selectRow(0); d._api["take_out"]()
    check("... Take out removes one", t.rowCount() == 1 and not SR.effort_rules(w.ws))
check("a rule needs a real phrase", pg.make_rule(M.items[0], answer=("ab", "L", "team")) is None)
# kept with the effort
w.save_now() if hasattr(w, "save_now") else None
check("suggestions and their outcome are kept with the effort", SR.store(w.ws) and SR.store(w.ws)[shall["id"]]["state"] == "accepted")
pg.sg_btn.click(); app.processEvents()
check("Suggest off: the dashed suggestions go; decisions stay", not pg.sg_strip.isVisibleTo(pg) and not any(b.sg for b in pg.view.boxes.values())
      and shall["decision"] == "Keep")
# the rules engine on its own
check("rules: the Government's sentence is the customer's", SR.suggest(M, {"text": "The Government will award one contract.",
      "actor": "Government", "type": "Information", "strength": "Information", "suggest": "Drop", "modal": "will"})["cat"] == "cust")
check("rules: may is never suggested", SR.suggest(M, {"text": "The Offeror may include a cover letter.", "actor": "Offeror",
      "type": "Instruction", "strength": "Optional", "suggest": "Review", "modal": "may"})["cat"] is None)
check("rules: a rule's 'No suggestion' stops one", SR.suggest(M, {"text": "Offerors are cautioned that late is late.",
      "suggest": "Keep", "strength": "Mandatory"}, [{"phrase": "are cautioned", "cat": "none"}])["cat"] is None)
w.close()
n = sum(checks)
print(f"QT SUGGEST {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
