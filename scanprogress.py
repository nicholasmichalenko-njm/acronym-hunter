"""How far an acronym scan is, and about how long is left (3.71.0; 4.30.3). The scan says where it is in lines like
"[3/20] Figure 3.png - Running OCR on image...", "[1/2] RFP.pdf - PDF page 40/212, picture 2/5..." or
"[1/1] Volume.docx - Reading Word body, picture 12/41..."; this turns them into the share of the whole done, the time
so far and a time left.

4.30.3 (Nicholas 2026-11-13 16:18, 16:20: a 700-page file sat at "0% done, working out the time left" for minutes):
every page and every picture moves the share; the share is shown to a tenth of a percent while it is small; the time so
far always shows and ticks; the time left comes from the pace of the last minute and a half, not from the start, and
shows after five seconds; a page that takes long says how long it has been on it. No Qt here, so it is checked without
a screen."""
import re
import time
from collections import deque

LINE = re.compile(r"^\[(\d+)/(\d+)\]\s+(.*?)(?:\s+-\s+(.*))?$")
PART = re.compile(r"(?:page|slide)\s+(\d+)\s*/\s*(\d+)", re.I)
PIC = re.compile(r"picture\s+(\d+)(?:\s*/\s*(\d+))?", re.I)
OF = re.compile(r"(\d+)\s*/\s*(\d+)")
WORDS = (("Running OCR on image", "reading the picture"), ("Reading vector graphic", "reading the drawing"),
         ("PDF page", "page"), ("Slide", "slide"), ("Reading Word body", "reading the text"),
         ("Reading headers, footers, notes, comments", "reading headers, footers and comments"),
         ("Reading Excel cells", "reading the cells"), ("Reading shapes, charts, images, comments", "reading shapes, charts and pictures"),
         ("Matching terms", "matching terms"),
         ("unchanged, matching again", "unchanged, matching again"), ("unchanged, using saved results", "unchanged"))
MIN_SHARE, MIN_SECONDS = 0.001, 5.0         # no time left until the pace means something
WINDOW = 90.0                               # the pace is the last minute and a half's
SLOW = 20.0                                 # a step this long says how long it has been on it


def parse(msg):
    """{'file', 'files', 'name', 'what', 'part'} from one progress line, or None. part: the share of this file done."""
    m = LINE.match(str(msg).strip())
    if not m:
        return None
    what = (m.group(4) or "").strip().rstrip(".").strip()
    p, c = PART.search(what), PIC.search(what)
    pic = (int(c.group(1)) - 1) / max(1, int(c.group(2))) if (c and c.group(2)) else 0.0
    if p:
        part = (int(p.group(1)) - 1 + min(pic, 1.0)) / max(1, int(p.group(2)))
    elif what.startswith("Matching terms"):
        part = 1.0                              # the file is read; only the matching is left
    else:
        part = pic
    for old, new in WORDS:
        if what.startswith(old):
            what = new + what[len(old):]
            break
    return {"file": int(m.group(1)), "files": max(1, int(m.group(2))), "name": m.group(3).strip(), "what": what,
            "part": min(max(part, 0.0), 1.0)}


def span_words(seconds):
    """A length of time in plain words: 42 s, 4 min 12 s, 1 h 5 min."""
    s = int(max(0, seconds))
    if s < 60:
        return f"{s} s"
    if s < 3600:
        return f"{s // 60} min {s % 60:02d} s"
    return f"{s // 3600} h {s % 3600 // 60} min"


def left_words(seconds):
    """Time left in plain words."""
    if seconds is None:
        return "Working out the time left"
    if seconds < 10:
        return "A few seconds left"
    if seconds < 60:
        return f"About {int(round(seconds / 5.0) * 5)} seconds left"
    mins = int(round(seconds / 60.0))
    if mins >= 90:
        return f"About {mins // 60} h {mins % 60} min left"
    return "About 1 minute left" if mins <= 1 else f"About {mins} minutes left"


class Progress:
    """One scan's progress. update() with each line the scan sends; left() any time (a timer counts down between lines)."""

    def __init__(self, now=None):
        self.t0 = time.monotonic() if now is None else now
        self.share, self.info, self.left_at, self.t_line = 0.0, None, None, self.t0
        self.t_step = self.t0                       # when the share last moved
        self.marks = deque([(self.t0, 0.0)])        # (time, share) each time the share moved, for the pace

    def update(self, msg, now=None):
        now = time.monotonic() if now is None else now
        p = parse(msg)
        if p is None:
            return self
        self.info = p
        share = (p["file"] - 1 + p["part"]) / p["files"]
        share = max(self.share, min(share, 0.999))               # never goes back; 100% only when the scan ends
        if share > self.share:
            self.share, self.t_step = share, now
            self.marks.append((now, share))
            while len(self.marks) > 2 and now - self.marks[1][0] >= WINDOW:
                self.marks.popleft()                             # keep one mark at least a window old
        took = now - self.t0
        t_from, s_from = self.marks[0]
        if self.share >= MIN_SHARE and took >= MIN_SECONDS and now > t_from and self.share > s_from:
            self.left_at = (1.0 - self.share) * (now - t_from) / (self.share - s_from)
        self.t_line = now
        return self

    def left(self, now=None):
        if self.left_at is None:
            return None
        now = time.monotonic() if now is None else now
        return max(0.0, self.left_at - (now - self.t_line))

    def percent(self):
        return int(self.share * 100)

    def permille(self):
        """The share in thousandths, for a bar that moves on a long file."""
        return int(self.share * 1000)

    def percent_words(self):
        """'0.4% done' while it is small, '37% done' after."""
        pct = self.share * 100.0
        return (f"{pct:.1f}% done" if 0 < pct < 10 else f"{int(pct)}% done")

    def took(self, now=None):
        return (time.monotonic() if now is None else now) - self.t0

    def line(self, now=None):
        """Beside the bar: '0.4% done · 4 min 12 s so far · About 40 minutes left', and how long a slow step has taken."""
        now = time.monotonic() if now is None else now
        out = [self.percent_words(), f"{span_words(self.took(now))} so far", left_words(self.left(now))]
        on = now - self.t_step
        if on >= SLOW and self.info is not None:
            out.append(f"{span_words(on)} on this step, still reading")
        return " · ".join(out)

    def where(self):
        """'File 3 of 20: Figure 3.png, reading the picture'; 'File 1 of 1: RFP.pdf, page 37 of 700, picture 2 of 5'."""
        p = self.info
        if p is None:
            return "Starting the scan"
        return f"File {p['file']} of {p['files']}: {p['name']}" + (f", {OF.sub(lambda m: f'{m.group(1)} of {m.group(2)}', p['what'])}" if p["what"] else "")
