"""3.51.0 the rest of the acronym toolset, offscreen: Acronym Finder's named lists (new, open, rename, add files, clear
no longer found, the one open last reopens); Full Text in its own window (read, save as one .txt and one per file);
another way of writing a term; the effort list's extras (export as chosen, for approval, import a volume's list,
volumes, activity, add to this PC's database); Submission Check's place window with This place is the first use.
Fictional content (the Kestrel set)."""
import os, sys, tempfile, time
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
import acrlists as AL, acrmore as AM
from skqt.acrtool import AcronymToolWindow
SAMPLES = os.path.join(A.BASE_DIR, "test_samples")
tech = os.path.join(SAMPLES, "Kestrel_Technical_Volume.docx")
others = sorted(os.path.join(SAMPLES, f) for f in os.listdir(SAMPLES) if f.lower().endswith(".docx") and f != os.path.basename(tech))


def wait(page):
    t0 = time.time()
    while page.worker is not None and time.time() - t0 < 300:
        app.processEvents(); time.sleep(0.05)


# ---- named lists
root = os.path.join(cfg, "acronym_tool")
check("a clean name: no folder characters, no ends", AL.clean(' Kestrel: draft / 2 ') == "Kestrel draft 2" and AL.clean("  ") == "")
tw = AcronymToolWindow(cfg); tw.show(); app.processEvents()
page = tw.page
check("the window opens on the first list", tw.host.name == AL.FIRST and tw.pick.currentText() == AL.FIRST and not tw.b_rename.isEnabled())
page.scan([tech]); wait(page)
n_first = len(page.session.results)
check("the first list scans as before", n_first > 0)
made = tw.make_list("Kestrel drafts")
check("New list: its own folder, opened, empty", made == "Kestrel drafts" and tw.host.name == made and os.path.isdir(os.path.join(root, "lists", made))
      and not page.session.results and tw.pick.count() == 2)
check("... a name already used is refused", tw.make_list("kestrel DRAFTS") == "")
if others:
    page.scan([others[0]]); wait(page)
second = set(page.session.results)
tw.open_list(AL.FIRST)
check("open the first list again: its own results came back", len(page.session.results) == n_first)
tw.open_list(made)
check("... and the other list's", set(page.session.results) == second)
tw.close()
tw = AcronymToolWindow(cfg); page = tw.page
check("the list open last reopens with the window", tw.host.name == made and set(page.session.results) == second)
check("Rename: the folder and the remembered list follow", tw.rename_list("Kestrel submittal") == "Kestrel submittal"
      and AL.last(root) == "Kestrel submittal" and tw.pick.currentText() == "Kestrel submittal")
before = set(page.session.last_scan.get("paths", [])) if page.session.last_scan else set()
tw.add_files([tech]); wait(page)
after = set(page.session.last_scan.get("paths", []))
check("Add files: the list's files again, with the new one", before <= after and tech in after, (before, after))
s = page.session
if s.effort is not None:
    pick = sorted(t for t in s.results if not t.startswith("[") and not s.results[t].get("excluded"))[0]
    s.add([pick])
    s.effort.rows[pick]["Scan status"] = "No longer found in Gone.docx"
    s.results.pop(pick, None)
    check("the terms no longer found", AL.gone_terms(s) == [pick], AL.gone_terms(s))
    check("Clear no longer found takes them off the list", tw.clear_gone() == [pick] and pick not in s.effort.rows)
else:
    check("the window keeps an acronym list", False)

# ---- another way of writing a term
s = page.session
terms = [t for t in sorted(s.results) if not t.startswith("[") and not s.results[t].get("excluded")]
prim, alt = terms[0], "K-ZQ"
s.results[alt] = {"category": "Acronym", "count": 1, "locations": [], "definitions": [], "selected_definition": "", "status": ""}
look = prim[0] + "-" + prim[1:] if len(prim) > 1 else prim + "-"
check("another way of writing: the same letters first", AM.alt_candidates(s, look)[:1] == [prim], AM.alt_candidates(s, look)[:3])
check("make it another way of writing the term", AM.make_alt(s, alt, prim) and alt in s.effort.alts(prim) and s.effort.alt_map().get(alt) == prim)
check("... and a term of its own again", AM.unmake_alt(s, alt) and alt not in s.effort.alts(prim) and not s.effort.alt_map().get(alt))

