"""4.22.0 offscreen: Prepare for Redline in the window. Under Documents; every PDF and picture in Documents is a row
with its state and one Prepare button (a Word file is not listed); no More menu; right-click for the other layout,
a copy without the comments and where the file is; Put its comments into my Word file... writes a dated copy of the
person's file; Check lists the comments; Quick tools prepares a file outside the effort beside it. Fictional content
(the Kestrel program)."""
import hashlib, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import docintake as DI, docversions as DV, effort as E, ocrpdf, workspace as W
import redlinemarks as RM, redlineprep as RP
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme, docstatus as DS, toolshome as TH
import skqt.mainwin as MW
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); CD = os.path.join(ED, "Customer documents"); os.makedirs(CD)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CD)
ws = W.Workspace(W.data_dir_for(LIST), "Kestrel")
S = os.path.join(A.BASE_DIR, "test_samples")
PDF = os.path.join(CD, "Kestrel_Section_L_reviewed.pdf"); shutil.copy2(os.path.join(S, "comments", "C01_prose_commented.pdf"), PDF)
DOCX = os.path.join(CD, "Kestrel_Section_L.docx"); shutil.copy2(os.path.join(S, "comments", "C01_prose.docx"), DOCX)
PIC = os.path.join(CD, "Kestrel_page.png")
import pypdfium2 as pdfium
BASE = os.path.join(S, "redline", "R01_cover_figure.pdf")
pd = pdfium.PdfDocument(BASE); pd[1].render(scale=200 / 72).to_pil().save(PIC); pd.close()
lib0 = DV.Library(ws.p("documents")).load()
dP, _v = lib0.add(PDF, DI.read(PDF), doc_name="Section L, reviewed", role="matrix", initial="L", dtype="Section L")
dW, _v = lib0.add(DOCX, DI.read(DOCX), doc_name="Section L in Word", role="context")
dI, _v = lib0.add(PIC, [], doc_name="A page as a picture", role="reference", category="graphics")
ocrpdf.make(lib0.path_of(dI["versions"][-1]), ws.p("page copies"),
            lines_of=lambda img: [t + (1.0,) for t in ocrpdf.typed_lines(BASE, 1, 200 / 72)])   # the reader's lines, as Shred makes them
for _d in lib0.all:                                   # 4.25.3: Prepare for Redline lists what is marked Redlined Deliverable
    lib0.set_returns(_d["id"], ["redline"])
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
toasts, said = [], []
w.open_effort("Kestrel"); app.processEvents()
w.toast = lambda msg, *a, **k: toasts.append(msg)
w.status = lambda msg, *a, **k: said.append(msg)
rail = [t for _k, t in MW.RAIL[0][1]]
check("4.25.3: Prepare for Redline is off the menu, and opens from Deliverables", "Prepare for Redline" not in rail
      and MW.GROUP_OF["redline"] == "Deliverables")
w.go("redline"); app.processEvents()
pp = w.redline_page; pp.refresh(); app.processEvents()
names = [pp.table.item(r, 0).text() for r in range(pp.table.rowCount())]
check("every PDF and picture marked Redlined Deliverable is a row; a Word file is not", sorted(names) == ["A page as a picture", "Section L, reviewed"], names)
check("each row says Not prepared and has its own Prepare button", all(pp.table.item(r, 2).text() == "Not prepared"
      and pp.table.cellWidget(r, 3).text() == "Prepare" for r in range(pp.table.rowCount())))
check("no More menu and no main button in the bar: one command", not pp.bar.more_menu.actions() and pp.bar.main is None
      and pp.bar.labels() == ["Put its comments into my Word file..."], pp.bar.labels())
rP, rI = names.index("Section L, reviewed"), names.index("A page as a picture")
pp.table.cellWidget(rP, 3).click(); app.processEvents()
st = pp.table.item(rP, 2).text()
check("Prepare on the row: the Word file is made and the row says so, with its comments", st.startswith("Prepared 20") and "comment(s) placed" in st
      and pp.table.cellWidget(rP, 3).text() == "Prepare again", st)
