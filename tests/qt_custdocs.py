"""2.65.0 Customer Documents in Qt, and Compare linked to the matrix: add the customer folder's files; an amendment is
matched to its document as a new version; the submission requirements show the changed page limit to review (mark
reviewed, edit, add, export); Compare shows each change beside the matrix requirement it touches and opens it in
Assign; the impact review lists the matrix sentence the amendment changed; deliverables are added, marked done for the
stage and exported. The library, register and record are the classic window's own files."""
import os, shutil, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
import app_gui as A
import effort as E, effortrec as RR, docversions as DV, docintake as DI, deliverables as DL, workspace as W, office_pdf as OP
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow
from test_docversions import amend

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); CDIR = os.path.join(EDIR, "Customer documents"); os.makedirs(CDIR)
RFP = os.path.join(A.BASE_DIR, "test_samples", "rfp")
for f in os.listdir(RFP):
    shutil.copy2(os.path.join(RFP, f), CDIR)
INBOX = os.path.join(tmp, "inbox"); os.makedirs(INBOX)
AMD = amend(os.path.join(RFP, "Kestrel_RFP_Sections_C_L_M.docx"), os.path.join(INBOX, "Kestrel_RFP_Sections_C_L_M_Amd1.docx"),
            [("exceed 50 pages", "exceed 40 pages"), ("the five highest", "the ten highest")])
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CDIR)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Management")
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
check("the rail: Deliverables with the effort; Documents: Library, Changes, Submission rules", [k for k in w.step_btns][1:3] == ["home", "deliverables"]
      and [k for k in w.step_btns][11:14] == ["library", "compare", "requirements"],          # 2.99.0: Compliance comes first
      list(w.step_btns))
# a compliance matrix with the page-limit sentence as a requirement
w.read_page.read([os.path.join(CDIR, "Kestrel_RFP_Sections_C_L_M.docx")], os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"))
t = time.time()
while w.review is None and time.time() - t < 60:
    app.processEvents(); time.sleep(0.02)
M = w.review.M
pl = next(it for it in M.items if "exceed 50 pages" in it["text"])
w.review.req([pl], "1.1 Technical Approach"); w.changed(); w.save_now()
# documents
w.go("docs"); app.processEvents()
dp = w.docs_page
un = dp.ctx.unadded()
check("the customer folder's files not added yet", len(un) == 2 and "(2)" in dp.b_folder.text(), un)
made = dp.add(un, choices=[{}, {}])
check("Add: both files become documents", len(made) == 2 and dp.tree.topLevelItemCount() == 2)
plan = DI.plan(dp.ctx.lib, [AMD])
check("the amendment is matched to its document (a strong match)", plan[0]["choice"] == "version" and plan[0]["best"][0]["name"].startswith("Kestrel"),
      plan[0].get("best", [None])[0] and plan[0]["best"][0]["name"])
made2 = dp.add([AMD], choices=[{}])
d, v = made2[0]
check("added as Amendment 1 of the RFP", v["label"] == "Amendment 1" and len(d["versions"]) == 2, (v["label"], len(d["versions"])))
check("the amendment shows its changes and is not reviewed yet", "to review" in dp.p_rev.text() and dp.p_rev.text().startswith("1"))
again = dp.add([AMD], choices=[{}])
check("the same file twice is skipped", again == [])
check("the timeline has the new version", any("Amendment 1 added" in e["text"] for e in RR.Record(w.ws.root).events()))
# requirements
w.go("requirements"); app.processEvents()
rp = w.requirements_page
key = next(k for k, r in rp.rows.items() if r["kind"] == "Page limit" and r["value"] == "40 pages")
check("the changed page limit is marked to review", rp.rows[key]["to_review"] and "Proposal 40" in rp.facts.text() and "1 change to review" in rp.facts.text(), rp.facts.text())
rp.select(key); app.processEvents()
check("its card shows the history", "Page limit" in rp.card.title.text())
rp.act("review", key)
check("Mark reviewed", not rp.rows[key]["to_review"])
rp.edit(key, "40 pages (Volume I and II together)")
check("Edit keeps what the documents say beside it", rp.rows[key]["value"].startswith("40 pages (") and rp.rows[key]["found"] == "40 pages")
k2 = rp.add("Format", "Font", "12-point Arial")
check("a typed-in requirement", k2 in rp.rows and rp.rows[k2]["manual"])
p = rp.export(os.path.join(tmp, "req.xlsx"))
check("export the requirements", p and os.path.isfile(p))
# compare, linked to the matrix
w.go("compare"); app.processEvents()
cp = w.compare_page
rows = cp.show(d["id"], None, v["id"])
ch = [i for i, r in enumerate(rows) if r["kind"] != "same"]
check("Compare: the two changes", len(ch) == 2, [rows[i]["kind"] for i in ch])
hit = next(i for i in ch if "40 pages" in rows[i]["new"])
check("the page-limit change is linked to its matrix requirement, with its section", cp.links[hit] and cp.links[hit][0]["id"] == pl["id"]
      and cp.links[hit][0]["map"] == "1.1 Technical Approach", cp.links[hit])
check("the matrix column names it", pl["id"] in cp.table.item(cp.shown.index(hit), 2).text())
cp.in_matrix.setChecked(True); app.processEvents()
check("Only what touches the matrix", cp.shown == [i for i in ch if cp.links[i]])
cp.table.selectRow(0); app.processEvents()
check("the change shows its words and the link", pl["id"] in cp.detail.toHtml() and "line-through" in cp.detail.toHtml())
cp.open_in_assign(0); app.processEvents()
check("double-click opens the requirement in Assign", w.stack.currentWidget() is w.assign_page and w.assign_page.cur == pl["id"])
w.go("compare"); app.processEvents()
r1 = cp.export_redline(os.path.join(tmp, "red.docx")); r2 = cp.export_list(os.path.join(tmp, "chg.xlsx"))
check("redline and change list", r1 and zipfile.is_zipfile(r1) and r2 and os.path.isfile(r2))
# impact review
w.go("impact"); app.processEvents()
ip = w.impact_page
r = ip.show(v["id"])
check("the impact review: the page limit and the matrix sentence it changed", r and r["requirements"] and
      any(x["id"] == pl["id"] for x in r["compliance"]["changed"]) and pl["id"] in ip.view.toHtml(), r and r["counts"])
check("Mark reviewed on the impact review", ip.mark_reviewed() and DV.Library(w.ws.p("documents")).load().counts()["unreviewed"] == 0)
pw = ip.export(os.path.join(tmp, "impact.docx"))
check("export the impact review", pw and zipfile.is_zipfile(pw))
# deliverables
w.go("deliverables"); app.processEvents()
dl = w.deliverables_page
did = dl.edit(None, {"name": "Volume I Technical", "kind": "Volume", "owner": "A. Lee", "format": "PDF", "limit": "40 pages", "status": "Drafting"})
dd = DL.get(RR.Record(w.ws.root), did)
check("+ Deliverable", dd and dd["owner"] == "A. Lee" and dd["status"] == "Drafting" and dl.table.rowCount() >= 1)
dl.table.selectRow(dl.ids.index(did)); dl.mark_stage()
check("done for this stage", RR.Record(w.ws.root).data["stage"] in DL.get(RR.Record(w.ws.root), did)["stages_done"])
pe = dl.export(os.path.join(tmp, "dl.xlsx"))
check("export the deliverables", pe and os.path.isfile(pe))
w.close()
n = sum(checks)
print(f"QT CUSTDOCS PASS ({n}/{len(checks)})" if n == len(checks) else f"QT CUSTDOCS FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
