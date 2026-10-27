"""2.50.0 compliance words the team adds make a sentence a requirement: a rescan finds them in an open matrix without
touching decisions; a word taken off the list sends its sentences back to Context; add_words adds selected text."""
import os, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import compliance as C, cwords as W
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
TEXT = ("L.4 Technical Volume\nThe Offeror shall describe the thermal design. The Offeror is responsible for quarterly "
        "program reviews. The program office is located in Colorado. Key personnel are responsible for safety training.")
C.set_extra_words([])
items = C.extract([("Section L Instructions.docx", [("Page 1", TEXT)])])
by = {it["text"][:30]: it for it in items}
resp = next(it for it in items if "quarterly" in it["text"])
safety = next(it for it in items if "safety" in it["text"])
check("before: a sentence without a compliance word is Context", resp["type"] == "Context" and safety["type"] == "Context")
safety["decision"] = "Drop"
new = W.add_words(["Responsible for", "shall"], config_dir=tmp)
check("add_words adds the new phrase (lower case) and skips one already there", new == ["responsible for"], new)
cfg = W.load(tmp)
check("added() lists the team's words", W.added(cfg) == ["responsible for"])
res = C.rescan_words(items, cfg=cfg)
check("rescan: the undecided sentence is a requirement candidate now", resp["type"] != "Context" and resp["suggest"] == "Keep"
      and resp["new"] == C.FOUND and resp["id"] in res["found"] and resp["modal"] == "responsible for", (resp["type"], resp["suggest"], resp["modal"]))
check("rescan: a decided sentence keeps its decision and is counted", safety["decision"] == "Drop" and safety["type"] == "Context"
      and res["decided"] == [safety["id"]], res)
check("rescan: other sentences stay as they were", next(it for it in items if "Colorado" in it["text"])["type"] == "Context"
      and next(it for it in items if "thermal" in it["text"])["new"] == "")
cfg["words"] = [w for w in cfg["words"] if w != "responsible for"]
res = C.rescan_words(items, cfg=cfg)
check("a word taken off the list: its sentences are Context again", resp["type"] == "Context" and resp["new"] == "" and res["back"] == [resp["id"]])
C.set_extra_words(["responsible for"])
items2 = C.extract([("Section L Instructions.docx", [("Page 1", TEXT)])])
check("a new read uses the added words too", next(it for it in items2 if "quarterly" in it["text"])["type"] != "Context")
C.set_extra_words([])
n = sum(checks)
print(f"CWRESCAN PASS ({n}/{len(checks)})" if n == len(checks) else f"CWRESCAN FAIL ({n}/{len(checks)})")