check("... and the message says what the comments became", toasts and "tracked change(s)" in toasts[-1] and "Word comment(s)" in toasts[-1], toasts[-1:])
made = RP.state(pp._folders()[0], pp.rows[rP][2])["copy"]
check("... in the effort's Redlines folder", os.path.basename(os.path.dirname(made)) == "Redlines")
plain = pp.row_menu(rP, pick="Prepare it without the comments"); app.processEvents()
check("right-click: Prepare it without the comments", plain and not RM.read_back(plain)["comments"] and "comment(s)" not in pp.table.item(rP, 2).text(),
      pp.table.item(rP, 2).text())
pp.table.cellWidget(rI, 3).click(); app.processEvents()
check("a picture is prepared from the words read on it", pp.table.item(rI, 2).text().startswith("Prepared 20") and "paragraphs" in toasts[-1], (toasts[-1:], said[-1:]))
# the PDF's comments into the Word file the person has
mine = os.path.join(tmp, "Our Section L.docx"); shutil.copy2(DOCX, mine)
h0 = hashlib.sha256(open(mine, "rb").read()).hexdigest()
pp.table.selectRow(rP)
res = pp.into_word(mine); app.processEvents()
check("Put its comments into my Word file: a dated copy of it, with the changes and comments; the file itself unchanged",
      res and os.path.basename(res["path"]).startswith("Our Section L - redline copy - ") and res["changes"] == 6 and res["word_comments"] == 13
      and hashlib.sha256(open(mine, "rb").read()).hexdigest() == h0, res and {k: res[k] for k in ("changes", "word_comments")})
check("... the row says which Word file, and the message counts them", "into Our Section L.docx" in pp.table.item(rP, 2).text()
      and "put into a copy of Our Section L.docx" in toasts[-1], (pp.table.item(rP, 2).text(), toasts[-1]))
pp.table.selectRow(rI); n_said = len(said)
none = pp.into_word(mine); app.processEvents()
check("a document with no comments says so", none is not None and not none["comments"] and len(said) > n_said and "no comments" in said[-1], said[-1:])
w.go("rcheck"); cp = w.rcheck_page; cp.refresh(); app.processEvents()
k = cp.copy.findData(res["path"])
check("Check lists the prepared files, the person's Word file among them", k >= 0 and cp.copy.count() >= 2)
cp.copy.setCurrentIndex(k)
got = cp.check_copy()
check("Check: the Word file against the PDF, and each comment with how it was placed", got and not got["differences"] and len(got["comments"]) >= 15
      and any(cp.table.item(r, 0).text().startswith("PDF ") for r in range(cp.table.rowCount())), got and got["differences"][:2])
# Documents
w.go("library"); lp = w.library_page; lp.refresh(); op = w.ours_page; op.refresh(); app.processEvents()
on = op if op.select(dI["id"]) else lp
on.select(dI["id"]); app.processEvents()
acts = [a.text() for a in DS.row_menu(on, run=False).actions()]
check("Documents: a picture's right-click offers Prepare for redline", "Prepare for redline" in acts, acts)
lp.select(dW["id"]); app.processEvents()
acts = [a.text() for a in DS.row_menu(lp, run=False).actions()]
check("... a Word file's does not", acts and "Prepare for redline" not in acts, acts)
# Quick tools: a file outside the effort
loose = os.path.join(tmp, "loose"); os.makedirs(loose)
other = os.path.join(loose, "Model contract.pdf"); shutil.copy2(BASE, other)
uses = dict(TH.uses_for([other]))
check("Quick tools offers Prepare it for redline for a PDF or a picture, not for a Word file", "redline" in uses
      and "redline" in dict(TH.uses_for([PIC])) and "redline" not in dict(TH.uses_for([DOCX])), list(uses))
out = pp.prepare(path=other); app.processEvents()
check("... and the Word file goes beside the file", out and os.path.dirname(out) == loose and os.path.isfile(out), out)
k = sum(checks)
print(f"QT REDLINE PREP 4220 {'PASS' if k == len(checks) else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if k == len(checks) else 1)
