"""3.73.0 offscreen: Symbols puts the clicked symbol where the insertion point is, in whichever box was clicked into last
(attached to the picker or not, a line or a paragraph box), and the picker belongs to the window being typed in, so a
dialog in front never blocks its clicks."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", tempfile.mkdtemp())
import app_gui as A  # noqa: F401
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget
from skqt import symbols as SYM

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


app = QApplication([])
win = QWidget(); v = QVBoxLayout(win)
a, b, para = QLineEdit("Kestrel"), QLineEdit("H O"), QPlainTextEdit("Delta v budget")
v.addWidget(a); v.addWidget(SYM.button(a)); v.addWidget(b); v.addWidget(para)
win.show(); win.activateWindow(); app.processEvents()


def click(picker, ch):
    btn = next(bb for c, bb in picker.buttons if c == ch) if any(c == ch for c, _b in picker.buttons) else None
    if btn is None:
        picker.q.setText(SYM.names_of(ch).split()[0] if SYM.names_of(ch) else ch); app.processEvents()
        btn = next(bb for c, bb in picker.buttons if c == ch)
    btn.click(); app.processEvents()


p = SYM.open_picker(a)
b.setFocus(); b.setCursorPosition(1); app.processEvents()
SYM._on_focus(None, b) if SYM._target() is not b else None       # offscreen focus is not always delivered
check("the box clicked into last is the target, attached or not", SYM._target() is b)
p.q.setText("subscript two"); app.processEvents()
click(p, "₂")
check("the symbol goes in at the insertion point", b.text() == "H₂ O" and b.cursorPosition() == 2, (b.text(), b.cursorPosition()))
c = para.textCursor(); c.setPosition(5); para.setTextCursor(c)
SYM._on_focus(None, para)
p.q.setText("delta"); app.processEvents()
click(p, "Δ")
check("a paragraph box too, at its insertion point", para.toPlainText() == "DeltaΔ v budget", para.toPlainText())
check("the picker's own search box is never the target", (SYM._on_focus(None, p.q), SYM._target())[1] is para)
# ---- a dialog in front: the picker belongs to it
d = QDialog(win); d.setModal(True); dv = QVBoxLayout(d)
e = QLineEdit("10 m/s"); dv.addWidget(e); dv.addWidget(SYM.button(e))
d.show(); app.processEvents()
p2 = SYM.open_picker(e)
check("opened from a dialog: the picker belongs to that dialog, so the dialog never blocks its clicks", p2.parent() is d and p2 is not p, p2.parent())
SYM._on_focus(None, e); e.setCursorPosition(2)
p2.q.setText("superscript two"); app.processEvents()
click(p2, "²")
check("... and its symbol goes in where the cursor is", e.text() == "10² m/s", e.text())
d.close(); app.processEvents()
p3 = SYM.open_picker(a)
check("back in the main window: the picker belongs to it again", p3.parent() is win)

print(f"QT SYMBOLS 373 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
