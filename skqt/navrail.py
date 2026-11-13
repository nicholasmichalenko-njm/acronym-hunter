"""The menu as the effort's path (3.96.0; canvas "Navigation", boards 1 and 3; claude/stationkeeper-navigation-3.93.md):
the effort switcher at the top (another effort, All Efforts, My Work, Your Tools); the Dashboard and the steps (4.0.0: six),
each with what is left (done, a count, next, a date); Team and Settings at the foot; Ctrl+K goes to any page or tool by
name. Inside the Shred step its tabs are a visual stepper with counts (4.0.0: Extract, Requirements, Acros & Abs, Acro List) and
its other pages are ways to see it (Our structure, List, Sort, L to M, Coverage). Every page in a step ends with
one next step (the bar at the bottom). navsteps holds the rules; nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

import diag
import shredwords as SW
import navsteps as NS
from . import design as D

# the Shred step's ways to see it: (page, label, the Shred page's own view or None). 4.0.0: the Matrix is Matrix & Outline's
VIEWS = (("assign", "Page", None), ("shredlist", "List", None))   # 4.19.0: List is the shred by the customer's structure   # 4.3.0: placing, L to M and
VIEW_OF = {"assign": "assign", "shredlist": "shredlist"}  # Coverage: Matrix & Outline
# 4.0.0: the Shred step's tabs as a stepper: (page, label)
CHIPS = (("assign", "Requirements"), ("requirements", "Rules & Dates"), ("evalcrit", "Evaluation"), ("acronyms", "Acros & Abs"))
CHIP_OF = {"acrlist": "acronyms", "lists": "acronyms"}   # 4.1.0: no Extract; Rules & Dates and Evaluation moved in; the Acro List
                                                          # opens from Acros & Abs
STEP_TITLES = {"home": ("Dashboard", "Where the effort is, what is left, and your next step"),
               "library": ("Documents", "The solicitation package: complete, current and readable"),
               "assign": ("Shred", "What every piece of the customer's text is, and its acros and abs"),
               "matrix": ("Matrix & Outline", "What we answer, and where in our structure"),
               "setups": ("Setup", "Who writes what, when and how long; the setup in Word"),
               "drafts": ("Drafts", "The team's drafts read back: where each section stands"),
               "finalcheck": ("Submit", "The last checks, then what happens after"),
               "graphics": ("Graphics", "Every graphic, the customer's and ours: its version, its words read, its acros and abs swept"),
               "redline": ("Prepare for Redline", "A Word file of each PDF and picture in Documents, with a reviewer's comments placed as tracked changes; checked word for word; the exceptions table")}


class ClickFrame(QFrame):
    """A card or chip that opens something when clicked (a frame, so its layout sets its size)."""
    from PySide6.QtCore import Signal
    clicked = Signal()

    def __init__(self, name):
        super().__init__()
        self.setObjectName(name); self.setCursor(Qt.PointingHandCursor)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(e)

    def click(self):
        self.clicked.emit()


def _circle(n, state, t):
    if state == "done":
        return f"background:{t['ok']};color:#FFFFFF;border:none;"
    if state == "now":
        return f"background:{t['rail_sel_bar']};color:#06101F;border:none;"
    return f"background:transparent;color:{t['rail_text']};border:2px solid #3A4B66;"


SUB = {"redline": "Documents", "graphics": "Documents"}   # 4.25.5: Graphics           # 4.12.0: a menu entry that sits under another (Redline under Documents), indented


class StepButton(QPushButton):
    """A menu entry: the step's number in a circle, its name, and what is left on the right."""
    def __init__(self, key, text, n=None):
        super().__init__(text.replace("&", "&&"))
        self.key, self.n = key, n
        self.setObjectName("rail"); self.setCheckable(True)
        self.setProperty("path", n is not None or key == "home")
        if n is not None or key == "home":
            self.setStyleSheet("QPushButton#rail { padding-left: 42px; }")
        elif key in SUB:                                       # 4.12.0: under its entry, past the step numbers
            self.setStyleSheet("QPushButton#rail { padding-left: 58px; font-size: 12px; }")
            self.setToolTip(f"Part of {SUB[key]}")
        h = QHBoxLayout(self); h.setContentsMargins(8, 0, D.SPACE["m"], 0); h.setSpacing(0)
        self.circle = QLabel("◎" if key == "home" else str(n or "")); self.circle.setFixedSize(24, 24)
        self.circle.setAlignment(Qt.AlignCenter); self.circle.setObjectName("railStepNo")
        self.circle.setVisible(n is not None or key == "home")
        h.addWidget(self.circle, 0, Qt.AlignVCenter); h.addStretch(1)
        self.badge = QLabel(""); self.badge.setObjectName("railBadge"); self.badge.setVisible(False)
        h.addWidget(self.badge, 0, Qt.AlignVCenter)
        self.stage_dot = QLabel(); self.stage_dot.setFixedSize(8, 8); self.stage_dot.setVisible(False)
        h.addWidget(self.stage_dot, 0, Qt.AlignVCenter)
        self.set_state("later", "")

    def set_state(self, state, badge):
        t = D.tokens()
        self.state = state
        if self.key == "home":
            self.circle.setStyleSheet(f"QLabel#railStepNo{{border:2px solid {t['rail_sel_bar']};border-radius:12px;color:{t['rail_sel_bar']};"
                                      "font-size:11px;font-weight:700;background:transparent;}")
        else:
            self.circle.setStyleSheet("QLabel#railStepNo{border-radius:12px;font-size:11px;font-weight:700;" + _circle(self.n, state, t) + "}")
        col = {"done": t["ok"], "now": t["warn"]}.get(state, "#8796AB")
        self.badge.setText(badge or "")
        self.badge.setVisible(bool(badge))
        self.badge.setStyleSheet(f"QLabel#railBadge{{color:{col};font-size:11px;background:transparent;}}")


