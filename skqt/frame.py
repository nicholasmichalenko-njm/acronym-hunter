"""The bar on every screen, made smaller (3.75.0, claude/stationkeeper-simplify-decisions-2026-11-06.md decision 5):
the title with its job sentence, Undo and Note stay; Issue or idea is a choice inside Note; Find a sentence shows on the
screens that hold sentences; the effort is switched from the effort's card at the top of the menu (the effort box is
gone from the bar); Saved sits in the status line; the mode shows only until it is set."""
from PySide6.QtWidgets import QMenu

SENTENCES = {"assign", "prove", "shredreq", "sort", "matrix", "crosswalk", "evalcrit", "read", "library", "docs", "shredacc",
             "compare", "impact", "requirements"}


def simplify(w):
    # 4.27.2 (Nicholas's recording 07:05): the button is Quick note and opens the note; Issue or idea is in Help (the
    # Guide's Issues and ideas..., Ctrl+Shift+I); Undo is Ctrl+Z, with a line at the foot and History (skqt/undoline)
    w.note_btn.setText("Quick note")
    w.note_btn.setToolTip("A note from this page, kept with the effort (Ctrl+Shift+N)")
    __import__("skqt.undoline", fromlist=["x"]).install(w)
    w.issue_btn.setVisible(False)
    w.effort_box.setVisible(False)
    w.statusBar().addPermanentWidget(w.saved)
    orig = w.show_mode_chip

    def show_mode_chip():
        orig()
        w.mode_chip.setVisible(not mode_set())
    w.show_mode_chip = show_mode_chip
    show_mode_chip()


def mode_set():
    try:
        import workmode as WM
        from .modes import mode
        return mode() in WM.NAMES
    except Exception:  # noqa: BLE001
        return True


def on_page(w, step):
    w.search.setVisible(step in SENTENCES)


def effort_menu(w):
    """The effort switcher at the top of the menu (3.96.0): the Dashboard, another effort, All Efforts, My Work, Your
    Tools."""
    m = QMenu(w)
    if w.effort_name:
        m.addAction("Overview", lambda: w.go("overview"))
    import unfiled as UF                                       # 4.27.2: Unfiled is a list under Quick tools, not an effort to switch to
    others = [w.effort_box.itemText(i) for i in range(w.effort_box.count())
              if w.effort_box.itemText(i) and w.effort_box.itemText(i) not in (w.effort_name, UF.NAME)]
    if others:
        m.addSeparator()
        for name in others[:15]:
            m.addAction("Switch to " + name, lambda n=name: switch(w, n))
    m.addSeparator()
    m.addAction("All Efforts", lambda: w.go("efforts"))
    import menufocus as MF
    from .modes import settings
    if "mywork" not in MF.hidden(settings()):                  # My Work is set aside for now
        m.addAction("My Work", lambda: w.go("mywork"))
    return m                                                   # 4.27.2: Quick tools is at the bottom of the menu


def switch(w, name):
    i = [w.effort_box.itemText(k) for k in range(w.effort_box.count())].index(name)
    w.effort_box.setCurrentIndex(i)
    w.effort_box.activated.emit(i)
