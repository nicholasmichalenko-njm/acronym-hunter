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
check("... an ignored term's definition without the mark; a real definition untouched",
      S.definition("[EXCLUDED] Statement of Work") == "Statement of Work" and S.definition("Statement of Work") == "Statement of Work")
# what is saved is not changed: the app still sorts finds by the saved words
check("the saved words still sort the finds (app_gui.status_kind reads what is saved)",
      A.status_kind("NEW CANDIDATE") == "candidate" and A.status_kind("CHOOSE DEFINITION") == "choice"
      and A.status_kind("Resolved (In DB)") == "resolved")
k = sum(checks)
print(f"ACRSAY 4460 {'PASS' if k == len(checks) and checks else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if checks and k == len(checks) else 1)
