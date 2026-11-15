"""A template is its components (4.39.0; ST27 of 2026-11-14, step 4). One named template seen whole: five rows, one per
component, each saying where it comes from, what it holds and whether it fits the others; and one line saying whether
the template is ready to make. Styles, Quick Parts and starting pages are the template's own pick (templatesets.recipe);
page layout and numbering are the named ones it picks (pagelayouts, 4.42.0), else the standards', the same for
every template. Only read;
nothing is saved and nothing leaves the PC."""
import namedtemplates as NT
import templatesets as TS

PARTS = (("styles", "Styles", "styles"), ("quick", "Quick Parts", "designs"), ("layout", "Page layout", "layouts"),
         ("numbering", "Numbering", "layouts"), ("starts", "Starting pages", "designs"))      # key, name, the page that changes it
SHARED = "From the standards, the same for every template"


def _n(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _in(x):
    return f"{x:g} in"


def rows(config_dir, t, lib=None, data=None):
    """[{"key", "name", "from", "holds", "state" ("ok" or "warn"), "says", "step"}], five, in PARTS' order."""
    import stylelib as SL
    import templatelib as TL
    lib = lib or TL.Library(config_dir)
    std = NT.std_of(config_dir, t, data)
    rec = TS.recipe(std)
    by = TS.checks_by_part(std, lib, config_dir)

    def verdict(rows_, fine):
        bad = [r for r in rows_ if r[0] == "warn"]
        return ("warn", "; ".join(f"{r[1]}: {r[2]}" if r[2] else r[1] for r in bad)) if bad else ("ok", fine)

    out = []
    names = [k["name"] for k in (SL.get_set(lib, s) for s in rec["style_sets"]) if k]
    chosen, _wins = TS.styles(lib, rec)
    st, says = verdict(by["styles"], "Fits")
    out.append({"key": "styles", "from": ("Style set: " if len(names) == 1 else "Style sets: ") + ", ".join(names) if names
                else "No style set picked: the standards' formatting alone",
                "holds": _n(len(chosen), "style") if names else "", "state": st, "says": says})
    k = SL.get_set(lib, rec["part_set"]) if rec["part_set"] else None
    import partstyles as PS
    tied = PS.goes_with(lib, rec["part_set"]) if k else None
    st, says = verdict(by["quick"], "Every style they use is here")
    out.append({"key": "quick", "from": (f"Quick Part set: {k['name']}" + (f" (goes with {tied['name']})" if tied else "")) if k
                else "No Quick Part set picked",
                "holds": _n(len(TS.quick_parts(lib, config_dir, rec)), "Quick Part") if k else "", "state": st if k else "ok",
                "says": says if k else "None in this template"})
    import pagelayouts as PGL                                # 4.42.0: the named page layout and numbering it picks
    for kind, label, _p in PGL.KINDS:
        it = PGL.get(config_dir, kind, rec[kind])
        gone = bool(rec[kind]) and it is None
        out.append({"key": kind, "from": f"{label}: {it['name']}" if it else SHARED,
                    "holds": PGL.words(kind, PGL.extract(std, kind)), "state": "warn" if gone else "ok",
                    "says": "The one it picked is gone: pick another in What goes in" if gone else "Fits"})
    starts = TS.start_files(config_dir, rec)
    st, says = verdict(by["starts"], "All open")
    out.append({"key": "starts", "from": ", ".join(n for _k, _p, _g, n in starts) if rec["starts"] else "No starting pages picked",
                "holds": (_n(len(rec["starts"]), "page") + ", in order") if rec["starts"] else "", "state": st if rec["starts"] else "ok",
                "says": says if rec["starts"] else "The document starts with its first heading"})
    for r, (key, name, step) in zip(out, PARTS):
        r["name"], r["step"] = name, step
    return out


def ready(rows_):
    """(True when nothing is wrong, the sentence)."""
    bad = [r for r in rows_ if r["state"] == "warn"]
    if not bad:
        return True, "Ready to make. The five components fit each other."
    return False, "Look before you make it. " + " ".join(f"{r['name']}: {r['says']}." for r in bad)
