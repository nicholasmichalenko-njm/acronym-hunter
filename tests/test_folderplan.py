"""2.95.0 folders and file names, no window: the team's tree (with fields in folder names), each output's folder and name
pattern, dates and spaces as the team writes them, an empty field leaves no doubled separator, characters Windows
refuses are dropped, {Version} counts up, a new effort's list can sit in a folder of the tree (the effort's root is then
found above it), and a new effort gets the whole tree; the built-in plan gives the names the app always used."""
import datetime, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import folderplan as FP, effortfolders as EF, workspace as W

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
when = datetime.datetime(2026, 11, 3, 14, 30)
P = FP.apply(cfg)
F = {"Effort": "Kestrel Thermal", "Client": "USSF SSC", "Solicitation": "FA8810-26-R-0042"}
check("built in: the names the app always used", FP.name_of("matrix_export", F, when=when) == "Kestrel_Thermal_Compliance_Matrix_2026-11-03.xlsx"
      and FP.name_of("tasks_questions", dict(F, Person="A_Lee"), when=when) == "Kestrel_Thermal_Tasks_and_Questions_A_Lee_2026-11-03_1430.xlsx"
      and FP.name_of("effort_list", F) == "Kestrel_Thermal_Effort_List.xlsx", FP.name_of("matrix_export", F, when=when))
check("built in: the four folders", [t["path"] for t in P["tree"]] == ["Customer Documents", "Volumes", "Response Setup", "Exports"]
      and FP.folder_of("calendar") == "Exports" and FP.folder_of("setup_changes") == "Response Setup" and FP.folder_of("effort_list") == "")
plan = FP.default()
plan.update(tree=[{"path": "01 Customer Documents", "role": "customer"}, {"path": "01 Customer Documents/Amendments", "role": ""},
                  {"path": "02 {Solicitation} Capture", "role": ""}, {"path": "05 Volumes", "role": "volumes"},
                  {"path": "06 Production/Response Setup", "role": "setup"}, {"path": "07 Deliverables", "role": "exports"},
                  {"path": "07 Deliverables/Reports", "role": ""}, {"path": "99 Stationkeeper", "role": ""}],
            places={"effort_status": "07 Deliverables/Reports", "calendar": "02 {Solicitation} Capture"},
            names={"matrix_export": "{Solicitation}_{Company}_Compliance_Matrix_{Date}_{Version}", "effort_status": "{Client} {Effort} Status {Date}"},
            date_format="%Y%m%d", space="-", company="Acme Space", home="99 Stationkeeper")
check("a plan with mistakes is refused", FP.problems(dict(plan, names={"keywords": "{Effort}_{Nope}?"}))
      == ["Keywords for SharePoint: {Nope} is not a field", "Keywords for SharePoint: a file name cannot hold < > : \" / \\ | ? *"])
P = FP.save(cfg, plan)
check("saved and in use", FP.current()["company"] == "Acme Space" and FP.current()["home"] == "99 Stationkeeper")
check("names by the team's pattern, dates and spaces as the team writes them", FP.name_of("effort_status", F, when=when) == "USSF-SSC-Kestrel-Thermal-Status-20261103.docx",
      FP.name_of("effort_status", F, when=when))
check("{Company} from the plan; a space in a value becomes the plan's choice, the pattern's own characters stay", FP.name_of("matrix_export", dict(F, Version="v1"), when=when) == "FA8810-26-R-0042_Acme-Space_Compliance_Matrix_20261103_v1.xlsx",
      FP.name_of("matrix_export", dict(F, Version="v1"), when=when))
check("an empty field leaves no doubled separator", FP.fill("{Effort}_{Client}_Report", {"Effort": "K"}, dict(P, space="_")) == "K_Report")
check("characters Windows refuses are dropped", FP.fill("{Effort}: Report?", {"Effort": "A/B"}, dict(P, space=" ")) == "AB Report")
check("folders by the plan, fields filled in", FP.folder_path(FP.folder_of("calendar"), F) == ["02 FA8810-26-R-0042 Capture"]
      and FP.folder_of("effort_status") == "07 Deliverables/Reports" and FP.folder_of("keywords") == "07 Deliverables"
      and FP.folder_of("effort_list") == "99 Stationkeeper")
# a new effort under that plan
efforts = os.path.join(tmp, "Efforts")
path, up = EF.new_list_path(efforts, "Kestrel Thermal", F)
check("a new effort's list sits in the team's folder for it", path == os.path.join(efforts, "Kestrel_Thermal", "99 Stationkeeper", "Kestrel-Thermal_Effort_List.xlsx")
      and up == 1, path)
os.makedirs(os.path.dirname(path)); open(path, "w").close()
W.Workspace(W.data_dir_for(path), "Kestrel Thermal").set("root_up", up)
check("the effort's root is found above it", EF.root(path) == os.path.join(efforts, "Kestrel_Thermal"))
made = EF.create_all(path, F)
root = EF.root(path)
check("a new effort gets the whole tree, fields filled in", all(os.path.isdir(os.path.join(root, *p.split("/"))) for p in
      ["01 Customer Documents/Amendments", "02 FA8810-26-R-0042 Capture", "06 Production/Response Setup", "07 Deliverables/Reports"]), made)
check("the jobs' folders follow the tree", EF.folder(path, "customer") == os.path.join(root, "01 Customer Documents")
      and EF.folder(path, "setup") == os.path.join(root, "06 Production", "Response Setup"))
p1 = EF.place(path, "matrix_export", {"Version": ""})
check("place: the folder and the name together, {Version} counting up", p1 == os.path.join(root, "07 Deliverables", FP.name_of("matrix_export", dict(F, Version="v1"))), p1)
open(p1, "w").close()
p2 = EF.place(path, "matrix_export")
check("... v2 when v1 is there", p2.endswith("_v2.xlsx"), p2)
check("an output that is a folder: just the folder", EF.place(path, "compliance_package") == os.path.join(root, "07 Deliverables"))
check("place: extra fields for one save", os.path.basename(EF.place(path, "redline", {"Doc": "RFP", "From": "Original", "To": "Amendment 2"}))
      == "RFP_Original_to_Amendment-2_Redline.docx")
check("the calendar with another extension", EF.place(path, "calendar", ext=".ics").endswith("Kestrel-Thermal_Calendar.ics"))
# an older effort: its list in the root, no root_up
old = os.path.join(efforts, "Heron", "Heron_Effort_List.xlsx"); os.makedirs(os.path.dirname(old)); open(old, "w").close()
check("an effort from before keeps its root beside its list", EF.root(old) == os.path.dirname(old))
FP.save(cfg, FP.default())
EF.remember(old, {"Effort": "Heron"})
check("back to the built-in plan", EF.place(old, "keywords") == os.path.join(efforts, "Heron", "Exports", "Heron_Keywords.xlsx"), EF.place(old, "keywords"))
n = sum(checks)
print(f"FOLDER PLAN {'PASS' if all(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
