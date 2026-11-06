"""3.73.0 without a screen: the compliance matrix exported, edited in Excel and brought back. The export is a version kept
with the effort with its design. The outline matrix: assigned to, page allocation and % complete filled in the workbook
come back, matched by item; a value changed in the app since the export too is changed in both and waits for a pick.
The sentence matrix: author(s), notes and the team's own column come back, matched by reference and wording; rows added
or left out in the workbook are listed, never applied. Another copy's matrix merges: every difference keeps ours unless
taken. A workbook in another design is refused in plain words. Fictional content (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", tempfile.mkdtemp())
import compliance as C, outlinexl as OX, outlinelayouts as OL, setupdoc as SD, pagebudget as PB, matrixdesign as MD, matrixversions as MV
from openpyxl import load_workbook

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


import test_versions373 as TV                                  # its outline workbook (its own checks run too)
tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg")
ED = os.path.join(tmp, "Kestrel"); os.makedirs(ED)
effort_path = os.path.join(ED, "Kestrel_Effort_List.xlsx")
M = C.Matrix(os.path.join(ED, "Kestrel_Matrix.xlsx"), "Kestrel")
x1 = TV.build(os.path.join(tmp, "Kestrel Outline.xlsx"), TV.V1)
book = OX.read(x1)
OX.apply(M, OX.parse(book, OL.profile(cfg, book)), os.path.basename(x1))


def edit(path, changes, add=None, drop=None):
    """changes: {(row label in the first column given, heading): value}."""
    wb = load_workbook(path); ws = wb["Compliance Matrix"]
    hr = next(r for r in range(1, 10) if any(c.value for c in ws[r]) and sum(1 for c in ws[r] if c.value) >= 3)
    heads = [c.value for c in ws[hr]]
    for (key_head, key_val, head), val in changes.items():
        kc = heads.index(key_head) + 1
        r = next(r for r in range(hr + 1, ws.max_row + 1) if str(ws.cell(row=r, column=kc).value or "").strip().startswith(key_val))
        ws.cell(row=r, column=heads.index(head) + 1).value = val
    if drop:
        kc = heads.index(drop[0]) + 1
        r = next(r for r in range(hr + 1, ws.max_row + 1) if str(ws.cell(row=r, column=kc).value or "").startswith(drop[1]))
        ws.delete_rows(r)
    if add:
        ws.append([add.get(h, "") for h in heads])
    wb.save(path)
    return path


# ---- the outline matrix
d = MD.default("outline")
out = os.path.join(tmp, "Kestrel_Compliance_Matrix.xlsx")
MD.export(M, out, d, "Kestrel")
v = MV.record(M, out, d, effort_path)
check("an export is a version kept with the effort, with its design", v["v"] == 1 and os.path.isfile(os.path.join(ED, "Matrix Versions",
      "Kestrel_Compliance_Matrix v1.xlsx")) and v["design"]["layout"] == "outline")
SD.set_progress(M, "1.2 Telemetry, Tracking and Command", 10)                    # the app, after the export
H = {k: MD.heading_of(k) for k in MD.OUTLINE_KEYS}
edit(out, {("Response Section No. Item", "1.1 Ground", H["assigned_to"]): "R. Diaz, K. Lee",
           ("Response Section No. Item", "1.1 Ground", H["pct_complete"]): "40%",
           ("Response Section No. Item", "1.1 Ground", H["page_alloc"]): "6",
           ("Response Section No. Item", "1.2 Telemetry", H["pct_complete"]): "25%"})
ch = MV.compare(M, out, effort_path=effort_path)
got = sorted((c["label"], c["what"], c["new"], c["both"]) for c in ch if c["kind"] == "Changed")
check("the team's values come back, matched by item", ("1.1 Ground Segment Architecture", "assigned to", "R. Diaz, K. Lee", False) in got
      and ("1.1 Ground Segment Architecture", "% complete", "40%", False) in got and ("1.1 Ground Segment Architecture", "page allocation", "6", False) in got, got)
check("a value changed in the app since the export too: changed in both", ("1.2 Telemetry, Tracking and Command", "% complete", "25%", True) in got, got)
check("nothing else is a change", len(got) == 4 and not [c for c in ch if c["kind"] != "Changed"], ch)
both = next(c["i"] for c in ch if c["both"])
n = MV.accept(M, ch, {}, out, effort_path=effort_path)
check("accepted without a pick: the change in both keeps ours", n == 3 and SD.progress_of(M, "1.2 Telemetry, Tracking and Command") == 10)
check("the values are in the effort", SD.section_people(M, "1.1 Ground Segment Architecture")["with"] == "K. Lee"
      and SD.progress_of(M, "1.1 Ground Segment Architecture") == 40 and PB.pages(M, "1.1 Ground Segment Architecture") == 6)
MV.accept(M, ch, {both: "theirs"})
check("theirs, picked: the workbook's value", SD.progress_of(M, "1.2 Telemetry, Tracking and Command") == 25)
# ---- the sentence matrix
ds = MD.default("sentences")
ds["columns"].append({"key": MD.CUSTOM + "Writer status", "heading": "Writer status"})
out2 = os.path.join(tmp, "Kestrel_Sentences.xlsx")
MD.export(M, out2, ds, "Kestrel")
MV.record(M, out2, ds, effort_path)
edit(out2, {("RFP content", "The offeror shall describe its approach to cyber", "Author(s)"): "J. Okafor",
            ("RFP content", "The offeror shall describe its approach to cyber", "Notes"): "Use the Kestrel controls table.",
            ("RFP content", "The offeror shall describe its approach to cyber", "Writer status"): "Drafting"},
     add={"RFP content": "A row typed in Excel."}, drop=("RFP content", "The offeror shall describe its operations concept"))
ch2 = MV.compare(M, out2, effort_path=effort_path)
kinds = sorted({c["kind"] for c in ch2})
check("sentences: author(s), notes and the team's own column come back", sorted(c["what"] for c in ch2 if c["kind"] == "Changed")
      == ["Writer status", "author(s)", "notes"], [(c["kind"], c["what"]) for c in ch2])
check("rows added or left out are listed", "Row added in the workbook" in kinds and "Row left out of the workbook" in kinds, kinds)
MV.accept(M, ch2, {}, out2, effort_path=effort_path)
it = next(i for i in M.items if i.get("text", "").startswith("The offeror shall describe its approach to cyber"))
check("the sentence's owner, notes and column are in", it["owner"] == "J. Okafor" and it["notes"] == "Use the Kestrel controls table."
      and it["cols"]["Writer status"] == "Drafting")
check("rows added or left out are never applied", not any(i.get("text") == "A row typed in Excel." for i in M.items)
      and any(i.get("text", "").startswith("The offeror shall describe its operations concept") for i in M.items))
# ---- another copy's matrix, merged
theirs = os.path.join(tmp, "Their_Matrix.xlsx")
MD.export(M, theirs, d, "Kestrel")
edit(theirs, {("Response Section No. Item", "1.3 Mission", H["assigned_to"]): "S. Patel"})
ch3 = MV.compare(M, theirs, design=d, merge=True)
check("merging another copy: the difference is listed, ours kept unless taken", len(ch3) == 1 and ch3[0]["both"]
      and MV.accept(M, ch3, {}) == 0 and MV.accept(M, ch3, {ch3[0]["i"]: "theirs"}) == 1
      and SD.section_people(M, "1.3 Mission Operations")["lead"] == "S. Patel", ch3)
# ---- a workbook in another design
try:
    MV.read(x1, d); refused = False
except ValueError as e:
    refused = "design" in str(e)
check("a workbook in another design is refused in plain words", refused)

print(f"MATRIX VERSIONS 373 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
if __name__ == "__main__":                                   # qt_matrixback373 imports its workbook editor
    sys.exit(0 if all(checks) else 1)
