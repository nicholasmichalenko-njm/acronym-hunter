"""3.49.0 library foundation: the library keeps changes all or nothing; an import that fails part way keeps nothing
(the half-saved import that made items look already kept); another window's saves are read; each item lands in its
library and category; Add, new version, Keep both, Replace and Undo; the standards become items once (tagged by
effort type, profiles as labelled versions) and rebuild the global standard; a style's values say where they come
from. Fictional content."""
import json, os, shutil, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ.setdefault("AH_TEST", "1")
import templatelib as TL, libcats as LC, libimport as LI, libconvert as CV, libstyle as LS, prodrules as PRL, prodtemplate as PT

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


def files(lib):
    d = os.path.join(lib.root, "items")
    return sorted(os.listdir(d)) if os.path.isdir(d) else []


# ---- all or nothing
cfg = tempfile.mkdtemp()
lib = TL.Library(cfg)
lib.add("style", "Kestrel Body", {"type": "paragraph", "font": "Arial", "size": 11})
index_before = open(os.path.join(lib.root, "index.json"), encoding="utf-8").read()
files_before = files(lib)
try:
    with lib.transaction():
        lib.add("style", "Kestrel Note", {"type": "paragraph", "size": 9})
        lib.update(lib.items[0]["id"], {"type": "paragraph", "font": "Arial", "size": 14})
        raise RuntimeError("stop")
except RuntimeError:
    pass
check("a transaction that fails keeps nothing: index, items and value files as they were",
      open(os.path.join(lib.root, "index.json"), encoding="utf-8").read() == index_before and files(lib) == files_before
      and len(lib.items) == 1 and lib.values(lib.items[0])["size"] == 11)
with lib.transaction():
    lib.add("style", "Kestrel Note", {"type": "paragraph", "size": 9})
    check("inside a transaction the index is not written yet", open(os.path.join(lib.root, "index.json"), encoding="utf-8").read() == index_before)
check("a transaction that finishes writes once", len(TL.Library(cfg).items) == 2)

# ---- another window's saves
other = TL.Library(cfg)
lib.add("page_setup", "Kestrel portrait", {"w": 8.5, "h": 11, "top": 1})
check("a library read before another window kept items sees them after fresh()", len(other.items) == 2 and other.fresh() and len(other.items) == 3)
check("fresh() does nothing when nothing changed", not other.fresh())

# ---- the same values under another name are another style
st, _hit = lib.match("style", "Kestrel Caption", {"type": "paragraph", "size": 9})
check("a style with the same values under another name is new, not the same", st == "new")
st, _hit = lib.match("variables", "Other fonts", {"body_font": "Arial"})
check("kinds that are not named by what they are for still match by values", st in ("new", "same"))

# ---- where items land
lib.add("style", "Kestrel Strong", {"type": "character", "bold": True})
lib.add("style", "Kestrel Grid", {"type": "table"})
lib.add("hf", "body", {"header": {"left": "{volume_name}"}, "footer": {}})
lib.add("quickpart", "Kestrel Callout", {"entry": "Kestrel Callout", "category": "05 Callouts", "source": "x.dotx"})
lib.add("matrix_view", "Kestrel view", {"cols": []})
pl = {i["name"]: LC.place(lib, i) for i in lib.items}
check("each item lands in its library and category", pl["Kestrel Body"] == ("formatting", "para_styles")
      and pl["Kestrel Strong"] == ("formatting", "char_styles") and pl["Kestrel Grid"] == ("formatting", "table_styles")
      and pl["Kestrel portrait"] == ("formatting", "page_setup") and pl["body"] == ("layout", "hf")
      and pl["Kestrel Callout"] == ("quickparts", "05 Callouts") and pl["Kestrel view"] == (None, None), pl)
check("Quick Parts list their own categories", LC.categories(lib, "quickparts") == [("05 Callouts", "05 Callouts")])
check("items kept before 3.49.0 read as Approved and not tagged", LC.status(lib.items[0]) == "approved" and LC.effort_types(lib.items[0]) == [])
ids = [i["id"] for i in lib.items if i["name"].startswith("Kestrel B")]
LC.set_effort_types(lib, ids, ["rfi"])
check("tagged for an effort type: shown for it, not for another", LC.items_in(lib, "formatting", "para_styles", "rfi")
      and not any(i["name"] == "Kestrel Body" for i in LC.items_in(lib, "formatting", "para_styles", "rfp")))
