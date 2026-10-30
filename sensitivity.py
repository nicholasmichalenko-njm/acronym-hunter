"""Sensitivity of documents and efforts (2.97.0): one scale, read from what a file carries.

    General business < Proprietary < CUI < Confidential < Secret < Top Secret

- An effort's declared sensitivity (Effort Home > Edit details: Not CUI, CUI, Proprietary, the team's own words) is
  read onto the scale by its words.
- A document's level is the highest of:
  - its embedded label: Microsoft Purview sensitivity labels stored in Word, Excel and PowerPoint files
    (docProps/custom.xml, MSIP_Label_..._Name) and in PDFs (their XMP metadata). A label name is read by its words;
    a label called only "Confidential" is a business label (Proprietary) unless the team maps it otherwise, because
    that is what Purview's default labels mean;
  - its visible classification markings: a banner line that is only a marking ("SECRET//NOFORN", "TOP SECRET//SCI",
    "CONFIDENTIAL"), a classification authority block ("Classified By:", "Derived From:", "Declassify On:"), or
    portion marks with controls ((S//NF), (C//REL TO USA)), or classified ones with (U) marks beside them. Ordinary RFP
    text (FAR paragraphs lettered (C), a quote headed CONFIDENTIAL) does not count: see markings().
    A CUI banner or portion mark (CUI, CUI//SP-PROPIN, (CUI)) is CUI.
  - Pictures carry no standard label: only the words read from them count.
- unknown: nothing found. Then the effort's declared level decides; with none declared, training refuses it.

This is a safety net, not a control: an unmarked or wrongly marked document cannot be detected. Rules only (No AI);
standard library only; nothing leaves the PC.
"""
import re
import zipfile

LEVELS = ("General business", "Proprietary", "CUI", "Confidential", "Secret", "Top Secret")
RANK = {n: i for i, n in enumerate(LEVELS)}
GB, PROP, CUI, CONF, SECRET, TS = range(6)
TRAINING_MAX = CUI                  # the highest level training may ever see
READ_MAX = CUI                      # the highest level a regular (not SCIF-ready) install may read

_BANNER = re.compile(r"^\W*(TOP\s+SECRET|SECRET|CONFIDENTIAL)(?://[A-Z0-9 ,/\-]+)?\W*$")
_AUTH = re.compile(r"\b(?:Classified\s+By|Derived\s+From|Declassify\s+On|Classification\s+Authority)\s*:", re.I)
_PORTION = re.compile(r"(?:^|\s)\((TS|S|C)(?://[A-Z0-9 ,/\-]+)?\)(?=\s)")
_UPORTION = re.compile(r"(?:^|\s)\((?:U|U//[A-Z ,/\-]+|CUI(?://[A-Z0-9 ,/\-]+)?)\)(?=\s)")
_CUI = re.compile(r"(?:^|\W)(?:CUI(?://[A-Z0-9 ,/\-]+)?|\(CUI(?://[A-Z0-9 ,/\-]+)?\)|CONTROLLED\s+UNCLASSIFIED\s+INFORMATION)(?=\W|$)")
_TRADE = re.compile(r"\btrade\s+secrets?\b", re.I)


def level_of_words(text, confidential_is="Proprietary"):
    """A label or a declared sensitivity, read onto the scale by its words: -1 when it says nothing known."""
    t = " ".join(str(text or "").split()).lower()
    if not t:
        return -1
    t = _TRADE.sub(" ", t)
    if re.search(r"\btop\s*secret\b|\bts\b|\bsci\b", t):
        return TS
    if re.search(r"\bsecret\b", t):
        return SECRET
    if re.search(r"\bconfidential\b", t) and re.search(r"\bclassified\b|//", t):
        return CONF
    if re.search(r"\bnot\s+cui\b|\bnon-?cui\b|\bno\s+cui\b", t):
        return GB
    if re.search(r"\bcui\b|controlled unclassified|\bfouo\b|for official use only|\bsbu\b", t):
        return CUI
    if re.search(r"\bconfidential\b", t):
        return RANK.get(confidential_is, PROP)
    if re.search(r"proprietary|internal|company|business sensitive|competition sensitive|source selection", t):
        return PROP
    if re.search(r"not cui|unclassified|public|general|non-sensitive|nonsensitive|\bnone\b", t):
        return GB
    return -1


class Spill(Exception):
    """A document marked above CUI on an install that is not SCIF-ready: everything stops, nothing is copied or kept."""

    def __init__(self, fname, info):
        super().__init__(fname)
        self.name, self.info = fname, info

    def text(self):
        return spill_text(self.name, self.info)


