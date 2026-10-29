"""2.77.0 the author list: names typed or imported (.txt, .csv, .xlsx with Name and Efforts columns); an import adds only
new names and leaves every name already on the list exactly as it is (its efforts too); each name shows in all efforts
or in the ones named; ticking and unticking one effort (a name in all efforts stays in the others); rename, remove,
export and read back; the first start seeds the list from the efforts' teams; nothing is shown with no effort."""
import csv, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import authorlist as AL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
L = AL.load(tmp)
check("a new list: empty, not on disk yet", L.people == [] and not L.exists)
check("seed from the efforts' teams: each name shows where it was on a team", AL.seed(L, [("Heron", ["A. Lee", "K. Park"]), ("Osprey", ["a. lee", "R. Diaz"])]) == 3
      and L.for_effort("Heron") == ["A. Lee", "K. Park"] and L.for_effort("Osprey") == ["A. Lee", "R. Diaz"] and L.exists)
check("seed runs once only", AL.seed(L, [("Kite", ["Z. New"])]) == 0 and not L.find("Z. New"))
check("add a typed name (all efforts)", L.add("  Joe   G. ") and L.find("joe g.")["name"] == "Joe G." and "Joe G." in L.for_effort("Kite"))
check("no duplicates, no blanks, no numbers-only", not L.add("JOE G.") and not L.add("   ") and not L.add("1234"))
L.set_efforts(["Joe G."], ["Heron"])
check("Joe G. on Effort A (Heron) only: in Heron's pickers, not in Osprey's", "Joe G." in L.for_effort("Heron") and "Joe G." not in L.for_effort("Osprey"))
check("no effort: no names", L.for_effort("") == [])
# import
txt = os.path.join(tmp, "names.txt"); open(txt, "w", encoding="utf-8").write("# team\nJoe G.\nM. Chen\n\nS. Patel\n")
res = L.merge(AL.read_file(txt), default=["Osprey"])
check("import a .txt: only new names added, with the chosen efforts", res["added"] == ["M. Chen", "S. Patel"] and res["kept"] == ["Joe G."]
      and L.find("M. Chen")["efforts"] == ["Osprey"], res)
check("a name already on the list keeps its efforts after an import", L.find("Joe G.")["efforts"] == ["Heron"])
cs = os.path.join(tmp, "names.csv")
with open(cs, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f); w.writerow(["Author", "Efforts"]); w.writerow(["T. Nguyen", "All efforts"]); w.writerow(["Joe G.", "Osprey; Kite"])
    w.writerow(["L. Ortiz", "Heron; Kite"]); w.writerow(["", "Heron"])
res = L.merge(AL.read_file(cs))
check("import a .csv with an Efforts column: new names get their efforts; Joe G. is not changed",
      res["added"] == ["T. Nguyen", "L. Ortiz"] and L.find("T. Nguyen")["efforts"] == AL.ALL and L.find("L. Ortiz")["efforts"] == ["Heron", "Kite"]
      and L.find("Joe G.")["efforts"] == ["Heron"] and res["skipped"] == 1, res)
import openpyxl
xp = os.path.join(tmp, "names.xlsx"); wb = openpyxl.Workbook(); ws = wb.active
ws.append(["Name", "Shows in"]); ws.append(["P. Kim", "Osprey"]); ws.append(["T. Nguyen", "Heron"]); wb.save(xp)
res = L.merge(AL.read_file(xp))
check("import an .xlsx", res["added"] == ["P. Kim"] and L.find("T. Nguyen")["efforts"] == AL.ALL)
nohead = os.path.join(tmp, "nohead.csv"); open(nohead, "w").write("Q. Ross\nJoe G.\n")
check("a .csv with no header: the first column is the names", [n for n, _e in AL.read_file(nohead)] == ["Q. Ross", "Joe G."])
# ticking one effort
check("tick: show in an effort", L.show_in("M. Chen", "Heron", True) and "M. Chen" in L.for_effort("Heron"))
check("untick a name in all efforts: it stays in the others", L.show_in("T. Nguyen", "Kite", False, ["Heron", "Osprey", "Kite"])
      and L.find("T. Nguyen")["efforts"] == ["Heron", "Osprey"])
check("rename keeps the efforts", L.rename("M. Chen", "Mei Chen") and L.find("Mei Chen")["efforts"] == ["Osprey", "Heron"] and not L.rename("Mei Chen", "Joe G."))
check("remove", L.remove(["Q. Ross", "P. Kim"]) == 1 and not L.find("P. Kim"))
check("effort renamed: names follow", L.effort_renamed("Heron", "Heron II") >= 1 and "Joe G." in L.for_effort("Heron II"))
# export and read back
ex = os.path.join(tmp, "out.xlsx"); n = L.export(ex)
L2 = AL.AuthorList(os.path.join(tmp, "b.json"))
res = L2.merge(AL.read_file(ex))
check("export to .xlsx and import it elsewhere: the same names and efforts", n == len(L.people) and sorted(L2.names()) == sorted(L.names())
      and L2.find("Joe G.")["efforts"] == ["Heron II"] and L2.find("Mei Chen")["efforts"] == ["Osprey", "Heron II"])
ec = os.path.join(tmp, "out.csv"); L.export(ec)
check("export to .csv reads back", sorted(n for n, _e in AL.read_file(ec)) == sorted(L.names()))
L3 = AL.load(tmp)
check("saved: the list reads back with its history", L3.names() == L.names() and any(h["what"] == "imported" for h in L3.history))
check("efforts text", AL.efforts_text(AL.ALL) == "All efforts" and AL.efforts_text(["A", "B"]) == "A; B" and AL.efforts_text([]) == "No effort yet")
n = sum(checks)
print(f"AUTHOR LIST PASS ({n}/{len(checks)})" if n == len(checks) else f"AUTHOR LIST FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
