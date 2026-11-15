"""The exported template, checked against its picks (4.43.0; ST44 of 2026-11-15). After a template's .dotx is written
the app reads the file back and ticks each pick: the page (size and margins), the page numbers of each part, every style
of the style sets and the Setup styles, every Quick Part of the part set. A tick that fails says what differs; nothing
is blocked and the file stays. What this reader cannot tell from the file is said to be not checked, never ticked.
Only read; no Word is needed; nothing leaves the PC."""
import os, re, zipfile

OK, BAD, SKIP = "ok", "warn", "skip"
_SEEN = {}                                         # {path: (mtime, size, key, ticks)}
_FMT = {"lowerRoman": "small Roman (i)", "upperRoman": "Roman (I)", "decimal": "1, 2, 3", "upperLetter": "A, B, C",
        "lowerLetter": "a, b, c"}


def _read(z, name):
    try:
        return z.read(name).decode("utf-8", "replace")
    except KeyError:
        return ""


def _twips(inches):
    return int(round(float(inches) * 1440))


def _page(std, doc):
    import prodrules as PRL
    v = std.get("variables") or {}
    sects = re.findall(r"<w:sectPr\b.*?</w:sectPr>", doc, re.S)
    if not sects:
        return BAD, "The file has no page setup"
    body = sects[-1]
    w, h = PRL.PAGE_SIZES.get(v.get("paper") or "Letter", PRL.PAGE_SIZES["Letter"])
    sz = re.search(r'<w:pgSz\b[^>]*w:w="(\d+)"[^>]*w:h="(\d+)"', body)
    mg = re.search(r"<w:pgMar\b[^>]*>", body)
    if not sz or not mg:
        return BAD, "The file's last section has no page size or margins"
    got = {k: int(m.group(1)) for k in ("top", "bottom", "left", "right") for m in [re.search(rf'w:{k}="(-?\d+)"', mg.group(0))] if m}
    want = {k: _twips(v.get("margin_" + k) or 0) for k in ("top", "bottom", "left", "right")}
    if sorted((int(sz.group(1)), int(sz.group(2)))) != sorted((_twips(w), _twips(h))):
        return BAD, f"The page is {int(sz.group(1)) / 1440:g} by {int(sz.group(2)) / 1440:g} in, not {v.get('paper') or 'Letter'}"
    off = [k for k in want if abs(got.get(k, -1) - want[k]) > 2]
    if off:
        return BAD, "Margins differ: " + ", ".join(f"{k} is {got.get(k, 0) / 1440:g} in, picked {want[k] / 1440:g} in" for k in off)
    return OK, f"{v.get('paper') or 'Letter'}, margins {', '.join(f'{want[k] / 1440:g}' for k in ('top', 'bottom', 'left', 'right'))} in"


def _numbers(std, doc):
    want = [(p.get("name") or p.get("key") or "", (p.get("numbers") or {}).get("fmt") or "decimal")
            for p in (std.get("pagination") or {}).get("parts") or [] if p.get("numbers")]
    got = [(re.search(r'w:fmt="([^"]+)"', m) or [None, "decimal"])[1] for m in re.findall(r"<w:pgNumType\b[^>]*>", doc)]
    if not want:
        return SKIP, "No part is numbered"
    i = 0
    for _name, fmt in want:                              # each part's format, in order, among the file's sections
        while i < len(got) and got[i] != fmt:
            i += 1
        if i >= len(got):
            return BAD, f"{_name}: no section numbers its pages {_FMT.get(fmt, fmt)}"
        i += 1
    return OK, "; ".join(f"{n}: {_FMT.get(f, f)}" for n, f in want)


def _names(xml):
    return {m.casefold() for m in re.findall(r'<w:name w:val="([^"]+)"', xml)}


def _styles(lib, rec, styles_xml):
    import templatesets as TS
    chosen, _wins = TS.styles(lib, rec)
    setup = TS.setup_styles(lib, rec)
    want = sorted(set(chosen) | set(setup))
    if not want:
        return SKIP, "No style set picked"
    have = _names(styles_xml)
    import prodlearn
    lost = [n for n in want if n.casefold() not in have and prodlearn.shown_style_name(n).casefold() not in have]
    if lost:
        return BAD, f"{len(lost)} of {len(want)} styles are not in the file: " + ", ".join(lost[:5])
    return OK, f"All {len(want)} styles are in the file"


def _parts(lib, config_dir, rec, glossary):
    import templatesets as TS
    if not rec["part_set"]:
        return SKIP, "No Quick Part set picked"
    want = [e["name"] for e in TS.quick_parts(lib, config_dir, rec)]
    have = _names(glossary)
    lost = [n for n in want if n.casefold() not in have]
    if lost:
        return BAD, f"{len(lost)} of {len(want)} Quick Parts are not in the file: " + ", ".join(lost[:5])
    return OK, f"All {len(want)} Quick Parts are in the file"


def check(config_dir, t, path=None, lib=None, data=None):
    """[{"key", "name", "state" (ok, warn or skip), "says"}] for the template's made file; [] when there is none."""
    import namedtemplates as NT
    import templatelib as TL
    import templatesets as TS
    path = path or ((t or {}).get("made") or {}).get("path") or ""
    try:
        st = os.stat(path)
    except OSError:
        return []
    key = NT.fingerprint(config_dir, t, data, lib)
    hit = _SEEN.get(path)
    if hit and hit[:3] == (st.st_mtime, st.st_size, key):
        return hit[3]
    lib = lib or TL.Library(config_dir)
    std = NT.std_of(config_dir, t, data)
    rec = TS.recipe(std)
    try:
        with zipfile.ZipFile(path) as z:
            doc, styles, gloss = _read(z, "word/document.xml"), _read(z, "word/styles.xml"), _read(z, "word/glossary/document.xml")
    except (OSError, zipfile.BadZipFile):
        out = [{"key": "file", "name": "The file", "state": BAD, "says": "It cannot be opened"}]
        _SEEN[path] = (st.st_mtime, st.st_size, key, out)
        return out
    out = []
    for k, name, fn in (("layout", "Page Setup", lambda: _page(std, doc)), ("numbering", "Page Numbers", lambda: _numbers(std, doc)),
                        ("styles", "Styles", lambda: _styles(lib, rec, styles)), ("quick", "Quick Parts", lambda: _parts(lib, config_dir, rec, gloss))):
        try:
            state, says = fn()
        except Exception:  # noqa: BLE001  a check that cannot run is not a failed pick
            state, says = SKIP, "Could not be checked"
        out.append({"key": k, "name": name, "state": state, "says": says})
    _SEEN[path] = (st.st_mtime, st.st_size, key, out)
    return out


def words(ticks):
    """'4 of 4 picks checked are in the file' or what differs, in a line; '' with no file."""
    if not ticks:
        return ""
    bad = [x for x in ticks if x["state"] == BAD]
    n = sum(1 for x in ticks if x["state"] != SKIP)
    if bad:
        return "Check the file: " + "; ".join(f"{x['name']}: {x['says']}" for x in bad)
    return f"The file holds what was picked ({n} of {n} checks)" if n else "Nothing to check in the file yet"
