"""3.68.0 without a screen: customer forms as locked parts (the part names its form and marking; its sections found and
fingerprinted; Fix a Copy puts a copy back when a fix changes it; Apply in Word leaves its paragraphs alone; Final Check
finds its pages by their words, leaves them out of the count when it does not count, checks its marking and does not ask
the volume's page marking of it); save-to (this effort, its effort type, every effort; a shared plan followed until the
effort sets its own; what a broader save would change; the plans Final Check reads); and the Production Standards
nothing-lost report (each section's status, values set on this PC that have no other editor, the places that still open
it). Fictional content (Kestrel)."""
import json, os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import formcheck as FM, finalcheck as FC, partplan as PP, prodfix as PF, readback as RB, wordlab as WL
import prodrules as PRL, prodstdreport as PSR

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
NSD = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')
FORM = ("Kestrel Past Performance Questionnaire. The respondent shall rate the offeror on quality of the ground "
        "segment, schedule adherence, cost control and management responsiveness for each contract listed below.")


def sect(fmt=None, start=None):
    pn = ("<w:pgNumType" + (f' w:fmt="{fmt}"' if fmt else "") + (f' w:start="{start}"' if start else "") + "/>") if fmt or start else ""
    return f'<w:sectPr><w:footerReference w:type="default" r:id="rIdF1"/><w:pgSz w:w="12240" w:h="15840"/>{pn}</w:sectPr>'


def para(text, sp=""):
    return f'<w:p><w:pPr>{sp}</w:pPr><w:r><w:t>{text}</w:t></w:r></w:p>'


def volume(path, form_text=FORM):
    body = (para("1 Introduction. We will utilize the Kestrel bus.", sect("decimal", 1))
            + para(form_text) + para("We will utilize the questionnaire as issued.", sect(None, 1))    # the customer form
            + '<w:p><w:r><w:t>Appendix A</w:t></w:r></w:p>' + sect("lowerLetter", 1))
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("word/document.xml", f'<w:document {NSD}><w:body>{body}</w:body></w:document>')
        z.writestr("word/_rels/document.xml.rels", '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rIdF1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="footer1.xml"/></Relationships>')
        z.writestr("word/footer1.xml", f'<w:ftr {NSD}><w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText>PAGE</w:instrText></w:r>'
                   '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p></w:ftr>')
    return path


vol = volume(os.path.join(tmp, "Kestrel_Volume_II.docx"))
form_doc = os.path.join(tmp, "Kestrel PPQ.docx")
import docxw
d = docxw.Doc(); d.para(FORM); d.save(form_doc)
parts = [PP.part("Response", "Body", fmt="1", restart=True),
         PP.part("Past performance questionnaire", "Customer form", fmt="1", restart=True, header="Its own (customer form)",
                 counts="Does not count", form=form_doc, marking="Kestrel Source Selection"),
         PP.part("Appendices", "Appendix", fmt="A-1", restart=True)]
# ---- the part
check("a Customer form part is locked and names its form and marking", PP.locked(parts[1]) and not PP.locked(parts[0])
      and parts[1]["form"] == form_doc and parts[1]["marking"] == "Kestrel Source Selection")
check("its line says it is kept as it is", "the customer's form, kept as it is, marked 'Kestrel Source Selection'" in PP.says(parts[1]))


class Rec:
    def __init__(self):
        self.data, self.logs = {}, []

    def log(self, *a, **k):
        self.logs.append(a)

    def save(self):
        pass


rec = Rec()
PP.set_plan(rec, "Volume II Past Performance", parts)
fr = PP.final_check_rules(rec, "Volume II Past Performance")
check("Final Check reads the form with its file, marking and count", fr["forms"] == [{"name": "Past performance questionnaire", "form": form_doc,
      "marking": "Kestrel Source Selection", "counts": False}])
