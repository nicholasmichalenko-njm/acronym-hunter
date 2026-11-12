"""The app's icon (4.19.0, Nicholas 2026-11-11 18:54: the taskbar icon bigger and more prominent): a satellite between
gold corner brackets on a navy rounded square, drawn at 1024 and scaled to every size Windows asks for. Below 32 pixels the
brackets go and the satellite fills the square, so the mark reads at taskbar size. Writes assets/scanner.ico and
assets/scanner_256.png. Run: python tools/make_icon.py"""
import os

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = 1024
GOLD, WHITE, NAVY, STRUT = (255, 184, 28, 255), (246, 249, 253, 255), (16, 42, 80, 255), (200, 210, 224, 255)


def background(size):
    g = Image.new("RGBA", (size, size)); d = ImageDraw.Draw(g)
    top, bot = (22, 52, 96), (8, 25, 52)
    for y in range(size):
        t = y / (size - 1)
        d.line([(0, y), (size, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)) + (255,))
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.2), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0)); out.paste(g, (0, 0), m)
    return out


def satellite(scale=1.0, body=1.0, stripes=3):
    c = Image.new("RGBA", (W * 2, W * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    cx = cy = W
    b, pw, ph = int(170 * scale * body), int(320 * scale), int(150 * scale)
    gap, st = int(60 * scale), max(6, int(16 * scale))
    d.rectangle([cx - gap - b // 2 - pw, cy - st // 2, cx + gap + b // 2 + pw, cy + st // 2], fill=STRUT)
    for side in (-1, 1):
        x0 = cx + b // 2 + gap if side > 0 else cx - b // 2 - gap - pw
        d.rounded_rectangle([x0, cy - ph // 2, x0 + pw, cy + ph // 2], radius=int(12 * scale), fill=WHITE)
        for k in range(1, stripes + 1):
            y = cy - ph // 2 + k * ph // (stripes + 1)
            d.rectangle([x0 + int(30 * scale), y - int(9 * scale), x0 + pw - int(30 * scale), y + int(9 * scale)], fill=NAVY)
    d.rectangle([cx - b // 2, cy - b // 2, cx + b // 2, cy + b // 2], fill=GOLD)
    c = c.rotate(30, resample=Image.BICUBIC)
    return c.crop((W // 2, W // 2, W // 2 + W, W // 2 + W))


def make(size):
    big = background(W); d = ImageDraw.Draw(big)
    small = size < 32
    if not small:
        m, L, t = int(W * 0.08), int(W * 0.19), int(W * 0.055)
        for cx, cy, sx, sy in ((m, m, 1, 1), (W - m, m, -1, 1), (m, W - m, 1, -1), (W - m, W - m, -1, -1)):
            d.rectangle([min(cx, cx + sx * L), min(cy, cy + sy * t), max(cx, cx + sx * L), max(cy, cy + sy * t)], fill=GOLD)
            d.rectangle([min(cx, cx + sx * t), min(cy, cy + sy * L), max(cx, cx + sx * t), max(cy, cy + sy * L)], fill=GOLD)
    big.alpha_composite(satellite(1.12 if small else 0.9, 1.45 if small else 1.0, 2 if small else 3))
    return big.resize((size, size), Image.LANCZOS)


def main():
    sizes = [16, 20, 24, 32, 40, 48, 64, 96, 128, 256]
    imgs = [make(s) for s in sizes]
    imgs[-1].save(os.path.join(ROOT, "assets", "scanner.ico"), sizes=[(s, s) for s in sizes], append_images=imgs[:-1])
    imgs[-1].save(os.path.join(ROOT, "assets", "scanner_256.png"))
    return imgs


if __name__ == "__main__":
    main()
