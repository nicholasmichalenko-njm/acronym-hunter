"""4.55.0 offscreen: the rest of the shred thread (UX decisions 13, 15, 17, 18, 14; Nicholas 2026-11-17 21:12 to 21:20).
Outline lists the pieces typed Structure, then those only suggested (shown as suggestions), in the customer's words with
where they are, Use it and Show on its page; Use it on an untouched outline puts the headings in at once and types a
suggested piece Structure; with a structure there, Add or Replace is asked first with the effect in counts and names,
and Replace keeps placed requirements in the matrix as not placed; with no piece, one line and Go to Shred. The start
card leaves once a start is chosen, on Outline and on Setup. Place shows none of Shred's document row but keeps the
picker and Fit width. The Matrix page opens on the matrix; Design... opens the design with Save as a view... in it.
Make the setup has no reference-text rows, one line instead; Effort Formatting > More > Reference text in the setup...
saves the options Make then uses. Fictional (Kestrel)."""
import os, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import compliance as C, effort as E, workspace as W, pdfmini, office_pdf as OP
import setupdoc as SD, setuptemplate as ST, shredtypes as ST2, structfrom as SF
OP.available = lambda: False
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QLineEdit, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
from skqt import structdoors as SDR, reftext as RT
from skqt.matrixpage import MatrixPage
from skqt.setuppage import MakeDialog

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
SECL = os.path.join(tmp, "Section_L.pdf")
pdfmini.write(SECL, [["The Offeror shall describe its integrated master schedule.",
                      "Volume I holds the technical approach and Volume II holds the management approach.",
                      "The proposal shall be organized as follows: (1) Technical Approach; (2) Management Approach; (3) Past Performance."],
                     ["The Offeror shall describe its risk register.", "The Offeror shall describe its staffing plan."]], size=9)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def pump(n=5):
    for _ in range(n):
        app.processEvents(); time.sleep(0.01)


def wait(cond, secs=90):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Kestrel")
w.read_page.read([SECL], os.path.join(ED, "Kestrel_Compliance_Matrix.xlsx"))
check("extracted", wait(lambda: w.review is not None and not w.read_page.running() and w.review.M.items))
M = w.review.M
by = lambda s: next(it for it in M.items if s in (it.get("text") or ""))       # noqa: E731
vol, org = by("Volume I holds"), by("organized as follows")
SD.setup_of(M)["outline_auto"] = True        # pdfmini writes no headings: the outline stands in for the app's own start
bp = w.setups_page.builder

# ---- decision 13: the list, the suggestions first only as suggestions
w.go("outline"); pump(); bp.refresh(); pump()
check("Outline shows the start card while the outline is untouched", SF.untouched(M) and bp.start_card.isVisibleTo(w) and bp.doors_w.isVisibleTo(w))
words = lambda: [(r.it["id"], r.suggested) for r in bp.piece_rows]             # noqa: E731
check("nothing typed yet: both pieces listed as suggestions", words() == [(vol["id"], True), (org["id"], True)], words())
r0 = bp.piece_rows[0]
check("... a suggestion says Suggested, in muted words, and Use it is not the main button", r0.where.text().startswith("Suggested. ")
      and r0.words.property("role") == "muted" and r0.use.property("kind") is None, r0.where.text())
check("... each row: the customer's words (full text in the tooltip), where it is, Use it and Show on its page",
      "Volume I holds the technical approach" in r0.words.text() and r0.words.toolTip().endswith("management approach.")
      and "Section_L.pdf" in r0.where.text() and "Past Performance" in bp.piece_rows[1].words.text() and "page 1" in r0.where.text()
      and r0.use.text() == "Use it" and r0.show_btn.text() == "Show on its page" and r0.use.isVisibleTo(w) and r0.show_btn.isVisibleTo(w))
check("... no Go to Shred and no Use all with nothing typed", not bp.go_shred.isVisibleTo(w) and not bp.door1.isVisibleTo(w))
w.go("setups"); pump()
check("Setup shows the card as its one line", bp.start_card.isVisibleTo(w) and bp.start_line.isVisibleTo(w) and not bp.doors_w.isVisibleTo(w))
ST2.toggle([org], "structure")
w.go("outline"); pump(); bp.refresh(); pump()
check("a piece typed Structure comes first, not as a suggestion; the other stays a suggestion",
      words() == [(org["id"], False), (vol["id"], True)] and not bp.piece_rows[0].where.text().startswith("Suggested"), words())
row = bp.piece_rows[1]
row.show_btn.click(); pump()
check("Show on its page: Shred with that piece selected", w.stack.currentWidget() is w.assign_page
      and vol["id"] in [x["id"] for x in w.assign_page.selected()])
w.go("outline"); pump()

# ---- Use it on the untouched outline: no question; a suggested piece is typed Structure
dlg = SDR.use_piece(bp, vol, run=False)
heads = dlg.heads()
check("Use it reads that piece only, through the preview", [h["title"] for h in heads] == ["Volume I", "Volume II"], heads)
ents = SDR.finish(bp, heads, dlg.pieces); pump()
check("... untouched: the headings go in, nothing asked", bp._ask is None and [o["num"] for o in M.outline] == ["Volume I", "Volume II"],
      [C.outline_label(o) for o in M.outline])
