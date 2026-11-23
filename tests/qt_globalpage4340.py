"""4.34.0, offscreen (ST7, ST9, ST14, ST18, ST19 of 2026-11-14): the Global Standards page. Its own page in the menu;
a change is shared at once with no Update button and no Put back; the number is in the window's title; a newer version
is told and taken as before; who has it is listed from each PC's receipt; the page and the editors it opens change the
Global Standards while an effort stays open; Save a file to share... Fictional values."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_THEME"] = "light"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effortset as ES, globalfile as GX, globalfolder as GF, globalstd as GS, prodrules as PRL
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as D, globalview as GV
from skqt.mainwin import MainWindow, RAIL

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


def put(rel, data):
    with open(os.path.join(cfg, rel), "w", encoding="utf-8") as f:
        f.write(data if isinstance(data, str) else json.dumps(data))


def rules(limit):
    put("rules.json", {"format": 1, "rules": [{"id": "r1", "limit": limit}]})


cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
F = os.path.join(tmp, "Shared", "Global Standards"); os.makedirs(F)
app = QApplication([]); D.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show(); app.processEvents()
check("Global Standards is a page of its own in the menu, first under Standards and Formatting (4.60.0)", dict(RAIL)["Standards and Formatting"][0] == ("globalstd", "Global Standards"))
w.go("globalstd"); app.processEvents()
gp = w.globalstd_page
vis = lambda b: not b.isHidden()
check("the page opens with its title", w.stack.currentWidget() is gp and w.page_title.text() == "Global Standards", w.page_title.text())
check("not connected: one sentence and one way to Settings; no setup buttons, no count", "No Production Datum is installed" in gp.gs_folder.text()
      and vis(gp.gs_setup) and not hasattr(gp, "gs_link") and not vis(gp.who_count) and not vis(gp.who_card), gp.gs_folder.text())
check("there is no Update button and no Put back (ST14)", not hasattr(gp, "gs_update") and not hasattr(GV, "update_dialog"))
words = (gp.gs_folder.text() + gp.edit_card.title.text() + GV.NOT_CONNECTED + " ".join(b.text() for b in gp.edit_buttons.values())).lower()
check("the page's words: no publish, no draft, no changes waiting, no starter set", not any(x in words for x in ("publish", "draft", "changes waiting", "put back", "starter set", "built-in starter")), words)
check("Settings holds the setup and the way to the page", hasattr(w.settings_page, "gsl_card") and not hasattr(w.settings_page, "gs_card"))
GV.link(w.settings_page, F); gp.refresh(); app.processEvents()
check("linked to a folder this PC can write to: a change saved here reaches everyone", GF.folder() == F and "reaches everyone" in gp.gs_folder.text() and not vis(gp.gs_setup), gp.gs_folder.text())
check("an empty shared folder: what this PC has becomes version 1", GF.versions(F) == [1] and GS.state(cfg)["version"] == 1, GF.versions(F))
rules(11)
gp.refresh(); app.processEvents()
check("a save is shared at once: version 2 is in the folder with no button pressed", GF.versions(F) == [1, 2] and GS.state(cfg)["version"] == 2, GF.versions(F))
check("the number is in the window's title", "Production Datum 2" in w.windowTitle(), w.windowTitle())
rules(12)
said = GV.share_now(w)
check("the next save is the next version, and the person is told", GF.versions(F) == [1, 2, 3] and "Global Standards 3" in said and "is shared" in said
      and "Production Datum 3" in w.windowTitle(), said)
check("with nothing saved since, nothing is shared", GV.share_now(w) == "" and GF.versions(F) == [1, 2, 3])
rules(13)
check("the tick shares too", GV.watch(w) != "" and GF.versions(F) == [1, 2, 3, 4])

# who has it
gp.refresh(); app.processEvents()
rows = [[gp.who.item(r, c).text() for c in range(4)] for r in range(gp.who.rowCount())]
check("the count is on the page; the list is closed until the count is pressed (ST23)", vis(gp.who_count) and gp.who_count.text() == "1 of 1 person is on version 4"
      and not vis(gp.who_card), gp.who_count.text())
gp.who_count.click(); app.processEvents()
check("pressing the count opens the list: this PC's own line with the version it is on", vis(gp.who_card) and len(rows) == 1 and rows[0][2] == "4", rows)
json.dump({"format": 1, "name": "Ben", "pc": "PC-0522", "version": 2, "when": "2026-11-13 09:00"}, open(os.path.join(F, "Receipts", "Ben (PC-0522).json"), "w"))
gp.refresh(); app.processEvents()
rows = [[gp.who.item(r, c).text() for c in range(4)] for r in range(gp.who.rowCount())]
check("someone behind comes first, with the latest named", rows[0] == ["Ben", "PC-0522", "2 (latest is 4)", "2026-11-13 09:00"] and gp.who_count.text() == "1 of 2 people are on version 4", (rows, gp.who_count.text()))
gp.who.selectRow([r[0] for r in rows].index("Ben"))
check("Remove the line removes that person's file only", gp.forget() == 1 and not os.path.exists(os.path.join(F, "Receipts", "Ben (PC-0522).json")) and gp.who.rowCount() == 1)
gp.who_count.click(); app.processEvents()
check("pressing the count again closes the list", not vis(gp.who_card))

# the page and its editors change the Global Standards while an effort stays open (ST9)
w.go("home"); app.processEvents()
f = w.home_page.start; f.name.setText("Osprey"); f.create(); app.processEvents()
root = w.ws.root
w.go("styles"); app.processEvents()
check("in the effort, a standards page changes the effort's own set", w.page_sub.text().startswith("Effort Standards: Osprey.") and ES.base(cfg) == ES.set_dir(root), w.page_sub.text())
w.go("globalstd"); app.processEvents()
check("the Global Standards page opens with the effort still open", w.stack.currentWidget() is gp and w.effort_name == "Osprey" and ES.base(cfg) == cfg)
gp.edit_buttons["styles"].click(); app.processEvents()
check("an editor opened from it says Global Standards and changes the Global Standards", w.stack.currentWidget() is w.styles_page
      and w.page_sub.text().startswith("Global Standards. A change here is saved for everyone.") and ES.base(cfg) == cfg, w.page_sub.text())
d = PRL.load(cfg); d["company"]["variables"]["body_font"] = "Global Font"; PRL.save(cfg, d)
n_before = len(GF.versions(F))
w.go("home"); app.processEvents()
check("leaving for the effort's work: the effort's own standards are in view again, untouched", ES.base(cfg) == ES.set_dir(root)
      and PRL.load(cfg)["company"]["variables"]["body_font"] != "Global Font" and not ES.viewing_global())
with ES.as_global():
    check("and what was saved in the Global Standards was shared on the way out", PRL.load(cfg)["company"]["variables"]["body_font"] == "Global Font"
          and len(GF.versions(F)) == n_before + 1 and not GF.waiting(cfg, F), GF.versions(F))
w.close_effort(); app.processEvents()
top = GF.versions(F)[-1]

# two people who can change them (ST13); a PC that only reads
other = os.path.join(tmp, "other", "config"); os.makedirs(other)
GF.take(other, F)
with open(os.path.join(other, "rules.json"), "w") as fh:
    json.dump({"format": 1, "rules": [{"id": "r1", "limit": 20}]}, fh)
GF.share(other, F, by="Ada")
w.go("globalstd"); app.processEvents()
check("a PC on an earlier version is told the newer one is ready, with who, and Use it now", f"Production Datum {top + 1} is ready, updated by Ada" in gp.gs_ready.text() and vis(gp.gs_use), gp.gs_ready.text())
rules(9)
said = GV.at_open(w)
check("this PC's own change is not shared over the newer version; it is told what Use it now replaces",
      GF.versions(F)[-1] == top + 1 and GS.state(cfg)["version"] == top and "is ready" in said and "replaces what this PC changed itself" in said, said)
gp.refresh(); said = GV.use_now(gp); app.processEvents()
check("Use it now takes it, says what it replaced and where the backup is, and the title follows", GS.state(cfg)["version"] == top + 1
      and "replaced this PC's own changes in: Rules" in said and "Global Standards backups" in said and f"Production Datum {top + 1}" in w.windowTitle(), said)
with open(os.path.join(other, "rules.json"), "w") as fh:
    json.dump({"format": 1, "rules": [{"id": "r1", "limit": 21}]}, fh)
GF.share(other, F, by="Ada")
real = GF.can_update
GF.can_update = lambda _f: False                                 # a PC whose account cannot write to the folder
gp.refresh(); app.processEvents()
check("a PC that only reads says so, and takes the newer version by itself when it opens", "reads the Global Standards from it" in gp.gs_folder.text()
      and f"Production Datum {top + 2}" in GV.at_open(w) and GS.state(cfg)["version"] == top + 2, gp.gs_folder.text())
rules(99)
check("... and shares nothing of its own", GV.share_now(w) == "" and GF.versions(F)[-1] == top + 2)
GF.can_update = real
rules(21)

# Save a file to share...
out = os.path.join(tmp, "to send.skgs")
check("Save a file to send... writes the latest in one file and leaves no copy in the folder", GV.save_file(w.settings_page, out) == out and os.path.isfile(out)
      and not [n for n in os.listdir(F) if n.endswith(".skgs")], os.listdir(F))
D2 = os.path.join(tmp, "d2", "config"); os.makedirs(D2)
check("that file installs on a PC with no folder", GX.install(D2, out)["version"] == GS.state(cfg)["version"])
on = GS.state(cfg)["version"]
GF.set_folder("")
rules(30)
out2 = os.path.join(tmp, "offline.skgs")
check("with no folder linked, a changed PC saves the next number", GV.save_file(w.settings_page, out2) == out2 and GS.state(cfg)["version"] == on + 1
      and GX.install(D2, out2)["version"] == on + 1, GS.state(cfg))
out3 = os.path.join(tmp, "again.skgs")
check("... and saving again with nothing changed keeps the number", GV.save_file(w.settings_page, out3) == out3 and GS.state(cfg)["version"] == on + 1, GS.state(cfg))
w.close()
n = sum(checks)
print(f"QT GLOBALPAGE 4340 {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
