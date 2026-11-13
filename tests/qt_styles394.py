"""3.94.0 offscreen: the Styles page (Team > Standards > Styles). Empty: one way in. Bring in from a document: only
styles, New and Different shown and ticked, yours and the file's side by side, a set each. One row per style with its
versions as tabs; a set's view, the newer-version notice and Move this set; a style made here; Make a copy to change;
the row's menu. Fictional files (the Kestrel set)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import office_pdf as OP
OP.available = lambda: False
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
import stylelib as SL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1600, 980); w.show()
w.go("styles"); app.processEvents()
sp = w.styles_page
check("Styles is a tab of Standards", ("styles", "Styles") in dict(__import__("skqt.mainwin", fromlist=["x"]).RAIL)["Templates"])   # 4.28.0: a menu entry of Templates
check("empty: one way in", sp.empty.isVisible() and not sp.rows.isVisible())
check("one bar: New style, Bring in from a document... (the main one)", sp.bar.main is sp.b_bring and len(sp.bar.commands) <= 5)
DOC = os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx")
rfp = sp.new_set(name="RFP volume")
check("a new set shows on the left with its count", sp.sets.count() == 2 and "RFP volume" in sp.sets.item(1).text())
dlg = sp.bring_in(DOC, run=False)
shown = [r["name"] for r in dlg.shown]
check("only styles, New ticked by default; Already have it hidden", dlg.rows and all(r["state"] == "new" for r in dlg.rows)
      and len(shown) == len(dlg.rows) and dlg.count() == len(dlg.rows))
dlg.tick_all(); app.processEvents()
check("Untick all shown, then Tick all shown", dlg.count() == 0 and dlg.b_all.text() == "Tick all shown")
for r in dlg.rows:
    r["keep"] = r["name"] in ("Heading 1", "Normal", "Heading 2")
    r["set"] = rfp["id"] if r["name"] != "Normal" else None
dlg.count()
check("the button says how many", dlg.b_go.text() == "Bring in 3 style(s)", dlg.b_go.text())
c = dlg.go(); app.processEvents()
check("they come in, into their set", c["new"] == 3 and len(sp.row_ids) == 3 and len(SL.get_set(sp.lib, rfp["id"])["items"]) == 2, c)
check("each row: a preview in the style's look", len(sp.rows.findChildren(__import__("PySide6.QtWidgets", fromlist=["x"]).QWidget, "stylePreview")) == 3)   # 4.28.1: a box
dlg2 = sp.bring_in(DOC, run=False)
same = [r["name"] for r in dlg2.rows if r["state"] == "same"]
check("met again: the three kept are Already have it; 4.30.1: shown and ticked, so they can join a set", sorted(same) == ["Heading 1", "Heading 2", "Normal"]
      and all(r["name"] in [x["name"] for x in dlg2.shown] and r["keep"] for r in dlg2.rows if r["state"] == "same")
      and dlg2.chips["same"].text() == "Already have it 3", (same, dlg2.chips["same"].text()))
dlg2.chips["same"].setChecked(True); app.processEvents()
check("... shown when asked, with yours beside the file's", len(dlg2.shown) == len(dlg2.rows) and dlg2.table.cellWidget(0, 2) is not None
      or any(dlg2.table.cellWidget(i, 2) is not None for i in range(dlg2.table.rowCount())))
dlg2.reject()
# a new version of Heading 1
h1 = next(i for i in sp.lib.items if i["name"] == "Heading 1")
rows = SL.against(sp.lib, [s for s in SL.read_styles(DOC) if s["name"] == "Heading 1"])
rows[0]["values"] = dict(rows[0]["values"], size=18.0); rows = SL.against(sp.lib, rows)
SL.bring_in(sp.lib, rows, DOC)
sp.refresh(); app.processEvents()
check("one row per style: two versions of Heading 1 are still one row", len(sp.row_ids) == 3)
tabs = sp.ver_tabs.get(h1["family"])
btns = tabs.findChildren(QPushButton) if tabs else []
check("its versions are tabs on the row, the newest shown", [b.text() for b in btns] == ["v1", "v2"] and btns[1].isChecked())
btns[0].click(); app.processEvents()
check("a tab clicked shows that version", h1["id"] in sp.row_ids)
# a set's view: the version it uses, and the newer one
sp.sets.setCurrentRow(1); app.processEvents()
check("a set's rows show the version it uses", sp.sid == rfp["id"] and h1["id"] in sp.row_ids and len(sp.row_ids) == 2)
check("... and say a newer version came in", sp.notice.isVisible() and "v2" in sp.notice_lab.text() and sp.b_move.text() == "Move this set to v2")
sp.move_newer(); app.processEvents()
h1v2 = sp.lib.latest(h1["id"])
check("Move this set to v2", h1v2["id"] in SL.get_set(sp.lib, rfp["id"])["items"] and not sp.notice.isVisible())
# a style made here, in the set shown
it = sp.new_style(name="SK Compliance Char", typ="character", look={"font": "Calibri", "size": 11, "color": "C00000", "bold": True,
                                                                   "hidden": True}, marks="Compliance language")
check("a style made here joins the set shown", it and it["id"] in SL.get_set(sp.lib, rfp["id"])["items"] and it["id"] in sp.row_ids)
new = sp.change_look(it["id"], look={"font": "Calibri", "size": 11, "color": "8B0000", "bold": True, "hidden": True})
check("Make a copy to change: a new version, shown on the row; the first stays", new and new["version"] == 2
      and sp.lib.get(it["id"]) is not None and new["id"] in sp.row_ids or new["id"] in [r["shown"] for r in SL.rows(sp.lib, None)])
sp.select(h1v2["id"]); app.processEvents()
acts = [a.text() for a in sp.row_menu(run=False).actions()]
check("the row's menu: Add to set, Take out of this set, Review or change (4.30.1), Duplicate, Name this version, Remove",
      all(x in acts for x in ("Add to set", "Take out of this set", "Review or change...", "Duplicate...", "Name this version...",
                              "Remove from the library")), acts)
sp.label_version(h1v2["id"], "large")
check("Name this version shows on its tab", any(b.text() == "v2 large" for b in sp.ver_tabs[h1["family"]].findChildren(QPushButton)))
check("a style in a set is not removed", sp.remove([h1v2["id"]]) == 0)
sp.sets.setCurrentRow(0); app.processEvents()
pl = sp.new_set(name="Page-limited RFP")
sp.add_to_set(pl["id"], [h1["id"]])
check("one style, two sets, different versions", h1["id"] in SL.get_set(sp.lib, pl["id"])["items"]
      and h1v2["id"] in SL.get_set(sp.lib, rfp["id"])["items"])
check("the set list takes drops", sp.sets.acceptDrops())
sp.find.setText("compliance"); app.processEvents()
check("find a style by name", len(sp.row_ids) == 1)
print(f"{sum(checks)}/{len(checks)} passed")
w.close()
sys.exit(0 if all(checks) else 1)