check("the plan is found from the file's name", PP.parts_for_file(rec.data["part_plans"], vol)[0] == "Volume II Past Performance")
# ---- its sections, fingerprinted
dig = RB.locked_digest(vol, parts)
check("the form's sections are fingerprinted (one locked part)", list(dig) == [parts[1]["id"]])
check("its paragraphs are known (the form text and its own line)", RB.locked_paragraphs(vol, parts) == {1, 2})
# ---- Fix a Copy: a fix that changes the form is undone
cp = os.path.join(tmp, "copy.docx")
volume(cp)
keep = PF._locked_before(cp, parts)
volume(cp, FORM.replace("respondent shall", "respondent will"))           # a fix that rewrote the form
rec2 = {"step": "Fix", "changed": True}
undone = PF._locked_after(cp, parts, keep, rec2)
check("a fix that changes the customer form is refused and the copy put back", undone and rec2["changed"] is False
      and "customer form" in rec2["refused"] and open(cp, "rb").read() == keep["bytes"])
volume(cp); keep = PF._locked_before(cp, parts)
with zipfile.ZipFile(cp) as z:
    xml = z.read("word/document.xml").decode().replace("1 Introduction. We will", "1 Introduction. We shall")
rewrite = os.path.join(tmp, "copy2.docx")
with zipfile.ZipFile(cp) as zi, zipfile.ZipFile(rewrite, "w") as zo:
    for n in zi.namelist():
        zo.writestr(n, xml if n == "word/document.xml" else zi.read(n))
os.replace(rewrite, cp)
rec3 = {"step": "Fix", "changed": True}
check("a fix outside the form stands", PF._locked_after(cp, parts, keep, rec3) is False and rec3["changed"] is True)
check("no plan or no form: nothing is held back", PF._locked_before(cp, None) is None and PF._locked_before(cp, [parts[0]]) is None)
# ---- Apply in Word: the form is left alone
items = [{"Phrase": "utiliz*", "Level": "Avoid", "Use instead": "use", "Why": "Plain language"}]
ch, held = WL.find_in_draft(vol, items, parts)
check("Apply in Word leaves the customer form's paragraphs alone", [c["para"] for c in ch] == [0] and held == 1, (ch, held))
check("... and without a plan finds every phrase", len(WL.find_in_draft(vol, items)[0]) == 2)
# ---- Final Check: the form's pages
words = FM.form_words(form_doc)
filler = "The offeror describes the Kestrel ground segment approach with enough words for a full page here today."
texts = ["Kestrel Volume II cover " + filler, "1 Introduction " + filler + " Use or disclosure of data contained on this sheet",
         FORM + " Kestrel Source Selection", FORM, "Appendix A " + filler + " Use or disclosure of data contained on this sheet"]
check("the form's pages found by their words", FM.pages_of(texts, words) == [3, 4], FM.pages_of(texts, words))
lines, pg = FM.check(texts, fr["forms"], FC._line, FC.PASS, FC.FAIL, FC.HUMAN)
st = {l["check"]: l for l in lines}
check("placed on pages 3 to 4, left out of the count", st["Past performance questionnaire placed"]["status"] == FC.PASS
      and "pages 3 to 4" in st["Past performance questionnaire placed"]["detail"] and pg["drop"] == [3, 4])
check("its marking is missing on page 4", st["Past performance questionnaire marking"]["status"] == FC.FAIL
      and "page 4" in st["Past performance questionnaire marking"]["detail"])
n, out = FC.count_pages(texts, [], None, 1, pg["drop"])
check("the count leaves the form out", n == 3 and out["forms"] == [3, 4])
gone = FM.check(texts[:2], fr["forms"], FC._line, FC.PASS, FC.FAIL, HUMAN := FC.HUMAN)[0]
check("a form not in the PDF fails", gone[0]["status"] == FC.FAIL and "not in the PDF" in gone[0]["detail"])
nofile = FM.check(texts, [dict(fr["forms"][0], form="")], FC._line, FC.PASS, FC.FAIL, FC.HUMAN)[0]
check("a form with no file set is checked by hand", nofile[0]["status"] == FC.HUMAN)
# ---- save-to
cfg = os.path.join(tmp, "cfg"); os.makedirs(cfg)
data = PRL.load(cfg)
import effortprofiles as EP
prof = EP.profiles(data)[0]
eid, pid = prof["eid"], prof["pid"]
rec = Rec()
PP.save_to(cfg, rec, "Volume II Past Performance", parts, "type", eid, pid)
check("save for the effort type: kept by the volume profile; this effort follows it", PP.shared_plan(cfg, eid, pid)[1]["kind"] == "Customer form"
      and not PP.own(rec, "Volume II Past Performance") and PP.shared_from(cfg, eid, pid) == "type")
