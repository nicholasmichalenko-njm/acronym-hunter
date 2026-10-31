"""3.0.4 Settings > Custom dictionaries, offscreen: start a dictionary, add typed words, search, change a spelling, remove
words, import a Word .dic, add the open effort's approved acronyms, export for Word (and the dated copy), rename and
remove; Settings' Go to row reaches the card."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import customdict as CD, effort as E
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.go("settings"); app.processEvents()
c = w.settings_page.dict_card
check("Settings has Custom dictionaries, empty to start", c.pick.count() == 0 and not c.words.isEnabled() and "No dictionaries" in c.note.text())
check("... and Go to reaches it", any(b.text() == "Custom dictionaries" for b in w.settings_page.findChildren(type(c.rename_btn))))
did = c.new_dict("Sierra Space Custom")
check("+ Dictionary starts one", did and c.pick.currentText() == "Sierra Space Custom" and c.words.count() == 0)
n = c.add_typed("CDRL, Tenacity  Dream-Chaser;LIFE CDRL")
check("typed words are added (spaces or commas between them)", n == 4 and c.words.count() == 4 and c.count.text() == "4 words", c.count.text())
c.find.setText("ten"); app.processEvents()
check("search shows only the matches", c.words.count() == 1 and c.words.item(0).text() == "Tenacity" and "1 of 4" in c.count.text())
c.find.setText("")
check("change a spelling", c.edit_word("LIFE", "LIFE-1") and "LIFE-1" in CD.Store(cfg).get(did)["words"])
check("remove selected words", c.remove_selected(["Dream-Chaser"]) == 1 and c.words.count() == 3)
dic = os.path.join(tmp, "word.dic")
with open(dic, "w", encoding="utf-16") as f:
    f.write("Zeta\r\nCDRL\r\nalpha\r\n")
check("import a Word .dic: only the new words", c.import_dic(dic) == 2 and c.words.count() == 5)
LIST = os.path.join(tmp, "K", "K_Effort_List.xlsx"); os.makedirs(os.path.dirname(LIST))
L = E.EffortList(LIST, "K"); L.pending = True; L.save()
w.efforts.put("K", path=LIST)
w.open_effort("K"); app.processEvents()
lst = E.EffortList(LIST, "K").load()
lst.rows["IMS"] = dict(next(iter(lst.rows.values()), {}), Status="Approved") if lst.rows else {"Status": "Approved"}
lst.rows["TBD"] = {"Status": "Rejected"}
w.record_page.effort_list = lambda: lst
w.go("settings"); c.refresh(); app.processEvents()
check("Add the effort's acronyms: the approved ones", c.effort_btn.isEnabled() and c.add_effort() == 1 and "IMS" in CD.Store(cfg).get(did)["words"]
      and "TBD" not in CD.Store(cfg).get(did)["words"])
out = os.path.join(tmp, "out.dic")
check("Export for Word writes the .dic", c.export(out) == out and open(out, "rb").read()[:2] == b"\xff\xfe" and len(CD.read_dic(out)) == 6)
kept = os.listdir(os.path.join(A.DATA_DIR, CD.EXPORTS))
check("... keeps a dated copy in the data folder and says so", len(kept) == 1 and "Last exported" in c.note.text(), kept)
c.with_effort.setChecked(True)
check("the effort's name can go in the file name", "K" in c.store.export_name(did, w.effort_name))
check("rename", c.rename("Team words") and c.pick.currentText() == "Team words")
check("remove the dictionary", c.remove_dict(sure=True) and c.pick.count() == 0)
w.close()
t = sum(checks)
print(f"QT DICT {'PASS' if t == len(checks) else 'FAIL'} ({t}/{len(checks)})")
sys.exit(0 if t == len(checks) else 1)
