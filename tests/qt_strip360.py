"""3.60.0, offscreen. Compare > Any two files > Tracked changes (Word)...: Word's own Compare for two Word files when Word
is on the PC (here a stand-in), the text of both otherwise; Plan > Setup > Strip setup... and Your Tools' Strip the setup
out make a clean copy beside the volume. Fictional content."""
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

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


app = QApplication([]); theme.apply(app)
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
from skqt import mainwin as MW
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1400, 900); w.show(); app.processEvents()
import docxw
a, b = os.path.join(tmp, "Draft A.docx"), os.path.join(tmp, "Draft B.docx")
for path, t in ((a, "The team keeps the network on station."), (b, "The team keeps the whole network on station.")):
    d = docxw.Doc(); d.heading("1 Approach", 1); d.para(t); d.save(path)
w.go("compare"); app.processEvents()
cs = w.compare_space
cs.show_files(a, b)
out = cs.files.export_tracked(os.path.join(tmp, "text.docx"), use_word=False)
with zipfile.ZipFile(out) as z:
    x = z.read("word/document.xml").decode()
check("Tracked changes (Word): the text of both, as tracked changes", "<w:ins " in x and "whole" in x)
import wordcompare as WC
called = []
WC.compare = lambda o, n, p, au="Compare", **k: called.append((o, n, p)) or open(p, "wb").write(open(out, "rb").read()) and {"ok": True, "revisions": 2}
got = cs.files.export_tracked(os.path.join(tmp, "word.docx"), use_word=True)
check("... two Word files go to Word's own Compare", called and called[0][0] == a and called[0][1] == b and got.endswith("word.docx"))
WC.compare = lambda *a_, **k: {"ok": False, "why": "Word could not compare the two files."}
got = cs.files.export_tracked(os.path.join(tmp, "fallback.docx"), use_word=True)
check("... and when Word cannot, the text comparison is saved instead", os.path.isfile(got))

# Strip setup
vol = os.path.join(tmp, "Volume I.docx")
d = docxw.Doc(); d.styles = {"rfp": "SKRFPRequirement"}
d.heading("1 Approach", 1); d.para("The Offeror shall describe its approach.", kind="rfp"); d.para("Our approach.")
d.save(vol)
with zipfile.ZipFile(vol) as z:
    has_style_def = b"SKRFPRequirement" in z.read("word/styles.xml")
import unfiled as UF
w.work_on(UF.NAME); w.go("setups"); app.processEvents()
res = w.setups_page.strip_files([vol])
check("Plan > Setup > Strip setup...: a clean copy beside the volume", res and os.path.isfile(res[0]["out"]) and res[0]["paragraphs"] == 1,
      (res, has_style_def))
import skqt.toolshome as TH
check("Your Tools offers Strip the setup out for a Word file", "strip" in [k for k, _t in TH.uses_for([vol])])
r2 = w.tools_page.run("strip", [vol])
check("... and makes the copy", r2 and r2[0]["out"] != res[0]["out"] and os.path.isfile(r2[0]["out"]))
w.close()
n = sum(checks)
print(f"QT STRIP AND TRACKED {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
