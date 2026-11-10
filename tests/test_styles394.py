"""3.94.0: the Styles library's rules (stylelib): styles read from a Word file with Word's own definition kept, each
against the library (New, Already have it, Different from yours), brought in as new styles or new versions; style
sets (one version of a style each, a color each, a newer version noticed and moved to only when asked); a simple
style made here with its definition written from its look; a changed look as a new version; the row's words.
Fictional files (the Kestrel set)."""
import os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import stylelib as SL
import templatelib as TL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
lib = TL.Library(tmp)
DOC = os.path.join(os.path.dirname(HERE), "test_samples", "Kestrel_Technical_Volume.docx")
st = SL.read_styles(DOC)
names = [s["name"] for s in st]
h1 = next((s for s in st if s["name"] == "Heading 1"), None)
check("a file's styles are read with Word's own definition", h1 is not None and h1["xml"].startswith("<w:style")
      and "Heading" in h1["xml"] and h1["values"].get("size"), names[:8])
ag = SL.against(lib, st)
check("against an empty library every style is New, ticked", all(x["words"] == "New" and x["keep"] for x in ag))
for x in ag:
    x["keep"] = x["name"] in ("Heading 1", "Normal")
rfp = SL.new_set(lib, "RFP volume")
check("a new set has a color of its own", rfp and rfp["color"] == SL.SET_COLORS[0] and rfp["kind"] == "style")
check("a set name is used once", SL.new_set(lib, "rfp volume") is None)
c = SL.bring_in(lib, ag, DOC, set_of={"Heading 1": rfp["id"]})
check("only the ticked styles come in", c["new"] == 2 and len(SL.styles(lib)) == 2, c)
h1v1 = next(i for i in lib.items if i["name"] == "Heading 1")
check("Word's definition is kept beside the values, out of the comparison", (lib.values(h1v1) or {}).get("_xml", "").startswith("<w:style")
      and lib.values(h1v1).get("_from") == "Kestrel_Technical_Volume.docx")
check("it went into its set", SL.sets_of(lib, h1v1["id"]) and SL.sets_of(lib, h1v1["id"])[0]["id"] == rfp["id"])
ag2 = SL.against(lib, st)
check("met again: Already have it, not ticked", next(x for x in ag2 if x["name"] == "Heading 1")["words"] == "Already have it"
      and not next(x for x in ag2 if x["name"] == "Heading 1")["keep"])
other = [dict(h1, values=dict(h1["values"], size=16.0))]
ag3 = SL.against(lib, other)
check("other values under the same name: Different from yours", ag3[0]["state"] == "variant" and ag3[0]["mine"]["id"] == h1v1["id"])
SL.bring_in(lib, ag3, DOC)
h1v2 = lib.latest(h1v1["id"])
check("... it comes in as version 2; version 1 stays", h1v2["version"] == 2 and lib.get(h1v1["id"]) is not None
      and lib.values(h1v2)["size"] == 16.0)
nv = SL.newer(lib, rfp["id"])
check("the set still uses version 1 and says a newer one is there", rfp["items"] == [h1v1["id"], ] and nv and nv[0][1]["id"] == h1v2["id"])
SL.move(lib, rfp["id"], h1v1["id"], h1v2["id"])
check("Move this set to v2", rfp["items"] == [h1v2["id"]] and not SL.newer(lib, rfp["id"]))
gone = SL.add_to_set(lib, rfp["id"], [h1v1["id"]])
check("a set holds one version of a style: adding v1 takes v2 out", rfp["items"] == [h1v1["id"]] and gone == [h1v2["id"]])
pl = SL.new_set(lib, "Page-limited RFP")
SL.add_to_set(lib, pl["id"], [h1v2["id"]])
check("one style, two sets, different versions", [k["name"] for k in SL.sets_of(lib, h1v2["id"])] == ["Page-limited RFP"]
      and pl["color"] != rfp["color"])
check("a set's rows are its versions", [i["id"] for i in SL.styles(lib, pl["id"])] == [h1v2["id"]])
# a style made here
it, s1 = SL.new_style(lib, "SK Compliance Char", "character", {"font": "Calibri", "size": 11, "color": "#C00000", "bold": True,
                                                              "hidden": True}, marks="Compliance language")
v = lib.values(it)
x = v.get("_xml", "")
check("a style made here: its definition written from its look", s1 == "new" and 'w:type="character"' in x and "<w:b/>" in x
      and "<w:vanish/>" in x and 'w:val="C00000"' in x and 'w:val="22"' in x and v.get("_made") == "app", x)
check("... and the row says so", SL.version_words(lib, it) == "v1 · made in the app")
d = SL.describe(v)
check("the row's words", d["paragraph"] == "Character style" and d["characters"] == "Bold · red · hidden"
      and d["font"] == "Calibri 11" and d["other"] == "Marks Compliance language", d)
_i, s2 = SL.new_style(lib, "SK Compliance Char", "character", {"font": "Calibri", "size": 11, "color": "C00000", "bold": True,
                                                               "hidden": True}, marks="Compliance language")
check("the same look again is the same style", s2 == "same")
it2, s3 = SL.change_style(lib, it["id"], {"font": "Calibri", "size": 11, "color": "8B0000", "bold": True, "hidden": True})
check("a changed look is a new version; the first stays", s3 == "version" and it2["version"] == 2
      and lib.values(it2)["color"] == "8B0000" and lib.values(lib.get(it["id"]))["color"] == "C00000"
      and 'w:val="8B0000"' in lib.values(it2)["_xml"])
check("a paragraph style made here rests on Normal", 'w:basedOn w:val="Normal"' in SL.style_xml("SK Note", SL.look_values("paragraph", {"size": 9})))
dp = SL.describe(lib.values(h1v1))
check("a paragraph style's words", "before" in dp["paragraph"] and dp["font"].startswith("Calibri"), dp)
check("rename a set; a name in use is refused", SL.rename_set(lib, pl["id"], name="Page-limited") and not SL.rename_set(lib, pl["id"], name="RFP volume"))
check("find a style by name", [i["name"] for i in SL.styles(lib, words="compliance")][:1] == ["SK Compliance Char v2"] or
      any("Compliance" in i["name"] for i in SL.styles(lib, words="compliance")))
lib2 = TL.Library(tmp)
check("sets and versions are kept on this PC", len(SL.sets(lib2)) == 2 and SL.get_set(lib2, rfp["id"])["color"] == rfp["color"])
shutil.rmtree(tmp, ignore_errors=True)
print(f"{sum(checks)}/{len(checks)} passed")
sys.exit(0 if all(checks) else 1)
