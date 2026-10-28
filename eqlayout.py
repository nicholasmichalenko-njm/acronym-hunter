"""Position rules for equations in pictures (2.55.0): no generative AI. The text reader recognizes each character; these
rules use where the characters sit to write the equation out:
- a smaller word sitting low on an equation line is a subscript (v0 -> v₀, or v_ref), a smaller raised one a
  superscript (m2 -> m², or e^x);
- two short lines stacked over a horizontal bar are a fraction (a over b -> a/b, or (a+b)/(c) for longer parts); a line
  just left of it that ends in = or an operator joins it (E = (1)/(2)...).
Rules only, applied only to lines that look like math (an =, an operator or a Greek letter), so ordinary text is
never changed."""
import re

SUB = dict(zip("0123456789+-=()aeoxhklmnpst", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜ"))
SUP = dict(zip("0123456789+-=()ni", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱ"))
GREEK = set("αβγδεζηθικλμνξοπρστυφχψωΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩϑϕϵ")
MATH = set("=+−×·÷±∓√∑∏∫∂∇≈≤≥≠≡∝∞^")
SMALL = 0.72          # a word this much smaller than the line's main words is a sub- or superscript
SHIFT = 0.18          # how far (in main word heights) its middle sits below or above the line's middle


def mathy(text):
    t = text or ""
    return any(c in MATH or c in GREEK for c in t) or bool(re.search(r"\w\s*=\s*\S", t))


def _script(text, table, mark):
    if text and all(c in table for c in text):
        return "".join(table[c] for c in text)
    return f"{mark}{text}" if len(text) == 1 else f"{mark}{{{text}}}"


def join_words(words):
    """One line's words [(x0, y0, x1, y1, text, conf)], left to right, as text with sub- and superscripts written out."""
    words = sorted(words, key=lambda t: t[0])
    text = " ".join(w[4] for w in words)
    if len(words) < 2 or not mathy(text):
        return text
    hs = sorted(w[3] - w[1] for w in words)
    main = hs[min(len(hs) - 1, (2 * len(hs)) // 3)]          # the main (full-size) height: upper part of the heights
    big = [w for w in words if (w[3] - w[1]) >= SMALL * main] or words
    mid = sorted((w[1] + w[3]) / 2 for w in big)[len(big) // 2]
    out = []
    for w in words:
        h, c = w[3] - w[1], (w[1] + w[3]) / 2
        if out and h < SMALL * main and c > mid + SHIFT * main:
            out[-1] += _script(w[4], SUB, "_")
        elif out and h < SMALL * main and c < mid - SHIFT * main:
            out[-1] += _script(w[4], SUP, "^")
        else:
            out.append(w[4])
    return " ".join(out)


def _bar_between(gray, top, bottom, x0, x1):
    """A dark horizontal bar spanning most of x0..x1 somewhere between rows top and bottom."""
    if gray is None or bottom <= top:
        return bottom - top <= 2            # touching boxes: the bar is inside them
    h, w = gray.shape[:2]
    top, bottom = max(0, int(top)), min(h, int(bottom) + 1)
    x0, x1 = max(0, int(x0)), min(w, int(x1))
    if x1 - x0 < 3 or bottom <= top:
        return False
    band = gray[top:bottom, x0:x1] < 128
    return bool((band.mean(axis=1) >= 0.8).any())


def _part(t):
    t = t.strip()
    return t if re.fullmatch(r"[\w.′″]+", t) else f"({t})"


def fractions(lines, gray=None):
    """lines: [(x0, y0, x1, y1, text, conf)]. Two short lines stacked over a bar become one 'a/b' line; a line just to
    the left ending in = or an operator joins it. Returns the new list of lines."""
    lines = sorted(lines, key=lambda t: (t[1], t[0]))
    used, out = set(), []
    for i, a in enumerate(lines):
        if i in used:
            continue
        best = None
        for j, b in enumerate(lines):
            if j == i or j in used or b[1] <= a[1]:
                continue
            ha, hb = a[3] - a[1], b[3] - b[1]
            gap = b[1] - a[3]
            ov = min(a[2], b[2]) - max(a[0], b[0])
            if (len(a[4]) <= 20 and len(b[4]) <= 20 and -0.2 * min(ha, hb) <= gap <= 1.2 * max(ha, hb)
                    and ov >= 0.6 * min(a[2] - a[0], b[2] - b[0])
                    and _bar_between(gray, a[3] - 1, b[1] + 1, max(a[0], b[0]), min(a[2], b[2]))):
                best = j
                break
        if best is None:
            continue
        b = lines[best]
        mid = (a[1] + b[3]) / 2
        eq_left = any(l[2] <= min(a[0], b[0]) + 4 and l[1] <= mid <= l[3] and re.search(r"=\s*$", l[4])
                      for k, l in enumerate(lines) if k not in (i, best))
        if not (mathy(a[4]) or mathy(b[4]) or eq_left):    # a table row over a rule is not a fraction
            continue
        used |= {i, best}
        frac = (min(a[0], b[0]), a[1], max(a[2], b[2]), b[3], f"{_part(a[4])}/{_part(b[4])}", min(a[5], b[5]))
        out.append(frac)
    rest = [l for k, l in enumerate(lines) if k not in used]
    merged = []
    for f in out:
        mid = (f[1] + f[3]) / 2
        left = [l for l in rest if l[2] <= f[0] + 4 and l[1] <= mid <= l[3] and f[0] - l[2] < 3 * (l[3] - l[1])
                and re.search(r"[=+\-−×·÷]\s*$", l[4])]
        if left:
            l = max(left, key=lambda t: t[2])
            rest.remove(l)
            f = (l[0], min(l[1], f[1]), f[2], max(l[3], f[3]), l[4].rstrip() + " " + f[4], min(l[5], f[5]))
        merged.append(f)
    return sorted(rest + merged, key=lambda t: (t[1], t[0]))
