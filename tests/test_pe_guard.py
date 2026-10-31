"""3.6.0 the engine's guard against rogue operations (from the feasibility lab, 22 cases): changes to anything an
operation did not declare (styles, numbering, settings, table text, alt text, bookmarks, pictures, parts, fields) are
refused with the original byte identical; hard kills at every write step leave the file intact; owner files, altChunk,
data binding, Mark as Final, non-Word packages and malformed XML are refused; macros are kept."""
import json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
work = tempfile.mkdtemp(prefix="pe_guard_")
res = os.path.join(work, "results.json")
data = os.path.join(HERE, "pefix", "data")
p = subprocess.run([sys.executable, os.path.join(HERE, "pefix", "rogue.py"), os.path.join(data, "small.docx"), work, res,
                    os.path.join(data, "PE_Master_Effort_Template.dotx")], capture_output=True, text=True, timeout=900)
try:
    data_out = json.load(open(res, encoding="utf-8"))
except (OSError, ValueError):
    data_out = {}
cases = data_out.get("results", data_out.get("cases_detail", [])) if isinstance(data_out, dict) else data_out
summary = data_out.get("summary", {}) if isinstance(data_out, dict) else {}
print(p.stdout[-300:], p.stderr[-500:]) if not cases else None
for c in cases:
    print("PASS" if c.get("pass") else "FAIL", c["case"], "" if c.get("pass") else c.get("message", ""))
ok = summary.get("cases") == 22 and not summary.get("failed") and len(cases) == 22 and all(c.get("pass") for c in cases)
print(f"TEST PE GUARD {'PASS' if ok else 'FAIL'} ({sum(1 for c in cases if c.get('pass'))}/{len(cases)})")
sys.exit(0 if ok else 1)
