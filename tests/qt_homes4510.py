"""4.51.0 Every document gets a named home, offscreen. With nothing open: every menu entry for an effort page opens its
page and no Unfiled is made or opened; the Working on box, All Efforts and Quick tools show no Unfiled. A file dropped on
Quick tools goes where it is told in the same step: a new effort or a new program made from a name alone, or another
home (switched to); the open home is listed first and picked; a bad new name is refused with its reason and nothing is
made; a use only an effort has lists no program; a tool beside any home asks nothing and opens no home. Then an Unfiled
that holds work from before: it is shown as Unfiled, from before (Quick tools, the strip, the window title, the top of
the menu); the offer at start is due once; Not now changes no file and is not due again; Name it as a program makes a
program holding its document and term and Unfiled is empty and hidden; in a second data folder Name it as an effort does
the same as an effort. Fictional (Kestrel, Heron, Osprey)."""
import os, shutil, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
A.CONFIG_DIR = os.path.join(A.DATA_DIR, "config"); os.makedirs(A.CONFIG_DIR, exist_ok=True)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import docversions as DV, effort as E, homes as HM, programs as PG, unfiled as UF, workspace as W, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D, homeask as HA, toolshome as TH, unfiledview as UV
from skqt import mainwin as MW

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


app = QApplication([]); D.apply(app)


def pump():
    for _ in range(5):
        app.processEvents(); time.sleep(0.01)


def window():
    w = MW.MainWindow(app, A.CONFIG_DIR, A.APP_VERSION); w.resize(1500, 950); w.show(); pump()
    return w


w = window()
statuses = []
_status = w.status
w.status = lambda t, *a, **k: (statuses.append(t), _status(t, *a, **k))
base = os.path.join(A.DATA_DIR, "Efforts")
w.efforts_page.add_effort({"name": "Heron", "path": os.path.join(base, "Heron", "Heron_Effort_List.xlsx")})
w.close_effort(); pump()
docx = os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx")
check("with nothing open, no Unfiled yet", w.ws is None and w.efforts.get(UF.NAME) is None)

# ---- 1. nothing open: the menu, the box, All Efforts, Quick tools
failed = []
for key in [k for k, _t in MW.RAIL[0][1]]:
    try:
        w.rail_go(key); pump()
        if w.ws is not None or w.efforts.get(UF.NAME) is not None:
            failed.append((key, "opened a home"))
    except Exception as e:  # noqa: BLE001  a page that fails with nothing open is reported, not hidden
        failed.append((key, type(e).__name__ + ": " + str(e)[:120]))
check("every menu entry for an effort page opens with nothing open, and no Unfiled is made or opened", not failed, failed)
w.rail_go("library"); pump()
check("... it goes to the page that says no effort is open (4.60.0), and none is opened", w.stack.currentWidget() is w.noeffort_page and w.ws is None)
w.fill_efforts()
check("the Working on box has no Unfiled", w.effort_box.findText(UF.NAME) < 0)
w.go("efforts"); pump()
hp = w.efforts_page
check("All Efforts has no Start without an effort button and no Unfiled card", not hasattr(hp, "start_btn") and not hp.uf_card.isVisibleTo(w)
      and not any("Unfiled" in b.text() for b in hp.findChildren(type(hp.add_btn)) if b.isVisibleTo(w)))
w.go("tools"); pump()
tl = w.tools_page
tl.refresh()
check("Quick tools shows no Unfiled block", not tl.uf_card.isVisibleTo(w))
check("the use labels name no Unfiled and no 'what I am working on'", not any("Unfiled" in t or "working on" in t for _k, t, _x in TH.USES)
      and dict((k, t) for k, t, _x in TH.USES)["library"] == "Add to Documents, in an effort or a program")
check("working_on() no longer answers Unfiled for nothing open", tl.working_on() == "")

