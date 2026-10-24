"""Effort List workbook: add, update (old definition kept as 'Other'), status with approvers, history, reload, exports."""
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
    assert L.set_status(["SOW"], "Approved", approver="J. Smith; A. Lee") == 1
    assert L.set_status(["SOW"], "Approved", approver="A. Lee; K. Wu") == 1
    assert L.rows["SOW"]["SS Approver"] == "J. Smith; A. Lee; K. Wu"
    L.set_status(["kWh"], "Needs author")
    L.save()
    M = E.EffortList(p).load()
    assert M.name == "Kestrel" and M.first_use == "submission"
    assert M.rows["SOW"]["Definition"] == "Scope of Work" and M.rows["SOW"]["Status"] == "Approved"
    assert M.rows["SOW"]["Approved on"] == E.today()
    assert len(M.history) == 6, M.history
    counts = M.export_views(os.path.join(d, "export.xlsx"))
    assert counts == {"Needs author": 1, "Conflicts": 1, "Approved": 1, "All": 2}, counts
    # people edit in Excel: odd status spelling, extra column order
    from openpyxl import load_workbook
    wb = load_workbook(p); ws = wb["Effort List"]
    ws.cell(row=3, column=E.COLUMNS.index("Status") + 1, value="approved ")
    wb.save(p)
    N = E.EffortList(p).load()
    assert N.rows["kWh"]["Status"] == "Approved"
    R = E.Registry(os.path.join(d, "efforts.json"))
    R.put("Kestrel", path=p, first_use="submission"); R.current = "Kestrel"
    assert E.Registry(os.path.join(d, "efforts.json")).current == "Kestrel"
    print("effort ok")

if __name__ == "__main__":
    run()
