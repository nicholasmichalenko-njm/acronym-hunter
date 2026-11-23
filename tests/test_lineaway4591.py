"""4.59.1 (G14 of claude/stationkeeper-g7-first-run-2026-11-22.md; Nicholas 2026-11-23 07:44: "The app should be taking
the line away, the same as the standard and the macro"): a line a table type's look takes away is drawn by no tool.
Before, the app's own resolution (rules.deep_merge) took a taken-away line for "not set" and drew the line below it.
Fictional values only (Heron, Kestrel)."""
import copy, os, sys, tempfile
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import prodengine.pe.rules as R
import prodrules as PRL
import standardsbook as SB

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


EDGES = ("top", "bottom", "left", "right", "inside_v")
std = R.resolve(R.COMPANY)
fig = {role: R.row_look(std, role, "fig")["edges"] for role in ("caption", "body")}
check("the Figure table's caption and body draw no line, as its standard says", all(fig[r][e] is None for r in fig for e in EDGES), fig)
check("the kind's own look still has its lines (the standard table)", R.row_look(std, "body", "std")["edges"]["inside_v"] is not None
      and R.row_look(std, "caption", "std")["edges"]["bottom"] is not None)
check("a type that changes only the fill keeps the kind's lines", R.row_look(std, "header", "kp")["edges"] == std["row_types"]["header"]["edges"])

# an effort that takes away one line of a Global type's look, and sets nothing else
effort = {"table_types": {"std": {"override": {"header": {"edges": {"bottom": None}}}}}, "row_types": {"header": {"fill": None}}}
eff = R.resolve(R.COMPANY, None, effort)
h = R.row_look(eff, "header", "std")["edges"]
check("an effort's line taken away is taken away", h["bottom"] is None, h)
check("... and the other lines of that look are kept", all(h[e] == std["row_types"]["header"]["edges"][e] for e in EDGES if e != "bottom"), h)
check("a None outside a look's lines still means not set: the header keeps its fill", eff["row_types"]["header"].get("fill")
      == std["row_types"]["header"].get("fill") and std["row_types"]["header"].get("fill") is not None)
check("an effort that does not mention a line keeps it", R.row_look(R.resolve(R.COMPANY, None, {"table_types": {"std": {"override": {"header": {"fill": "112233"}}}}}),
                                                                    "header", "std")["edges"] == std["row_types"]["header"]["edges"])

# the overnight case: an effort's own type whose header takes away its bottom line, through the workbook both tools read
lay = {"table_types": {"heron": {"name": "heron", "roles": ["header", "body"],
                                 "override": {"header": {"fill": "C00000", "edges": {"bottom": None}}}}}}
tmp = tempfile.mkdtemp()
ep = os.path.join(tmp, "Heron Effort Standards.xlsx")
SB.write(ep, lay, None, volumes=[])
parts = SB.split_volumes(SB.read(ep), [])
got = SB.apply({}, None, parts[""])["company"]
both = R.resolve(R.COMPANY, None, got)
hh = R.row_look(both, "header", "heron")
check("an effort's own type read from its workbook: its header's bottom line is taken away, its fill kept",
      hh["edges"]["bottom"] is None and hh["fill"] == "C00000", (hh["edges"], hh.get("fill")))
check("... and the header's other lines are the kind's own", hh["edges"]["top"] == std["row_types"]["header"]["edges"]["top"])

# the Global workbook round trip keeps the Figure table's lines away
gp = os.path.join(tmp, "Global Standards.xlsx")
SB.write(gp, copy.deepcopy(PRL.load(tempfile.mkdtemp())["company"]), [])
g = SB.apply(PRL.load(tempfile.mkdtemp())["company"], [], SB.read(gp))["company"]
gf = R.row_look(R.resolve(g), "body", "fig")["edges"]
check("the Global Standards read back from its workbook: the Figure table's body still draws no line", all(gf[e] is None for e in EDGES), gf)

print(f"LINEAWAY 4591 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