# ---- 2. the where-question, in the tool's own step
added = []
w.library_page.add = lambda paths=None, **k: added.append((w.effort_name, list(paths or []))) or 1
got = tl.files_in([docx], use="library", home=("new_effort", "Kestrel bid"))
info = w.efforts.get("Kestrel bid") or {}
check("a new effort from a name alone: made, opened, and the file goes to its Documents", got == "library" and w.effort_name == "Kestrel bid"
      and info.get("path") and not info.get("program") and added == [("Kestrel bid", [docx])] and w.stack.currentWidget() is w.library_page,
      (got, w.effort_name, info, added))
check("... in its own folder in Efforts, with its folders made", os.path.isfile(info.get("path", "")) and os.path.isdir(info.get("customer_dir", "")))
got = tl.files_in([docx], use="library", home=("new_program", "Osprey"))
check("a new program from a name alone: made, opened, the file goes there", got == "library" and w.effort_name == "Osprey"
      and PG.is_program(w.efforts, "Osprey") and added[-1] == ("Osprey", [docx]), (got, w.effort_name, added))
wb = HA.WhereBox(w.efforts, w.effort_name, [docx])
check("WhereBox lists the open home first and picks it", wb.combo.itemData(0) == ("home", "Osprey") and wb.combo.currentIndex() == 0
      and wb.combo.itemText(0) == "Osprey (open now)" and wb.picked() == ("home", "Osprey") and wb.ok() and not wb.name.isVisibleTo(wb))
w.open_effort("Kestrel bid"); pump()
wb = HA.WhereBox(w.efforts, w.effort_name, [docx])
labels = [wb.combo.itemText(i) for i in range(wb.combo.count())]
check("... an open effort too, then the efforts, the programs and the two new ones",
      labels == ["Kestrel bid (open now)", "Heron", "Osprey (program)", "A new effort", "A new program"], labels)
wb.combo.setCurrentIndex(labels.index("A new effort"))
check("a new one shows its name, filled in from the file's name", wb.name.isVisibleTo(wb) and wb.name.text() == "Kestrel Technical Volume"
      and wb.picked() == ("new_effort", "Kestrel Technical Volume") and wb.ok())
wb.name.setText("heron")
check("... a name in use cannot be used: the reason shows and ok() is False", not wb.ok() and "already has that name" in wb.reason.text())
got = tl.files_in([docx], use="library", home=("home", "Heron"))
check("another home: switched to it and the file goes there", got == "library" and w.effort_name == "Heron" and added[-1] == ("Heron", [docx]))
before = sorted(w.efforts.names()); n_added = len(added)
got = tl.files_in([docx], use="library", home=("new_effort", "kestrel BID"))
check("a bad new name is refused with the reason, and nothing is made", got is None and sorted(w.efforts.names()) == before
      and len(added) == n_added and w.effort_name == "Heron" and statuses and "already has that name" in statuses[-1], statuses[-1:])
got = tl.files_in([docx], use="copyreview", home=("home", "Osprey"))
check("a use only an effort has refuses a program, and nothing runs", got is None and w.effort_name == "Heron" and "in an effort" in statuses[-1])
d = TH.UseDialog(tl, [docx], w)
keys = [d.list.item(i).data(0x0100) for i in range(d.list.count())]
d.list.setCurrentRow(keys.index("library"))
check("the dialog asks where for a use that works in a home, with programs", not d.where.isHidden())
in_lib = [d.where.combo.itemText(i) for i in range(d.where.combo.count())]
d.list.setCurrentRow(keys.index("copyreview"))
in_cr = [d.where.combo.itemText(i) for i in range(d.where.combo.count())]
check("... Copy review (only an effort has it) lists no program", "Osprey (program)" in in_lib and "A new program" in in_lib
      and not any("program" in x for x in in_cr) and in_cr[0] == "Heron (open now)", (in_lib, in_cr))
