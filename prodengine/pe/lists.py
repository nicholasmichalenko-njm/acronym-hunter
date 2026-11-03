"""Lists and numbering cleanup: what writers' copy and paste leaves behind, mapped to the team list styles.

scan(pkg, std) -> ListMap   read only: every list paragraph with what it is now and what it should become
audit(lm, std) -> [Finding] area "lists"
op_lists(pkg, std, answers=None, only=None)   the fix, on the guarded write path

What it finds (rule):
  L1 typed bullet at the start of a paragraph (a character, a Symbol-font bullet, a dash), then a tab or spaces
  L2 typed number or letter (1. 1) (1) a. a) (a) i. (i) A.)
  L3 Word numbering that came in with pasted text (a list definition that is not the team's), or a list on a
     paragraph that is not in a team list style
  L4 manual indents on a list paragraph (the list level owns the positions, TabsLists)
  L5 a numbered list that continues from the list before it. After a heading it always restarts (sure); after a
     typed "1." or "a." it restarts (sure); after body text only, it is a question
  L6 a typed number inside a numbered heading ("2.1 Approach" under Heading 2 shows "2.1 2.1 Approach")
  L7 a typed list inside a table cell (report: table lists use the table text styles)
  L8 list definitions in the file that no paragraph uses (report)

Every change keeps the words: removing a typed prefix is the only text change, and the op proves for each
paragraph that the new text is the old text minus exactly that prefix.
"""
import re
from dataclasses import dataclass, field

from lxml import etree
from prodengine.engine.pkg import NS
from prodengine.engine.ordered import q, local, ensure, remove, insert_ordered
from prodengine.engine.fingerprint import visible_text
from prodengine.pe.sections import canon_style

BULLET_LEVEL = {"•": 1, "·": 1, "": 1, "*": 1, "-": 1, "–": 1, "➢": 1,
                "o": 2, "◦": 2, "‣": 2, "▪": 3, "": 3}
ROMAN = re.compile(r"^(i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii)$")
NUM_RX = re.compile(r"^\s*(\(?)(\d{1,2}|[a-zA-Z]|[ivx]{1,5})([.)])([\t ]+)")
HEAD_NUM_RX = re.compile(r"^\s*((?:\d+|[A-Z])(?:\.\d+)*\.?)([\t ]+)")


@dataclass
class Item:
    para: int
    style: str
    text: str
    kind: str               # typed_bullet | typed_number | word_list | team | heading_typed | table_typed
    prefix: str = ""        # the typed characters to remove
    marker: str = ""        # what the prefix reads as (1, a, iii, bullet char)
    num_kind: str = ""      # decimal | letter | roman | bullet
    level: int = 1
    target: str = ""        # team style it becomes
    num_id: str = ""
    ilvl: int = 0
    direct_ind: bool = False
    foreign: bool = False   # Word numbering from a definition that is not the team's
    direct_num: str = ""    # numId set on the paragraph itself (a decision kept in the file)
    block: int = -1
    el: object = None


@dataclass
class Block:
    id: int
    items: list
    numbered: bool
    after: str              # what sits before it: heading | text | start | list
    restart: str            # sure | ask | no | first
    why: str = ""
    shows_from: int = 1     # the number the first item shows after the fix
    start: int = 0          # the start the fix writes (0: none decided)


@dataclass
class ListMap:
    items: list
    blocks: list
    unused_defs: int
    team_nums: dict         # style -> numId
    stats: dict = field(default_factory=dict)


# ---------------------------------------------------------------- numbering part
def _numbering(pkg):
    part = pkg.word_part("/numbering")
    if not part:
        return None, {}, {}
    root = pkg.tree(part)
    abstract = {}
    for a in root.findall("w:abstractNum", NS):
        lv = {}
        for l in a.findall("w:lvl", NS):
            f = l.find("w:numFmt", NS)
            lv[int(l.get(q("ilvl")))] = f.get(q("val")) if f is not None else "decimal"
        abstract[a.get(q("abstractNumId"))] = lv
    nums = {}
    for n in root.findall("w:num", NS):
        a = n.find("w:abstractNumId", NS)
        so = n.find("w:lvlOverride[@w:ilvl='0']/w:startOverride", NS)
        nums[n.get(q("numId"))] = {"abstract": a.get(q("val")) if a is not None else None,
                                   "override": n.find("w:lvlOverride", NS) is not None,
                                   "start": so.get(q("val")) if so is not None else None}
    return part, abstract, nums


