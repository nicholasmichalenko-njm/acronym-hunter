"""The setup as it will be written, before it is written (4.64.0; Nicholas 2026-11-23: "the setup should be a preview
of the items in the shred exactly as it will be in the word export. I want to make sure the styles are applied
correctly, preview the doc with the text in their styles").

blocks() runs the same code that writes a volume's setup (setuptemplate.volume_docs, so the same pieces, the same
order under each heading, the same kinds left out) and reads the paragraphs back as a list: each heading, and each
piece of text with its kind and the style it is written in. html() draws that list with each kind's look (font, size,
color, bold, italic). It is the app's drawing of the text in its styles; Word's own pages (page breaks, the template's
cover and headers) are the Exact preview in Word. Nothing is written to disk. Rules only (No AI); nothing leaves the PC."""
import html as _html
import re

import setuptemplate as ST

_STYLE = re.compile(r'<w:pStyle w:val="([^"]*)"')
_TEXT = re.compile(r"<w:t(?: [^>]*)?>(.*?)</w:t>", re.S)
_LEVEL = re.compile(r"(\d+)\s*$")


def _text(xml):
    return _html.unescape("".join(_TEXT.findall(xml))).strip()


def _of_doc(d, kinds, out):
    for i, xml in enumerate(d.body):
        if not isinstance(xml, str):
            continue
        if xml.lstrip().startswith("<w:tbl"):
            out.append({"what": "other", "text": "A table (the section's requirements)", "kind": "", "style": ""})
            continue
        text = _text(xml)
        m = _STYLE.search(xml)
        sid = m.group(1) if m else ""
        if sid in kinds:
            if text:
                out.append({"what": "text", "text": text, "kind": kinds[sid][0], "style": kinds[sid][1]})
        elif "eading" in sid or sid.lower().startswith(("appendix", "unnumbered")):
            if text:
                lv = _LEVEL.search(sid)
                out.append({"what": "heading", "text": text, "level": int(lv.group(1)) if lv else 1, "kind": "", "style": sid})
        elif text:
            k = (getattr(d, "kind_at", {}) or {}).get(i) or ""
            out.append({"what": "text" if k else "plain", "text": text, "kind": "capture" if k.startswith("cap:") else k, "style": sid})
        elif "<w:sdt" in xml or "w:fldChar" in xml or "w:instrText" in xml:
            out.append({"what": "other", "text": "A part Word builds (a table of contents or a list)", "kind": "", "style": ""})
    return out


def blocks(M, vname, entries, std, config_dir, ws=None, info=None, context=None):
    """[{"what": "heading" | "text" | "plain" | "other", "text", "kind", "style", "level"}] for one volume, in the order
    it is written. Returns (opts, blocks)."""
    opts, df, dm, da = ST.volume_docs(M, vname, entries, std, config_dir, ws, info, context)
    sids = ST.style_ids(opts)
    kinds = {}
    for k, sid in sids.items():
        kinds.setdefault(sid, ("capture" if str(k).startswith("cap:") else k, opts[k]["style"]))
    out = []
    for d in (df, dm, da):
        if d is not None:
            _of_doc(d, kinds, out)
    return opts, out


def volumes(M, config_dir, ws=None, effort_name="", info=None):
    """[(volume name, entries, std)] as Make the setup would take them."""
    import setupdoc as SD
    planned = {p["volume"]: p for p in ST.plan(M, config_dir, ws, effort_name, info)}
    return [(v, e, planned[v]["std"]) for v, e in SD.volume_groups(M) if v in planned]


def headings(bl):
    """[(index in blocks, level, text)] for the list beside the preview."""
    return [(i, b.get("level", 1), b["text"]) for i, b in enumerate(bl) if b["what"] == "heading"]


def counts(bl):
    """{kind: how many pieces} for the line over the preview."""
    out = {}
    for b in bl:
        if b["what"] == "text" and b["kind"]:
            out[b["kind"]] = out.get(b["kind"], 0) + 1
    return out


def _css(lk, indent):
    s = f"color:#{lk.get('color') or '000000'};margin:0 0 6px {indent}px;"
    if lk.get("font"):
        s += f"font-family:'{_html.escape(lk['font'])}';"
    if lk.get("size"):
        s += f"font-size:{float(lk['size']):g}pt;"
    if lk.get("bold"):
        s += "font-weight:bold;"
    if lk.get("italic"):
        s += "font-style:italic;"
    return s


def html(opts, bl, show_styles=True):
    """The blocks as HTML for the preview: each heading with an anchor (h<index>), each piece in its kind's look, with
    the style's name after it in small grey when show_styles."""
    looks = {k: ST.look(opts, k) for k in opts}
    ind = {k: (36 if i else 0) for k, _l, _s, _c, i in ST.KINDS}
    out = ["<html><body style=\"font-family:Calibri,'Segoe UI',sans-serif;font-size:11pt;color:#111111;\">"]
    for i, b in enumerate(bl):
        t = _html.escape(b["text"])
        if b["what"] == "heading":
            lv = min(max(int(b.get("level", 1)), 1), 6)
            size = {1: 16, 2: 14, 3: 12}.get(lv, 11)
            out.append(f"<a name=\"h{i}\"></a><p style=\"font-size:{size}pt;font-weight:bold;color:#1F3864;margin:14px 0 6px 0;\">{t}</p>")
        elif b["what"] == "other":
            out.append(f"<p style=\"color:#6B7280;font-style:italic;margin:0 0 6px 0;\">[{t}]</p>")
        else:
            lk = looks.get(b["kind"]) or {"color": "000000"}
            tag = (f" <span style=\"color:#9CA3AF;font-size:8pt;font-weight:normal;font-style:normal;\">&nbsp;{_html.escape(b['style'])}</span>"
                   if show_styles and b.get("style") else "")
            out.append(f"<p style=\"{_css(lk, ind.get(b['kind'], 0))}\">{t}{tag}</p>")
    out.append("</body></html>")
    return "".join(out)