LC.set_effort_types(lib, ids, [LC.ALL, "rfi"])
check("Every effort type is one tag", LC.effort_types(lib.get(ids[0])) == [LC.ALL] and LC.fits(lib.get(ids[0]), "white_paper"))
LC.set_status(lib, ids, "retired")
check("status set and filtered", LC.status(lib.get(ids[0])) == "retired" and not LC.items_in(lib, "formatting", "para_styles", None, "approved")
      or all(i["id"] not in ids for i in LC.items_in(lib, "formatting", "para_styles", None, "approved")))

# ---- the import: staged, all or nothing
std = PRL.for_effort(tempfile.mkdtemp()); std["variables"]["marking"] = "Kestrel restriction"
SRC = os.path.join(tempfile.mkdtemp(), "Kestrel Volume.dotx")
shutil.copyfile(PT.make(std, tempfile.mkdtemp(), "").copy, SRC)
cfg2 = tempfile.mkdtemp()
lib2 = TL.Library(cfg2)
items, err = LI.stage(SRC, std, lib2)
check("stage reads the file and changes nothing in the library", items and not err and not lib2.items
      and not os.path.isfile(os.path.join(lib2.root, "index.json")))
check("each staged item knows its library, category, state and action", all(it["library"] in (None, "formatting", "quickparts", "layout")
      and it["state"] == "new" and it["take"] and it["action"] == "add" for it in items))
real_new = lib2._new
calls = {"n": 0}


def failing(*a, **k):
    calls["n"] += 1
    if calls["n"] == 4:
        raise OSError("disk full")
    return real_new(*a, **k)


lib2._new = failing
try:
    LI.commit(lib2, SRC, items, ["rfp"])
    failed = None
except LI.ImportFailed as e:
    failed = e
lib2._new = real_new
check("an import that fails part way keeps nothing and says the step it was in", failed is not None and failed.step.startswith("keeping")
      and isinstance(failed.cause, OSError) and not TL.Library(cfg2).items and not files(lib2), getattr(failed, "step", None))
LI.restate(lib2, items)
check("after a failed import nothing reads as already in the library", all(it["state"] == "new" for it in items))
rep = LI.commit(lib2, SRC, items, ["rfp"], {"use": ["RFP"]})
fresh = TL.Library(cfg2)
check("the import keeps every ticked item at once, Draft, tagged with the effort types", len(rep["added"]) == len([i for i in items if i["take"]])
      and len(fresh.items) == len(rep["added"]) and all(LC.status(i) == "draft" and LC.effort_types(i) == ["rfp"] for i in fresh.items))
LI.restate(lib2, items)
check("imported again: everything is Same, unticked", all(it["state"] == "same" and not it["take"] and it["action"] == "skip" for it in items))

sty = next(it for it in items if it["kind"] == "style")
hit = fresh.get(sty["match"])
v = dict(fresh.values(hit)); v["size"] = 27
fresh.update(hit["id"], v)
LI.restate(lib2, items)
check("a changed library item makes the file's one Differ, as a new version by default", sty["state"] == "variant" and sty["action"] == "version"
      and "27" in sty["differs"], sty.get("differs"))
for it in items:
    it["take"] = it is sty
sty["action"] = "version"
r2 = LI.commit(lib2, SRC, items)
check("Add as a new version: the next version of that item, Draft", len(r2["versions"]) == 1
      and TL.Library(cfg2).get(r2["versions"][0])["family"] == hit["family"])
LI.restate(lib2, items)
sty["take"] = True; sty["action"] = "both"
r3 = LI.commit(lib2, SRC, items)
check("Keep both: kept under a new name", r3["renamed"] and "Kestrel Volume" in r3["renamed"][0][1])
lib3 = TL.Library(cfg2)
newest = r2["versions"][0]                               # the family's newest version is what the file is compared with
v = dict(lib3.values(lib3.get(newest))); v["size"] = 33; lib3.update(newest, v)
LI.restate(lib2, items)
sty["take"] = True; sty["action"] = "replace"
r4 = LI.commit(lib2, SRC, items)
lib3.load()
check("Replace: the library item takes the file's values", r4["replaced"] == [newest] and lib3.values(lib3.get(newest))["size"] != 33, r4)
n = LI.undo(lib2, r4["id"])
lib3.load()
check("Undo puts the replaced values back", n == 1 and lib3.values(lib3.get(newest))["size"] == 33)
n = LI.undo(lib2, rep["id"])
lib3.load()
check("Undo of the first import takes its items out", n == len(rep["added"]) and all(i["id"] not in rep["added"] for i in lib3.items))
check("the imports that can be taken back are listed", [r[0] for r in LI.imports(lib2)] and rep["id"] not in [r[0] for r in LI.imports(lib2)])
check("Use here goes into a copy; the standard being edited is left alone", True if not items else
      (lambda w: (lambda c, s: c is not w and "page_setups" in c)(*LI.apply_here(cfg2, [dict(items[0], take=True)], w, SRC)))({"page_setups": {}}))