# ---- the effort list's extras
from skqt import effortlistextras as EX
from skqt.effortlistpage import EffortListPage
tw.host.acronym_page = page
tw.host.go = lambda *_a, **_k: None
lp = EffortListPage(tw.host)
L = lp.L
if prim not in L.rows:
    s.add([prim])
L.rows[prim]["Definition"] = "Kestrel Primary Term"; L.rows[prim]["Status"] = "Approved"
s._save_effort_list()
out = os.path.join(tmp, "list.csv")
EX.export_picker(lp, path=out, columns=["Term", "Definition", "Status"], statuses=["Approved"])
txt = open(out, encoding="utf-8-sig").read()
check("Export...: the columns and statuses chosen", txt.startswith("Term,Definition,Status") and f"{prim},Kestrel Primary Term,Approved" in txt, txt[:200])
others_t = [t for t in L.order if t != prim]
if others_t:
    L.rows[others_t[0]]["Status"] = "Proposed"
ap = EX.export_approvals(lp, path=os.path.join(tmp, "approve.xlsx"))
import openpyxl
ws = openpyxl.load_workbook(ap).active
hdr = [c.value for c in ws[1]]
check("For approval: the terms waiting, with an empty approver column", hdr[-1] == "SS Approver" and all(r[3] in ("Proposed", "Needs author") for r in ws.iter_rows(min_row=2, values_only=True)))
vol = os.path.join(tmp, "Kestrel Volume II.docx")
import volcheck as V
V.write_docx([("KXT", "Kestrel Transfer Test"), ("KQV", "Kestrel Quality Verification")], vol)
got = EX.import_volume(lp, path=vol)
check("Import a volume's list: in as Proposed", "KXT" in L.rows and L.rows["KXT"]["Status"] == "Proposed", got)
EX.assign_volumes(lp, terms=["KXT"], volumes=["Volume II"])
check("Volumes: the terms say which volumes use them", "Volume II" in L.rows["KXT"].get("Used in volumes", ""))
check("Export... for one volume: only its terms", [r[0] for r in EX.rows_for(L, ["Term"], volumes=["Volume II"])] == ["KXT"])
act = EX.activity(lp, run=False)
check("Activity: what changed, by whom and when", "KXT" in act and "Volume II" in act, act[:300])
db = EX.to_database(lp, terms=[prim], run=False)
check("Add to this PC's database: the chosen terms", db and db["added"] + db["updated"] + db["same"] == 1 and any(r[0] == prim for r in A.read_db_rows()))

# ---- Submission Check's place window
from skqt.firstusetool import PlaceDialog
s.results[prim].setdefault("locations", [])
loc = (s.results[prim].get("locations") or ["Kestrel_Technical_Volume.docx (para 1-3)"])[0]
row = {"term": prim, "volume": loc.split(" (")[0], "loc": loc, "state": "Used before it is defined"}
called = []
s.qa_rebuild = lambda: {"first_use": [], "rebuilt": True}
pdlg = PlaceDialog(None, s, row, {os.path.basename(tech): tech}, on_set=called.append)
rep = pdlg.set_here()
check("This place is the first use: kept for the term and the check rebuilt", rep and rep.get("rebuilt") and called
      and s.first_use_set.get(prim), s.first_use_set)
tw.close()

# ---- Full Text
from skqt import fulltexttool as FT
check("Acronym Finder's files: the list it last had open", tech in FT.last_scan_files(cfg))
ft = FT.open_tool(cfg)
check("Full Text keeps only files it can read", ft.set_files([tech, os.path.join(tmp, "x.zzz")]) == [tech])
texts = ft.go(wait=True)
body = texts.get(tech, "")
check("Read all the text: the file's words", len(body) > 200 and "Kestrel" in body, body[:200])
one = ft.save_one(os.path.join(tmp, "all.txt"))
check("Save as one .txt", one and open(one, encoding="utf-8").read() == ft.all_text())
each = os.path.join(tmp, "each"); os.makedirs(each)
check("Save one .txt per file, named after each", ft.save_each(each) == 1 and os.path.isfile(os.path.join(each, "Kestrel_Technical_Volume_fulltext.txt")))
check("the markings warning is on the window", any("classification and markings" in l.text() for l in ft.findChildren(type(ft.lbl))))
ft.close()

n = sum(checks)
print(f"QT ACRONYMS 3.51 MORE {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
