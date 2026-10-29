"""2.82.0 moving between pages is fast with many documents, offscreen: opening an effort works out in the background
what Documents, Requirements, Effort home and the dashboard would otherwise work out on every visit (what changed
between versions, the submission requirements each version sets, the customer folder's fingerprints); after that every
page opens within budget, and a second visit is instant; the kept results follow every change: a new version, a renamed
document and an edited file are worked out again, never shown stale; results kept on disk make the next start fast too."""
import os, random, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
A.LOG_DIR = os.path.join(tmp, "logs")
import effort as E, workspace as W, docversions as DV, subreq as SR
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Heron"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Heron_Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Heron")
lib = DV.Library(ws.p("documents")).load()
random.seed(7)
words = "the contractor shall provide deliver maintain thermal schedule report monthly within days".split()
for d in range(30):
    doc = None
    base = [{"x": " ".join(random.choice(words) for _ in range(14)) + ".", "l": f"{d}.{i}"} for i in range(600)]
    base[5]["x"] = f"Volume {d} shall not exceed {20 + d} pages."
    for v in range(3):
        p = os.path.join(CD, f"doc{d}_v{v}.pdf"); open(p, "wb").write(os.urandom(300_000))
        sents = [dict(s) for s in base]
        for i in random.sample(range(600), 30):
            sents[i]["x"] = sents[i]["x"].replace("shall", "must")
        doc, _v = lib.add(p, sents, doc_id=doc["id"] if doc else None, doc_name=f"Doc {d}")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Heron")
check("opening an effort starts the background work", getattr(w, "_warm_thread", None) is not None)
w._warm_thread.join(120)
slow = []
for page in list(w.pages):
    t = time.time(); w.go(page); app.processEvents(); dt = time.time() - t
    if dt > 1.0:
        slow.append((page, round(dt, 2)))
check("after it, every page opens within a second (90 versions)", not slow, slow)
times = {}
for page in ("docs", "requirements", "home", "dashboard"):
    t = time.time(); w.go(page); app.processEvents(); times[page] = round(time.time() - t, 3)
check("a second visit to Documents, Requirements, Effort home and the dashboard is instant", max(times.values()) < 0.3, times)
reqs = {r["subject"]: r for r in w.requirements_page.ctx.reg.rows()}
check("requirements are right", any("pages" in r["value"] for r in reqs.values()), list(reqs)[:4])
# kept results follow changes
d0 = w.docs_page.ctx.lib.docs[0]
p = os.path.join(CD, "doc0_v3.pdf"); open(p, "wb").write(b"new version")
sents = [dict(s) for s in w.docs_page.ctx.lib.text(d0["versions"][-1])]
sents[5]["x"] = "Volume 0 shall not exceed 99 pages."
lib2 = DV.Library(ws.p("documents")).load()
lib2.add(p, sents, doc_id=d0["id"])
w.go("requirements"); app.processEvents()
vals = [h["value"] for r in w.requirements_page.ctx.reg.rows() for h in r["history"] if "99" in h["value"]]
check("a new version: the requirements are worked out again, not shown stale", vals, vals)
w.go("docs"); app.processEvents()
top = next(w.docs_page.tree.topLevelItem(i) for i in range(w.docs_page.tree.topLevelItemCount()) if w.docs_page.tree.topLevelItem(i).text(0) == d0["name"])
check("and Documents shows what changed in it", top.childCount() == 4 and top.child(3).text(6) != "", top.child(3).text(6) if top.childCount() > 3 else "")
lib3 = DV.Library(ws.p("documents")).load(); lib3.rename(doc_id=d0["id"], name="Statement of Work")
w.go("requirements"); app.processEvents()
check("a renamed document: the requirements show the new name", any(h["doc"] == "Statement of Work" for r in w.requirements_page.ctx.reg.rows()
                                                                            for h in r["history"]))
open(os.path.join(CD, "doc1_v0.pdf"), "ab").write(b"edited")
time.sleep(0.05)
w.go("docs"); app.processEvents()
check("an edited file in the customer folder is fingerprinted again (offered to add)", "(1)" in w.docs_page.b_folder.text() or "(2)" in w.docs_page.b_folder.text(),
      w.docs_page.b_folder.text())
# results kept on disk
SR._FOUND.clear(); SR._BUILT.clear(); DV._CHANGE.clear()
found = os.path.join(ws.p("documents"), "found")
check("results are kept on disk for the next start", os.path.isdir(found) and len(os.listdir(found)) >= 90)
t = time.time(); w.go("home"); app.processEvents(); w.go("requirements"); app.processEvents(); dt = time.time() - t
check("a fresh start reads them back quickly", dt < 1.5, round(dt, 2))
w.close()
n = sum(checks)
print(f"QT SPEED PASS ({n}/{len(checks)})" if n == len(checks) else f"QT SPEED FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