def guard(path, lines=None):
    """The spill guard (2.97.0): on an install that is not SCIF-ready, a document marked above CUI raises Spill before
    anything is copied. Returns the document's level (-1 when nothing is found), which the library keeps."""
    import os
    import secure
    info = of_document(path, lines)
    if info["level"] > READ_MAX and not secure.ACTIVE:
        try:
            import diag
            diag.activity("spill_guard_stopped")
        except Exception:
            pass
        raise Spill(os.path.basename(path), info)
    return info["level"]


def guard_lines(fname, lines, level=-1):
    """The spill guard on words read later (scanned pages, pictures): raises Spill; else the higher level."""
    import secure
    lv, why = markings(lines)
    if lv > READ_MAX and not secure.ACTIVE:
        try:
            import diag
            diag.activity("spill_guard_stopped")
        except Exception:
            pass
        raise Spill(fname, {"level": lv, "why": why, "label": ""})
    return max(level, lv)


def name(level):
    return LEVELS[level] if 0 <= level < len(LEVELS) else "Not known"


def markings(lines):
    """(level, evidence) from a document's visible text lines: -1 when no marking is found.
    Built not to fire on ordinary RFP text: FAR clause paragraphs lettered (C) or (S), a vendor quote headed
    CONFIDENTIAL, a blank form with a "Classified By" box. Classified documents mark every paragraph, (U) included, and
    carry banners with control markings and a full authority block, so the evidence asked for is:
    - a banner line that is only TOP SECRET or SECRET (with or without //controls); CONFIDENTIAL only with //controls;
    - an authority block: at least two of Classified By, Derived From, Declassify On, Classification Authority;
    - portion marks: one with //controls ((S//NF), (C//REL TO USA)), or classified ones ((TS), (S), (C)) alongside at
      least two unclassified ones ((U), (U//FOUO), (CUI)).
    A bare CONFIDENTIAL banner is a business marking (Proprietary); CUI banners and portion marks are CUI."""
    best, why = -1, ""
    banners, auth_keys = [], set()
    classified_portions, controlled_portions, unclass_portions = 0, 0, 0
    bare_conf = False
    cui_seen = ""
    for ln in lines:
        s = " ".join(str(ln or "").split())
        if not s:
            continue
        if len(s) <= 80 and s == s.upper():
            m = _BANNER.match(s)
            if m:
                word, controls = m.group(1), "//" in s
                if word == "CONFIDENTIAL" and not controls:
                    bare_conf = True
                else:
                    banners.append(word)
        for m in _AUTH.finditer(s):
            auth_keys.add(" ".join(m.group(0).lower().replace(":", "").split()))
        for m in _PORTION.finditer(s):
            if "//" in m.group(0):
                controlled_portions += 1
            else:
                classified_portions += 1
        unclass_portions += len(_UPORTION.findall(s))
        if not cui_seen and _CUI.search(s) and not _TRADE.search(s):
            cui_seen = s[:60]
    if banners:
        top = max((TS if "TOP" in b else SECRET if b.startswith("SECRET") else CONF) for b in banners)
        best, why = top, f"a {name(top).upper()} banner"
    if len(auth_keys) >= 2 and best < CONF:
        best, why = CONF, "a classification authority block (Classified By / Derived From / Declassify On)"
    if best < CONF and (controlled_portions or (classified_portions and unclass_portions >= 2)):
        best, why = CONF, f"{controlled_portions + classified_portions} classified portion marks"
    if best < 0 and cui_seen:
        best, why = CUI, f"a CUI marking ({cui_seen})"
    if best < 0 and bare_conf:
        best, why = PROP, "a CONFIDENTIAL marking (a business marking without classification controls)"
    return best, why


def embedded_labels(path):
    """The sensitivity label names stored in an Office file or a PDF ([] when none)."""
    p = (path or "").lower()
    out = []
    try:
        if p.endswith((".docx", ".xlsx", ".pptx", ".docm", ".xlsm", ".pptm")):
            with zipfile.ZipFile(path) as z:
                if "docProps/custom.xml" in z.namelist():
                    x = z.read("docProps/custom.xml").decode("utf-8", "replace")
                    for m in re.finditer(r'name="MSIP_Label_[0-9a-fA-F\-]+_Name"[^>]*>\s*<vt:lpwstr>([^<]{1,120})</vt:lpwstr>', x):
                        out.append(m.group(1))
                    for m in re.finditer(r'name="(?:Classification|Sensitivity|ClassificationLevel|Marking)"[^>]*>\s*<vt:lpwstr>([^<]{1,120})</vt:lpwstr>', x, re.I):
                        out.append(m.group(1))
        elif p.endswith(".pdf"):
            with open(path, "rb") as f:
                data = f.read(4 * 1024 * 1024)
            for m in re.finditer(rb"MSIP_Label_[0-9a-fA-F\-]+_Name\s*[>=:\"']+\s*([^<\"'\r\n]{1,120})", data):
                out.append(m.group(1).decode("utf-8", "replace"))
            for m in re.finditer(rb"<pdfx:(?:Classification|Sensitivity)>([^<]{1,120})<", data):
                out.append(m.group(1).decode("utf-8", "replace"))
    except (OSError, zipfile.BadZipFile, KeyError):
        pass
    return list(dict.fromkeys(x.strip() for x in out if x.strip()))


