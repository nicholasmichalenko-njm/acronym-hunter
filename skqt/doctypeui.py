"""Document type and initial boxes (2.94.0): the type drop-down offers the team's types (Settings > Document types),
and the initial follows the type until the person types their own. 4.24.0: the first line is Add a type...; Other is
no longer offered (a document that has it keeps it)."""
from PySide6.QtWidgets import QComboBox
import docversions as DV


ADD = "Add a type..."       # 4.24.0: the first line of every type box; it takes the place of Other


def _config_dir():
    from PySide6.QtWidgets import QApplication
    for w in QApplication.topLevelWidgets():
        if getattr(w, "config_dir", None):
            return w.config_dir
    import app_gui
    return app_gui.CONFIG_DIR


def _locked():
    try:
        import teampack as TP
        return bool(TP.locked(_config_dir(), "doctypes"))
    except Exception:  # noqa: BLE001
        return False


def _fill(cb, cur):
    cb.blockSignals(True)
    cb.clear()
    if not _locked():
        cb.addItem(ADD)
    cb.addItems([t for t in DV.DOC_TYPES if t != "Other" or t == cur])      # Other shows only on a document that has it
    if cur and cb.findText(cur) < 0:                  # a type no longer listed stays visible for this document
        cb.addItem(cur)
    cb.setCurrentIndex(max(0, cb.findText(cur or DV.guess_type(""))))
    cb.setProperty("sk_type", cb.currentText())
    cb.blockSignals(False)


def type_box(current=""):
    cb = QComboBox()
    _fill(cb, DV.type_of(current))
    cb.activated.connect(lambda _i: picked(cb))
    return cb


def picked(cb, answer=None):
    """A line was picked. Add a type... asks for the new type; anything else is remembered as the box's type.
    answer (tests): (name, initial) or None to cancel."""
    if cb.currentText() != ADD:
        cb.setProperty("sk_type", cb.currentText())
        return cb.currentText()
    got = add_type(cb, answer)
    back = got or cb.property("sk_type") or ""
    _fill(cb, back)
    cb.currentTextChanged.emit(cb.currentText())
    return got


def short_name(name):
    """The initial a new type starts with: a short name as it is (Annex), else the first letters of its words."""
    import doctypes as DT
    words = (name or "").split()
    if len(words) == 1 and len(words[0]) <= 6:
        return DT.clean_initial(words[0])
    return DT.clean_initial("".join(w[0] for w in words).upper())


def add_type(parent, answer=None):
    """Ask for a type's name and initial and add it to the team's types (Settings > Document types). Returns its name,
    or '' when cancelled. A name already listed is picked, not added twice."""
    import doctypes as DT
    if answer is None:
        from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLineEdit
        d = QDialog(parent); d.setWindowTitle("Add a type"); d.setMinimumWidth(420)
        f = QFormLayout(d)
        name = QLineEdit(); name.setPlaceholderText("Annex, Pricing template, Wage determination...")
        ini = QLineEdit(); ini.setMaxLength(6); ini.setPlaceholderText("Up to 6 letters and digits")
        follow_name = [True]
        ini.textEdited.connect(lambda _t: follow_name.__setitem__(0, False))
        name.textChanged.connect(lambda t: follow_name[0] and ini.setText(short_name(t)))
        f.addRow("Type", name); f.addRow("Initial", ini)
        bb = QDialogButtonBox(QDialogButtonBox.Cancel)
        ok = bb.addButton("Add the type", QDialogButtonBox.AcceptRole); ok.setEnabled(False)
        name.textChanged.connect(lambda t: ok.setEnabled(bool(t.strip())))
        bb.accepted.connect(d.accept); bb.rejected.connect(d.reject); f.addRow(bb)
        if d.exec() != QDialog.Accepted:
            return ""
        answer = (name.text(), ini.text())
    if not answer:
        return ""
    name = " ".join((answer[0] or "").split())[:40]
    if not name or name == ADD:
        return ""
    cfg = _config_dir()
    types = DT.load(cfg)["types"]
    for t in types:
        if t["name"].casefold() == name.casefold():
            return t["name"]
    new = {"name": name, "initial": DT.clean_initial(answer[1]) or short_name(name) or "X", "numbered": False, "matrix": False, "words": ""}
    at = next((i for i, t in enumerate(types) if t["name"] == "Other"), len(types))
    DT.save(cfg, types[:at] + [new] + types[at:])
    import diag
    diag.activity("qt_doctype_added")
    return name


def follow(ini, ty, suggest):
    """The initial box ini follows the type box ty: picking a type puts suggest(type) in, unless the person typed an
    initial of their own (emptying the box hands it back to the type)."""
    ini.setProperty("sk_typed", False)
    ini.textEdited.connect(lambda t: ini.setProperty("sk_typed", bool(t.strip())))

    def changed(t):
        if not ini.property("sk_typed"):
            ini.setText(suggest(t))
    ty.currentTextChanged.connect(changed)
    return changed
