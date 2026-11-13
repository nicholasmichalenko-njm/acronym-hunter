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
         ("head", "head_soft"), ("crit", "surface"), ("text", "accent_soft"), ("req", "surface"), ("ctx", "surface"),
         ("rail_group", "rail"), ("rail_text", "rail_card"), ("rail_active_text", "rail_sel_bg"), ("rail_group", "rail_card"),
         ("text", "accent_tint"), ("muted", "accent_tint")]      # 3.15.0: menu groups, the selected item, key card headers
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
rail = [b.text() for b in w.findChildren(type(w.step_btns["home"])) if b.objectName() == "rail"]
steps = [b.text() for k, b in w.step_btns.items()]
check("the rail: the effort's path, then Team and Settings (4.0.0: six steps)", rail[:len(steps)] == steps
      and steps == ["Dashboard", "Calendar", "Tasks", "Documents", "Graphics", "Shred", "Matrix && Outline", "Setup", "Drafts", "Submit", "Quick tools", "Team", "Settings"], rail)
w.go("prove"); app.processEvents()
check("the top bar names the page: Coverage is a tab of Matrix & Outline (4.3.0)", w.page_title.text() == "Matrix & Outline"
      and w.stack.currentWidget() is w.assign_page and not w.stepper.isVisibleTo(w) and w.page_tabs.isVisibleTo(w)
      and w._tab_keys[w.page_tabs.currentIndex()] == "prove" and w.step_btns["matrix"].isChecked())
check("no effort: the saved state says so", w.saved.text() == "No matrix")
# 3.15.0: visual hierarchy: three type sizes, card headers, status pills that never stretch, the page's group above it
check("3.15.0: three sizes: page title > card title > body", D.TYPE["display"] > D.TYPE["title"] > D.TYPE["body"] and D.TYPE["display"] - D.TYPE["title"] >= 6)
c = D.Card("A card", "what it holds"); c.add(D.label("x")); k = D.Card("Key", key=True)
check("... a card's title sits in its own header row; a key card is marked", c.head is not None and c.head.objectName() == "cardhead"
      and k.property("key") is True and D.Card().head is None)
check("... status pills are as tall as their text", w.saved.sizePolicy().verticalPolicy() == w.saved.sizePolicy().Policy.Fixed
      and w.saved.height() < 30, w.saved.height())
check("... the page's step shows above its title (3.96.0)", w.page_crumb.text() == "Step 3 of 6")
check("... menu entries in regular weight", "font-weight: 400" in D.qss(D.LIGHT).split("QPushButton#rail {")[1].split("}")[0])
w.toast("Saved"); app.processEvents()
check("a toast shows and names what happened", w.toaster.isVisible() and w.toaster.text() == "Saved")
w.close()
n = sum(checks)
print(f"QT DESIGN PASS ({n}/{len(checks)})" if n == len(checks) else f"QT DESIGN FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