check("... the suggested piece used is typed Structure now", ST2.has(vol, "structure"))
bp.refresh(); w.outline_page.refresh(); pump()
check("decision 15: the start card leaves once a start is chosen (Outline)", not bp.start_card.isVisibleTo(w)
      and not w.outline_page.started.isVisibleTo(w))
w.go("setups"); pump()
check("... and on Setup", not bp.start_card.isVisibleTo(w) and not bp.start_line.isVisibleTo(w))
names = []
from PySide6.QtWidgets import QMenu
m = QMenu(); SDR.more_items(bp, m); names = [a.text() for a in m.actions() if a.text()]
check("... the ways back stay under Structure...", "Add the required headings (Structure pieces)..." in names and "Draft headings from" in names, names)
w.go("outline"); pump()

# ---- a structure exists: Add or Replace, the effect first
reqs = [by("integrated master schedule"), by("risk register"), by("staffing plan")]
for it in reqs:
    it["decision"] = "Keep"; it["map"] = C.outline_label(M.outline[0])
reqs[2]["map"] = C.outline_label(M.outline[1])
before = [C.outline_label(o) for o in M.outline]
dlg = SDR.use_piece(bp, org, run=False)
heads = dlg.heads()
got = SDR.finish(bp, heads, dlg.pieces, answer="cancel")
a = bp._ask
check("with a structure there, Add or Replace is asked first", a is not None and got is None
      and [b.text() for b in (a.b_add, a.b_rep, a.b_cancel)] == ["Add to our outline", "Replace our outline", "Cancel"])
check("... the effect in counts and names", f"{len(heads)} heading(s) go in after the 2" in a.add_say.text()
      and f"{len(heads)} heading(s) take the place of the 2" in a.rep_say.text() and "3 requirement(s)" in a.rep_say.text()
      and all(it["id"] in a.rep_say.text() for it in reqs), (a.add_say.text(), a.rep_say.text()))
check("... Cancel changes nothing", [C.outline_label(o) for o in M.outline] == before)
SDR.finish(bp, heads, dlg.pieces, answer="add"); pump()
check("Add: the headings after ours, every placed requirement keeps its place", len(M.outline) == 2 + len(heads)
      and [it["map"] for it in reqs] == [C.outline_label(M.outline[k]) for k in (0, 0, 1)], [C.outline_label(o) for o in M.outline])
dlg = SDR.use_piece(bp, org, run=False)
SDR.finish(bp, dlg.heads(), dlg.pieces, answer="replace"); pump()
check("Replace: our outline is the new headings", [o["title"] for o in M.outline] == ["Technical Approach", "Management Approach", "Past Performance"],
      [C.outline_label(o) for o in M.outline])
check("... the placed requirements are still in the matrix, not placed, still requirements",
      all(it in M.items and not it.get("map") and it["decision"] == "Keep" for it in reqs), [(it["id"], it.get("map")) for it in reqs])
reqs[0]["map"] = C.outline_label(M.outline[0])
eff = SF.effect(M, [{"title": "Other", "level": 1}])
check("effect() lists a requirement that would lose its place", eff["lose"] == [reqs[0]["id"]] and eff["have"] == 3 and eff["add"] == 1, eff)

# ---- no piece sets the structure: one line, Go to Shred
for it in SF.pieces(M) + SF.suggested(M):
    ST2.set_types([it], []); it["decision"] = "Drop"
SD.setup_of(M)["outline_auto"] = True
bp.refresh(); pump()
check("no piece typed or suggested: one line and Go to Shred", bp.start_card.isVisibleTo(w) and not bp.piece_rows
      and bp.door1_say.isVisibleTo(w) and bp.door1_say.text() == "No piece sets the structure yet." and bp.go_shred.isVisibleTo(w)
      and not bp.door1.isVisibleTo(w))
card_words = " ".join(x.text() for x in bp.start_card.findChildren(QLabel) if x.isVisibleTo(w))
check("... no how-to on the page; We build it stays beside it", "type it Structure" not in card_words and "select the piece" not in card_words
      and bp.door2.isVisibleTo(w) and bp.door2.text() == "Draft headings from...", card_words)
import skqt.guidetopics as GT
gt = " ".join(str(x) for t in GT.TOPICS if t[0] == "outline" for x in t)
check("... the how-to is in the Guide", "type it Structure" in gt and "No piece sets the structure yet" in gt)
bp.go_shred.click(); pump()
check("Go to Shred opens Shred", w.stack.currentWidget() is w.assign_page)

# ---- decision 17: Place
pg = w.assign_page
w.go("place"); pump(10)
row_vis = {n: getattr(pg, n).isVisibleTo(w) for n in ("queue_lbl", "done_btn", "next_btn", "focus_more", "shred_check", "files", "fit_btn")}
check("Place: none of Shred's document row; the picker and Fit width stay", row_vis == {"queue_lbl": False, "done_btn": False, "next_btn": False,
      "focus_more": False, "shred_check": False, "files": True, "fit_btn": True}, row_vis)
