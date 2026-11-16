"""4.44.0 offscreen (ST57): a template's exact pages. Draw with Word exports when the file is not the picks', Word
draws the file's pages (a fake Word here), the pictures are kept and shown labelled Exact, and a changed pick brings
the sample pages back. Nothing is drawn unless asked. Fictional (Osprey)."""
import json, os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import namedtemplates as NT
import pagelayouts as PGL, prodrules as PRL
import stylelib as SL
import templateexact as TX
import templatelib as TL
import pypdfium2 as pdfium
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
from skqt import design as D, mainwin as MW, qpjobs
from skqt import tplbuilder as TB

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


calls = []


def word(cmd, env, timeout):
    """A fake Word: notes what it was given and writes a PDF of three pages, the second landscape."""
    with zipfile.ZipFile(env["SK_DOC"]) as z:
        names = z.namelist(); ct = z.read("[Content_Types].xml").decode("utf-8")
    calls.append({"timeout": timeout, "names": names, "ct": ct})
    d = pdfium.PdfDocument.new()
    for w_, h_ in ((612, 792), (792, 612), (612, 792)):
        d.new_page(w_, h_)
    d.save(env["SK_PDF"]); d.close()
    return json.dumps({"ok": True, "pages": 3, "heads": []})


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
app = QApplication([]); D.apply(app)
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.rail_go("templates"); app.processEvents()
pg = w.named_page; pg._allowed = lambda: True
lib = TL.Library(cfg)
s1, _ = SL.new_style(lib, "Body Text", "paragraph", {"font": "Arial", "size": 11})
ka = SL.new_set(lib, "RFP volume"); SL.add_to_set(lib, ka["id"], [s1["id"]])
lay = PGL.new(cfg, "layout", "Letter, 0.75 in", PRL.load(cfg)["company"]); PGL.set_page(cfg, lay["id"], None, [0.75] * 4)
b = pg.new(); b.name.setText("Page-limited RFP, Volume I"); b.toggle_style_set(ka["id"])
check("the builder has Draw with Word between Close and Export", b.b_exact.text() == "Draw with Word"
      and "minute or more" in b.b_exact.toolTip())
check("nothing was drawn by opening the builder", calls == [] and not b.strip.exact and b.kind.text() == TB.SKETCH)
check("no file yet: the module says to export first", TX.draw(cfg, None, runner=word) == {"ok": False, "why": "Export the template first: Word draws the file the export writes."}
      and calls == [])
res = b.draw_exact(runner=word, wait=True)
t = NT.get(cfg, b.tid)
check("Draw with Word exports first, then Word draws the file", res == "done" and t and t["made"]["version"] == 1 and len(calls) == 1)
check("Word got the file as a document, without the Quick Parts, with a time limit", "wordprocessingml.document.main+xml" in calls[0]["ct"]
      and "template.main+xml" not in calls[0]["ct"] and not any(n.startswith("word/glossary/") for n in calls[0]["names"])
      and calls[0]["timeout"] == TX.LIMIT == 300, calls[0]["ct"][:300])
kept = TX.cached(cfg, t)
check("three pictures are kept under the template's fingerprint", [os.path.basename(p) for p in kept] == ["page001.png", "page002.png", "page003.png"]
      and os.path.basename(os.path.dirname(kept[0])) == f"{NT.fingerprint(cfg, t)}_1_{TX.SPECIMEN}")
check("the strip shows Word's pages, labelled Exact", b.strip.exact and [p["label"] for p in b.strip.pages] == ["Page 1", "Page 2", "Page 3"]
      and b.kind.text() == TB.EXACT and b.kind.text().startswith("Exact, drawn by Word"))
check("... each page keeps its shape", b.strip.pages[0]["h"] > b.strip.pages[0]["w"] and b.strip.pages[1]["w"] > b.strip.pages[1]["h"]
      and abs(b.strip.pages[0]["w"] - 8.5) < 0.01 and abs(b.strip.pages[1]["h"] - 8.5) < 0.01)
