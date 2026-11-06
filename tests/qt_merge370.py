"""3.70.0 offscreen: All Efforts' right-click menu (Open, Add to this effort..., Archive...; Restore for an archived
effort; never Delete), Archive asks first and No changes nothing, Show archived lists archived efforts and Restore
brings one back; the open effort is closed before it is archived; Add to this effort... merges another copy and shows
one summary with the items to review; the Effort Dashboard and the Library offer it too. Fictional content (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, effortrec as RR, workspace as W
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
reg = E.Registry(os.path.join(cfg, "efforts.json"))
paths = {}
for name, folder in (("Kestrel", "Mine"), ("Kestrel (Pat)", "Pat")):
    d = os.path.join(tmp, folder); os.makedirs(os.path.join(d, "Volumes"))
    lst = os.path.join(d, "Kestrel_Effort_List.xlsx"); L = E.EffortList(lst, "Kestrel"); L.pending = True; L.save()
    reg.put(name, path=lst); W.Workspace(W.data_dir_for(lst), name); paths[name] = lst
L = E.EffortList(paths["Kestrel (Pat)"]).load(); L.add_or_update("KTV", Definition="Kestrel Test Vehicle"); L.save()
L = E.EffortList(paths["Kestrel"]).load(); L.add_or_update("KTV", Definition="Kestrel Training Vehicle"); L.save()
import topics as TP
rp = RR.Record(W.data_dir_for(paths["Kestrel (Pat)"])); TP.add(rp, "Launch")
open(os.path.join(tmp, "Pat", "Volumes", "Kestrel_Volume_II.docx"), "wb").write(b"pat")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.go("efforts"); app.processEvents()
eh = w.efforts_page
eh.refresh(); app.processEvents()
check("both efforts on All Efforts", set(eh.cards) == {"Kestrel", "Kestrel (Pat)"})
menu = [a.text() for a in eh.card_menu("Kestrel (Pat)").actions() if a.text()]
check("right-click: Open, Add to this effort..., Archive... and never Delete", menu == ["Open", "Add to this effort...", "Archive..."]
      and not any("Delete" in t or "Remove" in t for t in menu), menu)
check("No at the question changes nothing", eh.archive("Kestrel (Pat)", answer=False) is False and not reg.get("Kestrel (Pat)").get("archived"))
w.open_effort("Kestrel (Pat)")
check("Yes archives it: the open effort is closed first, and it leaves All Efforts", eh.archive("Kestrel (Pat)", answer=True)
      and w.ws is None and set(eh.cards) == {"Kestrel"} and E.Registry(os.path.join(cfg, "efforts.json")).get("Kestrel (Pat)")["archived"]
      and os.path.isfile(paths["Kestrel (Pat)"]))
check("Show archived (1)", eh.show_arch.text() == "Show archived (1)")
check("the effort picker leaves it out", "Kestrel (Pat)" not in [w.effort_box.itemText(i) for i in range(w.effort_box.count())])
eh.show_arch.setChecked(True); app.processEvents()
check("Show archived lists it; its menu restores it", set(eh.cards) == {"Kestrel (Pat)"}
      and [a.text() for a in eh.card_menu("Kestrel (Pat)").actions() if a.text()] == ["Restore"])
eh.restore("Kestrel (Pat)"); eh.show_arch.setChecked(False); app.processEvents()
check("Restore brings it back", set(eh.cards) == {"Kestrel", "Kestrel (Pat)"} and not E.Registry(os.path.join(cfg, "efforts.json")).get("Kestrel (Pat)").get("archived"))
# ---- Add to this effort
w.open_effort("Kestrel")
out = eh.add_to("Kestrel", {"source": "Kestrel (Pat)", "parts": ["acronyms", "files", "record"]})
s = out["dialog"]
check("Add to this effort: merged into the open effort, which stays open", out["ok"] and w.effort_name == "Kestrel"
      and os.path.isfile(os.path.join(tmp, "Mine", "Volumes", "Kestrel_Volume_II.docx"))
      and any(t["name"] == "Launch" for t in RR.Record(w.ws.root).data.get("topics", [])))
check("one summary, with the two meanings of KTV to review", "From Kestrel (Pat)" in s.line.text() and s.table.rowCount() == 1
      and s.table.item(0, 1).text() == "KTV" and s.table.item(0, 2).text() == "Kestrel Training Vehicle")
s.close()
w.go("home"); app.processEvents()
check("the Effort Dashboard offers Add to this effort...", any(b.text() == "Add to this effort..." for b in w.home_page.findChildren(QPushButton)))
w.go("library"); app.processEvents()
check("the Library offers Add from another copy...", any(b.text() == "Add from another copy..." for b in w.library_page.findChildren(QPushButton)))
f = eh.add_to("Kestrel", {"source": "__files__"})
check("Files or a folder go in through the Library", f.get("library") and w.stack.currentWidget() is w.library_page)

print(f"QT MERGE 370 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
