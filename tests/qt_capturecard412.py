"""4.12.0 offscreen: Shred's capture card (claude/stationkeeper-capture-cards-plan-4.12.md, part A). Capture > Contact
opens a card at the top of the piece pane; the name and e-mail come from the first piece; a phone picked on another
piece goes in with Take while the card stays open; Save files one contact and marks both pieces; Captured from this
piece lists it with Open and Take out; Open shows the filed contact to add a second phone and fix a value in place;
Take out takes what that piece gave; one card at a time (Cancel keeps the open one; Discard drops it); a Key date card
sets the effort's due date. Fictional (an Osprey Section L)."""
import os, sys, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["AH_TEST"] = "1"
os.environ["SK_SANDBOX_TEMP"] = "temp_qt"
tmp = tempfile.mkdtemp()
os.environ["SK_DATA_DIR"] = os.path.join(tmp, "Stationkeeper Data")
import app_gui as A
import effort as E, workspace as W, pdfmini
import contactcard as CC, effortrec as RR, excerpts as EX
from PySide6.QtWidgets import QApplication, QMessageBox
QMessageBox.information = staticmethod(lambda *a, **k: None)
from skqt import design as theme
from skqt.mainwin import MainWindow
from skqt import capturecard as CCARD, piececaptures as PC

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


cfg = os.path.join(tmp, "config"); os.makedirs(cfg)
EDIR = os.path.join(tmp, "Osprey"); os.makedirs(EDIR)
LINES = ["L.2 PROPOSAL SUBMISSION",
         "Proposals shall be submitted electronically no later than 2:00 p.m. Eastern Time on December 15, 2026.",
         "Questions shall be sent to the Contracting Officer, Sam Ortiz, at sam.ortiz@osprey.example.",
         "The Offeror shall describe its Integrated Master Schedule (IMS) approach.",
         "The Contracting Officer may also be reached by phone at (555) 010-3100.",
         "After hours the Contracting Officer answers at (555) 010-3199.",
         "The Government intends to award a single contract."]
PDF = os.path.join(tmp, "Section_L.pdf"); pdfmini.write(PDF, [LINES], size=9)
LIST = os.path.join(EDIR, "Osprey_Effort_List.xlsx")
L = E.EffortList(LIST, "Osprey"); L.pending = True; L.save()
E.Registry(os.path.join(cfg, "efforts.json")).put("Osprey", path=LIST)
app = QApplication([]); theme.apply(app)
w = MainWindow(app, cfg, A.APP_VERSION); w.resize(1500, 950); w.show()


def wait(cond, secs=60):
    t = time.time()
    while not cond() and time.time() - t < secs:
        app.processEvents(); time.sleep(0.02)
    return cond()


w.open_effort("Osprey")
OUT = os.path.join(EDIR, "Osprey_Compliance_Matrix.xlsx")
w.read_page.read([PDF], OUT)
check("extracted", wait(lambda: w.review is not None and not w.read_page.running()))
w.go("assign"); app.processEvents()
pg = w.assign_page
M = w.review.M
by = lambda s: next(it for it in M.items if s in it["text"])          # noqa: E731
rec = lambda: RR.Record(w.ws.root)                                       # noqa: E731


def pick(it, words):
    pg.select(it["id"]); app.processEvents()
    s = it["text"].index(words)
    pg.grab = {"iid": it["id"], "a": 0, "b": 0, "s": s, "e": s + len(words), "text": words}


co, ph, ph2, due = by("sent to the Contracting Officer"), by("010-3100"), by("010-3199"), by("Proposals shall be submitted")
check("on Shred", pg.focus == "shred")
pg.select(co["id"]); app.processEvents()
got = pg.do_capture("contact")
card = pg.capture_card
check("Capture > Contact opens the card on the pane, not a dialog", got is None and card is not None and card.kind == "contact"
      and pg.right.widget(0) is pg.capture_holder)
