"""3.92.0: Acronyms on the page, the rules (acrpage). The filters as counts, a find inside a longer term (DC in DC-RVM),
the sources of a meaning against the decision, the effort's timeline, the A to Z rows a term adds, and the hyphen rule.
Fictional Kestrel terms."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import acrpage as P

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


R = {
    "TT&C": {"count": 9, "locations": ["RFP.pdf p.41", "SOW.docx para 12", "J-3.pdf p.2, image 1"],
             "custdef_all": [{"definition": "Telemetry, Tracking and Command", "where": "RFP.pdf p.41"}],
             "client_definitions": ["Telemetry, Tracking and Command"], "db_definitions": ["Telemetry, Tracking and Control"]},
    "DC": {"count": 6, "locations": ["SOW.docx para 3", "SOW.docx para 7", "RFP.pdf p.12"]},
    "RVM": {"count": 6, "locations": ["SOW.docx para 3", "SOW.docx para 7", "RFP.pdf p.12"]},
    "DC-RVM": {"count": 6, "locations": ["SOW.docx para 3", "SOW.docx para 7", "RFP.pdf p.12"]},
    "MOC": {"count": 6, "effort": "In the list", "list_definition": "Mission Operations Center", "locations": ["RFP.pdf p.41"]},
    "EIRP": {"count": 2, "effort": "In the list", "list_definition": "", "locations": ["RFP.pdf p.41"]},
    "SHALL": {"count": 40, "excluded": True, "locations": ["RFP.pdf p.41"]},
    "GEP": {"count": 1, "locations": ["J-3.pdf p.2, image 1"]},
}
kind = lambda d: "choice" if len(d.get("custdef_all") or []) > 1 else "other"
c = P.count_of(R, kind)
check("the counts: to decide, in the list, no definition yet, not a term, on pictures",
      c["To decide"] == 5 and c["In the list"] == 2 and c["No definition yet"] == 1 and c["Not a term"] == 1 and c["On pictures"] == 2, c)
lg = P.longer(R, "DC")
check("DC is found inside DC-RVM in 3 of 3 places", lg == {"whole": "DC-RVM", "shared": 3, "places": 3}, lg)
check("a term that stands alone has no longer term", P.longer(R, "MOC") is None)
src = P.sources(R["TT&C"], chosen="Telemetry, Tracking and Command")
check("sources, highest first: the customer's list, the customer's words, the team database",
      [r["source"] for r in src] == ["The customer's list", "The customer's words", "The team database"]
      and [r["against"] for r in src] == ["Agrees", "Agrees", "Differs"], src)
check("a differing team database does not send it back to decide", not P.differs(src))
src2 = P.sources(R["MOC"], team_db=["Memorandum of Clarification"])
check("a decision in the list is shown first as in use", src2[0] == {"source": "Your decision", "says": "Mission Operations Center", "against": "In use"}
      and src2[1]["against"] == "Differs", src2)
rows = P.table_rows([("SCF", "Satellite Control Facility"), ("SLA", "Service Level Agreement"), ("TLE", "Two-Line Element set"),
                     ("UHF", "Ultra High Frequency")], "TT&C", "Telemetry, Tracking and Command")
check("the A to Z rows around the new one, marked new", [r[0] for r in rows] == ["SLA", "TLE", "TT&C", "UHF"] and rows[2][2] is True, rows)


class WS:
    def __init__(self):
        self.d = {}

    def get(self, k, default=None):
        return self.d.get(k, default)

    def set(self, k, v):
        self.d[k] = v


ws = WS()
P.note(ws, "RFP read", found=61, to_decide=14)
P.note(ws, "Amendment 1", new=3, changed=1)
t = P.timeline(ws)
check("the timeline keeps each event with its counts", [x["what"] for x in t] == ["RFP read", "Amendment 1"]
      and P.counts_text(t[0]["counts"]) == "61 found, 14 to decide", t)


class S:
    def __init__(self, results):
        self.results = results
        self.parts = {}
        self.rules_extra = {}

    def save(self):
        pass


s = S({k: dict(v) for k, v in R.items()})
check("the hyphen rule is off until it is set", P.join_hyphenated(s) == 0 and not P.hyphen_whole(s))
n = P.set_hyphen_whole(s, True)
check("with the rule, DC and RVM found only inside DC-RVM join it", n == 2 and s.parts.get("DC", {}).get("whole") == "DC-RVM"
      and s.parts.get("RVM", {}).get("whole") == "DC-RVM", (n, s.parts))
check("the hyphen rule is kept", P.hyphen_whole(s) and s.rules_extra == {"hyphen_whole": True})

# In our drafts: a fictional Vol II draft, checked and fixed in a copy
import tempfile, zipfile
import docxw, acrfix as F
from lxml import etree
tmp = tempfile.mkdtemp()
d = docxw.Doc()
d.heading("2.1 Ground Segment Approach", 1)
d.para("Our design pairs two sites with a commercial GSaaS option, so no day of passes is lost.")
d.para("We contract Ground Station as a Service (GSaaS) passes at two commercial sites.")
d.para("The Mission Operations Center (MOC) runs both sites.")
d.para("Each Mission Operations Center (MOC) shift hands over at 0600; RF links are watched.")
d.table(["Acronym", "Definition"], [["GSaaS", "Ground Station as a Service"], ["LEO", "Low Earth Orbit"]], [2000, 6000])
draft = os.path.join(tmp, "Kestrel_VolII_draft_v4.docx"); d.save(draft)
before = open(draft, "rb").read()
ent = [("GSaaS", "Ground Station as a Service"), ("MOC", "Mission Operations Center"), ("LEO", "Low Earth Orbit")]
r = F.check(draft, ent)
kinds = {(f["term"], f["kind"]) for f in r["findings"]}
check("the draft: GSaaS used before it is spelled out, MOC spelled out again, RF not in the list",
      ("GSaaS", "before") in kinds and ("MOC", "again") in kinds and ("RF", "unlisted") in kinds and ("MOC", "before") not in kinds, kinds)
check("the volume's table: LEO listed but not used, MOC used but not listed",
      r["table"]["listed_not_used"] == ["LEO"] and r["table"]["used_not_listed"] == ["MOC"], r["table"])
check("each term's uses in the volume, the table left out", r["use"].get("GSaaS") == 2 and r["use"].get("MOC") == 2, r["use"])
out = F.fix(draft, os.path.join(tmp, "Kestrel_VolII_draft_v4 (fixes).docx"), [f for f in r["findings"] if f["kind"] != "unlisted"])
with zipfile.ZipFile(out) as z:
    root = etree.fromstring(z.read("word/document.xml"))
texts = [F._text(p) for p in F._paras(root)]
check("the copy, changes accepted: spelled out at the first use", any("commercial Ground Station as a Service (GSaaS) option" in t for t in texts), texts)
check("... the later spelled-out place keeps the acronym alone", any(t.startswith("We contract GSaaS passes") for t in texts), texts)
check("... spelled out again loses its words", any(t.startswith("Each MOC shift") for t in texts) and any("Mission Operations Center (MOC) runs" in t for t in texts), texts)
xml = etree.tostring(root).decode()
check("the fixes are tracked changes Word can accept or reject", "<w:ins " in xml and "<w:del " in xml and "w:delText" in xml and 'w:author="Stationkeeper"' in xml)
check("the draft itself is not changed", open(draft, "rb").read() == before)

print(f"{sum(checks)}/{len(checks)} passed")
sys.exit(0 if all(checks) else 1)
