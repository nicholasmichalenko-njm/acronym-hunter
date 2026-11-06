"""3.68.0 offscreen: a moved effort is not opened empty and is found again from its new folder; Efforts > Open an effort
from its folder (a copy opens as a second effort); the marker file in the effort's folder; Template Studio's customer
form part (its file and marking, only for a Customer form) and Save for every effort of the effort type (what it
changes, the effort then following the shared plan); Apply in Word leaving a customer form alone; Production Standards
> What retiring this would lose. Fictional content (Kestrel)."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, effortrec as RR, workspace as W, deliverables as DL, office_pdf as OP, partplan as PP, effortrelink as ER
import banned as BN
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Old", "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
ws0 = W.Workspace(W.data_dir_for(LIST), "Kestrel")
DL.add(RR.Record(ws0.root), "Volume II Past Performance", "Volume")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
check("an effort opens where it is, and its folder gets the marker file", w.open_effort("Kestrel")
      and os.path.isfile(os.path.join(ED, ER.MARKER)))
w.close_effort()
# ---- the folder moves
NEWD = os.path.join(tmp, "New", "Kestrel"); os.makedirs(os.path.dirname(NEWD)); shutil.move(ED, NEWD)
check("a moved effort does not open, and nothing is made at its old place", w.open_effort("Kestrel") is False and not os.path.exists(ED))
w.find_folder = os.path.join(tmp, "New")
check("found again from the folder it is in now, and opened", w.open_effort("Kestrel") and w.effort_path == os.path.join(NEWD, "Kestrel_Effort_List.xlsx")
      and E.Registry(os.path.join(cfg, "efforts.json")).get("Kestrel")["path"] == os.path.join(NEWD, "Kestrel_Effort_List.xlsx"))
w.find_folder = None
w.close_effort()
COPY = os.path.join(tmp, "Copy", "Kestrel"); shutil.copytree(NEWD, COPY)
w.go("efforts"); app.processEvents()
name = w.efforts_page.open_folder(os.path.join(COPY, ER.MARKER))
check("Efforts > Open an effort from its folder (here its marker file): a copy beside the original opens as a second effort", name == "Kestrel (2)"
      and w.effort_name == "Kestrel (2)" and w.effort_path == os.path.join(COPY, "Kestrel_Effort_List.xlsx"))
w.close_effort()
from skqt.effortfind import open_from_folder
check("opening the same folder again opens the effort it already is", open_from_folder(w, NEWD) == "Kestrel" and w.effort_name == "Kestrel")
ws0 = w.ws
# ---- Template Studio: a customer form part, saved for the effort type
w.go("studio"); app.processEvents()
st = w.studio_page
st.vol.setCurrentText("Volume II Past Performance"); st.fill()
st.tabs.setCurrentIndex(1); app.processEvents()
st.ptab.selectRow(1); app.processEvents()
check("the form file and marking are only for a Customer form", not st.e_form.isEnabled())
pid = st.add_part("Past performance questionnaire", "Customer form")
st.ptab.selectRow([p["id"] for p in st.parts].index(pid)); app.processEvents()
check("... and open for one", st.e_form.isEnabled() and st.e_marking.isEnabled())
v = st.part_values(); v.update(form=os.path.join(tmp, "Kestrel PPQ.docx"), marking="Kestrel Source Selection", counts="Does not count")
st.save_part(v)
r = RR.Record(ws0.root)
p = next(x for x in PP.plan_of(r, "Volume II Past Performance") if x["id"] == pid)
check("the customer form part keeps its file and marking", p["marking"] == "Kestrel Source Selection" and p["form"].endswith("Kestrel PPQ.docx")
      and "kept as it is" in PP.says(p))
ch = st.where_choices()
check("where a save goes: this effort first, then the broader saves with what each changes", ch[0][0] == "effort" and "This effort only (Kestrel)" in ch[0][1]
      and any(k == "team" and "effort(s) on this PC follow it" in t for k, t in ch), ch)
eid, prof = st.ids()
st.save_part(st.part_values(), where="type")
check("saved for every effort of the effort type: kept by the profile, and this effort follows it",
      len(PP.shared_plan(cfg, eid, prof)) == 5 and not PP.own(RR.Record(ws0.root), "Volume II Past Performance")
      and st.ptab.rowCount() == 5 and any("shared by its effort type" in r_[2] for r_ in st.anatomy_now), [r_[2] for r_ in st.anatomy_now][-3:])
# ---- Production Standards: the nothing-lost report
dlg = w.prodstd_page.retire_report(modal=False)
check("What retiring this would lose: every section, the sections with no other editor first, and the links",
      dlg.table.rowCount() == 27 and dlg.table.item(0, 4).text() == "Only here" and dlg.links.rowCount() == 6
      and dlg.verdict.text().startswith("Not yet"))
dlg.close()

print(f"QT STUDIO 368 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
