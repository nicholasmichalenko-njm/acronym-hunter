"""3.59.0 shred accuracy, standard library only. Answer keys saved from a review's decisions beside each RFP; the set's
files labeled or not; recall, precision and kind scored against the key (a requirement the shred never flags is a miss;
a flag the person dropped is a false alarm); the history logs numbers only; an acknowledgment row per amendment, once;
what a read set aside (headers, footers, lines repeated on every page) and putting a header back. Fictional content."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("AH_TEST", "1")
import app_gui as A
import compliance as C
import shredeval as SE
import shredquick as SQ

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
SET = os.path.join(tmp, "Shred Set"); os.makedirs(SET)
rfp = shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "rfp", "Kestrel_RFP_Sections_C_L_M.docx"), SET)
other = shutil.copy2(os.path.join(A.BASE_DIR, "test_samples", "rfp", "Kestrel_RFP_Section_L_Part2.pdf"), SET)
name = os.path.basename(rfp)

# a review of the RFP, decided by a person: the shred's flags kept, one dropped, one sentence it missed kept
items = C.extract([(name, A.typed_chunks(rfp))])
M = C.Matrix(os.path.join(tmp, "m.xlsx"), "Test")
M.items, M.sources = items, [[name, "", "", rfp]]
flags = {C.text_key(r["text"]) for r in SQ.shred(rfp)["rows"]}
flagged = [it for it in items if it["key"] in flags]
plain = [it for it in items if it["key"] not in flags and len(it["text"].split()) > 8 and it.get("type") != "Heading"]
for it in items:
    it["decision"] = "Keep" if it["key"] in flags else "Context"
flagged[0]["decision"] = "Drop"                       # a flag the person says is not a requirement
plain[0]["decision"] = "Keep"; plain[0]["type"] = "Instruction"; plain[0]["section"] = "L.9"   # a requirement the shred missed
next(it for it in items if it["key"] not in flags and it is not plain[0])["decision"] = ""   # one left undecided (not a flag)
got = SE.save_keys(M)
check("an answer key saved beside the RFP", len(got) == 1 and got[0][1] == rfp + SE.KEY_SUFFIX and os.path.isfile(got[0][1]))
check("... with every sentence, the undecided counted", got[0][2] == len([i for i in items if i.get("type") != "Heading"])
      and got[0][3] == got[0][2] - 1, got[0])
files = dict(SE.set_files(SET))
check("the set: each RFP file, labeled or not", files.get(rfp) == rfp + SE.KEY_SUFFIX and other in files and files[other] is None)
s = SE.score_file(rfp, rfp + SE.KEY_SUFFIX)
truth = len(flagged) - 1 + 1
check("the truth is what the person kept", s["truth"] == truth, (s["truth"], truth))
check("recall: the requirement the shred missed is a miss", s["found"] == truth - 1, s)
check("precision: the dropped flag is a false alarm", s["false"] == 1 and s["right"] == truth - 1, s)
check("the kind scored apart", s["kind_total"] == truth - 1 and 0 < s["kind_right"] <= s["kind_total"], s)
r = SE.score_set(SET)
check("the set's scores", r["rfps"] == 2 and r["labeled"] == 1 and r["requirements"] == truth
      and r["recall"] == round(100 * (truth - 1) / truth, 1) and r["precision"] == round(100 * (truth - 1) / truth, 1), r)
check("... by kind", "Instruction (L)" in r["by_kind"] and r["by_kind"]["Instruction (L)"] is not None)
hp = os.path.join(tmp, "hist.csv")
SE.append_history(hp, r, "3.59.0"); SE.append_history(hp, r, "3.59.1")
h = SE.history(hp)
check("the history: numbers only, one row a scoring", len(h) == 2 and h[1]["Version"] == "3.59.1" and h[0]["Recall"] == str(r["recall"])
      and name not in open(hp).read())

# amendments
docs = [({"id": "d1", "type": "RFP", "name": "Kestrel RFP"}, {"label": "Original"}), {"id": "d2", "type": "Amendment", "name": "Amendment 0001"},
        ({"id": "d1", "type": "RFP", "name": "Kestrel RFP"}, {"label": "Amendment 2"})]
n0 = len(M.items)
add = SE.acknowledgment_rows(M, docs)
check("an acknowledgment row per amendment: a document typed Amendment, a version labeled Amendment N", len(add) == 2
      and add[0]["decision"] == "Keep" and "Acknowledge Amendment 0001" in add[0]["text"] and "Amendment 2 to Kestrel RFP" in add[1]["text"]
      and add[0]["id"] and len(M.items) == n0 + 2, [a["text"] for a in add])
check("... once", SE.acknowledgment_rows(M, docs) == [])

# what a read set aside
chunks = [("p.1 (Header)", "Kestrel Source Selection Sensitive"), ("p.1", "The Offeror shall describe its orbit operations."),
          ("p.2 (Header)", "Kestrel Source Selection Sensitive"), ("p.2", "The Offeror shall provide a staffing plan.")]
C.extract([("Kestrel_RFP.docx", chunks)])
aside = list(C.SET_ASIDE.values())
check("a read lists the header it set aside, with how often", len(aside) == 1 and aside[0]["times"] == 2
      and aside[0]["why"] == "A page header or footer", aside)
from skqt.asideview import put_back
M2 = C.Matrix(os.path.join(tmp, "m2.xlsx"), "Test2"); M2.items = C.extract([("Kestrel_RFP.docx", chunks)])
n = len(M2.items)
back = put_back(M2, aside)
check("a header put back in the review as a sentence of its own", len(back) == 1 and len(M2.items) == n + 1
      and "Source Selection" in M2.items[-1]["text"])
n = sum(checks)
print(f"SHRED ACCURACY {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
