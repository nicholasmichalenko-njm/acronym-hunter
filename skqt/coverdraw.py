"""A cover, title page or back cover drawn as it will look (3.34.0): its background picture, the pictures on it, and
each text block, text box and floating table with its words (a field shows the volume's value, or its name in brackets)
in its size, weight, color, font and alignment. Drawn by Stationkeeper from the kept page; Word's own layout comes from
Open a sample in Word."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPixmap

import coverbuild as CB
import coverlayout as CL


def field_text(std, key):
    """What a field shows on the page: the volume's value, else its name in brackets."""
    v = ((std or {}).get("variables") or {}).get(key)
    if v:
        return str(v)
    try:
        import fillins as FI
        val = FI.value(std or {}, key)
        if val:
            return str(val)
    except Exception:  # noqa: BLE001
        pass
    label = dict((k, lab) for k, lab, _s in CL.fields(std)).get(key, key)
    return f"[{label}]"


def block_text(std, b):
    return field_text(std, b["field"]) if b.get("field") else (b.get("text") or "")


def draw_text(p, rect, std, b, scale):
    """One block's words inside rect (screen units), scale = screen units per inch."""
    f = QFont(b.get("font") or "Arial")
    f.setPointSizeF(max(2.0, float(b.get("size") or (24 if b.get("field") == "volume_name" else 12)) * scale / 72.0))
    f.setBold(bool(b.get("bold")) or (b.get("field") == "volume_name" and not b.get("size")))
    p.setFont(f)
    p.setPen(QColor("#" + str(b.get("color") or "1f2937")) if b.get("color") else QColor("#1f2937"))
    al = {"center": Qt.AlignHCenter, "right": Qt.AlignRight}.get(b.get("align") or "left", Qt.AlignLeft)
    p.drawText(rect, al | Qt.AlignTop | Qt.TextWordWrap, block_text(std, b))


def pictures(data):
    """[(x, y, w, h, QPixmap, behind)] of the page's floating and inline pictures (inches)."""
    out = []
    try:
        lay = CL.read(data)
    except Exception:  # noqa: BLE001
        return out
    for d in lay["pieces"]:
        if d["kind"] != "picture" or not d.get("embed"):
            continue
        b = CL.picture_bytes(data, d["embed"])
        pm = QPixmap()
        if b and pm.loadFromData(b):
            out.append((d.get("x") or lay["page"]["margins"]["left"], d.get("y") or lay["page"]["margins"]["top"],
                        d.get("w") or 1, d.get("h") or 1, pm, bool(d.get("behind"))))
    return out


def draw_page(p, page_rect, data, std=None):
    """The kept page drawn into page_rect (the page's edges on screen). Returns False when the page cannot be read."""
    try:
        design = CB.design_of(data, std)
    except Exception:  # noqa: BLE001
        return False
    pw = design["page"]["w"] or 8.5
    scale = page_rect.width() / pw
    p.fillRect(page_rect, QColor("#ffffff"))
    for x, y, w, h, pm, _behind in sorted(pictures(data), key=lambda t: not t[5]):
        p.drawPixmap(QRectF(page_rect.left() + x * scale, page_rect.top() + y * scale, w * scale, h * scale).toRect(), pm)
    for b in design["blocks"]:
        r = QRectF(page_rect.left() + b["x"] * scale, page_rect.top() + b["y"] * scale, b["w"] * scale, max(b["h"], 0.3) * scale * 1.5)
        draw_text(p, r, std, b, scale)
    if design["left_out"]:                              # words in the page's flow: stacked from the top margin
        import io, zipfile
        from lxml import etree
        root = etree.fromstring(zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml"))
        m = design["page"]["margins"]
        y = m["top"]
        for para in root.find(CL.w("body")).findall(CL.w("p")):
            t = CL._own_text(para)
            if not t:
                continue
            r = QRectF(page_rect.left() + m["left"] * scale, page_rect.top() + y * scale, (pw - m["left"] - m["right"]) * scale, 0.5 * scale)
            draw_text(p, r, std, {"text": t, "size": 12}, scale)
            y += 0.35
    return True
