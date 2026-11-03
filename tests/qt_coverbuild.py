"""3.34.0 covers built in the window, offscreen: Document parts > Cover's New from a blank page and From a saved cover
layout, and The title page; the layout editor's Background picture (full bleed, inside the margins), + Text block,
Remove the selected block, Save as a cover layout, Keep in the library and Save; a title page kept on the profile."""
import io, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
import coverbuild as CB, coverlayout as CL, templatelib as TL
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
from skqt import docparts as DP

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
from PIL import Image
pic = os.path.join(tmp, "background.png")
Image.new("RGB", (1300, 1700), (31, 56, 100)).save(pic, "PNG")
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1600, 980); w.show()
w.go("prodstd"); app.processEvents()
sp = w.prodstd_page
check("Document parts > Cover: The title page card, nothing kept yet", "No title page" in sp.part_ui["cover"]["title_lab"].text())
d = DP.new_page(sp, "cover", run=False)
check("New from a blank page: the editor on a blank page", d is not None and d.data and not [p for p in CL.read(d.data)["pieces"]])
check("Background picture: full bleed", d.background(pic, mode="bleed") and CB.background_mode(d.result_bytes()) == "bleed"
      and any(p["kind"] == "picture" for p in d.pieces))
d.add_block({"field": "volume_name", "x": 1.0, "y": 4.0, "w": 6.5, "h": 0.8, "size": 30, "bold": True, "color": "FFFFFF", "align": "center"})
d.add_block({"text": "Draft for review", "x": 1.0, "y": 9.5, "w": 3.0, "h": 0.4})
d.add_block({"field": "solicitation", "x": 1.0, "y": 5.0, "w": 6.5, "h": 0.4})
texts = [d.texts.item(r, 0).text() for r in range(d.texts.rowCount())]
check("+ Text block: three blocks, each a line on the page", texts == ["[Volume name]", "Draft for review", "[Solicitation]"], texts)
check("Remove the selected block", d.remove_block("table2") and [d.texts.item(r, 0).text() for r in range(d.texts.rowCount())] == ["[Volume name]", "[Solicitation]"])
check("a block not made here is not removed", not d.remove_block("picture1"))
d.background(pic, mode="margins")
check("Background picture again, inside the margins: one picture, the blocks kept", CB.background_mode(d.result_bytes()) == "margins"
      and len([p for p in d.pieces if p["kind"] == "picture"]) == 1 and d.texts.rowCount() == 2)
if os.environ.get("SK_SHOT"):
    d.resize(1180, 820); d.show(); app.processEvents(); d.grab().save(os.environ["SK_SHOT"])
lay = d.save_layout("Space Force cover", "navy")
lib = TL.Library(cfg)
check("Save as a cover layout: in the library, its structure (not its picture)", lay is not None and lay["kind"] == "cover_design"
      and len(lib.values(lay)["blocks"]) == 2 and lib.values(lay)["background"] == "margins" and lib.shown_name(lay) == "Space Force cover v1: navy")
lay2 = d.save_layout("Space Force cover")
check("... the same name again: the same layout (nothing changed)", lay2["id"] == lay["id"])
kept = d.keep_in_library("Navy cover")
check("Keep in the library: the page itself on the Covers shelf", kept["kind"] == "cover" and os.path.isfile(TL.Library(cfg).source_path(TL.Library(cfg).values(kept)["file"])))
name = d.save()
check("Save: the profile's cover", name and sp.work["page_parts"]["cover"] == name and os.path.isfile(os.path.join(sp.parts_dir(), name)))
# ---------------------------------------------------------------- the title page, from the saved layout
t = DP.new_page(sp, "title", from_layout=True, layout_id=lay["id"], run=False)
check("From a saved cover layout: its blocks, ready for a picture", t.windowTitle() == "Edit the title page layout"
      and [t.texts.item(r, 0).text() for r in range(t.texts.rowCount())] == ["[Volume name]", "[Solicitation]"] and not CB.has_background(t.data))
t.add_block({"text": "TITLE PAGE", "x": 1.0, "y": 2.0, "w": 6.5, "h": 0.5})
tn = t.save()
DP.fill(sp, "cover")
check("Save: the profile's title page, listed on the Cover part", sp.work["page_parts"]["title"] == tn and tn in sp.part_ui["cover"]["title_lab"].text())
sp.nav.setCurrentRow(sp.section_index("profile_parts")); app.processEvents()
row = next(r for r in range(sp.profile_parts.t.rowCount()) if sp.profile_parts.t.item(r, 1).text() == "Title page")
check("Template profile > Parts and versions lists the title page", sp.profile_parts.t.item(row, 2).text() == "the profile's own values",
      sp.profile_parts.t.item(row, 2).text())
it = sp.profile_parts.save_version("title", name="Volume title page", label="")
check("... Save as a new version keeps it on the Title pages shelf", it["kind"] == "title" and TL.Library(cfg).shelf("title"))
e = DP.edit_layout(sp, "title", run=False)
check("Edit the layout opens the title page", e is not None and e.texts.rowCount() == 3)
DP.clear_page(sp, "title")
check("Clear takes the title page off", "title" not in sp.work["page_parts"])
w.close()
n = sum(checks)
print(f"QT COVER BUILD {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.stdout.flush()
os._exit(0 if n == len(checks) else 1)
