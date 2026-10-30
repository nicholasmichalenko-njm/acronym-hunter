"""2.97.0 sensitivity and SCIF-ready, without windows: the scale and the words read onto it; visible markings (banners,
authority blocks, portion marks, CUI) and the ordinary RFP text that must not count (FAR paragraphs lettered (C), a quote
headed CONFIDENTIAL, a blank Classified By box); labels stored in Word and PDF files, and banners in Word headers; the
spill guard stops intake and Read RFP before anything is copied (and does not in SCIF-ready); an effort's level from its
declared sensitivity and its documents; training packs state their sensitivity and Training refuses what is above CUI or
not known; training data is kept only for an effort at most CUI; the efforts sent to training leave out the rest;
SCIF-ready seals the program and data folders, deletes the old logs and training data, and stops logging."""
import json, os, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_TEST"] = "1"
import app_gui as A
import sensitivity as S, secure, workmode as WM, docintake as DI, docversions as DV, compliance_read as CR, pdfmini
import effort as E, effortrec as R, branding as BR, workspace as W, trainpack as TP, corrections as CO, diag

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
# the scale
check("the scale: General business < Proprietary < CUI < Confidential < Secret < Top Secret", S.LEVELS[0] == "General business"
      and S.LEVELS[-1] == "Top Secret" and S.TRAINING_MAX == S.CUI == 2 and S.READ_MAX == S.CUI)
words = {"Not CUI": S.GB, "CUI": S.CUI, "CUI//SP-PROPIN": S.CUI, "Proprietary": S.PROP, "Company Confidential": S.PROP,
         "Confidential": S.PROP, "CONFIDENTIAL//REL TO USA": S.CONF, "Secret": S.SECRET, "Top Secret//SCI": S.TS,
         "General": S.GB, "trade secrets": -1, "": -1, "FOUO": S.CUI}
got = {k: S.level_of_words(k) for k in words}
check("words onto the scale (a label called only Confidential is a business label)", got == words, got)
# markings
m = S.markings
check("a SECRET banner", m(["SECRET//NOFORN", "(U) The system.", "(S) Details."])[0] == S.SECRET)
check("a TOP SECRET banner", m(["TOP SECRET//SCI"])[0] == S.TS)
check("an authority block (two of its lines)", m(["Classified By: J. Smith", "Derived From: SCG 2020"])[0] == S.CONF)
check("portion marks with controls", m(["(S//NF) The orbit."])[0] == S.CONF)
check("classified portion marks beside (U) marks", m(["(U) Intro.", "(U) Scope.", "(C) The orbit."])[0] == S.CONF)
check("a CUI banner is CUI", m(["CUI", "The Offeror shall..."])[0] == S.CUI)
check("not counted: FAR paragraphs lettered (C)", m(["(a) Scope", " (C) The contractor shall"] * 6)[0] == -1)
check("not counted: a quote headed CONFIDENTIAL (a business marking)", m(["CONFIDENTIAL", "Quote 4471"])[0] == S.PROP)
check("not counted: a blank Classified By box", m(["Classified By: ________"])[0] == -1)
check("not counted: trade secret", m(["The trade secret clause applies."])[0] == -1)
# files
from sensfiles import docx


src = os.path.join(tmp, "incoming"); os.makedirs(src)
d_sec = docx(os.path.join(src, "Orbit annex.docx"), "The orbit is described here.", header="SECRET//NOFORN")
d_cui = docx(os.path.join(src, "Section L.docx"), "The Offeror shall describe its approach.", label="CUI")
d_conf = docx(os.path.join(src, "Quote.docx"), "Price list.", label="Confidential")
d_plain = docx(os.path.join(src, "SOW.docx"), "The contractor shall deliver a monthly report.")
p_sec = os.path.join(src, "Annex B.pdf"); pdfmini.write(p_sec, [["SECRET", "The Offeror shall support the mission.", "SECRET"]], size=9)
p_lab = os.path.join(src, "Annex C.pdf"); pdfmini.write(p_lab, [["The Offeror shall provide the plan."]], size=9)
with open(p_lab, "ab") as f:
    f.write(b"\n% <pdfx:Classification>Top Secret</pdfx:Classification>\n")
