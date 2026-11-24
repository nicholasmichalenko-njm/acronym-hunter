"""4.63.0 (Nicholas 2026-11-23): the order of the kinds of text under a heading of the setup. One order for the whole
setup, a heading may have its own; until one is set a section is written as before; support text travels with its
requirement; within a kind the pieces keep their order. Fictional (Kestrel)."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["AH_OCR_ENGINE"] = "tesseract"
import compliance as C, setupdoc as SD, setuporder as SO, outline_ops as OO

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def item(i, text, decision="Keep", **kw):
    it = {"id": i, "text": text, "decision": decision, "suggest": "Keep", "file": "Kestrel_Section_L.pdf", "section": "L.4",
          "type": "Requirement", "map": "1.1 Thermal Design", "lead": "", "context_for": "", "where": "", "page": 1}
    it.update(kw)
    return it


def make():
    d = tempfile.mkdtemp()
    M = C.Matrix(os.path.join(d, "Kestrel_Matrix.xlsx"), "Kestrel")
    M.outline = C.parse_outline("Volume I Technical\n1.1 Thermal Design\n1.2 Risk Management")
    M.items = [item("K-1", "The Offeror shall describe the thermal design."),
               item("K-2", "Thermal margins are reported at each review.", decision="Context", context_for="K-1"),
               item("K-3", "The Offeror shall list the thermal tests."),
               item("K-4", "The Offeror shall name the risk owner.", map="1.2 Risk Management")]
    S = SD.setup_of(M)
    S["notes"]["K-1"] = "NOTE-ONE lead with the heritage design"
    S["notes"]["K-3"] = "NOTE-THREE name the chamber"
    S["mgmt"]["1.1 Thermal Design"] = "GUIDE keep it to two pages"
    S["mgmt"]["1.2 Risk Management"] = "GUIDE-RISK one table"
    S["notes"]["K-4"] = "NOTE-FOUR use the register"
    S["owners"]["1.1 Thermal Design"] = {"lead": "A. Lee", "with": ""}
    return d, M, S


def paras(M, d):
    out = SD.export(M, d)
    p = out[0] if isinstance(out, (list, tuple)) else out
    p = p if isinstance(p, str) else p.get("path", "")
    return [x if isinstance(x, str) else x[0] for x in SD.docx_paragraphs(p)]


def pos(ps, word):
    return next((i for i, t in enumerate(ps) if word in t), -1)


d, M, S = make()
ps = paras(M, d)
check("the setup was written", pos(ps, "thermal design") >= 0 and pos(ps, "NOTE-ONE") >= 0, ps)
before = [pos(ps, w) for w in ("Lead: A. Lee", "describe the thermal design", "NOTE-ONE", "Thermal margins", "list the thermal tests", "NOTE-THREE", "GUIDE keep")]
ps0 = list(ps)
check("with no order set, a section is written as before: each note under its requirement", before == sorted(before) and -1 not in before, before)
check("... and nothing is kept", "kind_order" not in S and SO.order_for(S, "1.1 Thermal Design") is None)

# his example: all management guidance beneath the RFP text
SO.set_order(S, ["note", "topic", "objective", "capture", "rfp", "customer", "pm", "library"])
ps = paras(M, d)
got = [pos(ps, w) for w in ("Lead: A. Lee", "describe the thermal design", "Thermal margins", "list the thermal tests", "NOTE-ONE", "NOTE-THREE", "GUIDE keep")]
check("an order for the whole setup: the RFP text, then all the management guidance", got == sorted(got) and -1 not in got, (got, ps))
check("... support text stays with the requirement it supports", pos(ps, "Thermal margins") == pos(ps, "describe the thermal design") + 1)
check("... within a kind the pieces keep their order", pos(ps, "NOTE-ONE") < pos(ps, "NOTE-THREE") < pos(ps, "GUIDE keep"))
r = [pos(ps, w) for w in ("name the risk owner", "NOTE-FOUR", "GUIDE-RISK")]
check("... every heading follows it", r == sorted(r) and -1 not in r, r)
check("... a section's text does not leave its section", pos(ps, "GUIDE keep") < pos(ps, "1.2 Risk Management") < pos(ps, "name the risk owner"))

# a heading that differs
SO.set_order(S, ["pm", "rfp"], "1.2 Risk Management")
ps = paras(M, d)
r = [pos(ps, w) for w in ("NOTE-FOUR", "GUIDE-RISK", "name the risk owner")]
check("a heading with its own order: guidance first there", r == sorted(r) and -1 not in r, r)
t = [pos(ps, w) for w in ("list the thermal tests", "NOTE-ONE")]
check("... the other headings keep the whole setup's", t == sorted(t), t)
check("an order names every kind once, the ones given first", SO.own(S, "1.2 Risk Management")[:2] == ["pm", "rfp"]
      and sorted(SO.own(S, "1.2 Risk Management")) == sorted(SO.default()))

# a heading renamed keeps its order
if hasattr(OO, "relabel"):
    OO.relabel(M, {"1.2 Risk Management": "1.2 Risk"})
    check("a heading renamed keeps its own order", SO.own(S, "1.2 Risk") is not None and SO.own(S, "1.2 Risk Management") is None, S.get("kind_order"))
    lab2 = "1.2 Risk"
else:
    lab2 = "1.2 Risk Management"

# back
check("Same as the whole setup takes a heading's own order away", SO.clear(S, lab2) and SO.own(S, lab2) is None and SO.order_for(S, lab2) == SO.own(S, ""))
check("As it was written before takes the whole setup's order away", SO.clear(S) and SO.order_for(S, "1.1 Thermal Design") is None)
ps = paras(M, d)
check("... and the section is written as it was at the start", ps[:9] == ps0[:9], ps)

# saved with the matrix
SO.set_order(S, ["pm", "rfp"])
M.pending = True
try:
    M.save()
    M2 = C.Matrix(M.path, "Kestrel"); M2.load()
    check("the order is saved with the matrix and read back", SO.own(SD.setup_of(M2), "")[:2] == ["pm", "rfp"], SD.setup_of(M2).get("kind_order"))
except Exception as e:  # noqa: BLE001
    check("the order is saved with the matrix and read back", False, repr(e))
print(f"SETUP ORDER 4630 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
