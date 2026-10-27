"""2.48.0 the compliance matrix in Excel, designed in the app: a design keeps only known columns (renamed, in order) and
roles; rows follow the response structure; the workbook has the title, the headings as designed, one row per compliance
requirement (and context when chosen), a Customer's sheet, About; the team default saves and loads; the matrix and the
Response Setup export together into one dated folder."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import compliance as C, setupdoc as SD, matrixdesign as MD
from test_assign import row


def build():
    a = row(1, "L.5", "The Offeror shall provide the schedule.")
    b = row(2, "L.4", "The Offeror shall describe the thermal design.")
    c = row(3, "L.4", "Thermal margins matter because the orbit has long eclipses.")
    e = row(4, "L.4", "The Government will evaluate the thermal design.")
    items = [a, b, c, e]
    M = C.Matrix(os.path.join(tempfile.mkdtemp(), "Kestrel_Matrix.xlsx"), "Kestrel")
    M.items = items
    M.outline = C.parse_outline("Volume I\n1.1 Thermal\n1.2 Schedule")
    C.assign_requirement(items, [a], "1.2 Schedule")
    C.assign_requirement(items, [b], "1.1 Thermal")
    C.assign_context(items, [c], ["L.4-02"])
    C.assign_customer(items, [e])
    SD.set_people(M, "1.1 Thermal", lead="J. Smith")
    a["response_page"] = "12"; a["status"] = "Compliant"
    return M


def run():
    M = build()
    d = MD.clean({"columns": [{"key": "text", "heading": "  Requirement   text "}, {"key": "bogus"}, {"key": "ref"},
                              {"key": "text"}, {"key": "owner", "heading": "Author"}], "roles": ["Keep", "Nope"]})
    assert [c["key"] for c in d["columns"]] == ["text", "ref", "owner"] and d["columns"][0]["heading"] == "Requirement text"
    assert d["roles"] == ["Keep"] and d["customer_sheet"] is True
    items, data = MD.rows(M, MD.default())
    assert [it["id"] for it in items] == ["L.4-02", "L.5-01"], "in the structure's order: 1.1 Thermal before 1.2 Schedule"
    assert data[0][3] == "J. Smith" and data[1][4] == "12" and data[1][5] == "Compliant", data
    both = dict(MD.default(), roles=["Keep", "Context"])
    assert [it["id"] for it in MD.rows(M, both)[0]] == ["L.4-02", "L.4-03", "L.5-01"]
    out = os.path.join(tempfile.mkdtemp(), "x", "Kestrel_Compliance_Matrix.xlsx")
    res = MD.export(M, out, d, "Kestrel")
    assert res == {"path": out, "rows": 2, "customer": 1}, res
    from openpyxl import load_workbook
    wb = load_workbook(out)
    ws = wb["Compliance Matrix"]
    assert ws["A1"].value == "Kestrel: Compliance Matrix" and [c.value for c in ws[4]] == ["Requirement text", "RFP reference", "Author"]
    assert ws.cell(row=5, column=1).value == "The Offeror shall describe the thermal design." and ws.cell(row=5, column=3).value == "J. Smith"
    assert wb.sheetnames == ["Compliance Matrix", "Customer's", "About"]
    assert "Government will evaluate" in wb["Customer's"].cell(row=3, column=2).value
    cfg = tempfile.mkdtemp()
    assert MD.load_team(cfg) is None
    MD.save_team(cfg, d)
    assert MD.load_team(cfg) == MD.clean(d) and MD.design_for(M, cfg) == MD.clean(d)
    MD.set_matrix(M, both)
    assert MD.design_for(M, cfg)["roles"] == ["Keep", "Context"], "the matrix's own design wins"
    M.save()
    assert MD.of_matrix(C.Matrix(M.path).load())["roles"] == ["Keep", "Context"], "kept with the matrix"
    t = MD.export_together(M, tempfile.mkdtemp(), MD.design_for(M, cfg), "Kestrel")
    names = sorted(os.path.basename(p) for p in t["files"])
    assert os.path.basename(t["folder"]).startswith("Kestrel compliance export ") and any(n.endswith(".xlsx") for n in names) \
        and any(n.endswith(".docx") for n in names), names
    print("matrix design ok")


if __name__ == "__main__":
    run()
