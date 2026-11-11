"""4.5.0 offscreen: Place, as designed, and the loose ends (claude/stationkeeper-shred-place-plan-4.5.md, steps 5 to 7).
Place shows no type chips, capture bar or outline editing; its pane says where the piece goes, with Place it (Enter),
Another section... and Leave it out..., and how many are not placed; rules, dates and information are not placed;
Outline has no Not placed yet list. The loose ends: Changed by <version> on the pane; lines set aside as running headers
in Suspects; a prescribed outline marked as the customer's with its volumes' page limits. Fictional (an Osprey L)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import compliance as C
import effort as E, workspace as W, pdfmini
import shredtypes as ST
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Osprey"); os.makedirs(EDIR)
LINES = ["L.2 PROPOSAL SUBMISSION",
         "Proposals shall be submitted electronically no later than 2:00 p.m. Eastern Time on December 15, 2026.",
         "The Offeror shall describe its Integrated Master Schedule (IMS) approach.",
         "Text shall be no smaller than 12-point Times New Roman with 1-inch margins.",
         "The contractor shall deliver a monthly status report.",
         "The Government will evaluate the realism of the schedule.",
         "The Government intends to award a single contract."]
PDF = os.path.join(tmp, "Section_L.pdf"); pdfmini.write(PDF, [["OSPREY RFP FA0000-26-R-0001 SECTION L"] + LINES[:4], ["OSPREY RFP FA0000-26-R-0001 SECTION L"] + LINES[4:]], size=9)
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
check("extracted", wait(lambda: w.review is not None and not w.read_page.running()))
import homesuggest as HS, reshred as RS, outlinemarks as OM, setupdoc as SD
import skqt.placepane as PP, skqt.fixtext as FX
M = w.review.M
by = lambda s: next(it for it in M.items if s in it["text"])          # noqa: E731
vis = lambda x: x is not None and x.isVisibleTo(w) and x.isVisible()   # noqa: E731
pg = w.assign_page
w.go("assign"); app.processEvents()
pg.select(by("Integrated Master Schedule")["id"]); app.processEvents()
pg.type_chips["instruction"].click(); app.processEvents()
pg.select(by("monthly status report")["id"]); app.processEvents()
pg.type_chips["deliverable"].click(); app.processEvents()
pg.select(by("12-point")["id"]); app.processEvents()
pg.type_chips["rule"].click(); app.processEvents()
w.go("place"); app.processEvents()
check("Place: its focus, no Shred controls", pg.focus == "place" and not vis(pg.decide_area) and not vis(pg.shred_main)
      and not vis(pg.vol_add_btn) and not any(vis(x) for x in pg.outline_rows))
ims = by("Integrated Master Schedule")
pg.select(ims["id"]); app.processEvents()
check("... no type chips on Place", not vis(getattr(pg, "type_chips", {}).get("requirement")))
labs = pg.R.labels()
pg.set_target(labs[-1]); app.processEvents()
pg.select(ims["id"]); app.processEvents()
left0 = len(HS.left(M)["unplaced"])
check("the pane: Place it (Enter), Another section..., Leave it out...", vis(pg.place_btn) and vis(pg.other_btn) and vis(pg.leave_btn)
      and pg.place_to == labs[-1] and pg.place_left.text().startswith("Not placed yet: "), getattr(pg, "place_to", None))
import skqt.shredfocus as SF
SF.enter(pg); app.processEvents()
ims = by("Integrated Master Schedule")
check("Enter places it", ims.get("map") == labs[-1] and len(HS.left(M)["unplaced"]) == left0 - 1, (ims.get("map"), left0))
rep = by("monthly status report")
pg.select(rep["id"]); app.processEvents()
PP.place_it(pg, labs[0]); app.processEvents()
check("Another section... places it there", by("monthly status report").get("map") == labs[0])
pg.select(by("12-point")["id"]); app.processEvents()
check("a rule is not placed: the pane says so", pg.place_btn is None)
q = RS.Queue(w.ws.root).load(); q.add("pk1", "k1", "dL", "Amendment 1", "old", "new", target=ims["id"])
pg.select(ims["id"]); app.processEvents()
check("Changed by <version> on the pane", vis(pg.flag_label) and "Changed by Amendment 1" in pg.flag_label.text())
sus = [x for x in FX.suspects(pg) if x[0] == "header"]
check("Suspects lists the running header set aside", sus and "OSPREY RFP" in sus[0][1]["text"] and "2 pages" in sus[0][2], sus)
w.go("outline"); app.processEvents()
b = w.setups_page.builder
check("Outline has no Not placed yet list (Place has it)", not vis(b.unp_list) and not vis(b.unp_btn) and b.place_btn.text() == "Put in the section")
M.items.append({"id": "x1", "text": "Volume I Technical shall not exceed 25 pages.", "file": "Section_L.pdf", "decision": ""})
check("the solicitation's page limits", OM.limits(M).get(1) == 25)
SD.setup_of(M).pop("outline_from", None); SD.setup_of(M).pop("prescribed_marked", None)
w.outline_page.refresh(); app.processEvents()
check("4.6.0: an outline started from the customer's headings still asks, once, whether the solicitation prescribes it",
      bool(M.outline) and vis(w.outline_page.started) and not vis(w.outline_page.start))
w.outline_page.answer("prescribed"); app.processEvents()
check("... Yes keeps the answer and the question goes", SD.setup_of(M).get("outline_from") == "prescribed" and not vis(w.outline_page.started))
import pagebudget as PB, compliance as C
vol = next(o for o in M.outline if "Volume" in C.outline_label(o))
check("a prescribed outline: the customer's sections, the volume's page limit", all(o.get("by") == "customer" for o in M.outline)
      and PB.pages(M, C.outline_label(vol)) == 25 and "customer's" in w.outline_page.said.text(), w.outline_page.said.text())
M.save(); M2 = C.Matrix(M.path); M2.load()
check("... kept in the workbook", all(o.get("by") == "customer" for o in M2.outline))
w.close()
n = sum(checks)
print(f"QT PLACEFOCUS 450 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
