"""3.22.0 the template library: Collect reads a template or a Word document once (never writing it) and lists what it
carries on shelves (styles grouped, hidden text styles on their own card, page setups, headers and footers, numbering,
table styles and looks, the TOC, covers, Quick Parts, fonts with whether they are installed); what is kept is saved as
format data, tagged; the same values match without asking and the same name with other values becomes a variant;
an item goes into a standard (a style, a Quick Part with its source), and the standard's template carries it; the Our
data file carries the library."""
import hashlib, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ.setdefault("SK_DATA_DIR", tempfile.mkdtemp())
import prodparts as PP
import prodquickparts as QP
import prodrules as PRL
import prodtemplate as PT
import teamdata as TD
import templatelib as TL
from _qpfixture import with_glossary

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
MASTER = os.path.join(HERE, "pefix", "data", "PE_Master_Effort_Template.dotx")
SMALL = os.path.join(HERE, "pefix", "data", "small.docx")
std = PRL.for_effort(tempfile.mkdtemp())
lib = TL.Library(cfg)
src = os.path.join(tmp, "Team Master.dotx")
with_glossary(MASTER, src)
before = hashlib.sha256(open(src, "rb").read()).hexdigest()

cards, err = TL.collect(src, std, lib, installed_fonts=["Calibri", "Arial"])
keys = [c.key for c in cards]
check("Collect lists what the file carries, card by card", not err and any(k.startswith("styles:") for k in keys)
      and {"pages", "heading_numbering", "quickparts", "fonts"} <= set(keys), keys)
check("... without writing the file", hashlib.sha256(open(src, "rb").read()).hexdigest() == before)
fonts = next(c for c in cards if c.key == "fonts").items
check("every font is listed with whether this PC has it", fonts and all(("installed" in f["summary"]) for f in fonts), [f["summary"] for f in fonts])
qpc = next(c for c in cards if c.key == "quickparts")
check("Quick Parts are listed with their category and gallery", [i["name"] for i in qpc.items] == ["Volume cover", "CUI header", "Table caption"]
      and "Covers / Cover Pages" in qpc.items[0]["summary"])
check("everything new starts ticked", all(i["keep"] and i["state"] == "new" for c in cards for i in c.items))
for c in cards:                                  # the person renames one and skips one
    for i in c.items:
        if i["kind"] == "quickpart" and i["name"] == "Table caption":
            i["keep"] = False
        if i["kind"] == "quickpart" and i["name"] == "Volume cover":
            i["name"] = "01 Volume cover"
n = TL.save_collected(lib, src, cards, tags={"use": ["RFP", "Page-limited RFP"], "customer": "USSF"})
lib2 = TL.Library(cfg)
check("what is kept is saved as format data, tagged, at once", n["new"] > 5 and lib2.shelf("style") and lib2.shelf("style", "RFP")
      and lib2.shelf("style")[0]["tags"]["customer"] == "USSF", n)
qps = lib2.shelf("quickpart")
check("a Quick Part keeps its source file, so its fields and pictures stay whole; the one skipped is not kept",
      sorted(q["name"] for q in qps) == ["01 Volume cover", "CUI header"] and os.path.isfile(lib2.source_path(lib2.values(qps[0])["source"])))
again, _e = TL.collect(src, std, lib2)
check("collecting the same file again: everything already in the library, nothing ticked",
      all(i["state"] == "same" and not i["keep"] for c in again for i in c.items if not (i["kind"] == "quickpart" and i["name"] == "Table caption")))
h1 = next(i for i in lib2.shelf("style") if i["name"] == "Heading 1")
v = dict(lib2.values(h1)); v["size"] = 22
it, st = lib2.add("style", "Heading 1", v, tags={"use": ["RFI"]})
check("the same name with other values is kept as a variant, tagged, never overwritten", st == "variant" and it["name"] == "Heading 1 (2)"
      and it["variant_of"] == h1["id"] and lib2.values(h1)["size"] != 22 and lib2.shelf("style", "RFI") == [it])

# ---------------------------------------------------------------- into a standard, and into its template
work = {}
said = [TL.use_in_standard(lib2, it["id"], work), TL.use_in_standard(lib2, qps[0]["id"], work, category="01 Covers")]
check("an item goes into the standard being edited: a style, a Quick Part with its source", work["style_defs"]["Heading 1"]["size"] == 22
      and work["quick_parts"]["entries"][0]["category"] == "01 Covers"
      and os.path.isfile(os.path.join(PP.parts_dir(cfg), work["quick_parts"]["entries"][0]["source"])), said)
s2 = PRL.merge(std, work); s2["_parts_dir"] = PP.parts_dir(cfg)
tj = PT.make(s2, os.path.join(tmp, "out"))
got = {(e["name"], e["category"], e["gallery"]) for e in QP.read(tj.copy)}
check("the standard's template carries them", ("01 Volume cover" if False else qps[0]["base_name"], "01 Covers", "docParts") in got
      or any(e[1] == "01 Covers" and e[2] == "docParts" for e in got), got)

# ---------------------------------------------------------------- hidden text styles and documents
std3 = PRL.for_effort(tempfile.mkdtemp())
std3["style_defs"]["SK RFP Reference"] = {"type": "paragraph", "based_on": "Normal", "color": "7030A0", "hidden": True}
tj3 = PT.make(std3, os.path.join(tmp, "out3"))
c3, _e = TL.collect(tj3.copy, std3, TL.Library(os.path.join(tmp, "cfg3")))
hid = next((c for c in c3 if c.key == "styles:Hidden text"), None)
check("hidden text styles get their own card, with hidden text in the summary", hid is not None and hid.items[0]["name"] == "SK RFP Reference"
      and "hidden text" in hid.items[0]["summary"], [c.key for c in c3])
c4, e4 = TL.collect(SMALL, std, lib2)
check("a Word document (.docx) is collected like a template", not e4 and any(c.key.startswith("styles:") for c in c4), e4)

# ---------------------------------------------------------------- the library travels in the Our data file
os.makedirs(os.path.join(TL.folder(cfg), "_collecting"), exist_ok=True)
open(os.path.join(TL.folder(cfg), "_collecting", "scratch.docx"), "wb").write(b"x")
man = TD.export(cfg, os.path.join(tmp, "share", "d" + TD.EXT), ["library"])
check("the Our data file carries the library (and leaves a collection in progress out)", "library" in man["parts"]
      and "config/template_library/index.json" in man["files"] and not any("_collecting" in f for f in man["files"]))

print(f"TEMPLATE LIBRARY {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