def _style_info(pkg):
    sp = pkg.word_part("/styles")
    names, style_num = {}, {}
    for s in pkg.tree(sp).findall("w:style", NS):
        n = s.find("w:name", NS)
        if n is None:
            continue
        nm = canon_style(n.get(q("val")))
        names[s.get(q("styleId"))] = nm
        ni = s.find("w:pPr/w:numPr/w:numId", NS)
        if ni is not None:
            style_num[nm] = ni.get(q("val"))
    ids = {v: k for k, v in names.items()}
    return names, style_num, ids


def _tokens(p):
    """The paragraph's leading visible characters as (element, text) tokens, outside fields."""
    out, depth = [], 0
    for r in p.iter(q("r")):
        if next(r.iterancestors(q("del")), None) is not None:
            continue
        fc = r.find("w:fldChar", NS)
        if fc is not None:
            t = fc.get(q("fldCharType"))
            depth += {"begin": 1, "end": -1}.get(t, 0)
            if depth > 0 or t == "end":
                return out if depth >= 0 else out      # a field at the start ends the prefix search
            continue
        for c in r:
            n = local(c)
            if n == "t":
                out.append((c, c.text or ""))
            elif n == "tab":
                out.append((c, "\t"))
            elif n == "sym":
                ch = chr(int(c.get(q("char"), "F0B7"), 16))
                out.append((c, ch))
        if sum(len(t) for _, t in out) > 12:
            break
    return out


def _lead(p):
    return "".join(t for _, t in _tokens(p))


def _bullet_prefix(s):
    m = re.match(r"^\s*([•·▪◦‣➢*\-–\uf0b7\uf0a7\uf0d8\uf0fc\uf076\uf075\uf06c\uf06e])([\t ]+)", s)   # 3.32.1: Symbol and Wingdings bullets too
    if m:
        return m.group(0), m.group(1)
    m = re.match(r"^\s*(o)(\t)", s)                       # a Word "o" bullet pasted as text, only with a tab
    if m:
        return m.group(0), m.group(1)
    return None, None


def _num_kind(tok, prev_kind):
    if tok.isdigit():
        return "decimal"
    if ROMAN.match(tok.lower()) and not (prev_kind == "letter" and len(tok) == 1):
        return "roman" if tok.islower() else ("roman" if len(tok) > 1 else "letter")
    return "letter"


def _ind(ppr):
    return ppr is not None and ppr.find("w:ind", NS) is not None


