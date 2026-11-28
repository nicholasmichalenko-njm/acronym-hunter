"""4.86.0 offscreen (step I4; Nicholas 2026-11-27 19:11 "go"): the Type list, change notices, the Section J check and
Last changed by.
- The built-in list is the direction's seed; a saved list is not changed by itself: Settings > Document types names the
  types new in 4.86.0 it lacks, with Add them (above Other; Save keeps them) and Leave them out (this PC).
- A file typed Amendment, Q&A, Evaluation Notice or FPR request (or a type renamed from one) is a change notice: it is
  listed first in the summary after the add, it brings the summary up on its own, and with no release said it stands
  for one, so the package's documents it did not replace are still listed.
- Section J's list of attachments is read and counted against the package: in the summary after the add (which it
  brings up on its own when one is missing, even for a first release) and on Documents' group line.
- Matrix > Assign: Last changed by, the newest version whose changes touched a piece's words.
Fictional (Heron)."""
import json, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import changereview as CR, docpackages as DP, docversions as DV, doctypes as DT, effort as E, lastchanged as LC, \
    sectionj as SJ, workspace as W, pdfmini
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme, intakesummary as IS
from skqt.mainwin import MainWindow
import hangguard

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def wait(page):
    t0 = time.time()
    while page.worker is not None and time.time() - t0 < 120:
        app.processEvents(); time.sleep(0.02)
    app.processEvents()


# ---- the rules alone
c0 = tempfile.mkdtemp()
check("no list saved: the built-in list is the seed, and nothing is offered", DT.missing_new(c0) == []
      and {"SF 33 / SF 1449", "Section C", "Exhibit", "Evaluation Notice", "FPR request", "RFI", "Sources Sought"} <= {t["name"] for t in DT.load(c0)["types"]}
      and DT.load(c0)["types"][-1]["name"] == "Other")
check("the library knows the same list", set(DV.DOC_TYPES) == {t["name"] for t in DT.BUILT_IN} and "Section C" in DV.MATRIX_TYPES
      and "Section B" not in DV.MATRIX_TYPES)
for n, t in (("SF1449_Solicitation.pdf", "SF 33 / SF 1449"), ("Amendment_0001_SF30.pdf", "Amendment"), ("SF_30.pdf", "Amendment"),
             ("Exhibit_B_Schedule.pdf", "Exhibit"), ("Attachment_J-2_Wage_Determination.pdf", "Wage determination"),
             ("52.212-1_Addendum.pdf", "Section L"), ("Evaluation_Notice_3.pdf", "Evaluation Notice"), ("FPR_Request.pdf", "FPR request"),
             ("Sources_Sought.pdf", "Sources Sought"), ("Kestrel_SOW_rev2.docx", "SOW"), ("Kestrel.docx", "RFP")):
    check(f"a file name suggests its type: {n}", DV.guess_type(n) == t, DV.guess_type(n))
check("change notices: Amendment, Q&A, Evaluation Notice, FPR request; not a SOW", all(DT.is_change_notice(t) for t in DT.CHANGE_NOTICES)
      and not DT.is_change_notice("SOW") and not DT.is_change_notice(""))
check("the Section J reader: J-1 and Attachment 1 are one; exhibits apart; page counts and dates off the titles",
      [(r, t) for _k, r, t in SJ.refs("Attachment J-1 Performance Work Statement, 12 pages J-2 Wage Determination dated 1 Oct 2026 "
                                      "Exhibit A Contract Data Requirements List Attachment 1 Performance Work Statement")]
      == [("J-1", "Performance Work Statement"), ("J-2", "Wage Determination"), ("Exhibit A", "Contract Data Requirements List")])

# ---- an effort
tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
old15 = [dict(t) for t in DT.BUILT_IN if t["name"] not in DT.NEW_IN_4860]
with open(os.path.join(cfg, DT.FILE), "w", encoding="utf-8") as f:                       # a list saved before 4.86.0
    json.dump({"types": old15}, f)
ED = os.path.join(tmp, "Heron"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Effort_List.xlsx"); L = E.EffortList(LIST, "Heron"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Heron", path=LIST, customer_dir=CD, solicitation="W912DY-24-R-0001")
ws = W.Workspace(W.data_dir_for(LIST), "Heron")
ws.set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Management")


