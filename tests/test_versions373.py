"""3.73.0 without a screen: outline versions. Version 1 recorded with a copy kept with the effort; edits made in the app;
version 2 compared before anything changes: wording changed, guidance changed in both (the app's note and the workbook's),
a row moved to a new section, a section renumbered, a row added and one removed, a requirement with no reference matched
by its wording, a renamed column. Accepted: matched rows keep their ids, app edits the new version leaves alone stay,
"ours" keeps the app's note, "theirs" takes the new one, a removed row kept as ours comes back, labels follow the
renumbered section, the section's direction written in the app stays, version 2 recorded. Re-importing the same workbook
no longer doubles a section's direction (3.71.0). Fictional content (Kestrel)."""
import copy, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", tempfile.mkdtemp())
import compliance as C, outlinexl as OX, outlinelayouts as OL, outlineversions as OV, setupdoc as SD

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


HEAD = ["Response Section Number", "Response Section Name", "RFPL Number", "Compliance Requirement", "Supporting RFP Content",
        "Authors", "Management Guidance"]


def build(path, rows, head=HEAD):
    """rows: (num, name, ref, requirement, [(look, text)], authors, guidance); look "cust" (purple) or "ital" (black italic)."""
    from openpyxl import Workbook
    from openpyxl.cell.rich_text import CellRichText, TextBlock
    from openpyxl.cell.text import InlineFont
    f = {"cust": InlineFont(color="FF6B21A8"), "ital": InlineFont(i=True, color="FF000000")}
    wb = Workbook(); ws = wb.active
    ws.append(["Kestrel Ground Segment: response outline"]); ws.append(head)
    for num, name, ref, req, sup, auth, guid in rows:
        ws.append([num, name, ref, req, None, auth, guid])
        if sup:
            ws.cell(row=ws.max_row, column=5).value = CellRichText([TextBlock(f[k], t) for k, t in sup])
    ws.column_dimensions["D"].width = 60
    from openpyxl.styles import Font, PatternFill
    for c in range(1, len(head) + 1):
        ws.cell(row=3, column=c).fill = PatternFill("solid", fgColor="FFF2E5")
        ws.cell(row=3, column=c).font = Font(name="Arial", size=9)
    wb.save(path)
    return path


V1 = [("1", "Technical Approach", "", "", [], "R. Diaz", "Lead with the mission thread."),
      ("1.1", "Ground Segment Architecture", "L.4.2.1", "The offeror shall describe its ground segment architecture.",
       [("cust", "The Government requires a resilient ground segment.")], "R. Diaz; J. Okafor", "Lead with the dual-site design."),
      ("1.1", "Ground Segment Architecture", "L.4.2.2", "The offeror shall describe its approach to cybersecurity.",
       [("ital", "Attachment J-3 lists the controls.")], "", ""),
      ("1.2", "Telemetry, Tracking and Command", "L.4.2.3", "The offeror shall describe its TT&C approach.", [], "S. Patel", ""),
      ("1.2", "Telemetry, Tracking and Command", "", "The offeror shall describe its staffing for the ground stations.", [], "", ""),
      ("1.3", "Mission Operations", "L.4.2.4", "The offeror shall describe its operations concept.", [], "", "")]
V2 = [("1", "Technical Approach", "", "", [], "R. Diaz", "Lead with the mission thread."),
      ("1.1", "Ground Segment Architecture", "L.4.2.1", "The offeror shall describe its ground segment architecture and its growth path.",
       [("cust", "The Government requires a resilient ground segment.")], "R. Diaz; J. Okafor", "Lead with the dual-site design and the growth path."),
      ("1.2", "Telemetry, Tracking and Command", "L.4.2.5", "The offeror shall describe its TT&C link margins.", [], "S. Patel", ""),
      ("1.2", "Telemetry, Tracking and Command", "", "The offeror shall describe its staffing for each of the ground stations.", [], "", ""),
      ("1.4", "Cybersecurity", "L.4.2.2", "The offeror shall describe its approach to cybersecurity.",
       [("ital", "Attachment J-3 lists the controls.")], "", ""),
      ("1.5", "Mission Operations", "L.4.2.4", "The offeror shall describe its operations concept.", [], "", "")]
tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg")
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
effort_path = os.path.join(ED, "Kestrel_Effort_List.xlsx")
lay = OL.load(cfg)[OL.STARTING]
lay["rules"]["support"].append({"color": "6B21A8", "italic": None, "bold": None, "kind": "customer"})
OL.put(cfg, OL.STARTING, lay)


def parsed(path):
    book = OX.read(path)
    return OX.parse(book, OL.profile(cfg, book)), book["headers"]


def fresh():
    M = C.Matrix(os.path.join(ED, "Kestrel_Matrix.xlsx"), "Kestrel")
    x1 = build(os.path.join(tmp, "Kestrel Outline.xlsx"), V1)
    p1, h1 = parsed(x1)
    OX.apply(M, p1, os.path.basename(x1))
    OV.record(M, p1, x1, effort_path, h1, OL.STARTING)
    return M


