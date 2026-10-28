"""Checks the Qt Assign test without a window (offscreen): reads the sample Section L, assigns, links, sets authors,
selects two sentences far apart, saves and reloads. Writes a picture of the window to the temp folder."""
import os, sys, shutil, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import compliance as C, pagesent as PS, setupdoc as SD
OUT = tempfile.mkdtemp()
PDF = os.path.join(OUT, "Section_L_print.pdf"); shutil.copy(os.path.join(os.path.dirname(HERE), "test_samples", "rfp_walk", "Section_L_print.pdf"), PDF)
mp = os.path.join(OUT, "Kestrel_Matrix.xlsx")
items, heads, _ = PS.read_review(PDF, "Section_L_print.pdf", C.extract)
M = C.Matrix(mp, "Kestrel"); M.items, M.headings = items, heads
for k, it in enumerate(M.items):
    it.setdefault("id", f"L-{k+1:02d}"); it.setdefault("decision", "")
M.sources = [["Section_L_print.pdf", "", "", PDF]]
M.outline = C.parse_outline("Volume I Technical\n1.1 Technical Approach\n1.2 Risk\nVolume II Management\n2.1 Program Management")
M.pending = True; M.save()
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
import assign_qt as Q
app = QApplication([])
w = Q.Main(mp); w.resize(1600, 1000); w.show(); app.processEvents()
S = w.store
by = lambda s: next(it for it in S.M.items if it["text"].startswith(s))
a = by("The Offeror shall describe its technical approach"); b = by("Each volume shall be written"); c = by("Information provided in one volume")
w.set_target("1.1 Technical Approach"); w.select(a["id"]); w.do_req()
w.set_target("2.1 Program Management"); w.select(b["id"]); w.do_req()
w.select(a["id"]); w.do_ctx() if False else None
w.select(c["id"]); S.last_req = a["id"]; w.do_ctx(); S.link(c, b["id"]); w.after()
w.select(a["id"]); S.set_authors(a, "A. Lee, K. Park"); w.after()
# Ctrl-like multi select of two far apart
w._guard = True; w.view.scene().clearSelection()
x1, x2 = by("Pages shall be"), by("The Offeror shall clearly identify") if any(it["text"].startswith("The Offeror shall clearly identify") for it in S.M.items) else S.M.items[30]
w.view.boxes[x1["id"]].setSelected(True); w.view.boxes[x2["id"]].setSelected(True); w._guard = False; w.on_select()
print("multi", [r["id"] for r in w.selected()])
w.select(a["id"]); app.processEvents()
w.view.fit(); app.processEvents()
w.grab().save(os.path.join(OUT, "assign_qt.png"))
print("boxes", len(w.view.boxes), "a", SD.item_sections(S.M, a), a.get("owner"), "c", c.get("context_for"))
w.do_save(); print("saved", os.path.isfile(mp), os.path.isfile(os.path.splitext(mp)[0] + " (before the Qt test).xlsx"))
M2 = C.Matrix(mp).load(); a2 = next(i for i in M2.items if i["id"] == a["id"]); print("reloaded", a2["decision"], a2["owner"])
ok = SD.item_sections(S.M, a) == ["1.1 Technical Approach"] and a2["owner"] == "A. Lee, K. Park" and len(w.view.boxes) >= 40
print("QT ASSIGN SMOKE " + ("PASS" if ok else "FAIL"), os.path.join(OUT, "assign_qt.png"))