d.where.combo.setCurrentIndex(in_cr.index("A new effort")); d.where.name.setText("Heron")
check("... OK waits while the new name cannot be used", not d.ok_btn.isEnabled())
d.where.name.setText("Plover")
check("... and is ready with a name that can", d.ok_btn.isEnabled() and d.home() == ("new_effort", "Plover"))
d.list.setCurrentRow(keys.index("fulltext"))
check("... a tool beside any home asks nothing (the where box hides, OK is ready)", d.where.isHidden() and d.ok_btn.isEnabled() and d.home() is None)
d.close()
w.close_effort(); pump()
import skqt.fulltexttool as FT, skqt.firstusetool as FU
opened = []
FT.open_tool = lambda cfg, paths: opened.append(("fulltext", list(paths))) or "window"
FU.open_tool = lambda cfg, paths: opened.append(("firstuse", list(paths))) or "window"
got = tl.files_in([docx], use="fulltext")
got2 = tl.files_in([docx], use="firstuse")
check("a tool beside any home asks nothing and opens no home", got == "fulltext" and got2 == "firstuse" and w.ws is None
      and opened == [("fulltext", [docx]), ("firstuse", [docx])] and w.efforts.get(UF.NAME) is None)
got = tl.files_in([docx], use="library")
check("a use that needs a home, with none given and none open, stops", got is None and w.ws is None and w.efforts.get(UF.NAME) is None)


# ---- 3. an Unfiled that holds work from before
def fill_unfiled(reg):
    UF.ensure(reg, A.DATA_DIR)
    info = reg.get(UF.NAME)
    os.makedirs(info["customer_dir"], exist_ok=True)
    p = os.path.join(info["customer_dir"], "Kestrel_Technical_Volume.docx")
    shutil.copy2(docx, p)
    lib = DV.Library(os.path.join(W.data_dir_for(info["path"]), "documents")).load()
    lib.add(p, [{"text": "The Kestrel bus carries the payload."}], doc_name="Kestrel Technical Volume")
    L = E.EffortList(info["path"], UF.NAME).load()
    L.add_or_update("KBS", Definition="Kestrel Bus System")
    L.pending = True; L.save()
    return os.path.dirname(info["path"])


def listing(folder):
    out = []
    for r, _ds, fs in os.walk(folder):
        for f in fs:
            p = os.path.join(r, f)
            out.append((os.path.relpath(p, folder), os.path.getsize(p), os.path.getmtime(p)))
    return sorted(out)


uf_folder = fill_unfiled(w.efforts)
check("Unfiled holds work: a document and a term", HM.holds_work(w.efforts) and UF.counts(w.efforts)["documents"] == 1
      and UF.counts(w.efforts)["terms"] == 1, UF.counts(w.efforts))
w.fill_efforts(); w.go("tools"); tl.refresh(); pump()
check("Quick tools shows it, as Unfiled, from before", tl.uf_card.isVisibleTo(w) and tl.uf_card.title.text() == "Unfiled, from before"
      and any("Kestrel Technical Volume" in tl.uf_list.item(i).text() for i in range(tl.uf_list.count())))
check("... its menu leads with Name it...", [a.text() for a in tl.uf_file.menu().actions()][0] == "Name it..." and tl.uf_make.isEnabled())
check("the Working on box has it while it holds work", w.effort_box.findText(UF.NAME) >= 0)
check("All Efforts' card reads Unfiled, from before with Name it... (kept hidden, 4.27.2)", hp.uf_card.title.text() == "Unfiled, from before"
      and hp.mk_btn.text() == "Name it..." and not hp.uf_card.isVisibleTo(w))
w.work_on(UF.NAME); pump()
check("an existing Unfiled still opens", w.effort_name == UF.NAME and w.ws is not None)
st = w.unfiled_strip.text.text()
check("the strip: Unfiled, from before, what it holds, Name it... first", st.startswith("<b>Unfiled, from before.</b> Holds 1 document")
      and "tool" not in st and w.unfiled_strip.mk.text() == "Name it..." and w.unfiled_strip.mk.isEnabled(), st)
check("the window title and the top of the menu read Unfiled, from before", w.windowTitle().startswith("Unfiled, from before: ")
      and w.rail_effort.name.text().startswith("Unfiled, from before"), (w.windowTitle(), w.rail_effort.name.text()))
