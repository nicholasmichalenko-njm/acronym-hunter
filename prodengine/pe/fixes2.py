"""Round 4 fixes behind docmap findings.

  op_caption_typed(pkg, std)          C1: a typed caption number ("Table 1-3") becomes the team's fields
                                      { STYLEREF 1 \\s }-{ SEQ Table \\* ARABIC \\s 1 }. The field results are the
                                      typed characters, so the page reads the same until Word updates fields.
  op_toc_list_identifiers(pkg, std)   T5: a list scoped by a bookmark (\\b Response \\c "Table") collects by its
                                      caption identifier only ({ TOC \\h \\z \\c "Table" }); appendix captions use
                                      TableApp, so the body list needs no bookmark.
  op_xref_relink(pkg, std, mapping)   X1: REF and PAGEREF fields to a deleted target point to the target the
                                      person picked ({old bookmark: new bookmark}); the result updates in Word.
Every op declares its field changes exactly; the guard refuses anything else.
"""
import copy
import re

from lxml import etree
from prodengine.engine.pkg import NS
from prodengine.engine.ordered import q, local
from prodengine.engine.fingerprint import visible_text
from prodengine.pe import docmap as D
from prodengine.pe.fixes import _fields_with_instr_runs, _rewrite, _norm

XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
CAPTION_TYPED_ALLOWED = ("fields",)
LIST_ALLOWED = ("fields",)
RELINK_ALLOWED = ("fields",)


def _run_like(src, text=None, child=None):
    r = etree.Element(q("r"))
    rpr = src.find("w:rPr", NS)
    if rpr is not None:
        r.append(copy.deepcopy(rpr))
    if text is not None:
        t = etree.SubElement(r, q("t")); t.text = text
        if text != text.strip():
            t.set(XML_SPACE, "preserve")
    if child is not None:
        r.append(child)
    return r


def _field_runs(src, instr, result):
    out = []
    for kind in ("begin", "instr", "separate", "result", "end"):
        if kind in ("begin", "separate", "end"):
            fc = etree.Element(q("fldChar")); fc.set(q("fldCharType"), kind)
            out.append(_run_like(src, child=fc))
        elif kind == "instr":
            it = etree.Element(q("instrText")); it.text = f" {instr} "; it.set(XML_SPACE, "preserve")
            out.append(_run_like(src, child=it))
        else:
            out.append(_run_like(src, text=result))
    return out


def caption_instrs(rule):
    lvl = rule["chapter_level"]
    chap = ("STYLEREF 7 \\n \\t" if lvl == 7 else f"STYLEREF {lvl} \\s") if lvl else None
    seq = f"SEQ {rule['identifier']} \\* ARABIC" + (f" \\s {lvl}" if lvl else "")
    return chap, seq


def op_caption_typed(pkg, std):
    pkg.touch(pkg.main)
    dm = D.build(pkg, std)
    rules = {(c["label"], c["part"]): c for c in std["captions"]}
    changes, done, skipped = [], 0, []
    for c in dm.captions:
        if not c.typed:
            continue
        rule = rules[(c.label, c.part)]
        p = dm.paras[c.para].el
        before = visible_text(p)
        sep = re.escape(rule.get("separator", "-"))
        m = re.match(rf"^(\w+)\s+([A-Z]|\d+){sep}(\d+)", c.shown and f"{c.label} {c.shown}" or "")
        # find the run whose text holds the typed number
        target = None
        for t in p.iter(q("t")):
            k = (t.text or "").find(c.shown)
            if k >= 0:
                target = (t, k)
                break
        if target is None or not m:
            skipped.append(c.shown)                         # the number is split over runs: convert in Word
            continue
        t, k = target
        run = t.getparent()
        if len(run.findall("w:t", NS)) != 1 or [x for x in run if local(x) not in ("rPr", "t")]:
            skipped.append(c.shown)
            continue
        chap_text, num_text = m.group(2), m.group(3)
        chap_i, seq_i = caption_instrs(rule)
        pre, post = t.text[:k], t.text[k + len(c.shown):]
        new = []
        if pre:
            new.append(_run_like(run, pre))
        if chap_i:
            new += _field_runs(run, chap_i, chap_text)
            new.append(_run_like(run, rule.get("separator", "-")))
            changes.append((pkg.main, None, _norm(chap_i)))
        else:
            new.append(_run_like(run, chap_text + rule.get("separator", "-")))
        new += _field_runs(run, seq_i, num_text)
        changes.append((pkg.main, None, _norm(seq_i)))
        if post:
            new.append(_run_like(run, post))
        pkg.mark(p)
        for el in new:
            run.addprevious(el)
        run.getparent().remove(run)
        if visible_text(p) != before:
            raise ValueError("a caption's visible text changed")
        done += 1
    return {"converted": done, "skipped_split_runs": skipped, "field_changes": changes,
            "after": "Update fields in Word to renumber", "checks": []}


def op_toc_list_identifiers(pkg, std):
    pkg.touch(pkg.main)
    body = pkg.tree(pkg.main).find("w:body", NS)
    changes = []
    for instr, its, _b in _fields_with_instr_runs(body):
        n = _norm(instr)
        if not n.upper().startswith("TOC "):
            continue
        sw = D._toc_switches(n)
        if "b" not in sw or not ("c" in sw or "f" in sw):
            continue
        new = re.sub(r'\s*\\b\s+("[^"]*"|\S+)', "", n)
        new = _norm(new)
        if new != n:
            _rewrite(pkg, its, new)
            changes.append((pkg.main, n, new))
    return {"rewritten": len(changes), "field_changes": changes, "after": "Update entire table in Word", "checks": []}


def op_xref_relink(pkg, std, mapping):
    pkg.touch(pkg.main)
    body = pkg.tree(pkg.main).find("w:body", NS)
    names = {b.get(q("name")) for b in body.iter(q("bookmarkStart"))}
    for old, new in mapping.items():
        if new not in names:
            raise ValueError(f"the new target {new} is not a bookmark in this document")
    changes = []
    for instr, its, _b in _fields_with_instr_runs(body):
        n = _norm(instr)
        parts = n.split()
        if len(parts) > 1 and parts[0].upper() in ("REF", "PAGEREF", "NOTEREF") and parts[1] in mapping:
            parts[1] = mapping[parts[1]]
            new = " ".join(parts)
            _rewrite(pkg, its, new)
            changes.append((pkg.main, n, new))
    return {"relinked": len(changes), "field_changes": changes, "after": "Update fields in Word", "checks": []}
