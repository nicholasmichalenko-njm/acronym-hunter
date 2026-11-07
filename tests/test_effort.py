"""Effort List workbook: add, update (old definition kept as 'Other'), status (3.76.0: In the list or Not a term), history, reload, exports."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import effort as E

def run():
    d = tempfile.mkdtemp(); p = os.path.join(d, "Kestrel_Effort_List.xlsx")
    L = E.EffortList(p, "Kestrel", "submission").load()
    assert L.rows == {}
    assert L.add_or_update("SOW", Type="Acronym", Definition="Statement of Work", Source="Database") == "added"
    assert L.add_or_update("kWh", Type="Unit", Definition="kilowatt-hour", Source="Database") == "added"
    assert L.add_or_update("SOW", Definition="Scope of Work", Source="Customer document") == "updated"
    assert L.rows["SOW"]["Other definitions"] == "Statement of Work"
    assert L.set_status(["SOW"], "Approved", approver="J. Smith; A. Lee") == 1      # 3.76.0: old names still read
    assert L.rows["SOW"]["Status"] == "In the list" and "Approver" not in L.rows["SOW"]
    assert L.set_status(["kWh"], "Not a term") == 1
    L.add_or_update("TBD", Type="Acronym")
    L.save()
    M = E.EffortList(p).load()
    assert M.name == "Kestrel" and M.first_use == "submission"
    assert M.rows["SOW"]["Definition"] == "Scope of Work" and M.rows["SOW"]["Status"] == "In the list"
    assert any("J. Smith" in " ".join(h) for h in M.history), M.history
    assert E.ready(M.rows["SOW"]) and not E.ready(M.rows["TBD"]) and not E.ready(M.rows["kWh"])
    counts = M.export_views(os.path.join(d, "export.xlsx"))
    assert counts == {"No definition yet": 1, "Conflicts": 1, "Ready": 1, "All": 3}, counts
    # people edit in Excel: odd status spelling, old names
    from openpyxl import load_workbook
    wb = load_workbook(p); ws = wb["Effort List"]
    ws.cell(row=3, column=E.COLUMNS.index("Status") + 1, value="approved ")
    wb.save(p)
    N = E.EffortList(p).load()
    assert N.rows["kWh"]["Status"] == "In the list", N.rows["kWh"]
    R = E.Registry(os.path.join(d, "efforts.json"))
    R.put("Kestrel", path=p, first_use="submission"); R.current = "Kestrel"
    assert E.Registry(os.path.join(d, "efforts.json")).current == "Kestrel"
    print("effort ok")

if __name__ == "__main__":
    run()