def pdf(name, lines):
    p = os.path.join(tmp, name); pdfmini.write(p, [lines], size=9); return p


RFP = ["SECTION J - LIST OF ATTACHMENTS", "Attachment J-1 Performance Work Statement, 12 pages", "Attachment J-2 Wage Determination",
       "Attachment J-3 DD Form 254", "SECTION K - REPRESENTATIONS", "K.1 The offeror shall complete the representations."]
SEC_L = ["L.1 GENERAL", "The offeror shall submit three volumes.", "L.2 VOLUME I", "Volume I shall not exceed 50 pages.",
         "L.3 VOLUME II", "Volume II shall describe the management approach."]
PWS = ["PWS 1", "The contractor shall staff the help desk.", "PWS 2", "Hours are 0700 to 1900."]
WD = ["WAGE DETERMINATION", "Rates by labor category for the site."]

app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()

# ---- Settings > Document types: the new types a saved list lacks
card = w.settings_page.doctypes_card
card.fill(); app.processEvents()
check("a list saved before 4.86.0: the line names the 16 new types", card.new_box.isVisibleTo(card) and len(card.new_types) == 16
      and card.new_line.text().startswith("16 types came with 4.86.0 and are not in your list: SF 33 / SF 1449, Section B"), card.new_line.text())
check("... and nothing was changed by itself", [t["name"] for t in DT.load(cfg)["types"]] == [t["name"] for t in old15])
card.grab().save(os.path.join(tmp, "doctypes.png"))
rows0 = card.table.rowCount()
check("Add them puts them in the table above Other; the line goes", card.add_new() == 16 and card.table.rowCount() == rows0 + 16
      and card.values()[-1]["name"] == "Other" and card.values()[-2]["name"] == "Sources Sought" and not card.new_box.isVisibleTo(card))
check("... Save keeps them", card.save() and len(DT.load(cfg)["types"]) == len(DT.BUILT_IN) and DT.missing_new(cfg) == [])
c2 = tempfile.mkdtemp()
with open(os.path.join(c2, DT.FILE), "w", encoding="utf-8") as f:
    json.dump({"types": old15 + [{"name": "Exh docs", "initial": "Exh", "aliases": ["Exhibit"]}]}, f)
check("a type the team renamed from a new one is not offered again", "Exhibit" not in [t["name"] for t in DT.missing_new(c2)]
      and len(DT.missing_new(c2)) == 15)
DT.leave_out(c2, ["RFI", "Sources Sought"])
check("Leave them out: not offered again on this PC, the team's list unchanged", len(DT.missing_new(c2)) == 13
      and "RFI" not in [t["name"] for t in DT.missing_new(c2)] and len(DT.load(c2)["types"]) == 16)

w.open_effort("Heron"); app.processEvents()
w.go("library"); app.processEvents()
lp = w.library_page

# ---- the Final RFP: Section J lists three attachments, two came
F_RFP, F_L, F_PWS, F_WD = pdf("RFP.pdf", RFP), pdf("Section_L.pdf", SEC_L), pdf("Attachment_J-1_PWS.pdf", PWS), pdf("Wage_Determination.pdf", WD)
FINAL = {"part_of": "Solicitation", "arrived_as": "Final RFP", "arrived_on": "2026-11-02"}
t0 = time.time()
lp.add(paths=[F_RFP, F_L, F_PWS, F_WD], choices={"RFP.pdf": dict(FINAL, initial="R", type="RFP"), "Section_L.pdf": dict(FINAL, initial="L", type="Section L"),
                                                "Attachment_J-1_PWS.pdf": dict(FINAL, initial="P", type="PWS"),
                                                "Wage_Determination.pdf": dict(FINAL, initial="WD", type="Wage determination")})
wait(lp)
print(f"TIMING add of four files with the Section J check: {time.time() - t0:.2f} s (offscreen, small fictional PDFs)")
dlg = lp.last_summary
lab = [x.text() for x in dlg.findChildren(QLabel)] if dlg else []
check("a first release with an attachment missing from Section J: the summary comes up", isinstance(dlg, IS.SummaryDialog)
      and dlg.windowTitle() == "Added: Solicitation: Final RFP", dlg)
