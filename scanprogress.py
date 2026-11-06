"""How far an acronym scan is, and about how long is left (3.71.0). The scan says where it is in lines like
"[3/20] Figure 3.png - Running OCR on image..." or "[1/2] RFP.pdf - PDF page 40/212..."; this turns them into the
share of the whole done and a time left from the pace so far. No Qt here, so it is checked without a screen."""
import re
import time

LINE = re.compile(r"^\[(\d+)/(\d+)\]\s+(.*?)(?:\s+-\s+(.*))?$")
PART = re.compile(r"(?:page|slide)\s+(\d+)\s*/\s*(\d+)", re.I)
WORDS = (("Running OCR on image", "reading the picture"), ("Reading vector graphic", "reading the drawing"),
         ("PDF page", "page"), ("Slide", "slide"), ("Reading Word body", "reading the text"),
         ("Reading headers, footers, notes, comments", "reading headers, footers and comments"),
         ("Reading Excel cells", "reading the cells"), ("Reading shapes, charts, images, comments", "reading shapes, charts and pictures"),
         ("unchanged, matching again", "unchanged, matching again"), ("unchanged, using saved results", "unchanged"))
MIN_SHARE, MIN_SECONDS = 0.02, 2.0          # no time left until the pace means something


def parse(msg):
    """{'file', 'files', 'name', 'what', 'part'} from one progress line, or None. part: the share of this file done."""
    m = LINE.match(str(msg).strip())
    if not m:
        return None
    what = (m.group(4) or "").strip().rstrip(".").strip()
    p = PART.search(what)
    part = (int(p.group(1)) - 1) / max(1, int(p.group(2))) if p else 0.0
    for old, new in WORDS:
        if what.startswith(old):
            what = new + what[len(old):]
            break
    return {"file": int(m.group(1)), "files": max(1, int(m.group(2))), "name": m.group(3).strip(), "what": what,
            "part": min(max(part, 0.0), 1.0)}


def left_words(seconds):
    """Time left in plain words."""
    if seconds is None:
        return "Working out the time left"
    if seconds < 10:
        return "A few seconds left"
    if seconds < 60:
        return f"About {int(round(seconds / 5.0) * 5)} seconds left"
    mins = int(round(seconds / 60.0))
    return "About 1 minute left" if mins <= 1 else f"About {mins} minutes left"


class Progress:
    """One scan's progress. update() with each line the scan sends; left() any time (a timer counts down between lines)."""

    def __init__(self, now=None):
        self.t0 = time.monotonic() if now is None else now
        self.share, self.info, self.left_at, self.t_line = 0.0, None, None, self.t0

    def update(self, msg, now=None):
        now = time.monotonic() if now is None else now
        p = parse(msg)
        if p is None:
            return self
        self.info = p
        share = (p["file"] - 1 + p["part"]) / p["files"]
        self.share = max(self.share, min(share, 0.999))          # never goes back; 100% only when the scan ends
        took = now - self.t0
        if self.share >= MIN_SHARE and took >= MIN_SECONDS:
            self.left_at = took / self.share * (1.0 - self.share)
        self.t_line = now
        return self

    def left(self, now=None):
        if self.left_at is None:
            return None
        now = time.monotonic() if now is None else now
        return max(0.0, self.left_at - (now - self.t_line))

    def percent(self):
        return int(self.share * 100)

    def where(self):
        """'File 3 of 20: Figure 3.png, reading the picture'."""
        p = self.info
        if p is None:
            return "Starting the scan"
        return f"File {p['file']} of {p['files']}: {p['name']}" + (f", {p['what']}" if p["what"] else "")