check("... and it says how many pages Word drew", b.said.text() == "Word drew 3 page(s). They are kept until a pick changes." and b.b_exact.isEnabled(), b.said.text())
b.strip.grab()
check("the strip paints the pictures", True)
check("asked again: the kept pages are shown and Word is not started", b.draw_exact(runner=word, wait=True) == "shown" and len(calls) == 1)
check("the module answers from what is kept", TX.draw(cfg, t, runner=word)["cached"] is True and len(calls) == 1)
b.set_pick("layout", lay["id"])
check("a pick changes: the sample pages come back, labelled Approximate", not b.strip.exact and b.kind.text() == TB.SKETCH
      and [p["key"] for p in b.strip.pages][:2] == ["front", "body"])
b.set_pick("layout", "")
check("the saved picks again: Word's pages again, with no new drawing", b.strip.exact and len(calls) == 1)
b.set_pick("layout", lay["id"])
res = b.draw_exact(runner=word, wait=True)
t2 = NT.get(cfg, b.tid)
check("drawn again for the new picks: a new export and a new set of pictures", res == "done" and len(calls) == 2 and t2["made"]["version"] == 2
      and os.path.dirname(TX.cached(cfg, t2)[0]) != os.path.dirname(kept[0]))
b.reject()
b2 = pg.open_builder(t2["id"])
check("the builder opened later shows the kept pages at once", b2.strip.exact and b2.kind.text() == TB.EXACT and len(calls) == 2)
for p in TX.cached(cfg, t2):
    os.remove(p)
bad = b2.draw_exact(runner=lambda *a: json.dumps({"ok": False, "why": "-1"}), wait=True)
check("Word fails: the reason is said, the sample pages stay", bad == "done" and not b2.strip.exact and b2.kind.text() == TB.SKETCH
      and b2.said.text().startswith("Word could not lay out the preview."), b2.said.text())


def late(cmd, env, timeout):
    import subprocess
    raise subprocess.TimeoutExpired(cmd, timeout)


b2.draw_exact(runner=late, wait=True)
check("Word passes the time limit: a plain message", b2.said.text() == "Word took too long; the Word this preview started was ended." and b2.b_exact.isEnabled(), b2.said.text())
qpjobs.busy = lambda: True
check("another Word job is running: it waits its turn", b2.draw_exact(runner=word, wait=True) is None and b2.said.text().startswith("Word is busy with a job already.") and len(calls) == 2)
qpjobs.busy = lambda: False
import exactpreview as XP
XP.available = lambda: False
check("no Word on this PC: it says so and keeps the sample pages", b2.draw_exact() is None and "Word on this PC draws the exact pages" in b2.said.text())
res = b2.draw_exact(runner=word)
check("in the app it runs in the background: the button waits, the note says Word is drawing", res == "started" and not b2.b_exact.isEnabled()
      and b2.said.text() == TX.SLOW and b2.kind.text() == TX.SLOW)
import time
end = time.time() + 30
while qpjobs.RUNNING and time.time() < end:
    app.processEvents(); time.sleep(0.02)
app.processEvents()
check("... and its pages are shown when Word is done", b2.strip.exact and b2.b_exact.isEnabled() and len(calls) == 3 and qpjobs.RUNNING == [], b2.said.text())
root = os.path.join(cfg, TX.SUB)
for i in range(15):
    os.makedirs(os.path.join(root, f"old{i:02d}"), exist_ok=True)
    os.utime(os.path.join(root, f"old{i:02d}"), (1000 + i, 1000 + i))
gone = TX.prune(cfg, keep=12)
check("only the newest sets of pictures are kept", gone >= 3 and len(os.listdir(root)) == 12 and TX.cached(cfg, NT.get(cfg, b2.tid)))
check("an unreadable PDF gives no pictures", TX.pictures(os.path.join(tmp, "none.pdf"), os.path.join(tmp, "o")) == [])
b2.reject()
w.close()
n = sum(checks)
print(f"QT TPLEXACT 4440 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
