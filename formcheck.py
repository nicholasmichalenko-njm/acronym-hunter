"""Customer forms in a volume (3.68.0, Template Studio decision 6): a Customer form part is the customer's own form,
locked. Final Check finds its pages in the volume's PDF by its words, says where it sits, leaves its pages out of the
count when the plan says it does not count, and checks the marking its pages must carry; the volume's own page marking
is not asked of them.

form_words(path) -> set of words        pages_of(texts, words) -> [page numbers]
check(texts, forms, line, PASS, FAIL, HUMAN) -> (lines, {"drop": pages not counted, "form_pages": pages of every form})
Rules only; the form file is only read."""
import os, re

WORD = re.compile(r"[a-z0-9]{3,}")
MATCH = 0.7                     # a page is the form's when this share of its words are in the form
MIN_WORDS = 12


def _words(text):
    return WORD.findall((text or "").lower())


def form_words(path):
    """Every word of the customer's form (a Word file or a PDF), or an empty set."""
    if not path or not os.path.isfile(path):
        return set()
    try:
        if path.lower().endswith(".pdf"):
            import finalcheck as FC
            texts = FC.read_pdf(path)["texts"]
        else:
            import wordlab as WL
            texts = WL.docx_paragraphs(path)
    except Exception:  # noqa: BLE001  a form that does not read
        return set()
    return {w for t in texts for w in _words(t)}


def pages_of(texts, words):
    """The volume's pages (1-based) whose words are mostly the form's."""
    if not words:
        return []
    out = []
    for i, t in enumerate(texts, 1):
        ws = _words(t)
        if len(ws) >= MIN_WORDS and sum(1 for w in ws if w in words) / len(ws) >= MATCH:
            out.append(i)
    return out


def _span(pages):
    if not pages:
        return ""
    return f"page {pages[0]}" if len(pages) == 1 else f"pages {pages[0]} to {pages[-1]}"


def check(texts, forms, line, PASS, FAIL, HUMAN):
    lines, drop, all_pages = [], set(), set()
    for f in forms or ():
        if not f.get("form"):
            lines.append(line("Customer forms", f"{f['name']} placed", HUMAN, "No form file set for this part "
                              "(Template Studio > Parts and numbering). Check it by hand."))
            continue
        words = form_words(f["form"])
        if not words:
            lines.append(line("Customer forms", f"{f['name']} placed", HUMAN, f"The form file {os.path.basename(f['form'])} "
                              "could not be read. Check it by hand."))
            continue
        ps = pages_of(texts, words)
        if not ps:
            lines.append(line("Customer forms", f"{f['name']} placed", FAIL, "Its pages are not in the PDF."))
            continue
        all_pages.update(ps)
        if not f.get("counts"):
            drop.update(ps)
        lines.append(line("Customer forms", f"{f['name']} placed", PASS, f"On {_span(ps)}"
                          + ("; left out of the page count." if not f.get("counts") else "; counted.")))
        if f.get("marking"):
            mk = " ".join(f["marking"].lower().split())
            miss = [p for p in ps if mk not in " ".join((texts[p - 1] or "").lower().split())]
            lines.append(line("Customer forms", f"{f['name']} marking", FAIL if miss else PASS,
                              (f"{f['marking']!r} is missing on page " + ", ".join(map(str, miss)) + ".") if miss
                              else f"{f['marking']!r} on each of its pages."))
    return lines, {"drop": sorted(drop), "form_pages": sorted(all_pages)}
