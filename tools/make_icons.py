"""Draws the Acronym Hunter icons (scanner + Trainer) as multi-size .ico files and a preview sheet.
Shared: rounded tile, white magnifier, lines of text in the lens. Scanner: navy tile, amber highlighted term.
Trainer: dark teal tile, a dashed selection box around the term (the Trainer's box-drawing), mint accent.
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
    navy = ((22, 52, 96), (9, 26, 52))
    teal = ((16, 92, 88), (6, 44, 44))
    img = tile(None, *(navy if kind == "scanner" else teal))
    d = ImageDraw.Draw(img)
    cx, cy, r, ring = 430, 430, 255, 70          # lens center, radius, ring width
    white = (245, 248, 252, 255)
    # handle (drawn first, under the ring), with rounded end
    hx0, hy0 = cx + int(r * 0.66), cy + int(r * 0.66)
    hx1, hy1 = 860, 860
    d.line((hx0, hy0, hx1, hy1), fill=white, width=118)
    d.ellipse((hx1 - 59, hy1 - 59, hx1 + 59, hy1 + 59), fill=white)
    # lens glass
    glass = (52, 84, 128, 255) if kind == "scanner" else (40, 110, 104, 255)   # solid tint: tile color lightened
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=glass)
    # text lines inside the lens: one highlighted term
    accent = (255, 184, 28, 255) if kind == "scanner" else (94, 234, 196, 255)
    muted = (205, 218, 235, 255)
    lh = 52
    rows = [(-120, 0.55, False), (-20, 0.80, True), (80, 0.62, False)]
    for dy, frac, hot in rows:
        y = cy + dy
        x0 = cx - int(r * 0.62)
        if hot:
            x1 = x0 + int(r * 0.80)
            d.rounded_rectangle((x0, y - lh // 2, x1, y + lh // 2), radius=lh // 2, fill=accent)
            if kind == "trainer":           # dashed selection box around the term
                pad, dash, gap, w = 26, 34, 22, 16
                bx0, by0, bx1, by1 = x0 - pad, y - lh // 2 - pad, x1 + pad, y + lh // 2 + pad
                for x in range(bx0, bx1, dash + gap):
                    d.line((x, by0, min(x + dash, bx1), by0), fill=white, width=w)
                    d.line((x, by1, min(x + dash, bx1), by1), fill=white, width=w)
                for yy in range(by0, by1, dash + gap):
                    d.line((bx0, yy, bx0, min(yy + dash, by1)), fill=white, width=w)
                    d.line((bx1, yy, bx1, min(yy + dash, by1)), fill=white, width=w)
        else:
            x1 = x0 + int(r * 2 * 0.62 * frac)
            d.rounded_rectangle((x0, y - lh // 2 + 8, x1, y + lh // 2 - 8), radius=lh // 2, fill=muted)
    # ring on top
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=white, width=ring)
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
