"""3.73.0 offscreen (decision 10): What's in your workbook, one list. A column whose cells mix red requirement text,
black guidance and italic supporting text has a row for each look; red is the compliance requirement before anyone
picks; the cells are shown piece by piece and a click on a piece changes every piece that looks the same; a structure
pick takes the whole column; every column of text is read; Use this structure keeps the picks in the layout, so the next
import asks nothing. Fictional content (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, outlinelayouts as OL
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


MIXED = "Requirement / Guidance"


def make(path):
    from openpyxl import Workbook
    from openpyxl.cell.rich_text import CellRichText, TextBlock
    from openpyxl.cell.text import InlineFont
    wb = Workbook(); ws = wb.active
    ws.append(["Response Section Number", "Response Section Name", "RFPL Number", MIXED, "Supporting RFP Content", "Context", "Notes"])
    red, black, ital = InlineFont(color="FFC00000"), InlineFont(color="FF000000"), InlineFont(i=True, color="FF000000")
    rows = [("1", "Technical Approach", "", None, None, None, "kick off"),
            ("1.1", "Ground Segment Architecture", "L.4.2.1",
             CellRichText([TextBlock(red, "The offeror shall describe its ground segment architecture.\n"),
                           TextBlock(black, "Lead with the dual-site design.\n"),
                           TextBlock(ital, "See SOW C.3.4 for the station locations.")]),
             "Attachment J-3 lists the stations.", "The stations share one operations floor.", ""),
            ("1.2", "Telemetry, Tracking and Command", "L.4.2.2",
             CellRichText([TextBlock(red, "The offeror shall describe its TT&C approach.\n"),
                           TextBlock(black, "Show the S-band and X-band paths.")]), "", "", "")]
    for r in rows:
        ws.append(["" if v is None else v for v in r[:3]] + [None, r[4], r[5], r[6]])
        ws.cell(row=ws.max_row, column=4).value = r[3]
    wb.save(path)
    return path


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
LIST = os.path.join(ED, "Kestrel_Effort_List.xlsx"); L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
xl = make(os.path.join(tmp, "Kestrel Outline.xlsx"))
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel")
w.go("setups"); app.processEvents()
pg = w.setups_page
pg.from_outline(xl, accept=False)
d = pg.outline_dialog
mixed = [lk for h, lk, _s, _n in d.list_rows if h == MIXED]
check("one list: the mixed column has a row for each look (red, black, italic)", set(mixed) == {"--C00000", "--auto", "-Iauto"}, mixed)
check("the colors in plain words", "red:" in d.list.cellWidget(d.row_of(MIXED, "--C00000"), 1).text() and "#C00000" in d.list.cellWidget(d.row_of(MIXED, "--C00000"), 1).toolTip())
check("red is the compliance requirement before anyone picks", d.pick_of(MIXED, "--C00000") == "rfp")
check("a column with one kind of text is one row", len([1 for h, *_r in d.list_rows if h == "Context"]) == 1)
cb = d.list.cellWidget(d.row_of(MIXED, "--auto"), 3); cb.setCurrentIndex(cb.findData("pm")); app.processEvents()
cb = d.list.cellWidget(d.row_of(MIXED, "-Iauto"), 3); cb.setCurrentIndex(cb.findData("support")); app.processEvents()
s11 = next(s for s in d.parsed["sections"] if s["num"] == "1.1")
kinds = [(b["kind"], b["text"][:22]) for b in s11["blocks"]]
check("each piece of the mixed cell goes to its own kind", ("rfp", "The offeror shall desc") in kinds and ("pm", "Lead with the dual-sit") in kinds
      and ("support", "See SOW C.3.4 for the ") in kinds, kinds)
check("every column of text is read, not only the first of a kind", any(t.startswith("The stations share") for _k, t in
      [(b["kind"], b["text"]) for b in s11["blocks"]]) and any(t.startswith("Attachment J-3") for t in [b["text"] for b in s11["blocks"]]), kinds)
check("the requirement keeps its RFP reference", next(b["ref"] for b in s11["blocks"] if b["kind"] == "rfp") == "L.4.2.1")
d.list.setCurrentCell(d.row_of(MIXED), 0); app.processEvents()
check("cells, piece by piece: each piece marked with what it is", d.cells_col == MIXED and "[Compliance requirement]" in d.cell_html
      and "[Management guidance]" in d.cell_html and 'href="pick:3:--auto"' in d.cell_html, d.cell_html[:300])
d.piece_menu("pick:3:--auto", pick="customer"); app.processEvents()
check("a click on a piece changes every piece that looks the same", d.pick_of(MIXED, "--auto") == "customer"
      and d.list.cellWidget(d.row_of(MIXED, "--auto"), 3).currentData() == "customer"
      and all(b["kind"] != "pm" for s in d.parsed["sections"] for b in s["blocks"]))
d.piece_menu("pick:3:--auto", pick="pm"); app.processEvents()
cb = d.list.cellWidget(d.row_of("Context"), 3); cb.setCurrentIndex(cb.findData("authors")); app.processEvents()
check("a structure pick takes the whole column", d.profile["columns"]["Context"] == "authors" and "Context" not in d.profile["rules"])
cb = d.list.cellWidget(d.row_of("Context"), 3); cb.setCurrentIndex(cb.findData("support")); app.processEvents()
check("a kind of text on a whole column makes it a column of text again", d.profile["columns"]["Context"] == "support"
      and d.pick_of("Context", "--auto") == "support")
d.close()
# Use this structure, with the same picks (made again by a fresh window, then used)
pg.from_outline(xl, accept=False); d2 = pg.outline_dialog
for lk, k in (("--auto", "pm"), ("-Iauto", "support")):
    cb = d2.list.cellWidget(d2.row_of(MIXED, lk), 3); cb.setCurrentIndex(cb.findData(k)); app.processEvents()
kept = d2.learn(); d2.close()
lay = OL.load(cfg)[OL.STARTING]
check("Use this structure keeps the picks in the layout", kept >= 2 and OL.role_of(lay, MIXED) == "requirement"
      and OL.rule_kind(lay, "requirement", "--auto") == "pm" and OL.rule_kind(lay, "requirement", "-Iauto") == "support", (kept, lay.get("rules")))
pg.from_outline(xl, accept=False); d3 = pg.outline_dialog
check("the next import of this layout asks nothing", not d3.profile["unknown"] and d3.pick_of(MIXED, "--auto") == "pm"
      and d3.pick_of(MIXED, "-Iauto") == "support" and d3.pick_of(MIXED, "--C00000") == "rfp", (d3.profile["unknown"], d3.profile["rules"]))
d3.close()

print(f"QT ONE LIST 373 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
