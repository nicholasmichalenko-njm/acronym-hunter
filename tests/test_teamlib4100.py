"""4.10.0: the library's kept Word files carry plain names in the team library (Cover.docx, Cover (2).docx), an index
CSV ties each plain name to the file the app keeps, and an older team library's fingerprinted names take their plain
names. Edits follow both ways as before. Fictional content."""
import csv, os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
import teamlib as T

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("ok  " if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "Stationkeeper Data", "config"); os.makedirs(cfg)
S = {"team_library": ""}
src = os.path.join(cfg, "template_library", "sources"); os.makedirs(src)
lib = os.path.join(T.folder(cfg, S), "Content", "Library files")
older = os.path.join(src, "Cover_page_0123456789.docx"); open(older, "wb").write(b"cover one")
time.sleep(0.02)
newer = os.path.join(src, "Cover_page_abcdef0123.docx"); open(newer, "wb").write(b"cover two")
open(os.path.join(src, "Back_cover_1111111111.docx"), "wb").write(b"back")
got = T.sync_content(cfg, S)
names = sorted(os.listdir(lib))
check("the team library shows plain names, the older version first", names == sorted(["Back cover.docx", "Cover page (2).docx", "Cover page.docx",
                                                                             T.INDEX]), names)
check("... with what each holds", open(os.path.join(lib, "Cover page.docx"), "rb").read() == b"cover one"
      and open(os.path.join(lib, "Cover page (2).docx"), "rb").read() == b"cover two")
rows = list(csv.reader(open(os.path.join(lib, T.INDEX), encoding="utf-8-sig")))
check("the index ties each plain name to the app's kept file and its fingerprint", rows[0] == ["Name", "Kept in the app as", "Fingerprint"]
      and ["Cover page.docx", "Cover_page_0123456789.docx", "0123456789"] in rows, rows)
check("the sync reports the plain names", sorted(got["out"]) == ["Back cover.docx", "Cover page (2).docx", "Cover page.docx"], got)
time.sleep(0.02); open(os.path.join(lib, "Cover page.docx"), "wb").write(b"cover one, edited in Word")
got = T.sync_content(cfg, S)
check("edited in Word under its plain name, the app's kept file follows", open(older, "rb").read() == b"cover one, edited in Word"
      and got["in"] == ["Cover page.docx"], got)
open(newer, "wb").write(b"cover two, changed in the app")
T.sync_content(cfg, S)
check("changed in the app, the plain-named file follows", open(os.path.join(lib, "Cover page (2).docx"), "rb").read() == b"cover two, changed in the app")
T.sync_content(cfg, S)
check("the names hold from one sync to the next", sorted(os.listdir(lib)) == names)
open(os.path.join(lib, "Letterhead.docx"), "wb").write(b"from the team")
T.sync_content(cfg, S)
check("a file someone put in the team library comes into the app as named", open(os.path.join(src, "Letterhead.docx"), "rb").read() == b"from the team")
check("the index is not copied into the app", not os.path.exists(os.path.join(src, T.INDEX)))
# a team library written by 4.7 to 4.9: fingerprinted names take their plain names
tmp2 = tempfile.mkdtemp()
cfg2 = os.path.join(tmp2, "Stationkeeper Data", "config"); src2 = os.path.join(cfg2, "template_library", "sources"); os.makedirs(src2)
lib2 = os.path.join(T.folder(cfg2, S), "Content", "Library files"); os.makedirs(lib2)
open(os.path.join(src2, "Title_page_2222222222.docx"), "wb").write(b"title")
open(os.path.join(lib2, "Title_page_2222222222.docx"), "wb").write(b"title")
st = T.state(cfg2); st.setdefault("content", {})["Library files/Title_page_2222222222.docx"] = T._sha(os.path.join(src2, "Title_page_2222222222.docx"))
T._save_state(cfg2, st)
got = T.sync_content(cfg2, S)
check("an older team library: the fingerprinted file is renamed to its plain name, nothing copied", sorted(os.listdir(lib2)) == sorted(["Title page.docx", T.INDEX])
      and not got["in"] and not got["out"], (os.listdir(lib2), got))
print(f"TEAMLIB 4100 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
