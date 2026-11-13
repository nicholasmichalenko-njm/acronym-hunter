"""The words on screen for a term the effort leaves out (4.29.1, Nicholas 2026-11-13 answer 13). The saved status keeps
its name (Not a term, effort.NOT); the screen says Ignore here (this place on this page), Ignore in this effort (the
whole effort) and Ignored (the status).

shown(status)   the status as the screen says it
key(text)       the saved status for a word read back from the screen
relabel(combo)  a filter filled with saved names shows the screen's words
"""
NOT = "Not a term"
HERE, EFFORT, IGNORED, SHOW = "Ignore here", "Ignore in this effort", "Ignored", "Show ignored"


def shown(status):
    return IGNORED if status == NOT else status


def key(text):
    return NOT if text == IGNORED else text


def relabel(combo):
    i = combo.findText(NOT)
    if i >= 0:
        combo.setItemText(i, IGNORED)
    return combo
