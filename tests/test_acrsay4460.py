"""4.46.0, UX decision 64: a find's saved status is said in the page's words on screen and in exports; what is saved
stays. Plain sentence case, customer (never client), acronym database (never DB), ignored (never excluded)."""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_TEST"] = "1"
import acrsay as S
import app_gui as A

checks = []
def check(name, ok, got=None):
    checks.append(bool(ok)); print(("ok    " if ok else "FAIL  ") + name + ("" if ok else f"   {got!r}"))

pairs = {"NEW CANDIDATE": "New, no definition on record", "CHOOSE DEFINITION": "Choose a definition",
         "CUSTOMER DOCS DIFFER (2)": "Customer documents differ (2)", "Resolved (In DB)": "In the acronym database",
         "Client list (database differs)": "On the customer's list (differs from the acronym database)",
         "User Selected": "Chosen by a person", "ADDED MANUALLY": "Added by hand",
         "EXCLUDED: heading word in capitals": "Ignored: heading word in capitals",
         "Not a term in this effort": "Ignored in this effort",
         "CHOOSE (client list: 3 meanings)": "Choose: the customer's list has 3 meanings",
         "CHOOSE (defined 2 ways)": "Choose: defined 2 ways in the document",
         "EQUATION: 1 symbol(s) not defined": "Equation: 1 symbol not defined",
         "EQUATION: 2 symbol(s) not defined": "Equation: 2 symbols not defined",
         "Alt form of FY": "Another form of FY",
         "Alt form of FY (effort list: In the list)": "Another form of FY (added to effort list)",
         "Effort list: In the list": "Added to effort list",
         "Effort list: In the list, no definition yet": "Added to effort list, no definition yet",
         "Effort list: To decide": "Undecided"}
bad = {k: S.shown(k) for k, v in pairs.items() if S.shown(k) != v}
check("each agreed word (Nicholas 2026-11-16 13:40)", not bad, bad)
check("a status the table does not know is shown as it is, never hidden",
      S.shown("Some later status") == "Some later status" and S.shown("") == "" and S.shown(None) == "")
check("unchanged on purpose: No longer found, Could not read file, Not scanned",
      all(S.shown(x) == x for x in ("No longer found", "No longer found: No longer found in A.docx", "Could not read file", "Not scanned")))
every = list(S._EXACT.values()) + list(pairs.values())
check("no capitals for emphasis, no client, no DB, no excluded",
      not [x for x in every if re.search(r"\b[A-Z]{3,}\b", x.replace("FY", "")) or re.search(r"client|\bDB\b|xclu", x, re.I)],
      [x for x in every if re.search(r"\b[A-Z]{3,}\b", x.replace("FY", "")) or re.search(r"client|\bDB\b|xclu", x, re.I)])
check("the decision a person made: Undecided, Added to effort list, Ignored",
      [S.decision(x) for x in ("To decide", "In the list", "Not a term", "Other")] == ["Undecided", "Added to effort list", "Ignored", "Other"])
check("the Definition column: none on record",
      S.definition("[Not in Database — Definition omitted]") == "No definition on record")
check("... several meanings, listed", S.definition("MULTIPLE (2 meanings) - Choose: Statement of Work OR Scope of Work")
      == "2 meanings: Statement of Work; Scope of Work"
      and S.definition("MULTIPLE (3 client meanings) - Choose: A OR B OR C") == "3 meanings: A; B; C")
check("... every meaning kept (Keep all), listed the same way", S.definition("MULTIPLE: Statement of Work | Scope of Work") == "Statement of Work; Scope of Work")
check("... an ignored term's definition without the mark; a real definition untouched",
      S.definition("[EXCLUDED] Statement of Work") == "Statement of Work" and S.definition("Statement of Work") == "Statement of Work")
# what is saved is not changed: the app still sorts finds by the saved words
check("the saved words still sort the finds (app_gui.status_kind reads what is saved)",
      A.status_kind("NEW CANDIDATE") == "candidate" and A.status_kind("CHOOSE DEFINITION") == "choice"
      and A.status_kind("Resolved (In DB)") == "resolved")
# the exported acronym list (acrrules.export_effort_lists): Status in the page's words; the effort's rows keep theirs
import tempfile, types, openpyxl
import acrrules as R, effort as E
tmp = tempfile.mkdtemp()
L = E.EffortList(os.path.join(tmp, "Kestrel_Effort_List.xlsx"), "Kestrel")
L.add_or_update("KZQ", Definition="Kestrel Zulu Quebec", Status="In the list")
L.add_or_update("KAT", Definition="", Status="In the list")
fake = types.SimpleNamespace(effort=L, efforts={"Kestrel": {}}, results={})
fake._list_rows = types.MethodType(R.AcronymRules._list_rows, fake)
made = R.AcronymRules.export_effort_lists(fake, folder=tmp, scope="whole")
xp = [m for m in made or [] if m.endswith(".xlsx")]
ws = openpyxl.load_workbook(xp[0])["Acronym list"] if xp else None
heads = [c.value for c in ws[1]] if ws else []
col = heads.index("Status") if "Status" in heads else None
cells = [r[col] for r in ws.iter_rows(min_row=2, values_only=True)] if ws and col is not None else []
check("the exported list's Status cells read Added to effort list", cells and all(c == "Added to effort list" for c in cells), cells)
check("... while the effort's own rows still hold In the list", all(L.rows[t]["Status"] == "In the list" for t in ("KZQ", "KAT")),
      {t: L.rows[t]["Status"] for t in L.rows})
check("... and the headings Term and Definition stay (a Word macro reads them)", heads[:2] == ["Term", "Definition"], heads)
wbx = openpyxl.load_workbook(xp[0]) if xp else None
ab = {r[0]: r[1] for r in wbx["About this list"].iter_rows(values_only=True) if r[0]} if wbx and "About this list" in wbx.sheetnames else {}
check("the export names its scan on a second sheet: effort, when made, the last scan, the files (decision 64)",
      wbx and wbx.sheetnames[0] == "Acronym list" and ab.get("Effort") == L.name and re.match(r"\d{4}-\d\d-\d\d \d\d:\d\d$", str(ab.get("List made")))
      and "Last scan" in ab and "Files scanned" in ab, (wbx.sheetnames if wbx else None, ab))
docx = [m for m in made or [] if m.endswith(".docx")]
import zipfile
xml = zipfile.ZipFile(docx[0]).read("word/document.xml").decode("utf-8") if docx else ""
check("... the Word list keeps its Term and Definition headings", ">Term<" in xml and ">Definition<" in xml)
import acrimport as AI
book = AI.read(xp[0]) if xp else {}
back = AI.to_rows(book) if book else []
check("Import a list reads the export back as In the list (the reader knows the page's words)",
      back and all(E._norm_status(r.get("Status")) == "In the list" for r in back) and E._norm_status("Ignored") == "Not a term", back)
k = sum(checks)
print(f"ACRSAY 4460 {'PASS' if k == len(checks) and checks else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if checks and k == len(checks) else 1)
