"""3.2.0 writing support, without screens: win themes (add, words to look for, sections, change, order, remove), the
draft check (where each theme's words appear, by volume and by the sections it is linked to, from a Word draft's
headings), and storyboards (saved per section, the facts from the structure, the Word export)."""
import os, sys, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import themes as TH, storyboard as SB, effortrec as R, compliance as C, setupdoc as SD, pagebudget as PB, graphics as GX, docxw

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
rec = R.Record(tmp)
check("the words to look for come from the theme", TH.guess_words("Flight-proven thermal design lowers risk") ==
      ["flight-proven", "thermal", "design", "lowers", "risk"], TH.guess_words("Flight-proven thermal design lowers risk"))
a = TH.add(rec, "Flight-proven thermal design", "Less schedule risk for the Government", discriminator="On-orbit data",
           proof=["Four missions", " "], sections=["1.1 Thermal Design", "1.2 Risk"], words=["flight-proven", "on-orbit"], who="x")
b = TH.add(rec, "Local team", kind="Discriminator", words=["Colorado"], sections=["2.1 Schedule"])
rec = R.Record(tmp)
t = TH.get(rec, a)
check("a theme: benefit, discriminator, proof, sections, words", t["kind"] == "Win theme" and t["proof"] == ["Four missions"]
      and t["sections"] == ["1.1 Thermal Design", "1.2 Risk"] and t["words"] == ["flight-proven", "on-orbit"])
check("an empty theme is refused", TH.add(rec, "  ") == "")
check("found by section", [x["id"] for x in TH.for_section(rec, "1.2 Risk")] == [a])
check("moving and changing", TH.move(rec, b, -1) and [x["id"] for x in TH.items(rec)] == [b, a]
      and TH.update(rec, b, statement="Close to the customer") and not TH.update(rec, b, kind="Nonsense"))
# a draft with headings
d = docxw.Doc()
d.heading("Volume I Technical", 1)
d.heading("1.1 Thermal Design", 2); d.para("Our flight-proven radiator has on-orbit heritage. Flight-proven twice.")
d.heading("1.2 Risk", 2); d.para("We retire risk early.")
d.heading("2.1 Schedule", 2); d.para("The team sits in Colorado.")
p = os.path.join(tmp, "Volume I.docx"); d.save(p)
labels = ["Volume I Technical", "1.1 Thermal Design", "1.2 Risk", "2.1 Schedule"]
parts = TH.draft_sections(p, labels)
check("a draft splits by its headings into the structure's sections", "radiator" in parts["1.1 Thermal Design"] and "retire" in parts["1.2 Risk"], list(parts))
got = {c["id"]: c for c in TH.check(rec, [("Volume I", p)], labels)}
check("the draft check: where a theme's words appear, and the linked sections that never say them",
      got[a]["found"] == {"Volume I": 3} and got[a]["sections"] == {"1.1 Thermal Design": 3, "1.2 Risk": 0} and got[a]["missing"] == ["1.2 Risk"], got[a])
check("... a theme said in its section has nothing missing", got[b]["missing"] == [] and got[b]["total"] == 1, got[b])
check("removing a theme", TH.remove(rec, b) and TH.get(R.Record(tmp), b) is None)
# storyboards
M = C.Matrix(os.path.join(tmp, "m.xlsx"))
M.outline = [{"num": "1.1", "title": "Thermal Design", "level": 1}, {"num": "1.2", "title": "Risk", "level": 1}]
M.items = [{"id": "L.1-01", "text": "The Offeror shall describe its thermal design.", "decision": "Keep", "map": "1.1 Thermal Design",
            "type": "Sentence", "section": "L.1"}]
SD.set_people(M, "1.1 Thermal Design", "J. Garcia", "M. Chen")
PB.set_pages(M, "1.1 Thermal Design", 6)
GX.add(rec, "Radiator cutaway", section="1.1 Thermal Design")
check("a new storyboard is empty, not started", SB.get(rec, "1.1 Thermal Design")["status"] == "Not started")
check("saving one", SB.save(rec, "1.1 Thermal Design", message="Proven design, least risk", approach="First...\nThen...",
                            features=[{"feature": "Loop heat pipes", "benefit": "Margin", "proof": "Test data"}, {"feature": " "}],
                            status="Drafting", themes=[a]))
sb = SB.get(R.Record(tmp), "1.1 Thermal Design")
check("... kept in the effort record; empty feature rows dropped", sb["message"] == "Proven design, least risk" and len(sb["features"]) == 1
      and sb["status"] == "Drafting" and sb["by"])
check("... saving the same again changes nothing", not SB.save(rec, "1.1 Thermal Design", message="Proven design, least risk"))
f = SB.facts(rec, M, "1.1 Thermal Design")
check("the facts from the structure: lead, writers, budget, requirements, themes, graphics", f["lead"] == "J. Garcia" and f["with"] == "M. Chen"
      and f["pages"] == 6 and len(f["reqs"]) == 1 and [x["id"] for x in f["themes"]] == [a] and len(f["graphics"]) == 1, f)
check("status counts", SB.status_counts(rec, labels[1:3]) == {"Not started": 1, "Drafting": 1, "Ready for review": 0, "Approved": 0})
out = SB.export(os.path.join(tmp, "sb.docx"), rec, M, ["1.1 Thermal Design", "1.2 Risk"], "Kestrel", ("CUI", "502B85"))
x = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
check("the Word storyboard: a page per section with what was written and what the structure says",
      "Storyboard: 1.1 Thermal Design" in x and "Storyboard: 1.2 Risk" in x and "Loop heat pipes" in x and "6 pages" in x
      and "The Offeror shall describe its thermal design." in x and "Radiator cutaway" in x and 'w:type="page"' in x)
n = sum(checks)
print(f"WRITING {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
