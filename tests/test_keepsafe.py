"""2.46.0 exports kept and backups (keepsafe.py). Exports: a file seen at a save window is copied, dated, into the
effort's exports folder once it is written and has stopped changing; nothing there is overwritten; the windows that
create the effort's own files, the effort's working files and the exports folder itself are left out; a folder export
keeps what the export wrote (not the app's own folders). Backups: the latest effort package, a dated one per day (old
ones pruned after 30 days), mirrors of the readable copy and the exports, the settings and team lists zip; the latest
package restores the effort."""
import datetime, os, sys, tempfile, time, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import keepsafe as K, effort as E, effortrec as ER, effortpkg as P


def run():
    d = tempfile.mkdtemp()
    eff = os.path.join(d, "Kestrel")
    os.makedirs(eff)
    lst = os.path.join(eff, "Kestrel_Effort_List.xlsx")
    ex = K.exports_folder(lst, "Kestrel")
    assert os.path.basename(ex) == "Kestrel - exports (Stationkeeper)" and os.path.dirname(ex) == eff
    when = datetime.datetime(2026, 10, 27, 8, 40)
    assert K.dated_name(os.path.join(d, "Kestrel_Response_Setup.docx"), when) == "Kestrel_Response_Setup 2026-10-27 0840.docx"

    # a file export: kept once written and quiet; a second export of the same name never overwrites the first
    W = K.Watch()
    out = os.path.join(d, "out", "Kestrel_Status.docx")
    os.makedirs(os.path.dirname(out))
    assert W.saw_file(out, "Save the effort status", ex)
    assert not W.saw_file(lst, "Where should the effort list live?", ex), "the effort's own files are not exports"
    assert not W.saw_file(os.path.join(eff, "M.xlsx"), "Save the list", ex, skip=[os.path.join(eff, "M.xlsx")])
    assert not W.saw_file(os.path.join(ex, "x.docx"), "Save the list", ex), "not the exports folder itself"
    assert not W.saw_file(out, "Save the list", ""), "no effort open: not kept"
    t0 = time.time()
    assert W.process(now=t0) == [] and len(W.pending) == 1, "not written yet"
    open(out, "w").write("v1")
    assert W.process(now=time.time()) == [], "just written: wait until it stops changing"
    made = W.process(now=time.time() + 10)
    assert len(made) == 1 and os.path.dirname(made[0]) == ex and open(made[0]).read() == "v1" and not W.pending
    assert os.path.basename(made[0]).startswith("Kestrel_Status ") and made[0].endswith(".docx")
    W.saw_file(out, "Save the effort status", ex)
    time.sleep(0.01); open(out, "w").write("v2")
    W.process(now=time.time() + 10); m2 = W.process(now=time.time() + 20)
    kept = sorted(os.listdir(ex))
    assert len(kept) == 2 and {open(os.path.join(ex, k)).read() for k in kept} == {"v1", "v2"}, kept
    # a folder export: what the export wrote, not the app's own folders or the effort's working files
    fold = os.path.join(d, "share")
    os.makedirs(os.path.join(fold, "old")); open(os.path.join(fold, "old", "before.txt"), "w").write("x")
    old = time.time() - 600
    os.utime(os.path.join(fold, "old", "before.txt"), (old, old))
    assert not W.saw_dir(fold, "Choose a folder", ex), "a folder window that is not an export"
    assert W.saw_dir(fold, "Folder for the export", ex, skip=[os.path.join(fold, "list.xlsx")])
    sub = os.path.join(fold, "Kestrel export 2026-10-27")
    os.makedirs(sub); open(os.path.join(sub, "Matrix.xlsx"), "w").write("m"); open(os.path.join(sub, "Setup.docx"), "w").write("s")
    open(os.path.join(fold, "list.xlsx"), "w").write("working file")
    os.makedirs(os.path.join(fold, "Kestrel - readable copy (Stationkeeper)")); open(os.path.join(fold, "Kestrel - readable copy (Stationkeeper)", "Tasks.csv"), "w").write("t")
    W.process(now=time.time() + 10)
    made = W.process(now=time.time() + 20)
    rel = sorted(os.path.relpath(m, ex) for m in made)
    assert len(rel) == 2 and all(r.startswith("share export ") for r in rel) and \
        sorted(os.path.basename(r) for r in rel) == ["Matrix.xlsx", "Setup.docx"], rel

    # backups
    L = E.EffortList(lst, "Kestrel", client="USSF SSC")
    L.add_or_update("TT&C", Type="Acronym", Definition="Telemetry, Tracking and Command")
    L.pending = True; L.save()
    data = os.path.join(eff, "Kestrel_Effort_List - app data")
    rec = ER.Record(data)
    rec.add_task("Draft the thermal design section", owner="J. Smith", who="pm")
    rd = os.path.join(eff, "Kestrel - readable copy (Stationkeeper)")
    os.makedirs(rd); open(os.path.join(rd, "Tasks.csv"), "w", encoding="utf-8").write("Task\nDraft the thermal design section\n")
    cfg = os.path.join(d, "config"); os.makedirs(os.path.join(cfg, "logs"))
    open(os.path.join(cfg, "banned_words.json"), "w").write("{}"); open(os.path.join(cfg, "logs", "a.log"), "w").write("x")
    sett = os.path.join(d, "settings.json"); open(sett, "w").write("{}")
    bdir = os.path.join(d, "Documents", "Stationkeeper backups")
    old_pkg = os.path.join(bdir, "Kestrel", "Kestrel 2026-09-01.skpkg")
    os.makedirs(os.path.dirname(old_pkg)); open(old_pkg, "w").write("old")
    keep_pkg = os.path.join(bdir, "Kestrel", "Kestrel 2026-10-01.skpkg"); open(keep_pkg, "w").write("recent")
    out = K.backup_effort(bdir, "Kestrel", lst, data, readable_dir=rd, exports_dir=ex, info={"client": "USSF SSC"},
                          stage="Intake", app_version="2.46.0", config_dir=cfg, settings_file=sett, when=when)
    root = os.path.join(bdir, "Kestrel")
    assert out["latest"] == os.path.join(root, "Kestrel - latest.skpkg") and os.path.isfile(out["latest"])
    assert out["dated"] == os.path.join(root, "Kestrel 2026-10-27.skpkg") and os.path.isfile(out["dated"])
    assert not os.path.exists(old_pkg) and os.path.isfile(keep_pkg), "dated packages are kept 30 days"
    assert os.path.isfile(os.path.join(root, "Readable copy", "Tasks.csv")) and len(os.listdir(os.path.join(root, "Exports"))) == 3
    assert open(os.path.join(bdir, "READ ME.txt")).read().startswith("Stationkeeper backups")
    with zipfile.ZipFile(out["settings"]) as z:
        names = z.namelist()
    assert os.path.basename(out["settings"]) == "Stationkeeper settings and team lists 2026-10-27.zip"
    assert "banned_words.json" in names and "app settings/settings.json" in names and not any(n.startswith("logs") for n in names), names
    assert not any(f.endswith(".tmp") for f in os.listdir(bdir) + os.listdir(root))
    with zipfile.ZipFile(out["latest"]) as z:
        names = z.namelist()
    assert "readable/Tasks.csv" in names and any(n.startswith("list/") for n in names) and any(n.endswith("record.json") for n in names)
    # the backup restores the effort: unpack it somewhere else and read the task back
    there = P.unpack(out["latest"], os.path.join(d, "restored"), lambda p: os.path.join(os.path.dirname(p), "data"))
    r2 = ER.Record(there["data"])
    assert any(t["title"] == "Draft the thermal design section" for t in r2.data["tasks"]), there
    # a second backup the same day replaces today's copy and adds nothing old
    K.backup_effort(bdir, "Kestrel", lst, data, readable_dir=rd, exports_dir=ex, when=when + datetime.timedelta(hours=2))
    assert sorted(f for f in os.listdir(root) if f.endswith(".skpkg")) == ["Kestrel - latest.skpkg", "Kestrel 2026-10-01.skpkg", "Kestrel 2026-10-27.skpkg"]
    assert K.synced(r"C:\Users\jsmith\OneDrive - Sierra Space\Documents\Stationkeeper backups") and not K.synced(r"C:\Users\jsmith\Documents\x")
    assert K.default_backup_dir().endswith("Stationkeeper backups")
    # restoring: what the backup folder holds, and the settings put back only inside the config folder
    found = K.find_backups(bdir)
    assert [b["name"] for b in found] == ["Kestrel"] and found[0]["package"] == out["latest"]
    assert K.latest_settings(bdir) == out["settings"] and K.find_backups(os.path.join(d, "nowhere")) == []
    bad = os.path.join(d, "bad.zip")
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("../outside.txt", "x"); z.writestr("banned_words.json", "{}"); z.writestr("app settings/settings.json", "{}")
    cfg2, st2 = os.path.join(d, "cfg2"), os.path.join(d, "s2", "settings.json")
    assert K.restore_settings(bad, cfg2, st2) == 3 and not os.path.exists(os.path.join(d, "outside.txt")) and os.path.isfile(st2)
    import coming_soon as CS
    assert "TEAMS AND OWNERS" in CS.text() and "CUSTOM DICTIONARIES" not in CS.text()     # 3.0.4: built
    print("keepsafe ok")


if __name__ == "__main__":
    run()
