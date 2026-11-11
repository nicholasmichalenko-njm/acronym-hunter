"""3.38.0 the Rules page, offscreen: Production > Rules lists every production rule by group, with how it is kept and a
link to where its values live; turning one off for every effort; adding and removing a rule of your own (built-in rules
cannot be removed); the summary says how many this effort departs from (set on Effort Formatting); Change it opens the
page that holds a rule's values; the second family lists the reading rules and phrase rules, added and removed here."""
from PySide6.QtCore import Qt
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, prodrules as PRL, roleaccess as RA, rulebook as RB, suggestrules as SR
from PySide6.QtWidgets import QApplication, QCheckBox, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
import skqt.mainwin as MW
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel"); app.processEvents()

check("Rules is in the Production menu after Templates, for the Production role",   # 3.52.0: Production Standards moved to Advanced
      list(MW.TEAM)[2:4] == ["studio", "rules"]   # 3.75.0: the Team group
      and RA.allowed("Production", "rules") and not RA.allowed("Author", "rules"))
w.go("rules"); app.processEvents()
pg = w.rules_page
check("the page opens on our documents", w.stack.currentWidget() is pg and pg.stack.currentIndex() == 0 and pg.b_ours.isChecked())
labels = [pg.t.item(i, 0).text() for i in range(pg.t.rowCount()) if pg.t.item(i, 0) is not None]
check("every rule is listed under its group", all(f"Rule {i}" in labels for i in range(1, 14)) and all(g in labels for g in RB.GROUPS
                                                                                                   if any(r["group"] == g for r in RB.rules(cfg))))
row7 = labels.index("Rule 7")
check("each rule says how it is kept", pg.t.item(row7, 2).text() == "Checked by the app"
      and pg.t.item(labels.index("Rule 13"), 2).text() == "Checklist for people")
check("the summary counts the rules", "13 rules" in pg.summary.text() and "Kestrel follows every rule" in pg.summary.text(), pg.summary.text())

cb = pg.t.cellWidget(row7, 3).findChild(QCheckBox)
cb.setChecked(False); app.processEvents()
check("unticking a rule turns it off for every effort", not RB.get(cfg, 7)["on"] and "7" in PRL.for_effort(cfg, w.ws)["_rules_off"]
      and "1 off for every effort" in pg.summary.text(), pg.summary.text())
cb.setChecked(True); app.processEvents()
check("and on again", RB.get(cfg, 7)["on"])

pg.new_text.setText("Every graphic has a callout in the text before it appears.")
pg.new_group.setCurrentIndex(pg.new_group.findData("Writing"))
rid = pg.add_own(); app.processEvents()
labels = [pg.t.item(i, 0).text() if pg.t.item(i, 0) else "" for i in range(pg.t.rowCount())]
check("a rule of your own is added, numbered after the built-in ones, kept by people", rid == "14" and "Rule 14" in labels
      and RB.get(cfg, rid)["group"] == "Writing" and RB.get(cfg, rid)["kept"] == "people" and "14 rules" in pg.summary.text())
check("an empty rule is not added", pg.add_own() is None)
pg.t.selectRow(labels.index("Rule 4")); app.processEvents()
check("a built-in rule cannot be removed", pg.remove_own() is False and RB.get(cfg, 4) is not None)
pg.t.selectRow(labels.index("Rule 14")); app.processEvents()
check("your own rule can be removed", pg.remove_own() is True and RB.get(cfg, "14") is None)

RB.set_effort_on(w.ws, 2, False); pg.refresh(); app.processEvents()
check("the summary says how many this effort departs from, and the rule says so", "Kestrel departs from 1" in pg.summary.text()
      and "this effort departs from it" in pg.t.item([pg.t.item(i, 0).text() if pg.t.item(i, 0) else "" for i in range(pg.t.rowCount())].index("Rule 2"), 1).text())
RB.set_effort_on(w.ws, 2, True)

row6 = [pg.t.item(i, 0).text() if pg.t.item(i, 0) else "" for i in range(pg.t.rowCount())].index("Rule 6")
btn = pg.t.cellWidget(row6, 4)
check("Change it names where the rule's values live", btn is not None and "Heading numbering" in btn.text(), btn.text() if btn else None)
btn.click(); app.processEvents()
import skqt.prodstdpage as PS
check("Change it opens where the values live now (3.69.0: Formatting Standards)", w.stack.currentWidget() is w.formatstd_page)
w.go("rules"); app.processEvents()
row10 = [pg.t.item(i, 0).text() if pg.t.item(i, 0) else "" for i in range(pg.t.rowCount())].index("Rule 10")
pg.t.cellWidget(row10, 4).click(); app.processEvents()
check("Rule 10's values are on the Acronym List", (w.stack.currentWidget() is w.acronym_page and w.acronym_page.tab_stack.currentWidget() is w.acrlist_page))

w.go("rules"); app.processEvents()
pg.b_theirs.click(); app.processEvents()
check("the second family: how Review's Suggest reads a sentence", pg.stack.currentIndex() == 1 and "shall, must and will" in pg.reading.text())
pg.p_text.setText("proposals are limited to"); pg.p_cat.setCurrentIndex(pg.p_cat.findData("L"))
pg.p_scope.setCurrentIndex(pg.p_scope.findData("effort"))
r = pg.add_phrase(); app.processEvents()
check("a phrase rule for this effort is added and listed", r is not None and SR.effort_rules(w.ws)[0]["phrase"] == "proposals are limited to"
      and pg.pt.rowCount() == 1 and pg.pt.item(0, 2).text() == "This effort")
pg.p_text.setText("will be evaluated"); pg.p_cat.setCurrentIndex(pg.p_cat.findData("M")); pg.p_scope.setCurrentIndex(0)
pg.add_phrase(); app.processEvents()
check("a phrase rule for every effort is kept with the team's", SR.team_rules(cfg)[0]["phrase"] == "will be evaluated" and pg.pt.rowCount() == 2)
check("too short a phrase is refused", (pg.p_text.setText("ab"), pg.add_phrase())[1] is None)
pg.pt.selectRow(0); app.processEvents()
check("a phrase rule can be removed", pg.remove_phrase() == 1 and pg.pt.rowCount() == 1)
check("the summary counts the phrase rules", "1 phrase rule for" in pg.summary.text(), pg.summary.text())

w.close()
n = sum(checks)
print(f"QT RULES {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
