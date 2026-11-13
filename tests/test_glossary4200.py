"""4.20.0: one word for one thing (claude/stationkeeper-glossary-4.20.md). No text the program shows uses a word the
glossary retired (tools/glossary.py; a string kept on purpose is in tools/glossary_allow.json with its reason, and every
entry there still matches a string). The shred's counts read the same on every surface (shredwords). Quick tools' tiles
carry the pages' names of today. Fictional (Kestrel)."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT); sys.path.insert(0, os.path.join(ROOT, "tools"))
os.environ["AH_TEST"] = "1"
os.environ.pop("GLOSSARY_ALLOW_EXTRA", None)
import glossary as G
import shredwords as SW

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


got = G.hits()
check("no retired word in the program's text", not got, [f"{r}:{l} [{k}] {s[:60]!r}" for r, l, k, _say, s in got][:12])
keep = json.load(open(G.ALLOW, encoding="utf-8"))
stale, no_why = [], []
for rel, rules in keep.items():
    have = [s for _l, s in G.strings(rel)] if os.path.isfile(os.path.join(ROOT, rel)) else []
    for rule, ents in rules.items():
        for e in ents:
            if not any(s.startswith(e["s"]) for s in have):
                stale.append((rel, rule, e["s"][:40]))
            if not (e.get("why") or "").strip():
                no_why.append((rel, e["s"][:40]))
check("every kept string is still there (the list does not outlive its strings)", not stale, stale[:8])
check("every kept string says why", not no_why, no_why[:8])
check("the rules know their own words", {k for k, *_r in G.RULES} >= {"review", "library", "sentence", "sorted", "global", "acronyms-page",
                                                                         "compare-page", "production-menu"})
# a retired word is found, a kept use is not
bad = lambda rule, s: any(k == rule and b.search(o.sub("", s)) for k, _say, b, o in G.RULES)          # noqa: E731
check("finds: Open in Review, add them in Library, 3 sentences, not sorted, Global value, Acronym Finder, Decide in Compare",
      all([bad("review", "Open in Review"), bad("library", "add them in Library"), bad("sentence", "3 sentences"),
           bad("sorted", "not sorted"), bad("global", "Global value"), bad("acronyms-page", "Acronym Finder"),
           bad("compare-page", "Decide in Compare"), bad("production-menu", "Production > Templates")]))
check("keeps: Color Reviews, Review by hand, the Effort Library, sorted by category, Compare two drafts",
      not any([bad("review", "Color Reviews"), bad("review", "Review by hand"), bad("library", "the Effort Library"),
               bad("sorted", "sorted by category"), bad("compare-page", "Compare two drafts")]))
# the shred's counts, one set of words
check("12 of 40 pieces shredded; 1 piece", SW.progress(12, 40) == "12 of 40 pieces shredded" and SW.pieces(1) == "1 piece")
check("28 not shredded; all shredded", SW.left(28) == "28 not shredded" and SW.left(0) == "all shredded")
check("a document: 40 pieces, 28 not shredded", SW.of_document(40, 28) == "40 pieces, 28 not shredded" and SW.of_document(3, 0) == "3 pieces, all shredded")
src = {f: open(os.path.join(ROOT, f), encoding="utf-8").read() for f in ("navsteps.py", "skqt/navrail.py", "skqt/docstatus.py", "skqt/shredlist.py")}
check("the menu, the stepper, Documents' panel and the List read them there", all("SW." in s for s in src.values()),
      [f for f, s in src.items() if "SW." not in s])
from skqt import toolshome as TH
names = {k: v[0] for k, v in TH.TOOLS.items()}
check("Quick tools' tiles: Shred, Documents, Changes, Acros & Abs, Quick shred, Dashboard", names["assign"] == "Shred" and names["library"] == "Documents"
      and names["compare"] == "Changes" and names["acronyms"] == "Acros & Abs" and names["acrfinder"] == "Acros & Abs Finder"
      and names["shredreq"] == "Quick shred" and names["home"] == "Dashboard", names)
check("... no two tiles share a name", len(set(names.values())) == len(names))
k = sum(checks)
print(f"GLOSSARY 4200 {'PASS' if k == len(checks) and checks else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if checks and k == len(checks) else 1)
