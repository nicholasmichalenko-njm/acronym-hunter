"""The compliance matrix in Excel, designed in the app (2.48.0). Rules only (No AI); nothing leaves the PC.

The team picks which columns the matrix shows, in what order and under what headings, and which roles it lists
(compliance requirements, context; the customer's sentences on a sheet of their own). The design is kept with the
effort's matrix and can be saved as the team default. Rows follow our response structure: section by section in
outline order, then by RFP reference. One export can also write the matrix and the Response Setup together, from the
same decisions, into one dated folder.
"""
import copy, datetime, json, os

# key: (default heading, width)
COLUMNS = {
    "ref": ("RFP reference", 16),
    "rfp_section": ("RFP section", 28),
    "text": ("Requirement", 70),
    "role": ("Role", 22),
    "section": ("Proposal section", 30),
    "lead": ("Section lead", 18),
    "owner": ("Owner", 18),
    "page": ("Proposal page", 12),
    "status": ("Compliance status", 16),
    "notes": ("Notes", 30),
    "context_for": ("Context for", 18),
    "source": ("Source document", 28),
    "location": ("Location in the document", 20),
    "strength": ("Strength", 12),
    "type": ("Type", 14),
    "id": ("Stationkeeper ID", 14),
}
ROLES = (("Keep", "Compliance requirements"), ("Context", "Context"))
DEFAULT = {"columns": [{"key": k, "heading": COLUMNS[k][0]} for k in ("ref", "text", "section", "owner", "page", "status", "notes")],
           "roles": ["Keep"], "customer_sheet": True, "title": ""}


def default():
    return copy.deepcopy(DEFAULT)


def clean(d):
    """A design read from a file or the matrix: only known columns and roles, every heading a short plain string."""
    out = default()
    if not isinstance(d, dict):
        return out
    cols = []
    for c in d.get("columns") or []:
        if isinstance(c, dict) and c.get("key") in COLUMNS and c["key"] not in [x["key"] for x in cols]:
            h = " ".join(str(c.get("heading") or COLUMNS[c["key"]][0]).split())[:60] or COLUMNS[c["key"]][0]
            cols.append({"key": c["key"], "heading": h})
    if cols:
        out["columns"] = cols
    roles = [r for r in (d.get("roles") or []) if r in dict(ROLES)]
    out["roles"] = roles or out["roles"]
    out["customer_sheet"] = bool(d.get("customer_sheet", True))
    out["title"] = " ".join(str(d.get("title") or "").split())[:120]
    return out


def of_matrix(M):
    import setupdoc as SD
    return clean(SD.setup_of(M).get("matrix_design")) if SD.setup_of(M).get("matrix_design") else None


def set_matrix(M, design):
    import setupdoc as SD
    SD.setup_of(M)["matrix_design"] = clean(design)
    M.pending = True


def team_file(config_dir):
    return os.path.join(config_dir, "matrix design.json")


def load_team(config_dir):
    try:
        with open(team_file(config_dir), encoding="utf-8") as f:
            return clean(json.load(f))
    except (OSError, ValueError):
        return None


def save_team(config_dir, design):
    os.makedirs(config_dir, exist_ok=True)
    p = team_file(config_dir)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(clean(design), f, indent=1)
    os.replace(tmp, p)
    return p


def design_for(M, config_dir=""):
    """The matrix's own design, else the team default, else the built-in one."""
    return of_matrix(M) or (load_team(config_dir) if config_dir else None) or default()


def _value(M, it, key, inh, people):
    import setupdoc as SD, compliance as C
    if key == "ref":
        return SD.ref_of(M, it, inh)[0] or it.get("section", "") or it["id"]
    if key == "rfp_section":
        return " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
    if key == "text":
        return ((it.get("lead") + " ") if it.get("lead") else "") + it.get("text", "")
    if key == "role":
        return C.context_label(it) if it.get("decision") == "Context" else C.LABEL.get(it.get("decision", ""), "Not used")
    if key == "section":
        return it.get("map", "")
    if key == "lead":
        m = it.get("map", "")
        if m not in people:
            people[m] = SD.section_people(M, m).get("lead", "") if m else ""
        return people[m]
    if key == "owner":
        return SD.owner_of(M, it)
    if key == "page":
        return it.get("response_page", "")
    if key == "status":
        return it.get("status", "")
    if key == "notes":
        return it.get("notes", "")
    if key == "context_for":
        return it.get("context_for", "")
    if key == "source":
        return it.get("file", "")
    if key == "location":
        p = it.get("page")
        return f"p.{p}" if p else (it.get("loc", "").split("(", 1)[-1].rstrip(")") if "(" in it.get("loc", "") else "")
    if key == "strength":
        return it.get("strength", "")
    if key == "type":
        return it.get("type", "")
    if key == "id":
        return it.get("id", "")
    return ""


