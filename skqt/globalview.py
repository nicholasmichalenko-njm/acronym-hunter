"""Settings > Team data > Global Standards (4.30.0; the Standards board of 2026-11-13, step 1): the version of the
foundation this PC is on, where it came from, what changed on this PC since, and its parts. Reading only for now:
publishing, linking a folder and installing a file come with step 2. Rules only (No AI); nothing leaves the PC."""
import diag
import globalstd as GS
from . import design as D


def add_card(page, v):
    page.gs_card = D.Card("Global Standards", "The foundation every effort starts from: formatting, rules, lists, styles, Quick "
                          "Parts, page layout, templates, acronyms, dictionaries, stages, roles, markings, document types "
                          "and the folder plan. One set, with a version number.")
    page.gs_text = page.gs_card.add(D.label("", None)); page.gs_text.setWordWrap(True)
    page.gs_parts = page.gs_card.add(D.label("", "muted")); page.gs_parts.setWordWrap(True)
    v.addWidget(page.gs_card)
    return page.gs_card


def show(page):
    """The line and the parts, read again. Returns the line."""
    try:
        cfg = page.host.config_dir
        page.gs_text.setText(GS.line(cfg))
        names = sorted(n for n, _m in GS.parts(cfg).values())
        page.gs_parts.setText(("Its parts on this PC: " + ", ".join(names) + ".") if names else "")
    except Exception:  # noqa: BLE001
        diag.swallowed()
    return page.gs_text.text()
