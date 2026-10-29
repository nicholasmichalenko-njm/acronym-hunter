"""Tasks and questions for one person or the whole team (2.92.0), as a workbook that says who it is for and when it
was made, named for them: <effort>_Tasks_and_Questions_<person or Full_Team>_<date>_<time>.xlsx. Two sheets: Tasks
(open first, late ones in red, done ones in green) and Questions (open ones first, with the answer once resolved).
Rules only (No AI); nothing leaves the PC."""
import datetime, getpass, os, re


def file_name(effort, person="", when=None):
    when = when or datetime.datetime.now()
    who = re.sub(r"[^A-Za-z0-9]+", "_", person).strip("_") if person else "Full_Team"
    return f"{re.sub(r'[^A-Za-z0-9]+', '_', effort).strip('_')}_Tasks_and_Questions_{who}_{when:%Y-%m-%d_%H%M}.xlsx"


def rows(rec, person=""):
    """(tasks, questions) for the person ('' for everyone)."""
    import effortrec as R
    names = {s["id"]: s["name"] for s in rec.stages}
    tasks = [t for t in rec.tasks() if not person or (t.get("owner") or "").casefold() == person.casefold()]
    qs = [n for n in rec.data.get("notes", []) if n.get("question")
          and (not person or (n.get("assignee") or "").casefold() == person.casefold())]
    qs.sort(key=lambda n: (bool(n.get("resolved")), n.get("at", "")))
    trows = [[t["title"], t.get("owner", ""), R.parse_date(t["due"]) if t.get("due") else None, names.get(t.get("stage"), ""),
              t.get("status", ""), "late" if rec.task_overdue(t) else "", t.get("notes", "")] for t in tasks]
    qrows = [[n.get("text", ""), n.get("assignee", ""), n.get("label", "") or n.get("on", ""), "Answered" if n.get("resolved") else "Open",
              n.get("answer", ""), (n.get("at", "") or "")[:10], n.get("who", "")] for n in qs]
    return trows, qrows


def export(rec, path, effort="", person="", who=None, sensitivity=""):
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    trows, qrows = rows(rec, person)
    wb = openpyxl.Workbook()
    now = datetime.datetime.now()

    def sheet(ws, title, heads, data, widths, color_col=None):
        ws["A1"] = f"{effort}: {title}"
        ws["A1"].font = Font(bold=True, size=15, color="0F1E33")
        ws["A2"] = (f"For {person}" if person else "For the full team") + f"  ·  {now:%Y-%m-%d %H:%M}  ·  by {who or getpass.getuser()}"
        ws["A2"].font = Font(color="4E5D71")
        if sensitivity:
            ws["A3"] = sensitivity.upper() if sensitivity.upper().startswith("CUI") else sensitivity
            ws["A3"].font = Font(bold=True, color="502B85")
        r0 = 5
        for c, h in enumerate(heads, start=1):
            cell = ws.cell(r0, c, h); cell.font = Font(bold=True, color="FFFFFF"); cell.fill = PatternFill("solid", fgColor="1F5FAD")
        for i, row in enumerate(data, start=r0 + 1):
            for c, v in enumerate(row, start=1):
                cell = ws.cell(i, c, v)
                cell.alignment = Alignment(wrap_text=True, vertical="top")
                if isinstance(v, datetime.date):
                    cell.number_format = "mmm d, yyyy"
            if color_col is not None:
                tone = color_col(row)
                if tone:
                    for c in range(1, len(heads) + 1):
                        ws.cell(i, c).fill = PatternFill("solid", fgColor=tone)
        if not data:
            ws.cell(r0 + 1, 1, "None.").font = Font(italic=True, color="4E5D71")
        for col, wdt in zip("ABCDEFG", widths):
            ws.column_dimensions[col].width = wdt
        ws.freeze_panes = ws.cell(r0 + 1, 1)
        ws.page_setup.orientation = "landscape"; ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_title_rows = f"{r0}:{r0}"
        ws.oddFooter.center.text = "Page &P of &N"
    t = wb.active; t.title = "Tasks"
    sheet(t, "tasks", ["Task", "Owner", "Due", "Stage", "Status", "Late", "Notes"], trows, (50, 18, 13, 18, 13, 7, 40),
          lambda r: "FBE2E2" if r[5] else ("DCF3E4" if r[4] == "Done" else None))
    q = wb.create_sheet("Questions")
    sheet(q, "questions", ["Question", "Who answers", "About", "State", "Answer", "Asked on", "Asked by"], qrows, (50, 18, 22, 11, 40, 12, 14),
          lambda r: "DCF3E4" if r[3] == "Answered" else None)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + ".tmp.xlsx"
    wb.save(tmp)
    os.replace(tmp, path)
    return path, len(trows), len(qrows)
