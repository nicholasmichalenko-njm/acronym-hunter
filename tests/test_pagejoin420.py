"""4.2.0 the page break (pagejoin): a piece placed over two pages is marked "Joined across p.N to N+1" and loses a page
number caught in its middle; Keep takes it off the suspects; the page break is found again to undo the join; the
suspects (a join not kept, a page that ends mid-sentence, a fragment, a word broken across a line, unreadable
characters). Fictional sentences."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import pagejoin as PJ

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


j = {"id": "L-1", "text": "The Offeror shall describe its approach to the ground Page 3 of 12 station operations.",
     "place": "3:100-160;4:0-19", "new": ""}
one = {"id": "L-2", "text": "The Offeror shall name an owner for each risk.", "place": "4:30-75", "new": ""}
tail = {"id": "L-3", "text": "The contractor shall deliver the reports listed in", "place": "4:80-130", "new": ""}
frag = {"id": "L-4", "text": "Table 2", "place": "5:0-7", "new": ""}
hy = {"id": "L-5", "text": "The plan covers configuration manage- ment of the ground segment.", "place": "5:10-70", "new": ""}
bad = {"id": "L-6", "text": "The ﬁnal report is due in thirty days.", "place": "5:72-110", "new": ""}
items = [j, one, tail, frag, hy, bad]
check("pages a piece runs over", PJ.pages_of(j) == [3, 4] and PJ.pages_of(one) == [4])
PJ.mark(items)
check("a piece over two pages is marked joined; the page number in its middle is taken out",
      j["new"] == "Joined across p.3 to 4" and j["text"] == "The Offeror shall describe its approach to the ground station operations."
      and one["new"] == "", j)
at = PJ.unjoin_at(j)
check("the page break is found again to undo the join", j["text"][:at].rstrip().endswith("the ground") and j["text"][at:] == "station operations.",
      (j["text"][:at], j["text"][at:]))
kinds = [(k, it["id"]) for k, it, _w in PJ.suspects(items)]
check("suspects: the join, the page that ends mid-sentence, the fragment, the broken word, the unreadable character",
      ("join", "L-1") in kinds and ("end", "L-3") in kinds and ("short", "L-4") in kinds and ("hyphen", "L-5") in kinds
      and ("bad", "L-6") in kinds and not any(i == "L-2" for _k, i in kinds), kinds)
check("Keep: kept, off the suspects", PJ.keep(j) and j["new"].endswith("(kept)") and not PJ.keep(j)
      and ("join", "L-1") not in [(k, it["id"]) for k, it, _w in PJ.suspects(items)])
check("a piece set aside or a heading is never a suspect", not PJ.suspects([dict(frag, decision="Drop"), dict(frag, header="Yes")]))
print(f"PAGE JOIN 420 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
