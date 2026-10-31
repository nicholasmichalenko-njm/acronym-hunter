"""Production standards (3.5.0): the team's formatting rules for its document types (proposal volume, cost volume,
customer deliverable...), and each effort's own values from the RFP's formatting instructions. Format Check reads
drafts against them. Kept in the config folder (the backups and team packs carry it); an effort's values live in its
app data. Rules only."""
import copy, json, os, re

FILE = "production_standards.json"
SCOPES = ("body", "table", "caption", "heading", "header", "footnote")
SCOPE_NAMES = {"body": "Body text", "table": "Text in tables", "caption": "Captions", "heading": "Headings",
               "header": "Headers and footers", "footnote": "Footnotes"}
DEFAULT = {
    "name": "Proposal volume",
    "fonts": {"body": {"font": "Times New Roman", "min": 12, "max": 12},
              "table": {"font": "Arial", "min": 10, "max": 10},
              "caption": {"font": "Arial", "min": 10, "max": 10},
              "heading": {"font": "", "min": 0, "max": 0},
              "header": {"font": "", "min": 0, "max": 0},
              "footnote": {"font": "", "min": 8, "max": 10}},
    "margins_in": 1.0,
    "page": "Letter",
    "landscape_ok": True,
    "caption_numbers": "chapter",          # chapter: 2-1, A-1 ; plain: 1, 2, 3
    "caption_sep": "tab",                  # tab | space   (after "Table 2-1.")
    "caption_fields": True,                # numbers must come from SEQ fields, not typed
    "caption_position": "first row",       # first row | above | below | either  (tables)
    "toc_forbid": ["\\o", "\\u"],          # switches the team's TOC never uses
    "page_numbers": True,                  # every section's footer carries a PAGE field
}
PAGES = {"Letter": (12240, 15840), "A4": (11906, 16838), "Legal": (12240, 20160)}


def load(config_dir):
    """{"types": [standard], "default": name}; the built-in proposal volume when nothing is saved."""
    try:
        with open(os.path.join(config_dir, FILE), encoding="utf-8") as f:
            d = json.load(f) or {}
    except (OSError, ValueError):
        d = {}
    types = [merge(DEFAULT, t) for t in d.get("types", []) if isinstance(t, dict) and t.get("name")] or [copy.deepcopy(DEFAULT)]
    names = [t["name"] for t in types]
    return {"types": types, "default": d.get("default") if d.get("default") in names else names[0]}


def save(config_dir, data):
    os.makedirs(config_dir, exist_ok=True)
    p = os.path.join(config_dir, FILE)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"types": data["types"], "default": data.get("default", "")}, f, indent=1)
    os.replace(p + ".tmp", p)


def merge(base, over):
    """base with over's values laid on top (nested dicts merged; blanks in over do not wipe base)."""
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        elif v not in (None, ""):
            out[k] = copy.deepcopy(v)
    return out


def get(data, name):
    return next((t for t in data["types"] if t["name"] == name), data["types"][0])


def for_effort(config_dir, ws=None):
    """The standard that applies to the open effort: its chosen type with the effort's own values on top."""
    data = load(config_dir)
    eff = (ws.get("prod_std", {}) if ws is not None else {}) or {}
    return merge(get(data, eff.get("type") or data["default"]), eff.get("over") or {})


def from_rfp(rows):
    """The effort's own values from the RFP's formatting rules (Submission Rules rows): fonts and sizes for body text
    and for tables and figures, margins and page size. Returns ({over}, [what was read, in words])."""
    over, said = {}, []
    for r in rows:
        subj, val = r.get("subject", ""), r.get("value", "") or ""
        if r.get("kind") != "Format" or not val:
            continue
        if subj in ("Font", "Font in tables and figures"):
            scope = "body" if subj == "Font" else "table"
            m = re.search(r"(\d+(?:\.\d+)?)\s*-?\s*(?:point|pt)", val, re.I)
            face = re.sub(r"(\d+(?:\.\d+)?)\s*-?\s*(?:point|pt)\b", "", val, flags=re.I).strip(" ,;-")
            f = over.setdefault("fonts", {}).setdefault(scope, {})
            if m:
                size = float(m.group(1))
                floor = bool(re.search(r"no smaller|minimum|at least|or larger|or greater", val, re.I))
                f["min"] = size
                f["max"] = 0 if (floor or scope != "body") else size        # 0: no largest size
            if face and re.search(r"[A-Za-z]{3,}", face):
                f["font"] = face
            if scope == "table":
                over["fonts"].setdefault("caption", dict(f))
            said.append(f"{subj}: {val}")
        elif subj == "Margins":
            m = re.search(r"(\d+(?:\.\d+)?)", val)
            if m:
                over["margins_in"] = float(m.group(1))
                said.append(f"Margins: {val}")
        elif subj == "Page size":
            over["page"] = "A4" if "a4" in val.lower() else "Letter"
            said.append(f"Page size: {val}")
    return over, said
