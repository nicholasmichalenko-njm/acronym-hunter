"""Write a small FICTIONAL sample set in Trainer format (training_data layout) for Training Kit dry runs.
  .\\venv\\Scripts\\python.exe tools\\make_dryrun_samples.py <output folder> [lines] [regions]
Text lines: random fictional acronyms/phrases in Windows fonts. Regions: diagram-like boxes with text plus
lines, arrows, and hatching that are NOT text (left unlabeled, so the finder learns them as background)."""
import os, sys, json, random
from PIL import Image, ImageDraw, ImageFont
out = sys.argv[1]; n_lines = int(sys.argv[2]) if len(sys.argv) > 2 else 150; n_regions = int(sys.argv[3]) if len(sys.argv) > 3 else 40
random.seed(7)
FONTS = [f for f in (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\consola.ttf", r"C:\Windows\Fonts\times.ttf",
                     r"C:\Windows\Fonts\calibri.ttf", r"C:\Windows\Fonts\segoeui.ttf") if os.path.exists(f)]
WORDS = ["PDR", "CDR", "ICD", "COPV", "MEOP", "TVAC", "GEVS", "TRL 6", "TT&C", "ADCS", "LL", "SOW", "IMS", "LEO",
         "3,600 psi", "1.8 kWh", "40 m/s", "per", "review", "valve", "thruster", "margin", "update", "before", "test"]
def text():
    return " ".join(random.choice(WORDS) for _ in range(random.randint(1, 4)))
os.makedirs(os.path.join(out, "images"), exist_ok=True); os.makedirs(os.path.join(out, "regions"), exist_ok=True)
with open(os.path.join(out, "labels.txt"), "w", encoding="utf-8", newline="\n") as lab:
    for i in range(n_lines):
        t = text(); font = ImageFont.truetype(random.choice(FONTS), random.randint(18, 34))
        w, h = font.getbbox(t)[2] + 12, font.getbbox(t)[3] + 10
        im = Image.new("RGB", (w, h), (255, 255, 255)); ImageDraw.Draw(im).text((6, 3), t, font=font, fill=(20, 20, 20))
        im.save(os.path.join(out, "images", f"dry_{i:04d}.png")); lab.write(f"images/dry_{i:04d}.png\t{t}\n")
with open(os.path.join(out, "det_labels.txt"), "w", encoding="utf-8", newline="\n") as lab:
    for i in range(n_regions):
        im = Image.new("RGB", (640, 420), (255, 255, 255)); d = ImageDraw.Draw(im); boxes = []
        for _ in range(random.randint(2, 4)):            # NOT text: lines, arrows, hatching
            x, y = random.randint(0, 600), random.randint(0, 380)
            d.line((x, y, x + random.randint(-200, 200), y + random.randint(-150, 150)), fill=(40, 40, 40), width=2)
        for k in range(0, 120, 8):
            d.line((500 + k, 300, 520 + k, 340), fill=(90, 90, 90), width=1)
        y = 20
        for _ in range(random.randint(2, 4)):            # text, labeled
            t = text(); font = ImageFont.truetype(random.choice(FONTS), random.randint(20, 30)); x = random.randint(10, 200)
            d.text((x, y), t, font=font, fill=(10, 10, 10)); b = d.textbbox((x, y), t, font=font)
            boxes.append({"transcription": t, "points": [[b[0] - 2, b[1] - 2], [b[2] + 2, b[1] - 2], [b[2] + 2, b[3] + 2], [b[0] - 2, b[3] + 2]]})
            y += random.randint(60, 90)
        im.save(os.path.join(out, "regions", f"dry_{i:04d}.png"))
        lab.write(f"regions/dry_{i:04d}.png\t{json.dumps(boxes)}\n")
print(f"Wrote {n_lines} text lines and {n_regions} regions to {out}")
