"""Pages set aside (3.57.0, claude/stationkeeper-direction-decisions-2026-11-05.md): authoring and its tracking live in
SharePoint, so the pages that need authors or the proposal manager to work in the app are out of the menu for now. Their
code and tests stay; Settings > Roles and Preview tools > Show the pages set aside brings them back. One list, each with
the date and the reason; review it each quarter.

SET_ASIDE {key: (date, reason)}; hidden(settings) -> set of keys out of the menu now."""

SET_ASIDE = {"mywork": ("2026-11-05", "Authors and the proposal manager track their work in SharePoint and Teams"),
             "drafts": ("2026-11-05", "Reading drafts back needs authors to write in the setup files the app made"),
             "truth": ("2026-11-05", "Authors check facts in the shared document"),
             "storyboards": ("2026-11-05", "Author workflow"),
             "datacalls": ("2026-11-05", "Coordinating authors and experts happens in SharePoint and email"),
             "reviews": ("2026-11-05", "Color review comments live in the shared document"),
             "kickoff": ("2026-11-05", "Author coordination (the Structure Builder's Kickoff packets button)")}
SETTING = "show_set_aside"


def hidden(settings=None):
    """The keys out of the menu: every one set aside, unless the person shows them."""
    return set() if (settings or {}).get(SETTING) else set(SET_ASIDE)


def names():
    """The set-aside pages' menu names, for the Settings line."""
    return ("My Work, Draft Status, Wall of Truth, Storyboards, Data calls, Color Reviews and the Structure Builder's "
            "Kickoff packets")
