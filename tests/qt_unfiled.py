"""2.91.0 Home and Unfiled work, offscreen: Home shows every effort as a card (soonest due first) with + Add an Effort as
the way to start one; Start without an effort opens Unfiled, where every tool works; a strip reminds while Unfiled holds
work; Add to an effort copies the chosen documents (every version, role and text) and the terms into another effort;
Make it an effort turns Unfiled into a named effort with its own folder (its documents, matrix and terms move with it)
and Unfiled starts empty, a copy kept in the new effort's backups."""
import datetime, os, sys, tempfile, time, shutil
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
import effort as E, effortrec as RR, workspace as W, unfiled as UF, docversions as DV, effortsummary as ES, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = A.CONFIG_DIR
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
check("Home is first in the menu", list(w.step_btns)[0] == "efforts" and w.step_btns["efforts"].text() == "All Efforts")
w.go("efforts"); app.processEvents()
hp = w.efforts_page
check("no efforts yet: Add an Effort, or start without one", hp.empty.isVisibleTo(w) and hp.add_btn.text() == "+ Add an Effort"
      and hp.start_btn.isVisibleTo(w) and not hp.uf_card.isVisibleTo(w))
base = os.path.join(A.DATA_DIR, "Efforts")
hp.add_effort({"name": "Heron", "path": os.path.join(base, "Heron", "Heron_Effort_List.xlsx")})
check("+ Add an Effort makes the effort with its folders and opens it", w.effort_name == "Heron"
      and os.path.isdir(os.path.join(base, "Heron", "Exports")) and w.stack.currentWidget() is w.home_page)
RR.Record(w.ws.root).set_due((datetime.datetime.now() + datetime.timedelta(days=30)).strftime("%Y-%m-%dT14:00"))
hp.add_effort({"name": "Osprey", "path": os.path.join(base, "Osprey", "Osprey_Effort_List.xlsx")})
r = RR.Record(w.ws.root); r.set_due((datetime.datetime.now() + datetime.timedelta(days=5)).strftime("%Y-%m-%dT14:00"))
r.add_task("Draft volume I", owner="A. Lee", due="2020-01-01"); r.add_note("Page limit for resumes?", question=True)
w.go("efforts"); app.processEvents()
names = [s["name"] for s in hp.rows]
check("Home: a card for each effort, the soonest due first", names == ["Osprey", "Heron"] and len(hp.cards) == 2, names)
o = hp.rows[0]
check("a card says how the effort stands without opening it", o["days"] in (4, 5) and o["tasks"] == 1 and o["late"] == 1
      and o["questions"] == 1 and o["stage"] == "Intake", o)
check("the effort open in this window is marked", "Osprey" == w.effort_name)
hp.open("Heron"); app.processEvents()
check("click a card: the effort opens on Effort Home", w.effort_name == "Heron" and w.stack.currentWidget() is w.home_page)
# Unfiled
w.go("efforts"); app.processEvents()
hp.open_unfiled(); app.processEvents()
check("Start without an effort opens Unfiled, in its own folder", w.effort_name == UF.NAME and UF.is_unfiled(w.efforts, w.effort_name)
      and w.effort_path == UF.list_path(A.DATA_DIR) and w.stack.currentWidget() is w.library_page)
check("the strip says it is unfiled work", w.unfiled_strip.isVisibleTo(w) and "Working unfiled" in w.unfiled_strip.text.text())
B = os.path.join(A.BASE_DIR, "test_samples", "rfp")
w.read_page.read([os.path.join(B, "Kestrel_RFP_Sections_C_L_M.docx")], os.path.join(os.path.dirname(w.effort_path), "Unfiled_Compliance_Matrix.xlsx"))
t = time.time()
while w.review is None and time.time() - t < 60:
    app.processEvents(); time.sleep(0.02)
