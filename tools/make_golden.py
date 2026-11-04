"""Save the golden files for this version (3.38.1): what a user of this version saves, so every later version can be
tested to open it with no lost work (tests/test_golden.py). Fictional content only (the Kestrel effort).

    python tools/make_golden.py 3.38           writes tests/golden/3.38/ (refuses to overwrite one that exists)

Writes:
  Kestrel.skpkg                 an effort package: the Effort List, the effort's saved work (settings with its formatting,
                                response type and rules it departs from; its record with a due date, a note and a task)
  config/production_standards.json, config/rules.json, config/suggestion_rules.json, config/template_library/...
                                the global standards with an effort type, style roles and Used on; an own rule and a rule
                                turned off; a phrase rule; a saved matrix view
  Team.skdata                   a Stationkeeper Data file carrying the standards
  expect.json                   what the test must find in each, written from the values above
Keep one set per minor version. Never put real data here."""
import json, os, shutil, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def make(version, out_root=None):
    out = os.path.join(out_root or os.path.join(ROOT, "tests", "golden"), version)
    if os.path.exists(out):
        raise SystemExit(f"{out} already exists: golden files are never rewritten")
    tmp = tempfile.mkdtemp()
    os.environ["SK_DATA_DIR"] = os.path.join(tmp, "data")
    import app_gui as A  # noqa: F401  (the engine first, as the program does)
    import effort as E, effortpkg as P, effortrec as R, matrixdesign as MD, prodrules as PRL, rulebook as RB
    import suggestrules as SR, teamdata as TD, workspace as W
    cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
    # the global standards
    data = PRL.load(cfg)
    data.setdefault("effort_types", []).append({"id": "kestrel_rfi", "name": "Kestrel RFI", "profiles": [data["types"][0]["id"]],
                                                "default_profile": data["types"][0]["id"], "response_type": "RFI"})
    data["company"]["style_roles"] = {"a_number": "AA A Number", "restriction": "AA Restriction"}
    data["company"].setdefault("style_defs", {})["AA Title Page Name"] = {"type": "paragraph", "used_on": "Title page", "size": 20}
    data["company"]["variables"]["body_font"] = "Georgia"
    extra = {}
    try:                                                  # 3.42.0: a footer built as a table (Rule 7's, with the team's line)
        import hfbuild as HB
        data["company"].setdefault("hf_layouts", {}).setdefault("body", {})["footer"] = HB.r7_footer(line2="Kestrel standard line")
        extra["hf_cells"] = {"part": "body", "line2": "Kestrel standard line"}
    except ImportError:
        pass
    try:                                                  # 3.45.0: a section's contents and its own page setup
        import sectioncontents as SC
        SC.set_items(data["company"], "body", [{"kind": "placeholder", "title": "Executive Summary", "pages": 2}])
        cover = next(p for p in data["company"]["pagination"]["parts"] if p.get("key") == "cover")
        cover["setup"] = "portrait"
        extra["sections"] = {"part": "body", "title": "Executive Summary", "setup_part": "cover", "setup": "portrait"}
    except (ImportError, StopIteration, KeyError):
        pass
    if "team_line" in (data["company"].get("variables") or {}):   # 3.48.0: Rule 7's team line from the variables; a Quick Part kept as built
        data["company"]["variables"]["team_line"] = "Kestrel Systems proprietary"
        data["company"].setdefault("quick_parts", {"one_gallery": True, "entries": []})["entries"].append(
            {"name": "Kestrel Callout", "category": "05 Callouts", "source": "qp_kestrel.dotx", "as_built": True})
        extra["team_line"] = {"words": "Kestrel Systems proprietary", "qp": "Kestrel Callout"}
    PRL.save(cfg, data)
    try:                                                  # 3.49.0: the standards as library items; a Draft item for one effort type
        import libconvert as CV, libcats as LC, templatelib as TL
        CV.convert(cfg)
        lib = TL.Library(cfg)
        it, _s = lib.add("style", "AA Kestrel Draft Style", {"type": "paragraph", "font": "Georgia", "size": 13})
        it["status"] = "draft"; lib.save()
        LC.set_effort_types(lib, [it["id"]], ["kestrel_rfi"])
        extra["library"] = {"draft": "AA Kestrel Draft Style", "effort_type": "kestrel_rfi", "converted": True}
    except ImportError:
        pass
    RB.add(cfg, "Every graphic has a callout in the text before it appears.", group="Writing")
    RB.set_on(cfg, 12, False)
    SR.add_rule(cfg, None, "proposals are limited to", "L", scope="team", why="page limits are instructions")
    vid = MD.save_view(cfg, "Kestrel outline view", MD.default("outline"))
    # an effort
    eff = os.path.join(tmp, "Kestrel"); os.makedirs(os.path.join(eff, "Customer documents"))
    lst = os.path.join(eff, "Kestrel_Effort_List.xlsx")
    L = E.EffortList(lst, "Kestrel"); L.pending = True; L.save()
    dd = W.data_dir_for(lst)
    ws = W.Workspace(dd, "Kestrel")
    ws.set("prod_std", {"effort_type": "kestrel_rfi", "over": {"variables": {"body_size": 11.5}}, "response_type": "RFI",
                        "rules_off": ["2"]})
    rec = R.Record(dd); rec.data["due"] = "2026-12-15 14:00"; rec.data["notes"].append({"text": "Kickoff held", "who": "pm"})
    rec.data["tasks"].append({"id": "t1", "text": "Draft the cover", "owner": "Dana Ruiz", "done": False}); rec.save()
    open(os.path.join(eff, "Customer documents", "Kestrel RFI.txt"), "w").write("The Offeror shall describe its approach.")
    try:                                                  # 3.39.0: a data call and a reviewer comment with its disposition
        import datacalls as DC, dispositions as DP
        rec = R.Record(dd)
        cid = DC.add(rec, "Give the TVAC test history of the bus.", section="1.1 Technical Approach", req="L.4.2",
                     words="150 to 250 words", owner="Dana Ruiz", due="2026-12-01")
        DC.update(rec, cid, answer="Three campaigns, eight cycles each.")
        kid = DP.add(rec, "Red team", "Add the test schedule.", author="G. Park", where="L.4.2 (1.1 Technical Approach)")
        DP.set_disposition(rec, kid, "Reject", reason="It is in Volume III", owner="Dana Ruiz", due="2026-12-02")
        extra.update({"data_call": {"code": "DC-1", "answer": "Three campaigns, eight cycles each.", "status": "Answered"},
                      "comment": {"text": "Add the test schedule.", "disposition": "Reject", "reason": "It is in Volume III"}})
    except ImportError:
        pass
    try:                                                  # 3.46.0: a Draft Status read with each section's status
        import setupread as SRD
        if hasattr(SRD, "section_status"):
            rec = R.Record(dd)
            SRD.keep(rec, {"file": "Volume I Technical.docx", "when": "2026-11-04T06:00", "counts": {"Not started": 1},
                           "removed": 0, "moved": 0, "styles": [], "words": 0,
                           "sections": [{"section": "1.1 Technical Approach", "status": "Not started", "pages": 0, "budget": 2.0,
                                         "removed": [], "moved": []}]})
            extra["draft"] = {"section": "1.1 Technical Approach", "status": "Not started"}
    except ImportError:
        pass
    try:                                                  # 3.41.0: a capture whose source is a meeting
        import excerpts as EX, meetings as MT
        if hasattr(EX, "SOURCES"):
            rec = R.Record(dd)
            mid = MT.add_meeting(rec, "Kickoff", "2026-11-02", participants=["Dana Ruiz"], notes="They worry about schedule risk.")
            EX.add(rec, "hot", [EX.part_from_meeting(MT.get(rec, mid), "They worry about schedule risk.")], source="meeting")
            extra["capture"] = {"text": "They worry about schedule risk.", "source": "meeting"}
    except ImportError:
        pass
    os.makedirs(out)
    man = P.save(os.path.join(out, "Kestrel"), "Kestrel", lst, dd, info={"client": "Fictional Space Office"},
                 customer_dir=os.path.join(eff, "Customer documents"), stage="Author drafts", app_version=version,
                 who="golden", when="2026-11-03T22:00")
    TD.export(cfg, os.path.join(tmp, "Team" + TD.EXT), parts=["standards"])   # never written into a git folder directly
    shutil.copy2(os.path.join(tmp, "Team" + TD.EXT), os.path.join(out, "Team" + TD.EXT))
    shutil.copytree(cfg, os.path.join(out, "config"), ignore=shutil.ignore_patterns("*.lock", "*.tmp"))
    expect = {"version": version, "package": os.path.basename(man["path"]), "effort": "Kestrel", "stage": "Author drafts",
              "prod_std": {"effort_type": "kestrel_rfi", "response_type": "RFI", "rules_off": ["2"], "body_size": 11.5},
              "record": {"due": "2026-12-15 14:00", "note": "Kickoff held", "task": "Draft the cover"},
              "customer_file": "Kestrel RFI.txt",
              "standards": {"effort_type": "Kestrel RFI", "a_number": "AA A Number", "used_on": ["AA Title Page Name", "Title page"],
                            "body_font": "Georgia"},
              "rules": {"own": "Every graphic has a callout in the text before it appears.", "off": "12"},
              "phrase": "proposals are limited to", "matrix_view": "Kestrel outline view", "data_file": "Team" + TD.EXT, **extra}
    with open(os.path.join(out, "expect.json"), "w", encoding="utf-8") as f:
        json.dump(expect, f, indent=1)
    return out, vid


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    print(make(sys.argv[1])[0])