w.close_effort(); pump()
check("the offer at start is due", HM.start_offer_due(w.efforts))
was = listing(uf_folder)
check("Not now: kept as later, no file changed, not due again", UV.offer_at_start(w, answer=False) == "later"
      and listing(uf_folder) == was and HM.offer_state(w.efforts) == "later" and not HM.start_offer_due(w.efforts)
      and UV.offer_at_start(w, answer=False) is None and HM.holds_work(w.efforts))
got = UV.name_it(w, kind="program", name="Heron")
check("Name it refuses a name in use and moves nothing", got is None and listing(uf_folder) == was and HM.holds_work(w.efforts))
got = UV.name_it(w, kind="program", name="Kestrel archive")
info = w.efforts.get("Kestrel archive") or {}
root = os.path.dirname(info.get("path", ""))
check("Name it as a program: a program in Programs, open", got == "Kestrel archive" and PG.is_program(w.efforts, got) and w.effort_name == got
      and os.path.normcase(os.path.dirname(root)) == os.path.normcase(PG.programs_dir(A.DATA_DIR)) and info["path"].endswith(PG.LIST_TAIL), (info, statuses[-3:]))
s = PG.summary(w.efforts, got)
terms = E.EffortList(info["path"]).load().rows
check("... holding the document and the term", s["documents"] == 1 and "KBS" in terms, (s, list(terms)))
docs = os.path.join(root, PG.DOCS)
check("... the document in Program Documents, no Customer Documents folder", os.path.isfile(os.path.join(docs, "Kestrel_Technical_Volume.docx"))
      and not os.path.isdir(os.path.join(root, "Customer Documents")) and info.get("customer_dir") == docs, sorted(os.listdir(root)))
print("   the program's folder holds:", sorted(os.listdir(root)))
lib = DV.Library(os.path.join(W.data_dir_for(info["path"]), "documents")).load()
vp = lib.path_of(lib.all[0]["versions"][0])
check("... the document's version points at the file in Program Documents", vp and os.path.normcase(os.path.dirname(vp)) == os.path.normcase(docs), vp)
check("Unfiled is empty afterwards and no longer shown", UF.empty(UF.counts(w.efforts)) and not HM.holds_work(w.efforts)
      and HM.offer_state(w.efforts) == "named")
w.fill_efforts(); w.go("tools"); tl.refresh(); pump()
check("... not on Quick tools nor in the Working on box", not tl.uf_card.isVisibleTo(w) and w.effort_box.findText(UF.NAME) < 0)
w.close_effort(); pump()
w.close()

# ---- 4. a second data folder: Name it as an effort
tmp2 = tempfile.mkdtemp()
A.DATA_DIR = os.path.join(tmp2, "Stationkeeper Data")
A.CONFIG_DIR = os.path.join(A.DATA_DIR, "config"); os.makedirs(A.CONFIG_DIR, exist_ok=True)
w2 = window()
uf2 = fill_unfiled(w2.efforts)
check("second folder: Unfiled holds work and the offer is due", HM.start_offer_due(w2.efforts) and uf2.startswith(tmp2))
got = UV.offer_at_start(w2, answer=("effort", "Heron bid"))
info = w2.efforts.get("Heron bid") or {}
check("Name it as an effort (from the start offer): an effort in Efforts, open", got == "Heron bid" and not PG.is_program(w2.efforts, got)
      and w2.effort_name == got and os.path.normcase(info.get("path", "")).startswith(os.path.normcase(os.path.join(A.DATA_DIR, "Efforts"))), info)
s = PG.summary(w2.efforts, got)
check("... holding the document and the term", s["documents"] == 1 and "KBS" in E.EffortList(info["path"]).load().rows)
check("... Unfiled is empty and no longer shown", UF.empty(UF.counts(w2.efforts)) and not HM.holds_work(w2.efforts)
      and HM.offer_state(w2.efforts) == "named")
check("... a copy of the old Unfiled is kept in its backups", any(f.startswith("Unfiled before") for f in os.listdir(os.path.join(w2.ws.root, "backups"))))
w2.close_effort(); w2.close()

n = sum(checks)
print(f"QT HOMES 4510 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)   # D1: a bare os._exit crashed while Windows unloaded Qt
