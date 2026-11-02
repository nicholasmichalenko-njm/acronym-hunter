"""QA/QC of our own Word deliverables (3.14.0: the rules the classic window's volume check kept, now on their own):
for each volume its own definitions, its acronym list and its banned words; the report against the effort list and the
page limits; the log line; adding what is missing to the effort list; recording use; one acronym list per volume.
Word (.docx) only: a PDF loses the difference between running text, tables, captions, figures and headings.
Rules only (No AI); nothing leaves the PC."""
import os, re
import diag
import subreq
import volcheck as V

WORD_ONLY = ("QA/QC checks the Word documents we produce (.docx), never customer documents. Run it on the Word files, "
             "not on PDF exports: a PDF loses the difference between running text, tables, captions, figures and "
             "headings, so first-use results on a PDF would not be accurate.")


def qa_collect(paths, eng, words, vc):
    """2.65.1: for each Word volume, its own definitions, its acronym list and its banned words (both programs)."""
    import banned
    import custdefs
    for p in paths:
        eng.check_cancel()
        try:
            vc["defs"][os.path.basename(p)] = custdefs.extract(eng.typed_chunks(p) + custdefs.table_chunks(p))
        except Exception:
            diag.swallowed()
        try:                                        # the volume's own acronym list (2.25.0)
            vc["lists"][os.path.basename(p)] = custdefs.acronym_list(p)
        except Exception:
            diag.swallowed()
        try:                                        # banned words and phrases (2.27.0)
            vc["banned"][os.path.basename(p)] = banned.find(eng.typed_chunks(p), words, eng.loc_kind)
        except Exception:
            diag.swallowed()
    return vc


def qa_report(results, L, vc, eng, reg_rows=(), volumes=()):
    """2.65.1: the QA/QC report of a finished check (both programs)."""
    report = V.build({t: d for t, d in results.items() if not d.get("known")}, L.rows,   # known names stay off
                     vc["names"], L.first_use, vc["defs"],
                     file_of=eng._file_of, in_picture=lambda loc: bool(eng._OCR_LOC.search(loc)),
                     vol_lists=vc.get("lists"), vol_banned=vc.get("banned"))
    report["paths"] = {os.path.basename(p): p for p in vc["paths"]}
    try:                                                # 2.39.0: against the page limits in the customer documents
        report["pages"] = subreq.page_check(report["paths"], reg_rows, volumes) if reg_rows else []
    except Exception:
        diag.swallowed(); report["pages"] = []
    for r in report["pages"]:
        r["check"] = V.CHECK_MARKS.get(r["level"], "")
    return report


def qa_log_text(report):
    s = report["summary"]
    pg = report.get("pages") or []
    return (f"QA/QC checked {s['volumes']} volume(s): {s.get('first_use_problems', 0)} first-use fixes, "
            f"{sum(s.get('banned', {}).values()) if s.get('banned_checked') else 0} banned words"
            + (f", {sum(1 for p in pg if p['level'] == 'bad')} over a page limit" if pg else ""))


def qa_add_missing(L, report):
    n = 0
    for m in report["missing"]:
        res = L.add_or_update(m["term"], change_note="added by volume check (Proposed)", Type=m["type"],
                              Definition=m["suggestion"] or None, Source="Volume check", **{"Used in volumes": m["volumes"]})
        n += res == "added"
    return n


def qa_record_use(L, report):
    n = 0
    for term, fields in V.effort_updates(report).items():
        if term in L.rows:
            n += L.add_or_update(term, change_note="volume check: volumes and first use", **fields) == "updated"
    return n


def qa_volume_lists(report, folder):
    """One Word acronym list per volume (and one for all volumes). Returns ([file names], open items)."""
    written, open_items = [], 0
    sets = [(v, report["lists"][v]) for v in report["volumes"]]
    if len(sets) > 1:
        combo = {}
        for _v, rows in sets:
            for x in rows:
                combo.setdefault(x.get("key", x["term"]), x)
        sets.append(("All volumes", sorted(combo.values(), key=lambda x: (x["term"].lower(), x["term"]))))
    for v, rows in sets:
        p = os.path.join(folder, re.sub(r"[^A-Za-z0-9 _.-]+", "_", os.path.splitext(v)[0]) + "_Acronym_List.docx")
        V.write_docx([(x["term"], x["definition"]) for x in rows], p)
        written.append(os.path.basename(p))
        if v != "All volumes":
            open_items += sum(1 for x in rows if x["status"] != "Approved" or not x["definition"])
    return written, open_items
