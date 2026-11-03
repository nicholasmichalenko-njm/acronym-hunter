"""3.33.0 versions, template profiles and the content map, without the window: library families with versions (older
variants folded in, names kept), save as a new version, the same values met again, labels, compare; a profile's parts
filled from pinned versions, a newer version waiting, Use it, own values, save as a new version from the profile; the
content map (defaults, the profile's map, this effort's change, an older matrix choice, a capture of its own); the setup
written with captures in their style, hidden, or left out."""
import copy, json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
import compliance as C, outline_ops as O, setupdoc as SD, setuptemplate as ST, templatelib as TL, templateprofile as TP, prodrules as PRL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
# ---------------------------------------------------------------- an older library: a style and its variant, folded in
root = TL.folder(cfg); os.makedirs(os.path.join(root, "items"))
old = [{"id": "a1", "kind": "style", "name": "Heading 1", "base_name": "Heading 1", "hash": "h1", "at": "2026-10-01T10:00"},
       {"id": "a2", "kind": "style", "name": "Heading 1 (2)", "base_name": "Heading 1", "hash": "h2", "variant_of": "a1", "at": "2026-10-02T10:00"},
       {"id": "b1", "kind": "variables", "name": "Base", "hash": "h3", "at": "2026-10-01T10:00"}]
for i, v in (("a1", {"size": 14}), ("a2", {"size": 16}), ("b1", {"body_font": "Arial", "body_size": 11})):
    json.dump(v, open(os.path.join(root, "items", i + ".json"), "w"))
json.dump({"format": 1, "items": old, "kits": []}, open(os.path.join(root, "index.json"), "w"))
lib = TL.Library(cfg)
a1, a2 = lib.get("a1"), lib.get("a2")
check("older variants are folded into one family, numbered in the order kept, names kept", a1["family"] == a2["family"] == "a1"
      and (a1["version"], a2["version"]) == (1, 2) and a2["name"] == "Heading 1 (2)")
check("listed as the family and its version", lib.shown_name(a2) == "Heading 1 v2" and [x["id"] for x in lib.family("a1")] == ["a2", "a1"])
check("kept folded: read again, the same", TL.Library(cfg).get("a2")["version"] == 2)
it, st = lib.add("style", "Heading 1", {"size": 18})
check("the same name with other values: the family's next version", st == "variant" and it["family"] == "a1" and it["version"] == 3
      and it["name"] == "Heading 1 v3")
v4, st4 = lib.save_version("a1", {"size": 20}, label="Space Force 2026", note="bigger")
check("save as a new version, with a label and a note", st4 == "version" and v4["version"] == 4 and lib.shown_name(v4) == "Heading 1 v4: Space Force 2026"
      and v4["note"] == "bigger")
same, sts = lib.save_version("a1", {"size": 18})
check("the same values as a version kept: that version, nothing new", sts == "same" and same["id"] == it["id"] and len(lib.family("a1")) == 4)
check("a label set later", lib.set_label("a2", "11 pt body") and lib.get("a2")["label"] == "11 pt body")
check("compare: every value that differs", lib.compare("a1", v4["id"]) == [("size", 14, 20)])
# ---------------------------------------------------------------- a profile's parts
std = copy.deepcopy(PRL.COMPANY)
names = [s[0] for s in TP.slots(std)]
check("the parts in the order a response runs, then the whole document's", names[:6] == ["cover", "hf:front", "toc", "hf:body", "hf:appendix", "backer"]
      and "variables" in names and "pagination" in names)
check("nothing pinned: the profile's own values", TP.state(std, lib, "variables")["item"] is None and TP.current_values(std, "variables"))
said = TP.pick(std, lib, "variables", "b1", cfg)
check("a part filled from a library version and pinned", std["variables"]["body_font"] == "Arial" and TP.pins(std)["variables"] == {"id": "b1", "family": "b1", "version": 1}, said)
b2, _ = lib.save_version("b1", {"body_font": "Garamond", "body_size": 12}, label="12 pt")
stt = TP.state(std, lib, "variables")
check("a newer version waits: the profile stays on its version", stt["item"]["id"] == "b1" and stt["newer"]["id"] == b2["id"] and std["variables"]["body_font"] == "Arial")
TP.pick(std, lib, "variables", stt["newer"]["id"], cfg)
check("Use v2: the newer version, pinned", std["variables"]["body_font"] == "Garamond" and TP.pins(std)["variables"]["version"] == 2
      and TP.state(std, lib, "variables")["newer"] is None)
std["pagination"]["parts"][0]["fmt"] = "upperRoman"
item, st = TP.save_version(std, lib, "pagination", name="Space Force pagination", label="roman front")
check("save as a new version from the profile: a new family, pinned", st == "new" and item["kind"] == "pagination" and item["label"] == "roman front"
      and TP.pins(std)["pagination"]["id"] == item["id"] and lib.values(item)["parts"][0]["fmt"] == "upperRoman")
std["pagination"]["parts"][0]["fmt"] = "lowerRoman"
item2, st2 = TP.save_version(std, lib, "pagination")
check("... and again: the next version of the pinned family", st2 == "version" and item2["family"] == item["family"] and item2["version"] == 2)
work2 = copy.deepcopy(PRL.COMPANY)
TP.pick(work2, lib, "pagination", item["id"], cfg)
check("a pagination scheme from the library", work2["pagination"]["parts"][0]["fmt"] == "upperRoman")
check("own values: the pin comes off, the values stay", TP.unpin(work2, "pagination") and "pagination" not in TP.pins(work2)
      and work2["pagination"]["parts"][0]["fmt"] == "upperRoman")
