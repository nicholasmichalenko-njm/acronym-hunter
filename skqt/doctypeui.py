"""Document type and initial boxes (2.94.0): the type drop-down offers the team's types (Settings > Document types),
and the initial follows the type until the person types their own."""
from PySide6.QtWidgets import QComboBox
import docversions as DV


def type_box(current=""):
    cb = QComboBox()
    cb.addItems(list(DV.DOC_TYPES))
    cur = DV.type_of(current)
    if cur and cb.findText(cur) < 0:                  # a type no longer listed stays visible for this document
        cb.addItem(cur)
    cb.setCurrentIndex(max(0, cb.findText(cur or DV.guess_type(""))))
    return cb


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