def build(w, rv, rail, beta):
    """The menu's entries into the rail's layout; w.step_btns maps each entry to its button."""
    w.steps_now = []
    head = QLabel("THE EFFORT'S PATH"); head.setObjectName("railPathHead")
    head.setStyleSheet("QLabel#railPathHead{color:#9FB1C9;font-size:11px;letter-spacing:1px;padding:10px 6px 2px 6px;background:transparent;}")
    rv.addWidget(head)
    w.group_heads, w.group_items = {}, {}
    for gi, (group, items) in enumerate(rail):
        if gi == 1:
            rv.addStretch(1)
            rule = QFrame(); rule.setFixedHeight(1); rule.setStyleSheet("background:#22344F;"); rv.addWidget(rule)
        w.group_heads[group] = head if gi == 0 else None
        w.group_items[group] = []
        for key, text in items:
            n = NS_NUM.get(key)
            b = StepButton(key, text, n)
            if key in beta:
                b.setToolTip("Beta: still being proven on real documents")
            b.clicked.connect(lambda _=False, k=key: w.rail_go(k))
            w.steps.addButton(b); w.step_btns[key] = b
            rv.addWidget(b); w.group_items[group].append(b)
    hint = QLabel("Ctrl+K  Go to any page or tool"); hint.setObjectName("railHint")
    hint.setStyleSheet("QLabel#railHint{color:#8EA2BD;font-size:11px;padding:4px 10px;background:transparent;}")
    rv.addWidget(hint)
    w.rail_hint = hint


NS_NUM = {k: i for i, (k, _n, _w) in enumerate(NS.STEPS, 1)}


def refresh_steps(w, force=False):
    """What is left on each step, in the menu (and for the bar at the bottom and the Dashboard). Worked out again at
    most every two seconds while the same effort is open, unless forced."""
    import time
    key = (w.effort_name if w.ws is not None else "", id(w.review.M) if getattr(w, "review", None) is not None else 0)
    last = getattr(w, "_steps_at", None)
    if not force and last and last[0] == key and time.monotonic() - last[1] < 2.0:
        return w.steps_now
    w._steps_at = (key, time.monotonic())
    sts = []
    w.path_facts = None
    if w.ws is not None:
        try:
            acr = None
            ses = getattr(getattr(w, "acronym_page", None), "session", None)
            if ses is not None:
                c = ses.counts()
                acr = c.get("choice", 0) + c.get("candidate", 0)
            import menufocus as MF
            from .modes import settings
            f = NS.facts(w.ws, w.effort_path, w.review.M if w.review is not None else None, acr,
                         drafts_on="drafts" not in MF.hidden(settings()))
            sts = NS.steps(f)
            w.path_facts = f
        except Exception:  # noqa: BLE001  the menu must never stop the window
            diag.swallowed()
    w.steps_now = sts
    by = {s["key"]: s for s in sts}
    for key, b in w.step_btns.items():
        s = by.get(key)
        b.set_state(s["state"] if s else "later", NS.menu_badge(s) if s else "")
    return sts


def refresh_access(w, rail_of, members):
    """Grey (or hide, when the person asked) the entries that are not for this person's role."""
    import roleaccess as RA
    import menufocus as MF
    from .modes import settings
    prof, _src = w.profile()
    hide = bool((settings() or {}).get("hide_other_roles"))
    aside = MF.hidden(settings())
    for key, b in w.step_btns.items():
        ok = any(RA.allowed(prof, k) for k in members(key))
        b.setProperty("offrole", not ok)
        b.style().unpolish(b); b.style().polish(b)
        b.setToolTip("" if ok else f"For {', '.join(RA.roles_for(key))}. Your role here: {prof}.")
        b.setVisible((ok or not hide) and key not in aside)
    refresh_stage_tools(w, rail_of, prof)
    refresh_steps(w)
    return prof


