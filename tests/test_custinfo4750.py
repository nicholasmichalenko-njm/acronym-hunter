"""4.75.0: Customer information under the screen (custinfo): a fact typed or captured, where it came from, never replaced
silently, the older Effort details spots read through, and contacts with a role. Fictional (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import branding as BR, custinfo as CI, effortrec as ER

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


d = tempfile.mkdtemp()
rec = ER.Record(d)
check("the facts: three groups, each fact once, the two he asked for by name among them", [g for g, _r in CI.GROUPS] ==
      ["Who the customer is", "What is being bought", "When and where"] and len(set(CI.LABELS)) == len(CI.LABELS)
      and "Agency or sub-agency" in CI.LABELS and "Buying office address" in CI.LABELS)
check("nothing filled: every row is empty and says where the fact usually is, where it has a usual place", CI.filled(rec) == 0
      and next(r for r in CI.rows(rec) if r["label"] == "Solicitation number")["hint"].startswith("SF 33 block 3"))
check("captured: the value, and where it came from", CI.set_fact(rec, "Contract type", "Firm Fixed Price", "captured", "Avery", {"doc": "Kestrel RFP", "page": 3}) == "set"
      and CI.fact(rec, "Contract type")["value"] == "Firm Fixed Price" and CI.where(CI.fact(rec, "Contract type")) == "Kestrel RFP, page 3")
out = CI.set_fact(rec, "Contract type", "Cost Plus", "captured", "Avery", {"doc": "Kestrel RFP", "page": 9})
check("a filled fact is never replaced silently: a capture that differs asks and changes nothing", isinstance(out, dict) and out["ask"]["value"] == "Firm Fixed Price"
      and CI.fact(rec, "Contract type")["value"] == "Firm Fixed Price")
check("... Keep leaves it; Replace takes the new one with its new source", CI.set_fact(rec, "Contract type", "Cost Plus", "captured", "Avery", {"doc": "Kestrel RFP", "page": 9}, replace=False) == "same"
      and CI.set_fact(rec, "Contract type", "Cost Plus", "captured", "Avery", {"doc": "Kestrel RFP", "page": 9}, replace=True) == "set"
      and CI.where(CI.fact(rec, "Contract type")) == "Kestrel RFP, page 9")
check("the same value again changes nothing (capitals and spaces left out)", CI.set_fact(rec, "Contract type", " cost  plus ", "captured") == "same")
check("typed: by whom and when", CI.set_fact(rec, "Department", "Department of Orbital Affairs", "typed", "Avery", replace=True) == "set"
      and CI.where(CI.fact(rec, "Department")).startswith("typed by Avery, 20"), CI.where(CI.fact(rec, "Department")))
check("cleared by typing nothing", CI.set_fact(rec, "Department", "", "typed", "Avery", replace=True) == "cleared" and CI.fact(rec, "Department")["value"] == "")
BR.set_identity(rec, fields=[{"label": "NAICS", "value": "541715"}])
check("an older Effort details spot of the same label reads through as typed", CI.fact(rec, "NAICS")["value"] == "541715" and CI.where(CI.fact(rec, "NAICS")) == "typed")
check("the page's rows carry value, from and hint", [(r["value"], r["from"]) for r in CI.rows(rec) if r["label"] in ("NAICS", "Contract type")] ==
      [("541715", "typed"), ("Cost Plus", "Kestrel RFP, page 9")] and CI.filled(rec) == 2)
cid = CI.add_contact(rec, "Jordan Reyes", "Contracting Officer", org="NOIA", email="jordan.reyes@noia.example", who="Avery")
check("a contact typed on the page, with a role", cid and CI.contacts(rec)[0]["role"] == "Contracting Officer" and CI.contacts(rec)[0]["email"] == "jordan.reyes@noia.example"
      and CI.contacts(rec)[0]["from"].startswith("typed"), CI.contacts(rec))
check("... a contact needs a name; the role can be changed", CI.add_contact(rec, "") is None and CI.set_role(rec, cid, "Questions go to") and not CI.set_role(rec, cid, "Questions go to"))
rec2 = ER.Record(d)
check("opened again: the facts, their sources and the contact's role are there", CI.fact(rec2, "Contract type") == CI.fact(rec, "Contract type")
      and CI.contacts(rec2)[0]["role"] == "Questions go to")
check("the value a piece's words give: the words themselves, cut to a line", CI.guess("Submit to", "  Proposals shall be   submitted to the portal. ") == "Proposals shall be submitted to the portal.")
print(f"CUSTINFO 4750 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
