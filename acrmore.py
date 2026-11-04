"""More of the acronym work on a session (3.51.0, brought back from the classic window): meaning from context, terms
added by hand, adding to this PC's database and its Exclusion List, the customer definitions' sources, equations.

All functions take the AcronymSession. Rules only (No AI); nothing leaves the PC."""
import os

import app_gui as A
import diag


# ------------------------------------------------------------------ meaning from context
def context_targets(s):
    """{term: (definitions, locations, long forms spelled out)} for every term with several meanings to choose from."""
    out = {}
    for term, d in s.results.items():
        st = A.status_text(d.get("status", ""))
        if d.get("excluded") or d.get("known") or d.get("gone") or not st.upper().startswith(("CHOOSE DEFINITION", "CUSTOMER DOCS DIFFER")):
            continue
        defs = d.get("customer_definitions") if st.upper().startswith("CUSTOMER DOCS DIFFER") else d.get("definitions", [])
        defs = [x for x in (defs or []) if x and not x.startswith("MULTIPLE")]
        if len(defs) >= 2:
            lfs = [u.get("lf", "") for u in (d.get("first_use") or {}).values() if u.get("lf")]
            out[term] = (defs, list(d.get("locations", [])), lfs)
    return out


def suggest_context(s, path_of):
    """Reads the words around every place each multi-meaning term is used and suggests the meaning that fits. Keeps
    each suggestion on the term (d["context"]); the person still decides. Returns how many terms got one."""
    import context as X
    targets = context_targets(s)
    texts, n = {}, 0
    for term, (defs, locs, lfs) in targets.items():
        places = {}
        for loc in locs:
            name = A._file_of(loc)
            if name not in texts:
                p = path_of(name)
                try:
                    texts[name] = A.typed_chunks(p) if p and os.path.isfile(p) else []
                except Exception:  # noqa: BLE001
                    diag.swallowed()
                    texts[name] = []
            want = loc.split(" [OCR fix", 1)[0]
            wins = [w for lbl, t in texts[name] if lbl == want for w in X.windows(t, term)]
            if wins:
                places[loc] = wins
        sug = X.suggest(defs, places, lfs)
        d = s.results[term]
        if sug:
            d["context"] = sug
            if sug.get("definition"):
                n += 1
    diag.activity("context_suggested", terms=n)
    s.save()
    return n


def accept_context(s, terms=None):
    """The context suggestion becomes the choice (like Apply Choice) for the terms given, or every term that has one."""
    terms = [t for t in (terms or list(s.results)) if ((s.results.get(t) or {}).get("context") or {}).get("definition")]
    for t in terms:
        d = s.results[t]
        choice = d["context"]["definition"]
        opt = next((o for o in d.get("definitions", []) if o == choice or o.endswith(choice)), choice)
        s.choose(t, opt)
    diag.activity("context_accepted", n=len(terms))
    return len(terms)


# ------------------------------------------------------------------ terms added by hand
def add_manual(s, term, category="Acronym", definition="", document="", to=("results",)):
    """A term the scan did not find. to: any of "results" (listed with the scan's terms), "list" (this effort's acronym
    list), "database" (this PC's database). Returns what was done, in words."""
    term = " ".join(str(term or "").split())
    if not term:
        return ""
    said = []
    if "results" in to:
        item = {"category": category or "Acronym", "count": 0, "locations": [document] if document else [], "definitions": [definition] if definition else [],
                "selected_definition": definition or "", "status": "ADDED MANUALLY", "manual": True, "in_db": False, "excluded": False}
        s.manual_items[term] = item
        s.results[term] = dict(item)
        said.append("listed with the scan's terms")
    if "list" in to and s.effort is not None:
        if term not in s.results:
            s.results[term] = {"category": category or "Acronym", "count": 0, "locations": [], "definitions": [definition] if definition else [],
                               "selected_definition": definition or "", "status": "ADDED MANUALLY", "manual": True}
        s.add([term], definition)
        said.append("added to the acronym list")
    if "database" in to and definition:
        import acrdb
        acrdb.add_terms([(term, category, definition)])
        said.append("added to this PC's database")
    s.save()
    diag.activity("acronym_added_by_hand", n=1)
    return f"{term}: " + ", ".join(said) if said else ""


