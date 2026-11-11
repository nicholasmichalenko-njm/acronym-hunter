"""3.89.0 Compare on the page, offscreen: adding an amendment flags the placed sentences it touches at once (decision 6);
Compare shows the amendment's own page with each change marked, our response on the right, lines for the selected change
only, and the decide bar beside the change, never over it; the suggestion with its reason, Enter takes it and goes on;
a click in Our response changes the target; Add to a section, Remove, No action for every editorial change; the summary
line filters; the flags show in Review and Setup until the change is decided and open the change; the Verify line and its
next step; the bar holds five commands; Storyboards stays off the menu even with the pages set aside shown. Fictional
content (Kestrel)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SHRED_CLASSIC"] = "1"           # 4.5.0: tests the machinery under the focused Shred screen
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ["SK_THEME"] = "light"
import app_gui as A
import effort as E, workspace as W, office_pdf as OP, pdfmini, changereview as CR, homesuggest as HS, menufocus as MF
OP.available = lambda: False
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
from skqt import amendflags as AF

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); CUST = os.path.join(EDIR, "Customer documents"); os.makedirs(CUST)
IN = os.path.join(tmp, "incoming"); os.makedirs(IN)
BASE = ["L.3 PROPOSAL VOLUMES",
        "Volume I Technical shall not exceed 50 pages.",
        "L.4 RISK MANAGEMENT",
        "The Offeror shall identify the five highest program risks.",
        "The Offeror shall provide a risk burn-down chart for each risk.",
        "The Offeror shall name an owner for each risk.",
        "L.5 TRANSITION",
        "The Offeror shall describe its transition approach in ninety days."]
AMD = ["L.3 PROPOSAL VOLUMES",
       "Volume I Technical shall not exceed 40 pages.",
       "L.4 RISK MANAGEMENT",
       "The Offeror shall identify the ten highest program risks.",
       "The offeror shall name an owner for each risk.",
       "The Offeror shall describe a mitigation plan for each high risk.",
       "L.5 TRANSITION",
       "The Offeror shall describe its transition approach in ninety days."]
P1 = os.path.join(IN, "Kestrel_Section_L.pdf"); pdfmini.write(P1, [BASE], size=9)
P2 = os.path.join(IN, "Kestrel_Section_L_Amd1.pdf"); pdfmini.write(P2, [AMD], size=9)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST, customer_dir=CUST)
W.Workspace(W.data_dir_for(LIST), "Kestrel").set("outline_text", "Volume I Technical\n1.1 Technical Approach\n1.2 Risk Management\n1.3 Transition")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Kestrel")
w.go("docs"); app.processEvents()
w.docs_page.add([P1], choices=[{}])
C1 = os.path.join(CUST, "Kestrel_Section_L.pdf")
w.read_page.read([C1], os.path.join(EDIR, "Kestrel_Compliance_Matrix.xlsx"), identities="suggested")
check("read", wait(lambda: w.review is not None))
M = w.review.M
by = lambda s: next(it for it in M.items if s in it["text"])                                           # noqa: E731
pages50, five, burn, owner = by("50 pages"), by("five highest"), by("burn-down"), by("owner for each")
w.review.req([pages50], "1.1 Technical Approach")
w.review.req([five, burn, owner], "1.2 Risk Management")
HS.map_heading(M, "L.4", "1.2 Risk Management")
w.changed(); w.save_now()
# the amendment comes in: decision 6 at once
w.go("docs"); app.processEvents()
d, v = w.docs_page.add([P2], choices=[{}])[0]
fl = AF.flags(w)
check("adding the amendment flags the placed sentences it touches, before Compare is opened",
      fl.get(pages50["id"], [{}])[0].get("text") == "Changed in Amendment 1" and fl.get(burn["id"], [{}])[0].get("text") == "Removed in Amendment 1", fl)
check("... the sentences keep their place", pages50["map"] == "1.1 Technical Approach" and burn["map"] == "1.2 Risk Management")
# Review shows them
pg = w.assign_page
w.go("assign"); app.processEvents()
pg.open_file("Kestrel_Section_L.pdf"); app.processEvents()
pg.restyle()
labs = [x.text() for x in pg.labels]
check("Review: the flag beside the sentence on the page", any(t.startswith("Changed in Amendment 1") for t in labs)
      and any(t.startswith("Removed in Amendment 1") for t in labs), labs)
pg.select(pages50["id"]); app.processEvents()
check("... and on the selection, with the link to the change", "Changed in Amendment 1" in pg.placer.home_lbl.text()
      and "amend:" in pg.placer.home_lbl.text(), pg.placer.home_lbl.text())
check("... the Left line counts them", "changed by an amendment" in pg.placer.left_lbl.text(), pg.placer.left_lbl.text())
# Setup shows them
w.go("setups"); app.processEvents()
bl = w.setups_page.blocks
bl.fill("1.1 Technical Approach")
check("Setup: the block says it changed", any("Changed in Amendment 1" in bl.item(k).text() for k in range(bl.count())),
      [bl.item(k).text() for k in range(bl.count())])
# Compare on the page
w.go("compare"); app.processEvents()
cp = w.compare_page
rows = cp.show(d["id"], None, v["id"])
ch = [i for i, r in enumerate(rows) if r["kind"] != "same"]
check("the amendment's own page, not a table", cp.pdf and cp.pdf.endswith("Kestrel_Section_L_Amd1.pdf") and not hasattr(cp, "table"), cp.pdf)
check("every change is marked on the page", all(i in cp.view.boxes for i in ch if rows[i]["kind"] != "removed")
      and any(cp.placed[rows[i]["key"]].get("removed") for i in ch if rows[i]["kind"] == "removed"))
check("the summary counts and links", all(s in cp.sum.text() for s in ("touch placed sentences", "editorial", "to decide", "href='placed'")),
      cp.sum.text())
check("... and the finish line", cp.p_dec.text() == f"0 of {len(ch)} decided", cp.p_dec.text())
check("the bar holds five commands at most", len(cp.bar.visible_commands()) <= 5)
hit = next(i for i in ch if "40 pages" in rows[i]["new"])
cp.select(hit); app.processEvents()
bar = cp.decide_panel
check("the suggestion, with its reason", bar.sugg["kind"] == "updates" and bar.sugg["target"] == pages50["id"]
      and "has the old wording" in bar.hint.text(), bar.hint.text())
check("the word change in the bar", "line-through" in bar.words.text() and "40" in bar.words.text())
br, sel = bar.geometry(), cp.view.view_rect(hit)
check("the bar opens beside the change, never over it", bar.isVisible() and not br.intersects(sel), (br, sel))
check("our response: the touched sentence under its section, flagged", pages50["id"] in cp.nodes
      and "Changed in Amendment 1" in cp.nodes[pages50["id"]].text(0))
check("a line for the selected change only, to the placed sentence", [x[4] for x in cp.gutter.compute()] == ["placed"], cp.gutter.drawn)
if os.environ.get("SHOT_DIR"):
    w.grab().save(os.path.join(os.environ["SHOT_DIR"], "compare_changed.png"))
# Enter takes it, then the next to decide
bar.take(); app.processEvents()
check("Enter: Update our wording; the old wording in its history", "exceed 40 pages" in w.review.item(pages50["id"])["text"]
      and CR.Review(w.ws.root).load().history(pages50["id"])[0]["old"].count("50 pages") == 1)
check("... and the next change to decide is selected", cp.i != hit and not cp.decided(cp.i))
check("... its flag is off in Review and Setup", pages50["id"] not in AF.flags(w))
# an added requirement: the section its heading maps to, a dotted line
add = next(i for i in ch if rows[i]["kind"] == "added")
cp.select(add); app.processEvents()
check("an added requirement: Add to the section L.4 maps to", bar.sugg["kind"] == "new" and bar.sugg["target"] == "1.2 Risk Management")
check("... a dotted line to that section", ("suggested" in [x[4] for x in cp.gutter.compute()]), cp.gutter.drawn)
sec13 = cp.sec_nodes["1.3 Transition"]
cp.tree_clicked(sec13, 0)
check("a click on a section in Our response changes the target", bar.sec_target == "1.3 Transition" and "1.3 Transition" in bar.hint.text())
dec = bar.decide("new")
newit = next(it for it in w.review.M.items if "mitigation plan" in it["text"])
check("Add to a section: the requirement is there", dec and newit["map"] == "1.3 Transition")
# a removed sentence
rm = next(i for i in ch if rows[i]["kind"] == "removed")
cp.select(rm); app.processEvents()
check("a removed sentence that is placed: Remove, suggested", bar.sugg["kind"] == "removes" and bar.sugg["target"] == burn["id"])
bar.decide("removes")
check("Remove: marked removed, never deleted; it keeps its place", w.review.item(burn["id"])["new"].startswith("Removed by")
      and w.review.item(burn["id"])["map"] == "1.2 Risk Management")
# editorial
cp.set_tag_filter("editorial"); app.processEvents()
check("the editorial link filters", len(cp.shown) == 1 and "Show all" in cp.sum.text())
n = cp.editorial_all()
check("Editorial changes: No action for all", n == 1 and any(x["why"] == "editorial" for x in CR.Review(w.ws.root).load().decisions(cp.pk, rows[cp.shown[0]]["key"])))
cp.set_tag_filter("all")
cp.select(rm); app.processEvents()
undo_ok = bar.undo(CR.Review(w.ws.root).load().decisions(cp.pk, rows[rm]["key"])[0]["id"])
check("a decision taken off undoes itself", undo_ok and not w.review.item(burn["id"])["new"].startswith("Removed by"))
check("... and the flag comes back", burn["id"] in AF.flags(w))
# the flag opens the change
w.go("assign"); app.processEvents()
f = AF.flags(w)[burn["id"]][0]
check("a flag opens its change in Compare", AF.open_change(w, f) and cp.i == rm and w.stack.currentWidget() is w.compare_space)
# the Verify line and its next step
check("the Verify line says how many pages a person verified", "pages verified" in cp.vline.text() and "Verify its pages" in cp.vline.text(),
      cp.vline.text())
check("... and goes to Verify on that document", cp.verify_pages() and w.verify_page.doc == "Kestrel_Section_L_Amd1.pdf")
vp = w.verify_page
vp.store().verify(vp.doc, 1); vp.show_page(); app.processEvents()
check("Verify's last page, verified: the next step is Compare", "Next: compare Amendment 1 with Original" in vp.line.text(), vp.line.text())
check("... and it opens the pair", vp.compare_next() and w.stack.currentWidget() is w.compare_space and cp.cur[2]["id"] == v["id"])
# Storyboards off the menu, even with the pages set aside shown
check("Storyboards stays off the menu, even with the pages set aside shown", "storyboards" in MF.hidden({MF.SETTING: True})
      and "storyboards" in MF.hidden({}))
if os.environ.get("SHOT_DIR"):
    w.go("compare"); cp.select(add); app.processEvents()
    w.grab().save(os.path.join(os.environ["SHOT_DIR"], "compare_on_the_page.png"))
w.close()
n = sum(checks)
print(f"QT COMPARE 389 PASS ({n}/{len(checks)})" if n == len(checks) else f"QT COMPARE 389 FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
