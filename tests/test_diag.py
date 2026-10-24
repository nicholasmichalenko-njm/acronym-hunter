"""Logs must never hold data: feed errors that carry a term, a path and a user name, then check the files."""
import json, os, sys, tempfile, threading
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import diag

SECRETS = ["SE&I-SECRET", r"C:\Users\jdoe\Customer\RFP_Kestrel.pdf", "jdoe", "RFP_Kestrel", "Kestrel"]

def run():
    d = tempfile.mkdtemp()
    diag.setup(d, "test")
    try:
        {}["SE&I-SECRET"]
    except KeyError:
        diag.swallowed()
    try:
        open(r"C:\Users\jdoe\Customer\RFP_Kestrel.pdf")
    except OSError:
        diag.error("scan", "File could not be read", exc=sys.exc_info(), ext=".PDF", pages=3, name="RFP_Kestrel")
    t = threading.Thread(target=lambda: (_ for _ in ()).throw(ValueError("Kestrel jdoe")))
    t.start(); t.join()
    diag.scan_started(2, {".pdf": 1, ".docx": 1, "Kestrel": 5})
    diag.activity("apply_choice", term="SE&I-SECRET", n=1)
    diag.activity("Kestrel jdoe")
    for _ in range(50):
        try:
            int("Kestrel")
        except ValueError:
            diag.swallowed("loop_area")
    diag.scan_finished(terms=4)
    diag.shutdown()
    blob = ""
    for f in os.listdir(d):
        blob += open(os.path.join(d, f), encoding="utf-8").read()
    for s in SECRETS:
        assert s not in blob, f"LEAK: {s!r} found in logs"
    ev = [json.loads(l) for l in open(os.path.join(d, "events.jsonl"), encoding="utf-8")]
    act = [json.loads(l) for l in open(os.path.join(d, "activity.jsonl"), encoding="utf-8")]
    types = {e.get("type") for e in ev}
    assert {"KeyError", "FileNotFoundError", "ValueError"} <= types, types
    assert any(e.get("repeats") == 50 for e in ev), "repeat counting missing"
    assert sum(1 for e in ev if e.get("area") == "loop_area") == 2, "loop flooded the log"
    assert any(e.get("ext") == ".pdf" and e.get("pages") == 3 for e in ev)
    assert any(a["action"] == "other" for a in act)
    assert any(a["action"] == "scan_finished" and a["terms"] == 4 for a in act)
    assert not os.path.exists(os.path.join(d, "crash_raw.txt"))
    print(f"diag ok: {len(ev)} events, {len(act)} activity lines, no data leaked")
    # crash conversion
    open(os.path.join(d, "crash_raw.txt"), "w").write('Fatal Python error: Segmentation fault\n\nThread 0x1:\n  File "C:\\Users\\jdoe\\AH\\app_gui.py", line 812 in read_pdf\n')
    diag.setup(d, "test2"); diag.shutdown()
    blob = open(os.path.join(d, "events.jsonl"), encoding="utf-8").read()
    assert "app_gui.py:812:read_pdf" in blob and "jdoe" not in blob and not os.path.exists(os.path.join(d, "crash_raw.txt"))
    print("crash conversion ok")

if __name__ == "__main__":
    run()