M = fresh()
v1 = OV.current(M)
check("version 1 recorded, a copy kept with the effort, each row with the ids it made", v1["v"] == 1
      and os.path.isfile(os.path.join(ED, "Outline Versions", "Kestrel Outline v1.xlsx")) and v1["rows"][1]["ids"]["req"]
      and v1["rows"][1]["ids"]["customer"], v1["rows"][1])
B = SD.by_id(M)
rid = lambda ref: next(i for i, r in SD.setup_of(M)["refs"].items() if r == ref)
id1, id2, id3, id4 = rid("L.4.2.1"), rid("L.4.2.2"), rid("L.4.2.3"), rid("L.4.2.4")
S = SD.setup_of(M)
S["notes"][id1] = "Lead with the dual-site design; cite the 2024 test."           # edited in the app
B[id4]["text"] = "The offeror shall describe its operations concept (CONOPS)."     # a fix made in the app
S["mgmt"]["1 Technical Approach"] = "Lead with the mission thread; open with the Kestrel story."
x2 = build(os.path.join(tmp, "Kestrel Outline 2.xlsx"), V2)
p2, h2 = parsed(x2)
ch = OV.compare(M, p2, h2)
kinds = sorted((c["kind"], c.get("what", "")) for c in ch)
find = lambda kind, what=None: [c for c in ch if c["kind"] == kind and (what is None or c["what"] == what)]
check("compared: the wording changed", any("growth path" in c["new"] for c in find("Changed", "wording")), kinds)
check("compared: the guidance changed in both (the app's note and the workbook's)", find("Changed", "guidance")
      and find("Changed", "guidance")[0]["both"] and "2024 test" in find("Changed", "guidance")[0]["ours"], find("Changed", "guidance"))
check("compared: a row moved to a new section, the section added", find("Moved") and find("Moved")[0]["new"] == "1.4 Cybersecurity"
      and find("Section added")[0]["new"] == "1.4 Cybersecurity")
check("compared: a section renumbered (not removed)", find("Renumbered") and find("Renumbered")[0]["old"] == "1.3 Mission Operations"
      and not find("Section removed"))
check("compared: a row added and one removed", find("Added")[0]["new"].startswith("The offeror shall describe its TT&C link")
      and find("Removed")[0]["old"].startswith("The offeror shall describe its TT&C approach"))
check("compared: a requirement with no reference matched by its wording", not any("staffing" in c["new"] for c in find("Added"))
      and any("staffing" in c["new"] for c in find("Changed", "wording")))
check("compared: an app fix the workbook left alone is not a change", not any("operations concept" in (c["old"] + c["new"]) for c in ch
      if c["kind"] in ("Changed", "Added", "Removed")))
check("one line for the person", "changed in both" in OV.summary(ch), OV.summary(ch))
check("nothing changed by comparing", SD.by_id(M)[id1]["text"].endswith("architecture.") and len(M.outline) == 4)
gi = find("Changed", "guidance")[0]["i"]
res = OV.accept(M, p2, x2, {gi: "ours"}, effort_path, h2, OL.STARTING)
B = SD.by_id(M); S = SD.setup_of(M)
check("accepted: matched rows keep their ids", id1 in B and id2 in B and id4 in B)
check("the new wording is in; ours kept the app's note", B[id1]["text"].endswith("growth path.") and "2024 test" in S["notes"][id1], S["notes"].get(id1))
check("the moved row is under the new section, same id", B[id2]["map"] == "1.4 Cybersecurity")
check("the renumbered section's label followed: the app's fix stays, under 1.5", B[id4]["map"] == "1.5 Mission Operations" and "CONOPS" in B[id4]["text"])
check("the removed row is gone; the added one has a new id no version used", id3 not in B
      and S["refs"].get(next(i for i, r in S["refs"].items() if r == "L.4.2.5")) == "L.4.2.5"
      and next(i for i, r in S["refs"].items() if r == "L.4.2.5") != id3)
check("the section's direction written in the app stays", S["mgmt"].get("1 Technical Approach") == "Lead with the mission thread; open with the Kestrel story.",
      S["mgmt"].get("1 Technical Approach"))
check("version 2 recorded, its copy kept", OV.current(M)["v"] == 2 and os.path.isfile(os.path.join(ED, "Outline Versions", "Kestrel Outline 2 v2.xlsx")))
check("each item once in its section", sum(1 for lab, ids in S["order"].items() for i in ids if i == id1) == 1)
# ---- written back out in its own layout
import outlinewrite as OW
from openpyxl import load_workbook
out = os.path.join(tmp, "Kestrel Outline (next).xlsx")
wr = OW.write_back(M, out, cfg, effort_path)
wb = load_workbook(out, rich_text=True); ws = wb.worksheets[0]
check("written back: its title row, headings and column widths stay", ws["A1"].value == "Kestrel Ground Segment: response outline"
      and [c.value for c in ws[2]][:7] == HEAD and ws.column_dimensions["D"].width == 60)
