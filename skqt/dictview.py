"""Settings > Custom dictionaries (3.0.4): the team's word lists for Word's spelling check. Pick a dictionary, see and search
every word in it, add or remove words, import a Word .dic, add the open effort's approved acronyms, and export a .dic for
Word named with the date (every export is also kept, dated, in the data folder). Kept with the app for every effort;
the backups carry them. Nothing leaves the PC."""
import os
import re
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QInputDialog, QLineEdit, QListWidget,
                               QMessageBox)
import diag
import customdict as CD
from . import design as D


class DictionariesCard(D.Card):
    def __init__(self, host):
        super().__init__("Custom dictionaries",
                         "Your team's words for Word's spelling check: acronyms, product and program names. Export one as a "
                         ".dic file and add it in Word (File > Options > Proofing > Custom Dictionaries).",
                         actions=[D.button("+ Dictionary...", None, lambda: self.new_dict()),
                                  D.button("Export for Word...", "primary", lambda: self.export())])
        self.host = host
        top = QHBoxLayout(); top.setSpacing(D.SPACE["s"])
        self.pick = QComboBox(); self.pick.setMinimumWidth(220); self.pick.currentIndexChanged.connect(lambda _i: self.show_words())
        top.addWidget(D.label("Dictionary", "label", wrap=False)); top.addWidget(self.pick)
        self.rename_btn = D.button("Rename...", "ghost", lambda: self.rename())
        self.remove_btn = D.button("Remove dictionary", "ghost", lambda: self.remove_dict())
        top.addWidget(self.rename_btn); top.addWidget(self.remove_btn); top.addStretch(1)
        self.body.addLayout(top)
        srow = QHBoxLayout(); srow.setSpacing(D.SPACE["s"])
        self.find = QLineEdit(); self.find.setPlaceholderText("Search the words..."); self.find.setClearButtonEnabled(True)
        self.find.textChanged.connect(lambda _t: self.show_words())
        self.count = D.label("", "muted", wrap=False)
        srow.addWidget(self.find, 1); srow.addWidget(self.count)
        self.body.addLayout(srow)
        self.words = QListWidget(); self.words.setSelectionMode(QAbstractItemView.ExtendedSelection); self.words.setMinimumHeight(220)
        self.words.itemDoubleClicked.connect(lambda it: self.edit_word(it.text()))
        self.words.setToolTip("Double-click a word to change its spelling; Ctrl+click or Shift+click to pick several")
        self.add(self.words)
        arow = QHBoxLayout(); arow.setSpacing(D.SPACE["s"])
        self.new_words = QLineEdit(); self.new_words.setPlaceholderText("Words to add, with spaces or commas between them")
        self.new_words.returnPressed.connect(lambda: self.add_typed())
        arow.addWidget(self.new_words, 1)
        arow.addWidget(D.button("Add", None, lambda: self.add_typed()))
        arow.addWidget(D.button("Remove selected", "ghost", lambda: self.remove_selected()))
        self.body.addLayout(arow)
        brow = QHBoxLayout(); brow.setSpacing(D.SPACE["s"])
        brow.addWidget(D.button("Import a .dic...", None, lambda: self.import_dic(), "Add the words of a Word custom dictionary"))
        self.effort_btn = D.button("Add the effort's acronyms", None, lambda: self.add_effort(),
                                   "The open effort's approved acronyms (from its acronym list)")
        brow.addWidget(self.effort_btn); brow.addStretch(1)
        self.with_effort = QCheckBox("Effort's name in the file name"); self.with_effort.setToolTip(
            "Export for Word... names the file with the dictionary, the open effort and the date")
        brow.addWidget(self.with_effort)
        self.body.addLayout(brow)
        self.note = self.add(D.label("", "muted")); self.note.setWordWrap(True)
        self.store = None
        self.refresh()

    # ------------------------------------------------------------ state
    def refresh(self, keep=None):
        self.store = CD.Store(self.host.config_dir)
        cur = keep if keep is not None else self.current_id()
        self.pick.blockSignals(True); self.pick.clear()
        for d in self.store.dicts:
            self.pick.addItem(d["name"], d["id"])
        if cur:
            self.pick.setCurrentIndex(max(0, self.pick.findData(cur)))
        self.pick.blockSignals(False)
        self.show_words()

    def current_id(self):
        return self.pick.currentData() if self.pick.count() else None

    def current(self):
        return self.store.get(self.current_id()) if self.store is not None and self.current_id() else None

    def show_words(self):
        d = self.current()
        on = d is not None
        for w in (self.rename_btn, self.remove_btn, self.words, self.new_words, self.find):
            w.setEnabled(on)
        self.effort_btn.setEnabled(on and self.host.ws is not None)
        self.with_effort.setEnabled(self.host.ws is not None)
        self.words.clear()
        if not on:
            self.count.setText("")
            self.note.setText("No dictionaries yet. + Dictionary... starts one; Import a .dic... can then fill it from Word's.")
            return
        q = self.find.text().strip().casefold()
        shown = [w for w in d["words"] if q in w.casefold()]
        self.words.addItems(shown)
        self.count.setText(f"{len(shown)} of {len(d['words'])} words" if q else f"{len(d['words'])} words")
        last = (d.get("exports") or [None])[-1]
        self.note.setText(f"Last exported {last['at'].replace('T', ' ')}: {last['file']} ({last['words']} words). Each export is "
                          f"kept, dated, in {os.path.join('your data folder', CD.EXPORTS)}." if last else
                          "Not exported yet. Export for Word... writes the .dic (named with the date) and keeps a dated copy.")

    # ------------------------------------------------------------ dictionaries
    def new_dict(self, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self, "New dictionary", "Its name (for example: Sierra Space Custom):")
            if not ok:
                return ""
        did = self.store.add(name)
        if not did:
            self.host.status("Give it a name not already used.")
            return ""
        diag.activity("dict_created")
        self.refresh(did)
        return did

    def rename(self, name=None):
        d = self.current()
        if d is None:
            return False
        if name is None:
            name, ok = QInputDialog.getText(self, "Rename the dictionary", "Its new name:", text=d["name"])
            if not ok:
                return False
        ok = self.store.rename(d["id"], name)
        if not ok:
            self.host.status("Give it a name not already used.")
        self.refresh(d["id"])
        return ok

    def remove_dict(self, sure=None):
        d = self.current()
        if d is None:
            return False
        if sure is None:
            sure = QMessageBox.question(self, "Remove the dictionary", f"Remove {d['name']} and its {len(d['words'])} words? Files "
                                        "already exported stay where they are.") == QMessageBox.Yes
        if not sure:
            return False
        ok = self.store.remove(d["id"])
        diag.activity("dict_removed")
        self.refresh("")
        return ok

    # ------------------------------------------------------------ words
    def add_typed(self, text=None):
        d = self.current()
        text = self.new_words.text() if text is None else text
        words = [w for w in re.split(r"[\s,;]+", text or "") if w]
        if d is None or not words:
            return 0
        n = self.store.add_words(d["id"], words)
        self.new_words.clear()
        diag.activity("dict_words_added", n=n)
        self.host.status(f"{n} word(s) added to {d['name']}." if n else "Those words are already in it.")
        self.refresh(d["id"])
        return n

    def remove_selected(self, words=None):
        d = self.current()
        if d is None:
            return 0
        words = words if words is not None else [it.text() for it in self.words.selectedItems()]
        n = self.store.remove_words(d["id"], words)
        if n:
            diag.activity("dict_words_removed", n=n)
            self.host.status(f"{n} word(s) removed from {d['name']}.")
        self.refresh(d["id"])
        return n

    def edit_word(self, old, new=None):
        d = self.current()
        if d is None:
            return False
        if new is None:
            new, ok = QInputDialog.getText(self, "Change the word", "Its spelling:", text=old)
            if not ok:
                return False
        ok = self.store.replace_word(d["id"], old, new)
        if not ok:
            self.host.status("A dictionary word has no spaces in it.")
        self.refresh(d["id"])
        return ok

    def import_dic(self, path=None):
        d = self.current()
        if d is None:
            did = self.new_dict("Imported")
            d = self.store.get(did) if did else None
            if d is None:
                return 0
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, "A Word custom dictionary", os.path.expanduser("~"), "Word dictionary (*.dic);;Text (*.txt)")
            if not path:
                return 0
        try:
            words = CD.read_dic(path)
        except OSError:
            self.host.status("That file could not be read.")
            return 0
        n = self.store.add_words(d["id"], words)
        diag.activity("dict_imported", n=n)
        self.host.toast(f"{n} new word(s) from {os.path.basename(path)} ({len(words)} in the file)")
        self.refresh(d["id"])
        return n

    def add_effort(self):
        d = self.current()
        if d is None or self.host.ws is None:
            return 0
        lst = self.host.record_page.effort_list()
        words = CD.from_effort(lst) if lst is not None else []
        n = self.store.add_words(d["id"], words)
        diag.activity("dict_from_effort", n=n)
        self.host.toast(f"{n} new word(s) from {self.host.effort_name}'s approved acronyms" if words else
                        f"{self.host.effort_name} has no approved acronyms yet")
        self.refresh(d["id"])
        return n

    def export(self, path=None, with_effort=False):
        d = self.current()
        if d is None:
            self.host.status("Start a dictionary first (+ Dictionary...).")
            return ""
        import app_gui
        if path is None:
            with_effort = with_effort or self.with_effort.isChecked()
            name = self.store.export_name(d["id"], self.host.effort_name if (with_effort and self.host.ws is not None) else "")
            start = os.path.join(os.path.expanduser("~"), "Documents", name)
            path, _ = QFileDialog.getSaveFileName(self, "Export for Word", start, "Word dictionary (*.dic)")
            if not path:
                return ""
        n = self.store.export(d["id"], path, app_gui.DATA_DIR)
        diag.activity("dict_exported", n=n)
        self.host.toast(f"{d['name']}: {n} words in {os.path.basename(path)}")
        self.refresh(d["id"])
        return path
