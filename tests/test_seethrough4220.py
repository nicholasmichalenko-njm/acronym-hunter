"""4.22.0: a picture with no background (a PNG with a see-through layer) is read and shown on white paper. Before,
dropping the see-through layer left black where the picture had nothing, so dark letters were black on black in the
acronym review and unreadable to the reader. Fictional content."""
import io, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
os.environ.setdefault("SK_DATA_DIR", os.path.join(tempfile.mkdtemp(), "data"))
import imgops as IO, ocrpdf, pictures
from PIL import Image, ImageDraw

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({info})"))


tmp = tempfile.mkdtemp()
im = Image.new("RGBA", (400, 160), (0, 0, 0, 0))
d = ImageDraw.Draw(im)
d.rectangle((20, 20, 380, 60), fill=(20, 20, 20, 255))           # dark ink
d.rectangle((20, 90, 200, 130), fill=(200, 16, 46, 128))          # half see-through red
png = os.path.join(tmp, "Kestrel logo no background.png"); im.save(png)
data = open(png, "rb").read()

w = IO.on_white(im)
check("on white: nothing is white, ink stays ink, half see-through is its color on white", w.mode == "RGB" and w.getpixel((5, 5)) == (255, 255, 255)
      and w.getpixel((100, 40)) == (20, 20, 20) and abs(w.getpixel((100, 110))[0] - 227) <= 2 and w.getpixel((100, 110))[1] > 120, w.getpixel((100, 110)))
check("a picture with a background is left as it is", IO.on_white(Image.new("RGB", (4, 4), (9, 8, 7))).getpixel((1, 1)) == (9, 8, 7)
      and IO.on_white(Image.new("L", (4, 4), 77)).getpixel((1, 1)) == (77, 77, 77))
pal = im.convert("P", palette=Image.ADAPTIVE, colors=8); pal.info["transparency"] = pal.getpixel((5, 5))
check("a palette picture with a see-through color too", IO.on_white(pal).getpixel((5, 5)) == (255, 255, 255))
bgr = IO.imdecode(data, "color")
gray = IO.imdecode(data, "gray")
check("the reader gets it on white, in color and in grey", tuple(bgr[5, 5]) == (255, 255, 255) and tuple(bgr[40, 100]) == (20, 20, 20)
      and gray[5, 5] == 255 and gray[40, 100] < 40, (tuple(bgr[5, 5]), gray[5, 5]))
keep = IO.imdecode(data, "unchanged")
check("asked for unchanged, the see-through layer is kept", keep.shape[2] == 4 and keep[5, 5][3] == 0)
shown = pictures._img_from_bytes(data)
check("the acronym review shows it on white", shown.mode == "RGB" and shown.getpixel((5, 5)) == (255, 255, 255) and shown.getpixel((100, 40)) == (20, 20, 20))
pc = os.path.join(tmp, "page copies")
out = ocrpdf.make(png, pc, lines_of=lambda img: [])
import pypdfium2 as pdfium
pd = pdfium.PdfDocument(out); page = pd[0].render(scale=1).to_pil().convert("RGB"); pd.close()
px = page.getpixel((int(page.width * 5 / 400), int(page.height * 5 / 160)))
check("its page copy (Shred, Prepare for Redline) is on white", min(px) > 235, px)
check("... under a name of its own, so a copy made before is not used again", os.path.basename(out).endswith("w.pdf")
      and ocrpdf.copy_path(png, pc) == out)
jpg = os.path.join(tmp, "plain.jpg"); Image.new("RGB", (40, 40), (255, 255, 255)).save(jpg)
check("a picture with a background keeps its copy's name", not ocrpdf.copy_path(jpg, pc).endswith("w.pdf"))

k = sum(checks)
print(f"SEE THROUGH 4220 {'PASS' if k == len(checks) and checks else 'FAIL'} ({k}/{len(checks)})")
sys.exit(0 if checks and k == len(checks) else 1)
