"""The words on screen for a term the effort leaves out (4.29.1, Nicholas 2026-11-13 answer 13; 4.56.0, UX decision 110
and his answer 8: "Not a term" is the one word, "ignore" is not used). The saved status keeps its name (Not a term,
effort.NOT); the screen says Not a term (the whole effort), Not a term on this page only (this place on this page) and
Not a term (the status).

shown(status)   the status as the screen says it
key(text)       the saved status for a word read back from the screen
relabel(combo)  a filter filled with saved names shows the screen's words
"""
NOT = "Not a term"
HERE, EFFORT, IGNORED, SHOW = "Not a term on this page only", "Not a term", "Not a term", "Show Not a term"
OLD = "Ignored"                       # the screen's word before 4.56.0, still read back


def shown(status):
    return IGNORED if status == NOT else status


def key(text):
    return NOT if text in (IGNORED, OLD) else text


def relabel(combo):
    i = combo.findText(NOT)
    if i >= 0:
        combo.setItemText(i, IGNORED)
    return combo