# ---------------------------------------------------------------- scan
def scan(pkg, std, answers=None):
    L = std["lists"]
    names, style_num, ids = _style_info(pkg)
    _part, abstract, nums = _numbering(pkg)
    team_styles = L["bullet_styles"] + L["number_styles"]
    team_abs = {nums.get(style_num.get(s), {}).get("abstract") for s in team_styles} - {None}
    headings = set(L["heading_styles"])
    skip = set(L["skip_styles"])
    body = pkg.tree(pkg.main).find("w:body", NS)
    items, seq = [], []                 # seq: per body paragraph, the item or a marker of what it is
    prev_kind = ""
    used_nums = set()
    for i, p in enumerate(body.iter(q("p"))):
        ppr = p.find("w:pPr", NS)
        ps = ppr.find("w:pStyle", NS) if ppr is not None else None
        style = names.get(ps.get(q("val")), ps.get(q("val"))) if ps is not None else "Normal"
        npr = ppr.find("w:numPr/w:numId", NS) if ppr is not None else None
        ilvl_el = ppr.find("w:numPr/w:ilvl", NS) if ppr is not None else None
        num_id = npr.get(q("val")) if npr is not None else ""
        if num_id and num_id != "0":
            used_nums.add(num_id)
        in_table = next(p.iterancestors(q("tbl")), None) is not None
        text = " ".join(visible_text(p).replace("¶", " ").split())
        lead = _lead(p)
        if style in headings:
            m = HEAD_NUM_RX.match(lead)
            numbered_style = style in style_num or (num_id and num_id != "0")
            if m and numbered_style:
                items.append(Item(i, style, text, "heading_typed", prefix=m.group(0), marker=m.group(1), el=p))
            seq.append(("heading", None)); prev_kind = ""
            continue
        if style in skip or not text:
            seq.append(("other" if text else "empty", None))
            continue
        bp, bch = _bullet_prefix(lead)
        nm = NUM_RX.match(lead) if not bp else None
        it = None
        if bp:
            lvl = BULLET_LEVEL.get(bch, 1)
            it = Item(i, style, text, "typed_bullet", prefix=bp, marker=bch, num_kind="bullet", level=lvl)
        elif nm and (nm.group(1) == "" or nm.group(3) == ")"):
            tok = nm.group(2)
            k = _num_kind(tok, prev_kind)
            prev_kind = k
            it = Item(i, style, text, "typed_number", prefix=nm.group(0), marker=tok, num_kind=k,
                      level=L["number_levels"][k])
        elif num_id and num_id != "0" or style in style_num and style in team_styles:
            nid = num_id or style_num.get(style, "")
            a = nums.get(nid, {}).get("abstract")
            ilvl = int(ilvl_el.get(q("val"))) if ilvl_el is not None else 0
            fmt = abstract.get(a, {}).get(ilvl, "decimal")
            foreign = bool(num_id and num_id != "0") and (a not in team_abs or style not in team_styles)
            kind = "bullet" if fmt == "bullet" else ("letter" if "Letter" in fmt else ("roman" if "Roman" in fmt else "decimal"))
            it = Item(i, style, text, "word_list" if foreign else "team", num_kind=kind, num_id=nid, ilvl=ilvl,
                      level=min(3, ilvl + 1) if foreign else (team_styles.index(style) % 3 + 1 if style in team_styles else 1),
                      foreign=foreign)
        if it is None:
            seq.append(("text", None)); prev_kind = "" if style not in team_styles else prev_kind
            continue
        it.el = p
        it.direct_ind = _ind(ppr)
        it.direct_num = num_id if num_id and num_id != "0" else ""
        if in_table:
            if it.kind in ("typed_bullet", "typed_number"):
                it.kind = "table_typed"
                items.append(it)
            seq.append(("other", None))
            continue
        if it.kind != "team" or it.style not in team_styles:
            fam = L["bullet_styles"] if it.num_kind == "bullet" else L["number_styles"]
            it.target = fam[min(it.level, 3) - 1]
        else:
            it.target = it.style
        items.append(it)
        seq.append(("list", it))
    # blocks of consecutive list paragraphs; a numbered block's restart status
    blocks, cur, before = [], None, "start"
    last_numbered = None
    counts = {}
    for kind, it in seq:
        if kind == "list":
            if cur is None:
                cur = Block(len(blocks), [], False, before, "no")
                blocks.append(cur)
            it.block = cur.id
            cur.items.append(it)
            continue
        if kind == "empty":
            continue
        if cur is not None:
            cur = None
        before = "heading" if kind == "heading" else "text"
    for b in blocks:
        top = [x for x in b.items if x.level == 1 and x.num_kind != "bullet"]
        b.numbered = bool(top)
        if not b.numbered:
            continue
        first = top[0]
        base = style_num.get(first.target)
        if first.kind == "team" and first.direct_num and base and first.direct_num != base \
                and nums.get(first.direct_num, {}).get("start"):
            b.restart, b.start = "done", int(nums[first.direct_num]["start"])
            b.why = f"Starts at {b.start}"
        elif first.kind == "typed_number":
            b.start = _marker_value(first.marker)
            b.restart = "first" if last_numbered is None and b.start == 1 else "typed"
            b.why = f"The writer typed {first.marker}"
        elif last_numbered is None:
            b.restart, b.why, b.start = "first", "The first numbered list", 1
        elif b.after == "heading" and std["lists"].get("restart_after_heading", True):
            b.restart, b.why, b.start = "sure", "A list after a heading starts at 1", 1
        elif first.kind == "word_list":
            b.restart, b.why, b.start = "sure", "It was numbered as its own list where it was pasted from", 1
        else:
            b.restart, b.why = "ask", "Body text sits between this list and the one before it"
        last_numbered = b
    _simulate(blocks, answers or {})
    unused = len({k for k in nums if k not in used_nums and k not in set(style_num.values())})
    lm = ListMap(items, blocks, unused, {s: style_num.get(s) for s in team_styles})
    lm.stats = {"items": len(items), "blocks": len(blocks), "numbered_blocks": sum(b.numbered for b in blocks)}
    return lm


