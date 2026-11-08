"""3.84.0 Verify's rules: the menu of roles (defaults, hidden and renamed roles, your own role with an "acts as", unique
keys, the team default); the page cut into blocks with a suggested role and why (headers and footers, headings by
their numbering, captions, list items, running text) and the ledger that counts every word into a block; what Verify
keeps (roles, caption links, verified pages and who, a page reopened by a spot check, corrected readings, the page
each document was left on); flags first and warn, never block; Select all text in this section; the reader following
Verify's decisions; a scanned page's unsure lines. Fictional content (the Kestrel set)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
import pagesent as PS, verifyblocks as VB, verifyroles as VR, verifystate as VS, ocrpdf as OP
from pdfmake import make_pdf

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


ROOT = os.path.dirname(HERE)
SL = os.path.join(ROOT, "test_samples", "rfp_walk", "Section_L_print.pdf")
SOW = os.path.join(ROOT, "test_samples", "rfp_walk", "SOW.pdf")
tmp = tempfile.mkdtemp()

# ---- the menu
m = VR.defaults()
check("thirteen roles to start: H1 to H6, Text, Bullet, Figure, Figure caption, Table, Table caption, Footnote, Running, "
      "Not needed", [r["name"] for r in m] == ["H1", "H2", "H3", "H4", "H5", "H6", "Text", "Bullet", "Figure", "Figure caption",
                                                "Table", "Table caption", "Footnote", "Running", "Not needed"], [r["name"] for r in m])
check("the default keys", VR.key_map(m) == {"1": "h1", "2": "h2", "3": "h3", "4": "h4", "5": "h5", "6": "h6", "T": "text", "B": "bullet",
                                            "F": "figure", "Shift+F": "figcap", "M": "table", "Shift+M": "tabcap", "N": "footnote",
                                            "R": "running", "X": "skip"})
m2, rid = VR.add_role(m, "Evaluation note", "text", key="E")
check("a role of your own, with what it acts as", rid == "u_evaluation_note" and VR.acts(m2, rid) == "text" and VR.key_map(m2)["E"] == rid)
check("the same name again is the same role", VR.add_role(m2, "evaluation note", "skip")[1] == rid)
m3, hid = VR.add_role(m2, "Sub-factor", "heading", key="", level_=3)
check("your own heading role sits at the level you pick", VR.level(m3, hid) == 3)
saved = [dict(r) for r in m3]
saved[0]["on"] = False; saved[6]["name"] = "Body text"; saved[7]["key"] = "T"
c = VR.clean(saved)
check("a hidden role stays in the menu, hidden", not VR.by_id(c)["h1"]["on"] and "1" not in VR.key_map(c))
check("a renamed role keeps what it does", VR.name(c, "text") == "Body text" and VR.acts(c, "text") == "text")
check("two roles never share a key", list(VR.key_map(c).values()).count("text") == 1 and VR.by_id(c)["bullet"]["key"] == "")
check("a built-in role taken out comes back", "skip" in VR.by_id(VR.clean([r for r in c if r["id"] != "skip"])))
check("the nearest shown heading stands in for a hidden one", VR.heading_role(c, 1) == "h2")
cfg = os.path.join(tmp, "cfg")
VR.save_team(cfg, m3)
check("Save as team default: new efforts start with it", VR.by_id(VS.Store(os.path.join(tmp, "e0")).menu(cfg)).get(rid))

# ---- blocks
d = VB.blocks(SL)
p1 = d["pages"][0]["blocks"]
by = {b["text"][:24]: b for b in p1}
check("the running header is its own block, Running", by["FA8811-26-R-0099 Section"]["suggest"] == "running")
check("SECTION L is H1, by its word", by["SECTION L - INSTRUCTIONS"]["suggest"] == "h1" and by["SECTION L - INSTRUCTIONS"]["sure"])
check("L.1 is H2, by its numbering", by["L.1 General Instructions"]["suggest"] == "h2" and "level 2" in by["L.1 General Instructions"]["why"])
check("running text is Text", by["The Government intends t"]["suggest"] == "text")
check("blocks in reading order", [b["box"][1] for b in p1] == sorted(b["box"][1] for b in p1))
lg = VB.ledger(SL, 1)
check("the ledger: every word of the page is in a block", lg["total"] > 100 and lg["placed"] == lg["total"] and not lg["missing"], lg)
sow = VB.blocks(SOW)["pages"][0]["blocks"]
unnum = next(b for b in sow if b["text"] == "STATEMENT OF WORK")
check("a heading with no number: a level from its size, and not sure", unnum["suggest"].startswith("h") and not unnum["sure"])

# ---- what Verify keeps, flags first
st = VS.Store(os.path.join(tmp, "e1"))
v = VS.view(SOW, st, "SOW.pdf", 1)
check("an unsure suggestion is a flag", any(b["key"] == unnum["key"] and b["flags"] for b in v))
check("Page verified waits on the page's flags", not VS.can_verify(v))
check("the strip: a page with flags is to look at", VS.status(SOW, st, "SOW.pdf")[0] == "look")
st.set_role("SOW.pdf", [unnum["key"]], "h1")
v = VS.view(SOW, st, "SOW.pdf", 1)
check("deciding the role clears the flag", VS.can_verify(v) and next(b for b in v if b["key"] == unnum["key"])["decided"])
st.verify("SOW.pdf", 1, who="A. Lee")
check("verified, with who", VS.status(SOW, st, "SOW.pdf")[0] == "verified"
      and VS.Store(os.path.join(tmp, "e1")).doc("SOW.pdf")["verified"]["1"]["by"] == "A. Lee")
st.reopen("SOW.pdf", 1, who="K. Park", why="Spot check: 2.3 should be H3")
check("a spot check reopens a verified page", VS.status(SOW, st, "SOW.pdf")[0] == "look"
      and st.doc("SOW.pdf")["reopened"]["1"]["by"] == "K. Park")
check("Next to look at finds it", VS.next_to_look(SOW, st, "SOW.pdf", 0) == 1)
st.verify("SOW.pdf", 1, who="K. Park")
check("verifying again closes it", VS.status(SOW, st, "SOW.pdf")[0] == "verified")
st.set_last("SOW.pdf", 2)
check("each document opens where it was left", VS.Store(os.path.join(tmp, "e1")).doc("SOW.pdf")["last"] == 2)
v = VS.view(SOW, st, "SOW.pdf", 1)
k21 = next(b["key"] for b in v if b["text"].startswith("The Contractor shall design"))
sec = VS.section_of(v, k21)
check("Select all text in this section: the text under 2.1, to the next heading",
      len(sec) == 2 and all(next(b for b in v if b["key"] == k)["role"] == "text" for k in sec), sec)
c0 = VS.counts(SOW, st, "SOW.pdf")
check("the page counts", c0["pages"] == 2 and c0["verified"] == 1, c0)

# ---- captions link to their object
cap_pdf = make_pdf(os.path.join(tmp, "caps.pdf"), [["3 Staffing", "Table 1 Staffing by month", "Month Lead Analysts",
                                                     "The plan ramps to full staff in month three."]])
st2 = VS.Store(os.path.join(tmp, "e2"))
v = VS.view(cap_pdf, st2, "caps.pdf", 1)
cap = next(b for b in v if b["text"].startswith("Table 1"))
check("a caption suggests Table caption", cap["role"] == "tabcap")
check("a caption with nothing to name is a flag", "Link this caption to its figure or table" in cap["flags"])
row = next(b for b in v if b["text"].startswith("Month"))
st2.set_role("caps.pdf", [row["key"]], "table")
cap = next(b for b in VS.view(cap_pdf, st2, "caps.pdf", 1) if b["key"] == cap["key"])
check("set a Table: the caption suggests it, dashed until confirmed", cap["link"] == {"to": row["key"], "ok": False}
      and "Confirm what this caption names" in cap["flags"])
st2.set_link("caps.pdf", cap["key"], row["key"])
cap = next(b for b in VS.view(cap_pdf, st2, "caps.pdf", 1) if b["key"] == cap["key"])
check("confirmed: solid, no flag", cap["link"]["ok"] and not cap["flags"])

# ---- the reader follows Verify
before = PS.chunks_for(SL, "Section_L_print.pdf")[0]
st3 = VS.Store(os.path.join(tmp, "e3"))
grant = next(b for b in VB.blocks(SL)["pages"][0]["blocks"] if b["text"].startswith("Offerors are cautioned"))
st3.set_role("Section_L_print.pdf", [grant["key"]], "skip")
PS.OVERRIDES[:] = [lambda path, nm: VS.overrides(path, st3, nm)]
after = PS.chunks_for(SL, "Section_L_print.pdf")[0]
check("Not needed: the block never reaches Review", "Offerors are cautioned" in before[0][1] and "Offerors are cautioned" not in after[0][1])
hdr = by["FA8811-26-R-0099 Section"]
st3.set_role("Section_L_print.pdf", [hdr["key"]], "text")
after = PS.chunks_for(SL, "Section_L_print.pdf")[0]
check("a header set to Text is read after all", "FA8811-26-R-0099" in after[0][1] and "FA8811-26-R-0099" not in before[0][1])
PS.OVERRIDES[:] = []
check("no decisions: the reader reads as before", PS.chunks_for(SL, "Section_L_print.pdf")[0] == before)

# ---- a scanned page: the reader's lines, unsure ones flagged
from PIL import Image
img = Image.new("RGB", (1700, 2200), "white")
lines = [(200, 300, 1000, 340, "Personne1 Qualifications", 0.62), (200, 400, 1500, 440, "Key personnel shall have resumes.", 0.97)]
scan = OP.write(os.path.join(tmp, "scan (words) abc.pdf"), [(img, lines, 200)])
OP.save_readings(scan, {"1": OP._readings(lines, 200)})
check("the readings are kept beside the copy, in PDF points", OP.readings_of(scan)["1"][0]["box"] == [72.0, 108.0, 360.0, 122.4])
st4 = VS.Store(os.path.join(tmp, "e4"))
v = VS.view(scan, st4, "scan.png", 1)
flagged = [f for b in v for f in b["flags"] if f.startswith("Check the reading")]
check("an unsure reading is a flag on its block", flagged == ["Check the reading: Personne1 Qualifications"], [b["flags"] for b in v])
st4.set_reading("scan.png", 1, 0, "Personnel Qualifications")
check("corrected, the flag goes", not any(f.startswith("Check the reading") for b in VS.view(scan, st4, "scan.png", 1) for f in b["flags"]))

print(f"VERIFY 384 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
