"""4.25.2: Used for and folders (Documents board 2026-11-12, step B; answers 4 and 6). A document's marks in words; the
saved role words are unchanged, so an older effort reads the same; context reads Reference; a document may carry Return
it, redlined and Filled-in Deliverable as well; a folder brought in keeps its nested folders and takes any kind of file.
Fictional content."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import docversions as DV, docintake as DI

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


def put(path, text="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


tmp = tempfile.mkdtemp()
lib = DV.Library(os.path.join(tmp, "documents"))
a = put(os.path.join(tmp, "in", "Kestrel_SOW.txt"), "The Contractor shall deliver the plan.")
b = put(os.path.join(tmp, "in", "Kestrel_QA.txt"), "Question 1. Answer 1.")
d1, _ = lib.add(a, DI.read(a)["sents"] if isinstance(DI.read(a), dict) else DI.read(a), dtype="SOW", initial="SOW")
d2, _ = lib.add(b, [], category="qa")
check("the saved words are the ones every effort already holds", (d1["role"], d2["role"]) == ("matrix", "context")
      and [k for k, _n in DV.ROLES] == ["matrix", "context", "reference", "not_needed"])
check("in words: For the shred; context reads Reference", lib.marks_of(d1) == ["For the shred"] and lib.marks_of(d2) == ["Reference"]
      and DV.use_key("context") == "reference" and DV.use_key("matrix") == "matrix")
check("a document may carry several marks", lib.set_returns(d1["id"], ["redline", "fill", "nonsense"])
      and lib.marks_of(lib.doc(d1["id"])) == ["For the shred", "Redlined Deliverable", "Filled-in Deliverable"]
      and DV.Library(os.path.join(tmp, "documents")).load().returns_of(DV.Library(os.path.join(tmp, "documents")).load().doc(d1["id"])) == ["redline", "fill"])
check("no mark: left out", lib.set_role(d2["id"], "not_needed") and lib.marks_of(lib.doc(d2["id"])) == [])
check("taking the return marks off leaves no key behind", lib.set_returns(d1["id"], []) and "returns" not in lib.doc(d1["id"]))
check("an effort made before (no returns key) reads the same", lib.returns_of({"role": "matrix"}) == [] and lib.marks_of({"role": "reference"}) == ["Reference"])
check("Source in words: Customer or Internal, with what kind when the folder said so", [DV.source_name(lib, k) for k in ("customer", "bidders", "qa", "ours", "graphics")]
      == ["Customer", "Customer (bidders library)", "Customer (Q&A)", "Internal", "Internal (graphics)"])
top = os.path.join(tmp, "Past work")
for rel in ("Kestrel summary.docx", "2025/Proposal/Volume I.pdf", "2025/Proposal/Art/logo.ai", "2025/Schedule.mpp", "2025/~$lock.docx", "2025/desktop.ini"):
    put(os.path.join(top, *rel.split("/")))
got = dict((os.path.relpath(p, top).replace(os.sep, "/"), f) for p, f in DI.walk(top))
check("a folder brought in keeps its nested folders, with its own name first", got.get("2025/Proposal/Volume I.pdf") == "Past work/2025/Proposal"
      and got.get("Kestrel summary.docx") == "Past work" and got.get("2025/Proposal/Art/logo.ai") == "Past work/2025/Proposal/Art", got)
check("... any kind of file, but not what programs leave behind", "2025/Schedule.mpp" in got and "2025/~$lock.docx" not in got and "2025/desktop.ini" not in got, sorted(got))
n = sum(checks)
print(f"TEST USED FOR 4252 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