def refresh_stage_tools(w, rail_of, prof=None):
    """The entries holding the tools the effort's stage needs get a dot in the stage's color; the effort and its stage
    show in the switcher at the top of the menu."""
    import roleaccess as RA
    import stagecolors as SC
    from .modes import settings
    st = settings() or {}
    tools, color, name = [], "", ""
    if w.ws is not None:
        try:
            import effortrec as _R
            r = _R.Record(w.ws.root)
            cur = r.stages[r.index()]
            color, name = SC.color_of(cur, r.index()), cur["name"]
            if st.get("stage_tools", True):
                tools = list(dict.fromkeys(rail_of.get(k, k) for k in RA.stage_tools(cur)))
                tools = [k for k in tools if k in w.step_btns]
        except Exception:  # noqa: BLE001
            diag.swallowed()
    w.rail_effort.set(w.effort_name if w.ws is not None else "", name, color)
    w.stage_tools_now = tools
    for k, b in w.step_btns.items():
        on = k in tools
        b.stage_dot.setVisible(on)
        b.stage_dot.setStyleSheet(f"background:{color};border-radius:4px;" if on else "")
        if on:
            b.setToolTip(" ".join(x for x in (b.toolTip(), f"Tools for {name} are here.") if x))
    return tools


# ------------------------------------------------------------------ inside a step: the stepper, the views, the bar
class Stepper(QWidget):
    """The Shred step's tabs as steps (4.0.0; Review's until 3.98.0): each with its number, its name and a count; done ones
    in green, the current outlined."""
    def __init__(self, w):
        super().__init__()
        self.w = w
        from .adaptive import FlowLayout
        from PySide6.QtWidgets import QSizePolicy
        fl = FlowLayout(self, 10); fl.setContentsMargins(0, 6, 0, 6)       # the views wrap under the steps when narrow
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        steps = QWidget(); h = QHBoxLayout(steps); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(0)
        fl.addWidget(steps)
        self.chips = {}
        for i, (k, label) in enumerate(CHIPS, 1):
            if i > 1:
                ln = QFrame(); ln.setFixedSize(18, 2); ln.setObjectName("stepLine"); h.addWidget(ln, 0, Qt.AlignVCenter)
                self.chips[k + ":line"] = ln
            b = ClickFrame("stepChip")
            bl = QHBoxLayout(b); bl.setContentsMargins(6, 3, 10, 3); bl.setSpacing(6)
            no = QLabel(str(i)); no.setFixedSize(18, 18); no.setAlignment(Qt.AlignCenter); no.setObjectName("stepNo")
            nm = QLabel(label); nm.setObjectName("stepName")
            ct = QLabel(""); ct.setObjectName("stepCount")
            for x in (no, nm, ct):
                bl.addWidget(x); x.setAttribute(Qt.WA_TransparentForMouseEvents)
            b.no, b.nm, b.ct = no, nm, ct
            b.clicked.connect(lambda key=k: w.go(key))
            h.addWidget(b); self.chips[k] = b
        see = QWidget(); vh = QHBoxLayout(see); vh.setContentsMargins(0, 0, 0, 0); vh.setSpacing(8)
        vh.addWidget(D.label("See it as", "muted", wrap=False))
        fl.addStretch(); fl.addWidget(see)
        self.views = {}
        seg = QFrame(); seg.setObjectName("viewSeg"); sh = QHBoxLayout(seg); sh.setContentsMargins(0, 0, 0, 0); sh.setSpacing(0)
        for k, label, _v in VIEWS:
            b = QPushButton(label); b.setCheckable(True); b.setObjectName("viewBtn"); b.setCursor(Qt.PointingHandCursor)
            b.setToolTip({"assign": "The customer's pages, each piece boxed",
                          "shredlist": "Every piece under the customer's headings, with what is decided"}[k])
            b.clicked.connect(lambda _=False, key=k: self.see(key))
            sh.addWidget(b); self.views[k] = b
        vh.addWidget(seg)

    def see(self, key):
        """A way to see the shred: the page or the list (4.19.0; 4.3.0: placing is Matrix & Outline's)."""
        ok = self.w.go(key)
        if key == "assign" and ok is not False:
            self.show_for("assign")
        return ok

    def view_now(self, step):
        return VIEW_OF.get(step)

    def counts(self):
        f = getattr(self.w, "path_facts", None) or {}
        r = f.get("reqs")
        acr = f.get("acronyms") or 0
        tot = f.get("acr_total") or 0
        rv = getattr(self.w, "review", None)
        by = {}
        if rv is not None:                           # 4.1.0: the pieces on Rules & Dates and Evaluation
            import shredtypes as ST
            by = ST.counts(rv.M.items)[1]
        nr, ne = by.get("rule", 0) + by.get("date", 0), by.get("evaluation", 0)
        return {"assign": (SW.left(r["undecided"]) if r else SW.NONE,
                           "warn" if r and r["undecided"] else "done" if r else "todo"),
                "requirements": (f"{nr} from the shred" if nr else "none from the shred", "done" if nr else "todo"),
                "evalcrit": (f"{ne} from the shred" if ne else "none from the shred", "done" if ne else "todo"),
                "acronyms": (f"{acr} to decide" if acr else f"{tot} in the list" if tot else "not scanned",
                             "warn" if acr else "done" if tot else "todo")}

    def show_for(self, step):
        t = D.tokens()
        step = CHIP_OF.get(step, step)
        cur = "assign" if step in VIEW_OF else step if step in self.chips else "assign"
        cs = self.counts()
        for k, _l in CHIPS:
            b = self.chips[k]
            text, st = cs[k]
            b.ct.setText(text)
            if k == cur:
                fg, bg, bd = t["accent"], t["accent_soft"], f"2px solid {t['accent']}"
            elif st == "done":
                fg, bg, bd = t["ok"], t["ok_soft"], "2px solid transparent"
            elif st == "warn":
                fg, bg, bd = t["warn"], t["warn_soft"], "2px solid transparent"
            else:
                fg, bg, bd = t["muted"], t["surface2"], "2px solid transparent"
            b.setStyleSheet(f"QFrame#stepChip{{background:{bg};border:{bd};border-radius:6px;}}"
                            f"QLabel#stepName{{color:{fg};font-weight:600;background:transparent;}}"
                            f"QLabel#stepCount{{color:{t['muted']};font-size:11px;background:transparent;}}"
                            f"QLabel#stepNo{{background:{fg};color:{t['bg']};border-radius:9px;font-size:10px;font-weight:700;}}")
            ln = self.chips.get(k + ":line")
            if ln is not None:
                ln.setStyleSheet(f"background:{t['ok'] if st == 'done' else t['border_strong']};")
        view = self.view_now(step)
        for k, b in self.views.items():
            b.setChecked(k == view)
            b.setStyleSheet(f"QPushButton#viewBtn{{border:1px solid {t['border_strong']};border-left:none;padding:4px 10px;"
                            f"background:{t['surface']};color:{t['text']};font-size:11px;border-radius:0;min-height:22px}}"
                            f"QPushButton#viewBtn:checked{{background:{t['accent_soft']};color:{t['accent']};font-weight:600}}")
        first = self.views[VIEWS[0][0]]
        first.setStyleSheet(first.styleSheet().replace("border-left:none;", ""))
        return cur


