"""4.70.0: the Response Structure pass under the screen (structmark). A mark fills the outline at once, under the volume
or heading marked above it, in the customer's order; the same title attaches, a near one is asked, anything else is
added; taking a mark off takes its own empty heading away. Fictional (Kestrel)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import compliance as C, outline_ops as OO, setupdoc as SD, shredtypes as ST, structmark as SM, assignlinks as AL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def item(i, text, **kw):
    it = {"id": i, "text": text, "decision": "", "suggest": "", "file": "Kestrel_Section_L.pdf", "section": "L.2",
          "type": "Requirement", "map": "", "lead": "", "context_for": "", "where": "", "page": 1}
    it.update(kw)
    return it


def labels(M):
    return [("  " * (o["level"] - 1)) + C.outline_label(o) for o in M.outline]


d = tempfile.mkdtemp()
M = C.Matrix(os.path.join(d, "Kestrel_Matrix.xlsx"), "Kestrel")
M.items = [item("K-1", "Volume I Technical shall not exceed 40 pages."),
           item("K-2", "Technical Approach"),
           item("K-3", "Thermal Design"),
           item("K-4", "Risk Management"),
           item("K-5", "Volume II Management"),
           item("K-6", "Staffing Plan"),
           item("K-7", "The Offeror shall describe the thermal design.", type="Requirement"),
           item("K-8", "Volume III shall be organized as follows: (1) Past Performance; (2) Small Business Plan; (3) Price Narrative.",
                file="Kestrel_Section_M.pdf"),
           ]
it = {x["id"]: x for x in M.items}

check("the lines of a plain piece: its title, without the page limit", SM.lines(M, it["K-1"]) == ["Volume I Technical"], SM.lines(M, it["K-1"]))
r = SM.mark(M, it["K-1"], "volume")
check("Volume: the outline has the volume at once", labels(M) == ["Volume I Technical"] and r["made"] == ["Volume I Technical"], labels(M))
check("... a page limit in the same words is kept, with the piece that required it", M.outline[0].get("limit") == 40 and M.outline[0].get("req") == "K-1"
      and "page 1" in M.outline[0].get("ref", ""), M.outline[0])
check("... it is one of the response's volumes", SD.volumes_of(M)[0] == "several" and SD.volumes_of(M)[2] == ["Volume I Technical"])
check("... and the piece is typed Response Structure, at Volume", ST.has(it["K-1"], "structure") and SM.level_of(M, it["K-1"]) == "volume")
SM.mark(M, it["K-2"], "h1"); SM.mark(M, it["K-4"], "h1")
check("Heading 1 goes under the volume marked above it, numbered", labels(M) == ["Volume I Technical", "  1 Technical Approach", "  2 Risk Management"], labels(M))
SM.mark(M, it["K-3"], "h2")
check("Heading 2 goes under the Heading 1 marked above it", labels(M) == ["Volume I Technical", "  1 Technical Approach", "    1.1 Thermal Design", "  2 Risk Management"], labels(M))
SM.mark(M, it["K-6"], "h1")
check("marked before its volume, a heading goes under the nearest one above", labels(M)[-1] == "  3 Staffing Plan", labels(M))
SM.unmark(M, it["K-6"])
check("the mark taken off: its own empty heading goes, and the type", labels(M)[-1] == "  2 Risk Management" and not ST.has(it["K-6"], "structure")
      and "K-6" not in SM.marks(M), labels(M))
SM.mark(M, it["K-5"], "volume"); SM.mark(M, it["K-6"], "h1")
check("a second volume, and its heading under it, numbered from 1", labels(M)[-2:] == ["Volume II Management", "  1 Staffing Plan"], labels(M))
SM.unmark(M, it["K-3"]); SM.mark(M, it["K-3"], "h1")
check("marked out of order, a heading sits in the customer's order", labels(M)[:4] == ["Volume I Technical", "  1 Technical Approach", "  2 Thermal Design", "  3 Risk Management"], labels(M))

# attach, ask, add
M.items.insert(4, item("K-9", "technical  approach.")); it["K-9"] = M.items[4]
n = len(M.outline)
r = SM.mark(M, it["K-9"], "h1")
check("the same title in the same volume attaches without asking (capitals, spacing, punctuation left out)",
      r["attached"] == ["1 Technical Approach"] and not r["made"] and len(M.outline) == n, r)
check("... the heading keeps the first piece that required it; the second mark finds it", M.outline[1]["req"] == "K-2"
      and SM.entries_of(M, "K-9") == [1])
SM.unmark(M, it["K-9"])
check("... taking that mark off leaves the heading and its first piece", len(M.outline) == n and M.outline[1].get("req") == "K-2")
M.items.insert(5, item("K-4b", "Risk Management Approach"))
it["K-4b"] = M.items[5]
r = SM.mark(M, it["K-4b"], "h1")
check("a near match changes nothing and is asked once", r["ask"] == [{"title": "Risk Management Approach", "label": "3 Risk Management"}]
      and len(M.outline) == n and "K-4b" not in SM.marks(M), r)
r = SM.mark(M, it["K-4b"], "h1", attach=True)
check("Attach: no heading is added", r["attached"] == ["3 Risk Management"] and len(M.outline) == n, r)
SM.unmark(M, it["K-4b"])
r = SM.mark(M, it["K-4b"], "h1", attach=False)
check("Add as new: a heading of its own, after the one before it", r["made"] == ["4 Risk Management Approach"] and len(M.outline) == n + 1, labels(M))
check("the same title in another volume does not attach", SM.match(M, "Staffing Plan", SM._scope(M, 0))[0] == "", SM.match(M, "Staffing Plan", SM._scope(M, 0)))

# a piece that lists several sections
check("a piece that lists several sections: each item is a line", SM.lines(M, it["K-8"]) == ["Volume III", "Past Performance", "Small Business Plan", "Price Narrative"],
      SM.lines(M, it["K-8"]))
M.items.insert(M.items.index(it["K-8"]), item("K-8v", "Volume III", file="Kestrel_Section_M.pdf")); it["K-8v"] = M.items[M.items.index(it["K-8"]) - 1]
SM.mark(M, it["K-8v"], "volume")
r = SM.mark(M, it["K-8"], "h1", titles=["Past Performance", "Price Narrative"])
check("one press makes the ticked lines headings at the level picked; an unticked one is left out",
      labels(M)[-2:] == ["  1 Past Performance", "  2 Price Narrative"] and M.outline[-3]["num"] == "Volume III" and len(r["made"]) == 2, labels(M))
check("... each keeps the piece that required it", [M.outline[i]["req"] for i in SM.entries_of(M, "K-8")] == ["K-8", "K-8"])

# a heading with something assigned is kept
it["K-7"]["decision"] = "Keep"
AL.assign(M, ["K-7"], "2 Thermal Design")
before = len(M.outline)
SM.unmark(M, it["K-3"])
check("a heading with a piece assigned stays when its mark goes; it only loses its link",
      len(M.outline) == before and "req" not in M.outline[2] and M.outline[2]["title"] == "Thermal Design", M.outline[2])

# not needed, the documents, the next suggestion
check("each document's state: finds counted", [(x["file"], x["state"]) for x in SM.docs(M)] ==
      [("Kestrel_Section_L.pdf", f"Has finds ({sum(1 for k, m in SM.marks(M).items() if m['level'] in SM.DEPTH and it[k]['file'] == 'Kestrel_Section_L.pdf')})"),
       ("Kestrel_Section_M.pdf", "Has finds (2)")], SM.docs(M))
M2 = C.Matrix(os.path.join(d, "Kestrel2_Matrix.xlsx"), "Kestrel")
M2.items = [item("H-1", "The proposal shall be organized as follows:"), item("H-2", "(1) Technical Approach", lead="The proposal shall be organized as follows:"),
            item("H-3", "The Offeror shall submit two volumes: Volume I (Technical) and Volume II (Cost)."), item("H-4", "The Offeror shall describe its safety plan."),
            item("H-5", "Appendix requirements", file="Kestrel_SOW.pdf")]
check("a document nobody marked: Not looked at; one click says Nothing of this kind here, and takes it back",
      SM.docs(M2)[1]["state"] == "Not looked at" and SM.set_none(M2, "Kestrel_SOW.pdf") and SM.docs(M2)[1]["state"] == "Nothing of this kind here"
      and not SM.set_none(M2, "Kestrel_SOW.pdf", False) and SM.docs(M2)[1]["state"] == "Not looked at", SM.docs(M2))
sg = [x["id"] for x in SM.suggestions(M2)]
check("the pass suggests the pieces that read as setting the structure, and no others", sg == ["H-1", "H-3"], sg)
check("the suggestion is the level the words read as", SM.suggest(M2, M2.items[2]) == "volume" and SM.suggest(M2, M2.items[3]) == "", SM.suggest(M2, M2.items[2]))
SM.not_needed(M2, M2.items[0])
check("Not needed: out of the pass's next, no heading, and it can be reopened", SM.next_suggestion(M2)["id"] == "H-3" and not M2.outline
      and SM.level_of(M2, M2.items[0]) == "x" and SM.not_needed(M2, M2.items[0], False) is False and SM.next_suggestion(M2)["id"] == "H-1")
check("next goes on after the piece in hand, and comes round", SM.next_suggestion(M2, "H-1")["id"] == "H-3" and SM.next_suggestion(M2, "H-3")["id"] == "H-1")
M2.items[3][ST.FIELD] = "structure"
check("a piece typed Response Structure before 4.70.0 shows at the level its words read as; nothing is rewritten",
      SM.level_of(M2, M2.items[3]) in ("h1", "h2", "h3") and "H-4" not in SM.marks(M2) and M2.items[3] in SM.suggestions(M2))
M3 = C.Matrix(os.path.join(d, "Kestrel3_Matrix.xlsx"), "Kestrel")
M3.outline = C.parse_outline("1 Technical Approach\n2 Management")
M3.items = [item("J-1", "Technical Approach"), item("J-2", "Past Performance")]
SM.mark(M3, M3.items[0], "h1"); SM.mark(M3, M3.items[1], "h1")
check("an outline already there is never replaced: one attaches, one is added", [C.outline_label(o) for o in M3.outline] ==
      ["1 Technical Approach", "2 Management", "3 Past Performance"] or [o["title"] for o in M3.outline] == ["Technical Approach", "Management", "Past Performance"],
      [C.outline_label(o) for o in M3.outline])
M3.save()
M4 = C.Matrix(M3.path if hasattr(M3, "path") else os.path.join(d, "Kestrel3_Matrix.xlsx"), "Kestrel"); M4.load()
check("saved and opened again: the marks, the headings' pieces and the levels are there", SM.marks(M4) == SM.marks(M3)
      and [o.get("req") for o in M4.outline] == [o.get("req") for o in M3.outline] and SM.level_of(M4, M4.items[1]) == "h1", SM.marks(M4))
print(f"STRUCTMARK 4700 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
