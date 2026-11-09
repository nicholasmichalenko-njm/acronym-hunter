"""3.92.1: a heading on the same line as its text, split in Verify (verifysplit, verifystate, pagesent). The suggestion
for "L.4.2.1 Title. The Offeror shall ...", the split kept with Verify's decisions, and the reader giving the outline
the heading and Review the text. Fictional Kestrel content."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
import verifysplit as SPL
import verifystate as VS
import verifyblocks as VB
import pagesent as PS
from pdfmake import make_pdf

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


check("the suggestion: number, title, period, then a sentence",
      SPL.runin("L.4.2.1 Telemetry, Tracking and Command. The Offeror shall describe its TT&C approach.") == "L.4.2.1 Telemetry, Tracking and Command.")
check("... a colon works too", SPL.runin("3.2 Staffing: The Offeror shall name its key personnel.") == "3.2 Staffing:")
check("a sentence that only starts with a number is not a heading", SPL.runin("2 sites shall be staffed. The Offeror shall ...") == "")
check("a title that says shall is not a heading", SPL.runin("1.1 The Offeror shall describe. Then more text follows here.") == "")
check("a heading alone on its line is not run in", SPL.runin("1.2 Commercial Passes.") == "")
_ln = "L.4.2.1  Telemetry,  Tracking and Command. The Offeror"
check("where the heading ends, with any spacing", SPL.at(_ln, "L.4.2.1 Telemetry, Tracking and Command.") == _ln.index(" The"))

tmp = tempfile.mkdtemp()
pdf = make_pdf(os.path.join(tmp, "Kestrel Section L.pdf"), [[
    "L.4 Technical Volume",
    "L.4.2.1 Telemetry, Tracking and Command. The Offeror shall describe its TT&C approach for both sites.",
    "The Offeror shall state how commanding continues when one site is down.",
]])
store = VS.Store(os.path.join(tmp, "work"))
name = os.path.basename(pdf)
v = VS.view(pdf, store, name, 1)
blk = next((b for b in v if b.get("split_suggest")), None)
check("Verify flags the block: heading on the same line as its text", blk is not None
      and any(f.startswith("Heading on the same line") for f in blk["flags"]), [(b["text"], b["flags"]) for b in v])
store.set_split(name, blk["key"], blk["split_suggest"])
v2 = VS.view(pdf, store, name, 1)
b2 = next(b for b in v2 if b["key"] == blk["key"])
check("the split is kept and the flag is gone", b2["split"] == "L.4.2.1 Telemetry, Tracking and Command."
      and not any(f.startswith("Heading on the same line") for f in b2["flags"]))
check("the split stamps the document changed (Review offers read it again)", bool(store.doc(name).get("changed")))
sp = VS.splits(pdf, store, name)
check("the reader gets the split by page and line", list(sp.values()) == ["L.4.2.1 Telemetry, Tracking and Command."], sp)
PS.OVERRIDES[:] = []
PS.SPLITS[:] = [lambda path, nm: VS.splits(path, store, nm)]
chunks, places = PS.chunks_for(pdf, name)
text = "\n".join(c for _n, c in chunks)
lines = [l for l in text.split("\n") if l.strip()]
check("the heading is its own line for the outline", "L.4.2.1 Telemetry, Tracking and Command." in lines, lines)
check("the text it ran into starts its own paragraph", any(l.startswith("The Offeror shall describe its TT&C approach") for l in lines), lines)
words = [w for w, *_ in places]
check("every word keeps its place on the page", "telemetry" in words and "offeror" in words and len(places) >= 25, len(places))
doc = PS.doc_of(pdf)
pi, li = list(sp)[0]
ln = doc["pages"][pi]["lines"][li]
d2, remap, heads, bodies = SPL.split_doc(doc, sp)
b_ln = d2["pages"][pi]["lines"][list(bodies)[0][1]]
check("the text's characters still point at the page", ln["text"][b_ln["a"] - ln["a"]:].startswith("The Offeror shall describe"))
store.set_split(name, blk["key"], None)
check("Undo the split takes it back", VS.splits(pdf, store, name) == {})
store.set_split(name, blk["key"], "")
v3 = VS.view(pdf, store, name, 1)
check("It has no heading puts the suggestion away", not any(f.startswith("Heading on the same line") for b in v3 for f in b["flags"])
      and VS.splits(pdf, store, name) == {})
PS.SPLITS[:] = []
print(f"RUNIN 392 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