# ---- the old Collect is all or nothing too
cards, _e = TL.collect(SRC, std, TL.Library(tempfile.mkdtemp()))
cfg4 = tempfile.mkdtemp(); lib4 = TL.Library(cfg4)
real = lib4.add
k = {"n": 0}
def bad_add(*a, **kw):
    k["n"] += 1
    if k["n"] == 3:
        raise OSError("disk full")
    return real(*a, **kw)
lib4.add = bad_add
try:
    TL.save_collected(lib4, SRC, cards)
except OSError:
    pass
check("Collect from 3.22.0 keeps nothing when it fails part way", not TL.Library(cfg4).items)

# ---- converting the standards
cfg5 = tempfile.mkdtemp()
d = PRL.load(cfg5)
d["company"]["style_defs"]["Body Text"] = {"type": "paragraph", "font": "Arial", "size": 11}
d["company"]["style_defs"]["Heading 1"] = {"type": "paragraph", "font": "Arial", "size": 14, "bold": True, "based_on": "Body Text"}
d["types"][0]["style_defs"] = {"Body Text": {"size": 12}}
e = PRL.add_effort_type(d, "Kestrel page-limited")
e["variables"] = {"body_size": 10}
PRL.save(cfg5, d)
check("not converted yet", not CV.done(cfg5))
r = CV.ensure(cfg5)
lib5 = TL.Library(cfg5)
check("the standards become items once", r and r["new"] > 5 and CV.done(cfg5) and CV.ensure(cfg5) is None)
g = [i for i in lib5.items if i.get("source") == "Global standard"]
check("the global standard's items are for every effort type, Approved", g and all(LC.effort_types(i) == [LC.ALL] and LC.status(i) == "approved" for i in g))
bt = [i for i in lib5.items if i["kind"] == "style" and lib5.base_of(i) == "Body Text"]
check("a profile's change is a new version labelled with the profile", len(bt) == 2 and any(i.get("label") == d["types"][0]["name"]
      and lib5.values(i)["size"] == 12 and lib5.values(i)["font"] == "Arial" for i in bt), [(i.get("label"), lib5.values(i)) for i in bt])
va = [i for i in lib5.items if i["kind"] == "variables" and i.get("label") == "Kestrel page-limited"]
check("an effort type's change is tagged with that effort type", va and LC.effort_types(va[0]) == [e["id"]] and lib5.values(va[0])["body_size"] == 10)
check("the global standard rebuilds from its items", CV.rebuild_check(cfg5) == [], CV.rebuild_check(cfg5))
r = CV.convert(cfg5)
check("converting again adds nothing new", r["new"] == 0 and r["version"] == 0)
hf = [i for i in lib5.items if i["kind"] == "hf"]
check("each part's header and footer is its own item, even when two are alike", {lib5.base_of(i) for i in hf} >= {"front", "body", "appendix"})

# ---- a style's values and where they come from
h1 = next(i for i in lib5.items if i["kind"] == "style" and lib5.base_of(i) == "Heading 1")
v = lib5.values(h1)
o = LS.origins(lib5, h1, v)
check("a value equal to the base style's comes from it", o["font"][0] == "from Body Text", o["font"])
check("a value of its own is set here", o["size"][0] == "here" and o["bold"][0] == "here")
check("the chain of base styles", [n for n, _b, _v in LS.chain(lib5, h1, v)] == ["Body Text"])
v2 = LS.reset(lib5, h1, v, "size")
check("Reset puts the base style's value back", v2["size"] == 11 and LS.origins(lib5, h1, v2)["size"][0] == "from Body Text")
tree = {"levels": [{"style": "Heading 1", "text": "%1.", "on": True}], "xml": "<w:theme/>" * 50, "n": 3}
rows = LS.rows(tree)
check("any item as a tree of values, Word XML kept whole", any(p == ("levels", 0, "style") for p, *_r in rows)
      and any(p == ("xml",) and not ed for p, _w, _s, ed in rows))
t2 = LS.set_path(tree, ("levels", 0, "on"), "no")
t3 = LS.set_path(tree, ("n",), "5")
check("a value typed keeps its type", t2["levels"][0]["on"] is False and t3["n"] == 5 and tree["n"] == 3)
try:
    LS.set_path(tree, ("levels", 0, "on"), "maybe"); bad = False
except ValueError:
    bad = True
check("a value that does not fit is refused", bad)

n = sum(checks)
print(f"LIBRARY 3.49 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
