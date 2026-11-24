"""4.64.0 (Nicholas 2026-11-23): the setup as it will be written, read back before it is written. The blocks are the
paragraphs Make the setup writes, in the same order, each with its kind and style; an order set under each heading
shows; the drawing gives each kind its look and names its style. Fictional (Kestrel)."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["AH_OCR_ENGINE"] = "tesseract"
import compliance as C, setupdoc as SD, setuporder as SO, setuppreview as SP, setuptemplate as ST

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def item(i, text, decision="Keep", **kw):
    it = {"id": i, "text": text, "decision": decision, "suggest": "Keep", "file": "Kestrel_Section_L.pdf", "section": "L.4",
          "type": "Requirement", "map": "1.1 Thermal Design", "lead": "", "context_for": "", "where": "", "page": 1}
    it.update(kw)
    return it


d = tempfile.mkdtemp(); cfg = tempfile.mkdtemp()
M = C.Matrix(os.path.join(d, "Kestrel_Matrix.xlsx"), "Kestrel")
M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal Design\n1.2 Risk Management")
M.items = [item("K-1", "The Offeror shall describe the thermal design."),
           item("K-2", "Thermal margins are reported at each review.", decision="Context", context_for="K-1"),
           item("K-3", "The Offeror shall list the thermal tests."),
           item("K-4", "The Offeror shall name the risk owner.", map="1.2 Risk Management")]
S = SD.setup_of(M)
S["notes"]["K-1"] = "NOTE-ONE lead with the heritage design"
S["mgmt"]["1.1 Thermal Design"] = "GUIDE keep it to two pages"
S["owners"]["1.1 Thermal Design"] = {"lead": "A. Lee", "with": ""}

vols = SP.volumes(M, cfg)
check("one volume, as Make the setup would take it", [v for v, _e, _s in vols] == ["Volume I Technical"], [v for v, _e, _s in vols])
v, e, std = vols[0]
opts, bl = SP.blocks(M, v, e, std, cfg)
heads = SP.headings(bl)
check("the headings, with their levels", [(lv, t) for _i, lv, t in heads] == [(1, "Volume I Technical"), (2, "1.1 Thermal Design"), (2, "1.2 Risk Management")], heads)
texts = [(b["kind"], b["style"]) for b in bl if b["what"] == "text"]
check("each piece has its kind and the style it is written in", ("rfp", "SK RFP Requirement") in texts and ("pm", "SK PM Direction") in texts
      and ("support", "SK RFP Support") in texts and ("note", "SK Setup Note") in texts, texts)


def pos(word):
    return next((i for i, b in enumerate(bl) if word in b["text"]), -1)


first = [pos(w) for w in ("Lead: A. Lee", "describe the thermal design", "NOTE-ONE", "Thermal margins", "list the thermal tests", "GUIDE keep", "1.2 Risk Management", "name the risk owner")]
check("the same order Make the setup writes with no order set", first == sorted(first) and -1 not in first, first)
check("the counts by kind", SP.counts(bl) == {"note": 1, "rfp": 3, "pm": 2, "support": 1}, SP.counts(bl))
check("nothing was written to disk", os.listdir(d) == [] and os.listdir(cfg) == [], (os.listdir(d), os.listdir(cfg)))

SO.set_order(S, ["note", "topic", "objective", "capture", "rfp", "customer", "pm", "library"])
opts, bl = SP.blocks(M, v, e, std, cfg)
got = [pos(w) for w in ("describe the thermal design", "Thermal margins", "list the thermal tests", "NOTE-ONE", "GUIDE keep")]
check("an order set under each heading shows in the preview", got == sorted(got) and -1 not in got, got)

opts2 = dict(opts); opts2["pm"] = dict(opts["pm"], font="Georgia", size=9.0, color="AA0000", bold=True)
h = SP.html(opts2, bl)
check("the drawing: a heading has its anchor", f'<a name="h{SP.headings(bl)[1][0]}"></a>' in h and "1.1 Thermal Design" in h)
check("... each kind in its look: the default color, and a look set in the app", "color:#7030A0" in h and "color:#AA0000" in h
      and "font-family:'Georgia'" in h and "font-size:9pt" in h and "font-weight:bold" in h, h[:600])
check("... with the style's name after the text", "SK PM Direction</span>" in h and "SK RFP Requirement</span>" in h)
check("... or without it", "SK PM Direction" not in SP.html(opts2, bl, show_styles=False))
check("... and the customer's words are escaped", "<script>" not in SP.html(opts, [{"what": "text", "text": "<script>x</script>", "kind": "rfp", "style": "S"}]))
opts3 = dict(opts); opts3["pm"] = dict(opts["pm"], include=False)
S2 = SD.setup_of(M); S2["on_template"] = {"pm": {"include": False}}
_o, bl3 = SP.blocks(M, v, e, std, cfg)
check("a kind left out of the setup is left out of the preview", not any(b["kind"] == "pm" for b in bl3) and any(b["kind"] == "rfp" for b in bl3),
      [b["kind"] for b in bl3])
print(f"SETUP PREVIEW 4640 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
