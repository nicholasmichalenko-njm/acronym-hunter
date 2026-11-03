"""Fixes behind the docmap findings. Each is an engine op for the guarded write path (closed file) and is
written so the same element changes can be made through the table/paragraph XML of the document open in Word.

Every op declares what it changes: field instructions as field_changes (story, old, new), and its content
facets in *_ALLOWED. An op that would change anything else is refused by the unit guard and the fingerprint.

  op_toc_field(pkg, std)            main TOC field code to the rule (levels, switches); result kept until Word's
                                    Update entire table
  op_toc_styles(pkg, std)           TOC 1..n and Table of Figures: number position, text position, right indent,
                                    right tab with leader (the team's TabsLists values)
  op_xref_switches(pkg, std)        REF and PAGEREF: \\* MERGEFORMAT -> \\* CHARFORMAT, \\h when the rule says links
  op_caption_fields(pkg, std)       SEQ identifier and STYLEREF chapter part to the caption rule of the part
  op_caption_after(pkg, std)        what follows the number (". " -> ".<tab>"), the words unchanged
  op_scope_reset(pkg, std, names)   response and appendix scope bookmarks to the first Heading 1 / first Heading 7
"""
import re

from lxml import etree
from prodengine.engine.pkg import NS
from prodengine.engine.ordered import ensure, remove, q
from prodengine.engine.fingerprint import visible_text
from prodengine.pe import docmap as D

WP, WR, WT = q("p"), q("r"), q("t")
TOC_ALLOWED = ("fields",)
STYLES_ALLOWED = ()
XREF_ALLOWED = ("fields",)
CAPTION_ALLOWED = ("fields",)
AFTER_ALLOWED = ("text",)           # one space becomes a tab in caption paragraphs; checked inside the op
SCOPE_ALLOWED = ("bookmarks", "bookmark_context")


def _norm(s):
    return " ".join(s.split())


def _fields_with_instr_runs(body):
    """Top-level complex fields in document order: (instr text, [instrText elements], begin run)."""
    out, depth, cur = [], 0, None
    for r in body.iter(WR):
        fc = r.find("w:fldChar", NS)
        if fc is not None:
            t = fc.get(q("fldCharType"))
            if t == "begin":
                depth += 1
                if depth == 1:
                    cur = {"its": [], "begin": r, "sep": False}
            elif t == "separate" and depth == 1:
                cur["sep"] = True
            elif t == "end":
                depth -= 1
                if depth == 0 and cur:
                    out.append(("".join(i.text or "" for i in cur["its"]), cur["its"], cur["begin"]))
                    cur = None
            continue
        it = r.find("w:instrText", NS)
        if it is not None and cur is not None and depth == 1 and not cur["sep"]:
            cur["its"].append(it)
    return out


