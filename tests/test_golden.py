"""3.38.1 every version opens what every earlier version saved, with no lost work. tests/golden/<version>/ holds what a
user of that version saved (tools/make_golden.py, fictional): an effort package, the global standards, the rules, the
phrase rules, the template library and a Stationkeeper Data file. For each set: the package unpacks and the effort's
formatting, response type, rules it departs from, record (due date, note, task) and customer file are all there; the
standards, rules and library read back with their values; the effort's standard is built from them; the data file
reads and installs. The golden files are copied first and never changed. Add one set per minor version."""
import json, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "data")
import app_gui as A  # noqa: F401
import effortpkg as P, effortrec as R, matrixdesign as MD, prodrules as PRL, rulebook as RB, suggestrules as SR
import teamdata as TD, workspace as W

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


GOLD = os.path.join(HERE, "golden")
sets = sorted(d for d in os.listdir(GOLD) if os.path.isfile(os.path.join(GOLD, d, "expect.json"))) if os.path.isdir(GOLD) else []
check("there is at least one golden set (one per minor version from 3.38)", sets, sets)
for ver in sets:
    src = os.path.join(GOLD, ver)
    ex = json.load(open(os.path.join(src, "expect.json"), encoding="utf-8"))
    work = os.path.join(tmp, ver); shutil.copytree(src, work)
    cfg = os.path.join(work, "config")
    # the effort package
    pkg = os.path.join(work, ex["package"])
    man = P.read_manifest(pkg)
    check(f"{ver}: the package's manifest reads", man.get("effort") == ex["effort"] and man.get("stage") == ex["stage"], man.get("effort"))
    got = P.unpack(pkg, os.path.join(work, "opened"), W.data_dir_for)
    check(f"{ver}: the package unpacks, every file matching its fingerprint", os.path.isfile(got["list"]) and os.path.isdir(got["data"]))
    ws = W.Workspace(got["data"], ex["effort"])
    eff = ws.get("prod_std") or {}
    want = ex["prod_std"]
    check(f"{ver}: the effort's formatting is all there", eff.get("effort_type") == want["effort_type"] and eff.get("response_type")
          == want["response_type"] and eff.get("rules_off") == want["rules_off"]
          and (eff.get("over") or {}).get("variables", {}).get("body_size") == want["body_size"], eff)
    rec = R.Record(got["data"]).data
    check(f"{ver}: the effort's record is all there (due date, note, task)", rec.get("due") == ex["record"]["due"]
          and any(n.get("text") == ex["record"]["note"] for n in rec.get("notes", []))
          and any(t.get("text") == ex["record"]["task"] for t in rec.get("tasks", [])), {k: rec.get(k) for k in ("due", "notes", "tasks")})
    check(f"{ver}: the customer's file came with it", os.path.isfile(os.path.join(got.get("customer_dir") or "", ex["customer_file"])),
          got.get("customer_dir"))
    if ex.get("data_call"):                               # 3.39 on: a data call and a reviewer comment
        import datacalls as DC, dispositions as DP
        r2 = R.Record(got["data"])
        dc = DC.by_code(r2, ex["data_call"]["code"])
        check(f"{ver}: the data call is all there", dc is not None and dc.get("answer") == ex["data_call"]["answer"]
              and dc.get("status") == ex["data_call"]["status"], dc)
        k = next((x for x in DP.items(r2) if x.get("text") == ex["comment"]["text"]), None)
        check(f"{ver}: the reviewer comment and its disposition are all there", k is not None and k.get("disposition")
              == ex["comment"]["disposition"] and k.get("reason") == ex["comment"]["reason"], k)
    if ex.get("capture"):                                 # 3.41 on: a capture with its source
        import excerpts as EX
        k = next((x for x in EX.excerpts(R.Record(got["data"])) if EX.text_of(x) == ex["capture"]["text"]), None)
        check(f"{ver}: the capture and its source are all there", k is not None and EX.source_of(k) == ex["capture"]["source"], k)
    if ex.get("draft"):                                   # 3.46 on: a Draft Status read with each section's status
        import setupread as SRD
        st = SRD.section_status(R.Record(got["data"]))
        check(f"{ver}: the Draft Status read and its sections are all there", (st.get(ex["draft"]["section"]) or {}).get("status")
              == ex["draft"]["status"], st)
    if ex.get("techedit"):                                # 3.54 on: the effort's style sheet for Technical Edit
        sh = ws.get("techedit_sheet") or {}
        te = ex["techedit"]
        check(f"{ver}: the style sheet reads back", (sh.get("terms") or {}).get(te["term"][0]) == te["term"][1]
              and te["off"] in (sh.get("off") or []) and te["word"] in (sh.get("words") or []), sh)
    if ex.get("acronyms"):                                # 3.51 on: Omit and a first use set by hand, kept in the acronym results
        import acrsession as AS
        s = AS.AcronymSession(ws, got["list"], {}, {})
        s.restore()
        t, f, loc = ex["acronyms"]["first_use"]
        check(f"{ver}: the omitted term stays out (3.76.0: Not a term) and the first use set by hand is kept", (ex["acronyms"]["omitted"] in s.omitted or (ver >= "3.51" and s.effort is not None
              and (s.effort.rows.get(ex["acronyms"]["omitted"]) or {}).get("Status") == "Not a term"))   # 3.76.0: omitted became Not a term
              and (s.results.get(ex["acronyms"]["omitted"]) or {}).get("excluded") and (s.first_use_set.get(t) or {}).get(f) == loc,
              (s.omitted, s.first_use_set))
    if ex.get("parts"):                                   # 3.76 on: part of a longer term, kept with the effort's scan
        import acrsession as AS
        s = AS.AcronymSession(ws, got["list"], {}, {})
        s.restore()
        check(f"{ver}: a part of a longer term is kept", (s.parts.get(ex["parts"]["part"]) or {}).get("whole") == ex["parts"]["whole"], s.parts)
    if ex.get("profile"):                                 # 3.52 on: a profile's volumes and limit inside its effort type
        import effortprofiles as EPF
        dd_ = PRL.load(cfg)
        pr = ex["profile"]
        lim = next((r for r in EPF.limits(EPF.resolved(dd_, pr["eid"], pr["pid"])) if r["scope"] == "table"), {})
        check(f"{ver}: the profile's volumes and RFP limit read back", EPF.volumes(dd_, pr["eid"], pr["pid"]) == pr["volumes"]
              and lim.get("min") == pr["table_min"], (EPF.volumes(dd_, pr["eid"], pr["pid"]), lim))
    # the global standards, rules, phrase rules and library
    d = PRL.load(cfg)
    st = ex["standards"]
    check(f"{ver}: the global standards read back with their values", any(e.get("name") == st["effort_type"] for e in d.get("effort_types", []))
          and d["company"].get("style_roles", {}).get("a_number") == st["a_number"]
          and d["company"].get("style_defs", {}).get(st["used_on"][0], {}).get("used_on") == st["used_on"][1]
          and d["company"]["variables"].get("body_font") == st["body_font"])
    if ex.get("hf_cells"):                                # 3.42 on: a footer built as a table
        ft = ((d["company"].get("hf_layouts") or {}).get(ex["hf_cells"]["part"]) or {}).get("footer") or {}
        cells = (ft.get("table") or {}).get("cells") or []
        check(f"{ver}: the footer built as a table reads back, the team's line in it", len(cells) == 3
              and any(ln.get("text") == ex["hf_cells"]["line2"] for c in cells for ln in c.get("lines") or []), ft)
    if ex.get("team_line"):                               # 3.48 on: Rule 7's team line from the variables; a Quick Part kept as built
        import hfbuild as HB
        qp = next((e for e in (d["company"].get("quick_parts") or {}).get("entries") or [] if e.get("name") == ex["team_line"]["qp"]), {})
        check(f"{ver}: the team's line and a Quick Part kept as built read back", HB.team_line(d["company"]) == ex["team_line"]["words"]
              and qp.get("as_built") is True, qp)
    if ex.get("library"):                                 # 3.49 on: library items with status and effort types; the standards converted
        import templatelib as TL, libcats as LC, libconvert as CV
        lib = TL.Library(cfg)
        it = next((i for i in lib.items if i["name"] == ex["library"]["draft"]), None)
        check(f"{ver}: a Draft library item for one effort type reads back, and the standards were converted", it is not None
              and LC.status(it) == "draft" and LC.effort_types(it) == [ex["library"]["effort_type"]] and CV.done(cfg)
              and LC.place(lib, it) == ("formatting", "para_styles"), it)
        if ex["library"].get("quickpart"):              # 3.50 on: a Quick Part in its category with its pages
            qx = ex["library"]["quickpart"]
            q = next((i for i in lib.items if i["name"] == qx["name"]), None)
            check(f"{ver}: a library Quick Part reads back in its category with its pages", q is not None
                  and LC.place(lib, q) == ("quickparts", qx["category"]) and lib.pages_of(q["id"]) == qx["pages"], q)
    if ex.get("sections"):                                # 3.45 on: a section's contents and its page setup
        sx = ex["sections"]
        items = ((d["company"].get("section_contents") or {}).get(sx["part"])) or []
        part = next((p for p in d["company"]["pagination"]["parts"] if p.get("key") == sx["setup_part"]), {})
        check(f"{ver}: a section's contents and its page setup read back", any(r.get("title") == sx["title"] for r in items)
              and part.get("setup") == sx["setup"], (items, part.get("setup")))
    rs = RB.rules(cfg)
    check(f"{ver}: the rules read back (an own rule, a rule off)", any(r["text"] == ex["rules"]["own"] and r["own"] for r in rs)
          and not RB.get(cfg, ex["rules"]["off"])["on"])
    check(f"{ver}: the phrase rule reads back", any(r["phrase"] == ex["phrase"] for r in SR.team_rules(cfg)))
    check(f"{ver}: the saved matrix view reads back", any(ex["matrix_view"] in name for _i, name in MD.views(cfg)),
          MD.views(cfg))
    std = PRL.for_effort(cfg, ws)
    check(f"{ver}: the effort's standard is built from all of it", std["response_type"] == want["response_type"]
          and set(want["rules_off"]) | {ex["rules"]["off"]} <= set(std["_rules_off"])
          and std["variables"].get("body_size") == want["body_size"] and std["variables"].get("body_font") == st["body_font"],
          (std["response_type"], std["_rules_off"], std["variables"].get("body_size")))
    # the Stationkeeper Data file
    m2, d2 = TD.read(os.path.join(work, ex["data_file"]))
    fresh = os.path.join(tmp, ver + "-fresh", "config"); os.makedirs(fresh)
    rep = dict(TD.install(fresh, m2, d2))
    check(f"{ver}: the Stationkeeper Data file reads and installs its standards", "standards" in rep, rep)
for ver in sets:
    a = os.path.join(GOLD, ver)
    check(f"{ver}: the golden files were not changed by the test", json.load(open(os.path.join(a, "expect.json"), encoding="utf-8"))["version"] == ver)

n = sum(checks)
print(f"GOLDEN {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
