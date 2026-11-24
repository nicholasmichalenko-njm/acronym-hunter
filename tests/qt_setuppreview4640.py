"""4.64.0 offscreen: Setup opens on the preview. A slim list of headings beside the volume as it will be written; a
heading clicked is gone to; Style names shows or hides the names; Sections shows who writes each and when; an order set
under each heading shows at once. Fictional (Kestrel)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import effort as E, workspace as W, setupdoc as SD, setuporder as SO
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk")
PDFS = [os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", n) for n in ("Section_L_print.pdf", "SOW.pdf")]
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.open_effort("Kestrel"); app.processEvents()
sp = w.setups_page
w.read_page.read(PDFS, os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"))
t0 = time.time()
while not (w.review is not None and w.stack.currentWidget() is w.assign_page) and time.time() - t0 < 120:
    app.processEvents(); time.sleep(0.02)
M = w.review.M; S = SD.setup_of(M)
labs = SD.labels(M)
kept = [it for it in M.items if it.get("suggest") != "Drop"][:8]
for n, it in enumerate(kept):
    it["decision"] = "Keep"; it["map"] = labs[1 + n % 2]
S["mgmt"][labs[1]] = "GUIDE keep this to two pages"
S["notes"][kept[0]["id"]] = "NOTE use the test table"
w.go("setups"); app.processEvents()
pp = sp.preview_pane
check("Setup opens on the preview, not the sections", sp.view == "preview" and pp.isVisibleTo(w) and not sp.builder.isVisibleTo(w)
      and sp.view_btns["preview"].isChecked() and not sp.view_btns["sections"].isChecked())
heads = [pp.heads.item(i).text() for i in range(pp.heads.count())]
check("a slim list of the volume's headings, indented by level", [h.strip() for h in heads] == labs and heads[1].startswith("    ")
      and not heads[0].startswith(" ") and pp.heads.width() < pp.view.width() / 2, heads)
txt = pp.view.toPlainText()
check("the volume as it will be written: the headings and the pieces placed", all(lab in txt for lab in labs) and kept[0]["text"][:30] in txt
      and "GUIDE keep this to two pages" in txt and "NOTE use the test table" in txt, txt[:300])
check("... each piece with its style's name", "SK RFP Requirement" in txt and "SK PM Direction" in txt and pp.names.isChecked())
check("the line over it says what is there and where Word's own pages are", "3 heading(s)" in pp.said.text() and "usual order" in pp.said.text()
      and "Exact preview in Word" in pp.said.text(), pp.said.text())
check("one volume: no volume box", not pp.volume.isVisibleTo(w))
pp.names.setChecked(False); app.processEvents()
check("Style names off: the names go, the text stays", "SK RFP Requirement" not in pp.view.toPlainText() and kept[0]["text"][:30] in pp.view.toPlainText())
pp.names.setChecked(True); app.processEvents()
pp.heads.setCurrentRow(2); app.processEvents()
check("a heading clicked is gone to", pp.goto(2) == labs[2])
a0, b0 = txt.index("NOTE use the test table"), txt.index(kept[2]["text"][:30])
SO.set_order(S, ["note", "topic", "objective", "capture", "rfp", "customer", "pm", "library"])
sp.refresh(); app.processEvents()
txt2 = pp.view.toPlainText()
check("an order set under each heading shows at once: the guidance after the RFP text", a0 < b0 and txt2.index("NOTE use the test table") > txt2.index(kept[2]["text"][:30])
      and "order you set" in pp.said.text(), pp.said.text())
sp.view_btns["sections"].click(); app.processEvents()
check("Sections shows the sections, who writes each and when", sp.view == "sections" and sp.builder.isVisibleTo(w) and not pp.isVisibleTo(w)
      and sp.p_lead.isVisibleTo(w))
sp.view_btns["preview"].click(); app.processEvents()
check("Preview brings the preview back", sp.view == "preview" and pp.isVisibleTo(w) and not sp.builder.isVisibleTo(w) and not sp.p_lead.isVisibleTo(w))
check("More has Exact preview in Word, where the line says it is", sp.bar.action("Exact preview in Word") is not None)
check("nothing was written: no setup made yet", not (M.setup or {}).get("exports"))
w.close()
print(f"QT SETUP PREVIEW 4640 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
