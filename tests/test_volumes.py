"""2.56.1 the response's volumes are the person's answer: one volume (a name or blank) or several (the headings that
start a volume); the matrix's Volume column and the Response Setup's documents follow it; nothing is guessed from
section names; a structure with 'Volume ...' headings and no answer yet uses them."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import compliance as C, setupdoc as SD, matrixdesign as MD

M = C.Matrix(os.path.join(tempfile.mkdtemp(), "m.xlsx"), "Kestrel")
M.outline = C.parse_outline("1 Technical Approach\n1.1 Thermal\n2 Management\n2.1 Schedule")
assert SD.volumes_of(M) == ("", "", []) and set(MD.volume_map(M).values()) == {""}, "no guess from section names"
assert len(SD.volume_groups(M)) == 1
SD.set_volumes(M, "one", "Technical and Management Volume")
assert set(MD.volume_map(M).values()) == {"Technical and Management Volume"} and len(SD.volume_groups(M)) == 1
SD.set_volumes(M, "one", "")
assert set(MD.volume_map(M).values()) == {""}
SD.set_volumes(M, "several", heads=["1 Technical Approach", "2 Management"])
vm = MD.volume_map(M)
assert vm["1.1 Thermal"] == "1 Technical Approach" and vm["2.1 Schedule"] == "2 Management", vm
g = SD.volume_groups(M)
assert [n for n, _e in g] == ["1 Technical Approach", "2 Management"] and len(g[0][1]) == 2, g
M2 = C.Matrix(os.path.join(tempfile.mkdtemp(), "m.xlsx"), "K")
M2.outline = C.parse_outline("Volume I Technical\n1.1 Thermal\nVolume II Management\n2.1 Schedule")
assert SD.volumes_of(M2)[0] == "several" and MD.volume_map(M2)["2.1 Schedule"] == "Volume II Management"
M.save()
M3 = C.Matrix(M.path).load()
assert SD.volumes_of(M3) == ("several", "", ["1 Technical Approach", "2 Management"]), "kept with the matrix"
print("volumes ok")
