"""Phase 1 dev kit: folder layout + synthetic hard-font Trainer samples."""
import os, sys, shutil, random, glob
from PIL import Image, ImageDraw, ImageFont, ImageFilter
P = r"C:\Users\nmich\AcronymHunterProject"
K = os.path.join(P, "_local_sandbox", "kitdev")
for d in ("kit", "weights\\models", "base_models", "samples\\synth\\images"):
    os.makedirs(os.path.join(K, d), exist_ok=True)
for f in glob.glob(os.path.join(os.environ["USERPROFILE"], ".cache", "doctr", "models", "*.pt")):
    shutil.copy2(f, os.path.join(K, "weights", "models"))
for f in ("doctr_det.onnx", "doctr_reco.onnx", "doctr_models.json"):
    shutil.copy2(os.path.join(P, "vendor", "doctr", f), os.path.join(K, "base_models"))
if not os.path.isdir(os.path.join(K, "doctr_ref")):
    shutil.copytree(os.path.join(P, "_local_sandbox", "mathbench", "doctr_src", "references"), os.path.join(K, "doctr_ref"))
FD = r"C:\Windows\Fonts"
want = ["BRADHITC.TTF", "segoesc.ttf", "Inkfree.ttf", "FREESCPT.TTF", "ITCKRIST.TTF", "Gabriola.ttf", "comic.ttf", "MISTRAL.TTF", "segoepr.ttf"]
fonts = [os.path.join(FD, f) for f in want if os.path.isfile(os.path.join(FD, f))]
print("fonts:", [os.path.basename(f) for f in fonts])
random.seed(11)
terms = ["C&DH", "TT&C", "ICD-204", "PCU", "TVAC", "CCB", "EGSE", "COPV", "MEOP", "GN&C", "RWA", "SRR", "PDR", "CDR", "IMS",
         "TRL", "BAPTA", "SADM", "HPA", "OMUX", "LNA", "RF", "ADCS", "EPS", "OBC", "MLI", "ESD", "FMEA", "SEU", "TID",
         "28V", "450W", "2.2GHz", "3600psi", "Ku-band", "S-band", "Rev-C", "J1", "P2", "TB-3"]
words = ["Unit", "Bus", "Module", "Review", "Board", "Transponder", "Processor", "Test", "Assy", "Harness", "Panel", "Valve"]
lines = []
for i in range(600):
    text = random.choice(terms) if random.random() < 0.7 else random.choice(words)
    f = ImageFont.truetype(random.choice(fonts), random.randint(18, 34))
    w = int(f.getlength(text)) + 16; h = int(f.size * 1.7)
    im = Image.new("L", (w, h), random.randint(215, 255)); d = ImageDraw.Draw(im)
    d.text((8, (h - f.size) // 2 - 3), text, fill=random.randint(0, 90), font=f)
    if random.random() < 0.4: im = im.filter(ImageFilter.GaussianBlur(random.uniform(0.4, 1.0)))
    if random.random() < 0.3: im = im.rotate(random.uniform(-3, 3), expand=True, fillcolor=255)
    p = f"images/hf_{i:04d}.png"; im.save(os.path.join(K, "samples", "synth", p)); lines.append(f"{p}\t{text}")
open(os.path.join(K, "samples", "synth", "labels.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("samples:", len(lines))
