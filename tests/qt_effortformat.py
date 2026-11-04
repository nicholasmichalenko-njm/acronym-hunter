"""3.36.0 Effort Formatting, offscreen: a page under Effort with this effort's formatting on top of the team's
standards. A value set here is the effort's only (the team standard is untouched) and Fix a Copy and templates use it;
Reset takes it back; a change for one volume holds for that volume only; the RFP's rules show beside each value with
Use it, in red when the value breaks them; Keep for the team writes the value into a team layer and Undo puts it back;
Every setting opens Production Standards on this effort (amber band), and the menu opens the team's standards (blue)."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
import app_gui as A
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "appconfig"); os.makedirs(A.CONFIG_DIR)
A.SETTINGS_FILE = os.path.join(tmp, "settings.json"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
import effort as E, workspace as W, prodrules as PRL, effortformat as EFM, roleaccess as RA
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
import skqt.mainwin as MW
from skqt.mainwin import MainWindow

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Kestrel"); os.makedirs(EDIR)
LIST = os.path.join(EDIR, "Kestrel_Effort_List.xlsx")
L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Kestrel", path=LIST)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()
w.open_effort("Kestrel"); app.processEvents()
check("Effort Formatting is in the Effort menu, for the Production role too", ("effortfmt", "Effort Formatting") in dict(MW.RAIL)["Effort"]
      and RA.allowed("Production", "effortfmt") and not RA.allowed("Author", "effortfmt"))
w.go("effortfmt"); app.processEvents()
pg = w.effortfmt_page
check("the page opens on the effort, amber band, every value the team's", pg.body.isVisible() and "Kestrel only" in pg.band.text()
      and "Nothing yet" in pg.changes.text())
team_font = PRL.load(cfg)["company"]["variables"]["body_font"]
check("each value shows the team's beside it", pg.rows["body_font"]["team"].text() == team_font)
pg.edited("body_font", "Arial"); pg.edited("body_size", 12.0); pg.edited("caption_table", "below"); pg.edited("heading_font", "Calibri")
std = PRL.for_effort(cfg, w.ws)
check("this effort's values are in force", std["variables"]["body_font"] == "Arial" and std["variables"]["body_size"] == 12.0
      and std["style_defs"]["Heading 2"]["font"] == "Calibri"
      and next(c for c in std["captions"] if c["label"] == "Table" and c["part"] == "body")["position"] == "below")
check("the team's standards are untouched", PRL.load(cfg)["company"]["variables"]["body_font"] == team_font)
check("Changed for this effort lists them", "Body text: Font" in pg.changes.text() and "Captions: Table captions" in pg.changes.text()
      and pg.rows["body_font"]["ed"].font().bold())
pg.reset("caption_table")
check("Reset takes one back to the team's", EFM.get(cfg, w.ws, "caption_table")["effort"] is None
      and next(c for c in PRL.for_effort(cfg, w.ws)["captions"] if c["label"] == "Table" and c["part"] == "body")["position"] == "above")
data, eid, default, vols = EFM.ids(cfg, w.ws)
pg.set_etype("rfp_limited"); app.processEvents()
data, eid, default, vols = EFM.ids(cfg, w.ws)
check("the effort takes an effort type here", eid == "rfp_limited" and pg.etype.currentData() == "rfp_limited")
cost = vols[-1]
pg.scope.setCurrentIndex(pg.scope.findData(cost)); pg.fill()
pg.edited("table_size", 8.0)
check("a change for one volume holds for that volume only", PRL.for_effort(cfg, w.ws, type_id=cost)["variables"]["table_size"] == 8.0
      and PRL.for_effort(cfg, w.ws, type_id=vols[0])["variables"]["table_size"] != 8.0 if len(vols) > 1 else
      PRL.for_effort(cfg, w.ws, type_id=cost)["variables"]["table_size"] == 8.0)
check("a volume inherits the effort's every-volume values", pg.rows["body_font"]["team"].text() == "Arial")
pg.scope.setCurrentIndex(0); pg.fill()
from skqt.custdocs import Ctx
reg = Ctx(w).reg
reg.add("Format", "Font", "12-point Times New Roman"); reg.add("Format", "Margins", "1-inch margins")
pg.refresh()
check("the RFP's rule shows beside the value, in red where it breaks it", "12-point Times New Roman" in pg.rows["body_font"]["rfp"].text()
      and pg.rows["body_font"].get("bad") and pg.rows["body_font"]["use"].isVisible())
pg.use_rfp("body_font")
check("Use it takes the RFP's value", EFM.get(cfg, w.ws, "body_font")["effort"] == "Times New Roman" and not pg.rows["body_font"].get("bad"))
e = pg.keep("body_size", "team")
check("Keep for the team writes it into the team standard and takes it off the effort",
      e and PRL.load(cfg)["company"]["variables"]["body_size"] == 12.0 and EFM.get(cfg, w.ws, "body_size")["effort"] is None
      and EFM.history(cfg)[-1]["field"] == "body_size")
pg.undo_keep()
check("Undo puts the team standard back", PRL.load(cfg)["company"]["variables"]["body_size"] != 12.0 and EFM.history(cfg)[-1].get("undone"))
check("library parts list where each comes from", pg.parts.rowCount() >= 10 and pg.parts.item(0, 1).text())
pg.every_setting(); app.processEvents()
sp = w.prodstd_page
check("Every setting opens Production Standards on this effort, amber band", w.stack.currentWidget() is sp and sp.mode == "effort"
      and sp.scope == "effort" and "Kestrel only" in sp.band.text() and sp.band_back.isVisible()
      and sp.work["variables"]["body_font"] == "Times New Roman")
sp.vol_pick.setCurrentIndex(sp.vol_pick.findData("effortvol:" + cost)); sp.picked(); app.processEvents()
check("there, one volume of the effort", sp.scope == "effortvol" and sp.work["variables"]["table_size"] == 8.0)
it = next(i for i in sp.binder.items if i["path"] == ("variables", "caption_size"))
it["w"].setValue(7.0); sp.save()
check("a change there is the volume's, in the effort", EFM.layer(w.ws, cost)["variables"].get("caption_size") == 7.0
      and PRL.load(cfg)["company"]["variables"]["caption_size"] != 7.0)
w.go("prodstd"); app.processEvents()
check("the menu opens the team's standards, blue band, no effort scope", sp.mode == "team" and sp.scope == "team"
      and "every effort" in sp.band.text() and not sp.band_back.isVisible() and sp.scope_box.findData("effort:") < 0
      and not sp.this_effort.isVisible())
w.close()
n = sum(checks)
print(f"QT EFFORT FORMAT PASS ({n}/{len(checks)})" if n == len(checks) else f"QT EFFORT FORMAT FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
