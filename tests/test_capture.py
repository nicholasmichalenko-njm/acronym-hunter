"""2.70.0 nothing the reader misses stays missed: a list's lead-in ("The description shall address the following:") is
a sentence of its own, placed on the page, and the text check no longer counts it as read through its items; an older
matrix gets its lead-ins as sentences (decisions kept); Add missed text reads an area of a page (the PDF's own text,
else OCR on the picture) and adds it as a sentence in its place."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
import app_gui as A
import compliance as C, compliance_read as CR, capture as CAP, pagesent as PS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


PDF = os.path.join(A.BASE_DIR, "test_samples", "rfp_walk", "Section_L_print.pdf")
LEAD = "The description shall address the following:"
items, heads, src, empty = CR.read_files([PDF], A.rfp_chunks)
M = CR.new_matrix(os.path.join(tempfile.mkdtemp(), "m.xlsx"), items, heads, src, "")
lead = next((it for it in M.items if it["text"] == LEAD), None)
check("the lead-in before a list of bullets is a sentence of its own", lead is not None)
bullets = [it for it in M.items if it.get("lead") == LEAD]
check("its bullets still carry it", len(bullets) == 4 and M.items.index(lead) < M.items.index(bullets[0]), len(bullets))
pl = PS.place_all(PDF, [it for it in M.items if it["file"] == "Section_L_print.pdf"])
check("it has its own place on the page (a box to click)", bool(pl.get(lead["id"], ("",))[0]), pl.get(lead["id"]))
res = CR.text_check(M)
check("the text check: every word read", res and res[0]["missing"] == 0, res and res[0]["missing"])

# an older matrix: the lead-in only inside its items
old = C.Matrix(os.path.join(tempfile.mkdtemp(), "old.xlsx"), "old")
old.items = [dict(it) for it in M.items if it["text"] != LEAD]
old.items[old.items.index(next(x for x in old.items if x.get("lead") == LEAD)) - 1]["decision"] = "Keep"
res_old = CR.text_check(type("Mx", (), {"sources": M.sources, "items": old.items, "headings": M.headings})())
check("the text check finds the lead-in an older read left inside its items", res_old[0]["missing"] >= 1, res_old[0]["missing"])
kept = [(x["id"], x["decision"]) for x in old.items if x["decision"]]
got = CAP.add_lead_ins(old)
check("opening it makes the lead-in a sentence, just before the list", len(got) == 1 and got[0]["text"] == LEAD
      and old.items[old.items.index(got[0]) + 1].get("lead") == LEAD, [g["text"] for g in got])
check("decisions are kept", [(x["id"], x["decision"]) for x in old.items if x["decision"]] == kept)
check("and only once", CAP.add_lead_ins(old) == [])

# Add missed text: an area of the page
import pypdfium2 as pdfium
doc = pdfium.PdfDocument(PDF)
page = doc[0]
w, h = page.get_size()
tp = page.get_textpage()
sr = tp.search("The description shall address")
i0, _cnt = sr.get_next()
sr.close()
boxes = [tp.get_charbox(i) for i in range(i0, i0 + len(LEAD)) if i < tp.count_chars()]
tp.close(); doc.close()
l = min(b[0] for b in boxes) - 1; r = max(b[2] for b in boxes) + 1
t = h - max(b[3] for b in boxes) - 1; b_ = h - min(b[1] for b in boxes) + 1
text, how = CAP.text_in(PDF, 0, (l, t, r, b_))
check("an area is read from the PDF's own text", how == "pdf" and text == LEAD, (how, text))
fake = lambda img: [(0, 0, 40, 10, "Offerors", 90.0), (45, 0, 90, 10, "shall comply.", 90.0)]
text2, how2 = CAP.text_in(PDF, 0, (5, 5, 60, 20), ocr=fake)
check("an area with no text layer goes to OCR", how2 == "ocr" and text2 == "Offerors shall comply.", (how2, text2))
check("nothing readable: nothing", CAP.text_in(PDF, 0, (5, 5, 60, 20), ocr=lambda img: []) == ("", ""))
first = next(x for x in M.items if x["file"] == "Section_L_print.pdf")
new = CAP.add_sentence(M, "Section_L_print.pdf", "The Offeror shall describe its quality plan.", after_id=lead["id"], page=1, how="pdf")
check("added in its place, under the same RFP section, with an ID", M.items[M.items.index(lead) + 1] is new
      and new["section"] == lead["section"] and new["id"] and new["type"] != "Context", (new["id"], new["type"]))
top = CAP.add_sentence(M, "Section_L_print.pdf", "Draft", at_start=True, how="typed")
check("nothing above it: before the file's first sentence", M.items.index(top) == M.items.index(first) - 1)
n = sum(checks)
print(f"CAPTURE PASS ({n}/{len(checks)})" if n == len(checks) else f"CAPTURE FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
