"""4.30.3 (Nicholas 2026-11-13 16:18, 16:20): a 700-page file sat at "0% done, working out the time left" for minutes.
Honest progress: every page and every picture is said and moves the share; a Word file has a position; the share shows
to a tenth of a percent; the time so far always shows; the time left comes from the recent pace; a slow step says so.
The reading itself is unchanged. Fictional files."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", os.path.join(tempfile.mkdtemp(), "d"))
import scanprogress as SP, scansay as SS

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


# ---- the lines
q = SP.parse("[1/1] Osprey RFP.pdf - PDF page 37/700, picture 2/5...")
check("a picture inside a page counts toward the page", abs(q["part"] - (36 + 0.2) / 700) < 1e-9 and q["what"] == "page 37/700, picture 2/5", q)
q = SP.parse("[1/1] Osprey Volume.docx - Reading Word body, picture 12/41...")
check("a Word file has a position: its pictures read so far", abs(q["part"] - 11 / 41) < 1e-9 and q["what"] == "reading the text, picture 12/41", q)
q = SP.parse("[1/3] Osprey Brief.pptx - Slide 3/20, picture 7...")
check("a picture with no count does not move a slide's share on its own", abs(q["part"] - 2 / 20) < 1e-9)
q = SP.parse("[2/4] Osprey RFP.pdf - Matching terms...")
check("Matching terms: the file is read", q["part"] == 1.0 and q["what"] == "matching terms")

# ---- a 700-page file at 6 seconds a page
pr = SP.Progress(now=0.0)
pr.update("[1/1] Osprey RFP.pdf - PDF page 1/700...", now=0.1)
check("page 1: 0% done, the time so far shows at once", pr.line(now=3.0) == "0% done · 3 s so far · Working out the time left", pr.line(now=3.0))
pr.update("[1/1] Osprey RFP.pdf - PDF page 2/700...", now=6.0)
check("page 2, six seconds in: a share to a tenth of a percent and a time left", pr.percent_words() == "0.1% done" and pr.permille() == 1
      and pr.left(now=6.0) is not None and 60 < pr.left(now=6.0) / 60 < 80, (pr.percent_words(), pr.left(now=6.0)))
check("... where it is: page 2 of 700", pr.where() == "File 1 of 1: Osprey RFP.pdf, page 2 of 700", pr.where())
for n in range(3, 41):
    pr.update(f"[1/1] Osprey RFP.pdf - PDF page {n}/700...", now=6.0 * (n - 1))
line = pr.line(now=6.0 * 39)
check("page 40: the line says done, so far and left", line == "5.6% done · 3 min 54 s so far · About 66 minutes left", line)
# pictures inside one page
pr.update("[1/1] Osprey RFP.pdf - PDF page 40/700, picture 3/4...", now=6.0 * 39 + 4)
check("a picture inside the page moves the bar", pr.share > 39 / 700 and pr.where().endswith("page 40 of 700, picture 3 of 4"), pr.where())
# the pace changes: typed pages now fly by
t = 6.0 * 39 + 4
for n in range(41, 341):
    t += 0.1
    pr.update(f"[1/1] Osprey RFP.pdf - PDF page {n}/700...", now=t)
t += 95                                            # and then a stretch of slow pages, 5 s each
for n in range(341, 360):
    t += 5
    pr.update(f"[1/1] Osprey RFP.pdf - PDF page {n}/700...", now=t)
whole = (1 - pr.share) * (t - 0.0) / pr.share       # what the pace since the start would say
check("the time left follows the pace of the last minute and a half, not the pace since the start",
      pr.left(now=t) > 2 * whole and abs(pr.left(now=t) - (700 - 359) * 5) < 400, (pr.left(now=t), whole))
# a slow step
check("a step that takes long says how long it has been on it", pr.line(now=t + 45).endswith("45 s on this step, still reading"), pr.line(now=t + 45))
check("... and the time so far keeps counting", "so far" in pr.line(now=t + 45) and pr.took(now=t + 45) == t + 45)
check("lengths of time in plain words", [SP.span_words(x) for x in (42, 252, 3900)] == ["42 s", "4 min 12 s", "1 h 5 min"]
      and SP.left_words(100 * 60) == "About 1 h 40 min left")

# ---- what the reader says
said = []
say = SS.wrap(said.append, "", ".pdf")
say("[1/1] Osprey RFP.pdf - PDF page 1/3...")
SS.pictures(2); SS.picture(); SS.picture()
say("[1/1] Osprey RFP.pdf - PDF page 2/3...")
SS.pictures(1); SS.picture()
check("a PDF: each page, and each picture on it, counted afresh on every page",
      said == ["[1/1] Osprey RFP.pdf - PDF page 1/3...", "[1/1] Osprey RFP.pdf - PDF page 1/3, picture 1/2...", "[1/1] Osprey RFP.pdf - PDF page 1/3, picture 2/2...",
               "[1/1] Osprey RFP.pdf - PDF page 2/3...", "[1/1] Osprey RFP.pdf - PDF page 2/3, picture 1/1..."], said)
check("every line the reader says is one the bar reads", all(SP.parse(x) for x in said))
SS.done(); n = len(said); SS.picture()
check("after the file nothing more is said", len(said) == n)

# ---- a real Word file with pictures, read by the reader itself
import app_gui as A
from docx import Document
from PIL import Image
tmp = tempfile.mkdtemp()
doc = Document(); doc.add_paragraph("The Osprey Ground Support Equipment (GSE) is described here.")
for i in range(3):
    pic = os.path.join(tmp, f"p{i}.png"); Image.new("RGB", (60 + i, 40), (255, 255, 255)).save(pic)
    doc.add_picture(pic)
path = os.path.join(tmp, "Osprey Volume.docx"); doc.save(path)
check("an Office file's pictures are counted before it is read", SS.media_count(path) == 3)
lines = []
before = A.extract_chunks_from_file(path, lambda _m: None, 1, 1)
chunks = A.extract_chunks_from_file(path, lines.append, 1, 1)
pics = [x for x in lines if "picture" in x]
check("a Word file says each picture it reads: 1/3, 2/3, 3/3", [x.split("picture ")[1] for x in pics] == ["1/3...", "2/3...", "3/3..."], lines)
check("... and what it reads is the same with or without anyone listening", chunks == before and any("GSE" in t for _l, t in chunks))
pr = SP.Progress(now=0.0)
for i, x in enumerate(lines):
    pr.update(x, now=float(i))
check("... so the bar moves inside one Word file", 0.6 < pr.share < 0.7, pr.share)
got = []
A.CANCEL.clear()
A.analyze_batch([path], got.append)
check("the scan says Matching terms as its last step for a file", got and got[-1] == "[1/1] Osprey Volume.docx - Matching terms...", got[-3:])
n = sum(checks)
print(f"SCAN PROGRESS 4303 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
