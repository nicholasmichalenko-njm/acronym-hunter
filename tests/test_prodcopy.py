"""3.6.0 the copy-only write path: the original is read once and never written; the copy is named, dated and marked as
Stationkeeper output in the output folder only; a file in use or changing is not copied; the engine refuses every
write that is not a Stationkeeper copy in an output folder; the original's SHA-256, size and date are the same after
every step."""
import os, shutil, sys, tempfile, zipfile, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import prodcopy as PC
from prodengine.engine.pkg import Package
from prodengine.pe import rules as R, fonts as Fo
from tests.pefix import fixtures_fonts as FF

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


tmp = tempfile.mkdtemp()
src_dir = os.path.join(tmp, "Effort", "Volumes"); os.makedirs(src_dir)
out = os.path.join(tmp, "Stationkeeper Data", "Production Copies")
orig = os.path.join(src_dir, "Volume I Technical.docx")
shutil.copy2(os.path.join(HERE, "pefix", "data", "small.docx"), orig)
before = PC.state(orig)
when = datetime.datetime(2026, 10, 31, 16, 2)

check("the default output folder is in the Stationkeeper data folder", PC.output_folder({}, "/D") == os.path.join("/D", "Production Copies")
      and PC.output_folder({"prod_output_dir": "/X"}, "/D") == "/X")
job = PC.make_copy(orig, out, when=when, open_list=[])
check("the copy is named, dated and marked as Stationkeeper output", os.path.basename(job.copy) == "Volume I Technical - COPY - Stationkeeper 2026-10-31 1602.docx"
      and os.path.dirname(job.copy) == out, job.copy)
check("the copy is the original byte for byte", PC.sha256_file(job.copy) == before["sha256"])
check("the original is unchanged (SHA-256, size, date)", PC.state(orig) == before and job.original_unchanged())
check("the report goes beside the copy", job.report_path == os.path.join(out, "Volume I Technical - COPY - Stationkeeper 2026-10-31 1602 - report.xlsx"))
job2 = PC.make_copy(orig, out, when=when, open_list=[])
check("never over another file: the same minute gets (2)", os.path.basename(job2.copy).endswith("1602 (2).docx") and os.path.isfile(job.copy))
check("a copy of a copy keeps one stamp", PC.copy_name(job.copy, when) == "Volume I Technical - COPY - Stationkeeper 2026-10-31 1602.docx"
      and PC.copy_name(job2.copy, when) == "Volume I Technical - COPY - Stationkeeper 2026-10-31 1602.docx")


def refused(fn, kind):
    n = len(os.listdir(out))
    try:
        fn()
    except kind as e:
        return str(e), len(os.listdir(out)) == n
    return "", False


owner = os.path.join(src_dir, "~$lume I Technical.docx"); open(owner, "w").write("x")
msg, none = refused(lambda: PC.make_copy(orig, out, open_list=[]), PC.Busy)
check("Word's owner file beside it: not copied, nothing written", none and "owner file" in msg, msg)
os.remove(owner)
msg, none = refused(lambda: PC.make_copy(orig, out, open_list=[orig]), PC.Busy)
check("open in Office on this PC: not copied", none and "open in Word, Excel or PowerPoint" in msg, msg)
url = "https://contoso.sharepoint.com/sites/Proposals/Shared%20Documents/Volume%20I%20Technical.docx"
msg, none = refused(lambda: PC.make_copy(orig, out, open_list=[url]), PC.Busy)
check("open from SharePoint (matched by file name): not copied", none and "OneDrive or SharePoint" in msg, msg)
msg, none = refused(lambda: PC.make_copy(orig, out, open_list=None), PC.Busy)
check("when Office cannot be asked, the answer is no", none and "could not ask Office" in msg, msg)
real_stat = os.stat
calls = {"n": 0}


def moving_stat(p, *a, **k):
    st = real_stat(p, *a, **k)
    if os.path.abspath(p) == orig:
        calls["n"] += 1
        if calls["n"] == 2:
            return os.stat_result((st.st_mode, st.st_ino, st.st_dev, st.st_nlink, st.st_uid, st.st_gid, st.st_size + 1,
                                   int(st.st_atime), int(st.st_mtime), int(st.st_ctime)))
    return st


