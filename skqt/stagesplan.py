"""The stages plan on Effort Settings (4.80.0, step E3 of claude/stationkeeper-effort-settings-direction-2026-11-25.md):
the line of stages across the top of Stages and reviews (each stage a block with its planned dates, the current one
outlined), Add stage with a blank stage or one of the standard reviews and its one line of purpose, "Gate passed" with
its date, and who may change the plan: the effort's proposal manager, or anyone when none is named (187). Nothing
leaves the PC."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMenu, QVBoxLayout, QWidget

import effortrec as R
from . import design as D

# The standard reviews offered as starting choices only (the direction page; his own stage names stay the default).
STANDARD_REVIEWS = (
    ("Blue team", "strategy and solution, before writing"),
    ("Pink team", "storyboards and early draft"),
    ("Red team", "complete draft scored as the evaluator would"),
    ("Green team", "cost and price"),
    ("Gold team", "final approval to submit"),
    ("White glove", "final production proofread"),
)
NOTE = ("Double-click a name to rename it. Drag a stage still ahead to move it; right-click to remove one. "
        "The current stage moves on Overview.")
LOCKED = "Only the proposal manager changes stages"


def gate_short(gid):
    """The team's gate name, short: '' -> 'None'; 'Soft gate: warn and log' -> 'Soft'."""
    if not gid:
        return "None"
    name = R.GATES.get(gid, gid).split(":")[0].strip()
    return name[:-5].strip() if name.casefold().endswith(" gate") and len(name) > 5 else name


def passed_text(at, year=True):
    """'Gate passed Nov 20, 2026' from the time the effort moved on from the stage ('' when not passed)."""
    d = R.parse_date((at or "")[:10]) if at else None
    return (f"Gate passed {d.strftime('%b')} {d.day}" + (f", {d.year}" if year else "")) if d else ""


def passed_at(r, s):
    """When the gate of stage s was passed: the time the effort moved on from it, for a stage before the current one
    that has a gate ('' otherwise)."""
    if not s.get("gate") or r.state_of(s) != "done":
        return ""
    return s.get("ended", "") or ""


def plan_text(s):
    a, b = R.short_date(s.get("planned", "") or ""), R.short_date(s.get("planned_end", "") or "")
    return f"{a} to {b}" if a and b else (f"From {a}" if a else (f"Until {b}" if b else "No dates yet"))


def proposal_manager(r):
    import branding as BR
    try:
        return (BR.proposal_manager(r, BR.identity(r)) or "").strip()
    except Exception:  # noqa: BLE001
        return ""


def can_edit(r, me):
    """(True, '') when this person may change the stages plan: the effort's proposal manager, someone whose role on
    the effort says so, or anyone when no proposal manager is named; else (False, the line to show)."""
    pm = proposal_manager(r)
    me = (me or "").strip()
    if not pm:
        return True, ""
    if me and (me.casefold() == pm.casefold() or "proposal manager" in (r.role_of(me) or "").casefold()):
        return True, ""
    return False, (f"{LOCKED} ({pm}). " + (f"You are set as {me} on this PC." if me else
                                            "Customize... > I am sets who you are on this PC."))


def my_name():
    from .modes import settings
    return (settings() or {}).get("my_name", "")


class StageBlock(QFrame):
    clicked = Signal()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(e)


class StagesLine(QWidget):
    """The stages in order, one block each with its name and planned dates; the current one outlined; a passed gate
    with its date. Read here; the current stage moves on Overview. Clicking a block picks its row in the table."""
    picked = Signal(int)

    def __init__(self):
        super().__init__()
        self.row = QHBoxLayout(self); self.row.setContentsMargins(0, 0, 0, 0); self.row.setSpacing(D.SPACE["xs"])
        self.blocks = []

    def fill(self, r):
        while self.row.count():
            it = self.row.takeAt(0)
            if it.widget() is not None:
                it.widget().hide(); it.widget().deleteLater()
        self.blocks = []
        t = D.tokens()
        for i, s in enumerate(r.stages):
            st = r.state_of(s)
            f = StageBlock(); f.setObjectName("stageblock"); f.setCursor(Qt.PointingHandCursor)
            border = f"2px solid {t['accent']}" if st == "current" else f"1px solid {t['border']}"
            f.setStyleSheet(f"QFrame#stageblock{{background:{t['surface2'] if st == 'done' else t['surface']};"
                            f"border:{border};border-radius:{D.RADIUS['card']}px;}} QLabel{{background:transparent;}}")
            fv = QVBoxLayout(f); fv.setContentsMargins(D.SPACE["s"], D.SPACE["xs"], D.SPACE["s"], D.SPACE["xs"]); fv.setSpacing(0)
            name = D.label(s["name"]); name.setAlignment(Qt.AlignCenter)
            name.setStyleSheet("font-weight:600;" if st == "current" else ("color:%s;" % t["muted"] if st == "done" else ""))
            fv.addWidget(name)
            lines = [plan_text(s)]
            p = passed_text(passed_at(r, s), year=False)
            if p:
                lines.append(p)
            when = D.label("\n".join(lines)); when.setAlignment(Qt.AlignCenter)
            when.setStyleSheet(f"font-size:{D.TYPE['small']}pt;color:{t['muted']};")
            fv.addWidget(when)
            f.setToolTip(f"{s['name']}" + (": the current stage" if st == "current" else ""))
            f.setProperty("sk_state", st)
            f.clicked.connect(lambda i=i: self.picked.emit(i))
            self.row.addWidget(f, 1)
            self.blocks.append(f)

    def texts(self):
        """(tests) each block's words, top to bottom, and its state."""
        from PySide6.QtWidgets import QLabel
        return [(" | ".join(l.text() for l in b.findChildren(QLabel)), b.property("sk_state")) for b in self.blocks]


def add_menu(page):
    """Add stage: a blank stage, or one of the standard reviews with its one line of purpose."""
    m = QMenu(page)
    m.addAction("Blank stage", lambda: page.add_stage_here("New stage", rename=True))
    m.addSeparator()
    for name, why in STANDARD_REVIEWS:
        a = m.addAction(f"{name}: {why}", lambda n=name: page.add_stage_here(n))
        a.setData(name)
    return m


def build(page, v):
    """The line, the note with Add stage, on Effort Settings' Stages and reviews. Returns the note's row."""
    page.stages_line = StagesLine()
    page.stages_line.picked.connect(lambda i: page.stage_table.setCurrentCell(i, 0))
    v.addWidget(page.stages_line)
    srow = QHBoxLayout()
    page.stage_note = D.label(NOTE, "muted")
    srow.addWidget(page.stage_note, 1)
    page.add_stage_btn = D.button("Add stage", None, None, "Add a blank stage, or one of the standard reviews")
    page.add_stage_btn.setMenu(add_menu(page))
    srow.addWidget(page.add_stage_btn)
    v.addLayout(srow)
    return srow
