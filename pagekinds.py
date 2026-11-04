"""What kind of page a kept cover, title page or back cover is (3.40.0), so it is kept and edited as it was built and
never turned into another kind:

  flow    paragraphs in the page's flow with their spacing, then pictures in the text
  table   a table holds the text and logos
  placed  a background picture, text boxes or floating text blocks placed on the page

A placed page is edited in the layout editor (move, resize, Text on the page). Flow and table pages are edited in Word
(Edit in Word), so their paragraphs and tables stay paragraphs and tables. Read straight from the page file; rules only."""
import coverlayout as CL

KINDS = {"flow": ("A flow page", "paragraphs with their spacing, then pictures in the text"),
         "table": ("A table page", "a table holds the text and logos"),
         "placed": ("A placed page", "a background picture and text placed on it")}


def kind_of(data, std=None):
    """'flow', 'table' or 'placed' for a kept page's bytes ('' when it cannot be read)."""
    try:
        pieces = CL.read(data, std)["pieces"]
    except Exception:  # noqa: BLE001  an unreadable page has no kind
        return ""
    floating = [p for p in pieces if p.get("floating") and p["kind"] in ("picture", "textbox", "table", "shape")]
    placed_text = [p for p in pieces if p.get("floating") and p["kind"] in ("textbox", "table")]
    behind = [p for p in pieces if p.get("floating") and p.get("behind")]
    texts = [p for p in pieces if p["kind"] == "paragraph" and (p.get("text") or "").strip()]
    in_flow = [p for p in texts if p.get("where") == "the page"]
    in_cells = [p for p in texts if p.get("where") == "a table cell"]
    inline_tables = [p for p in pieces if p["kind"] == "table" and not p.get("floating")]
    if floating and (behind or placed_text) and len(in_flow) <= 1:
        return "placed"
    if inline_tables and in_cells and len(in_cells) >= len(in_flow):
        return "table"
    if floating and not texts:
        return "placed"
    return "flow"


def describe(kind):
    """'A flow page: paragraphs with their spacing, then pictures in the text'."""
    name, what = KINDS.get(kind, ("A page", "kept as built"))
    return f"{name}: {what}"


def editor_for(kind):
    """Where a page of this kind is changed: 'layout' (the layout editor) or 'word' (Edit in Word)."""
    return "layout" if kind == "placed" else "word"
