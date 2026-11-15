"""4.43.0 (ST39 to ST44 of 2026-11-15): the rules behind the gallery and the builder. A template is duplicated and
archived; its sample pages follow its picks; its exported file is read back and checked against its picks, and a pick
changed after the export shows as a difference. Fictional names."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import namedtemplates as NT, pagelayouts as PGL, prodrules as PRL, stylelib as SL, templatelib as TL
import templateproof as TPF, templatesample as TSM

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
lib = TL.Library(cfg)
s1, _ = SL.new_style(lib, "Body Text", "paragraph", {"font": "Arial", "size": 11})
k = SL.new_set(lib, "RFP volume"); SL.add_to_set(lib, k["id"], [s1["id"]])
data = PRL.load(cfg)
lay = PGL.new(cfg, "layout", "Letter, 0.75 in", data["company"]); PGL.set_page(cfg, lay["id"], None, [0.75] * 4)
t = NT.new(cfg, "Page-limited RFP, Technical")
NT.set_recipe(cfg, t["id"], {"style_sets": [k["id"]], "layout": lay["id"]})

# ---------------------------------------------------------------- duplicate and archive
d1 = NT.duplicate(cfg, t["id"]); d2 = NT.duplicate(cfg, t["id"])
check("Duplicate: Copy of ..., then Copy 2 of ..., the same picks, not made", d1["name"] == "Copy of Page-limited RFP, Technical"
      and d2["name"] == "Copy 2 of Page-limited RFP, Technical" and d1["sets"] == NT.get(cfg, t["id"])["sets"] and not d1.get("made"), (d1, d2))
check("... under a name given; a name in use or an unknown template is refused", NT.duplicate(cfg, t["id"], "Program plan")["name"] == "Program plan"
      and NT.duplicate(cfg, t["id"], "program PLAN") is None and NT.duplicate(cfg, "nope") is None)
check("Archive: off the shown ones, still among every one", NT.archive(cfg, d1["id"]) and d1["id"] not in [x["id"] for x in NT.shown(cfg)]
      and [x["id"] for x in NT.shown(cfg, True)] == [d1["id"]] and len(NT.every(cfg)) == 4 and not NT.archive(cfg, "nope"))
check("... and back", NT.archive(cfg, d1["id"], on=False) and NT.shown(cfg, True) == [] and "archived" not in NT.get(cfg, d1["id"]))

# ---------------------------------------------------------------- sample pages
std = NT.std_of(cfg, NT.get(cfg, t["id"]))
pages = TSM.pages(std, cfg, ["Cover"])
check("the sample pages: each starting page, front matter, body, a landscape page, an appendix", [p["key"] for p in pages] == ["start0", "front", "body", "landscape", "appendix"]
      and pages[0]["label"] == "Cover" and pages[0]["blocks"] == [("built", "Cover")], [p["key"] for p in pages])
check("they take the template's margins", all(p["m"] == [0.75] * 4 for p in pages if p["key"] != "landscape") and pages[1]["w"] == 8.5 and pages[1]["h"] == 11)
check("the landscape page is turned", pages[3]["w"] == 11 and pages[3]["h"] == 8.5)
check("each part's page number: i, 1-1, A-1", [p["number"] for p in pages] == ["", "i", "1-1", "1-1", "A-1"], [p["number"] for p in pages])
check("the header and the marking are the standard's, with sample words", pages[2]["header"][0] == "Volume I: Technical" and pages[2]["footer"] == "Restriction marking"
      and pages[0]["header"] == ("", "", "") and pages[0]["footer"] == "", pages[2]["header"])
body = dict((b[0], b) for b in pages[2]["blocks"])
check("the body page holds headings, text, a list, a table and a figure with their captions", [b[0] for b in pages[2]["blocks"]] == ["h", "text", "h", "text", "list", "table", "h", "figure"]
      and body["table"][1] == {"text": "Table 1-1.", "above": True} and body["figure"][1] == {"text": "Figure 1-1.", "above": False}, pages[2]["blocks"])
check("headings carry no number while heading numbering is off", all(b[2] == "" for b in pages[2]["blocks"] if b[0] == "h"))
on = PRL.merge(std, {"heading_numbering": {"on": True}})
check("... and their numbers when it is on", [b[2] for b in TSM.pages(on, cfg)[1]["blocks"] if b[0] == "h"] == ["1", "1.1", "1.1.1"])
check("a page number in words: none, plain, by chapter", TSM.page_number(None) == "" and TSM.page_number({"fmt": "decimal"}) == "1"
      and TSM.page_number({"fmt": "decimal", "chapter_level": 1, "separator": "period"}) == "1.1")

# ---------------------------------------------------------------- the exported file, checked
check("not made: nothing to check", TPF.check(cfg, NT.get(cfg, t["id"])) == [] and TPF.words([]) == "")
job = NT.make(cfg, os.path.join(tmp, "out"), t["id"])
ticks = TPF.check(cfg, NT.get(cfg, t["id"]))
by = {x["key"]: x for x in ticks}
check("four checks, in order", [x["key"] for x in ticks] == ["layout", "numbering", "styles", "quick"] and [x["name"] for x in ticks] == ["Page Setup", "Page Numbers", "Styles", "Quick Parts"])
check("the page: the file's size and margins are the pick's", by["layout"]["state"] == TPF.OK and by["layout"]["says"] == "Letter, margins 0.75, 0.75, 0.75, 0.75 in", by["layout"])
check("page numbers: each numbered part has a section numbered its way", by["numbering"]["state"] == TPF.OK and by["numbering"]["says"].startswith("Front matter: small Roman (i)"), by["numbering"])
check("styles: every style of the style sets is in the file", by["styles"]["state"] == TPF.OK and by["styles"]["says"] == "All 1 styles are in the file", by["styles"])
check("Quick Parts: none picked is said, not ticked", by["quick"]["state"] == TPF.SKIP and by["quick"]["says"] == "No Quick Part set picked")
check("in a line", TPF.words(ticks) == "The file holds what was picked (3 of 3 checks)", TPF.words(ticks))
PGL.set_page(cfg, lay["id"], None, [0.5, 0.75, 0.75, 0.75])
ticks = TPF.check(cfg, NT.get(cfg, t["id"]))
check("a pick changed since the export shows as a difference, in words", ticks[0]["state"] == TPF.BAD and ticks[0]["says"] == "Margins differ: top is 0.75 in, picked 0.5 in"
      and TPF.words(ticks) == "Check the file: Page Setup: Margins differ: top is 0.75 in, picked 0.5 in", ticks[0])
s2, _ = SL.new_style(lib, "Callout Text", "paragraph", {"font": "Arial", "size": 10}); SL.add_to_set(lib, k["id"], [s2["id"]])
ticks = TPF.check(cfg, NT.get(cfg, t["id"]), lib=TL.Library(cfg))
check("a style added to the set since the export is named", ticks[2]["state"] == TPF.BAD and ticks[2]["says"] == "1 of 2 styles are not in the file: Callout Text", ticks[2])
with open(job.copy, "wb") as f:
    f.write(b"not a zip")
ticks = TPF.check(cfg, NT.get(cfg, t["id"]))
check("a file that cannot be opened is said so, never ticked", [x["key"] for x in ticks] == ["file"] and ticks[0]["state"] == TPF.BAD)
os.remove(job.copy)
check("a file that is gone: nothing to check", TPF.check(cfg, NT.get(cfg, t["id"])) == [])
shutil.rmtree(tmp, ignore_errors=True)
print(f"TEMPLATE GALLERY 4430 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
