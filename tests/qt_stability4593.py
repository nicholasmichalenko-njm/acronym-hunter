"""4.59.3 offscreen (Nicholas 2026-11-23 13:08, "Yes" to a stability release; claude/stationkeeper-diagnosis-freezes-
crashes-and-updates-2026-11-23.md): no event filter on the whole application; link_items gives the same links without
reading every instruction again for every item; a run that reopened the last effort and ended badly soon after makes
the next start safe; the two standing errors; a file the watch adds by itself is no version by likeness. Fictional."""
import copy, json, os, random, re, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
import compliance as C, supportfile as SF, watch as WA, redlinecopy as RC, docintake as DI
from PySide6.QtWidgets import QApplication, QHeaderView, QTableWidget, QVBoxLayout, QWidget
from skqt import adaptive as AD, design as theme, foundview as FV

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


# ---- the links, as before
def old_links(items):
    instr = [it for it in items if it["type"] in ("Instruction", "Format")]
    for it in items:
        links = []
        for r in [r.strip() for r in it.get("xrefs", "").split(";") if r.strip()]:
            num = re.sub(r"^(?:section|sec\.|paragraph|para\.?|¶)\s+", "", r, flags=re.I)
            if "." not in num:
                continue
            for o in items:
                if o is not it and o["section"] and (o["section"] == num or o["section"].startswith(num + ".")):
                    links.append(o["id"])
        if it["type"] in ("Evaluation", "SOW") and not links and instr:
            w = C._words(it["text"])
            best, score = None, 0.0
            for o in instr:
                ow = C._words(o["text"])
                if w and ow:
                    j = len(w & ow) / len(w | ow)
                    if j > score:
                        best, score = o, j
            if best is not None and score >= 0.3:
                links.append(best["id"])
        it["links"] = "; ".join(dict.fromkeys(links))[:300]
    return items


random.seed(4593)
WORDS = ("kestrel heron osprey petrel merlin system shall provide offeror proposal describe approach management technical staffing "
         "schedule risk quality data security training transition performance report plan test delivery support interface review").split()


def make(n):
    out = []
    for i in range(n):
        sec = ".".join(str(random.randint(1, 6)) for _ in range(random.randint(0, 3)))
        out.append({"id": f"K-{i}", "type": random.choice(["Instruction", "Evaluation", "SOW", "Format", "Context"]),
                    "section": ("L." + sec) if sec and i % 3 else sec,
                    "text": " ".join(random.choice(WORDS) for _ in range(random.randint(3, 14))),
                    "xrefs": "; ".join(random.choice([f"Section L.{random.randint(1, 6)}.{random.randint(1, 6)}", f"{random.randint(1, 6)}.{random.randint(1, 6)}",
                                                      "Section C", "para 2.3"]) for _ in range(random.randint(0, 2)))})
    return out


a = make(1200); b = copy.deepcopy(a)
old_links(a); C.link_items(b)
check("the same links as before, item for item", [x["links"] for x in a] == [x["links"] for x in b] and any(x["links"] for x in b))
big = make(6000)
t0 = time.time(); C.link_items(big); took = time.time() - t0
check("6,000 items are linked in seconds, not minutes", took < 20, took)

# ---- no filter on the whole application
app = QApplication([]); theme.apply(app)
src = open(os.path.join(os.path.dirname(HERE), "skqt", "adaptive.py"), encoding="utf-8").read()
check("the tuner is not installed as a filter on the application", "app.installEventFilter" not in src and getattr(app, "_sk_tuner", None) is not None)
st = AD.PageStack()
pg = QWidget(); v = QVBoxLayout(pg); tb = QTableWidget(3, 3); tb.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch); v.addWidget(tb)
other = QWidget(); st.addWidget(other); st.addWidget(pg); st.show(); app.processEvents()
st.setCurrentWidget(pg); app.processEvents()
check("a page's tables are tuned when the page is shown", tb.property("sk_tuned") and tb.horizontalHeader().sectionResizeMode(0) == QHeaderView.Interactive)
lone = QTableWidget(2, 2); lone.show(); app.processEvents()
check("a table in a window of its own is found by the sweep", app._sk_tuner.sweep() >= 0 and lone.property("sk_tuned"))

# ---- a safe start after a run that ended badly soon after reopening the effort
sd = tempfile.mkdtemp()
check("a first start is not safe", SF.begin(sd) is False)
SF.started(sd); SF.opened(sd)
check("the run reopened the effort and was not closed: the next start is safe, and says why", SF.begin(sd) is True and SF.REASON == "soon")
SF.started(sd); SF.opened(sd); SF.ended(sd)
check("closed by the person: the next start reopens", SF.begin(sd) is False)
SF.started(sd)
check("no effort was reopened: not safe", SF.begin(sd) is False)
SF.started(sd); SF.opened(sd)
d = json.load(open(os.path.join(sd, SF.START_FILE))); d["alive"] = d["began"] + SF.SOON + 60
json.dump(d, open(os.path.join(sd, SF.START_FILE), "w"))
check("it ran longer than ten minutes: not safe", SF.begin(sd) is False)
sd2 = tempfile.mkdtemp()
check("two starts that never finished still make the third safe", (SF.begin(sd2), SF.begin(sd2), SF.begin(sd2)) == (False, False, True) and SF.REASON == "twice")

# ---- the two standing errors
pl = open(os.path.join(os.path.dirname(HERE), "skqt", "pagelayoutsview.py"), encoding="utf-8").read()
check("Page Layout's New, Rename and Remove no longer take the click's own value for the kind", "lambda k=kind" not in pl and pl.count("lambda _c=False, k=kind") == 3)
check("the double-click zoom is on the picture preview, not the text", "mouseDoubleClickEvent" in FV.PicView.__dict__ and "mouseDoubleClickEvent" not in FV.PreviewText.__dict__)

# ---- the watch
tmp = tempfile.mkdtemp()
copyf = os.path.join(tmp, RC.copy_name(os.path.join(tmp, "Kestrel_Section_L.pdf")))
open(copyf, "wb").write(b"x")
check("a file only named like a redline copy is a file that came in", not WA._made_here(copyf))
json.dump({"source": "Kestrel_Section_L.pdf"}, open(copyf + RC.SIDE, "w"))
check("a redline copy Prepare made is not added by the watch", WA._made_here(copyf))
check("the watch asks for no version by likeness", "by_likeness=False" in open(os.path.join(os.path.dirname(HERE), "skqt", "watchauto.py"), encoding="utf-8").read()
      and "by_likeness" in DI.plan.__code__.co_varnames)

print(f"STABILITY 4593 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