def _rewrite(pkg, its, new):
    """Put the whole instruction in the first instrText and empty the others (their runs stay)."""
    for it in its:
        p = next(it.iterancestors(WP))
        pkg.mark(p)
    its[0].text = f" {new} "
    its[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for it in its[1:]:
        it.text = ""


def toc_instr(std):
    levels = ",".join(f"{s},{n}" for s, n in std["toc"]["levels"])
    return f'TOC \\t "{levels}" ' + " ".join(std["toc"]["switches"])


def op_toc_field(pkg, std):
    pkg.touch(pkg.main)
    body = pkg.tree(pkg.main).find("w:body", NS)
    want = toc_instr(std)
    changes = []
    for instr, its, _b in _fields_with_instr_runs(body):
        n = _norm(instr)
        if not n.upper().startswith("TOC "):
            continue
        sw = D._toc_switches(n)
        if ("c" in sw or "f" in sw) and "t" not in sw and "o" not in sw:
            continue                                       # a list of tables or figures, not the main TOC
        if n != _norm(want):
            _rewrite(pkg, its, want)
            changes.append((pkg.main, n, _norm(want)))
    return {"rewritten": len(changes), "field_changes": changes, "after": "Update entire table in Word", "checks": []}


def op_toc_styles(pkg, std):
    from prodengine.engine.ops.word_ops import find_style, new_style
    sp = pkg.word_part("/styles")
    pkg.touch(sp)
    root = pkg.tree(sp)
    done = []
    for name, v in std["toc"]["entry_styles"].items():
        s = find_style(root, name)
        if s is None:
            s = new_style(root, name, based_on="Normal")
        pkg.mark(s)
        ppr = ensure(s, "pPr")
        remove(ppr, "tabs", "ind")
        tabs = ensure(ppr, "tabs")
        if v["text_at"] > v["number_at"]:
            t1 = etree.SubElement(tabs, q("tab")); t1.set(q("val"), "left"); t1.set(q("pos"), str(int(round(v["text_at"] * 1440))))
        pos, align, leader = v["tab"]
        t2 = etree.SubElement(tabs, q("tab")); t2.set(q("val"), align); t2.set(q("leader"), leader)
        t2.set(q("pos"), str(int(round(pos * 1440))))
        ind = ensure(ppr, "ind")
        ind.set(q("left"), str(int(round(v["text_at"] * 1440))))
        ind.set(q("hanging"), str(int(round((v["text_at"] - v["number_at"]) * 1440))))
        ind.set(q("right"), str(int(round(v["right_indent"] * 1440))))
        au = s.find("w:autoRedefine", NS)                  # "Automatically update" off on TOC styles
        if au is not None:
            s.remove(au)
        done.append(name)
    return {"styles": done, "checks": []}


def op_xref_switches(pkg, std, link=True):
    pkg.touch(pkg.main)
    body = pkg.tree(pkg.main).find("w:body", NS)
    changes = []
    for instr, its, _b in _fields_with_instr_runs(body):
        n = _norm(instr)
        k = n.split()[0].upper() if n else ""
        if k not in ("REF", "PAGEREF"):
            continue
        new = n.replace("\\* MERGEFORMAT", "\\* CHARFORMAT")
        if k == "REF" and "\\* CHARFORMAT" not in new:
            new += " \\* CHARFORMAT"
        if link and "\\h" not in new.split():
            parts = new.split(); parts.insert(2, "\\h"); new = " ".join(parts)
        if new != n:
            _rewrite(pkg, its, new)
            changes.append((pkg.main, n, new))
    return {"rewritten": len(changes), "field_changes": changes, "checks": []}


def op_caption_fields(pkg, std):
    """SEQ identifier and STYLEREF chapter part of every field caption, to the rule of its part."""
    pkg.touch(pkg.main)
    root = pkg.tree(pkg.main)
    body = root.find("w:body", NS)
    dm = D.build(pkg, std)
    rules = {(c["label"], c["part"]): c for c in std["captions"]}
    caption_paras = {dm.paras[c.para].el: (c, rules[(c.label, c.part)]) for c in dm.captions if not c.typed}
    changes = []
    for instr, its, b in _fields_with_instr_runs(body):
        p = next(b.iterancestors(WP), None)
        if p not in caption_paras:
            continue
        c, r = caption_paras[p]
        n = _norm(instr)
        lvl = r["chapter_level"]
        if n.upper().startswith("SEQ "):
            parts = n.split()
            from prodengine.pe.fixes2 import seq_format
            fmt = seq_format(r)
            want = f"SEQ {r['identifier']} \\* {fmt}" + (f" \\s {lvl}" if lvl else "")
            have_fmt = next((parts[i + 1] for i, x in enumerate(parts[:-1]) if x == "\\*"), "ARABIC")
            if parts[1] != r["identifier"] or (lvl and f"\\s {lvl}" not in n) or have_fmt != fmt:
                _rewrite(pkg, its, want)
                changes.append((pkg.main, n, _norm(want)))
        elif n.upper().startswith("STYLEREF ") and lvl:
            want = "STYLEREF 7 \\n \\t" if lvl == 7 else f"STYLEREF {lvl} \\s"
            if n != want:
                _rewrite(pkg, its, want)
                changes.append((pkg.main, n, want))
    return {"rewritten": len(changes), "field_changes": changes, "after": "Update fields in Word", "checks": []}


def op_caption_after(pkg, std):
    """'Table 1-3. Title' -> 'Table 1-3.<tab>Title' where the rule is period_tab. Only the one space changes."""
    pkg.touch(pkg.main)
    dm = D.build(pkg, std)
    rules = {(c["label"], c["part"]): c for c in std["captions"]}
    fixed = 0
    for c in dm.captions:
        r = rules[(c.label, c.part)]
        if r["after_number"] != "period_tab" or c.after != "period_space" or c.typed:
            continue
        p = dm.paras[c.para].el
        before = visible_text(p)
        depth, instr, seen = 0, "", False
        for run in list(p.iter(WR)):
            fc = run.find("w:fldChar", NS)
            if fc is not None:
                t = fc.get(q("fldCharType"))
                depth += {"begin": 1, "end": -1}.get(t, 0)
                if t == "begin" and depth == 1:
                    instr = ""
                if t == "end" and depth == 0 and instr.strip().upper().startswith("SEQ"):
                    seen = True
                continue
            it = run.find("w:instrText", NS)
            if it is not None:
                instr += it.text or ""; continue
            if seen and depth == 0:
                t = run.find("w:t", NS)
                if t is not None and (t.text or "").startswith(". "):
                    pkg.mark(p)
                    rest = t.text[2:]
                    t.text = "."
                    tab = etree.Element(q("tab"))
                    t.addnext(tab)
                    if rest:
                        t2 = etree.Element(WT); t2.text = rest
                        if rest != rest.strip():
                            t2.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
                        tab.addnext(t2)
                    fixed += 1
                break
        after = visible_text(p)
        if after.replace("\t", " ") != before.replace("\t", " ") and after.replace(".\t", ". ", 1) != before:
            raise ValueError("caption text changed beyond the space after the number")
    return {"fixed": fixed, "checks": []}


def op_scope_reset(pkg, std, names=("Response", "Appendices")):
    """Response: from the first Heading 1 to the end of the last paragraph before the first Heading 7.
    Appendices: from the first Heading 7 to the end of the last paragraph. Other bookmarks are not touched."""
    pkg.touch(pkg.main)
    root = pkg.tree(pkg.main)
    body = root.find("w:body", NS)
    dm = D.build(pkg, std)
    h1 = next((h for h in dm.headings if h.level == 1), None)
    h7 = dm.paras[dm.first_appendix] if dm.first_appendix >= 0 else None
    paras = [p for p in dm.paras if not p.in_table]
    last_body = next((p for p in reversed(paras) if h7 is None or p.i < h7.i), None)
    last = paras[-1] if paras else None
    done = []
    for name in names:
        starts = [b for b in body.iter(q("bookmarkStart")) if b.get(q("name")) == name]
        if not starts:
            continue
        bid = starts[0].get(q("id"))
        ends = [e for e in body.iter(q("bookmarkEnd")) if e.get(q("id")) == bid]
        if name.lower().startswith(("response", "body", "volume")):
            a, z = h1, last_body
        else:
            a, z = h7, last
        if a is None or z is None:
            continue
        for el in starts + ends:
            par = el.getparent()
            pkg.mark(par)
            par.remove(el)
        s = etree.Element(q("bookmarkStart")); s.set(q("id"), bid); s.set(q("name"), name)
        ppr = a.el.find("w:pPr", NS)
        a.el.insert(1 if ppr is not None else 0, s)
        e = etree.Element(q("bookmarkEnd")); e.set(q("id"), bid)
        z.el.append(e)
        pkg.mark(a.el); pkg.mark(z.el)
        done.append(name)
    return {"reset": done, "checks": []}
