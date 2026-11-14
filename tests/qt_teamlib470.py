"""4.7.0 offscreen: the team library in the window. The tick writes Global Standards.xlsx in the team library and says
so; Settings > The team shows the Team library card with where it is; Change... points it at another folder (a synced
SharePoint library) and the workbook is written there; a value changed in Excel reaches Styles' standard on the next
tick; the open effort's formatting workbook is written beside its list (Effort Formatting's Open this effort's
workbook); a column taken out asks once; Styles' More opens the workbook. Fictional content."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_TEAMLIB_TEST"] = "1"
import app_gui as A
tmp = tempfile.mkdtemp()
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
import openpyxl
import effort as E, prodrules as PRL, effortformat as EFM, teamlib as T
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme, teamlibview as TV
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "Stationkeeper Data", "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
d = PRL.load(cfg); d["company"]["style_defs"] = {"Body Text": {"type": "paragraph", "font": "Arial", "size": 11}}; PRL.save(cfg, d)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel"); app.processEvents()
check("the window ticks the team library every two minutes", w.team_timer.interval() == 120000 and w.team_timer.isActive())
said = TV.tick(w)
book = T.book_path(cfg)
check("the tick writes Global Standards.xlsx in Stationkeeper Data\\Team library and says so", os.path.isfile(book)
      and "Team library" in book and any("written" in s for s in said), (book, said))
ebook = T.effort_book_path(LIST, "Kestrel")
check("... and the open effort's formatting workbook beside its list", os.path.isfile(ebook))
w.go("settings"); sp = w.settings_page; app.processEvents()
check("Settings > The team shows the Team library card with where it is", sp.tl_card is not None and T.folder(cfg) in sp.tl_where.text(),
      sp.tl_where.text())
wb = openpyxl.load_workbook(book); ws = wb["Styles"]; hdr = [c.value for c in ws[1]]
ws.cell(2, hdr.index("Size (pt)") + 1).value = 12; wb.save(book); time.sleep(0.02)
def _glob(fn):                                                  # 4.32.0: the workbook holds the Global Standards, effort open or not
    with __import__("effortset").as_global():
        return fn()


said = TV.read_now(sp)                                          # 4.10.0: Read it now does the two-minute check at once
check("a value changed in Excel reaches the standard with Read it now, and the status says so",
      _glob(lambda: PRL.load(cfg))["company"]["style_defs"]["Body Text"]["size"] == 12 and any("Read from the Global Standards workbook" in s for s in said), said)
check("Settings > Team library has Read it now", any(b.text() == "Read it now" for b in sp.tl_card.findChildren(__import__("PySide6.QtWidgets", fromlist=["x"]).QPushButton)))
seen = []; real_status = w.status; w.status = lambda t: (seen.append(t), real_status(t))
check("... with nothing new it says so", TV.read_now(sp) == [] and any("no changes" in t for t in seen), seen)
w.status = real_status
EFM.set_layer(w.ws, {"variables": {"body_size": 12}})
w.go("effortfmt"); app.processEvents()
p = w.effortfmt_page.open_book()
check("Effort Formatting: Open this effort's workbook (written first with the effort's change)", p == ebook
      and [r[0].value for r in openpyxl.load_workbook(ebook)["Settings"].iter_rows(min_row=2)] == ["body_size"])
wb = openpyxl.load_workbook(book); ws = wb["Styles"]; hdr = [c.value for c in ws[1]]
ws.delete_cols(hdr.index("Size (pt)") + 1); wb.save(book); time.sleep(0.02)
asked = []
TV.ask_removed = lambda ww, cols, run=True, answer=None: asked.append(cols)
TV.tick(w)
check("a column taken out asks once", asked and ("Styles", "size") in [tuple(x) for x in asked[0]], asked)
other = os.path.join(tmp, "SharePoint", "Proposal Team Library"); os.makedirs(other)
TV.change(sp, other); TV.tick(w)
check("Change... points it at another folder: the workbook is written there", os.path.isfile(os.path.join(other, T.BOOK)))
w.go("styles"); app.processEvents()
check("Styles' More opens the Global Standards workbook", "Open the Global Standards workbook" in w.styles_page.bar.labels())
w.close()
print(f"QT TEAMLIB 470 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
