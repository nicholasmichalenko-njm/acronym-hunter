"""3.19.0 parts of the response structure in Review, offscreen: add a cover, a title page, front matter items, appendices
and a back cover to a volume; the structure list shows each part with the rules it follows from Production Standards;
an item moves to another part; which parts count toward the page limit (the Page budget follows); sentences go in a
front matter item like any section; Undo takes a part item back out; the Structure tab's text and Response Setup carry
the parts and their rules."""
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
import effort as E, workspace as W, office_pdf as OP, compliance as C, pagemarks as PM, suggestrules as SR
OP.available = lambda: False
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


import outline_ops as O, setupdoc as SD, structparts as SP, pagebudget as PB, zipfile
from PySide6.QtCore import Qt
w.go("assign"); app.processEvents()
v1 = pg.new_volume(title="Technical"); app.processEvents()
s1 = pg.new_section(title="Technical Approach"); app.processEvents()
check("a volume with a response section", v1.startswith("Volume ") and s1 == "1 Technical Approach", (v1, s1))
cov = pg.add_part("cover"); ttl = pg.add_part("title")
toc = pg.add_part("front", title="Table of contents"); es = pg.add_part("front", title="Executive summary")
app_a = pg.add_part("appendix", title="Resumes"); bk = pg.add_part("back"); app.processEvents()
order = O.in_volume(M, v1)
check("a cover, title page, front matter, appendix and back cover take their places in the volume",
      order == [v1, "Cover", "Title page", "Table of contents", "Executive summary", "1 Technical Approach", "Appendix A Resumes", "Back cover"], order)
heads = [n.text(0) for n in pg.part_nodes]
check("the structure list shows each part", heads == ["COVER", "TITLE PAGE", "FRONT MATTER", "RESPONSE", "APPENDICES", "BACK COVER"], heads)
fm = next(n for n in pg.part_nodes if n.text(0) == "FRONT MATTER")
check("... with the rules it follows from Production Standards", "i, ii" in fm.toolTip(0) and "volume name" in fm.toolTip(0)
      and fm.text(3) == "not counted", fm.toolTip(0))
check("... and its items under it", [fm.child(i).text(0) for i in range(fm.childCount())] == ["Table of contents", "Executive summary"])
pg.set_target("Executive summary"); new = pg.move_to_part("body"); app.processEvents()
check("an item moves to another part: Executive summary becomes the first response section", new == "1 Executive summary"
      and O.in_volume(M, v1).index(new) == O.in_volume(M, v1).index("2 Technical Approach") - 1, (new, O.in_volume(M, v1)))
w.undo_here(); app.processEvents()
check("Undo puts it back in the front matter", "Executive summary" in O.labels(M) and "1 Technical Approach" in O.labels(M))
n0 = len(M.outline)
pg.add_part("appendix", title="Past performance"); app.processEvents()
w.undo_here(); app.processEvents()
check("Undo takes an added part item back out", len(M.outline) == n0)
# sentences go in a front matter item like any section
rows = [it for it in M.items if it.get("file") == "Section_L_print.pdf" and not it.get("decision") and it["id"] in pg.view.boxes]
pg.set_target("Executive summary"); pg.select(rows[0]["id"]); pg.do_lm("L"); app.processEvents()
check("a requirement goes in a front matter item", pg.R.item(rows[0]["id"])["map"] == "Executive summary")
# page limits: only the parts that count
PB.set_pages(M, "Executive summary", 2); PB.set_pages(M, "1 Technical Approach", 10); PB.set_pages(M, "Appendix A Resumes", 5)
labs = O.in_volume(M, v1)
check("the page total counts only the response by default", PB.total(M, labs) == 10, PB.total(M, labs))
d = pg.parts_dialog(run=False)
check("Part rules and page limits lists every part with its rules", d._api["table"].rowCount() == 6 and "i, ii" in d._api["sums"]["front"]
      and "no page numbers" in d._api["sums"]["cover"], d._api["sums"])
d._api["boxes"]["appendix"].setChecked(True); d._api["save"]()
check("ticking the appendices counts them", SP.counts(M, "appendix") and PB.total(M, labs) == 15)
check("the Page budget splits only across the parts that count", PB.parts(M, labs) == ["1 Technical Approach", "Appendix A Resumes"], PB.parts(M, labs))
# the Structure tab's text and Response Setup carry the parts
w.go("structure"); app.processEvents()
txt = w.structure_page.text.toPlainText()
check("the Structure tab's text tags each part", "[Cover] Cover" in txt and "[Front matter] Table of contents" in txt and "[Appendix]" in txt, txt)
tv = next(w.structure_page.tree.topLevelItem(i) for i in range(w.structure_page.tree.topLevelItemCount())
          if w.structure_page.tree.topLevelItem(i).text(0).startswith(v1))
pv = [tv.child(i).text(0) for i in range(tv.childCount())]
check("... and its preview shows them", any("[Front matter]" in x for x in pv), pv)
check("Apply keeps the parts", w.structure_page.apply() and [SP.part_of(o) for o in M.outline].count("front") == 2)
out = os.path.join(tmp, "setup"); os.makedirs(out)
SD.export(M, out, part_rules=lambda vol: SP.summaries(w.config_dir, w.ws, M, vol))
doc = "".join(zipfile.ZipFile(os.path.join(r, f)).read("word/document.xml").decode("utf-8", "replace")
              for r, _d, fs in os.walk(out) for f in fs if f.endswith(".docx"))
check("Response Setup starts each part with its rules", "FRONT MATTER: page numbers i, ii" in doc and "COVER: no page numbers" in doc
      and "APPENDICES: page numbers A-1" in doc, doc[doc.find("COVER"):doc.find("COVER") + 120])
w.close()
n = sum(checks)
print(f"QT PARTS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