def remove_manual(s, term):
    if term not in s.manual_items:
        return False
    s.manual_items.pop(term, None)
    d = s.results.get(term)
    if d is not None and d.get("manual"):
        s.results.pop(term, None)
    s.save()
    return True


# ------------------------------------------------------------------ this PC's database
def add_to_database(s, terms):
    """The terms' chosen meanings into this PC's database (apart from the effort list). Returns the counts."""
    import acrdb
    items = []
    for t in terms:
        d = s.results.get(t) or {}
        defn = d.get("selected_definition") or ""
        row = (s.effort.rows.get(t) if s.effort is not None else None) or {}
        defn = row.get("Definition") or defn
        items.append((t, d.get("category") or "Acronym", defn))
    got = acrdb.add_terms(items)
    diag.activity("acronym_db_added", added=got["added"])
    return got


def add_list_to_database(s, terms=None):
    """3.51.0, usually after submission: terms from this effort's acronym list (approved ones by default) into this
    PC's database. Returns the counts."""
    import acrdb
    if s.effort is None:
        return {"added": 0, "updated": 0, "same": 0}
    rows = s.effort.rows
    pick = terms if terms is not None else [t for t, r in rows.items() if r.get("Status") == "Approved"]
    items = [(t, rows[t].get("Type") or rows[t].get("Category") or "Acronym", rows[t].get("Definition", "")) for t in pick if t in rows]
    got = acrdb.add_terms(items)
    diag.activity("acronym_list_to_db", added=got["added"])
    return got


def to_exclusion_list(s, terms, reason=""):
    """Onto this PC's Exclusion List (never shown in any effort); left out here at once."""
    import acrdb
    n = acrdb.exclusion_add([(t, (s.results.get(t) or {}).get("category", "Acronym"), reason) for t in terms])
    for t in terms:
        d = s.results.get(t)
        if d is not None:
            d["excluded"] = True
            d["status"] = "On the Exclusion List"
    s.save()
    diag.activity("acronym_exclusion_added", n=n)
    return n


# ------------------------------------------------------------------ what the card shows
def found_line(d):
    """(meaning, where it came from) for the ready line: the customer's definition first, then the database's, or None."""
    cust = [x for x in d.get("customer_definitions") or [] if x]
    if cust and d.get("selected_definition") != cust[0]:
        return cust[0], ", ".join(sources_of(d, cust[0])[:3]) or "the customer's documents"
    defs = [x for x in d.get("definitions") or [] if x and not x.startswith(("MULTIPLE", "["))]
    if len(defs) == 1 and defs[0] != d.get("selected_definition"):
        return defs[0], "this PC's database"
    return None


def sources_of(d, definition):
    """The customer documents a definition was found in (file names)."""
    return list(dict.fromkeys(A._file_of(h.get("where", "")) for h in d.get("custdef_all") or []
                              if h.get("definition") == definition and h.get("where")))


def equation_symbols(s, term):
    """For a term found in an equation: [(symbol, its meaning or '')] of the equation's other symbols, or []."""
    d = s.results.get(term) or {}
    eq_locs = [l for l in d.get("locations", []) if "[equation" in l]
    if not eq_locs:
        return []
    out = []
    for t, x in s.results.items():
        if t == term or not any(l in x.get("locations", []) for l in eq_locs):
            continue
        if "symbol" in str(x.get("category", "")).lower() or "equation" in str(x.get("category", "")).lower():
            out.append((t, "" if (x.get("selected_definition") or "").startswith("[") else x.get("selected_definition", "")))
    return sorted(out, key=lambda r: (bool(r[1]), r[0]))
