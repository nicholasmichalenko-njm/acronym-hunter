"""Colors and the application style for the Qt edition, light and dark (follows Windows)."""
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import Qt

DEC = {"Keep": ("#16A34A", "Compliance requirement", "REQ"), "Context": ("#2563EB", "Supporting context", "SUPPORTS"),
       "Customer": ("#7E22CE", "The customer's (identified, not answered)", "CUSTOMER'S"),
       "Heading": ("#334155", "RFP heading", ""), "": ("#94A3B8", "Not used (not assigned)", "")}
CHIP_REQ = ("#DCFCE7", "#14532D")
CHIP_CTX = ("#DBEAFE", "#1E3A8A")


def is_dark(app):
    try:
        return app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return False


def chip(dark, kind):
    c = CHIP_REQ if kind == "req" else CHIP_CTX
    return c[1] if dark else c[0]


def apply(app):
    app.setStyle("Fusion")
    dark = is_dark(app)
    if dark:
        pal = QPalette()
        for role, col in ((QPalette.Window, "#0F172A"), (QPalette.WindowText, "#E2E8F0"), (QPalette.Base, "#111827"),
                          (QPalette.AlternateBase, "#1E293B"), (QPalette.Text, "#E2E8F0"), (QPalette.Button, "#1E293B"),
                          (QPalette.ButtonText, "#E2E8F0"), (QPalette.Highlight, "#2563EB"), (QPalette.HighlightedText, "#FFFFFF"),
                          (QPalette.ToolTipBase, "#1E293B"), (QPalette.ToolTipText, "#E2E8F0"), (QPalette.Link, "#93C5FD"),
                          (QPalette.PlaceholderText, "#64748B")):
            pal.setColor(role, QColor(col))
        app.setPalette(pal)
    app.setStyleSheet("""
        QToolBar { spacing: 4px; padding: 4px; }
        QPushButton#step { border: none; padding: 6px 14px; border-radius: 14px; font-weight: 600; }
        QPushButton#step:checked { background: #1E3A8A; color: white; }
        QPushButton#key { padding: 6px 12px; border-radius: 6px; font-weight: 600; color: white; border: none; }
        QLabel#kind { color: white; font-weight: bold; padding: 6px; border-radius: 6px; }
        QLabel#h { font-weight: bold; margin-top: 10px; }
        QLabel#muted { color: palette(placeholder-text); }
    """)
    return dark
