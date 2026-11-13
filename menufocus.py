"""Pages set aside (3.57.0, claude/stationkeeper-direction-decisions-2026-11-05.md): authoring and its tracking live in
SharePoint, so the pages that need authors or the proposal manager to work in the app are out of the menu for now. Their
code and tests stay; Settings > Roles and Preview tools > Show the pages set aside brings them back. One list, each with
the date and the reason; review it each quarter.

SET_ASIDE {key: (date, reason)}; OFF {key: (date, reason)} (3.89.0: out even when the set-aside pages show);
hidden(settings) -> set of keys out of the menu now."""

SET_ASIDE = {"mywork": ("2026-11-05", "Authors and the proposal manager track their work in SharePoint and Teams"),
             "truth": ("2026-11-05", "Authors check facts in the shared document"),
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
# 3.89.0 (Nicholas, 2026-11-09 07:24): off the menu and the feature lists even when the pages set aside are shown; the
# code and its tests stay, to revisit later
OFF = {"storyboards": ("2026-11-09", "Not needed for now; kept in the code to revisit later")}
# 4.0.0 (2026-11-10): Draft Status came back as the Drafts step's Status (claude/stationkeeper-steps-decisions-2026-11-10.md)


def hidden(settings=None):
    """The keys out of the menu: every one set aside, unless the person shows them, and every one turned off."""
    return set(OFF) if (settings or {}).get(SETTING) else set(SET_ASIDE) | set(OFF)


def names():
    """The set-aside pages' menu names, for the Settings line."""
    return ("My Work, Wall of Truth, Data calls, Color Reviews, Setup's "
            "Kickoff packets, and Overview's stages and gates, gate goals, win themes, All overviews and the "
            "Evaluation and hot buttons card")
