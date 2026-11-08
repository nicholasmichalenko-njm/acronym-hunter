"""3.56.0 Setup, offscreen. A Setup page in Plan: a structure is the least it needs (typed, from a Word outline, from an
RFP's headings; no Review); each section's lead, contributors, due date, pages and PM direction; layers on by default
(requirements, evaluation, Management guidance, pages, author and due) and off (customer context, captures, topics), each left
out of the setup when off; Make the setup on the templates; Plain setup; Changes for authors as one Word file per person;
the Structure Builder's Make the setup opens it. Fictional content."""
import os, sys, tempfile, zipfile
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


def text_of(path):
    with zipfile.ZipFile(path) as z:
        return z.read("word/document.xml").decode("utf-8")


app = QApplication([]); theme.apply(app)
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
import docxw, setupmake as SM, setupdoc as SD, compliance as C

# ---------------------------------------------------------------- the rules
outline = os.path.join(tmp, "outline.docx")
d = docxw.Doc(); d.heading("1 Technical Approach", 1); d.heading("1.1 Orbit Operations", 2); d.heading("2 Management", 1)
d.save(outline)
txt = SM.structure_from_docx(outline)
check("a structure from a Word outline's headings", "Technical Approach" in txt and "Orbit Operations" in txt and "Management" in txt, txt)
rfp = os.path.join(A.BASE_DIR, "test_samples", "rfp", "Kestrel_RFP_Sections_C_L_M.docx")
rt = SM.structure_from_rfp(rfp)
check("a structure from an RFP's headings", bool(SM.structure_from_text(rt)), rt[:200])
M = SM.start(os.path.join(tmp, "m", "Kestrel_Compliance_Matrix.xlsx"), "Kestrel", "1 Technical Approach\n  1.1 Orbit Operations\n2 Management")
check("a matrix holding only the structure, saved", os.path.isfile(M.path) and len(M.outline) == 3 and not M.items)
on = SM.layers(M)
check("layers on by default: requirements, evaluation, Management guidance, pages, author and due",
      all(on[k] for k in ("requirements", "evaluation", "pm", "pages", "author")), on)
check("... off: customer context, captures, topics", not any(on[k] for k in ("customer", "captures", "topics")), on)
check("the off layers' kinds are left out", set(SM.ensure_skip(M)) >= {"customer", "library", "objective", "capture", "topic"})
SM.set_layer(M, "evaluation", False)
check("a layer turned off leaves its kind out", "eval" in SD.setup_of(M)["layer_skip"] and not SM.layers(M)["evaluation"])
SM.set_layer(M, "evaluation", True)
lab = C.outline_label(M.outline[1])
SM.set_people(M, lab, "Avery Pine", "Rowan Hale")
SM.set_due(M, lab, "2026-12-01")
SM.set_direction(M, lab, "Lead with the ground station handover.")
pv = dict(SM.preview(M, lab))
check("a section's preview: author and due, PM direction", "Avery Pine" in pv["Author and due date"]
      and "2026-12-01" in pv["Author and due date"] and "handover" in pv["Management guidance"], pv)
check("... a subsection inherits its parent's lead", SD.section_people(M, lab)["lead"] == "Avery Pine")
g = SM.gaps(M)
check("sections still missing a lead or a due date", C.outline_label(M.outline[0]) in g["no_lead"] and lab not in g["no_due"], g)
check("changes for authors need a setup first", SM.changes_by_person(M) is None)

# ---------------------------------------------------------------- the page
from skqt import mainwin as MW
check("Setup sits in Plan, the Structure Builder part of it (3.74.0)", [k for g_, it in MW.RAIL if g_ == "Plan" for k, _t in it] == ["setups", "storyboards"])
w = MW.MainWindow(app, cfg, A.APP_VERSION); w.resize(1400, 900); w.show(); app.processEvents()
import unfiled as UF
w.work_on(UF.NAME); app.processEvents()
w.go("setups"); app.processEvents()
sp = w.setups_page
check("Setup opens on an effort with no matrix: Start with a structure", w.stack.currentWidget() is sp and w.review is None
      and sp.start_card.isVisibleTo(sp) and not sp.main.isEnabled())
check("Use these headings needs one", sp.use_headings("") is None)
sp.from_docx(outline)
check("From a Word outline fills the headings", "Orbit Operations" in sp.heads.toPlainText())
M2 = sp.use_headings()
check("Use these headings: a matrix with the structure, no Review", M2 is not None and w.review is not None and w.review.M is M2
      and len(M2.outline) == 3 and os.path.isfile(M2.path) and w.ws.get("compliance_path") == M2.path)
