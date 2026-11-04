"""3.40.0 pages come out right, offscreen. Page kinds: a page built here with a background and text blocks is a placed
page, paragraphs make a flow page, a table holding the text makes a table page; the labels say which. A flow or table page
is never turned into a placed one: Edit the layout sends it to Edit in Word, and Save as a cover layout refuses it. Text on
the page: lines listed as they print (your words or the field), Add a field and Add text with no dialog. Edit in Word: a
dated working copy opens; while Word holds it nothing is kept; once saved and let go it is kept as a new version and the
page before it stays. Word draws the page: Word's picture is shown when it is kept ("Drawn by Word"), else the sketch, and
Word's PDF becomes the picture once per page. Fictional content only."""
import json, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import coverbuild as CB, docxw, pagekinds as PK, prodparts as PP, wordedit as WE, wordpreview as WP
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
from skqt import docparts as DP
from skqt.coverview import CoverLayoutDialog

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
from PIL import Image
pic = os.path.join(tmp, "background.png")
Image.new("RGB", (1300, 1700), (31, 56, 100)).save(pic, "PNG")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1600, 980); w.show()
w.go("prodstd"); app.processEvents()
sp = w.prodstd_page

# ---------------------------------------------------------------- page kinds
d = DP.new_page(sp, "cover", run=False)
d.background(pic, mode="margins")
d.add_block({"field": "volume_name", "x": 1.0, "y": 4.0, "w": 6.5, "h": 0.8, "size": 30, "bold": True, "align": "center"})
check("a page built here (a background and text blocks) is a placed page", PK.kind_of(d.result_bytes(), sp.work) == "placed")
check("... and the editor says so", "A placed page" in d.kind_lab.text(), d.kind_lab.text())


def doc_bytes(build):
    doc = docxw.Doc(); build(doc)
    p = os.path.join(tmp, f"page{time.time_ns()}.docx"); doc.save(p)
    return open(p, "rb").read()


flow = doc_bytes(lambda doc: [doc.rich([("Kestrel Flight Software Plan", {"bold": True, "size": 40})]), doc.rich([("Volume I: Technical", None)]),
                              doc.rich([("Prepared for the Fictional Space Office", None)])])
table = doc_bytes(lambda doc: doc.table(["", ""], [["Kestrel Flight Software Plan", "Volume I"], ["Prepared for", "Fictional Space Office"]], [4680, 4680]))
check("paragraphs in the page's flow make a flow page", PK.kind_of(flow, sp.work) == "flow", PK.kind_of(flow, sp.work))
check("a table holding the text makes a table page", PK.kind_of(table, sp.work) == "table", PK.kind_of(table, sp.work))
check("flow and table pages are changed in Word; placed pages in the layout editor", PK.editor_for("flow") == "word"
      and PK.editor_for("table") == "word" and PK.editor_for("placed") == "layout")

# ---------------------------------------------------------------- Text on the page
n0 = d.texts.rowCount()
check("Add a field adds a line that prints the field, under the last line", d.quick_add(field="solicitation") and d.texts.rowCount() == n0 + 1)
check("Add text adds a line of your own words", d.quick_add(text="Draft for review") and d.texts.rowCount() == n0 + 2
      and any(d.texts.item(r, 0).text() == "Draft for review" for r in range(d.texts.rowCount())))
heads = [d.texts.horizontalHeaderItem(c).text() for c in range(3)]
labels = [d.texts.cellWidget(r, 2).currentText() for r in range(d.texts.rowCount())]
check("each line says what it prints: your words or the field", heads == ["Prints", "Where", "What it is"] and "Your words" in labels
      and any(x.startswith("The Volume name field") for x in labels), (heads, labels))
placed_name = d.save()
check("the placed page is kept", placed_name and (sp.work.get("page_parts") or {}).get("cover") == placed_name)

# ---------------------------------------------------------------- a flow page is never converted
fd = CoverLayoutDialog(sp, "cover", data=flow)
check("Save as a cover layout refuses a flow page (it would turn it into a placed page)", fd.save_layout("Flow cover") is None
      and "flow page" in fd.status.text().lower(), fd.status.text())
