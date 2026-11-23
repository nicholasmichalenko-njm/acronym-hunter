"""4.59.4 offscreen (Nicholas 2026-11-23 14:24, "Address open stability items"): the window is built with the
application's style sheet set aside and the sheet is back when it is done; the usage counter is on the buttons, not on
every event; an update saves and closes the work before the program's files change; splitting a document by section
makes a new document per section without copying the whole. Fictional content (Kestrel)."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import sectiondesigns as SDG
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from skqt import design as theme, updates as UP, usage as US
import skqt.mainwin as MW

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


ROOT = os.path.dirname(HERE)
app = QApplication([]); theme.apply(app)
sheet = app.styleSheet()
seen = []
orig = MW.MainWindow._build
MW.MainWindow._build = lambda self, *a, **k: (seen.append(app.styleSheet()), orig(self, *a, **k))[1]
w = MW.MainWindow(app, tempfile.mkdtemp(), A.APP_VERSION); w.resize(1400, 900); w.show(); app.processEvents()
MW.MainWindow._build = orig
check("the window is built with the application's style sheet set aside", sheet and seen == [""], seen)
check("... and the sheet is back, the same, once it is built", app.styleSheet() == sheet)
check("the menu's entries are styled as before", w.step_btns["home"].objectName() == "rail" and w.isVisible())

# the usage counter
c = US.install(w)
src = open(os.path.join(ROOT, "skqt", "usage.py"), encoding="utf-8").read()
check("the usage counter is not a filter on the whole application", "instance().installEventFilter" not in src)
if c is not None:
    b = QPushButton("Kestrel check", w); b.show(); app.processEvents()
    n = app._sk_tuner.sweep()
    before = sum(v for s in c.d["counts"].values() for v in (s.values() if isinstance(s, dict) else [s]))
    QTest.mouseClick(b, Qt.LeftButton, Qt.NoModifier, QPoint(5, 5)); app.processEvents()
    after = sum(v for s in c.d["counts"].values() for v in (s.values() if isinstance(s, dict) else [s]))
    check("a button found by the sweep has its clicks counted", b.property("sk_usage") and after == before + 1, (before, after))
else:
    check("no counter in this edition", True)

# the update: saved and closed before the files change
order = []


class _U:
    EXT = UP.U.EXT
    UpdateError = UP.U.UpdateError
    check = staticmethod(lambda path, folder, prog: {"info": {}})
    summary = staticmethod(lambda plan: "")
    stage = staticmethod(lambda plan, path, folder: order.append("stage"))
    apply = staticmethod(lambda plan, folder: order.append("apply") or {"copied": 1, "to": "9.9.9"})
    undo = staticmethod(lambda folder, prog: order.append("undo") or {"to": "9.9.8"})
    backup_info = staticmethod(lambda folder: {"version": "9.9.8"})


real = UP.U
UP.U = _U
try:
    UP.install_update(w, path="x.skupdate", answer="install", on_close=lambda: order.append("close"), restart=lambda *a, **k: order.append("restart"))
    check("an update: staged, the work saved and closed, then the files changed, then the restart", order == ["stage", "close", "apply", "restart"], order)
    order.clear()
    UP.undo_update(w, answer="undo", on_close=lambda: order.append("close"), restart=lambda *a, **k: order.append("restart"))
    check("a roll back: the work saved and closed, then the files changed", order == ["close", "undo", "restart"], order)
finally:
    UP.U = real

# splitting by section
W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W_NS}"><w:body>'
       '<w:p><w:r><w:t>Kestrel cover</w:t></w:r></w:p><w:p><w:pPr><w:sectPr><w:pgSz w:w="12240" w:h="15840"/></w:sectPr></w:pPr></w:p>'
       '<w:p><w:r><w:t>Heron back page</w:t></w:r></w:p><w:sectPr><w:pgSz w:w="15840" w:h="12240"/></w:sectPr></w:body></w:document>')
tmp = tempfile.mkdtemp(); srcx = os.path.join(tmp, "Kestrel designs.docx")
with zipfile.ZipFile(srcx, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", "<Types/>"); z.writestr("word/document.xml", doc); z.writestr("word/media/image1.png", b"\x89PNG" + b"0" * 4000)
out = SDG.split(srcx, os.path.join(tmp, "out"))
texts = [zipfile.ZipFile(p).read("word/document.xml").decode("utf-8") for p in out]
check("one file per section, each with its own words and page", len(out) == 2 and "Kestrel cover" in texts[0] and "Heron" not in texts[0]
      and "Heron back page" in texts[1] and "Kestrel" not in texts[1] and 'w:w="12240"' in texts[0] and 'w:w="15840"' in texts[1], texts)
zi = {i.filename: i for i in zipfile.ZipFile(out[0]).infolist()}
check("every part goes along; a picture is stored as it is", set(zi) == {"[Content_Types].xml", "word/document.xml", "word/media/image1.png"}
      and zi["word/media/image1.png"].compress_type == zipfile.ZIP_STORED and zi["word/document.xml"].compress_type == zipfile.ZIP_DEFLATED)

print(f"STABILITY 4594 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
