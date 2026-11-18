"""Reference text in the setup (4.55.0, UX decision 14; Nicholas 2026-11-17 21:12, "Behind More"): the nine kinds of
reference text the setup writes (the RFP's requirement and support text, the customer's own pieces, objectives, topics,
captures, library context, the proposal manager's direction and notes, leads and page limits), each with its style
name, Hidden and In the file. Set in one place, Effort Formatting > More > Reference text in the setup...; Make the setup
shows one line saying what will be used, with a link here. The rows moved from the Make dialog (setuppage, 3.24.0);
the options are kept where they were (setuptemplate.options and set_options: this effort's change to the profile's
content map). Rules only; nothing leaves the PC."""
from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QGridLayout, QLineEdit, QVBoxLayout

import diag
from . import design as D


def opts_now(host):
    """The options Make will use: the first volume's standard with this effort's changes (as Make reads them), else the
    effort's standard, else the kinds' defaults."""
    import setuptemplate as ST
    R = getattr(host, "review", None)
    M = R.M if R is not None else None
    std = None
    try:
        if M is not None and M.outline:
            info = host.efforts.get(host.effort_name) or {}
            pl = ST.plan(M, host.config_dir, host.ws, host.effort_name or "", info)
            std = pl[0]["std"] if pl else None
        if std is None and host.ws is not None:
            import prodrules as PRL
            std = PRL.for_effort(host.config_dir, host.ws)
    except Exception:  # noqa: BLE001  no standard yet: the kinds' defaults
        diag.swallowed()
    return ST.options(M, std)


def summary(opts):
    """"Reference text: N kinds in the file, M hidden." for the nine kinds."""
    import setuptemplate as ST
    kinds = [opts.get(k) or {} for k, *_r in ST.KINDS]
    inc = [o for o in kinds if o.get("include", True)]
    return f"Reference text: {len(inc)} kinds in the file, {sum(1 for o in inc if o.get('hidden'))} hidden."


class RefTextDialog(QDialog):
    """The nine rows: style name, Hidden, In the file. Save keeps them for this effort; Cancel changes nothing."""

    def __init__(self, parent, host):
        super().__init__(parent)
        import setuptemplate as ST
        self.host = host
        self.setWindowTitle("Reference text in the setup"); self.setMinimumWidth(680)
        opts = opts_now(host)
        v = QVBoxLayout(self)
        v.addWidget(D.label("Each kind goes in its own style. Hidden text shows only with Show/Hide on, so authors see the "
                            "response alone with it off. Type the name of one of your own styles to use it.", "muted"))
        g = QGridLayout(); v.addLayout(g)
        self.rows = {}
        for r, (k, label, _s, _c, _i) in enumerate(ST.KINDS):
            g.addWidget(D.label(label, None), r, 0)
            e = QLineEdit(opts[k]["style"]); g.addWidget(e, r, 1)
            cb = QCheckBox("Hidden"); cb.setChecked(opts[k]["hidden"]); g.addWidget(cb, r, 2)
            inc = QCheckBox("In the file"); inc.setChecked(opts[k].get("include", True)); g.addWidget(inc, r, 3)
            self.rows[k] = (e, cb, inc)
        self.opts = opts
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.b_save = bb.button(QDialogButtonBox.Save)
        bb.accepted.connect(lambda: (self.save(), self.accept())); bb.rejected.connect(self.reject)
        v.addWidget(bb)
        R = getattr(host, "review", None)
        self.b_save.setEnabled(host.ws is not None or R is not None)

    def values(self):
        out = {k: dict(o) for k, o in self.opts.items()}
        for k, (e, cb, inc) in self.rows.items():
            out[k] = dict(out.get(k) or {}, style=e.text().strip() or k, hidden=cb.isChecked(), include=inc.isChecked())
        return out

    def save(self):
        """Kept where Make kept them: this effort's change to the profile's content map (or with the matrix)."""
        import setuptemplate as ST
        R = getattr(self.host, "review", None)
        M = R.M if R is not None else None
        vals = self.values()
        if self.host.ws is not None:
            ST.set_options(M, vals, self.host.ws)
        elif M is not None:
            ST.set_options(M, vals)
        else:
            return None
        if M is not None:
            M.pending = True
        self.host.changed()
        diag.activity("reference_text_saved")
        self.host.toast("Reference text in the setup saved for this effort")
        return vals


def open_window(parent, host, modal=True):
    d = RefTextDialog(parent, host)
    if modal:
        d.exec()
    return d


def line(parent, host, after=None):
    """The one line for Make: what will be used, and Change in Effort Formatting (opens the window over the dialog;
    after() runs when it closes, to say the line again)."""
    lab = D.label("", None)
    lab.setOpenExternalLinks(False)

    def say():
        lab.setText(summary(opts_now(host)) + " <a href='reftext'>Change in Effort Formatting</a>")

    def go(_h):
        open_window(parent, host)
        say()
        if after is not None:
            after()
    lab.linkActivated.connect(go)
    say()
    lab.say = say
    return lab