pg.open_file(pg.file); pump()
check("... picking a document again keeps it so", not pg.done_btn.isVisibleTo(w) and not pg.queue_lbl.isVisibleTo(w))
for step in ("crosswalk", "prove"):
    w.go(step); pump()
    check(f"... the same on {step}", not pg.done_btn.isVisibleTo(w) and not pg.focus_more.isVisibleTo(w) and pg.fit_btn.isVisibleTo(w))
w.go("assign"); pump(10)
check("Shred's own row is unchanged", pg.queue_lbl.isVisibleTo(w) and pg.focus_more.isVisibleTo(w) and pg.shred_check.isVisibleTo(w)
      and not pg.fit_btn.isVisibleTo(w) and "Fit width" in pg.more_acts)

# ---- decision 18: the matrix leads
w.go("matrix"); pump()
mp = w.matrix_page
check("the Matrix page opens on the matrix, the design closed", not mp.design_w.isVisibleTo(w) and mp.table.isVisibleTo(w)
      and not mp.b_design.isChecked())
bar = [b.text() for b in mp.bar.visible_commands()]
check("the bar: Bring the edited matrix back..., Design..., Export the matrix... (main)", bar == ["Bring the edited matrix back...", "Design...",
      "Export the matrix..."] and mp.bar.main.text() == "Export the matrix..." and "Save as a view..." not in mp.bar.labels(), bar)
check("... Save as a view... is not shown with the design closed", not mp.b_saveview.isVisibleTo(w))
mp.b_design.click(); pump()
check("Design... opens the design beside the matrix, Save as a view... in it", mp.design_w.isVisibleTo(w) and mp.table.isVisibleTo(w)
      and mp.b_saveview.isVisibleTo(w) and MatrixPage.design_open)
iid = mp.save_view("Kestrel outline")
check("... Save as a view... saves", iid and mp.view_box.currentData() == iid)
mp.b_design.click(); pump()
check("Design... closes it again", not mp.design_w.isVisibleTo(w) and not MatrixPage.design_open)
check("a view is used with the design closed", mp.use_view("builtin:outline") is not None)
mp2 = MatrixPage(w)
check("a new page opens closed (the session's choice only)", not mp2.design_w.isVisibleTo(mp2) and not mp2.b_design.isChecked())

# ---- decision 14: Make the setup
for it in reqs:
    it["map"] = C.outline_label(M.outline[0])
sp = w.setup_page
d = MakeDialog(sp, ST.ready(M, None))
check("Make the setup: no reference-text rows", not d.findChildren(QLineEdit) and not d.findChildren(QCheckBox))
check("... one line: what will be used, with the link", d.ref_line.text().startswith("Reference text: 9 kinds in the file, 9 hidden.")
      and "Change in Effort Formatting" in d.ref_line.text(), d.ref_line.text())
links = [x.text() for x in d.lines if "href" in x.text()]
check("... an open line links to where it is fixed", any("still open" in t and "href='assign'" in t for t in links), [x.text() for x in d.lines])
d.go_fix("assign"); pump()
check("... Fix it closes the window and opens the page", d.goto == "assign" and w.stack.currentWidget() is w.assign_page)
w.go("effortfmt"); pump()
ef = w.effortfmt_page
check("Effort Formatting: More > Reference text in the setup...", ef.bar.action("Reference text in the setup...") is not None
      and ef.bar.b_more.isVisibleTo(w))
rd = RT.open_window(ef, w, modal=False)
check("... the same nine rows: style, Hidden, In the file", len(rd.rows) == len(ST.KINDS) == 9 and rd.rows["rfp"][0].text() == "SK RFP Requirement")
rd.rows["rfp"][0].setText("Kestrel RFP Text"); rd.rows["pm"][2].setChecked(False); rd.rows["support"][1].setChecked(False)
rd.save()
o = RT.opts_now(w)
check("... Save keeps them where Make reads them", o["rfp"]["style"] == "Kestrel RFP Text" and o["pm"]["include"] is False
      and ((w.ws.get("prod_std", {}) or {}).get("over") or {}).get("content_map", {}).get("rfp", {}).get("style") == "Kestrel RFP Text")
d = MakeDialog(sp, ST.ready(M, None))
check("... the Make line says so", d.ref_line.text().startswith("Reference text: 8 kinds in the file, 7 hidden."), d.ref_line.text())
out = sp.make_on_templates(go=True)
doc = zipfile.ZipFile(out[0]["setup"]).read("word/document.xml").decode() if out else ""
check("Make uses the saved options without asking", out and 'w:val="KestrelRFPText"' in doc, out)
k = sum(checks)
print(f"QT THREAD 4550 {'PASS' if k == len(checks) else 'FAIL'} ({k}/{len(checks)})")
sys.stdout.flush()
w.close()
__import__("hangguard").end(0 if k == len(checks) else 1)
