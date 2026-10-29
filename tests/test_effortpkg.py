"""2.40.0 effort package: what goes in (list, saved work, matrix, customer files, optional volumes; no locks, backups or
recovery files), fingerprints checked on import, a tampered file and an unsafe file name are refused, the saved work
is pointed at the new place, and a newer package format is refused with a clear message."""
import json, os, sys, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import effortpkg as P, workspace as W


def run():
    d = tempfile.mkdtemp()
    eff = os.path.join(d, "Kestrel"); os.makedirs(os.path.join(eff, "Customer documents")); os.makedirs(os.path.join(eff, "Volumes"))
    lst = os.path.join(eff, "Kestrel_Effort_List.xlsx"); open(lst, "wb").write(b"list")
    data = W.data_dir_for(lst); os.makedirs(os.path.join(data, "documents")); os.makedirs(os.path.join(data, "backups"))
    open(os.path.join(eff, "Customer documents", "RFP.docx"), "wb").write(b"rfp")
    open(os.path.join(eff, "Customer documents", "~$RFP.docx"), "wb").write(b"lock")
    open(os.path.join(eff, "Volumes", "Vol_1.docx"), "wb").write(b"vol")
    mx = os.path.join(eff, "Kestrel_Matrix.xlsx"); open(mx, "wb").write(b"matrix")
    W.write_json(os.path.join(data, "record.json"), {"stage": "x"})
    W.write_json(os.path.join(data, "settings.json"), {"compliance_path": mx})
    W.write_json(os.path.join(data, "lock.json"), {"user": "a"})
    open(os.path.join(data, "backups", "old.xlsx"), "wb").write(b"b")
    W.write_json(os.path.join(data, "documents", "index.json"), {"docs": [{"id": "d", "name": "RFP", "versions": [{"id": "v", "file": "RFP.docx",
                                                                       "path": os.path.join(eff, "Customer documents", "RFP.docx")}]}]})
    other = os.path.join(d, "elsewhere_draft.docx"); open(other, "wb").write(b"draft")
    rec = W.read_json(os.path.join(data, "record.json")); rec["deliverables"] = [{"id": "x", "name": "Vol I", "file": other}]
    W.write_json(os.path.join(data, "record.json"), rec)
    items, size = P.plan(lst, data, mx, os.path.join(eff, "Customer documents"), os.path.join(eff, "Volumes"), True, False)
    arcs = [a for a, _p in items]
    assert "list/Kestrel_Effort_List.xlsx" in arcs and "data/record.json" in arcs and "matrix/Kestrel_Matrix.xlsx" in arcs
    assert "customer/RFP.docx" in arcs and not any("lock.json" in a or "backups" in a or "~$" in a or a.startswith("volumes/") for a in arcs), arcs
    pkg = os.path.join(d, "out", "K")
    os.makedirs(os.path.dirname(pkg))
    man = P.save(pkg, "Kestrel", lst, data, info={"client": "USSF", "bad": object()}, matrix_path=mx,
                 customer_dir=os.path.join(eff, "Customer documents"), volumes_dir=os.path.join(eff, "Volumes"), volumes=True,
                 stage="Red team", app_version="2.40.0", who="pm", when="2026-10-26T18:00", extra_files=[other])
    assert "files/1/elsewhere_draft.docx" in man["files"] and man["origin"]["files/1/elsewhere_draft.docx"] == os.path.abspath(other)
    assert man["path"].endswith(".skpkg") and man["has"] == {"customer": True, "volumes": True, "matrix": True, "library": "all"} and man["info"] == {"client": "USSF"}
    assert P.read_manifest(man["path"])["stage"] == "Red team"
    import shutil                                              # 2.44.0: a package saved by Acronym Hunter (.ahpkg) still opens
    old_pkg = shutil.copy(man["path"], os.path.join(d, "out", "From_Acronym_Hunter.ahpkg"))
    assert P.read_manifest(old_pkg)["stage"] == "Red team" and ".ahpkg" in P.EXTS and P.EXT == ".skpkg"
    got = P.unpack(man["path"], os.path.join(d, "there", "Kestrel"), W.data_dir_for)
    assert open(got["list"], "rb").read() == b"list" and os.path.isfile(os.path.join(got["data"], "record.json"))
    assert open(os.path.join(got["customer_dir"], "RFP.docx"), "rb").read() == b"rfp" and os.path.isfile(os.path.join(got["volumes_dir"], "Vol_1.docx"))
    n = P.repoint(got["data"], got["customer_dir"], got["matrix"], got["moved"])
    idx = W.read_json(os.path.join(got["data"], "documents", "index.json"))
    newf = W.read_json(os.path.join(got["data"], "record.json"))["deliverables"][0]["file"]
    assert newf == os.path.join(d, "there", "Kestrel", "Our files", "1", "elsewhere_draft.docx") and open(newf, "rb").read() == b"draft", newf
    assert n == 2 and idx["docs"][0]["versions"][0]["path"] == os.path.join(got["customer_dir"], "RFP.docx")
    assert W.read_json(os.path.join(got["data"], "settings.json"))["compliance_path"] == got["matrix"]
    # tampered, unsafe, newer, not a package
    bad = os.path.join(d, "bad.ahpkg")
    with zipfile.ZipFile(man["path"]) as zi, zipfile.ZipFile(bad, "w") as zo:
        for it in zi.infolist():
            zo.writestr(it, b"changed" if it.filename == "data/record.json" else zi.read(it.filename))
    for path, word in ((bad, "fingerprint"),):
        try:
            P.unpack(path, os.path.join(d, "t2"), W.data_dir_for); assert False
        except P.PackageError as e:
            assert word in str(e)
    evil = os.path.join(d, "evil.ahpkg")
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("manifest.json", json.dumps({"format": 1, "files": {}}))
        z.writestr("list/K.xlsx", b"x")
        z.writestr("data/../../escape.txt", b"x")
    try:
        P.unpack(evil, os.path.join(d, "t3"), W.data_dir_for); assert False
    except P.PackageError as e:
        assert "unsafe" in str(e)
    assert not os.path.exists(os.path.join(d, "escape.txt"))
    newer = os.path.join(d, "newer.ahpkg")
    with zipfile.ZipFile(newer, "w") as z:
        z.writestr("manifest.json", json.dumps({"format": 99}))
    for p, word in ((newer, "newer"), (lst, "not a Stationkeeper effort package")):
        try:
            P.read_manifest(p); assert False
        except P.PackageError as e:
            assert word in str(e), str(e)
    print("effortpkg ok")


if __name__ == "__main__":
    run()