class NextBar(QFrame):
    """The bar at the bottom of a page in a step: what is left on this step, and the next step."""
    def __init__(self, w):
        super().__init__()
        self.w = w
        self.setObjectName("nextBar"); self.setFixedHeight(54)
        t = D.tokens()
        self.setStyleSheet(f"QFrame#nextBar{{background:{t['surface']};border-top:1px solid {t['border']};}}")
        h = QHBoxLayout(self); h.setContentsMargins(D.SPACE["xl"], 0, D.SPACE["xl"], 0); h.setSpacing(D.SPACE["m"])
        self.left = D.label("", "muted"); self.left.setMinimumWidth(80); h.addWidget(self.left, 1)
        self.when = D.label("When this is done", "muted", wrap=False); h.addWidget(self.when)
        self.btn = D.button("", "primary", lambda: self.go())
        h.addWidget(self.btn)
        self.target = ""
        self.setVisible(False)

    def show_for(self, step, rail_of):
        e = rail_of.get(step, step)
        if e == "assign":                           # 4.26.0 (answer 18): Shred's Next: Matrix & Outline is gone; it committed
            self.setVisible(False)                  # nothing the menu does not, and the menu says what is left
            return None
        b = NS.bar(e, self.w.steps_now) if self.w.ws is not None and e in NS.NAME else None
        if not b:
            self.setVisible(False)
            return None
        self.left.setText("On this step: " + b["left"])
        self.target = b["go"]
        self.btn.setText(b["button"].replace("&", "&&") + "  →"); self.btn.setVisible(bool(b["button"])); self.when.setVisible(bool(b["button"]))
        self.setVisible(True)
        return b

    def go(self):
        return self.w.rail_go(self.target) if self.target else None