w.save_now()
lib = DV.Library(w.ws.p("documents")).load()
cdoc = shutil.copy2(os.path.join(B, "Kestrel_RFP_Sections_C_L_M.docx"), w.efforts.get(UF.NAME)["customer_dir"])
lib.add(cdoc, [{"x": "The Offeror shall describe its approach.", "l": "p.1", "s": "L.3", "t": "Approach"}], doc_name="Kestrel RFP", initial="R", dtype="RFP")
L = E.EffortList(w.effort_path, UF.NAME).load(); L.add_or_update("CDRL", Definition="Contract Data Requirements List"); L.add_or_update("SOW", Definition="Statement of Work"); L.pending = True; L.save()
c = UF.counts(w.efforts)
check("tools work in Unfiled: Read RFP made a matrix and filed its document", c["matrix"] == 1 and c["documents"] >= 1 and c["terms"] == 2, c)
w.unfiled_strip.refresh()
check("the strip counts what Unfiled holds", "compliance matrix" in w.unfiled_strip.text.text() and w.unfiled_strip.mk.isEnabled())
w.go("efforts"); app.processEvents()
check("Home shows the Unfiled card while it holds work", hp.uf_card.isVisibleTo(w) and "2 terms" in hp.uf_text.text(), hp.uf_text.text())
check("Unfiled is not one of the effort cards", "Unfiled" not in hp.cards)
docs = UF.documents(w.efforts)
n = hp.add_unfiled_to({"target": "Heron", "docs": [d[0] for d in docs], "terms": True})
hl = DV.Library(os.path.join(W.data_dir_for(w.efforts.get("Heron")["path"]), "documents")).load()
check("Add to an effort: the documents join its Library with their text", n["documents"] == len(docs) and len(hl.all) == len(docs)
      and hl.text(hl.all[0]["versions"][0]))
check("customer documents are copied into its Customer Documents folder", all(os.path.dirname(hl.path_of(v)) == os.path.join(base, "Heron", "Customer Documents")
      for d in hl.all for v in d["versions"]))
check("its terms join the effort list", set(E.EffortList(w.efforts.get("Heron")["path"], "Heron").load().rows) >= {"CDRL", "SOW"})
n2 = hp.add_unfiled_to({"target": "Heron", "docs": [d[0] for d in docs], "terms": True})
check("adding again adds nothing twice", n2 == {"documents": 0, "versions": 0, "terms": 0}, n2)
# make it an effort
if w.effort_name != UF.NAME:
    w.open_effort(UF.NAME)
got = w.make_unfiled_effort("Kestrel Bid")
k = w.efforts.get("Kestrel Bid") or {}
check("Make it an effort: Unfiled becomes a named effort in its own folder", got == "Kestrel Bid" and w.effort_name == "Kestrel Bid"
      and k.get("path") == os.path.join(base, "Kestrel_Bid", "Kestrel_Bid_Effort_List.xlsx") and os.path.isfile(k["path"]), k)
check("its matrix, documents and terms came with it", w.review is not None and len(w.review.M.items) > 10
      and len(DV.Library(w.ws.p("documents")).load().all) == len(docs)
      and set(E.EffortList(k["path"], "Kestrel Bid").load().rows) >= {"CDRL", "SOW"})
check("its files point at its own folder", w.review.M.path.startswith(os.path.join(base, "Kestrel_Bid"))
      and all(DV.Library(w.ws.p("documents")).load().path_of(v).startswith(os.path.join(base, "Kestrel_Bid"))
              for d in DV.Library(w.ws.p("documents")).load().all for v in d["versions"]))
check("it has the effort folders", all(os.path.isdir(os.path.join(base, "Kestrel_Bid", n)) for n in ("Customer Documents", "Volumes", "Response Setup", "Exports")))
check("a copy of the old Unfiled is kept in its backups", any(f.startswith("Unfiled before") for f in os.listdir(os.path.join(w.ws.root, "backups"))))
check("Unfiled starts empty again", UF.empty(UF.counts(w.efforts)) and UF.is_unfiled(w.efforts, UF.NAME))
w.go("efforts"); app.processEvents()
check("Home: three efforts, no Unfiled card", sorted(hp.cards) == ["Heron", "Kestrel Bid", "Osprey"] and not hp.uf_card.isVisibleTo(w))
w.close()
n = sum(checks)
print(f"QT UNFILED PASS ({n}/{len(checks)})" if n == len(checks) else f"QT UNFILED FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
