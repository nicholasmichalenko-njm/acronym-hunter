"""Draws the Stationkeeper icons (the app + Training) as multi-size .ico files and a preview sheet (2.44.0).
Shared: rounded tile, a satellite whose solar panels are lines of a page, inside corner brackets (the box a satellite
keeps to, as a proposal keeps to the customer's requirements). The app: navy tile, amber body and brackets.
Training: dark teal tile, mint body and brackets.
  .\\venv\\Scripts\\python.exe tools\\make_icons.py"""
import os
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "assets")
S = 1024                                   # draw large, downsample for crisp edges
SIZES = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]

def tile(d, top, bottom):
    grad = Image.new("RGB", (1, S))
    for y in range(S):
        t = y / (S - 1)
        grad.putpixel((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    grad = grad.resize((S, S))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle((40, 40, S - 40, S - 40), radius=210, fill=255)
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)
    return img

def draw(kind):
    import math
    navy = ((22, 52, 96), (9, 26, 52))
    teal = ((16, 92, 88), (6, 44, 44))
    img = tile(None, *(navy if kind == "scanner" else teal))
    d = ImageDraw.Draw(img)
    white = (245, 248, 252, 255)
    accent = (255, 184, 28, 255) if kind == "scanner" else (94, 234, 196, 255)
    lines = (52, 84, 128, 255) if kind == "scanner" else (40, 110, 104, 255)
    cx = cy = S // 2
    k, a = 100, math.radians(-35)
    ca, sa = math.cos(a), math.sin(a)

    def P(x, y):
        return (cx + (x * ca - y * sa) * k, cy + (x * sa + y * ca) * k)
    d.line([P(-1.3, 0), P(1.3, 0)], fill=white, width=int(0.14 * k))          # the struts
    for x0, x1 in ((1.25, 3.3), (-3.3, -1.25)):                                # solar panels: lines of a page
        d.polygon([P(x0, -0.75), P(x1, -0.75), P(x1, 0.75), P(x0, 0.75)], fill=white)
        for yy in (-0.35, 0.05, 0.42):
            d.line([P(x0 + 0.22, yy), P(x1 - 0.22, yy)], fill=lines, width=int(0.13 * k))
    d.polygon([P(-0.85, -0.85), P(0.85, -0.85), P(0.85, 0.85), P(-0.85, 0.85)], fill=accent)   # the body
    m, L, w = 150, 170, 44                                                     # corner brackets: the box it keeps to
    for (x, y, sx, sy) in ((m, m, 1, 1), (S - m, m, -1, 1), (m, S - m, 1, -1), (S - m, S - m, -1, -1)):
        d.line((x, y, x + sx * L, y), fill=accent, width=w)
        d.line((x, y, x, y + sy * L), fill=accent, width=w)
        d.ellipse((x - w // 2, y - w // 2, x + w // 2, y + w // 2), fill=accent)
    return img

def small(img, size):
    out = img.resize((size, size), Image.LANCZOS)
    if size <= 32:
        out = out.filter(ImageFilter.UnsharpMask(radius=0.6, percent=120, threshold=0))
    return out

def main():
    os.makedirs(OUT, exist_ok=True)
    sheet = Image.new("RGBA", (40 + 2 * 360 + 2 * 340, 640), (236, 239, 243, 255))
    dark = Image.new("RGBA", sheet.size, (32, 33, 36, 255))
    for k, kind in enumerate(("scanner", "trainer")):
        big = draw(kind)
        frames = [small(big, s) for s in SIZES]
        frames[-1].save(os.path.join(OUT, f"{kind}.ico"), sizes=[(s, s) for s in SIZES], append_images=frames[:-1])
        big.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, f"{kind}_256.png"))
        for bg in (sheet, dark):
            x = 40 + k * 720
            bg.alpha_composite(frames[-1], (x, 30))
            xx = x
            for s in (16, 24, 32, 48, 64):
                f = frames[SIZES.index(s)]
                bg.alpha_composite(f.resize((s * 4, s * 4), Image.NEAREST) if s <= 24 else f, (xx, 320 if s <= 24 else 330))
                xx += (s * 4 if s <= 24 else s) + 24
            yy = 480
            xx = x
            for s in (16, 24, 32, 48):
                bg.alpha_composite(frames[SIZES.index(s)], (xx, yy)); xx += s + 30
    combo = Image.new("RGBA", (sheet.width, sheet.height * 2))
    combo.paste(sheet, (0, 0)); combo.paste(dark, (0, sheet.height))
    combo.save(os.path.join(OUT, "icon_preview.png"))
    print("wrote", os.listdir(OUT))

if __name__ == "__main__":
    main()