def _marker_value(m):
    if m.isdigit():
        return int(m)
    if ROMAN.match(m.lower()) and len(m) > 1:
        return {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10}.get(m.lower(), 1)
    return ord(m.lower()) - 96


def _simulate(blocks, answers):
    """The number each numbered list shows first after the fix. Every decided list gets its own explicit start
    (startOverride), so the result does not depend on how Word or another reader counts shared lists. Continue
    means: one after the last number of the list before it in the same style."""
    last = {}
    for b in blocks:
        if not b.numbered:
            continue
        top = [x for x in b.items if x.level == 1 and x.num_kind != "bullet"]
        tgt = top[0].target
        if b.restart == "ask":
            b.start = 1 if answers.get(b.id) == "restart" else (last.get(tgt, 0) + 1 if answers.get(b.id) == "continue" else 0)
            b.shows_from = b.start or last.get(tgt, 0) + 1
        else:
            b.shows_from = b.start or 1
        last[tgt] = b.shows_from - 1 + len(top)


# ---------------------------------------------------------------- audit
def audit(lm, std):
    from prodengine.pe.docmap import Finding
    out = []
    groups = {}
    for it in lm.items:
        if it.kind == "typed_bullet":
            groups.setdefault(("L1", it.block), []).append(it)
        elif it.kind == "typed_number":
            groups.setdefault(("L2", it.block), []).append(it)
        elif it.kind == "word_list":
            groups.setdefault(("L3", it.block), []).append(it)
        elif it.kind == "heading_typed":
            out.append(Finding("lists", "error", "L6", f"{it.style} \"{it.text[:50]}\" has a typed number \"{it.marker}\" as well as "
                                                       f"the heading number", it.para, "op_lists", "heading"))
        elif it.kind == "table_typed":
            out.append(Finding("lists", "info", "L7", f"Typed list in a table cell: \"{it.text[:50]}\"", it.para, "", "table"))
        if it.kind in ("team", "word_list", "typed_bullet", "typed_number") and it.direct_ind:
            groups.setdefault(("L4", it.block), []).append(it)
    words = {"L1": ("starts with a typed bullet", "start with a typed bullet"),
             "L2": ("starts with a typed number or letter", "start with a typed number or letter"),
             "L3": ("uses list numbering pasted from another document", "use list numbering pasted from another document"),
             "L4": ("carries manual indents", "carry manual indents")}
    for (rule, blk), its in groups.items():
        tgt = sorted({x.target for x in its if x.target})
        out.append(Finding("lists", "error" if rule != "L4" else "warning", rule,
                           f"{len(its)} paragraph{'s' if len(its) > 1 else ''} {words[rule][len(its) > 1]} (list {blk + 1}); "
                           f"they become {', '.join(tgt)}", its[0].para, "op_lists", f"block{blk}"))
    for b in lm.blocks:
        if b.restart == "sure":
            out.append(Finding("lists", "error", "L5", f"List {b.id + 1} continues the numbering of the list before it. {b.why}.",
                               b.items[0].para, "op_lists", f"block{b.id}"))
        elif b.restart == "ask":
            out.append(Finding("lists", "warning", "L5?", f"List {b.id + 1}: {b.why}. Restart at 1, or continue at "
                                                          f"{b.shows_from}?", b.items[0].para, "ask", f"block{b.id}"))
    if lm.unused_defs:
        out.append(Finding("lists", "info", "L8", f"{lm.unused_defs} list definitions in the file are not used by any paragraph "
                                                  f"(pasted from other documents)", 0, "", "defs"))
    return out


# ---------------------------------------------------------------- fix
LISTS_ALLOWED = ("text", "text_len")      # typed prefixes only; proved per paragraph inside the op


