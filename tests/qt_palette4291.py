"""4.29.1 offscreen: the app's colors by choice (Nicholas 2026-11-13 answer 19). Station navy, Slate and teal, or My
colors: an accent, a menu color and a page color typed as hex values in Settings > Appearance, kept on this PC, used at
once, with a line saying what would be hard to read, and Reset. The colors are made up (no brand's)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
os.environ.pop("SK_THEME", None)
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
from skqt import design as D, palette as P
from skqt.mainwin import MainWindow
from skqt.modes import save, settings

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


# ---- the rules, with no window
check("a hex color reads with or without #, three digits or six; anything else is not one",
      P.clean("0f6f6a") == "#0F6F6A" and P.clean("#abc") == "#AABBCC" and P.clean("teal") == "" and P.clean("#12345") == "")
check("Station navy changes nothing", P.colors_of({}) == {} and P.colors_of({"palette": "navy"}) == {})
PAIRS = [("text", "bg"), ("text", "surface"), ("muted", "bg"), ("accent_fg", "accent"), ("rail_text", "rail"), ("rail_group", "rail"),
         ("rail_active_text", "rail_active"), ("rail_text", "rail_sel_bg"), ("accent", "accent_soft"), ("accent", "surface")]
for nm, base, dark in (("light", D.LIGHT, False), ("dark", D.DARK, True)):
    t = P.tokens(base, P.colors_of({"palette": "slate"}), dark)
    low = [(a, b, round(P.contrast(t[a], t[b]), 2)) for a, b in PAIRS if P.contrast(t[a], t[b]) < 4.5]
    check(f"Slate and teal, {nm}: text holds 4.5 to 1 on what it sits on, and nothing to warn of", not low and not P.warn(t), (low, P.warn(t)))
    check(f"... {nm}: it names the same colors as Station navy", set(t) == set(base))
t = P.tokens(D.LIGHT, P.colors_of({"palette": "slate"}), False)
check("... its accent, menu and page are the three it names; the menu is the same in light and dark", t["accent"] == "#0F6F6A" and t["rail"] == "#0E2230"
      and t["bg"] == "#F1F4F3" and P.tokens(D.DARK, P.colors_of({"palette": "slate"}), True)["rail"] == "#0E2230")
mine = {"palette": "mine", "brand_colors": {"accent": "#7A3E9D", "menu": "#F3EEF8", "page": "nonsense"}}
t = P.tokens(D.LIGHT, P.colors_of(mine), False)
check("My colors: a light menu gets dark words; a value that is not a color is left out, not guessed", t["rail"] == "#F3EEF8"
      and P.contrast(t["rail_text"], t["rail"]) >= 4.5 and t["bg"] == D.LIGHT["bg"] and t["accent"] == "#7A3E9D", t["rail_text"])
pale = P.tokens(D.LIGHT, {"accent": "#FFE9A8"}, False)
w = P.warn(pale)
check("a pale accent: the line says links are hard to see on a card, with the ratio", any("accent is too close" in x and "to 1" in x for x in w), w)
check("... in dark the same accent is moved until it reads", P.contrast(P.tokens(D.DARK, {"accent": "#10263F"}, True)["accent"], D.DARK["surface"]) >= 4.5)

# ---- Settings > Appearance
app = QApplication.instance() or QApplication(sys.argv)
D.apply(app, "light")
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg, exist_ok=True)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1400, 900); w.show(); app.processEvents()
w.go("settings"); app.processEvents()
sp = w.settings_page
check("Appearance has Colors: Station navy, Slate and teal, My colors", [sp.colors.itemText(i) for i in range(sp.colors.count())]
      == ["Station navy", "Slate and teal", "My colors"] and sp.colors.currentData() == "navy" and not sp.mine_w.isVisibleTo(sp))
navy = dict(D.tokens())
sp.colors.setCurrentIndex(1); app.processEvents()
check("Slate and teal: kept, and used at once", settings().get("palette") == "slate" and D.tokens()["accent"] == "#0F6F6A"
      and D.tokens()["rail"] == "#0E2230" and "#0F6F6A" in app.styleSheet())
sp.colors.setCurrentIndex(2); app.processEvents()
check("My colors: three boxes, Accent, Menu and Page", sp.mine_w.isVisibleTo(sp) and list(sp.color_boxes) == ["accent", "menu", "page"])
sp.color_boxes["accent"].setText("7a3e9d"); sp.color_boxes["accent"].editingFinished.emit(); app.processEvents()
check("type a hex value: kept as #RRGGBB in this PC's settings and used at once", settings()["brand_colors"] == {"accent": "#7A3E9D"}
      and D.tokens()["accent"] == "#7A3E9D" and sp.color_boxes["accent"].text() == "#7A3E9D", settings().get("brand_colors"))
sp.color_boxes["menu"].setText("purple"); sp.color_boxes["menu"].editingFinished.emit(); app.processEvents()
check("a value that is not a color: said, and the menu stays as it was", "not a hex color" in sp.colors_warn.text()
      and D.tokens()["rail"] == navy["rail"] and "menu" not in settings()["brand_colors"], sp.colors_warn.text())
sp.color_boxes["menu"].setText(""); sp.color_boxes["accent"].setText("#FFE9A8"); sp.color_boxes["accent"].editingFinished.emit(); app.processEvents()
check("a color that is hard to read is used, with a line saying so", D.tokens()["accent"] == "#FFE9A8" and "hard to" in sp.colors_warn.text()
      and sp.colors_warn.isVisibleTo(sp), sp.colors_warn.text())
sp.colors_reset.click(); app.processEvents()
check("Reset: Station navy again, the three colors forgotten", settings().get("palette") == "navy" and settings().get("brand_colors") == {}
      and D.tokens() == navy and sp.colors.currentData() == "navy" and not sp.colors_warn.isVisibleTo(sp))
import glob
src = "".join(open(f, encoding="utf-8").read() for f in glob.glob(os.path.join(os.path.dirname(HERE), "skqt", "*.py")))
check("the person's colors are in settings, never in the code", "#7A3E9D" not in src)
n = sum(checks)
print(f"QT PALETTE 4291 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
