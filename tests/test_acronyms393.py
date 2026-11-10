"""3.93.0: the rules behind Acronyms On the page (acrpages): the pages with finds and what is left to decide on each,
Page done kept with the effort, where a term sits in a passage and in a picture's readings (whole words; a hyphen is a
boundary, so DC is found inside DC-RVM; the longer term wins the same spot), what a dragged box holds (finds, and
words never found), which bar a selection gets, the type, and Not a term with its way back. Fictional (Kestrel)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import acrpages as AG

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


R = {
    "TT&C": {"category": "Acronym (Candidate)", "locations": ["Section_L.pdf (p.41)", "Section_L.pdf (p.42)"]},
    "MOC": {"category": "Acronym", "effort": "In the list", "locations": ["Section_L.pdf (p.41)"]},
    "SHALL": {"category": "Abbreviation (Candidate)", "effort": "Not a term", "locations": ["Section_L.pdf (p.41)"]},
    "DC": {"category": "Acronym (Candidate)", "locations": ["Section_L.pdf (p.41)", "SOW.pdf (p.12)"]},
    "DC-RVM": {"category": "Acronym (Candidate)", "locations": ["SOW.pdf (p.12)", "Section_L.pdf (p.41)"]},
    "GSaaS": {"category": "Acronym (Candidate)", "locations": ["Section_L.pdf (p.9)"]},
    "CDRLs": {"category": "Acronym", "plural_of": "CDRL", "locations": ["Section_L.pdf (p.9)"]},
    "[Not scanned] OCR engine": {"category": "Not Scanned", "locations": ["OCR engine"]},
}

pgs = AG.pages(R)
keys = [p["key"] for p in pgs]
check("pages by file, then page number (p.9 before p.41)", keys == ["Section_L.pdf (p.9)", "Section_L.pdf (p.41)",
                                                                  "Section_L.pdf (p.42)", "SOW.pdf (p.12)"], keys)
p41 = pgs[1]
check("each page knows its finds and how many are left to decide", p41["to_decide"] == 3 and p41["terms"]["MOC"] == "list"
      and p41["terms"]["SHALL"] == "not", p41)
check("a page's label is the place in the file", p41["label"] == "p.41" and p41["name"] == "Section_L.pdf", p41)
check("a not-scanned note is not a page", not any("OCR engine" in k for k in keys))
check("a plural is tied, not to decide", pgs[0]["terms"]["CDRLs"] == "tied" and pgs[0]["to_decide"] == 1, pgs[0])
check("an OCR fix noted after a place is the same page", AG.place_of("Deck.pptx (Slide 4) [OCR fix: x]") == "Deck.pptx (Slide 4)")

tot = AG.totals(pgs)
check("the totals: to decide, pages left, pages done", tot == {"to_decide": 7, "pages_left": 4, "pages_done": 0}, tot)
check("the next page with finds", AG.next_page(pgs, "Section_L.pdf (p.9)") == "Section_L.pdf (p.41)")


class WS:
    def __init__(self):
        self.d = {}

    def get(self, k, default=None):
        return self.d.get(k, default)

    def set(self, k, v):
        self.d[k] = v


ws = WS()
AG.set_done(ws, "Section_L.pdf (p.41)")
pgs = AG.pages(R, AG.done_set(ws))
check("Page done is kept with the effort", AG.done_set(ws) == {"Section_L.pdf (p.41)"} and pgs[1]["done"])
check("a page done is skipped by Next page", AG.next_page(pgs, "Section_L.pdf (p.9)") == "Section_L.pdf (p.42)")
check("a done page no longer counts as left", AG.totals(pgs)["pages_left"] == 3 and AG.totals(pgs)["pages_done"] == 1)
AG.set_done(ws, "Section_L.pdf (p.41)", False)
check("... and can be undone", not AG.done_set(ws))

# where a term sits
text = "Each site in the DC-RVM before the design review; the TT&C link and the MOC. DCX is another word."
f = AG.text_finds(text, ["DC", "RVM", "TT&C", "MOC"])
words = [text[a:b] for a, b, _t in f]
check("DC and RVM are found inside DC-RVM (a hyphen is a boundary), never inside DCX", words == ["DC", "RVM", "TT&C", "MOC"], words)
f2 = AG.text_finds(text, ["DC", "DC-RVM", "TT&C"])
check("the longer term takes the spot when both are terms", [t for _a, _b, t in f2] == ["DC-RVM", "TT&C"], f2)
check("TT&C is one word (the & is part of it)", AG.spans("TT&CX and TT&C", "TT&C") == [(10, 14)])

lines = [((100, 50, 400, 70), "TT&C ANTENNA", 0.62), ((100, 200, 300, 220), "GEP / SITE B", 0.9),
         ((500, 50, 760, 70), "MISSION OPERATIONS CENTER (MOC)", 0.95)]
lf = AG.line_finds(lines, ["TT&C", "MOC"])
check("a term's box is its part of the line", len(lf) == 2 and lf[0]["box"][0] == 100 and lf[0]["box"][2] < 400
      and lf[0]["conf"] == 0.62, lf)
two = [{"term": "DC", "box": (10, 10, 30, 20)}, {"term": "DC-RVM", "box": (10, 10, 70, 20)}]
r1 = AG.resolve(two, R)
check("DC still to decide inside DC-RVM: DC stays, DC-RVM behind it (partly found)",
      r1[0]["term"] == "DC" and r1[0]["whole"]["term"] == "DC-RVM" and r1[1].get("behind"), r1)
R2 = dict(R, DC=dict(R["DC"], part_of="DC-RVM"))
r2 = AG.resolve(two, R2)
check("... once DC is decided, DC-RVM takes the spot", [x["term"] for x in r2] == ["DC-RVM"] and not r2[0].get("behind"), r2)
sp = AG.resolve(AG.all_spans(text, ["DC", "DC-RVM", "MOC"]), R)
check("the same in typed text", [(x["term"], bool(x.get("whole")), bool(x.get("behind"))) for x in sp]
      == [("DC-RVM", False, True), ("DC", True, False), ("MOC", False, False)], sp)
got, rest = AG.area_pick(lf, lines, (90, 190, 320, 230))
check("a box around words never found: no finds, what the reader sees", got == [] and rest == "GEP / SITE B", (got, rest))
got, rest = AG.area_pick(lf, lines, (0, 0, 800, 100))
check("a box around finds selects them", sorted(x["term"] for x in got) == ["MOC", "TT&C"] and rest == "", (got, rest))
check("the word that looks like a term", AG.guess_term("GEP / SITE B") == "GEP" and AG.guess_term("the 3D-2 board") == "3D-2")

# which bar
check("one term inside a longer one: partly found", AG.bar_kind([{"term": "DC", "conf": None}], R, 0.5) == "partial")
check("one find read with doubt", AG.bar_kind([{"term": "TT&C", "conf": 0.3}], R, 0.5) == "doubt")
check("found, to decide", AG.bar_kind([{"term": "TT&C", "conf": 0.9}, {"term": "MOC", "conf": None}], R, 0.5) == "decide")
check("words never found", AG.bar_kind([{"term": None}], R, 0.5) == "new")


class Effort:
    def __init__(self):
        self.rows = {"MOC": {}}


class S:
    def __init__(self):
        self.results = {k: dict(v) for k, v in R.items()}
        self.effort = Effort()
        self.calls = []

    def save(self):
        self.calls.append("save")

    def list_remove(self, terms):
        self.calls.append(("remove", tuple(terms)))
        for t in terms:
            self.results[t]["effort"] = None

    def list_status(self, terms, st):
        self.calls.append(("status", tuple(terms), st))
        for t in terms:
            self.results[t]["effort"] = st

    def exclude(self, terms, on=True):
        self.calls.append(("exclude", tuple(terms), on))


s = S()
check("the type said on the page; a candidate stays a candidate", AG.set_type(s, ["TT&C"], "Abbreviation") == 1
      and s.results["TT&C"]["category"] == "Abbreviation (Candidate)" and AG.type_of(s.results["TT&C"]) == "Abbreviation")
check("the type of a unit", AG.type_of({"category": "Unit (Candidate)"}) == "Unit")
was = AG.before(s, ["TT&C", "MOC"])
s.results["TT&C"]["effort"] = "Not a term"; s.results["MOC"]["effort"] = "Not a term"
AG.undo_not_term(s, was)
check("Undo: a term not in the list leaves it again", ("remove", ("TT&C",)) in s.calls)
check("Undo: a term in the list goes back to its status", ("status", ("MOC",), "In the list") in s.calls
      and s.results["MOC"]["effort"] == "In the list")

print(f"{sum(checks)}/{len(checks)} passed")
sys.exit(0 if all(checks) else 1)
