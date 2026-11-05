"""3.54.0 Technical Edit's rules and the edited copy, on a fictional draft: each starter group finds what it should and
leaves ordinary text alone; numbers one to nine spelled out; 30 words a sentence; passive voice as Check; spelling against
the word list and the team's dictionaries; the acronym list read, not changed; the effort's style sheet (terms, rules
off, skips); edit levels; the edited copy holds the accepted fixes as tracked changes with a comment each, and the
original is unchanged."""
import os, re, sys, tempfile, zipfile, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "data")
import app_gui as A  # noqa: F401
import banned as BN
import docxw
import techedit as T
import techeditdocx as TD

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


d = docxw.Doc()
d.heading("1.1 Kestrel Approach", 2)
d.para("The the program manager reports weekly to the government.  We use 7 engineers and twelve analysts.")
d.para("Our team delivers world-class reliability in order to make a decision about the web site, the website and the website.")
d.para("The thermal design was validated by testing in 2027-2029; power, thermal and data margins hold at 15% and the bus is 5kg.")
d.para("The [Insert customer name] mission requires the Osprey payload; the payload shall downlink. The Government approves.")
d.heading("1.2 Kestrel Schedule", 2)
d.para("Figure 3. Block diagram")
d.para("The Department of Defense (DOD) funds it and the DOD (DOD) reviews it. The telemtry link closes with margin.")
d.para("Because the bus carries redundant avionics, cross-strapped power, and a fault management layer that watches every "
       "subsystem ten times a second and isolates faults within one orbit, the mission meets its availability goal without help.")
d.para("Volume 2 of the plan has 3 steps in Section 4, and Figure 5 shows them.")
src = os.path.join(tmp, "Kestrel Volume I.docx")
d.save(src)
before = hashlib.sha256(open(src, "rb").read()).hexdigest()
refs = {"acronyms": {"DoD": "Department of Defense"}, "other_names": ["Osprey"], "banned": BN.starter(), "dictionaries": {"downlink"}}
fs = T.review(src, refs=refs)
by = {}
for f in fs:
    by.setdefault(f["rule"], []).append(f)


def hits(rid):
    return [f["hit"] for f in by.get(rid, [])]


check("doubled words, as Fix", hits("doubled") == ["The the"] and by["doubled"][0]["level"] == "Fix" and by["doubled"][0]["fix"] == "The")
check("two spaces between words", hits("spaces") == ["  "])
check("numbers one to nine spelled out in running text", hits("numbers_small") == ["7", "3"] and by["numbers_small"][0]["fix"] == "seven",
      hits("numbers_small"))
check("... not after Volume, Section, Figure or Step", "2" not in hits("numbers_small") and "4" not in hits("numbers_small")
      and "5" not in hits("numbers_small"), hits("numbers_small"))
check("10 and up as numerals", hits("numbers_large") == ["twelve", "ten"] and by["numbers_large"][0]["fix"] == "12", hits("numbers_large"))
check("government capitalized for the customer when the draft does", hits("government") == ["government"])
check("one term written two ways: the less used form", hits("variants") == ["web site"] and by["variants"][0]["fix"] == "website")
check("plain language: wordy phrases and nouns from verbs", hits("wordy") == ["in order to"] and hits("nominal") == ["make a decision"])
check("a claim with no number, once (the banned list's entry wins)", len(by.get("claims", [])) + len(by.get("banned", [])) >= 1
      and hits("claims").count("world-class") <= 1)
check("an en dash for year ranges", by["range_dash"][0]["fix"] == "2027–2029")
check("Chicago: percent spelled out in running text", by["percent"][0]["fix"] == "15 percent", hits("percent"))
check("a space between a number and its unit", by["unit_space"][0]["fix"] == "5 kg")
check("serial comma", any(f["fix"] == "thermal," for f in by.get("serial_comma", [])), hits("serial_comma"))
check("passive voice, as Check", "was validated" in hits("passive") and by["passive"][0]["level"] == "Check")
check("placeholders and another effort's name, as Fix", hits("placeholders") == ["[Insert customer name]"] and hits("stale") == ["Osprey"]
      and all(f["level"] == "Fix" for f in by["placeholders"] + by["stale"]))
