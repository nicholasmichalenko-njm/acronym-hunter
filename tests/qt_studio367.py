"""3.67.0 Template Studio II, offscreen: Template Studio > Read back (read a volume against the volume's parts and the field
recipes; Word draws each part with a stand-in Word); Production > Apply in Word (Beta, last in Production; read a draft,
untick and edit a change, make the copy with tracked changes; live needs Allow for this session; read the document open
in Word and put the ticked changes in, logged in the effort; a fixed copy as tracked changes through a stand-in Word).
Fictional content (Kestrel)."""
import json, os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, effortrec as RR, workspace as W, deliverables as DL, office_pdf as OP, banned as BN
OP.available = lambda: False
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow, RAIL, BETA

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
ws0 = W.Workspace(W.data_dir_for(LIST), "Kestrel")
DL.add(RR.Record(ws0.root), "Volume I Technical", "Volume")
BN.load = lambda: [{"Phrase": "will try", "Level": "Banned", "Use instead": "will", "Why": "Weak commitment"},
                   {"Phrase": "utiliz*", "Level": "Avoid", "Use instead": "use", "Why": "Plain language"},
                   {"Phrase": "seamless", "Level": "Avoid", "Use instead": "describe the interface", "Why": "Vague"}]
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
prod = [k for g, it in RAIL if g == "Production" for k, _t in it]
check("Apply in Word is last in Production, marked Beta", prod[-1] == "applyword" and "applyword" in BETA and "applyword" in w.step_btns)
# ---- Read back
import test_studio367 as T                       # its fixture volume and stand-in Word (its own checks run too)
w.go("studio"); app.processEvents()
st = w.studio_page
st.vol.setCurrentText("Volume I Technical"); st.fill()
st.tabs.setCurrentWidget(st.readback); app.processEvents()
rb = st.readback
res = rb.read(T.vol)
check("Read back: a row per thing checked, the summary on top", res and rb.table.rowCount() == len(res["rows"]) and "4 of 4 part(s)" in rb.what.text()
      and rb.b_draw.isEnabled())
check("... every part matches the usual plan", all(rb.table.item(i, 4).text() == "Matches" for i in range(rb.table.rowCount())
                                                   if rb.table.item(i, 0).text() != "Whole file"))
dr = rb.draw(runner=T.fake_word)
check("Word draws each part: one picture per part under the table", dr["ok"] and len(rb.pngs) == 4 and rb.sl.count() == 5)
check("a file that is not Word says so", rb.read(os.path.join(tmp, "x.docx")) is None)
# ---- Apply in Word
w.go("applyword"); app.processEvents()
ap = w.applyword_page
check("live is off until allowed for this session", not ap.b_live_read.isEnabled() and not ap.b_live.isEnabled())
import docxw
d = docxw.Doc(); d.para("Hopefully the Kestrel team will utilize the bus. We will try to finish early."); d.para("A seamless interface.")
src = os.path.join(tmp, "Kestrel draft.docx"); d.save(src)
ch = ap.read_draft(src)
check("read a draft: each phrase with its sentence; plain replacements ticked", ap.table.rowCount() == 3
      and [ap.table.item(i, 0).checkState() == Qt.Checked for i in range(3)] == [True, True, False]
      and "3 phrase(s) found, 2 ticked" in ap.what.text() and ap.b_copy.isEnabled())
ap.table.item(0, 2).setText("employ"); ap.table.item(1, 0).setCheckState(Qt.Unchecked)
check("edit the words and untick one", ch[0]["fix"] == "employ" and ch[1]["on"] is False)
out = os.path.join(tmp, "copy.docx")
cp = ap.make_copy(out)
x = zipfile.ZipFile(out).read("word/document.xml").decode()
check("the copy: one tracked change with the edited words, the advice as a comment", cp["changes"] == 1 and cp["comments"] == 1
      and "employ" in x and "beside the draft" in ap.what.text())
ap.allow.setChecked(True); app.processEvents()
check("Allow switches on Read the document open in Word", ap.b_live_read.isEnabled())
text = "\r".join(["Hopefully the Kestrel team will utilize the bus. We will try to finish early.", "A seamless interface.", ""])


def word(cmd, env, timeout):
    s = cmd[-1]
    if "Documents) { $docs" in s:
        return json.dumps({"ok": True, "docs": [{"name": "Kestrel draft.docx", "full": "C:\\Kestrel draft.docx", "saved": True, "track": False, "ro": False}]})
    if "Content.Text" in s:
        return json.dumps({"ok": True, "text": text, "track": False})
    plan = json.load(open(env["SK_PLAN"], encoding="utf-8"))
    return json.dumps({"ok": True, "results": [{"id": p["id"], "done": True} for p in plan], "track_was": False})


lv = ap.read_live("C:\\Kestrel draft.docx", runner=word)
check("read the document open in Word: its phrases, ready to put in", len(lv) == 3 and ap.b_live.isEnabled() and not ap.b_copy.isEnabled())
res = ap.apply_live(runner=word)
r = RR.Record(ws0.root)
check("put the ticked changes into Word: logged in the effort and listed", res["applied"] == 2 and len(r.data.get("word_live", [])) == 2
      and ap.log.rowCount() == 2 and ap.log.item(0, 5).text() == "Yes" and not ap.b_live.isEnabled())
ap.allow.setChecked(False)
check("without Allow nothing reaches Word", ap.read_live("C:\\Kestrel draft.docx", runner=word) is None)
fixed = os.path.join(tmp, "Kestrel draft - COPY - Stationkeeper.docx"); d.save(fixed)


def cmp_word(cmd, env, timeout):
    open(env["SK_OUT"], "wb").write(b"x")
    return json.dumps({"ok": True, "revisions": 7})


fx = ap.fixed_as_tracked(src, fixed, os.path.join(tmp, "fixes.docx"), runner=cmp_word)
check("a fixed copy as tracked changes: Word compares the draft with its fixed copy", fx["ok"] and fx["revisions"] == 7)

print(f"QT STUDIO 367 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