check("a banner in a Word header is found", S.of_document(d_sec)["level"] == S.SECRET, S.of_document(d_sec))
check("a Word sensitivity label (Purview) is read: CUI", S.of_document(d_cui)["level"] == S.CUI and S.of_document(d_cui)["label"] == "CUI")
check("a label called Confidential is Proprietary", S.of_document(d_conf)["level"] == S.PROP)
check("an unmarked file: not known", S.of_document(d_plain)["level"] == -1)
check("a banner on a PDF page", S.of_document(p_sec)["level"] == S.SECRET)
check("a label stored in a PDF", S.of_document(p_lab)["level"] == S.TS, S.of_document(p_lab))
# the spill guard: intake
data = os.path.join(tmp, "effort data"); cust = os.path.join(tmp, "Customer documents"); os.makedirs(cust)
lib = DV.Library(os.path.join(data, "documents")).load()
try:
    DI.plan(lib, [d_plain, d_sec]); stopped = None
except DI.Spill as ex:
    stopped = ex
check("intake: a document marked above CUI stops everything", stopped is not None and stopped.name == "Orbit annex.docx"
      and "SECRET" in stopped.text() and "no copy" in stopped.text())
check("... and nothing was copied", os.listdir(cust) == [])
plan = DI.plan(lib, [d_plain, d_cui, d_conf])
check("intake: each file keeps the level found", [e["sensitivity"] for e in plan] == [-1, S.CUI, S.PROP], [e["sensitivity"] for e in plan])
for e, ini in zip(plan, "ABC"):
    e["initial"] = ini
made = DI.apply(lib, plan, cust)
check("... and the library keeps it", sorted(d.get("sensitivity", -1) for d, _v in made) == [-1, S.PROP, S.CUI])
# Read RFP
try:
    CR.read_files([d_plain, p_sec], A.rfp_chunks); stopped = None
except S.Spill as ex:
    stopped = ex
check("Read RFP: a file marked above CUI stops the read", stopped is not None and stopped.name == "Annex B.pdf")
items, _h, srcs, _e = CR.read_files([d_plain], A.rfp_chunks)
check("... an unmarked one reads", len(srcs) == 1 and items)
# SCIF-ready reads it
secure.ACTIVE = True
try:
    lv = S.guard(d_sec); ok = True
except S.Spill:
    ok, lv = False, -1
check("SCIF-ready: the guard lets a marked document through (the system is accredited for it)", ok and lv == S.SECRET)
check("... and the mode is SCIF-ready whatever the settings say", WM.get({"work_mode": "connected"}) == WM.SECURED)
check("... and no training data, no bug reports", not secure.training_ok(S.GB) and not secure.feedback_ok())
secure.ACTIVE = False
check("a setting of Secured from before 2.97 reads as Offline", WM.get({"work_mode": "secured"}) == WM.OFFLINE)
# an effort's level
lp = os.path.join(tmp, "Kestrel", "Kestrel_Effort_List.xlsx"); os.makedirs(os.path.dirname(lp))
L = E.EffortList(lp, "Kestrel"); L.pending = True; L.save()
ed = W.data_dir_for(lp)
check("an effort with nothing declared and no documents: not known", S.effort_level(lp) == -1)
BR.set_identity(R.Record(ed), sensitivity="Not CUI")
check("declared Not CUI: General business", S.effort_level(lp) == S.GB)
lib2 = DV.Library(os.path.join(ed, "documents")).load()
pl = DI.plan(lib2, [d_cui]); pl[0]["initial"] = "L"; DI.apply(lib2, pl, "")
check("a CUI document raises it to CUI", S.effort_level(lp) == S.CUI)
# training data only for an effort at most CUI
CO.set_dir(os.path.join(tmp, "td"))
from PIL import Image
img = Image.new("RGB", (60, 20), "white")
secure.EFFORT_LEVEL = -1
A.TRAINING_APP = False
try:
    CO.save_sample(img, "x", "x", 0.5, "s", (0, 0, 1, 1)); kept = True
except PermissionError:
    kept = False
