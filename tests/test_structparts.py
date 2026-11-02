"""3.19.0 parts of the response structure: cover, title page, front matter, response, appendices and back cover in each
volume, in order; unnumbered items for cover, title and front matter, lettered appendices; an item moved to another part
takes its place and numbering, and its sentences follow; the text of the structure keeps the parts; the matrix workbook
keeps them; each part's rules come from the Production Standards page scheme; only the response counts toward the page
limit unless set."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import compliance as C, outline_ops as O, setupdoc as SD, structparts as SP, prodrules as PRL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


class M_:
    def __init__(self):
        self.outline, self.items, self.setup, self.pending = [], [], {}, False

    def log(self, *a):
        pass


M = M_()
v1 = O.add_volume(M, "Technical")
v2 = O.add_volume(M, "Cost")
s1 = O.add(M, "Technical Approach", parent=v1)
s2 = O.add(M, "Management Approach", parent=v1)
it = {"id": "L.1-01", "text": "The Offeror shall describe its approach.", "decision": "Keep", "map": s2}
M.items.append(it)
cov = O.add_part_item(M, "cover", "Cover", v1)
toc = O.add_part_item(M, "front", "Table of contents", v1)
ttl = O.add_part_item(M, "title", "Title page", v1)
app = O.add_part_item(M, "appendix", "Resumes", v1)
app2 = O.add_part_item(M, "appendix", "Past performance", v1)
sub = O.add(M, "Key personnel", parent=app)
back = O.add_part_item(M, "back", "Back cover", v1)
order = O.in_volume(M, v1)
check("a volume's parts in order: cover, title page, front matter, response, appendices, back cover",
      order == [v1, "Cover", "Title page", "Table of contents", "1 Technical Approach", "2 Management Approach",
                "Appendix A Resumes", "A.1 Key personnel", "Appendix B Past performance", "Back cover"], order)
check("cover, title page and front matter carry no number; appendices are lettered", cov == "Cover" and toc == "Table of contents"
      and app == "Appendix A Resumes" and sub == "A.1 Key personnel" and app2 == "Appendix B Past performance")
toc2 = O.add_part_item(M, "front", "Table of contents", v2)
check("the same front matter item in another volume gets its own name", toc2 == "Table of contents (Vol II)", toc2)
es = O.add(M, "Executive summary", parent=v1)
new = O.set_part(M, es, "front")
order = O.in_volume(M, v1)
check("an item moved to front matter goes before the response and loses its number", new == "Executive summary"
      and order.index("Executive summary") < order.index("1 Technical Approach") and order.index("Executive summary") > order.index("Title page"), order)
back_to = O.set_part(M, "Table of contents", "body")
check("an item moved into the response is numbered there", back_to and back_to[0].isdigit(), back_to)
O.set_part(M, back_to, "front")
mv = O.set_part(M, "2 Management Approach", "appendix")
check("a response section moved to the appendices is lettered, and its sentences follow it", mv == "Appendix A Management Approach"
      and it["map"] == mv and O.labels(M).count("Appendix B Resumes") == 1, (mv, it["map"]))
check("a section under a part's item is in that part", SP.part_of(M.outline[O.index_of(M, "A.1 Key personnel".replace("A.1", "B.1"))]) == "appendix")
txt = C.outline_text(M.outline)
back = C.parse_outline(txt)
check("the structure's text keeps the parts", "[Cover] Cover" in txt and "[Front matter]" in txt and "[Appendix]" in txt
      and [SP.part_of(o) for o in back] == [SP.part_of(o) for o in M.outline], txt)
check("'Executive summary' typed alone is a title, not section E", C.parse_outline("Executive summary")[0] == {"num": "", "title": "Executive summary", "level": 1})
# the matrix workbook keeps the parts
tmp = tempfile.mkdtemp()
X = C.Matrix(os.path.join(tmp, "m.xlsx")) if hasattr(C, "Matrix") else None
if X is not None:
    X.items = []; X.outline = [dict(o) for o in M.outline]
    X.save()
    Y = C.Matrix(os.path.join(tmp, "m.xlsx")); Y.load() if hasattr(Y, "load") and not Y.outline else None
    check("the matrix workbook keeps each section's part", [SP.part_of(o) for o in Y.outline] == [SP.part_of(o) for o in M.outline])
# page limits
check("only the response counts toward the page limit by default", SP.counts(M, "body") and not SP.counts(M, "front")
      and not SP.counts(M, "appendix") and not SP.counts(M, "cover"))
SP.set_counts(M, "appendix", True)
check("a part can be set to count", SP.counts(M, "appendix"))
# the rules from Production Standards
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
std = PRL.for_effort(cfg)
r = SP.rules(std, "front")
check("front matter follows the page scheme: roman numbers, the volume name in the header", r["found"] and "i, ii" in r["numbers"]
      and "volume name" in r["header"] and "TOC Heading" in r["starts"], r)
check("the cover has no page numbers; the response numbers by chapter; appendices by chapter too",
      SP.rules(std, "cover")["numbers"] == "no page numbers" and "by chapter" in SP.rules(std, "body")["numbers"]
      and "Heading 7" in SP.rules(std, "appendix")["starts"] and "A-1" in SP.rules(std, "appendix")["numbers"], (SP.rules(std, "body"), SP.rules(std, "appendix")))
check("a title page follows the cover's rules when the scheme has no title part", SP.rules(std, "title")["numbers"] == "no page numbers"
      and "Cover" in SP.rules(std, "title")["scheme"], SP.rules(std, "title"))
std2 = dict(std, pagination=PRL.presets()["straight"])
check("a scheme without front matter says so", not SP.rules(std2, "front")["found"] and "not in the page scheme" in SP.summary(std2, "front"))
n = sum(checks)
print(f"STRUCT PARTS {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
