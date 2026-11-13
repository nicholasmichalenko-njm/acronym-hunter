"""4.27.3 offscreen: light and dark, everywhere at once (Nicholas's recording 2026-11-12: the menu and parts of pages
kept the other theme's colors). Every page of the menu and its tabs is opened, the theme is switched three times, and no
widget in view keeps a color that belongs only to the other theme. The menu is one navy in both. Text holds 4.5 to 1.
Settings > People: a person's role on the open effort is on their row of the author list. Fictional (Osprey)."""
import os, re, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ.pop("SK_THEME", None)
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import deliverables as DL, effort as E, effortrec as RR, workspace as W
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
from skqt import design as D
from skqt.mainwin import MainWindow, RAIL, TABS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


# ---- the colors, with no window
rail = [k for k in D.LIGHT if k.startswith("rail")]
check("the menu is one navy: every menu color is the same in light and dark", rail and all(D.LIGHT[k] == D.DARK[k] for k in rail))
check("light and dark name the same colors", set(D.LIGHT) == set(D.DARK))
PAIRS = [("text", "bg"), ("text", "surface"), ("text", "surface2"), ("muted", "surface"), ("muted", "bg"), ("accent_fg", "accent"),
         ("rail_text", "rail"), ("rail_group", "rail"), ("rail_active_text", "rail_active"), ("rail_text", "rail_sel_bg"),
         ("ok", "ok_soft"), ("warn", "warn_soft"), ("crit", "crit_soft"), ("req", "req_soft"), ("ctx", "ctx_soft"), ("cust", "cust_soft"),
         ("accent", "accent_soft"), ("accent", "surface"), ("ok", "surface"), ("warn", "surface"), ("crit", "surface")]
for nm, t in (("light", D.LIGHT), ("dark", D.DARK)):
    low = [(a, b, round(D.contrast(t[a], t[b]), 2)) for a, b in PAIRS if D.contrast(t[a], t[b]) < 4.5]
    check(f"{nm}: text holds 4.5 to 1 on what it sits on", not low, low)

# ---- the window
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
ED = os.path.join(tmp, "Osprey"); os.makedirs(os.path.join(ED, "Customer documents"))
LIST = os.path.join(ED, "Osprey_Effort_List.xlsx"); L = E.EffortList(LIST, "Osprey"); L.client = "Osprey Systems Command"; L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST, customer_dir=os.path.join(ED, "Customer documents"))
ws = W.Workspace(W.data_dir_for(LIST), "Osprey")
rec = RR.Record(ws.root)
DL.add(rec, "Volume I Technical", kind="Volume", owner="Dana")
rec.add_task("Call the teammate", owner="Dana") if hasattr(rec, "add_task") else None
app = QApplication([]); D.apply(app, "light")
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
w.work_on("Osprey"); app.processEvents()
keys = list(dict.fromkeys([k for _g, items in RAIL for k, _t in items] + [k for v in TABS.values() for k, _t in v]))
opened = []
for k in keys:
    try:
        w.go(k); app.processEvents(); opened.append(k)
    except Exception as e:                           # noqa: BLE001
        print("could not open", k, repr(e)[:120])
check("every page of the menu and its tabs opens", len(opened) == len(keys), sorted(set(keys) - set(opened)))
ONLY = {"light": {v.upper() for v in D.LIGHT.values()} - {v.upper() for v in D.DARK.values()} - {"#FFFFFF"},
        "dark": {v.upper() for v in D.DARK.values()} - {v.upper() for v in D.LIGHT.values()}}


def stale(other):
    """Widgets in view whose own style still holds a color only the other theme has."""
    out = []
    for x in app.allWidgets():
        s = x.styleSheet()
        if not s or x.window() is not w or not x.isVisibleTo(w):
            continue
        if {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}", s)} & ONLY[other]:
            out.append((x.objectName() or type(x).__name__, s[:70]))
    return out


sp = w.settings_page if hasattr(w, "settings_page") else w.pages["settings"]
for turn, (want, other) in enumerate((("dark", "light"), ("light", "dark"), ("dark", "light")), 1):
    w.go("settings"); app.processEvents()
    got = sp.set_look(want)
    check(f"switch {turn}: Settings > Appearance sets {want} and says it is everywhere", got == (want == "dark") and "every page" in sp.look_note.text()
          and "restart" not in sp.look_note.text().lower(), sp.look_note.text())
    here = stale(other)
    check(f"switch {turn}: the page in view and the menu took {want} at once", not here, here[:4])
    bad = {}
    for k in opened:
        w.go(k); app.processEvents(); QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        s = stale(other)
        if s:
            bad[k] = s[:2]
    check(f"switch {turn}: no page keeps a {other} color ({len(opened)} pages)", not bad, bad)
    check(f"switch {turn}: the menu's navy did not move", D.tokens()["rail"] == D.LIGHT["rail"] and w.palette().window().color().name().upper() == D.tokens()["bg"].upper())
p = D.Pill("Saved", "ok"); c = D.Chip("L.3.2", "req"); tl = D.Tile("3", "tasks late", "crit")
D.apply(app, "light")
check("a pill, a chip and a tile write their own colors again", D.LIGHT["ok"] in p.styleSheet() and D.LIGHT["req"] in c.styleSheet()
      and D.LIGHT["crit"] in tl.styleSheet() + tl.value.styleSheet() and D.DARK["ok"] not in p.styleSheet())
n0 = D.retheme(); del p, c, tl
import gc; gc.collect()
check("a widget that is gone is not kept for its style", D.retheme() <= n0 - 3, (n0, D.retheme()))

# ---- People: the role on the row
from skqt import modes
modes.save(appearance="windows")
w.authors.add("Dana Reyes", efforts=["Osprey"]) if hasattr(w.authors, "add") else None
w.go("settings"); app.processEvents()
card = sp.authors; card.fill()
names = [card.table.item(r, 0).text() for r in range(card.table.rowCount())]
check("the author list has a Role column named for the open effort", card.table.horizontalHeaderItem(1).text() == "Role on Osprey"
      and card.table.columnCount() == 4, card.table.horizontalHeaderItem(1).text())
if "Dana Reyes" in names:
    box = card.role_box("Dana Reyes")
    check("a name that shows in the effort has its role on the row", box is not None)
    check("... picked, it is saved on the effort at once", card.save_role("Dana Reyes", "Volume lead") and RR.Record(ws.root).role_of("Dana Reyes") == "Volume lead")
    card.fill()
    check("... and shown when the list is drawn again", card.role_box("Dana Reyes").currentText() == "Volume lead")
    check("... the same role twice changes nothing", card.save_role("Dana Reyes", "Volume lead") is False)
else:
    check("a name was added to the author list for the test", False, names)
w.close()
n = sum(checks)
print(f"QT THEME 4273 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
__import__("hangguard").end(0 if n == len(checks) else 1)
