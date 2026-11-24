"""An effort's page with no effort open (4.60.0; Nicholas 2026-11-23, Layout 1: the menu's entries never come or go
because an effort exists). The entry stays in the menu; its page says in one sentence what it is for and offers the one
way in, Open or create an effort. Overview is not here: with nothing open it shows the ways to start. Only the entry
itself is answered this way; a page under it that works with nothing open (What changed on any two files, Acronyms)
still opens. Text only."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget

from . import design as D

# menu entry -> the one sentence
SAY = {"library": "Documents holds an effort's files, each marked with what it is used for.",
       "graphics": "Graphics holds an effort's graphics, the customer's and ours.",
       "deliverables": "Deliverables lists everything an effort hands back to the customer, and whether it is ready.",
       "assign": "Shred says what every piece of the customer's documents is, for an effort. To shred one file without an "
                 "effort, use Quick tools.",
       "matrix": "Matrix shows each requirement of an effort and where our response answers it.",
       "outline": "Outline is the structure of an effort's response.",
       "setups": "Setup makes each author's starting draft for an effort.",
       "drafts": "Drafts reads an effort's drafts back and says where each section stands.",
       "redline": "Redlining makes a Word file of a customer's PDF for an effort, to mark up and return. To redline one file "
                  "without an effort, use Quick tools.",
       "finalcheck": "Submission Check checks an effort's volumes before they go.",
       "activity": "Effort Activity lists everything that happened in an effort, by day."}
BUTTON = "Open or create an effort"
ON = True        # a test of a page itself, with nothing open, turns this off


class NoEffortPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host, self.entry = host, ""
        v = QVBoxLayout(self); v.setAlignment(Qt.AlignCenter); v.setSpacing(D.SPACE["m"])
        self.title = D.label("No effort is open", "title", wrap=False); self.title.setAlignment(Qt.AlignCenter); v.addWidget(self.title)
        self.say = D.label("", "muted"); self.say.setAlignment(Qt.AlignCenter); self.say.setFixedWidth(460); v.addWidget(self.say, 0, Qt.AlignCenter)
        self.btn = D.button(BUTTON, "primary", lambda: self.host.go("efforts")); v.addWidget(self.btn, 0, Qt.AlignCenter)

    def show_for(self, entry):
        self.entry = entry
        self.say.setText(SAY[entry])
        self.say.setMinimumHeight(self.say.heightForWidth(460) + 4)
        return self


def wanted(host, entry):
    """This entry's page is the no-effort page now: nothing is open and the entry works on an effort."""
    return ON and host.ws is None and entry in SAY
