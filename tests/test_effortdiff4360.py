"""4.36.0 (ST8, ST11, ST20 of 2026-11-14): where an effort's standards differ from the Global Standards, row by row,
with the effort's own value in use and the Global value one choice away, made and unmade without losing either.
A fictional PC and effort."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import effortdiff as ED, effortset as ES, prodrules as PRL, stylehistory as SH, stylelib as SL, templatelib as TL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "Stationkeeper Data", "config"); os.makedirs(cfg)
root = os.path.join(tmp, "Osprey", "work")


def var(k):
    return PRL.load(cfg)["company"]["variables"].get(k)


def set_var(k, v):
    d = PRL.load(cfg); d["company"]["variables"][k] = v; PRL.save(cfg, d)


set_var("body_font", "Arial"); set_var("body_size", 11)
lib = TL.Library(cfg)
body, _ = lib.add("style", "Osprey Body", {"type": "paragraph", "size": 11.0})
head, _ = lib.add("style", "Osprey Heading 1", {"type": "paragraph", "size": 16.0, "bold": True})
rfp = SL.new_set(lib, "RFP"); SL.add_to_set(lib, rfp["id"], [body["id"], head["id"]])

ES.enter(cfg, root)
check("an effort just started differs nowhere", ED.rows(cfg, root) == [], ED.rows(cfg, root))
set_var("body_size", 10)                                         # the effort's own change
elib = TL.Library(cfg)
e2, _st, _m = SH.save(elib, body["id"], {"size": 10.0})
with ES.as_global():
    set_var("body_font", "Calibri")                              # the Global Standards change since
rows = ED.rows(cfg, root)
by = {r["what"]: r for r in rows}
check("each value that differs is a row, with the effort's value and the Global value",
      by["company > variables > body size"]["mine"] == "10" and by["company > variables > body size"]["global"] == "11"
      and by["company > variables > body font"]["mine"] == "Arial" and by["company > variables > body font"]["global"] == "Calibri", [(r["what"], r["mine"], r["global"]) for r in rows])
check("the effort's value is the one in use on every row", all(r["using"] == "effort" for r in rows))
st = by["Osprey Body  [RFP]"]
check("a style that differs is a row too, saying what the effort's has", st["kind"] == "item" and st["part"] == "Styles" and st["mine"] == "Size: 10 pt (Global: 11 pt)" and st["can"], st)
check("what is the same is not listed", "Osprey Heading 1  [RFP]" not in by and len(rows) == 3, [r["what"] for r in rows])
check("the count", ED.counts(rows) == {"differs": 3, "only_here": 0, "only_global": 0, "global": 0}, ED.counts(rows))

k = by["company > variables > body size"]["key"]
check("choosing Global on a row: the effort uses the Global value", ED.use_global(cfg, root, k) and var("body_size") == 11)
r = next(x for x in ED.rows(cfg, root) if x["key"] == k)
check("the row stays, marked as using Global, with the effort's own value still shown", r["using"] == "global" and r["mine"] == "10" and r["global"] == "11", r)
check("choosing it twice does nothing", not ED.use_global(cfg, root, k))
with ES.as_global():
    check("the Global Standards were not touched", var("body_size") == 11 and var("body_font") == "Calibri")
check("choosing This effort again: its own value is back", ED.use_mine(cfg, root, k) and var("body_size") == 10
      and next(x for x in ED.rows(cfg, root) if x["key"] == k)["using"] == "effort")
check("with nothing switched, This effort does nothing", not ED.use_mine(cfg, root, k))

ks = st["key"]
check("choosing Global on a style: the effort's latest has the Global values", ED.use_global(cfg, root, ks)
      and TL.Library(cfg).values(SH.top(TL.Library(cfg), body["id"]))["size"] == 11.0)
r = next(x for x in ED.rows(cfg, root) if x["key"] == ks)
check("the style's row stays, using Global, and its history kept the effort's own version", r["using"] == "global"
      and [h["note"] for h in SH.history(TL.Library(cfg), body["id"])][0] == "The Global Standards' version"
      and len(SH.history(TL.Library(cfg), body["id"])) == 3, SH.history(TL.Library(cfg), body["id"]))
check("choosing This effort on the style: its own values are the latest again, as a new version", ED.use_mine(cfg, root, ks)
      and TL.Library(cfg).values(SH.top(TL.Library(cfg), body["id"]))["size"] == 10.0 and len(SH.history(TL.Library(cfg), body["id"])) == 4)
check("the set uses it", [TL.Library(cfg).values(TL.Library(cfg).get(i)).get("size") for i in TL.Library(cfg).kit(rfp["id"])["items"]][0] == 10.0)

# only here, only in Global
new, _ = TL.Library(cfg).add("style", "Osprey Callout", {"type": "paragraph", "size": 9.0})
with ES.as_global():
    g = TL.Library(cfg); g.add("style", "Osprey Note", {"type": "paragraph", "size": 8.0})
    d = PRL.load(cfg); d["company"]["variables"]["new_global_value"] = "x"; PRL.save(cfg, d)
by = {r["what"]: r for r in ED.rows(cfg, root)}
check("a style made in the effort says so and carries no switch", by["Osprey Callout"]["state"] == "only_here" and not by["Osprey Callout"]["can"], by.get("Osprey Callout"))
check("a style only the Global Standards have says so", by["Osprey Note"]["state"] == "only_global" and by["Osprey Note"]["mine"] == "(not in this effort)")
v = by["company > variables > new global value"]
check("a value only the Global Standards have can be taken, and given back", v["state"] == "only_global" and v["can"] and ED.use_global(cfg, root, v["key"])
      and var("new_global_value") == "x" and ED.use_mine(cfg, root, v["key"]) and var("new_global_value") is None, v)

# a file that is not a list of values
os.makedirs(os.path.join(ES.set_dir(root), "production_parts"), exist_ok=True)
with open(os.path.join(ES.set_dir(root), "production_parts", "cover.docx"), "wb") as f:
    f.write(b"effort cover")
os.makedirs(os.path.join(cfg, "production_parts"), exist_ok=True)
with open(os.path.join(cfg, "production_parts", "cover.docx"), "wb") as f:
    f.write(b"global cover")
fr = next(r for r in ED.rows(cfg, root) if r["kind"] == "file")
check("a file that differs is one row", fr["what"] == "cover.docx" and fr["state"] == "differs" and fr["can"], fr)
ED.use_global(cfg, root, fr["key"])
p = os.path.join(ES.set_dir(root), "production_parts", "cover.docx")
check("choosing Global takes the file and keeps the effort's own beside it", open(p, "rb").read() == b"global cover"
      and next(r for r in ED.rows(cfg, root) if r["key"] == fr["key"])["using"] == "global")
ED.use_mine(cfg, root, fr["key"])
check("choosing This effort puts the effort's file back", open(p, "rb").read() == b"effort cover" and not os.path.exists(os.path.join(ES.set_dir(root), "_mine", "production_parts", "cover.docx")))
ES.leave(); ES.enter(cfg, root)
check("the choices are kept with the effort", isinstance(ED._switches(root), dict) and os.path.isfile(os.path.join(ES.set_dir(root), ED.SWITCHES)))
ES.leave()
check("with the effort closed the values still list; the library waits for the effort to be open", any(r["kind"] == "value" for r in ED.rows(cfg, root))
      and not any(r["kind"] == "item" for r in ED.rows(cfg, root)))

n = sum(checks)
print(f"EFFORT DIFF 4360 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