check("the list numbering's lists are parts too", any(s.startswith("list:") for s in [x[0] for x in TP.slots({"list_numbering": {"lists": [{"name": "Bullets"}]}})]))
pdir = os.path.join(tmp, "parts"); os.makedirs(pdir)
open(os.path.join(pdir, "cover1.docx"), "wb").write(b"PK cover bytes")
std["page_parts"] = {"cover": "cover1.docx"}
cv, stc = TP.save_version(std, lib, "cover", name="Volume cover", parts_dir=pdir)
check("the profile's cover kept as a library cover", stc == "new" and cv["kind"] == "cover" and os.path.isfile(lib.source_path(lib.values(cv)["file"])))
# ---------------------------------------------------------------- the content map
M = C.Matrix(os.path.join(tmp, "m.xlsx"), "m")
o = ST.options(M)
check("defaults: every kind hidden and in the file, captures in SK Capture", o["capture"] == {"style": "SK Capture", "hidden": True, "include": True}
      and o["rfp"]["style"] == "SK RFP Requirement" and all(v["hidden"] and v["include"] for v in o.values()))
pstd = {"content_map": {"pm": {"style": "PM Note", "hidden": False}, "cap:hot": {"style": "Hot Button Note", "hidden": False},
                        "capture": {"include": False}}}
o = ST.options(M, pstd)
check("the profile's map over the defaults; a capture of its own", o["pm"] == {"style": "PM Note", "hidden": False, "include": True}
      and o["cap:hot"]["style"] == "Hot Button Note" and o["cap:hot"]["include"] is False and not o["capture"]["include"], o["cap:hot"])
SD.setup_of(M)["on_template"] = {"pm": {"style": "Older Choice", "hidden": True}}
check("an older choice kept with the matrix still counts", ST.options(M, pstd)["pm"]["style"] == "Older Choice")


class WS:
    def __init__(self):
        self.d = {"prod_std": {"over": {"variables": {"body_size": 12}}}}

    def get(self, k, default=None):
        return copy.deepcopy(self.d.get(k, default))

    def set(self, k, v):
        self.d[k] = v


ws = WS()
ST.set_options(M, dict(ST.options(M, pstd), rfp={"style": "RFP Words", "hidden": True, "include": True}), ws)
over = ws.d["prod_std"]["over"]
check("Make templates' choices are this effort's change to the profile's map", over["content_map"]["rfp"]["style"] == "RFP Words"
      and over["variables"] == {"body_size": 12} and "on_template" not in SD.setup_of(M))
check("left out: the kinds not in the file", ST.skip_kinds(ST.options(M, pstd)) >= {"capture", "cap:hot"})
# ---------------------------------------------------------------- the setup with captures
vol = O.add_volume(M, "Technical")
t1 = O.add(M, "Approach", parent=vol)
SD.set_volumes(M, "several", "", [vol])
bins = {"excerpts": [{"id": "x1", "bin": "hot", "text": "Speed matters", "sections": [t1], "parts": []},
                     {"id": "x2", "bin": "graphic", "text": "Ops diagram", "sections": [t1], "parts": []}],
        "bins": [], "topics": [{"name": "Schedule", "sections": [t1]}]}
entries = [o_ for o_ in M.outline if C.outline_label(o_) != vol]
P, inh = SD.placed_in(M), SD.inherited_sections(M)
opts = ST.options(M, {"content_map": {"cap:hot": {"style": "Hot Button Note", "hidden": False}}})
d = SD._doc_for(M, vol, entries, P, inh, "now", bins=bins, styles=ST.style_ids(opts), extras={"skip_kinds": ST.skip_kinds(opts)})
xml = "".join(d.body)
check("a capture with its own row takes its style; another takes the Captures row; topics their own",
      'w:val="HotButtonNote"' in xml and 'w:val="SKCapture"' in xml and 'w:val="SKTopic"' in xml)
opts = ST.options(M, {"content_map": {"capture": {"include": False}}})
d = SD._doc_for(M, vol, entries, P, inh, "now", bins=bins, styles=ST.style_ids(opts), extras={"skip_kinds": ST.skip_kinds(opts)})
xml = "".join(d.body)
check("captures left out of the file when the map says so; the topic stays", "Speed matters" not in xml and "Ops diagram" not in xml and "Schedule" in xml)
import zipfile
from lxml import etree
sroot = etree.fromstring(zipfile.ZipFile(os.path.join(HERE, "pefix", "data", "PE_Master_Effort_Template.dotx")).read("word/styles.xml"))
ids = ST.ensure_styles(sroot, ST.options(M, {"content_map": {"cap:hot": {"style": "Hot Button Note", "hidden": False}}}))
names_ = {s.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}name").get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val")
          for s in sroot.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}style")
          if s.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}name") is not None}
check("the template gets each mapped style, a capture's own too", {"SK Capture", "SK Topic", "SK Customer Objective", "Hot Button Note"} <= names_
      and "cap:hot" in ids)
n = sum(checks)
print(f"TEMPLATE PROFILE {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