check("... it says Section J's count and names the one missing", dlg is not None and dlg.sj_line.isVisibleTo(dlg)
      and dlg.sj_line.text() == "Section J lists 3 attachments; 2 are in this package. Not here: J-3 DD Form 254.", dlg.sj_line.text() if dlg else "")
check("... nothing else in it: no new version, no change notice, nothing to confirm", dlg is not None and dlg.versions.count() == 0
      and dlg.notices.count() == 0 and dlg.confirm.count() == 0 and "Done" == dlg.b_done.text() and not dlg.b_compare.isVisibleTo(dlg))
dlg.show(); app.processEvents(); dlg.grab().save(os.path.join(tmp, "summary_sectionj.png")); dlg.done_now()
lib = DV.Library(ws.p("documents")).load()
r = SJ.check(lib, "Solicitation")
check("the check: read from the RFP; J-1 is the PWS by its file name, J-2 the wage determination by its title",
      r and r["doc"]["name"] == "RFP" and [(x[0], x[2]["name"]) for x in r["here"]] == [("J-1", "Attachment J-1 PWS"), ("J-2", "Wage Determination")]
      and r["missing"] == [("J-3", "DD Form 254")], r and [(x[0], x[2]["name"]) for x in r["here"]])
lp.lib = lib; lp.refresh(); app.processEvents()
groups = [lp.table.item(i, 0).text() for i in range(lp.table.rowCount()) if lp.table.columnSpan(i, 0) > 1]
check("Documents: the release's group line says Section J: 2 of 3 here", any(g.startswith("Solicitation: Final RFP") and g.endswith("Section J: 2 of 3 here") for g in groups), groups)
lp.grab().save(os.path.join(tmp, "documents.png"))

# ---- the matrix, from Section L, with the pieces kept
w.read_page.read([F_L], os.path.join(ED, "Heron_Compliance_Matrix.xlsx"))
t0 = time.time()
while not (w.review is not None and w.stack.currentWidget() is w.assign_page) and time.time() - t0 < 120:
    app.processEvents(); time.sleep(0.02)
M = w.review.M
for it in M.items:
    it["decision"] = "Keep"
w.go("library"); app.processEvents()

# ---- Amendment 0001 re-posts Section L (50 pages becomes 40) with the DD 254
F_L2 = pdf("Section_L_Amd_0001.pdf", SEC_L[:3] + ["Volume I shall not exceed 40 pages."] + SEC_L[4:])
F_254 = pdf("DD254.pdf", ["DD FORM 254", "Contract security classification specification."])
lib = DV.Library(ws.p("documents")).load()
dL = next(d for d in lib.all if d["name"] == "Section L")
AMD = {"part_of": "Solicitation", "arrived_as": "Amendment 0001", "arrived_on": "2026-11-20"}
lp.add(paths=[F_L2, F_254], choices={"Section_L_Amd_0001.pdf": dict(AMD, choice="version", doc=dL["id"], compare=True),
                                     "DD254.pdf": dict(AMD, initial="DD", type="DD 254")})
wait(lp)
dlg = lp.last_summary
check("Amendment 0001 with the DD 254: Section J's count is whole", dlg is not None
      and dlg.sj_line.text() == "Section J lists 3 attachments; all are in this package.", dlg.sj_line.text() if dlg else "")
dlg.done_now()
rv = CR.Review(ws.root).load()
pk = next(k for k, p in rv.pairs.items() if p.get("doc") == dL["id"])
vol1 = next(it for it in M.items if "50 pages" in it.get("text", ""))
check("What changed kept every matrix row the amendment touched, placed or not", vol1["id"] in rv.pairs[pk].get("changed", []), rv.pairs[pk].get("changed"))
w.go("assignto"); app.processEvents()
pg = w.assignto_page
pg.show_box.setCurrentIndex(1); app.processEvents()
hdr = [pg.table.horizontalHeaderItem(c).text() for c in range(pg.table.columnCount())]
row = next((i for i, d in enumerate(pg.data) if d["id"] == vol1["id"]), None)
check("Matrix > Assign: a Last changed by column", hdr[-1] == "Last changed by", hdr)
check("... the piece the amendment changed says Amendment 0001, with where and when on hover", row is not None
      and pg.table.item(row, 5).text() == "Amendment 0001" and "of Section L (2026-11-20)" in pg.table.item(row, 5).toolTip(),
      (row, row is not None and pg.table.item(row, 5).text()))
