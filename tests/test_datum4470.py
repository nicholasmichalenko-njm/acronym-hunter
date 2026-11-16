"""4.47.0, UX decisions 34, 36, 39, 40 and 59: the Production Datum's three states and what the app says about each.
The set is what the Global Standards code keeps; nothing new is saved. Two fictional PCs and one folder."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "A", "Stationkeeper Data")
import datum as DT, globalfolder as GF, globalstd as GS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


def put(cfg, rel, text):
    p = os.path.join(cfg, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p


A = os.path.join(tmp, "A", "Stationkeeper Data", "config"); os.makedirs(A)
B = os.path.join(tmp, "B", "Stationkeeper Data", "config"); os.makedirs(B)
F = os.path.join(tmp, "Shared", "Production Datum"); os.makedirs(F)

st = DT.state(B, "")
check("nothing installed: the state, the mark and the line", st["kind"] == DT.NONE and st["number"] == 0
      and DT.mark(st) == "No Production Datum installed" and DT.line(st) == "Production Datum: none installed", st)
check("... and the panel's one sentence names no Datum and explains nothing",
      DT.NOTHING == "Stationkeeper has no standards, acronym database or dictionaries yet.")
check("nothing installed and nothing newer: nothing will change", DT.will_change(B, F) is None)

put(A, "production_standards.json", json.dumps({"fonts": {"body": {"size": 11}}}))
put(A, "banned_words.csv", "word\nsynergy\n")
put(A, "custom_dictionaries.json", json.dumps({"dictionaries": [{"name": "One", "words": ["Kestrel"]}, {"name": "Two", "words": []}]}))
db = put(os.path.dirname(A), "acronym_database.csv", "Term,Definition,Category,Action\nKZQ,Kestrel Zone Query,Acronym,\nKAT,Kestrel Antenna Test,Acronym,\n\n")
GF.update(A, F, by="Ada", note="The first")
st = DT.state(A, F)
check("installed: Production Datum 1", st["kind"] == DT.INSTALLED and st["number"] == 1 and DT.mark(st) == "Production Datum 1"
      and DT.line(st) == "Production Datum 1" and st["taken"], st)
h = {name: (n, said) for name, n, said in DT.holds(A, db)}
check("what it holds, one line each with a count", h["Acronym database"] == (2, "Acronym database: 2 terms")
      and h["Custom dictionaries"][0] == 2 and h["Global Standards"][0] >= 2 and h["Global Standards"][1].startswith("Global Standards: "), h)
check("a database with one term says term, not terms", DT._n(1, "term", "terms") == "1 term")

stb = DT.state(B, F)
check("a PC with nothing installed sees one ready", stb["kind"] == DT.READY and stb["ready"] == 1
      and DT.mark(stb) == "No Production Datum installed, 1 is ready", stb)
GF.take(B, F)
check("... and after installing it is on 1", DT.mark(DT.state(B, F)) == "Production Datum 1")

put(A, "banned_words.csv", "word\nsynergy\nseamless\n")
GF.update(A, F, by="Ada", note="One more phrase")
stb = DT.state(B, F)
check("a newer one is ready: Production Datum 1, 2 is ready", stb["kind"] == DT.READY and DT.mark(stb) == "Production Datum 1, 2 is ready", stb)
wc = DT.will_change(B, F)
check("... what will change is said in counts, by part, before anything happens",
      wc and wc["number"] == 2 and wc["parts"] == [GS.names()["banned"]] and wc["words"].startswith("1 part will change: "), wc)
check("... and nothing was installed by asking", GS.state(B)["version"] == 1)
check("a folder that is gone is nothing newer, not an error", DT.state(B, os.path.join(tmp, "nowhere"))["kind"] == DT.INSTALLED)
check("the words never say Knowledge Pack, starter or Global Standards version",
      not any(w in " ".join([DT.mark(stb), DT.line(stb), DT.NOTHING, wc["words"]]) for w in ("Knowledge Pack", "starter", "Global Standards version")))
# 4.47.1: an effort remembers what it was started on; the final check says what it worked from
class WS:
    def __init__(self): self.d = {}
    def get(self, k, default=None): return self.d.get(k, default)
    def set(self, k, v): self.d[k] = v
ws = WS()
check("an effort started before this was kept says nothing (nothing is guessed)", DT.started(ws) == "" and DT.started(None) == "")
check("a new effort remembers the Production Datum it was started on", DT.record_start(ws, B) == 1 and DT.started(ws) == "Started on Production Datum 1", ws.d)
empty = os.path.join(tmp, "C", "config"); os.makedirs(empty)
ws2 = WS(); DT.record_start(ws2, empty)
check("... or that none was installed", DT.started(ws2) == "Started with no Production Datum installed", ws2.d)
import finalcheck as FC
r1 = FC.run({"name": "Volume I"}, {"datum_line": DT.line(DT.state(empty))})
r2 = FC.run({"name": "Volume I"}, {"datum_line": DT.line(DT.state(B))})
l1 = [x for x in r1["lines"] if x["check"] == "Working from"]; l2 = [x for x in r2["lines"] if x["check"] == "Working from"]
check("the checks before submission say what they worked from: none installed needs a person's look",
      len(l1) == 1 and l1[0]["status"] == FC.HUMAN and l1[0]["detail"].startswith("Production Datum: none installed."), l1)
check("... and with one installed it is named and passes", len(l2) == 1 and l2[0]["status"] == FC.PASS and l2[0]["detail"] == "Production Datum 1.", l2)
check("... and a check run with no Datum line given is as it was", not [x for x in FC.run({"name": "Volume I"}, {})["lines"] if x["check"] == "Working from"])
k = sum(checks)
print(f"DATUM 4470 {'PASS' if k == len(checks) and checks else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if checks and k == len(checks) else 1)
