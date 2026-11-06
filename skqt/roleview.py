"""Roles and Preview tools in the window (3.13.0): the page shown instead of a tool that is for another role, or a
Preview tool the team has not turned on. It says what the tool does, who it is for, and how to get it."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget
import diag
import roleaccess as RA
from . import design as D


class NoticePage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        self.why = None
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["xl"], D.SPACE["xl"], D.SPACE["xl"], D.SPACE["xl"])
        self.card = D.Card("Tool", "")
        v.addWidget(self.card, 0, Qt.AlignTop)
        self.text = self.card.add(D.label("", None))
        self.does = self.card.add(D.label("", "muted"))
        row = QHBoxLayout(); row.setSpacing(D.SPACE["s"]); self.card.body.addLayout(row)
        self.act = D.button("", "primary", lambda: self.do_action())
        self.back = D.button("Back to the Effort Dashboard", None, lambda: self.host.go("home"))
        row.addWidget(self.act); row.addWidget(self.back); row.addStretch(1)
        v.addStretch(1)

    def show_for(self, why):
        from .mainwin import TITLES
        self.why = why
        step = why["step"]
        title, does = TITLES.get(step, (RA.PREVIEW.get(step, (step,))[0], ""))
        self.does.setText(f"{title}: {does}." if does else "")
        if why["kind"] == "preview":
            name, what = RA.PREVIEW[step]
            pm = why["profile"] == RA.PM
            self.card.title.setText(f"{name} is in Preview")
            self.text.setText(f"It {what}. It is still being proven on real documents, so it is off for this team until the "
                              "proposal manager turns it on. Your files are not touched either way."
                              + ("" if pm else " The proposal manager turns it on in Settings > Team defaults."))
            self.act.setText("Turn it on for this team"); self.act.setVisible(pm)
        else:
            roles = ", ".join(why["roles"])
            src = {"effort": "from People in this effort", "pm": "you are this effort's proposal manager",
                   "own": "your own choice in Customize... on the Effort Dashboard"}.get(why["source"], "")
            pm_name = self.pm_name()
            self.card.title.setText(f"{title} is for {roles}")
            self.text.setText(f"Your role here is {why['profile']} ({src}). "
                              + (f"Ask {pm_name or 'the proposal manager'} to change your role in People if you need it."
                                 if why["source"] == "effort" else
                                 "Change your role in Customize... if this is your work, or ask the proposal manager to set it "
                                 "in People."))
            self.act.setText("Change my role..."); self.act.setVisible(why["source"] == "own")
        return self.card.title.text()

    def pm_name(self):
        if self.host.ws is None:
            return ""
        try:
            import branding as BR
            import effortrec as R
            r = R.Record(self.host.ws.root)
            return BR.proposal_manager(r, BR.identity(r)) or ""
        except Exception:
            diag.swallowed()
            return ""

    def do_action(self, answer=None):
        """Preview: the proposal manager turns the tool on and it opens. Role: Customize opens (answer, tests: a role)."""
        why = self.why or {}
        if why.get("kind") == "preview":
            RA.set_preview(self.host.config_dir, why["step"], True)
            diag.activity("qt_preview_turned_on")
            self.host.toast(f"{RA.PREVIEW[why['step']][0]} is on for this team")
            return self.host.go("templates" if why["step"] == "template" else why["step"])   # 3.69.0
        hp = self.host.home_page
        if answer is not None:
            import branding as BR
            hp.customize({"role": answer, "order": BR.preset(answer)["order"], "hidden": BR.preset(answer)["hidden"]})
        elif hp.customize() is False:
            return False
        return self.host.go(why.get("step", "home"))


class RolesCard(D.Card):
    """Settings > Roles and Preview tools: your role and where it comes from, hiding other roles' tools, the stage's tools
    marked in the menu, and (for the proposal manager) which Preview tools are on for the team."""

    def __init__(self, host):
        super().__init__("Roles and Preview tools", "Your role decides which tools open; the others stay in the menu, greyed, "
                         "and say who they are for. Preview tools are off for the whole team until the proposal manager turns "
                         "them on.")
        from PySide6.QtWidgets import QCheckBox
        self.host = host
        self.role_text = self.add(D.label("", None))
        self.hide = QCheckBox("Hide the tools that are not for my role"); self.add(self.hide)
        self.hide.toggled.connect(lambda on: self.set_opt("hide_other_roles", on))
        self.stage = QCheckBox("Mark the stage's tools in the menu (a dot in the stage's color)"); self.add(self.stage)
        self.stage.toggled.connect(lambda on: self.set_opt("stage_tools", on))
        import menufocus as MF                                             # 3.57.0: pages set aside for now
        self.aside = QCheckBox("Show the pages set aside for now"); self.add(self.aside)
        self.aside.setToolTip(MF.names() + ": out of the menu while authoring and its tracking live in SharePoint. "
                              "Their work is kept.")
        self.aside.toggled.connect(lambda on: self.set_opt(MF.SETTING, on))
        self.add(D.label("Preview tools for this team", "label"))
        self.prev = {}
        for key, (name, what) in RA.PREVIEW.items():
            cb = QCheckBox(f"{name} (it {what})"); self.add(cb); self.prev[key] = cb
            cb.toggled.connect(lambda on, k=key: self.set_preview(k, on))
        self.prev_note = self.add(D.label("", "muted"))

    def set_opt(self, key, on):
        if getattr(self, "_filling", False):
            return
        from .modes import save
        save(**{key: bool(on)})
        self.host.refresh_access()

    def set_preview(self, key, on):
        if getattr(self, "_filling", False):
            return
        RA.set_preview(self.host.config_dir, key, on)
        diag.activity("qt_preview_set")
        self.host.toast(f"{RA.PREVIEW[key][0]} is {'on' if on else 'off'} for this team")

    def fill(self):
        from .modes import settings
        import teampack as TP
        st = settings() or {}
        prof, src = self.host.profile()
        self._filling = True
        self.role_text.setText(f"Your role: <b>{prof}</b> " + {"effort": "(from People in this effort)",
                               "pm": "(you are this effort's proposal manager)",
                               "own": "(your own choice: Customize... on the Effort Dashboard)"}.get(src, ""))
        self.hide.setChecked(bool(st.get("hide_other_roles")))
        self.stage.setChecked(bool(st.get("stage_tools", True)))
        self.aside.setChecked(bool(st.get("show_set_aside")))
        locked = TP.locked(self.host.config_dir, "access")
        for key, cb in self.prev.items():
            cb.setChecked(RA.preview_on(self.host.config_dir, key))
            cb.setEnabled(prof == RA.PM and not locked)
        self.prev_note.setText("Set by the team pack." if locked else
                               ("Only the proposal manager turns Preview tools on or off." if prof != RA.PM else
                                "A team pack (Team defaults) carries this choice to every PC."))
        self._filling = False