check("an effort following it sees the shared plan", [p["name"] for p in PP.plan_of(rec, "Volume II Past Performance", PP.shared_plan(cfg, eid, pid))]
      == ["Response", "Past performance questionnaire", "Appendices"])
PP.save_to(cfg, rec, "Volume II Past Performance", parts[:1], "team", eid, "other-profile")
check("save for every effort: kept for that profile across effort types", PP.shared_plan(cfg, "another-type", "other-profile")[0]["name"] == "Response"
      and PP.shared_from(cfg, "another-type", "other-profile") == "team")
PP.save_to(cfg, rec, "Volume II Past Performance", parts[:2], "effort", eid, pid)
check("save for this effort only: its own plan, the shared one unchanged", PP.own(rec, "Volume II Past Performance")
      and len(PP.shared_plan(cfg, eid, pid)) == 3)
eff = [{"name": "Kestrel", "eid": eid, "own": ["Volume II Past Performance"]}, {"name": "Osprey", "eid": eid, "own": []},
       {"name": "Harrier", "eid": "other", "own": []}]
check("what a broader save changes: efforts that follow it, and those that keep their own",
      PP.impact(eff, "type", eid) == {"efforts": 2, "keep": 1} and PP.impact(eff, "team") == {"efforts": 3, "keep": 1}
      and PP.impact(eff, "effort") == {"efforts": 0, "keep": 0})
rec4 = Rec()
eff_plans = PP.effective_plans(cfg, rec4, eid, data)
check("the plans an effort uses: the shared plan by each volume its profile makes", all(eff_plans[v][1]["kind"] == "Customer form" for v in prof["volumes"]))
rec4.data["part_plans"] = {prof["volumes"][0]: parts[:1]}
check("... with the effort's own plan over it", len(PP.effective_plans(cfg, rec4, eid, data)[prof["volumes"][0]]) == 1)
check("no shared file: only the effort's own", PP.effective_plans(os.path.join(tmp, "none"), rec4, eid, data) == rec4.data["part_plans"])
# ---- the nothing-lost report
rep = PSR.report(cfg, data)
keys = {r["key"]: r for r in rep["rows"]}
check("every Production Standards section is in the report", len(rep["rows"]) == 27 and all(r["where"] for r in rep["rows"]))
check("sections with no other editor are named", {k for k, r in keys.items() if r["status"] == PSR.ONLY} == {"content_map", "styles", "fillins", "graphics", "office"})
check("nothing set on a fresh PC: no values at risk; still not ready", rep["at_risk"] == 0 and not rep["ready"] and rep["verdict"].startswith("Not yet"))
d2 = PRL.load(cfg)
d2["company"].setdefault("graphics", {})["min_ppi"] = 299
d2["company"].setdefault("style_defs", {})["Kestrel Callout"] = {"font": "Arial", "size": 10}
rep2 = PSR.report(cfg, d2)
k2 = {r["key"]: r for r in rep2["rows"]}
check("a value set here with no other editor is at risk; one with a new home is not", k2["graphics"]["at_risk"]
      and any("Global standard" == ln for ln, _w in k2["graphics"]["values"]) and k2["styledefs"]["at_risk"] and rep2["at_risk"] == 2, rep2["at_risk"])
check("the places that still open Production Standards are listed", len(rep["links"]) == 6 and rep["links"][0][0].startswith("Setup page"))

print(f"STUDIO 368 {'OK' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
if __name__ == "__main__":
    sys.exit(0 if all(checks) else 1)
