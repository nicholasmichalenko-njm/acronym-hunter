"""A single letter read apart in the middle of a word (4.26.1; Nicholas's recording 2026-11-12 02:55: the S of DEFENSE
found as a term on large title type). On letter-spaced or very large type the reader can return one word as several
readings side by side: DEFEN, S, E. A lone letter then looks like a term. This joins a one-letter reading to the
readings it sits between, when all three are letters on one line and the gaps are smaller than a space between words.
Nothing else is joined: a letter after a number (5 A), a letter with a word space before it (Volume I, Section L) and a
letter at the end of a line stay as read. Rules only; standard library only."""

GAP = 0.35            # a gap under this share of the letter's height is inside a word


def _same_row(a, b):
    ha, hb = a[3] - a[1], b[3] - b[1]
    if ha <= 0 or hb <= 0 or not (0.6 <= ha / hb <= 1.7):
        return False
    over = min(a[3], b[3]) - max(a[1], b[1])
    return over >= 0.5 * min(ha, hb)


def _letters(s, last):
    s = str(s).strip()
    return bool(s) and (s[-1] if last else s[0]).isalpha()


def join_split_letters(lines):
    """lines: [(x0, y0, x1, y1, text, conf)]. Returns the same list with each one-letter reading that sits tight between
    two letter readings joined to them (box united, the lower confidence kept). The order of the rest is unchanged."""
    lines = list(lines)
    changed = True
    while changed:
        changed = False
        for i, ln in enumerate(lines):
            t = str(ln[4]).strip()
            if len(t) != 1 or not t.isalpha():
                continue
            h = ln[3] - ln[1]
            left = right = None
            for j, o in enumerate(lines):
                if j == i or not _same_row(ln, o):
                    continue
                if o[2] <= ln[0] + 0.1 * h and ln[0] - o[2] < GAP * h and _letters(o[4], True):
                    if left is None or o[2] > lines[left][2]:
                        left = j
                elif o[0] >= ln[2] - 0.1 * h and o[0] - ln[2] < GAP * h and _letters(o[4], False):
                    if right is None or o[0] < lines[right][0]:
                        right = j
            if left is None or right is None:
                continue
            a, b = lines[left], lines[right]
            joined = (min(a[0], ln[0]), min(a[1], ln[1], b[1]), max(b[2], ln[2]), max(a[3], ln[3], b[3]),
                      str(a[4]).rstrip() + t + str(b[4]).lstrip(), min(float(a[5]), float(ln[5]), float(b[5])))
            keep = [x for k, x in enumerate(lines) if k not in (i, left, right)]
            keep.insert(min(left, right, i), joined)
            lines = keep
            changed = True
            break
    return lines
