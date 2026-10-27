"""2.46.0 readable copy: everything an effort holds, readable without Stationkeeper. A test effort with stages and gate
goals, tasks, notes and an open question, deliverables, the timeline, customer document versions, submission
requirements, compliance decisions (requirement, context, not used, not decided) placed in sections with leads and
contributors, acronyms and keywords. The copy is read back from the files alone (CSV and text): every item is there,
by name and not by internal ID; the READ ME explains each file; customer document text is one file per version; the
effort package carries the copy and unzips it; files are replaced whole (no temp files left)."""
import csv, os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ.setdefault("AH_OCR_ENGINE", "tesseract")
import readable as RD, effortrec as ER, deliverables as D, docversions as DV, subreq as SR, compliance as C, setupdoc as SD
import effort as E, effortpkg as P
from test_docversions import amend


def read_csv(folder, name):
    with open(os.path.join(folder, name), encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def run():
    import app_gui as A
    d = tempfile.mkdtemp()
    eff = os.path.join(d, "Kestrel")
    os.makedirs(eff)
    lst = os.path.join(eff, "Kestrel_Effort_List.xlsx")
    data = os.path.join(eff, "Kestrel_Effort_List - app data")
    L = E.EffortList(lst, "Kestrel", client="USSF SSC", solicitation="FA8810-27-R-0042")
    L.add_or_update("TT&C", Type="Acronym", Definition="Telemetry, Tracking and Command")
    L.add_or_update("IMS", Type="Acronym", Definition="Integrated Master Schedule")
    L.set_status(["IMS"], "Approved", approver="R. Diaz")
    L.add_keyword("thermal control system", "Our solution", "Typed in", "our offer")
    L.pending = True; L.save()
    # the record: due date, stages, a goal met, a task, a note and an open question, a deliverable
    rec = ER.Record(data)
    rec.set_due("2026-12-15T14:00", "MT", who="pm")
    st0 = rec.stage()
    g0 = st0["goals"][0]
    tid = rec.add_task("Draft the thermal design section", owner="J. Smith", due="2026-11-06", who="pm")
    rec.add_note("Kickoff held; capture lead confirmed the win themes.", who="pm")
    rec.add_note("Does the 50-page limit include the executive summary?", label="RFP Section L", question=True, who="pm")
    # customer documents: original and an amendment
    src = os.path.join(A.BASE_DIR, "test_samples", "rfp", "Kestrel_RFP_Sections_C_L_M.docx")
    amd = amend(src, os.path.join(d, "Kestrel_RFP_Amd1.docx"), [("December 15, 2026", "December 22, 2026")])
    lib = DV.Library(os.path.join(data, "documents"))
    doc, v1 = lib.add(src, DV.snapshot("a.docx", A.typed_chunks(src)), doc_name="Kestrel RFP", who="pm", when="2026-10-02T09:00")
    lib.add(amd, DV.snapshot("b.docx", A.typed_chunks(amd)), doc_id=doc["id"], who="pm", when="2026-10-14T09:00")
    reg = SR.Register(lib)
    rows = reg.rows(include_hidden=True)
    did = D.add(rec, "Volume I Technical", kind="Volume", owner="B. Chen", limit="40 pages", who="pm")
    D.mark_stage(rec, did, who="pm")
    rec.move_to(rec.data["stages"][1]["id"], who="pm") if hasattr(rec, "move_to") else None
    # the compliance matrix: decisions in sections with people
    M = C.Matrix(os.path.join(eff, "Kestrel_Matrix.xlsx"), "Kestrel")
    M.items = C.extract([("Kestrel_RFP_Sections_C_L_M.docx", A.typed_chunks(src))], [])
    M.outline = C.parse_outline("1.1 Thermal Design\n1.2 Management Approach")
    keep = next(it for it in M.items if "thermal design that maintains" in it["text"])
    C.assign_requirement(M.items, [keep], "1.1 Thermal Design")
    ctx = next(it for it in M.items if "flight-proven" in it["text"])
    C.assign_context(M.items, [ctx], [keep["id"]])
    drop = next(it for it in M.items if "fictional test sample" in it["text"])
    drop["decision"] = "Drop"
    SD.set_people(M, "1.1 Thermal Design", lead="J. Smith", with_="K. Ito")
    M.save()
    # write the readable copy and read it back from the files alone
    parts = RD.build(L, rec, lib, rows, M, {"effort": "Kestrel"}, "2.46.0")
    folder = RD.folder_for(lst, "Kestrel")
    written = RD.write(folder, parts, lib)
    assert os.path.basename(folder) == "Kestrel - readable copy (Stationkeeper)" and os.path.dirname(folder) == eff
    files = sorted(os.listdir(folder))
    for f in ("READ ME FIRST.txt", "Effort summary.txt", "Stages and gate goals.csv", "Tasks.csv", "Notes and open questions.csv",
              "Deliverables.csv", "Timeline (paper trail).csv", "Submission requirements.csv", "Customer documents.csv",
              "Compliance assignments.csv", "Response structure and people.csv", "Acronyms.csv", "Keywords.csv", "Customer document text"):
        assert f in files, (f, files)
    assert not any(f.endswith(".tmp") for f in files)
    texts = sorted(os.listdir(os.path.join(folder, "Customer document text")))
    assert texts == ["Kestrel RFP - Amendment 1.txt", "Kestrel RFP - Original.txt"], texts
    t1 = open(os.path.join(folder, "Customer document text", "Kestrel RFP - Amendment 1.txt"), encoding="utf-8-sig").read()
    assert "December 22, 2026" in t1 and "[L.1 GENERAL INSTRUCTIONS]" in t1 and "SHA-256" in t1, t1[:300]
    readme = open(os.path.join(folder, "READ ME FIRST.txt"), encoding="utf-8-sig").read()
    assert all(f in readme for f in ("Compliance assignments.csv", "Tasks.csv", "IF STATIONKEEPER CANNOT RUN", "Kestrel_Matrix.xlsx",
                                     "record.json"))
    summ = open(os.path.join(folder, "Effort summary.txt"), encoding="utf-8-sig").read()
    assert "EFFORT: Kestrel" in summ and "Client: USSF SSC" in summ and "Proposal due: Dec 15, 2026" in summ
    assert "OPEN QUESTIONS (1)" in summ and "Does the 50-page limit" in summ and "Draft the thermal design section, J. Smith" in summ
    stages = read_csv(folder, "Stages and gate goals.csv")
    assert [r["Stage"] for r in stages if r["Gate goal"] == g0["text"]][:1] == [st0["name"]]
    assert {r["Stage"] for r in stages} >= {"Intake", "Red team", "Gold team", "Final to pubs"}
    tasks = read_csv(folder, "Tasks.csv")
    assert tasks[0]["Task"] == "Draft the thermal design section" and tasks[0]["Owner"] == "J. Smith" and tasks[0]["Stage"] == st0["name"]
    ids = {s["id"] for s in rec.data["stages"]} | {tid}
    every = "".join(open(os.path.join(folder, f), encoding="utf-8-sig").read() for f in files if f.endswith(".csv"))
    assert not any(i in every for i in ids), "names, not internal IDs"
    notes = read_csv(folder, "Notes and open questions.csv")
    assert {(n["Kind"], n["Text"][:20]) for n in notes} == {("Note", "Kickoff held; captur"), ("Open question", "Does the 50-page lim")}
    dl = read_csv(folder, "Deliverables.csv")
    assert dl[0]["Deliverable"] == "Volume I Technical" and dl[0]["Owner"] == "B. Chen" and dl[0]["Done for stages"].startswith(st0["name"] + " (")
    tl = read_csv(folder, "Timeline (paper trail).csv")
    assert any("Task added: Draft the thermal design section" in r["What happened"] for r in tl) and all(r["When"][:4] == "2026" for r in tl)
    req = {(r["Kind"], r["Subject"]): r for r in read_csv(folder, "Submission requirements.csv")}
    due = req[("Due", "Proposal")]
    assert due["Value"].startswith("December 22, 2026") and due["Version"] == "Amendment 1" and due["Changed in a newer version"] == "yes" \
        and due["Change reviewed"] == "not yet", due
    docs = read_csv(folder, "Customer documents.csv")
    assert [(x["Document"], x["Version"]) for x in docs] == [("Kestrel RFP", "Original"), ("Kestrel RFP", "Amendment 1")] and len(docs[0]["Fingerprint (SHA-256)"]) == 64
    comp = {r["ID"]: r for r in read_csv(folder, "Compliance assignments.csv")}
    k = comp[keep["id"]]
    assert k["Role"] == "Compliance requirement" and k["Our section"] == "1.1 Thermal Design" and k["Owner"] == "J. Smith" \
        and k["Section lead"] == "J. Smith" and k["Section contributors"] == "K. Ito" and "thermal design that maintains" in k["RFP text"], k
    assert comp[ctx["id"]]["Role"] == "Context" and comp[ctx["id"]]["Context for (requirement IDs)"] == keep["id"]
    assert comp[drop["id"]]["Role"] == "Not used" and sum(1 for r in comp.values() if r["Role"] == "Not decided yet") == len(M.items) - 3
    ppl = read_csv(folder, "Response structure and people.csv")
    assert ppl[0]["Title"] == "Thermal Design" and ppl[0]["Lead"] == "J. Smith" and ppl[0]["Compliance requirements"] == "1"
    acr = {r["Term"]: r for r in read_csv(folder, "Acronyms.csv")}
    assert acr["TT&C"]["Definition"] == "Telemetry, Tracking and Command" and acr["IMS"]["Status"] == "Approved" and acr["IMS"]["SS Approver"] == "R. Diaz"
    assert read_csv(folder, "Keywords.csv")[0]["Keyword"] == "thermal control system"
    # rewriting keeps the copy current; a version's text file is written once
    rec.add_task("Confirm red team reviewers", owner="N. Michalenko", who="pm")
    w2 = RD.write(folder, RD.build(L, rec, lib, rows, M, {"effort": "Kestrel"}, "2.46.0"), lib)
    assert [t["Task"] for t in read_csv(folder, "Tasks.csv")][-1] == "Confirm red team reviewers"
    assert not any(x.startswith("Customer document text/") for x in w2) and any(x.startswith("Customer document text/") for x in written)
    # the effort package carries the copy, and it unzips as plain files
    pkg = P.save(os.path.join(d, "out", "Kestrel"), "Kestrel", lst, data, matrix_path=M.path, customer=False, volumes=False,
                 readable_dir=folder, who="pm", when="2026-10-27T09:00")
    with zipfile.ZipFile(pkg["path"]) as z:
        names = z.namelist()
        assert "readable/Compliance assignments.csv" in names and "READ ME.txt" in names and "readable/Customer document text/Kestrel RFP - Original.txt" in names
    there = P.unpack(pkg["path"], os.path.join(d, "there"), lambda p: os.path.join(os.path.dirname(p), "data"))
    assert os.path.isfile(os.path.join(there["readable_dir"], "Tasks.csv")) and \
        os.path.basename(there["readable_dir"]) == "Kestrel - readable copy (Stationkeeper)"
    print("readable copy ok")


if __name__ == "__main__":
    run()