def of_document(path, lines=None, confidential_is="Proprietary"):
    """{"level", "why", "label"}: the highest of the embedded label and the visible markings; lines: the document's
    text lines (read here from typed text when not given)."""
    best, why, label = -1, "", ""
    for lab in embedded_labels(path):
        lv = level_of_words(lab, confidential_is)
        if lv > best:
            best, why, label = lv, f"its sensitivity label “{lab}”", lab
    if lines is None:
        lines = typed_lines(path)
    lv, w = markings(lines)
    if lv > best:
        best, why = lv, w
    return {"level": best, "why": why, "label": label}


def typed_lines(path):
    """The typed text of a file as lines (no picture reading), for the markings check, with the page headers and
    footers, slide masters and Excel page headers where banners sit (the app's reading leaves those out)."""
    out = office_margins(path)
    try:
        import app_gui
        for _loc, text in app_gui.typed_chunks(path):
            out += str(text).splitlines()
    except Exception:
        pass
    return out


_XCODES = re.compile(r'&(?:"[^"]*"|\d+|[A-Za-z])')


def office_margins(path):
    """The text of a Word file's headers and footers, a PowerPoint file's slide masters and layouts, and an Excel file's
    page headers and footers, one line per paragraph ([] for other files)."""
    import html
    p = (path or "").lower()
    out = []
    try:
        if not p.endswith((".docx", ".docm", ".pptx", ".pptm", ".xlsx", ".xlsm")):
            return out
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if len(out) > 400:
                    break
                if re.match(r"word/(header|footer)\d*\.xml$", n):
                    x = z.read(n).decode("utf-8", "replace")
                    for para in re.findall(r"<w:p[ >].*?</w:p>", x, re.S):
                        t = "".join(re.findall(r"<w:t(?: [^>]*)?>([^<]*)</w:t>", para))
                        if t.strip():
                            out.append(html.unescape(t))
                elif re.match(r"ppt/(slideMasters|slideLayouts)/[^/]+\.xml$", n):
                    x = z.read(n).decode("utf-8", "replace")
                    for para in re.findall(r"<a:p>.*?</a:p>|<a:p .*?</a:p>", x, re.S):
                        t = "".join(re.findall(r"<a:t>([^<]*)</a:t>", para))
                        if t.strip():
                            out.append(html.unescape(t))
                elif re.match(r"xl/worksheets/[^/]+\.xml$", n):
                    x = z.read(n).decode("utf-8", "replace")
                    for m in re.finditer(r"<(?:odd|even|first)(?:Header|Footer)>([^<]*)</", x):
                        for part in re.split(r"&[LCR]", html.unescape(m.group(1))):
                            t = _XCODES.sub("", part).strip()
                            if t:
                                out.append(t)
    except (OSError, zipfile.BadZipFile, KeyError):
        pass
    return out


def effective(doc_level, effort_level):
    """The level that decides: the higher of the document's and the effort's (-1 when both are unknown)."""
    return max(doc_level, effort_level)


def training_ok(level):
    """Training may see it: General business, Proprietary or CUI, never unknown, never above CUI."""
    return 0 <= level <= TRAINING_MAX


def spill_text(fname, info):
    return (f"Stop: {fname} is marked {name(info['level']).upper()} ({info['why']}). Stationkeeper does not read documents "
            "marked above CUI on this PC, and has made no copy of it. Leave the file where it is and follow your site's "
            "spillage procedure (tell your security officer).")


def effort_level(list_path, rec=None, lib=None):
    """An effort's level: the higher of its declared sensitivity (Edit details) and its documents' levels found when
    they were added; -1 when neither is known."""
    import os
    try:
        import workspace as W
        data = W.data_dir_for(list_path)
        if rec is None:
            import effortrec as R
            rec = R.Record(data)
        if lib is None:
            import docversions as DV
            lib = DV.Library(os.path.join(data, "documents")).load()
    except Exception:
        return -1
    try:
        import branding as BR
        declared = level_of_words(BR.identity(rec).get("sensitivity", ""))
    except Exception:
        declared = -1
    docs = max([d.get("sensitivity", -1) for d in (lib.all if lib is not None else []) if isinstance(d.get("sensitivity", -1), int)] + [-1])
    return max(declared, docs)
