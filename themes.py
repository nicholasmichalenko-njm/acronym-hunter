"""Win themes and discriminators (3.2.0): the effort's themes as agreed at kickoff (the benefit to the customer, the
discriminator that only we offer, and the proof points behind it), linked to the sections that must carry them and,
when one answers it, to a customer hot button. Check the drafts reads the volume drafts and says, theme by theme and
section by section, where each theme's words appear and where they are missing, so themes do not drift. Kept in the
effort record. Rules only: plain word matching, no AI and no ML."""
import datetime, getpass, re, uuid

KINDS = ("Win theme", "Discriminator")
_STOP = set("""a an and are as at be by for from has have in into is it its of on or our that the their them this to we
with will your you than then also more most very can all each any per via""".split())


def _now():
    return datetime.datetime.now().isoformat(timespec="minutes")


def _clean(v, n=600):
    return " ".join(str(v or "").split())[:n]


def items(rec):
    return sorted((t for t in rec.data.get("themes", []) if isinstance(t, dict)), key=lambda t: t.get("order", 0))


def get(rec, tid):
    return next((t for t in rec.data.get("themes", []) if t.get("id") == tid), None)


def guess_words(title, statement=""):
    """Words to look for in the drafts: the title's meaningful words (or the statement's, when the title is short)."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", title or "") if w.lower() not in _STOP]
    if len(words) < 2:
        words += [w for w in re.findall(r"[A-Za-z][A-Za-z0-9\-]{4,}", statement or "") if w.lower() not in _STOP][:3]
    return list(dict.fromkeys(w.lower() for w in words))[:6]


def add(rec, title, statement="", kind="Win theme", discriminator="", proof=(), sections=(), hot="", words=None, who=None):
    title = _clean(title, 160)
    if not title:
        return ""
    ts = rec.data.setdefault("themes", [])
    t = {"id": uuid.uuid4().hex[:10], "title": title, "kind": kind if kind in KINDS else "Win theme",
         "statement": _clean(statement, 1200), "discriminator": _clean(discriminator, 600),
         "proof": [p for p in (_clean(x, 400) for x in proof) if p], "sections": [s for s in sections if s],
         "hot": hot or "", "words": [w for w in (words if words is not None else guess_words(title, statement)) if w],
         "order": 1 + max([x.get("order", 0) for x in ts] or [0]), "who": who or getpass.getuser(), "at": _now()}
    ts.append(t)
    rec.log("effort", f"{t['kind']}: {title}", ref={"theme": t["id"]}, who=who)
    rec.save()
    return t["id"]


def update(rec, tid, who=None, **fields):
    t = get(rec, tid)
    if t is None:
        return False
    changed = False
    for k, v in fields.items():
        if k in ("title", "statement", "discriminator", "hot"):
            v = _clean(v, 1200)
            if k == "title" and not v:
                continue
        elif k == "kind":
            if v not in KINDS:
                continue
        elif k in ("proof", "sections", "words"):
            v = [x for x in (_clean(y, 400) for y in v) if x]
        else:
            continue
        if t.get(k) != v:
            t[k] = v
            changed = True
    if changed:
        rec.log("effort", f"{t['kind']} changed: {t['title']}", ref={"theme": tid}, who=who)
        rec.save()
    return changed


def remove(rec, tid, who=None):
    t = get(rec, tid)
    if t is None:
        return False
    rec.data["themes"] = [x for x in rec.data.get("themes", []) if x.get("id") != tid]
    rec.log("effort", f"{t['kind']} removed: {t['title']}", who=who)
    rec.save()
    return True


def move(rec, tid, step):
    ts = items(rec)
    i = next((k for k, t in enumerate(ts) if t["id"] == tid), None)
    j = (i if i is not None else 0) + step
    if i is None or not 0 <= j < len(ts):
        return False
    ts[i], ts[j] = ts[j], ts[i]
    for k, t in enumerate(ts, 1):
        t["order"] = k
    rec.save()
    return True


def for_section(rec, label):
    return [t for t in items(rec) if label in t.get("sections", [])]


# ------------------------------------------------------------------ the drafts
def draft_sections(path, labels):
    """{section label or "": text} from a .docx draft: each Heading paragraph that matches a section of the structure
    starts that section (by its number, or its title); text before any matching heading goes under ""."""
    import setupdoc as SD
    paras = SD.docx_paragraphs(path)
    keys = []
    for lab in labels:
        num = (lab.split()[0] if lab and re.match(r"^[A-Z]?[\d.]+[A-Za-z]?$", lab.split()[0]) else "")
        title = re.sub(r"^\S+\s+", "", lab) if num else lab
        keys.append((lab, num.rstrip(".").lower(), title.lower().strip()))
    out, cur = {"": []}, ""
    for text, style, level in paras:
        t = " ".join((text or "").split())
        heading = level is not None or (style or "").lower().startswith(("heading", "berschrift", "titre"))
        if heading and t:
            tl = t.lower()
            hit = next((lab for lab, num, title in keys if (num and (tl.startswith(num + " ") or tl.startswith(num + ".") or tl == num))
                        or (title and len(title) > 3 and (tl == title or tl.endswith(" " + title) or title in tl))), None)
            if hit:
                cur = hit
                out.setdefault(cur, [])
                continue
        out.setdefault(cur, []).append(t)
    return {k: " ".join(v) for k, v in out.items()}


def _count(words, text):
    tl = (text or "").lower()
    return sum(len(re.findall(r"\b" + re.escape(w.lower()) + r"\b", tl)) for w in words if w)


def check(rec, drafts, labels):
    """Theme by theme: where its words appear in the drafts. drafts: [(volume name, .docx path)]. Returns
    [{"id", "title", "words", "found": {volume: count}, "sections": {label: count} (the theme's own sections),
    "missing": [linked sections where the words never appear], "total"}]."""
    read = []
    for vol, path in drafts:
        try:
            read.append((vol, draft_sections(path, labels)))
        except Exception:
            continue
    out = []
    for t in items(rec):
        words = t.get("words") or guess_words(t["title"], t.get("statement", ""))
        found, secs = {}, {s: 0 for s in t.get("sections", [])}
        for vol, parts in read:
            n = sum(_count(words, txt) for txt in parts.values())
            if n:
                found[vol] = n
            for s in secs:
                secs[s] += _count(words, parts.get(s, ""))
        out.append({"id": t["id"], "title": t["title"], "words": words, "found": found, "sections": secs,
                    "missing": [s for s, n in secs.items() if not n], "total": sum(found.values())})
    return out