def _remove_prefix(p, prefix):
    before = visible_text(p)
    left = len(prefix)
    removed = ""
    for el, t in _tokens(p):
        if left <= 0:
            break
        if local(el) == "t":
            take = min(left, len(t))
            removed += t[:take]
            el.text = t[take:]
            if el.text and el.text != el.text.strip():
                el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            left -= take
        else:
            removed += "\t" if local(el) == "tab" else "[sym:" + (el.get(q("char")) or "") + "]"
            el.getparent().remove(el)
            left -= 1
    after = visible_text(p)
    if after != before.replace(removed, "", 1):
        raise ValueError("a list prefix removal changed more than the prefix")
    return before, after


def _new_restart_num(pkg, base_num_id, start=1):
    part = pkg.word_part("/numbering")
    root = pkg.tree(part)
    pkg.touch(part)
    base = next(n for n in root.findall("w:num", NS) if n.get(q("numId")) == base_num_id)
    nid = str(max(int(n.get(q("numId"))) for n in root.findall("w:num", NS)) + 1)
    n = etree.SubElement(root, q("num")); n.set(q("numId"), nid)
    a = etree.SubElement(n, q("abstractNumId")); a.set(q("val"), base.find("w:abstractNumId", NS).get(q("val")))
    o = etree.SubElement(n, q("lvlOverride")); o.set(q("ilvl"), "0")
    so = etree.SubElement(o, q("startOverride")); so.set(q("val"), str(start))
    pkg.mark(n)
    return nid


def op_lists(pkg, std, answers=None, only=None):
    """answers: {block id: "restart" | "continue"} for the asked lists. only: rule keys to fix (default all)."""
    answers = answers or {}
    rules = set(only or ("L1", "L2", "L3", "L4", "L5", "L6"))
    pkg.touch(pkg.main)
    lm = scan(pkg, std, answers)
    names, style_num, ids = _style_info(pkg)
    held = {b.id for b in lm.blocks if b.restart == "ask" and not b.start}
    changed, prefixes = 0, 0
    for it in lm.items:
        p = it.el
        if it.kind == "heading_typed" and "L6" in rules:
            pkg.mark(p); _remove_prefix(p, it.prefix); prefixes += 1; changed += 1
            continue
        if it.kind not in ("typed_bullet", "typed_number", "word_list", "team"):
            continue
        if it.block in held and it.kind in ("typed_number", "word_list"):
            continue                     # the number it shows depends on the answer: change nothing yet
        want_rule = {"typed_bullet": "L1", "typed_number": "L2", "word_list": "L3", "team": "L4"}[it.kind]
        if want_rule not in rules and not (it.direct_ind and "L4" in rules):
            continue
        ppr = ensure(p, "pPr")
        touched = False
        if it.kind in ("typed_bullet", "typed_number") and want_rule in rules:
            pkg.mark(p); _remove_prefix(p, it.prefix); prefixes += 1; touched = True
        if it.kind != "team" and want_rule in rules:
            pkg.mark(p)
            ps = ensure(ppr, "pStyle"); ps.set(q("val"), ids.get(it.target, it.target.replace(" ", "")))
            remove(ppr, "numPr")
            touched = True
        if it.direct_ind and "L4" in rules:
            pkg.mark(p); remove(ppr, "ind"); touched = True
        if touched:
            changed += 1
    # restarts
    if "L5" in rules:
        for b in lm.blocks:
            if not b.numbered:
                continue
            if b.restart not in ("sure", "typed", "ask") or not b.start or b.id in held:
                continue                     # first list, already decided, or waiting for an answer
            top = [x for x in b.items if x.level == 1 and x.num_kind != "bullet"]
            base = style_num.get(top[0].target)
            if not base:
                continue
            nid = _new_restart_num(pkg, base, b.start)
            for x in b.items:
                if x.target == top[0].target and x.num_kind != "bullet":
                    pkg.mark(x.el)
                    ppr = ensure(x.el, "pPr")
                    npr = ensure(ppr, "numPr")
                    for c in list(npr):
                        npr.remove(c)
                    il = etree.SubElement(npr, q("ilvl")); il.set(q("val"), "0")
                    ni = etree.SubElement(npr, q("numId")); ni.set(q("val"), nid)
            changed += 1
    return {"paragraphs_changed": changed, "prefixes_removed": prefixes, "checks": []}