v = card.values()
check("the first piece fills name and e-mail", v["name"] == "Sam Ortiz" and v["email"][0]["value"] == "sam.ortiz@osprey.example", v)
pick(ph, "(555) 010-3100")
check("the card stays open while another piece is picked", pg.capture_card is card and card.isVisibleTo(w))
check("Take puts the picked phone in", card.take("phone") and card.values()["phone"][0]["value"] == "(555) 010-3100")
card.rows["phone"][0][0].setCurrentText("Office")
check("two pieces picked", len(card.picks) == 2 and "2 pieces" in card.picked.text())
cid = card.save()
c = rec().contact(cid)
check("Save files one contact", c is not None and c["name"] == "Sam Ortiz" and c["phone"] == "(555) 010-3100"
      and CC.values(c, "phone")[0]["label"] == "Office" and CC.values(c, "phone")[0]["source"]["sid"] == ph["id"])
check("the card closes", pg.capture_card is None and pg.capture_holder is None)
xs = [x for x in EX.excerpts(rec()) if x["bin"] == "contact"]
check("both pieces carry the capture", {p["sid"] for x in xs for p in x["parts"]} == {co["id"], ph["id"]}
      and all(x["refs"] == [cid] for x in xs))
pg.clear_grab(); pg.select(ph["id"]); app.processEvents()
check("Captured from this piece lists the contact", len(pg.capture_lines) == 1 and "Sam Ortiz" in pg.capture_lines[0][1].text())
x = EX.of_sentence(rec(), ph["id"])[0]
card = PC.open_capture(pg, x)
check("Open shows the filed contact", card is not None and card.cid() == cid and card.values()["name"] == "Sam Ortiz"
      and len(card.values()["phone"]) == 1)
pick(ph2, "(555) 010-3199")
card.take("phone")
card.rows["phone"][1][0].setCurrentText("Mobile")
card.rows["phone"][0][1].setText("(555) 010-3101"); card._set("phone", 0, value="(555) 010-3101")
card.save()
c = rec().contact(cid)
check("a second phone added to the same contact, and a value fixed in place",
      [(v["label"], v["value"]) for v in CC.values(c, "phone")] == [("Office", "(555) 010-3101"), ("Mobile", "(555) 010-3199")],
      CC.values(c, "phone"))
check("still one contact", len(rec().contacts()) == 1)
pg.clear_grab(); pg.select(ph2["id"]); app.processEvents()
x2 = EX.of_sentence(rec(), ph2["id"])[0]
PC.take_out(pg, x2, ph2["id"])
check("Take out takes what that piece gave", [v["value"] for v in CC.values(rec().contact(cid), "phone")] == ["(555) 010-3101"]
      and not EX.of_sentence(rec(), ph2["id"]))
# one card at a time
pg.select(co["id"]); app.processEvents()
pg.do_capture("contact")
first = pg.capture_card
check("a new card from a piece is changed (it guessed)", first.dirty)
check("Cancel keeps the open card", CCARD.open_card(pg, "keydate", ask="cancel") is None and pg.capture_card is first)
pg.select(due["id"]); app.processEvents()
kd = CCARD.open_card(pg, "keydate", ask="drop")
check("Discard drops it and opens the next", kd is not None and pg.capture_card is kd and len(rec().contacts()) == 1)
kv = kd.values()
check("the Key date card guesses from the piece", kv["date"] == "2026-12-15" and kv["kind"] == "Proposal due", kv)
kd.save()
check("Save sets the effort's due date", (rec().data.get("due") or "").startswith("2026-12-15"), rec().data.get("due"))
check("the due piece carries the capture", any(x["bin"] == "keydate" for x in EX.of_sentence(rec(), due["id"])))
# Effort detail card, then leaving Shred drops a card
pg.select(by("single contract")["id"]); app.processEvents()
dc = CCARD.open_card(pg, "detail")
dc.edits["label"].setCurrentText("Contract type"); dc.edits["value"].setText("Single award")
check("the Effort detail card has Detail and Value", set(dc.values()) == {"label", "value"})
w.go("place"); app.processEvents()
check("leaving Shred closes the card", pg.capture_card is None)
print(f"{sum(checks)}/{len(checks)} passed")
sys.exit(0 if all(checks) else 1)
