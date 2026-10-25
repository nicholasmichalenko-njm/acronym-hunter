"""2.15.0 corrections: Acronym Hunter saves corrected readings and sends them as a corrections pack; Acronym Hunter
Training checks a pack (format, file names, SHA-256 of every file, PNG pictures) before copying anything, imports it
once, and taught lines leave out what the training team rejected or fixed."""
import os, sys, tempfile, zipfile, json, csv
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_TEST"] = "1"
import app_gui as A
import corrections as C
import tess_train
from PIL import Image

tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); os.makedirs(A.CONFIG_DIR)
user, team = os.path.join(tmp, "user_td"), os.path.join(tmp, "team_td")
img = Image.new("RGB", (60, 20), "white")

C.set_dir(user)
for i, (t, r) in enumerate((("RFP", "RFF"), ("SE&I", "SE8I"), ("TT&C", "TT8C"))):
    C.save_sample(img, t, r, 0.5, f"Deck.pptx (Slide {i + 1})", (0, 0, 60, 20))
C.save_region(img, [], [], [((0, 0, 5, 5), "~~", 0.4)], "Diagram.png (Image)", (0, 0, 60, 20))
lines, regions = C.unsent()
assert len(lines) == 3 and len(regions) == 1, (lines, regions)
pack = os.path.join(tmp, "pack1.zip")
r = C.export_pack(pack)
assert r["lines"] == 3 and r["regions"] == 1, r
assert C.unsent() == ([], []), "sent samples are not sent again"
C.save_sample(img, "CDRL", "CDRI", 0.6, "Doc.pdf (p.2)", (0, 0, 60, 20))
r2 = C.export_pack(os.path.join(tmp, "pack2.zip"))
assert r2["lines"] == 1 and r2["regions"] == 0, r2
print("export ok")

# tampered, traversal and junk packs are refused, nothing copied
def remake(src, dst, change):
    with zipfile.ZipFile(src) as z, zipfile.ZipFile(dst, "w") as o:
        items = {n: z.read(n) for n in z.namelist()}
        change(items)
        for n, d in items.items():
            o.writestr(n, d)
bad = os.path.join(tmp, "bad.zip")
remake(pack, bad, lambda it: it.__setitem__([n for n in it if n.endswith(".png")][0], b"\x89PNG\r\n\x1a\nchanged"))
C.set_dir(team)
for maker, why in ((lambda it: it.__setitem__([n for n in it if n.endswith(".png")][0], b"\x89PNG\r\n\x1a\nchanged"), "checksum"),
                   (lambda it: it.__setitem__("../evil.png", b"x"), "unexpected"),
                   (lambda it: it.__setitem__("manifest.json", json.dumps({"format": "Other"}).encode()), "wrong format")):
    remake(pack, bad, maker)
    try:
        C.import_pack(bad); raise SystemExit("bad pack was imported: " + why)
    except C.PackError as ex:
        assert why in str(ex), (why, ex)
assert not os.path.exists(C.LABELS_FILE), "nothing copied from a refused pack"
print("refused ok")

got = C.import_pack(pack)
assert got["lines"] == 3 and got["regions"] == 1 and got["skipped"] == 0, got
again = C.import_pack(pack)
assert again["lines"] == 0 and again["skipped"] == 4, again
C.import_pack(os.path.join(tmp, "pack2.zip"))
s = C.samples()
assert len(s) == 4 and all(x["source"].startswith("Pack from") for x in s), s
assert len(C.packs()) == 3
rfp = next(x for x in s if x["text"] == "RFP")
C.set_rejected([rfp["rel"]])
taught = {t for _p, t in tess_train.read_samples(team)}
assert "RFP" not in taught and "SE&I" in taught, taught
tt = next(x for x in s if x["text"] == "TT&C")
assert C.set_text(tt["rel"], "TT&C (fixed)")
assert "TT&C (fixed)" in {t for _p, t in tess_train.read_samples(team)}
assert C.set_rejected([rfp["rel"]], on=False) == 0
print("corrections ok")
