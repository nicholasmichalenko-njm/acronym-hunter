"""2.42.0 Submission > Impact on screen: a new amendment opens its impact review; the band (document, version, file,
fingerprint, text counts); six cards (requirements, deliverables, compliance, structure, acronyms, keywords) with what
changed; add the newly named attachment as a deliverable; add a new customer phrase as a keyword; update the matrix
with the new version (decisions kept, new sentences marked); who it touches; the Word report; author briefs (2.43.0: one per person, copy, Word); Mark impact reviewed
(the version and its requirement changes, logged in the timeline); Effort home's Next line; the Impact review button
on a version in Documents; the version picker."""
import os, sys, tempfile, shutil, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, effort as E, compliance as C, deliverables as D
from tkinter import messagebox
from test_docversions import amend
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
messagebox.showinfo = lambda *a, **k: None
messagebox.askyesno = lambda *a, **k: True
messagebox.showwarning = lambda *a, **k: None
messagebox.showerror = lambda *a, **k: None
LIST = os.path.join(tmp, "Kestrel", "Kestrel_Effort_List.xlsx")
CDIR = os.path.join(tmp, "Kestrel", "Customer documents"); os.makedirs(CDIR)
RFP = os.path.join(A.BASE_DIR, "test_samples", "rfp", "Kestrel_RFP_Sections_C_L_M.docx")
BASE = amend(RFP, os.path.join(CDIR, "Kestrel_RFP.docx"), [("Proposals shall not exceed 50 pages", "Volume I shall not exceed 50 pages")])
INBOX = os.path.join(tmp, "inbox"); os.makedirs(INBOX)
AMD = amend(BASE, os.path.join(INBOX, "Kestrel_RFP_Amd1.docx"), [
    ("December 15, 2026", "December 22, 2026"), ("exceed 50 pages", "exceed 40 pages"),
    ("L.4.2 Management Approach", "L.4.2 Management and Schedule Approach"),
    ("an Integrated Master Schedule (IMS) as Attachment J-2.",
     "an Integrated Master Schedule (IMS) as Attachment J-2. The Offeror shall provide a Small Business Participation Plan (SBPP) "
     "as Attachment J-7. The SBPP shall describe verification by analysis and test. Verification by analysis and test applies to "
     "every TRL claim."),
    ("The Contractor should use flight-proven components where practical.", "")])
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def texts_of(w):
    out = []
    for c in w.winfo_children():
        try:
            t = c.cget("text")
            if isinstance(t, str):
                out.append(t)
        except Exception:
            pass
        out += texts_of(c)
    return out