def rows(M, design):
    """The matrix rows in our structure's order: (items, [[value, ...]])."""
    import setupdoc as SD, compliance as C
    order = {C.outline_label(o): k for k, o in enumerate(M.outline)}
    pick = [it for it in M.items if it.get("decision") in design["roles"]]
    inh = SD.inherited_sections(M)
    pick.sort(key=lambda it: (order.get(it.get("map", ""), len(order)), C.sec_key(it.get("section", "") or ""), M.items.index(it)))
    people = {}
    return pick, [[_value(M, it, c["key"], inh, people) for c in design["columns"]] for it in pick]


def customer_rows(M):
    import setupdoc as SD
    inh = SD.inherited_sections(M)
    return [[SD.ref_of(M, it, inh)[0] or it.get("section", "") or it["id"], _value(M, it, "text", inh, {}), it.get("file", ""),
             _value(M, it, "location", inh, {})] for it in M.items if it.get("decision") == "Customer"]


def preview(M, design, n=8):
    _items, r = rows(M, design)
    return [c["heading"] for c in design["columns"]], r[:n], len(r)


def export(M, path, design, effort_name="", when=None):
    """Write the designed compliance matrix workbook. Returns {"path", "rows", "customer"}."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    import compliance as C
    when = when or datetime.datetime.now()
    design = clean(design)
    wb = Workbook()
    ws = wb.active
    ws.title = "Compliance Matrix"
    title = design["title"] or f"{effort_name or M.name}: Compliance Matrix"
    ws.append([title])
    ws["A1"].font = Font(bold=True, size=14, color="1E3A8A")
    ws.append([f"Built {when:%B %d, %Y %H:%M} from the decisions in Stationkeeper. "
               + ", ".join(lab for r, lab in ROLES if r in design["roles"]) + "."])
    ws["A2"].font = Font(italic=True, color="475569")
    ws.append([])
    heads = [c["heading"] for c in design["columns"]]
    ws.append(heads)
    thin = Side(style="thin", color="CBD5E1")
    for k, cell in enumerate(ws[4], 1):
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1E3A8A")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
        ws.column_dimensions[cell.column_letter].width = COLUMNS[design["columns"][k - 1]["key"]][1]
    items, data = rows(M, design)
    fill = {"Context": PatternFill("solid", fgColor="EFF6FF")}
    for it, r in zip(items, data):
        ws.append(r)
        for cell in ws[ws.max_row]:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(top=thin, bottom=thin, left=thin, right=thin)
            if it.get("decision") in fill:
                cell.fill = fill[it["decision"]]
    ws.freeze_panes = "A5"
    if data:
        ws.auto_filter.ref = f"A4:{ws.cell(row=4, column=len(heads)).column_letter}{ws.max_row}"
    ws.print_title_rows = "4:4"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToHeight = 0
    cust = customer_rows(M) if design["customer_sheet"] else []
    if design["customer_sheet"]:
        cs = wb.create_sheet("Customer's")
        cs.append(["Sentences that read like requirements but are the customer's to act on. Identified, not answered."])
        cs["A1"].font = Font(italic=True, color="475569")
        cs.append(["RFP reference", "Sentence", "Source document", "Location in the document"])
        for cell in cs[2]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="7E22CE")
        for r in cust:
            cs.append(r)
            for cell in cs[cs.max_row]:
                cell.alignment = Alignment(vertical="top", wrap_text=True)
        for col, w in zip("ABCD", (16, 80, 28, 20)):
            cs.column_dimensions[col].width = w
    ab = wb.create_sheet("About")
    c = M.counts()
    for r in (["Effort", effort_name or M.name], ["Built", f"{when:%Y-%m-%d %H:%M}"],
              ["Compliance requirements", c["Keep"]], ["Context", c["Context"]], ["Customer's", c.get("Customer", 0)],
              ["Not used", c[""] + c["Drop"]], ["Rows in this matrix", len(data)],
              ["Note", "Built by Stationkeeper from the compliance decisions; the working matrix stays in Stationkeeper. "
                       "This workbook holds customer content: keep it on this PC or SharePoint."]):
        ab.append(r)
    ab.column_dimensions["A"].width = 26
    ab.column_dimensions["B"].width = 90
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp"
    wb.save(tmp)
    os.replace(tmp, path)
    return {"path": path, "rows": len(data), "customer": len(cust)}


def export_together(M, folder, design, effort_name="", when=None):
    """The designed matrix and the Response Setup, from the same decisions, in one dated folder. Returns the folder and
    the files written."""
    import setupdoc as SD
    when = when or datetime.datetime.now()
    name = f"{(effort_name or M.name)} compliance export {when:%Y-%m-%d %H%M}"
    name = "".join(ch if ch not in '<>:"/\\|?*' else " " for ch in name).strip()
    sub = os.path.join(folder, name)
    k = 2
    while os.path.exists(sub):
        sub = os.path.join(folder, f"{name} ({k})"); k += 1
    os.makedirs(sub)
    mx = export(M, os.path.join(sub, f"{(effort_name or M.name).replace(' ', '_')}_Compliance_Matrix_{when:%Y-%m-%d}.xlsx"),
                design, effort_name, when)
    files = [mx["path"]]
    if M.outline:
        files += SD.export(M, sub, when)
    return {"folder": sub, "files": files, "rows": mx["rows"]}