cells = {(r[1].value, r[2].value): r for r in ws.iter_rows(min_row=3) if r[2].value}
sup = cells[("Ground Segment Architecture", "L.4.2.1")][4].value
check("each row's cells in the pattern row's style", all(r[0].fill.fgColor.rgb in ("00FFF2E5", "FFFFF2E5") and r[0].font.name == "Arial"
      for r in ws.iter_rows(min_row=3)), [r[0].fill.fgColor.rgb for r in ws.iter_rows(min_row=3)][:3])
check("mixed text written in the looks the layout gives it (purple customer text)", hasattr(sup, "__iter__") and not isinstance(sup, str)
      and any(getattr(b, "font", None) is not None and (b.font.color is not None and str(b.font.color.rgb).endswith("6B21A8")) for b in sup), sup)
check("the effort as it is now: the moved row under 1.4, the app's fix in, ours kept", ("Cybersecurity", "L.4.2.2") in cells
      and "CONOPS" in cells[("Mission Operations", "L.4.2.4")][3].value and "2024 test" in cells[("Ground Segment Architecture", "L.4.2.1")][6].value)
chs = wb["Changes"]
lines = [" | ".join(str(c.value or "") for c in r) for r in chs.iter_rows(min_row=2)]
check("one Changes sheet: every change from the last version", wr["changes"] == len(lines) and any("CONOPS" in x for x in lines), lines)
book = OX.read(out); pw = OX.parse(book, OL.profile(cfg, book))
key = lambda r: (r["section"], r["ref"], r["req"], tuple(r["customer"]), tuple(r["support"]), r["guidance"])
check("read back, it is exactly what the effort holds (a clean round trip)", [key(r) for r in OV.rows_of(pw)]
      == [key(r) for r in OW.rows_now(M)[0]], ([key(r) for r in OV.rows_of(pw)][:3], [key(r) for r in OW.rows_now(M)[0]][:3]))
check("the kept workbook is only read", os.path.getsize(os.path.join(ED, "Outline Versions", "Kestrel Outline 2 v2.xlsx")) > 0
      and "Changes" not in load_workbook(os.path.join(ED, "Outline Versions", "Kestrel Outline 2 v2.xlsx")).sheetnames)
# ---- theirs, and a removed row kept as ours
M = fresh(); S = SD.setup_of(M)
id1, id3 = rid("L.4.2.1"), rid("L.4.2.3")
S["notes"][id1] = "Lead with the dual-site design; cite the 2024 test."
ch = OV.compare(M, p2, h2)
gi = next(c["i"] for c in ch if c["kind"] == "Changed" and c["what"] == "guidance")
ri = next(c["i"] for c in ch if c["kind"] == "Removed")
OV.accept(M, p2, x2, {gi: "theirs", ri: "ours"}, effort_path, h2, OL.STARTING)
B = SD.by_id(M); S = SD.setup_of(M)
check("theirs: the new version's note", S["notes"][id1] == "Lead with the dual-site design and the growth path.", S["notes"].get(id1))
check("a removed row kept as ours comes back, same id, placed", id3 in B and B[id3]["map"] == "1.2 Telemetry, Tracking and Command"
      and id3 in S["order"].get("1.2 Telemetry, Tracking and Command", []))
# ---- a renamed column
x3 = build(os.path.join(tmp, "Kestrel Outline 3.xlsx"), V2, HEAD[:3] + ["L Requirement"] + HEAD[4:])
OL.remember(cfg, OL.STARTING, "L Requirement", "requirement")
p3, h3 = parsed(x3)
check("a renamed column is a change", any(c["kind"] == "Column renamed" and c["new"] == "L Requirement" for c in OV.compare(M, p3, h3)))
# ---- an RFP paragraph renumbered, its words the same: one change (the reference), not a row removed and one added
V4 = [r if r[2] != "L.4.2.4" else (r[0], r[1], "L.4.3.1", r[3], r[4], r[5], r[6]) for r in V2]
p4, h4 = parsed(build(os.path.join(tmp, "Kestrel Outline 4.xlsx"), V4))
ch4 = [c for c in OV.compare(M, p4, h4) if c["kind"] in ("Added", "Removed", "Changed")]
check("an RFP paragraph renumbered with the same words: Changed (reference) only", [(c["kind"], c["what"], c["new"]) for c in ch4]
      == [("Changed", "reference", "L.4.3.1")], [(c["kind"], c["what"], c["new"]) for c in ch4])
# ---- 3.71.0: the same workbook again no longer doubles a section's direction
M2 = C.Matrix(os.path.join(ED, "Kestrel_Matrix2.xlsx"), "Kestrel")
x1 = os.path.join(tmp, "Kestrel Outline.xlsx")
p1, _h = parsed(x1)
OX.apply(M2, p1, "Kestrel Outline.xlsx"); OX.apply(M2, p1, "Kestrel Outline.xlsx")
check("importing the same workbook again: the section's direction once", SD.setup_of(M2)["mgmt"]["1 Technical Approach"] == "Lead with the mission thread.",
      SD.setup_of(M2)["mgmt"].get("1 Technical Approach"))

print(f"VERSIONS 373 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
if __name__ == "__main__":                                   # qt_versions373 imports the workbook maker
    sys.exit(0 if all(checks) else 1)
