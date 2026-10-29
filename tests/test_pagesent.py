"""2.57.0 sentences cut from the page: headers and footers are page furniture (never in the review, never boxed, never
part of a selection, never 'missing'); body text close to the page edge stays; a paragraph that runs over a page break
is one sentence without the footer and header between; every sentence knows its place on the page; sentences combined
from lines that are not next to each other keep each part's place; Word headers and footers are left out too."""
import os, sys, copy, zipfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_TEST"] = "1"
import compliance as C, pagesent as PS, textcheck as T, docview as DV

B = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_samples")
fails = []


def check(name, ok, info=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {info}"))
    if not ok:
        fails.append(name)


def furn(path):
    d = PS.read(path)
    return [(pi + 1, d["pages"][pi]["lines"][li]["text"].strip()) for pi, li in sorted(PS.running(d))]


L = os.path.join(B, "rfp_walk", "Section_L_print.pdf")
f = furn(L)
check("a running header on every page is furniture, on every page", len(f) == 6 and {p for p, _t in f} == {1, 2, 3}, f)
f = furn(os.path.join(B, "rfp_hard", "Hard_RFP.pdf"))
check("a one-page header and a 'CUI // Page' footer are furniture", [t for _p, t in f] == ["Solicitation FA8811-26-R-0042 Section L", "CUI // Page"], f)
N = os.path.join(B, "rfp_margins", "Narrow_Margins.pdf")
f = furn(N)
check("page numbers, a header standing apart and a long legend on each page are furniture",
      sorted(t[:20] for _p, t in f) == sorted(["Use or disclosure of", "Page 1", "Company Confidential", "Use or disclosure of", "Page 2"]), f)
items, heads, info = PS.read_review(N, "N.pdf", C.extract)
txt = [it["text"] for it in items]
check("body text close to the top and bottom edges stays in the review",
      any(t.startswith("The Offeror shall describe the approach on a page with narrow margins") for t in txt)
      and "The final body sentence sits low on the page." in txt, txt[:2] + txt[-3:])
check("a sentence running over the page break is one sentence, without the legend, page number and header between",
      "The last line of the page sits in the bottom margin and continues onto the second page past the footer and header." in txt,
      [t for t in txt if "bottom margin" in t])
check("no header or footer text is in the review", not any(k in " ".join(txt) for k in ("Company Confidential", "Page 2", "Use or disclosure")))
check("every sentence is placed on the page", not info["missed"] and all(it.get("place") for it in items), info)

S = os.path.join(B, "rfp_walk", "SOW.pdf")
items, heads, info = PS.read_review(S, "SOW.pdf", C.extract)
txt = [it["text"] for it in items]
check("SOW: the running title is not in the review; the deliverables table is", not any("Statement of Work Spacecraft Bus" in t for t in txt)
      and any(t.startswith("A001") for t in txt) and any(t.startswith("A003") for t in txt), txt)
check("SOW: sections from the headings", [h["num"] for h in heads] == ["2.1", "2.2", "2.3"], heads)

# places: kept while the words are there; found again otherwise; combined sentences keep each part
items, heads, info = PS.read_review(L, "S.pdf", C.extract)
for i, it in enumerate(items):
    it["id"] = f"X{i}"
pl = PS.place_all(L, items)
check("place_all keeps every sentence's own place", all(pl[it["id"]][0] == it["place"] for it in items))
a, b = items[2]["text"], items[7]["text"]
two = copy.deepcopy(items)
m = C.merge_items(items, ["X2", "X7"])
check("combining sentences that are not next to each other keeps both places", m["place"].count(";") == 1 and m["text"] == a + " " + b, m["place"])
pl = PS.place_all(L, items)
check("the combined sentence is placed in two pieces", pl["X2"][0] == m["place"])
m2 = C.merge_items(two, ["X2", "X7"]); m2["place"] = ""
pl2 = PS.place_all(L, two)
check("a combined sentence with no place is found in pieces", pl2.get("X2", ("",))[0] == m["place"], pl2.get("X2"))
mp = PS.place_map(L, 1, [dict(it, place=pl[it["id"]][0], lead_place=pl[it["id"]][1]) for it in items], heads)
x2 = next(x for x in mp["items"] if x["id"] == "X2")
check("the page map boxes both parts and nothing is missing", len(x2["rects"]) >= 2 and not mp["missing"], (len(x2["rects"]), mp["missing"]))
check("the page map has the headers as furniture, not boxes", len(mp["furniture"]) == 2
      and not any(r[1] < 60 for x in mp["items"] for r in x["rects"]), mp["furniture"])
st = os.path.join(B, "rfp_stress", "Stress_RFP.pdf")
items, heads, info = PS.read_review(st, "St.pdf", C.extract)
leads = [it for it in items if it["text"].endswith(":") and it.get("place")]
check("two lists with the same lead-in: each lead-in is a sentence placed on its own words (2.70.0)", len(leads) >= 2
      and not any(it.get("lead_place") for it in items), [it["text"][:20] for it in leads])
for i, it in enumerate(items):
    it["id"] = f"X{i}"
check("Stress: nothing missing on the pages", not any(PS.place_map(st, p, items, heads)["missing"] for p in (1, 2)))

# the text check and the page view text leave headers and footers out (PDF and Word)
ct = T.content_text(L)
check("PDF text for the check has no headers", not any("FA8811-26-R-0099" in l for _w, l in ct) and len(ct) > 20)
D = os.path.join(B, "rfp_walk", "Section_L.docx")
with zipfile.ZipFile(D) as z:
    has_header = any(n.startswith("word/header") for n in z.namelist())
raw = T.raw_text(D)
ct = T.content_text(D)
check("Word text for the check has no header or footer parts", not any(w.startswith(("header", "footer")) for w, _l in ct)
      and (not has_header or len(ct) < len(raw)), (has_header, len(raw), len(ct)))
check("the page view text is the same", not any("FA8811-26-R-0099" in l for _w, l in DV.doc_lines(L)))
check("the compliance reader leaves out Word header and footer passages",
      [it["text"] for it in C.extract([("a.docx", [("a.docx (Header 1)", "The offeror shall do X."), ("a.docx (Footer 2)", "Page 1 of 3"),
                                                   ("a.docx (Body)", "The offeror shall do Y.")])])] == ["The offeror shall do Y."])
check("merge_places sorts by page and character", PS.merge_places([{"place": "2:5-9"}, {"place": "1:30-40;2:0-3"}]) == "1:30-40;2:0-3;2:5-9")
print(f"PAGESENT PASS ({len(fails) == 0})" if not fails else f"PAGESENT FAIL {fails}")
sys.exit(1 if fails else 0)