check("Stationkeeper keeps no training line for an effort of unknown sensitivity", not kept and not A.corrections_on())
secure.EFFORT_LEVEL = S.CUI
check("... and keeps one for a CUI effort", bool(CO.save_sample(img, "x", "x", 0.5, "s", (0, 0, 1, 1))) and A.corrections_on())
secure.EFFORT_LEVEL = S.SECRET
check("... never above CUI", not secure.training_ok() and not secure.feedback_ok())
secure.EFFORT_LEVEL = -1
# packs
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
out = os.path.join(tmp, "p.sktrain")
r = TP.build(out, cfg, app_version="2.97.0", acknowledged=True, matrices=[], words={"choices": {"IMS": "keep"}},
             sensitivity="CUI", everything=True)
man = json.loads(zipfile.ZipFile(out).read("manifest.json")) if r["path"] else {}
check("a training pack states its sensitivity and the rule", man.get("sensitivity") == "CUI" and "at most CUI" in man.get("sensitivity_rule", ""), man.get("sensitivity"))
check("Training: a CUI pack imports", TP.sensitivity_problem({"sensitivity": "CUI"}) == "")
check("... a Secret one never", "above CUI" in TP.sensitivity_problem({"sensitivity": "Secret"}))
check("... one of unknown sensitivity is refused", "not known" in TP.sensitivity_problem({"sensitivity": "Blue"}))
check("... one made before 2.97 only when confirmed", TP.sensitivity_problem({}) != "" and TP.sensitivity_problem({}, confirmed_old=True) == "")
secure.ACTIVE = True
try:
    TP.build(out + "2", cfg, acknowledged=True, matrices=[]); refused = False
except PermissionError:
    refused = True
secure.ACTIVE = False
check("SCIF-ready never builds a training pack", refused)
# which efforts go to training
from trainpack_ui import TrainPackMixin
reg = E.Registry(os.path.join(tmp, "efforts.json"))
def effort(name, sens):
    p = os.path.join(tmp, name, f"{name}_Effort_List.xlsx"); os.makedirs(os.path.dirname(p), exist_ok=True)
    Lx = E.EffortList(p, name); Lx.pending = True; Lx.save()
    if sens is not None:
        BR.set_identity(R.Record(W.data_dir_for(p)), sensitivity=sens)
    reg.put(name, path=p)
effort("Osprey", "CUI"); effort("Heron", None); effort("Falcon", "Proprietary")
class H(TrainPackMixin):
    def __init__(self):
        self.efforts, self.matrix = reg, None
h = H()
args = h.tp_args()
check("training leaves out efforts with no sensitivity set", sorted(h.tp_left_out) == ["Heron"], h.tp_left_out)
check("... and the pack says the highest level it holds", args["sensitivity"] == "CUI", args["sensitivity"])
# SCIF-ready seals
base, dat = os.path.join(tmp, "program"), os.path.join(tmp, "data")
for d in (os.path.join(base, "logs"), os.path.join(dat, "training_data", "images"), os.path.join(dat, "feedback", "reports")):
    os.makedirs(d); open(os.path.join(d, "x.txt"), "w").write("x")
check("not sealed: not SCIF-ready", not secure.scif(base, dat))
secure.seal(base, dat, who="tester")
check("sealed: the seal in the program folder and the data folder", os.path.isfile(os.path.join(base, secure.SEAL))
      and os.path.isfile(os.path.join(dat, secure.SEAL)) and secure.ACTIVE)
check("... the old logs, training data and bug reports are deleted", not os.path.exists(os.path.join(base, "logs"))
      and not os.path.exists(os.path.join(dat, "training_data")) and not os.path.exists(os.path.join(dat, "feedback")))
check("... logging stops", diag.OFF and diag.LOG_DIR is None and not diag.usage_on)
check("a fresh program over a sealed data folder is still SCIF-ready", secure.scif(os.path.join(tmp, "fresh"), dat))
check("... and so is a sealed program with a new data folder", secure.scif(base, os.path.join(tmp, "new data")))
secure.ACTIVE = False
shutil.rmtree(tmp, ignore_errors=True)
n = sum(checks)
print(f"TEST SENSITIVITY {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
