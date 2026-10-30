"""2.99.0 what the customer values, without windows: evaluation factors and subfactors read from the customer's words with
their relative importance, kept in order with subfactors under their factor; hot buttons; effort details (NAICS, contract
type, period of performance, set-aside, place of performance, clauses, clearances, key personnel) read and filed into
Effort details, one per name."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
import app_gui as A
import custfocus as F, effortrec as R, branding as BR

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


g = F.factor_guess("Factor 1: Technical Approach. Technical is significantly more important than Past Performance.")
check("a factor, its number and importance", g == {"name": "Technical Approach", "sub": False, "number": "1", "importance": "Significantly more important"}, g)
g = F.factor_guess("Subfactor 1.2 Systems Engineering will be evaluated for soundness.")
check("a subfactor", g["sub"] and g["name"] == "Systems Engineering" and g["number"] == "1.2", g)
g = F.factor_guess("Factor 3, Past Performance, will be evaluated on an acceptable/unacceptable basis.")
check("a pass/fail factor", g["name"] == "Past Performance" and g["importance"] == "Pass/fail", g)
check("equal importance", F.factor_guess("Technical and Management are approximately equal.")["importance"] == "Approximately equal")
check("no factor: nothing", F.factor_guess("The contractor shall deliver a monthly report.") is None)
cases = {"The NAICS code for this acquisition is 336414 with a size standard of 1,250 employees.": ("NAICS", "336414"),
         "The Government anticipates award of a firm-fixed-price contract.": ("Contract type", "firm-fixed-price"),
         "The period of performance is 60 months from contract award.": ("Period of performance", "60 months from contract award"),
         "This acquisition is a total small business set-aside.": ("Set-aside", "total small business set-aside"),
         "The place of performance is Peterson SFB, Colorado.": ("Place of performance", "Peterson SFB, Colorado"),
         "Offerors shall comply with CMMC Level 2 requirements.": ("Clause that matters", "CMMC Level 2 requirements"),
         "The contractor shall possess a Top Secret facility clearance.": ("Security clearance", "Top Secret facility clearance"),
         "Key personnel include the Program Manager and Chief Engineer.": ("Key personnel", "the Program Manager and Chief Engineer")}
got = {t: F.detail_guess(t) for t in cases}
check("effort details read from the customer's words", got == cases, {t[:30]: v for t, v in got.items() if v != cases[t]})
check("a hot button: what the sentence stresses", F.hot_guess("The Government places strong emphasis on schedule realism and launch readiness.")
      == "schedule realism and launch readiness")
tmp = tempfile.mkdtemp()
rec = R.Record(os.path.join(tmp, "d"))
src = {"doc": "Section_M.pdf", "loc": "p.4, para 2", "sid": "SectionM-04"}
t1 = F.add_factor(rec, "Technical Approach", importance="Significantly more important", text="Factor 1...", source=src)
t2 = F.add_factor(rec, "Past Performance", importance="Pass/fail", source=src)
s1 = F.add_factor(rec, "Systems Engineering", parent=t1, source=src)
check("factors in order, each subfactor under its factor", [f["name"] for f in F.factors(rec)] == ["Technical Approach", "Systems Engineering", "Past Performance"]
      and F.factors(rec)[0]["doc"] == "Section_M.pdf")
F.remove_factor(rec, t1)
check("removing a factor removes its subfactors", [f["name"] for f in F.factors(R.Record(os.path.join(tmp, "d")))] == ["Past Performance"])
h = F.add_hot(rec, "Schedule realism", quote="The Government places strong emphasis on schedule realism.", source=src)
check("a hot button with the customer's words", F.hot_buttons(rec)[0]["quote"].startswith("The Government") and F.remove_hot(rec, h)
      and F.hot_buttons(rec) == [])
F.set_detail(rec, "NAICS", "336414", source=src)
F.set_detail(rec, "NAICS", "336415", source=src)
F.set_detail(rec, "Contract type", "FFP")
fields = BR.identity(R.Record(os.path.join(tmp, "d")))["fields"]
check("effort details: one per name, with where it came from", [f["label"] for f in fields] == ["NAICS", "Contract type"]
      and fields[0]["value"] == "336415 (Section_M.pdf p.4, para 2)", fields)
n = sum(checks)
print(f"TEST CUSTFOCUS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
