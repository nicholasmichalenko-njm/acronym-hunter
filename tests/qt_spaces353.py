"""3.53.0 spaces, offscreen. Acronyms: paste a picture (a screenshot or copied figure saved beside the list and read with
the files already scanned; picture files copied in File Explorer taken as they are; Ctrl+V in a text box still pastes
text) and the Found in pictures filter. Fictional content."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
from PySide6.QtCore import QMimeData, QUrl
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


app = QApplication([]); theme.apply(app)
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
from skqt.acrtool import AcronymToolWindow
from skqt import acrextras as AX
tw = AcronymToolWindow(cfg); tw.show(); app.processEvents()
page = tw.page
s = page.session
tech = os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx")
s.last_scan = {"paths": [tech], "folder": None, "cache": {}}
asked = []
page.scan = lambda paths, folder=None: asked.append(list(paths)) or "scanned"

img = QImage(320, 120, QImage.Format_RGB32); img.fill(QColor("white"))
check("Paste a picture is on the page", page.b_paste.isVisibleTo(tw) and page.b_paste.text() == "Paste a picture")
got = AX.paste_picture(page, image=img)
pasted = asked[-1][-1] if asked else ""
check("a pasted picture is saved beside the list as a PNG", os.path.isfile(pasted) and pasted.endswith(".png")
      and os.path.basename(os.path.dirname(pasted)) == "pasted pictures", pasted)
check("... and read with the files already scanned", got == "scanned" and asked[-1][0] == tech and len(asked[-1]) == 2, asked[-1])
AX.paste_picture(page, image=img)
check("a second paste keeps its own file", len(set(asked[-1])) == len(asked[-1]) and asked[-1][-1] != pasted, asked[-1])
fig = os.path.join(tmp, "Figure 3-2 Ops Concept.png"); img.save(fig, "PNG")
md = QMimeData(); md.setUrls([QUrl.fromLocalFile(fig)])
AX.paste_picture(page, mime=md)
check("picture files copied in File Explorer are taken as they are", asked[-1][-1] == fig, asked[-1])
n = len(asked)
empty = QMimeData(); empty.setText("just words")
check("nothing to paste: says so, scans nothing", AX.paste_picture(page, mime=empty) is None and len(asked) == n)
page.f_search.setFocus(); app.processEvents()
QApplication.clipboard().setText("KTV")
page._paste_shortcut.activated.emit()
check("Ctrl+V in the search box pastes text as always", page.f_search.text() == "KTV" and len(asked) == n, page.f_search.text())
page.f_search.clear()

# Found in pictures
s.results = {
    "KGS": {"category": "Acronym", "count": 1, "locations": ["Figure 3-2 Ops Concept.png (Image)"], "definitions": [],
            "selected_definition": "", "status": ""},
    "TTC": {"category": "Acronym", "count": 2, "locations": ["Kestrel_Technical_Volume.docx (para 4)",
                                                              "Kestrel_Technical_Volume.docx (page 3, image image2.png)"],
            "definitions": [], "selected_definition": "", "status": ""},
    "MOC": {"category": "Acronym", "count": 1, "locations": ["Kestrel_Technical_Volume.docx (para 7)"], "definitions": [],
            "selected_definition": "", "status": ""}}
page.f_status.setCurrentIndex(0); page.fill()
allrows = set(page.rows())
page.f_pics.setChecked(True)
pics = set(page.rows())
check("Found in pictures: only the terms read from a picture", pics == {"KGS", "TTC"} and "MOC" in allrows, (pics, allrows))
page.f_pics.setChecked(False)
tw.close()

# ---- the spaces, Home (Your Tools) and Team References
from skqt import mainwin as MW
from skqt import toolshome as TH
heads = [g for g, _i in MW.RAIL]
check("the menu is spaces by job", heads == ["Home", "Effort", "Customer Documents", "Shred", "Plan", "Write", "Submit", "Team",
                                             "Settings"], heads)   # 3.69.0: no Advanced group; 3.75.0: nine groups
check("each page in one space only", len([k for _g, it in MW.RAIL for k, _t in it]) == len({k for _g, it in MW.RAIL for k, _t in it}))
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1400, 900); w.show(); app.processEvents()
check("the tools button at the foot of the menu is gone", not hasattr(w, "tools_btn"))
w.rail_go("formatstd"); app.processEvents()
check("a space with nothing to work on, like Formatting Standards, opens as it is", w.ws is None and w.stack.currentWidget() is w.formatstd_page)
w.step_btns["acronyms"].click(); app.processEvents()
import unfiled as UF
check("a space that works on an effort opens on Unfiled when nothing is open", w.effort_name == UF.NAME
      and w.stack.currentWidget() is w.acronym_page and w.acronym_page.session is not None)
w.close_effort(); app.processEvents()
w.go("tools"); app.processEvents()
home = w.tools_page
check("Your Tools opens with no effort", w.stack.currentWidget() is home and w.page_title.text() == "Your Tools")
check("pins start from the role's set", home.pins == TH.load_pins(cfg, home.role()) and len(home.pins) >= 4, home.pins)
check("... Edit pins keeps your choice", home.edit_pins(["fulltext", "refs"]) == ["fulltext", "refs"] and TH.load_pins(cfg) == ["fulltext", "refs"])
docx = os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx")
pdf = os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Program_Manual.pdf")
kd = {k for k, _t in TH.uses_for([docx])}
kp = {k for k, _t in TH.uses_for([pdf])}
check("ask which tool: a Word file can have its first use checked, a PDF cannot", "firstuse" in kd and "firstuse" not in kp
      and {"acrfinder", "fulltext", "library"} <= kp, (kd, kp))
check("... a file the reader does not take: no tools", TH.uses_for([os.path.join(tmp, "notes.zzz")]) == [])
check("Pull out all the text: Full Text opens with the file", home.files_in([docx], use="fulltext") == "fulltext")
from skqt import fulltexttool as FT
check("... its window holds it", FT._OPEN and FT._OPEN[0].files == [docx])
FT._OPEN[0].close()
import recentfiles as RF
check("... and it is a recent file", RF.shown(cfg)[0]["path"] == docx and home.recent.item(0).data(0x0100) == docx)
import unfiled as UF
check("Working on: Unfiled is always there", w.effort_box.findText(UF.NAME) >= 0 and "Unfiled" in w.effort_box.toolTip())
w.go("tools"); w.work_on(UF.NAME); app.processEvents()
check("... working on Unfiled keeps you on Your Tools", w.effort_name == UF.NAME and w.stack.currentWidget() is home)
added = []
w.library_page.add = lambda paths=None, **k: added.append(list(paths or [])) or 1      # the Library asks where each file goes
got = home.files_in([docx], use="library")
check("Add to the Library of what I am working on: Unfiled's Library", got == "library" and w.effort_name == UF.NAME and added == [[docx]])
w.go("refs"); app.processEvents()
refs = w.refs_page
check("Team References: one space with every shared list", w.stack.currentWidget() is refs
      and set(refs.cards) == {"banned", "database", "exclusion", "ocrfix", "truth"} and refs.dict_card is not None)
check("... each says how many it holds", refs.cards["banned"].count.text().endswith("phrase(s)"), refs.cards["banned"].count.text())
dlg = refs.open_banned(run=False)
dlg.add_row({"Phrase": "best-in-orbit", "Level": "Avoid", "Use instead": "say what is better", "Why": "unproven claim"})
dlg.save(); refs.refresh()
import banned as BN
check("Banned phrases: added and saved for every effort", any(r["Phrase"] == "best-in-orbit" and r["Level"] == "Avoid" for r in BN.load()))
check("Fixes for misread text open from here", refs.open_fixes(run=False) is not None)
w.close()

n = sum(checks)
print(f"QT SPACES 3.53 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
