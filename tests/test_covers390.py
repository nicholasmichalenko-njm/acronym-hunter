"""3.90.0 covers live in Section designs (decision 13): the template library's covers, title pages and back covers come
onto their Section designs shelves once each (the newest version of each family), marked with the item they came from,
never twice; a profile's cover, title page or back cover slot picks from those shelves (the profile keeps its own copy
of the file, as it does for a library page, and the slot is no longer pinned to a library version); a design on another
shelf is refused. Fictional content (Kestrel)."""
import os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("AH_TEST", "1")
import sectiondesigns as SDZ, templatelib as TL, templateprofile as TP, prodparts as PP

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


WNS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def page(path, text):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" '
                   'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("word/document.xml", f'<w:document {WNS}><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p><w:sectPr/></w:body></w:document>')
    return path


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
lib = TL.Library(cfg)
c1 = page(os.path.join(tmp, "Kestrel Cover.docx"), "KESTREL GROUND SEGMENT")
c2 = page(os.path.join(tmp, "Kestrel Cover v2.docx"), "KESTREL GROUND SEGMENT VOLUME I")
bk = page(os.path.join(tmp, "Kestrel Back.docx"), "Back cover")
v1, _ = lib.add("cover", "Volume cover", {"file": lib.keep_file(c1, "Kestrel Cover.docx"), "sha": "c1"})
v2, _ = lib.add("cover", "Volume cover", {"file": lib.keep_file(c2, "Kestrel Cover v2.docx"), "sha": "c2"})
b1, _ = lib.add("backer", "Back cover", {"file": lib.keep_file(bk, "Kestrel Back.docx"), "sha": "b1"})
lib.add("hf", "Volume header", {"left": "{marking}"})
lib = TL.Library(cfg)
n = SDZ.adopt(cfg, lib)
cov, back = SDZ.designs(cfg, "cover"), SDZ.designs(cfg, "back")
check("the library's covers come onto Section designs: one per family, the newest", n == 2 and len(cov) == 1 and len(back) == 1
      and cov[0]["library"] == v2["id"] and cov[0]["library_family"] == v1["family"], (n, cov, back))
check("... the newest version's file", "VOLUME I" in zipfile.ZipFile(SDZ.path_of(cfg, cov[0])).read("word/document.xml").decode())
check("... a header is not a section design", not SDZ.designs(cfg, "toc") and len(SDZ.designs(cfg)) == 2)
check("once only: brought again, nothing doubles", SDZ.adopt(cfg, TL.Library(cfg)) == 0 and len(SDZ.designs(cfg)) == 2)
std = {"library_pins": {"cover": {"id": v1["id"], "family": v1["family"], "version": 1}}}
check("a cover slot lists the cover shelf", [x["id"] for x in TP.design_choices(cfg, "cover")] == [cov[0]["id"]]
      and [x["id"] for x in TP.design_choices(cfg, "backer")] == [back[0]["id"]] and TP.design_choices(cfg, "title") == [])
said = TP.pick_design(std, cfg, "cover", cov[0]["id"])
pf = std.get("page_parts", {}).get("cover", "")
check("picking a design: the profile keeps its own copy and the slot is no longer pinned", said and pf
      and os.path.isfile(os.path.join(PP.parts_dir(cfg), pf)) and "cover" not in std["library_pins"]
      and std["design_picks"]["cover"] == cov[0]["id"], (said, std))
check("a design from another shelf is refused", TP.pick_design(std, cfg, "cover", back[0]["id"]) == "")
print(f"COVERS 390 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
