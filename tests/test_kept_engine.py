"""3.14.0 engine checks that only the classic window's tests held, kept when the classic window retired: a workbook open
in Excel is reported as locked and the file on disk is left exactly as it was (the matrix and the Effort List); review
progress per file; several authors on one sentence; the matrix design preview; the RFP's suggested headers; the
activity log's recent lines; finding an offering by name."""
import os, sys, shutil, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_kept"
import compliance as C, effort as E, setupdoc as SD, matrixdesign as MD, rfpoutline as RO, diag, offerings, workspace as W

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()

# ------------------------------------------------------------------ open in Excel: locked, original untouched, no temp left
BLANK = {"decision": "", "map": "", "owner": "", "status": "", "notes": "", "response_page": "", "links": "", "new": "",
         "learned": "", "loc": "", "kind": "", "ref": ""}


def items():
    rows = [{"id": "L-01", "file": "Section_L.pdf", "text": "TECHNICAL APPROACH", "decision": ""},
            {"id": "L-02", "file": "Section_L.pdf", "text": "The Offeror shall describe its technical approach.", "decision": "Keep",
             "owner": "A. Lee, K. Park"},
            {"id": "L-03", "file": "Section_L.pdf", "text": "The Offeror shall provide a risk register.", "decision": ""},
            {"id": "M-01", "file": "Section_M.pdf", "text": "Proposals are evaluated on technical merit.", "decision": "Context"}]
    return [dict(BLANK, key=C.text_key(r["text"]), **{k: v for k, v in r.items()}) for r in rows]


MP = os.path.join(tmp, "Kestrel_Compliance_Matrix.xlsx")
M = C.Matrix(MP, "Kestrel"); M.items = items(); M.save()
before = open(MP, "rb").read()
real = W.replace_retry


def refuse(src, dst, **k):
    raise PermissionError(dst)


W.replace_retry = refuse
M.items.append(dict(BLANK, id="L-04", file="Section_L.pdf", text="Added while open.", key="added while open"))
try:
    M.save(); raised = None
except C.Locked as e:
    raised = e
check("a matrix open in Excel: Locked names the file", raised is not None and MP in str(raised), raised)
check("... the workbook on disk is exactly as it was", open(MP, "rb").read() == before)
check("... and no temporary copy is left beside it", not [f for f in os.listdir(tmp) if f.startswith(".matrix_")], os.listdir(tmp))
LP = os.path.join(tmp, "Kestrel_Effort_List.xlsx")
W.replace_retry = real
L = E.EffortList(LP, "Kestrel"); L.pending = True; L.save()
lbefore = open(LP, "rb").read()
W.replace_retry = refuse
L.pending = True
try:
    L.save(); lraised = None
except E.ListLocked as e:
    lraised = e
W.replace_retry = real
check("an Effort List open in Excel: ListLocked, and the list on disk is untouched", lraised is not None and open(LP, "rb").read() == lbefore)

# ------------------------------------------------------------------ review progress
pg = C.progress(items())
f = {x["file"]: x for x in pg["files"]}
check("progress: decided over total, overall and per file", pg["total"] == 4 and pg["decided"] == 2 and pg["pct"] == 50
      and f["Section_L.pdf"]["decided"] == 1 and f["Section_M.pdf"]["pct"] == 100, pg)

# ------------------------------------------------------------------ several authors
M2 = C.Matrix(os.path.join(tmp, "m2.xlsx"), "K"); M2.items = items()
check("a sentence with several authors lists each", SD.owners_list(M2, M2.items[1]) == ["A. Lee", "K. Park"], SD.owners_list(M2, M2.items[1]))
check("... names split on commas and semicolons, spaces tidied", SD.split_names(" A. Lee ;K.  Park, ") == ["A. Lee", "K. Park"])

# ------------------------------------------------------------------ matrix design preview
d = MD.default()
heads, rows, n = MD.preview(M2, d)
check("the design preview: one heading per column, every row unless a count is given",
      len(heads) == len(d["columns"]) and n == len(rows) and n >= 1, (heads, n))
_h, rows1, n1 = MD.preview(M2, d, n=1)
check("... a count limits the rows shown, not the total", len(rows1) == 1 and n1 == n)

# ------------------------------------------------------------------ the RFP's suggested headers
cand = RO.candidates(M2)
check("a short capitalized title line is suggested as a header; a shall sentence is not", "L-01" in cand and "L-02" not in cand, cand)
check("headers() reads without any marked", isinstance(RO.headers(M2), list))

# ------------------------------------------------------------------ activity log and offerings
diag.activity("kept_engine_check", n=1)
check("the activity log's recent lines include the latest", any("kept_engine_check" in str(x) for x in diag.recent_activity(5)))
check("an offering is found by name, ignoring case and spacing",
      offerings.find([{"Offering": "ThermaLoop Radiator"}], "  thermaloop   radiator ") is not None
      and offerings.find([{"Offering": "ThermaLoop Radiator"}], "Other") is None)

shutil.rmtree(tmp, ignore_errors=True)
t = sum(checks)
print(f"KEPT ENGINE {'PASS' if t == len(checks) else 'FAIL'} ({t}/{len(checks)})")
sys.exit(0 if t == len(checks) else 1)
