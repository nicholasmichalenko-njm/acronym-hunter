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

n = sum(checks)
print(f"QT SPACES 3.53 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