check("a placeholder is not also a banned phrase", not any(f["start"] == by["placeholders"][0]["start"] for f in by.get("banned", [])))
check("shall written by the offeror", hits("shall") == ["shall"] and by["shall"][0]["fix"] == "will")
check("a caption that states no benefit", hits("captions") == ["Block diagram"])
check("acronyms: written another way than the list, spelled out twice", "DOD" in hits("acr_case") and hits("acr_twice") == ["(DOD)"])
check("spelling: a misspelling found; a word in the team's dictionary is not", "telemtry" in hits("spelling") and "downlink" not in hits("spelling"))
check("... ordinary words are known (the SCOWL list)", not {"program", "manager", "reliability", "validated", "engineers", "payload"} & set(hits("spelling")),
      hits("spelling"))
long_ = by.get("long_sentence", [])
check("a sentence over 30 words, with its count", len(long_) == 1 and "words; the limit is 30" in long_[0]["why"], [f["why"] for f in long_])
check("each finding names its section", by["captions"][0]["section"] == "1.2 Kestrel Schedule" and by["doubled"][0]["section"] == "1.1 Kestrel Approach")

# levels and the style sheet
last = T.review(src, level="last", refs=refs)
groups = {f["group"] for f in last}
check("Last look: leftovers, banned phrases and doubled words only", groups <= {"Leftovers", "Banned phrases", "Mechanics"}
      and {f["rule"] for f in last if f["group"] == "Mechanics"} <= {"doubled"}, groups)
sheet = {"off": ["passive"], "skips": [by["doubled"][0]["key"]], "terms": {"Kestrel bus": "Kestrel spacecraft bus"}}
fs2 = T.review(src, sheet=sheet, refs=refs)
check("the style sheet: a rule off, a place skipped", not any(f["rule"] in ("passive", "doubled") for f in fs2))
stats = T.section_stats(T.read(src)[0])
check("readability by section", [s["section"] for s in stats] == ["1.1 Kestrel Approach", "1.2 Kestrel Schedule"]
      and all(s["grade"] > 0 for s in stats), stats)

# the edited copy
acc = [f for f in fs if f["rule"] in ("doubled", "spaces", "numbers_small", "range_dash", "unit_space", "variants", "long_sentence", "placeholders")]
out = TD.copy_path(src)
got = TD.write(src, acc, out)
check("the edited copy: fixes as tracked changes, advice as comments", got["changes"] >= 6 and got["comments"] >= 2 and got["skipped"] == 0, got)
check("the original is unchanged", hashlib.sha256(open(src, "rb").read()).hexdigest() == before)
z = zipfile.ZipFile(out)
doc = z.read("word/document.xml").decode("utf-8")
com = z.read("word/comments.xml").decode("utf-8")
check("tracked changes in the copy", doc.count("<w:del ") >= 6 and doc.count("<w:ins ") >= 6, (doc.count("<w:del "), doc.count("<w:ins ")))
check("a comment for each, naming the rule", com.count("<w:comment ") == got["changes"] + got["comments"] and "A word written twice" in com)
check("Word can open it: comments declared", "comments+xml" in z.read("[Content_Types].xml").decode() and "comments.xml" in z.read("word/_rels/document.xml.rels").decode())


def accepted(xml):
    """The text with every change accepted."""
    xml = re.sub(r"<w:del [^>]*>.*?</w:del>", "", xml, flags=re.S)
    return [ "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p)) for p in re.findall(r"<w:p[ >].*?</w:p>", xml, flags=re.S)]


txt = accepted(doc)
check("accepting the changes gives the edited text", txt[1].startswith("The program manager reports weekly to the government. We use seven engineers")
      and "2027–2029" in txt[3] and "5 kg" in txt[3] and "the website, the website and the website" in txt[2], txt[1:4])
paras2, _left = T.read(out)
again = T.review((paras2, _left), refs=refs)
check("the copy says it holds tracked changes and comments", any(f["rule"] == "file_left" for f in again))
n = sum(checks)
print(f"TECHNICAL EDIT {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
