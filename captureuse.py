"""4.21.0: captured means delivered (claude/stationkeeper-evaluation-4.19.html, cause B). Where each thing said in the
shred goes: for every piece type and every mark on a piece, the pages that read it, in the words the pane shows under
the type chips ("Goes to: ..."). One list, so a page never promises a use that no code makes.

Each use names its proof: a program file and words in it that do the reading. tests/test_captureuse4210.py fails when a
type has no entry, when a page named here is not a page, or when the proof is gone from the file (the reader was taken
out and the list not corrected). Rules only (No AI)."""
import shredtypes as ST

# key: (the line the pane shows, [(page key, proof file, proof words)])
TYPES = {
    "requirement": ("Matrix & Outline > Place, then the Matrix and its section in the Setup",
                    [("place", "skqt/placepane.py", "ST.placed_any"), ("matrix", "shredtypes.py", '"Keep"'),
                     ("setups", "setupdoc.py", "def export_check")]),
    "instruction": ("Matrix & Outline > Place and Crosswalk, then the Matrix and its section in the Setup",
                    [("place", "skqt/placepane.py", "ST.placed_any"), ("crosswalk", "crosswalk.py", '"instruction"'),
                     ("setups", "setupdoc.py", '"instruction"')]),
    "evaluation": ("Shred > Evaluation Criteria and Matrix & Outline > Crosswalk",
                   [("evalcrit", "skqt/evalpage.py", "ST.types_of"), ("crosswalk", "crosswalk.py", '"evaluation"')]),
    "deliverable": ("Matrix & Outline > Place, and the deliverable you pick for it (Overview > Deliverables)",
                    [("place", "skqt/placepane.py", "ST.placed_any"), ("deliverables", "skqt/piececaptures.py", "Which deliverable")]),
    "rule": ("Shred > Submission Checklist. A rule the reader found on its own also checks Effort Formatting and Submit",
             [("requirements", "skqt/rulesdates.py", '"rule"')]),
    "date": ("Shred > Submission Checklist. Capture > Key date puts a date on the Overview's calendar",
             [("requirements", "skqt/rulesdates.py", '"date"')]),
    "information": ("Nowhere else: it stays in the shred as the customer's own text", []),
    "not_applicable": ("Nowhere: it is left out", []),
    "structure": ("Matrix & Outline > Outline: Read the Structure pieces... makes our required headings from it",
                  [("outline", "structfrom.py", 'ST.has(it, "structure")')]),
}

# marks on a piece or a heading that are not types
MARKS = {
    "heading": ("A heading at H1 to H9 sets where its pieces are found: the Matrix, the customer's outline and the Setup",
                [("matrix", "compliance.py", "Heading level"), ("outline", "rfpoutline.py", "hlevel"), ("setups", "headinglevels.py", "def found_under")]),
    "compliance": ("Compliance language marks the words in the Matrix, the outline file and the Setup",
                   [("matrix", "compliance.py", "it=it"), ("setups", "setupdoc.py", "it=")]),
    "page_limit": ("A page limit on a required heading is the section's pages: the Matrix's page allocation and Drafts > Status",
                   [("outline", "structfrom.py", "def deliver_limits"), ("drafts", "pagebudget.py", "def set_pages")]),
    "required_by": ("Source is checked on the Outline and in Submit > Report",
                    [("outline", "structfrom.py", "def drift"), ("finalcheck", "finalcheck.py", "The required structure")]),
}


# 4.29.4 (the capture audit; Nicholas 2026-11-13: "a label without a home or purpose means the decision is lost"): every
# capture in Shred's Capture menu, where it is kept in the words the menu shows, and the page that reads it with its
# proof. tests/test_captureuse4210.py fails when a capture has no entry or its reader is gone.
CAPTURES = {
    "contact": ("the Overview's Customer card", [("overview", "skqt/overviewpage.py", "rec.contacts()")]),
    "submit": ("Shred > Submission Checklist", [("requirements", "skqt/custdocs.py", "c.reg.rows()")]),
    "format": ("Shred > Submission Checklist", [("requirements", "skqt/custdocs.py", "c.reg.rows()")]),
    "acronym": ("Shred > Acronyms > Effort list", [("acrlist", "skqt/effortlistpage.py", "self.L.rows")]),
    "question": ("Customer Q&A", [("custqa", "skqt/custqapage.py", "Q.items(rec)")]),
    "keydate": ("Calendar", [("calendar", "skqt/calendarpage.py", "st.calendar(")]),
    "objective": ("the Matrix's Customer objective column and each section's kickoff sheet",
                  [("matrix", "matrixdesign.py", '"objective"'), ("setups", "kickoff.py", '"objectives"')]),
    "keypoint": ("the Matrix's Key points column and each section's kickoff sheet",
                 [("matrix", "matrixdesign.py", '"keypoints"'), ("setups", "kickoff.py", '"keypoints"')]),
    "graphic": ("Documents > Graphics, as a graphic need", [("graphics", "skqt/graphicspage.py", "GX.items(")]),
    "factor": ("Shred > Evaluation Criteria", [("evalcrit", "skqt/evalpage.py", "F.factors(r)")]),
    "pagelimit": ("Shred > Submission Checklist, and the section's pages on Drafts > Status",
                  [("requirements", "skqt/custdocs.py", "c.reg.rows()"), ("drafts", "pagebudget.py", '"Page limit"')]),
    "deliverable": ("Overview > Deliverables", [("deliverables", "skqt/custdocs.py", "DL.items(")]),
    "detail": ("the Overview's banner, under the effort's name", [("overview", "skqt/brandview.py", "BR.identity(rec)")]),
    "hot": ("Shred > Evaluation Criteria, under Hot buttons", [("evalcrit", "skqt/evalpage.py", "F.hot_buttons(r)")]),
    "other": ("Shred > Submission Checklist", [("requirements", "skqt/rulesdates.py", "Other submission detail")]),
    "written": ("Submit > Final Checks, under The RFP's written rules", [("checks", "skqt/checkspage.py", "The RFP's written rules")]),
    "unit": ("Settings > Units of measurement", [("settings", "skqt/unitsview.py", "import units")]),
}


def capture_line(key):
    """Where a capture is kept, as the Capture menu says it ("" for a capture the list does not know: an effort's own)."""
    return CAPTURES.get(key, ("", []))[0]


def line(keys, names=None):
    """'Goes to: ...' for the pane, '' for a piece with no type. names: {key: the type's name as the team shows it}."""
    names = names or {}
    got = [TYPES[k][0] for k in ST.KEYS if k in keys and k in TYPES]
    if not got:
        return ""
    if len(got) == 1:
        return "Goes to: " + got[0] + "."
    return "Goes to: " + "; ".join(f"{names.get(k, k.replace('_', ' ').capitalize())}: {TYPES[k][0]}"
                                   for k in ST.KEYS if k in keys and k in TYPES) + "."


def pages():
    """Every page key the list names."""
    return sorted({p for _say, uses in list(TYPES.values()) + list(MARKS.values()) + list(CAPTURES.values()) for p, _f, _w in uses})
