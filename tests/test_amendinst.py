"""Amendments written as instructions, and task and delivery orders, without windows: the instructions an SF 30 style
amendment gives (delete and insert words, change to, replace a paragraph, delete a paragraph, add a paragraph after
another, and words changed everywhere) are found in its text, the most specific paragraph named is the one changed;
applying them gives the conformed sentences and says what was applied and what was not found (and why); the conformed
version goes into the library as the base document's next version, with a readable text file; and orders are typed,
numbered and filed under the contract or RFP."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
import app_gui as A
import amendinst as AI, docversions as DV, docintake as DI, whatchanged as WC
import pdfmini

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


AMD = ["AMENDMENT OF SOLICITATION 0001. The solicitation is amended as follows:",
       "1. Section L, paragraph L.4.2, delete \"twenty (20) pages\" and insert \"twenty-five (25) pages\".",
       "2. In paragraph C.3.1, change \"monthly\" to \"quarterly\".",
       "3. Paragraph L.5.3 is deleted in its entirety and replaced with the following: \"The Offeror shall provide a risk register. The register shall be updated monthly.\"",
       "4. Paragraph M.2.4 is hereby deleted in its entirety.",
       "5. Add the following new paragraph L.5.6 after paragraph L.5.5: \"The Offeror shall describe its software assurance approach.\"",
       "6. Delete \"CDRL A007\" and insert \"CDRL A008\".",
       "7. In paragraph L.9.9, delete \"foo\" and insert \"bar\".",
       "All other terms and conditions remain unchanged."]
ins = AI.parse(" ".join(AMD))
check("seven instructions found, in order", [i["op"] for i in ins] == ["words", "words", "section", "delete", "add", "words", "words"], [i["op"] for i in ins])
check("... the most specific paragraph named (L.4.2, not Section L)", ins[0]["sec"] == "L.4.2" and ins[0]["old"] == "twenty (20) pages"
      and ins[0]["new"] == "twenty-five (25) pages", ins[0])
check("... an added paragraph knows where it goes", ins[4]["sec"] == "L.5.6" and ins[4]["after"] == "L.5.5")
check("... words changed everywhere when no paragraph is named", ins[5]["sec"] == "" and ins[5]["old"] == "CDRL A007")
check("an ordinary sentence is no instruction", AI.parse("The Offeror shall describe its approach. All other terms remain unchanged.") == [])
BASE = ["L.4.2 Volume II. Volume II shall not exceed twenty (20) pages.",
        "L.5.3 Risk. The Offeror shall describe its risk process.",
        "L.5.5 Test. The Offeror shall describe its test approach.",
        "C.3.1 Reports. The contractor shall deliver status reports monthly per CDRL A007.",
        "M.2.4 Past Performance. Past performance will be rated.",
        "M.2.5 Price. Price will be evaluated."]
tmp = tempfile.mkdtemp()
p1 = os.path.join(tmp, "RFP.pdf"); pdfmini.write(p1, [BASE], size=9)
pa = os.path.join(tmp, "Amendment_0001.pdf"); pdfmini.write(pa, [AMD], size=9)
lib = DV.Library(os.path.join(tmp, "data", "documents")).load()
pl = DI.plan(lib, [p1]); pl[0]["initial"] = "R"; DI.apply(lib, pl, "")
pl = DI.plan(lib, [pa]); pl[0]["choice"] = "new"; pl[0]["initial"] = "A1"; pl[0]["type"] = "Amendment"; DI.apply(lib, pl, "")
base = next(d for d in lib.docs if d["initial"] == "R")
amend = next(d for d in lib.docs if d["initial"] == "A1")
secs = {s["s"] for s in lib.text(base["versions"][-1])}
check("the base document's paragraphs are known by their numbers", {"L.4.2", "L.5.3", "C.3.1", "M.2.4"} <= secs, secs)
out, res = AI.apply(lib.text(base["versions"][-1]), AI.instructions_of(lib, amend["versions"][-1]), "Amendment 0001")
text = " ".join(s["x"] for s in out)
check("words changed in their paragraph", "twenty-five (25) pages" in text and "twenty (20) pages" not in text)
check("a paragraph replaced", "risk register" in text and "risk process" not in text)
check("a paragraph deleted", "Past performance will be rated" not in text and "Price will be evaluated" in text)
check("a paragraph added after the one named", [s["s"] for s in out].index("L.5.6") == max(i for i, s in enumerate(out) if s["s"] == "L.5.5") + 1)
check("words changed everywhere", "quarterly per CDRL A008" in text)
check("what was not found says why", res[6]["status"] == "not found" and "L.9.9 is not in the document" in res[6]["why"], res[6])
check("the summary", AI.summary(res) == "6 of 7 instruction(s) applied; 1 not found", AI.summary(res))
d, v, res2 = AI.conform(lib, amend, base)
check("the conformed version is the base document's next version", v and v["label"] == "Conformed (A1)" and d["id"] == base["id"]
      and len(base["versions"]) == 2 and v["conformed_from"] == amend["versions"][-1]["id"])
check("... with a readable text file saying what was applied", open(v["path"], encoding="utf-8").read().count("[applied]") == 6
      and "[not found]" in open(v["path"], encoding="utf-8").read())
s = WC.summary(lib, lib.doc(base["id"]), v)
check("... and What changed reads it like any new version", s and s["changed"] >= 3 and s["removed"] >= 1 and s["added"] >= 1, s and s["text"])
check("nothing applied: no version", AI.conform(lib, amend, base, pick=[6])[1] is None and len(lib.doc(base["id"])["versions"]) == 2)
# task and delivery orders
check("orders are typed from their names", DV.guess_type("Task_Order_0003.pdf") == "Task order" and DV.guess_type("Delivery Order 12.pdf") == "Delivery order"
      and DV.guess_type("IDIQ_Base_Contract.pdf") == "Contract")
pc = os.path.join(tmp, "IDIQ_Base_Contract.pdf"); pdfmini.write(pc, [["Section B Supplies or Services. The contractor shall provide engineering services."]], size=9)
pt = os.path.join(tmp, "Task_Order_0003.pdf"); pdfmini.write(pt, [["Task Order 0003. The contractor shall perform orbit analysis."]], size=9)
pl = DI.plan(lib, [pc]); pl[0]["choice"] = "new"; pl[0]["initial"] = "CT"; DI.apply(lib, pl, "")
pl = DI.plan(lib, [pt])
check("an order is suggested under the contract, numbered TO1", pl[0]["type"] == "Task order" and pl[0]["initial"] == "TO1"
      and lib.doc(pl[0]["under"])["type"] == "Contract", (pl[0]["type"], pl[0]["initial"], pl[0].get("under")))
pl[0]["choice"] = "new"; made = DI.apply(lib, pl, "")
to = made[0][0]
check("... and filed under it", to["under"] == lib.base_for_orders()["id"] and lib.children(to["under"]) == [to])
check("a document cannot be filed under itself or one of its own", not lib.set_under(to["under"], to["id"]) and not lib.set_under(to["id"], to["id"]))
check("taking it out", lib.set_under(to["id"], "") and "under" not in lib.doc(to["id"]))
n = sum(checks)
print(f"TEST AMENDINST {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
