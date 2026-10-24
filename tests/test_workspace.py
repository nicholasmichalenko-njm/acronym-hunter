"""2.11.0 workspace: settings and choices per effort, session and resume round trip, recovery copies (offered only when
newer than the file), backups (throttled, pruned, restore keeps the current file), the one-window lock."""
import datetime, json, os, sys, tempfile, time
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import workspace as W


def run():
    d = tempfile.mkdtemp()
    a_list, b_list = os.path.join(d, "A", "A_Effort_List.xlsx"), os.path.join(d, "B", "B_Effort_List.xlsx")
    assert W.data_dir_for(a_list).endswith(os.path.join("A", "A_Effort_List - app data"))
    A, B = W.Workspace(W.data_dir_for(a_list), "A"), W.Workspace(W.data_dir_for(b_list), "B")
    # choices and settings never cross
    A.save_choice("SOW", "Statement of Work"); B.save_choice("SOW", "Scope of Work")
    assert A.load_choices() == {"SOW": "Statement of Work"} and B.load_choices() == {"SOW": "Scope of Work"}
    A.set("compliance_path", "a.xlsx")
    assert A.get("compliance_path") == "a.xlsx" and B.get("compliance_path") is None
    # session and resume, including sets and tuples from the results
    A.save_session({"results": {"SOW": {"status": "x", "files": {"v1.docx"}, "_pre_effort": ("a", "b", False)}}})
    s = A.load_session()
    assert s["results"]["SOW"]["files"] == ["v1.docx"] and s["results"]["SOW"]["_pre_effort"] == ["a", "b", False] and s["saved_at"]
    assert B.load_session() is None
    A.save_resume({"selected_term": "SOW"})
    assert A.load_resume()["selected_term"] == "SOW" and A.last_worked() is not None and B.last_worked() is None
    # recovery: offered when newer than the file, cleared otherwise
    wb = os.path.join(d, "A", "matrix.xlsx")
    open(wb, "wb").write(b"old")
    time.sleep(1.1)
    A.write_recovery("matrix", wb, {"items": [1, 2, 3]})
    rec = A.read_recovery("matrix", wb)
    assert rec and rec["state"]["items"] == [1, 2, 3]
    assert B.read_recovery("matrix", wb) is None, "recovery copies belong to one effort"
    time.sleep(1.1)
    open(wb, "wb").write(b"saved later")
    assert A.read_recovery("matrix", wb) is None, "a file saved after the copy wins"
    assert not os.listdir(A.p("recovery"))
    # backups: throttled, then pruned to 10 recent + one per day
    b1 = A.backup(wb, "matrix")
    assert b1 and A.backup(wb, "matrix") is None, "second backup within 10 minutes is skipped"
    for i in range(14):
        A.backup(wb, "matrix", force=True)
        time.sleep(1.01)
    rows = A.backups("matrix")
    assert len(rows) <= 11, len(rows)                       # 10 recent + today's first one at most
    open(wb, "wb").write(b"current")
    A.restore(rows[-1][0], wb)
    assert open(wb, "rb").read() == b"saved later"
    assert any(open(r[0], "rb").read() == b"current" for r in A.backups("matrix")), "restore keeps the file it replaced"
    # lock: this process holds it; a different person or a live other process blocks; stale or dead does not
    assert A.acquire_lock()
    me = W.Workspace._me()
    W.write_json(A.p("lock.json"), dict(me, user="someone", time=datetime.datetime.now().isoformat(timespec="seconds")))
    assert not A.acquire_lock() and A.locked_by["user"] == "someone"
    W.write_json(A.p("lock.json"), dict(me, user="someone", time=(datetime.datetime.now() - datetime.timedelta(hours=13)).isoformat()))
    assert A.acquire_lock(), "a lock older than 12 hours is stale"
    W.write_json(A.p("lock.json"), dict(me, pid=999999, time=datetime.datetime.now().isoformat(timespec="seconds")))
    assert A.acquire_lock(), "same user and PC, process no longer running"
    A.release_lock()
    assert not os.path.exists(A.p("lock.json"))
    print("workspace ok")


if __name__ == "__main__":
    run()