fd.reject()
flow_name = os.path.basename(PP.save_part(sp.parts_dir(), flow, "back cover"))
sp.work.setdefault("page_parts", {})["backer"] = flow_name
check("Edit the layout sends a flow page to Edit in Word", DP.edit_layout(sp, "backer", run=False) is None)
check("the page's label says which kind it is", "A flow page" in DP.page_kind_text(sp, flow_name) and "Edit in Word" in DP.page_kind_text(sp, flow_name))
check("a placed page still opens in the layout editor", DP.edit_layout(sp, "cover", run=False) is not None)

# ---------------------------------------------------------------- Edit in Word
opened = []


def word_opens(path):
    opened.append(path)
    open(WE.lock_names(path)[0], "w").write("lock")          # Word holds it


copy = DP.edit_in_word(sp, "backer", opener=word_opens)
check("Edit in Word opens a dated working copy, never the kept page", copy and opened == [copy] and os.path.dirname(copy).endswith("Editing")
      and os.path.basename(copy) != flow_name)
check("while Word holds the copy nothing is kept", DP.check_word_edit(sp) == "" and sp.work["page_parts"]["backer"] == flow_name)
new_flow = doc_bytes(lambda doc: [doc.rich([("Kestrel Flight Software Plan", {"bold": True, "size": 40})]),
                                  doc.rich([("Volume II: Management", None)])])
open(copy, "wb").write(new_flow)
os.utime(copy, (time.time() + 5, time.time() + 5))
os.remove(WE.lock_names(copy)[0])                             # saved and closed
new_name = DP.check_word_edit(sp)
check("once saved and let go, it is kept as a new version", new_name and new_name != flow_name and sp.work["page_parts"]["backer"] == new_name)
check("the page before it stays", os.path.isfile(os.path.join(sp.parts_dir(), flow_name)))
check("the new version is still a flow page (Word kept its paragraphs)", DP.page_kind(sp, new_name) == "flow")
copy2 = DP.edit_in_word(sp, "backer", opener=lambda p: None)
check("closing Word without saving keeps nothing new", DP.check_word_edit(sp, force=False) == "" and sp.work["page_parts"]["backer"] == new_name)
DP._stop_word_edit(sp)

# ---------------------------------------------------------------- Word draws the page
pv = DP.PartPreview(sp, "cover"); pv.resize(320, 420)
data = open(os.path.join(sp.parts_dir(), placed_name), "rb").read()
img = QImage(320, 420, QImage.Format_ARGB32); img.fill(0xFFFFFFFF)
p = QPainter(img)
check("without Word's picture the sketch is drawn", pv.draw_word(p, pv.rect().toRectF() if hasattr(pv.rect(), "toRectF") else pv.rect(), data) is False)
p.end()


def fake_word(cmd, env, timeout):                           # Word saves a PDF of the page
    Image.new("RGB", (850, 1100), (240, 240, 240)).save(env["SK_PDF"], "PDF")
    return json.dumps({"ok": True, "pages": 1, "heads": []})


r1 = WP.draw(sp.parts_dir(), data, runner=fake_word)
check("Word's PDF of the page becomes its picture", r1["ok"] and os.path.isfile(r1["png"]) and not r1["cached"], r1)
check("drawn once: the same page uses the kept picture", WP.draw(sp.parts_dir(), data, runner=fake_word)["cached"])
img2 = QImage(320, 420, QImage.Format_ARGB32); img2.fill(0xFFFFFFFF)
p2 = QPainter(img2)
from PySide6.QtCore import QRectF
check("Word's picture is shown when it is kept", pv.draw_word(p2, QRectF(10, 10, 300, 390), data) is True)
p2.end()
pv.grab()
check("the preview draws without an error", True)
check("a changed page has no picture until Word draws it", WP.cached(sp.parts_dir(), new_flow) == "")

w.close()
n = sum(checks)
print(f"QT PAGES {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
