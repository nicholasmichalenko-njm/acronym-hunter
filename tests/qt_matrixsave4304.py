"""4.30.4: the matrix's own save, two seconds after a change, is written on another thread (it froze the window for the
length of the save: 12 seconds with 4,200 pieces). It is "not saved yet" until it is on disk; a change made while it is
written is saved by the next one; Save now and closing wait for it. Margin labels and boxes that read the same are left
as they are. Fictional effort."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen"); os.environ["AH_TEST"] = "1"
tmp = tempfile.mkdtemp(); os.environ.setdefault("SK_DATA_DIR", os.path.join(tmp, "d"))
import app_gui as A, compliance as C, effort as E, workspace as W, pdfmini
from PySide6.QtWidgets import QApplication
from skqt import design as theme, matrixsave as MS
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Osprey"); os.makedirs(EDIR)
pages = [[f"{p + 1}.0 SECTION {p + 1}"] + [f"The Offeror shall describe its approach to item {p}-{k} within {10 + k} days." for k in range(6)] for p in range(6)]
PDF = os.path.join(tmp, "Osprey_SOW.pdf"); pdfmini.write(PDF, pages, size=9)
LIST = os.path.join(EDIR, "Osprey_Effort_List.xlsx")
L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Osprey").set("outline_text", "Volume I Technical\n1.1 Technical Approach")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Osprey")
OUT = os.path.join(EDIR, "Osprey_Compliance_Matrix.xlsx")
w.read_page.read([PDF], OUT)
check("read", wait(lambda: w.review is not None and not w.read_page.running()))
w.save_now()
w.go("assign"); app.processEvents()
pg, M = w.assign_page, w.review.M
ids = [it["id"] for it in M.items if it["text"].startswith("The Offeror")]
pg.select(ids[0]); app.processEvents(); pg.type_chips["requirement"].click(); app.processEvents()
check("a decision leaves the matrix not saved yet, and the timer running", M.pending and w.save_timer.isActive())
m0 = os.path.getmtime(OUT)
check("4.30.4: by default the timer's save writes on the window's thread and says so", MS.THREADED is False and MS.soon(w) is None and not M.pending
      and os.path.getmtime(OUT) > m0 and {it["id"]: it["decision"] for it in C.Matrix(OUT).load().items}[ids[0]] == "Keep")
MS.THREADED = True                                       # the other-thread path stays tested for when it is turned back on
pg.select(ids[5]); app.processEvents(); pg.type_chips["requirement"].click(); app.processEvents()
ids[0] = ids[5]
m0 = os.path.getmtime(OUT)
th = MS.soon(w)
check("the timer's save starts a write on another thread and says so", th is not None and w.statusBar().currentMessage() == MS.SAVING)
check("... the matrix is still not saved yet while it is written", M.pending)
pg.select(ids[1]); app.processEvents(); pg.type_chips["requirement"].click(); app.processEvents()      # a change while it is written
check("the write finishes", wait(lambda: not th.isRunning(), 30)); app.processEvents()
on_disk = {it["id"]: it["decision"] for it in C.Matrix(OUT).load().items}
check("the first decision is on disk", os.path.getmtime(OUT) > m0 and on_disk[ids[0]] == "Keep")
check("what follows the write runs on the window's thread, never the writing one", MS.DONE_ON is True, MS.DONE_ON)
check("the change made meanwhile keeps the matrix not saved, and the timer runs again", M.pending and w.save_timer.isActive())
rp = os.path.join(w.ws.root, "recovery")
has_copy = lambda: (w.safety.settle(), os.path.isdir(rp) and any(f.startswith("matrix_") for f in os.listdir(rp)))[1]    # noqa: E731
check("... and its recovery copy is written and kept, not cleared by the earlier save", wait(has_copy, 6))
th2 = MS.soon(w)
w.save_now()                                             # Save now while a write is under way
check("Save now waits for the write and leaves everything on disk", not M.pending and {it["id"]: it["decision"] for it in C.Matrix(OUT).load().items}[ids[1]] == "Keep"
      and (th2 is None or not th2.isRunning()))
check("... and a save clears the recovery copy", not any(f.startswith("matrix_") for f in os.listdir(rp)))
check("with nothing changed the timer's save does nothing", MS.soon(w) is None)

# ---- the page: what reads the same is left as it is
labs = list(pg.labels)
pg.select(ids[3]); app.processEvents()
check("selecting another piece keeps the margin labels that read the same", len(labs) >= 10 and sum(1 for x in labs if any(x is y for y in pg.labels)) >= len(labs) - 4,      # the ones beside the selection move a hair
      ([(x.text(), x.pos().y()) for x in labs], [(x.text(), x.pos().y()) for x in pg.labels]))
box = pg.view.boxes[ids[0]]
calls = []
real = box.setPen
box.setPen = lambda *a: (calls.append(1), real(*a))
pg.restyle(); app.processEvents()
check("... and a box that looks the same is not drawn again", calls == [])
pg.select(ids[0]); app.processEvents()
check("... one whose look changes is", calls != [] and box.current)
pg.type_chips["requirement"].click(); app.processEvents()
check("a decision taken back takes its label out of the margin", len(pg.labels) == len(labs) - 1 and M.items[[i["id"] for i in M.items].index(ids[0])].get("decision") != "Keep", (len(pg.labels), len(labs)))
pg.do_undo(); app.processEvents()
check("Undo draws the page again with the label back", len(pg.labels) == len(labs))
w.close_effort()
check("closing the effort leaves nothing unsaved and no write running", getattr(w, "_matrix_saver", None) is None or not w._matrix_saver.isRunning())
n = sum(checks)
print(f"QT MATRIXSAVE 4304 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
w.close()
sys.exit(0 if n == len(checks) else 1)
