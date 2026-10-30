"""What changed, the moment a new version is added (2.98.0): one card per new version, "What changed in Amendment 1 of
the RFP": how many sentences changed, were added or removed; the submission rules it touches; the compliance
requirements it touches and their owners; new sentences not in the matrix yet; and how many changes are still to decide.
Review the changes opens Changes on that pair; Show on the page opens Review with the changes outlined. Rules only
(No AI); nothing leaves the PC."""
import os
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QVBoxLayout
import diag
from . import design as D


def after_added(host, made, lib, run=None):
    """After documents were added: the summary of each new version that has one before it. run: show the card (default:
    not while tests run). Returns the summaries (host.last_changes)."""
    import whatchanged as WC
    out = []
    M = host.review.M if host.review is not None else None
    for d, v in made or []:
        if d.get("category", "customer") != "customer":
            continue
        try:
            dd = lib.doc(d["id"]) or d
            s = WC.summary(lib, dd, v, M=M, data_dir=host.ws.root if host.ws is not None else "")
        except Exception:
            diag.swallowed()
            s = None
        if s:
            out.append(s)
        elif d.get("type") == "Amendment":               # an amendment that says what to change, not a reissue
            try:
                import amendinst as AI
                n = len(AI.instructions_of(lib, v))
                if n:
                    host.last_hint = (f"{d.get('name', 'The amendment')} holds {n} change instruction(s): Library > Apply its "
                                      "instructions makes the conformed version of the document it changes.")
                    host.status(host.last_hint)
            except Exception:
                diag.swallowed()
    host.last_changes = out
    if out:
        diag.activity("what_changed_shown", n=len(out))
        if run is None:
            run = not os.environ.get("AH_TEST")
        if run:
            for s in out:
                WhatChangedDialog(host, s).exec()
    return out


class WhatChangedDialog(QDialog):
    def __init__(self, host, s):
        super().__init__(host)
        self.host, self.s = host, s
        self.setWindowTitle(s["title"])
        self.setMinimumWidth(640)
        v = QVBoxLayout(self)
        v.addWidget(D.label(s["title"], "display"))
        v.addWidget(D.label(f"{s['from'].get('label', '')} ({s['from'].get('file', '')}) to {s['to'].get('label', '')} "
                            f"({s['to'].get('file', '')})", "muted"))
        tiles = QHBoxLayout(); v.addLayout(tiles)
        for n, word, tone in ((s["changed"], "changed", "warn"), (s["added"], "added", "ok"), (s["removed"], "removed", "crit"),
                              (len(s["rules"]), "submission rules", "accent"), (len(s["requirements"]), "requirements", "req"),
                              (s["to_decide"], "to decide", "head")):
            tiles.addWidget(D.Pill(f"{n} {word}", tone))
        tiles.addStretch(1)
        v.addWidget(D.label(s["text"]))
        if s["rules"]:
            v.addWidget(D.label("Submission rules it touches", "label"))
            for r in s["rules"][:6]:
                v.addWidget(D.label("•  " + r[:220]))
        if s["requirements"]:
            v.addWidget(D.label("Compliance requirements it touches" + (f" (owners: {', '.join(s['owners'][:6])})" if s["owners"] else ""), "label"))
            v.addWidget(D.label(", ".join(h["id"] for h in s["requirements"][:20]) + (" ..." if len(s["requirements"]) > 20 else ""), "mono"))
        if s["not_in_matrix"]:
            v.addWidget(D.label(f"{s['not_in_matrix']} new sentence(s) are not in the matrix yet: Read RFP > Add the new version, "
                                "or decide them in Changes.", "muted"))
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        rev = bb.addButton("Review the changes", QDialogButtonBox.ActionRole)
        rev.clicked.connect(lambda: self.review())
        page = bb.addButton("Show on the page", QDialogButtonBox.ActionRole)
        page.clicked.connect(lambda: self.on_page())
        page.setEnabled(self.host.review is not None and bool(self.host.review.M.path_of(s["to"].get("file", ""))))
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def review(self):
        self.accept()
        self.host.go("compare")
        return self.host.compare_page.show(self.s["doc"]["id"], self.s["from"]["id"], self.s["to"]["id"])

    def on_page(self):
        self.accept()
        self.host.go("assign")
        return self.host.assign_page.open_file(self.s["to"].get("file", ""))
