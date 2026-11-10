"""3.58.0 Final Check, offscreen. Check and Submit holds one menu item, Final Check, whose tabs are the report,
Submission Check and Final Checks; a volume's PDF is set once beside its Word file; pages that do not count are ticked
out per volume; Check gives every volume its eight sections; Export writes the Excel report and records it in the effort
record. Fictional content."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
sys.path.insert(0, HERE)

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


app = QApplication([]); theme.apply(app)
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
from skqt import mainwin as MW
check("Submit holds Final Check (3.75.0: nine groups)", ("finalcheck", "Submit") in dict(MW.RAIL)["Effort"])
check("... with Submission Check and Final Checks as its tabs", [k for k, _t in MW.TABS["finalcheck"]][:3] == ["finalcheck", "qa", "checks"])
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1400, 900); w.show(); app.processEvents()
import unfiled as UF
w.work_on(UF.NAME); app.processEvents()
w.step_btns["finalcheck"].click(); app.processEvents()
fp = w.finalcheck_page
check("the menu item opens the report, with its tabs", w.stack.currentWidget() is fp and w._tab_keys == ["finalcheck", "qa", "checks", "postsub", "keywords"])
w.go("checks"); app.processEvents()
check("Final Checks is a tab of it", w.stack.currentWidget() is w.checks_page and w._tab_keys == ["finalcheck", "qa", "checks", "postsub", "keywords"])
w.go("finalcheck"); app.processEvents()
check("no volumes yet: it says what to do", fp.check() == [] and "Add volumes" in fp.note.text())

# a volume: Word file and PDF
from pdfmake import make_pdf, PAGES as pages   # noqa: E402  (the engine test's fictional PDF)
docx = os.path.join(tmp, "Volume I Technical.docx")
WNS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
with zipfile.ZipFile(docx, "w") as z:
    z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
    z.writestr("word/document.xml", f'<w:document {WNS}><w:body><w:p><w:r><w:t>1 Technical Approach</w:t></w:r></w:p></w:body></w:document>')
pdf = make_pdf(os.path.join(tmp, "Volume I Technical.pdf"), pages)
fp.add_volumes([docx]); app.processEvents()
check("the volume listed, its PDF not set", fp.vols.rowCount() == 1 and fp.vols.item(0, 1).text() == "not set"
      and fp.vols.item(0, 2).text() == "every page counts")
fp.vols.selectRow(0)
fp.set_pdf(pdf)
check("Set the PDF: kept beside the Word file", fp.vols.item(0, 1).text() == "Volume I Technical.pdf"
      and w.ws.get("final_pdfs", {}).get(docx) == pdf)
fp.set_exclude(["cover", "toc"])
check("Pages that do not count: kept per volume", fp.vols.item(0, 2).text() == "The cover, The table of contents"
      and w.ws.get("final_exclude", {}).get(docx) == ["cover", "toc"])
got = fp.check()
import finalcheck as FC
check("Check: the volume's eight sections", got and {x["section"] for x in got[0]["lines"]} == set(FC.SECTIONS),
      {x["section"] for x in got[0]["lines"]} if got else None)
top = fp.tree.topLevelItem(0)
check("the report tree: the volume, its sections and lines", top.text(0) == "Volume I Technical" and top.childCount() == 8)
check("the counts in the pills", fp.p_fail.text().endswith("fail") and fp.p_pass.text().endswith("pass"))
pl = [x for x in got[0]["lines"] if x["check"] == "Pages against the limit"][0]
check("the page count leaves out what was ticked", "5 of 7 pages counted" in pl["detail"], pl["detail"])
out = fp.export(os.path.join(tmp, "Final Check.xlsx"))
check("Export writes the report", os.path.isfile(out))
import effortrec as R
ev = R.Record(w.ws.root).events(kinds=["check"])
check("... and records it in the effort record", ev and ev[0]["text"].startswith("Final Check: 1 volume(s)"), ev[:1])
check("guide topic and title", "finalcheck" in __import__("skqt.guide", fromlist=["TOPIC"]).TOPIC
      and "finalcheck" in __import__("skqt.pagetitles", fromlist=["TITLES"]).TITLES)
w.close()
n = sum(checks)
print(f"QT FINAL CHECK {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
