"""2.60.0 the Qt design system: every text color on every surface meets WCAG 2.1 AA contrast (4.5:1) in light and
dark; the meaning colors are distinct; the components build in both themes; the main window shows the navigation
rail (Compliance steps, the areas still in the classic app shown but not clickable), the page title, search and the
saved state."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import tempfile
import app_gui as A
from PySide6.QtWidgets import QApplication
from skqt import design as D

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


PAIRS = [("text", "bg"), ("text", "surface"), ("text", "surface2"), ("muted", "surface"), ("muted", "bg"), ("muted", "surface2"),
         ("faint", "surface"), ("accent", "surface"), ("accent_fg", "accent"), ("rail_text", "rail"), ("rail_active_text", "rail_active"),
         ("req", "req_soft"), ("ctx", "ctx_soft"), ("cust", "cust_soft"), ("ok", "ok_soft"), ("warn", "warn_soft"), ("crit", "crit_soft"),
         ("head", "head_soft"), ("crit", "surface"), ("text", "accent_soft"), ("req", "surface"), ("ctx", "surface")]
for name, t in (("light", D.LIGHT), ("dark", D.DARK)):
    low = [(a, b, round(D.contrast(t[a], t[b]), 2)) for a, b in PAIRS if D.contrast(t[a], t[b]) < 4.5]
    check(f"{name}: every text color meets 4.5:1 on its surface", not low, low)
    check(f"{name}: the same tokens in both themes", set(t) == set(D.LIGHT))
check("the meaning colors are distinct", len({D.LIGHT[k] for k in ("req", "ctx", "cust", "head", "warn", "crit")}) == 6)
app = QApplication([])
for theme in ("light", "dark"):
    os.environ["SK_THEME"] = theme
    dark = D.apply(app)
    check(f"{theme}: applied", dark == (theme == "dark") and D.tokens() is (D.DARK if dark else D.LIGHT))
    card = D.Card("Coverage", "Every sentence of every file.", actions=(D.button("Run", "primary"),))
    card.add(D.Pill("3 requirements", "req")); card.add(D.Chip("1.1 Technical Approach", "req", on_remove=lambda: None))
    card.add(D.EmptyState("Nothing yet", "Read the RFP first.", "Read", lambda: None))
    card.resize(500, 300); card.show(); app.processEvents()
    check(f"{theme}: components build and show", card.isVisible() and card.title.text() == "Coverage")
    card.close()
os.environ["SK_THEME"] = "light"
D.apply(app)
from skqt.mainwin import MainWindow
tmp = tempfile.mkdtemp()
w = MainWindow(app, os.path.join(tmp, "config"), A.APP_VERSION); w.resize(1400, 900); w.show(); app.processEvents()
rail = [b.text() for b in w.findChildren(type(w.step_btns["read"])) if b.objectName() == "rail"]
check("the rail: Compliance steps, then the areas still in the classic app", rail[:4] == ["Read RFP", "Structure", "Assign", "Prove"]
      and all(not b.isEnabled() for b in w.findChildren(type(w.step_btns["read"])) if b.objectName() == "rail" and b.text() not in rail[:4]), rail)
w.go("prove"); app.processEvents()
check("the top bar names the page", w.page_title.text() == "Prove" and w.stack.currentWidget() is w.prove_page)
check("no effort: the saved state says so", w.saved.text() == "No matrix")
w.toast("Saved"); app.processEvents()
check("a toast shows and names what happened", w.toaster.isVisible() and w.toaster.text() == "Saved")
w.close()
n = sum(checks)
print(f"QT DESIGN PASS ({n}/{len(checks)})" if n == len(checks) else f"QT DESIGN FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
