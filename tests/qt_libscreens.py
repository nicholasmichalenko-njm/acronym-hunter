"""3.50.0 the Quick Parts and Layout screens, offscreen: every item previews (Word's picture when Word drew it, the
app's sketch otherwise, never a blank); Quick Parts by their categories with their pages, Category... and Pages...;
Layout's covers drawn from their kept page; Draw with Word runs in the background, one Word job at a time, and keeps
Quick Parts' pages by the window. Word is stood in for. Fictional content."""
import os, shutil, sys, tempfile, threading, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import templatelib as TL, libcats as LC, libimport as LI, libpreview as LP, prodrules as PRL, prodtemplate as PT
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow, RAIL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
from skqt.mainwin import TABS as _TABS
check("Team lists Standards, its tabs Styles (3.94.0), Formatting, Quick Parts, Layout (3.75.0) and Parts (3.87.0 Section designs)",
      [k for g, it in RAIL if g == "Team" for k, _l in it][:1] == ["formatstd"] and [k for k, _t in _TABS["formatstd"]] == ["styles", "formatstd", "qpstd", "layoutstd", "designs"])     # 3.87.0: Section designs
# a template with Quick Parts, a cover and sections, imported into the library
from _qpfixture import with_glossary
QP_SRC = os.path.join(tmp, "Kestrel Master.dotx")
with_glossary(os.path.join(HERE, "pefix", "data", "PE_Master_Effort_Template.dotx"), QP_SRC, table_hdr=True)
std = PRL.for_effort(tempfile.mkdtemp()); std["variables"]["marking"] = "Kestrel restriction"
SRC = os.path.join(tmp, "Kestrel Volume.dotx")
shutil.copyfile(PT.make(std, tempfile.mkdtemp(), "").copy, SRC)
w.go("qpstd"); app.processEvents()
qp = w.qpstd_page
for path in (QP_SRC, SRC):
    ib = qp.import_file(path, run=False)
    ib.take(); ib.reject()
qp.library_changed(); app.processEvents()
cats = [qp.cats.item(r).data(0x0100) for r in range(qp.cats.count())]
check("Quick Parts lists their own categories", len(cats) >= 2 and all(c for c in cats), cats)
check("the Quick Parts list has a Pages column", qp.cols[-1] == "Pages")
qp.cats.setCurrentRow(0); app.processEvents()
first = qp.current()
check("a Quick Part shows its card as a sketch, and every value", qp.picture.source() == "sketch" and qp.editor.tree_ed.topLevelItemCount() > 2
      and not qp.picture.grab().isNull())
n = qp.set_category("09 Kestrel moved")
check("Category... moves a Quick Part to another category", n == 1 and qp.category() == "09 Kestrel moved"
      and TL.Library(cfg).values(TL.Library(cfg).get(first["id"]))["category"] == "09 Kestrel moved")
qp.select(first["id"])
check("Pages... types its pages", qp.type_pages(3) and qp.t.item(qp.t.currentRow(), 5).text().startswith("3 (typed)"))

# Draw with Word, one job at a time, pages kept by the window
from skqt import qpjobs
gate = threading.Event()
fake_png = os.path.join(tmp, "word.png"); QImage(40, 50, QImage.Format_RGB32).save(fake_png)


def fake_draw(_p, _s):
    gate.wait(10)
    lib = TL.Library(cfg)
    return {first["id"]: LP.keep_png(lib, lib.get(first["id"]), fake_png)}, {first["id"]: 4}


job = qp.draw_word([first["id"]], fn=fake_draw)
second = w.layoutstd_page.draw_word([first["id"]], fn=fake_draw)
check("Draw with Word runs in the background; a second Word job waits its turn", job is not None and second is None and job in qpjobs.RUNNING)
gate.set()
t0 = time.time()
while qpjobs.RUNNING and time.time() - t0 < 10:
    app.processEvents(); time.sleep(0.02)
app.processEvents()
qp.select(first["id"]); app.processEvents()
check("Word's picture shows once drawn, marked as Word's, and its pages are kept", qp.picture.source() == "word"
      and TL.Library(cfg).get(first["id"]).get("pages") == 4 and qp.t.item(qp.t.currentRow(), 5).text().startswith("4 (measured)"))

# ---- Layout
w.go("layoutstd"); app.processEvents()
lay = w.layoutstd_page
lcats = [lay.cats.item(r).text() for r in range(lay.cats.count())]
check("Layout lists its categories with counts (3.90.0: covers, title pages and back covers are in Section designs)",
      [c.split(" (")[0] for c in lcats] == [t for k, _t, _ks in LC.CATEGORIES["layout"] for t in [_t] if k not in lay.moved], lcats)
cov = next((i for i in lay.lib.items if i["kind"] == "cover"), None)
check("the imported cover is in Layout > Covers", cov is not None and LC.place(lay.lib, cov) == ("layout", "covers"))
if cov is not None:
    lay.select(cov["id"]); app.processEvents()
    w.go("designs"); app.processEvents()
    import sectiondesigns as SDZ
    check("3.90.0: the imported cover moved to Section designs", any(x.get("library_family") == cov.get("family", cov["id"])
                                                                   for x in SDZ.designs(cfg, "cover")), SDZ.designs(cfg))
blank = []
for lib_key, page in (("formatting", w.formatstd_page), ("quickparts", qp), ("layout", lay)):
    w.go({"formatting": "formatstd", "quickparts": "qpstd", "layout": "layoutstd"}[lib_key]); app.processEvents()
    for it in [i for i in page.lib.items if LC.place(page.lib, i)[0] == lib_key and LC.place(page.lib, i)[1] not in getattr(page, "moved", ())]:
        page.select(it["id"]); app.processEvents()
        img = page.picture.grab().toImage()
        bg = img.pixel(3, 3)
        drawn = sum(1 for x in range(10, img.width() - 10, 3) for y in range(10, img.height() - 30, 3) if img.pixel(x, y) != bg)
        if page.picture.it is None or img.isNull() or drawn < 20:
            blank.append((it["kind"], it["name"]))
check("every item previews (no blank picture)", not blank, blank)
check("the sketch says Word can draw it when it can", any(LP.word_can(i) for i in lay.lib.items))

w.close()
n = sum(checks)
print(f"QT LIBRARY SCREENS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