PC.os.stat = moving_stat
msg, none = refused(lambda: PC.make_copy(orig, out, open_list=[]), PC.Busy)
PC.os.stat = real_stat
check("a file that changes while it is read: not copied", none and "changed while" in msg, msg)
bad = os.path.join(src_dir, "Half synced.docx"); open(bad, "wb").write(open(orig, "rb").read()[:5000])
msg, none = refused(lambda: PC.make_copy(bad, out, open_list=[]), PC.Busy)
check("an incomplete file: not copied", none and "not a complete Office file" in msg, msg)
txt = os.path.join(src_dir, "notes.txt"); open(txt, "w").write("x")
msg, none = refused(lambda: PC.make_copy(txt, out, open_list=[]), PC.NotAllowed)
check("only Office files", none and "Only Word, Excel and PowerPoint" in msg, msg)
msg, _n = refused(lambda: PC.make_copy(orig, src_dir, open_list=[]), PC.NotAllowed)
check("copies never go beside the original", "Choose another output folder" in msg and len([f for f in os.listdir(src_dir) if "COPY" in f]) == 0, msg)
# the engine's write guard
sw = PC.install_guard()
from prodengine.engine.pkg import Refused
op = lambda pkg: {}   # noqa: E731
msg, _n = refused(lambda: sw.apply(orig, op), PC.NotAllowed)
check("the engine refuses to write the original", "only into the production output folder" in msg, msg)
plain = os.path.join(out, "Volume I Technical.docx"); shutil.copy2(orig, plain)
msg, _n = refused(lambda: sw.apply(plain, op), PC.NotAllowed)
check("the engine refuses a file in the output folder that is not a Stationkeeper copy", "its own dated copies" in msg, msg)
os.remove(plain)
other = os.path.join(tmp, "Elsewhere"); os.makedirs(other)
fake = os.path.join(other, os.path.basename(job.copy)); shutil.copy2(job.copy, fake)
msg, _n = refused(lambda: sw.apply(fake, op), PC.NotAllowed)
check("a copy-like name outside an output folder is refused too", "output folder" in msg, msg)
real_norm = PC.os.path.normcase
PC.os.path.normcase = lambda x: x.lower()          # Windows lowers paths: the copy's own name must still pass
PC.allow_root(out)
try:
    PC.check_write(job.copy); win_ok = True
except PC.NotAllowed:
    win_ok = False
PC.os.path.normcase = real_norm
check("Windows path case: the guard still knows Stationkeeper's own copy", win_ok)
check("THE GATE: the original is unchanged after the refusals", PC.state(orig) == before)
# a real fix on the copy (fonts), then the properties
fsrc = os.path.join(src_dir, "Fonts.docx"); FF.make(fsrc)
fbefore = PC.state(fsrc)
fjob = PC.make_copy(fsrc, out, open_list=[])
std = R.resolve(R.COMPANY, effort={"fonts": FF.RULES})
rec = PC.run_step(fjob, "Fonts", Fo.op_fonts, Fo.FONTS_ALLOWED, {"std": std})
check("a fix runs on the copy through the guarded write", rec["changed"] and "refused" not in rec and PC.sha256_file(fjob.copy) != fbefore["sha256"], rec)
check("no snapshot folder clutters the output folder", not any(n.startswith("_PE") for n in os.listdir(out)), os.listdir(out))
check("THE GATE: the original is unchanged after the fix", PC.state(fsrc) == fbefore and fjob.original_unchanged())
m = PC.mark_properties(fjob)
with zipfile.ZipFile(fjob.copy) as z:
    cust = z.read("docProps/custom.xml").decode("utf-8")
    rels = z.read("_rels/.rels").decode("utf-8")
check("the copy is marked in its properties", m["changed"] and "Stationkeeper copy" in cust and "Copy of Fonts.docx made by Stationkeeper" in cust
      and "custom-properties" in rels, m)
PC.mark_properties(fjob)
with zipfile.ZipFile(fjob.copy) as z:
    cust = z.read("docProps/custom.xml").decode("utf-8")
check("marking twice keeps one property, and the copy still opens", cust.count('name="Stationkeeper copy"') == 1 and Package(fjob.copy).is_word)
own = os.path.join(out, "~$" + os.path.basename(fjob.copy)); open(own, "w").write("x")
rec = PC.run_step(fjob, "Fonts again", Fo.op_fonts, Fo.FONTS_ALLOWED, {"std": std})
check("someone opened the copy: the step is refused, the copy kept", "refused" in rec and "opened the copy" in rec["refused"], rec)
os.remove(own)
if sys.platform.startswith("win"):
    with open(orig, "rb"):
        msg, none = refused(lambda: PC.make_copy(orig, out, open_list=[]), PC.Busy)
    check("Windows: another program holding the file: not copied", none and "Another program" in msg, msg)
check("THE GATE: every original unchanged at the end", PC.state(orig) == before and PC.state(fsrc) == fbefore)
n = sum(checks)
print(f"PROD COPY {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