app = A.AcronymAppGUI()
app.geometry("1500x940+0+0")


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST, customer_dir=CDIR)
    app.open_effort("Kestrel"); app.update()
    app.shell_go("submission", "impact"); app.update()
    check("with no new version yet, Impact says what will show there", app.imp_r is None and
          any("No new versions yet" in t for t in texts_of(app.imp_scroll)))
    w = app.sub_add_dialog(app.sub_unadded()); w.update(); w._api["add"](); app.update()
    lib = app.doclib()
    rfp = lib.docs[0]
    # the matrix, read from the Original; two sentences placed with owners
    mpath = os.path.join(tmp, "Kestrel", "Kestrel_Matrix.xlsx")
    M = C.Matrix(mpath, "Kestrel")
    M.items = C.extract([("Kestrel_RFP.docx", A.typed_chunks(BASE))], [])
    M.sources = [["Kestrel_RFP.docx", rfp["versions"][0]["sha256"], "2026-10-26", BASE]]
    M.outline = C.parse_outline("1.1 Management Approach\n1.2 Schedule")
    for it in M.items:
        if "Integrated" in it["text"] or "flight-proven" in it["text"]:
            C.assign_requirement(M.items, [it], "1.1 Management Approach")
            it["owner"] = "J. Smith" if "flight" in it["text"] else "R. Diaz"
    M.save()
    app.ws.set("compliance_path", mpath)
    app.open_compliance(show=False); app.update()
    app._c_load(mpath, quiet=True)
    vol = os.path.join(tmp, "Kestrel", "Vol_1.docx")
    with zipfile.ZipFile(vol, "w") as z:
        z.writestr("word/document.xml", "<w:document/>")
        z.writestr("docProps/app.xml", "<Properties><Pages>45</Pages></Properties>")
    rec = app.effrec()
    D.add(rec, "Volume I Technical", kind="Volume", owner="B. Chen", file=vol)
    app.shell_go("home"); app.update()
    # the amendment arrives
    w = app.sub_add_dialog([AMD]); w.update(); w._api["add"](); app.update()
    r = app.imp_r
    check("adding the amendment opens its impact review", app.shell_step == "impact" and r is not None and r["version"] == "Amendment 1"
          and app.imp_title.cget("text") == "Amendment 1 of Kestrel RFP: what it touched", (app.shell_step, app.imp_title.cget("text")))
    pills = [x.cget("text").split("  ")[0] for x in app.strip_pills.winfo_children()]
    check("Impact is a Submission step after Documents", "4 Impact" in pills, pills)
    band = texts_of(app.imp_scroll)
    check("the band: document, version and the one before, file, fingerprint, text counts",
          "Amendment 1 (was Original)" in band and "Kestrel_RFP_Amd1.docx" in band and "2 changed, 3 added, 1 removed" in band
          and "FINGERPRINT (SHA-256)" in band, band[:14])
    cards = app.imp_cards
    check("six cards", list(cards) == ["requirements", "deliverables", "compliance", "structure", "acronyms", "keywords"], list(cards))
    req = " | ".join(cards["requirements"]._lines)
    check("requirements: the due date and the page limit, was and now; the new attachment",
          "Due, Proposal\nWas December 15, 2026" in req and "Page limit, Volume I\nWas 50 pages, now 40 pages" in req
          and "Deliverable, Attachment J-7\nNew:" in req, req[:300])
    dl = " | ".join(cards["deliverables"]._lines)
    check("deliverables: the volume's new limit with our page count; the new attachment suggested",
          "Volume I Technical, owner B. Chen" in dl and "Page limit was 50 pages, now 40 pages; our file is 45 pages" in dl
          and "New: Attachment J-7" in dl, dl)
    cp = " | ".join(cards["compliance"]._lines)
    check("compliance: changes in assigned sections, new sentences not assigned, the removed one with its section and owner",
          "3 new sentence(s), 3 not assigned yet" in cp and "Removed:" in cp and "1.1 Management Approach is no longer asked for (owner J. Smith)" in cp, cp)
    st = " | ".join(cards["structure"]._lines)
    check("structure: the renamed heading and our section named like it",
          '"Management Approach" is now "Management and Schedule Approach". Rename our section 1.1 Management Approach to match?' in st, st)
    ac = " | ".join(cards["acronyms"]._lines)
    check("acronyms: the new terms", "SBPP" in ac and "TRL" in ac, ac)
    kw = " | ".join(cards["keywords"]._lines)
    check("keywords: the new customer phrase", "verification by analysis and test" in kw, kw)
    check("who it touches: the people the author briefs go to", "J. Smith (1 section)" in app.imp_people.cget("text")
          and "B. Chen (1 deliverable)" in app.imp_people.cget("text") and "R. Diaz (1 section)" in app.imp_people.cget("text"), app.imp_people.cget("text"))
    # actions
    key = r["suggested"][0]["key"]
    did = app.impact_add_deliverable(key); app.update()
    check("Add as a deliverable adds it and the card updates", did and D.get(rec, did)["name"] == "Attachment J-7"
          and not app.imp_r["suggested"], app.imp_r["suggested"])
    res = app.impact_add_keyword("verification by analysis and test"); app.update()
    kwrow = next((k for k in app.effort.keywords if k["Keyword"] == "verification by analysis and test"), None)
    check("Add puts the phrase in the keyword list as Proposed, with where it came from", res == "added" and kwrow and kwrow["Status"] == "Proposed"
          and "Amendment 1" in kwrow["Source"] and not app.imp_r["keywords"], (res, kwrow))
    paths = app.impact_matrix_paths()
    check("the matrix was read from the Original: Update the matrix reads the amendment in its place",
          paths == [lib.docs[0]["versions"][1]["path"]], paths)
    done = {}
    app.compliance_reread_paths(paths, after=lambda n, g: done.update(n=n, g=g))
    for _ in range(100):
        app.update(); app.after(50)
        if done:
            break
        import time; time.sleep(0.05)
    kept = next((it for it in app.matrix.items if "Integrated Master Schedule" in it["text"]), None)
    check("the matrix update keeps decisions on unchanged sentences and marks the new ones", done and done["n"] >= 3
          and kept and kept["decision"] == "Keep" and kept["map"] == "1.1 Management Approach", (done, kept and kept["decision"]))
    app.impact_refresh(); app.update()
    check("after the update the matrix holds the new version: no update offered again", app.impact_matrix_paths() is None)
    out = app.impact_export(os.path.join(tmp, "impact.docx"))
    x = zipfile.ZipFile(out).read("word/document.xml").decode("utf-8")
    check("the Word report", "IMPACT REVIEW" in x and "Amendment 1 of Kestrel RFP" in x and "Who it touches" in x)
    # the due date (2.43.0): the version moved it; Effort details still hold the old one
    rec.set_due("2026-12-15T14:00", "MT")
    app.impact_refresh(); app.update()
    req2 = " | ".join(cards["requirements"]._lines) if False else " | ".join(app.imp_cards["requirements"]._lines)
    check("the old due date in Effort details is pointed out, with the new one offered", "Effort details still hold the old due date" in req2
          and app.impact_due_text().startswith("Dec 22, 2026"), (req2[-120:], app.impact_due_text()))
    check("Use the new due date: Effort details and the countdown follow", app.impact_use_due() and rec.data["due"] == "2026-12-22T14:00"
          and "Effort details still hold" not in " | ".join(app.imp_cards["requirements"]._lines), rec.data["due"])
    # author briefs (2.43.0)
    check("the briefs button says how many people", app.imp_brief.cget("text").startswith("Author briefs (3 people)"), app.imp_brief.cget("text"))
    bw = app.impact_briefs_dialog(); bw.update()
    bs = bw._api["briefs"]
    check("a brief per person it touches, and one for the team", list(bs) == ["J. Smith", "R. Diaz", "B. Chen", "Everyone"], list(bs))
    shown = bw._api["text"].get("1.0", "end")
    check("the first brief shows: subject, the person's section, the removed sentence quoted, the due date",
          shown.startswith("Subject: Kestrel RFP, Amendment 1: what changed for J. Smith") and "YOUR SECTIONS\n1.1 Management Approach" in shown
          and "flight-proven components" in shown and "Proposal due " in shown, shown[:400])
    bw._api["show"]("B. Chen"); bw.update()
    shown = bw._api["text"].get("1.0", "end")
    check("another person's brief: their deliverable and its new limit", "YOUR DELIVERABLES\n- Volume I Technical: Page limit was 50 pages, now 40 pages" in shown, shown[:400])
    copied = bw._api["copy"](); app.update()
    check("Copy puts the brief on the clipboard", app.clipboard_get() == copied and copied.startswith("Subject: Kestrel RFP, Amendment 1: what changed for B. Chen"))
    bp = bw._api["save"](os.path.join(tmp, "briefs.docx")); app.update()
    bx = zipfile.ZipFile(bp).read("word/document.xml").decode("utf-8")
    check("Save all as Word: one brief per page, logged in the timeline", bx.count('w:type="page"') == 3 and "AUTHOR BRIEF" in bx
          and any(e["text"].startswith("Author briefs for Amendment 1 of Kestrel RFP: J. Smith, R. Diaz, B. Chen") for e in rec.events()[:3]))
    bw.destroy(); app.update()
    # Effort home says what is next
    app.shell_go("home"); app.update(); app.shell_overview_refresh()
    check("Effort home: Next, review what the amendment touched", app.ov_next.cget("text").startswith("Next: Customer Documents, review what Amendment 1")
          and app._ov_target == ("submission", "impact"), app.ov_next.cget("text"))
    app.shell_go(*app._ov_target); app.update()
    reg = app.subreg()
    before = sum(1 for x in reg.rows() if x["to_review"])
    ok = app.impact_mark_reviewed(); app.update()
    after = sum(1 for x in reg.rows() if x["to_review"])
    ev = " | ".join(e["text"] for e in rec.events()[:4])
    check("Mark impact reviewed: the version and its requirement changes, logged", ok and before >= 2 and after == 0
          and lib.docs[0]["versions"][1]["reviewed"] and "Impact of Amendment 1 of Kestrel RFP reviewed" in ev, (before, after, ev[:200]))
    check("the button shows it is done", app.imp_done.cget("state") == "disabled" and app.imp_done.cget("text").startswith("Impact reviewed"))
    app.shell_overview_refresh()
    check("Effort home moves on", not app.ov_next.cget("text").startswith("Next: Customer Documents, review"), app.ov_next.cget("text"))
    # Documents: the Impact review button; the picker
    app.shell_go("submission", "documents"); app.sub_show(rfp["id"]); app.update()
    btn = next((b for b in app.sub_detail.winfo_children()[1].winfo_children()[-1].winfo_children() if getattr(b, "cget", None)
                and b.cget("text") == "Impact review"), None) if len(app.sub_detail.winfo_children()) > 1 else None
    check("a version in Documents has an Impact review button", btn is not None)
    if btn is not None:
        btn.invoke(); app.update()
    check("it opens that version's impact", app.shell_step == "impact" and app.imp_vid == rfp["versions"][1]["id"])
    check("the picker lists the versions to review", any("Kestrel RFP: Amendment 1" in k for k in app._imp_map), list(app._imp_map))
    n = sum(checks)
    print(f"GUI IMPACT {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
