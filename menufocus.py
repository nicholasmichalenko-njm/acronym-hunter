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
             "kickoff": ("2026-11-05", "Author coordination (Setup's Kickoff packets)"),
             # 3.61.0: the Effort Dashboard's proposal-management parts, not fleshed out for production
             "stages": ("2026-11-05", "Stages and gates are not managed in the app for now (the stage track, the stage pill, "
                                      "the Stages card, Move stage)"),
             "gategoals": ("2026-11-05", "Gate goals belong with stages and gates"),
             "alloverviews": ("2026-11-05", "The All overviews list of exported overviews"),
             "winthemes": ("2026-11-05", "Win themes (the card and the strip under the header)"),
             "evalcard": ("2026-11-05", "The Evaluation and hot buttons card; evaluation factors get their own page (3.63.0)")}
SETTING = "show_set_aside"


def hidden(settings=None):
    """The keys out of the menu: every one set aside, unless the person shows them."""
    return set() if (settings or {}).get(SETTING) else set(SET_ASIDE)


def names():
    """The set-aside pages' menu names, for the Settings line."""
    return ("My Work, Draft Status, Wall of Truth, Storyboards, Data calls, Color Reviews, Setup's "
            "Kickoff packets, and the Effort Dashboard's stages and gates, gate goals, win themes, All overviews and the "
            "Evaluation and hot buttons card")