other = next((i for i, d in enumerate(pg.data) if d["id"] != vol1["id"] and "three volumes" in d["text"]), None)
check("... a piece it did not touch is blank", other is not None and pg.table.item(other, 5).text() == "")
pg.grab().save(os.path.join(tmp, "assign.png"))
check("the newest wins", LC.of(type("R", (), {"pairs": {"a": {"labels": ["Final RFP", "Amendment 0001"], "changed": ["x"], "doc": dL["id"], "to": "v?"},
                                                        "b": {"labels": ["Amendment 0001", "Amendment 0002"], "changed": ["x"], "doc": dL["id"], "to": "v?"}},
                                              "lineage": {"x": [{"kind": "updated", "label": "Amendment 0003", "when": "2026-12-01T10:00"}]}})(), lib)["x"]["label"]
      == "Amendment 0003")

# ---- a change notice with no release said: Amendment 0002's SF 30 alone
w.go("library"); app.processEvents()
F_SF30 = pdf("SF30_Amendment_0002.pdf", ["AMENDMENT OF SOLICITATION", "The due date is unchanged. Questions are answered in Attachment J-4."])
lp.add(paths=[F_SF30], choices={"SF30_Amendment_0002.pdf": {"type": "Amendment", "initial": "Amd2"}})
wait(lp)
dlg = lp.last_summary
lab = [x.text() for x in dlg.findChildren(QLabel)] if dlg else []
check("a change notice alone brings the summary up", isinstance(dlg, IS.SummaryDialog), dlg)
check("... it is listed first, under Change notice, with its type", dlg is not None and dlg.notices.count() == 1 and "Change notice" in lab
      and dlg.notices.item(0).text() == "SF30   ·   Amendment", dlg.notices.item(0).text() if dlg and dlg.notices.count() else lab)
check("... with no release said it stands for one, so the package's documents it did not replace are listed",
      dlg is not None and dlg.windowTitle() == "Added: Solicitation: Amendment 0002" and "Not in Amendment 0002" in lab
      and [dlg.confirm.item(i).text().split("   ")[0] for i in range(dlg.confirm.count())] == ["Attachment J-1 PWS", "DD254", "RFP", "Section L", "Wage Determination"]
      and all(dlg.confirm.item(i).checkState() == Qt.Unchecked for i in range(dlg.confirm.count())), (dlg.windowTitle() if dlg else "", dlg.confirm.count() if dlg else 0))
m = dlg.notice_menu(dlg.notices.visualItemRect(dlg.notices.item(0)).center(), run=False) if dlg else None
check("right-click the notice: Show on the page", m is not None and [a.text() for a in m.actions()][0] == "Show on the page")
dlg.show(); app.processEvents(); dlg.grab().save(os.path.join(tmp, "summary_notice.png")); dlg.done_now()
lib = DV.Library(ws.p("documents")).load()
check("... and nothing was saved as its release (Not said stays not said)", not any(v.get("arrived_as") for d in lib.all if d["name"].startswith("SF30")
                                                                                    for v in d["versions"]))
check("an Evaluation Notice stands for Discussions & FPR; a Q&A set numbers itself from its name",
      DP.release_of_notice({"type": "Evaluation Notice", "name": "EN 3", "versions": [{}]}) == ("Discussions & FPR", "Evaluation Notices")
      and DP.release_of_notice({"type": "Q&A", "name": "Questions and Answers 2", "versions": [{}]}) == ("Solicitation", "Q&A set 2"))

w.close()
print(f"QT INTAKE 4860 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
print("PICTURES", tmp)
hangguard.end(0 if all(checks) else 1)