from PySide6.QtCore import Qt as _Qt
node = lambda lab: next(iter(sp.builder.btree.findItems(lab, _Qt.MatchExactly | _Qt.MatchRecursive, 0)), None)
L2 = C.outline_label(M2.outline[1])
check("the sections listed", all(node(C.outline_label(o)) is not None for o in M2.outline) and sp.builder.isVisibleTo(sp)
      and not sp.start_card.isVisibleTo(sp))
sp.builder.btree.setCurrentItem(node(L2)); app.processEvents()
check("picking a section shows it", sp.cur == L2)
sp.f_lead.setText("Avery Pine"); sp.f_with.setText("Rowan Hale, Kit Ash"); sp.f_due.setText("2026-12-01")
sp.f_pages.setText("lots")
check("pages must be a number", sp.save_section() is False)
sp.f_pages.setText("4"); sp.f_dir.setPlainText("Lead with the ground station handover.")
check("Save this section", sp.save_section())
import pagebudget as PB
check("... kept on the matrix: people, due, pages, direction", SM.people(M2, L2) == ("Avery Pine", "Rowan Hale, Kit Ash")
      and SM.due(M2, L2) == "2026-12-01" and PB.pages(M2, L2) == 4 and "handover" in SM.direction(M2, L2))
check("... the row shows them", node(L2).text(5) == "Avery Pine" and node(L2).text(6) == "2026-12-01" and node(L2).text(4).startswith("4"),
      [node(L2).text(i) for i in range(7)])
check("... and what it prints", "Avery Pine" in sp.prev.text() and "handover" in sp.prev.text())
sp.refresh()
sp.layer_boxes["pm"].setChecked(False)
check("a layer box turns its layer off", not SM.layers(M2)["pm"] and "pm" in SD.setup_of(M2)["layer_skip"]
      and "Management guidance" not in sp.prev.text())
out = os.path.join(tmp, "plain")
paths = sp.plain(out)
check("Plain setup writes the setup", paths and all(os.path.isfile(p) for p in paths))
body = "".join(text_of(p) for p in paths)
check("... with the section's lead, contributors and due date", "Avery Pine" in body and "Due: 2026-12-01" in body)
check("... and leaves out the layer that is off", "handover" not in body)
sp.layer_boxes["author"].setChecked(False)
body2 = "".join(text_of(p) for p in sp.plain(os.path.join(tmp, "plain2")))
check("the author layer off: no lead line", "Avery Pine" not in body2)
sp.layer_boxes["author"].setChecked(True); sp.layer_boxes["pm"].setChecked(True)
check("nothing changed since the last setup", sp.packets(os.path.join(tmp, "pk0")) == [])
sp.builder.btree.setCurrentItem(node(L2)); app.processEvents()
sp.f_dir.setPlainText("Lead with the handover, then the cost of ownership."); sp.save_section()
pk = sp.packets(os.path.join(tmp, "pk"))
check("Changes for authors: one Word file per person in the section", pk and len(pk) == 3
      and any("Avery Pine" in os.path.basename(p) for p in pk) and any("Kit Ash" in os.path.basename(p) for p in pk), pk)
check("... each with what changed in their sections", "cost of ownership" in text_of(pk[0]))
check("... and the next comparison starts there", sp.packets(os.path.join(tmp, "pk2")) == [])
made = []
w.setup_page.make_on_templates = lambda folder=None, opts=None, go=None, starts=None: made.append((opts, go)) or ["t"]
check("Make the setup makes it on the templates", sp.make() == ["t"] and made)
check("each volume's template shown", "Templates" in sp.tmpl.text())

# ---------------------------------------------------------------- the Structure Builder's button
w.go("structure"); app.processEvents()
from PySide6.QtWidgets import QPushButton
btn = [b for b in w.structure_page.findChildren(QPushButton) if b.text() == "Make the setup"]
check("the Structure Builder's Make templates is now Make the setup", len(btn) == 1
      and not [b for b in w.structure_page.findChildren(QPushButton) if b.text() == "Make templates"])
btn[0].click(); app.processEvents()
check("... and opens the Setup page", w.stack.currentWidget() is sp)
check("guide topic and page title", "setups" in __import__("skqt.guide", fromlist=["TOPIC"]).TOPIC
      and "setups" in __import__("skqt.pagetitles", fromlist=["TITLES"]).TITLES)
import roleaccess as RA
check("authors and production open it", RA.allowed("Author", "setups") and RA.allowed("Production", "setups"))
w.close()
n = sum(checks)
print(f"QT SETUP {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
