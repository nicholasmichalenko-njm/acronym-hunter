"""3.87.0 Section designs: the shelves; a Word file brought onto a shelf (copied, never changed) with what fills it set
once per styled paragraph; the text other pages read (STYLEREF sources) and the quiet check (a source missing or in a
text box); a file with several Word sections split into one file each; a design filled for an effort (mapped paragraphs
take their values, the sample table row repeats once per entry, fields kept and updated on open); replacing a design
keeps its map; Setup's pick per section, with None only where a section is optional. Fictional content (Kestrel)."""
import hashlib, json, os, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ.setdefault("AH_TEST", "1")
import sectiondesigns as SDZ

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


tmp = tempfile.mkdtemp()
WNS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def style(sid, name):
    return f'<w:style w:type="paragraph" w:styleId="{sid}"><w:name w:val="{name}"/></w:style>'


STY = (f'<w:styles {WNS}>' + style("Normal", "Normal") + style("AACoverTitle", "AA Cover Title") + style("AAVolumeName", "AA Volume Name")
       + style("AAANumber", "AA A Number") + '</w:styles>')


def p(t, sid="", sect=""):
    ps = f'<w:pPr>{f"<w:pStyle w:val=\'{sid}\'/>" if sid else ""}{sect}</w:pPr>' if (sid or sect) else ""
    return f'<w:p>{ps}<w:r><w:t xml:space="preserve">{t}</w:t></w:r></w:p>'


def cell(t):
    return f'<w:tc>{p(t)}</w:tc>'


def make(path, body, footer_fields=("STYLEREF \"AA Volume Name\"",)):
    foot = f'<w:ftr {WNS}>' + "".join(f'<w:p><w:fldSimple w:instr=" {f.replace(chr(34), '&quot;')} "><w:r><w:t>x</w:t></w:r></w:fldSimple></w:p>' for f in footer_fields) + '</w:ftr>'
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>')
        z.writestr("word/document.xml", f'<w:document {WNS}><w:body>{body}<w:sectPr/></w:body></w:document>')
        z.writestr("word/styles.xml", STY)
        z.writestr("word/footer1.xml", foot)
        z.writestr("word/settings.xml", f'<w:settings {WNS}/>')
    return path


cover = make(os.path.join(tmp, "Kestrel Cover.docx"),
             p("Proposal Title Here", "AACoverTitle") + p("Volume Name Here", "AAVolumeName") + p("Prepared for the Program Office")
             + p("A-000", "AAANumber"))
acr = make(os.path.join(tmp, "Kestrel Acronyms.docx"),
           p("Acronyms and Abbreviations", "AACoverTitle")
           + f'<w:tbl><w:tr>{cell("Acronym")}{cell("Meaning")}</w:tr><w:tr>{cell("XXX")}{cell("Sample meaning")}</w:tr></w:tbl>',
           footer_fields=('STYLEREF "AA A Number"', "PAGE"))
before = hashlib.sha256(open(cover, "rb").read()).hexdigest()

info = SDZ.read(cover)
check("seven shelves", SDZ.SHELVES == ("cui", "cover", "title", "toc", "acronyms", "units", "back")
      and SDZ.SHELF_NAME["acronyms"] == "Acronyms and Abbreviations")
check("each paragraph with its style", [(x["style"], x["text"]) for x in info["paragraphs"]][:2] ==
      [("AA Cover Title", "Proposal Title Here"), ("AA Volume Name", "Volume Name Here")], info["paragraphs"])
check("the text other pages read: the footer's STYLEREF source", info["sources"] == ["AA Volume Name"]
      and SDZ.other_pages(cover)[0]["where"] == "Volume Name Here")
check("the check stays quiet on a good design", SDZ.check(cover) == [])
check("... names a source no paragraph carries", any("AA A Number" in x for x in SDZ.check(acr)), SDZ.check(acr))
tb = make(os.path.join(tmp, "Kestrel Cover TB.docx"),
          '<w:p><w:r><w:pict><w:txbxContent>' + p("Volume Name Here", "AAVolumeName") + '</w:txbxContent></w:pict></w:r></w:p>')
check("... and a source in a text box", any("text box" in x for x in SDZ.check(tb)), SDZ.check(tb))

cfg = os.path.join(tmp, "cfg")
x = SDZ.add(cfg, "cover", cover, "Kestrel cover, blue")
check("Bring in from Word: on its shelf, a copy", x["shelf"] == "cover" and os.path.isfile(SDZ.path_of(cfg, x))
      and hashlib.sha256(open(cover, "rb").read()).hexdigest() == before)
check("what fills it: one row per styled paragraph; Normal waits", x["map"] == {"0": "aa_cover_title", "1": "aa_volume_name", "3": "aa_a_number"}, x["map"])
check("the shelf lists it", [d["name"] for d in SDZ.designs(cfg, "cover")] == ["Kestrel cover, blue"] and SDZ.designs(cfg, "title") == [])
SDZ.set_map(cfg, x["id"], {"0": "title", "1": "volume_name", "2": "", "3": "a_number"})
x = SDZ.get(cfg, x["id"])
out = SDZ.fill(SDZ.path_of(cfg, x), x["map"], {"title": "Kestrel Ground Segment Sustainment", "volume_name": "Volume I Technical",
                                                 "a_number": "A-1"}, os.path.join(tmp, "filled", "cover.docx"))
got = SDZ.read(out)
check("filled: each mapped paragraph shows its value, the rest as written",
      [p_["text"] for p_ in got["paragraphs"]] == ["Kestrel Ground Segment Sustainment", "Volume I Technical",
                                                    "Prepared for the Program Office", "A-1"], got["paragraphs"])
with zipfile.ZipFile(out) as z:
    settings = z.read("word/settings.xml").decode(); foot = z.read("word/footer1.xml").decode()
check("fields kept as written; Word updates them on open", 'STYLEREF &quot;AA Volume Name&quot;' in foot and "updateFields" in settings)
a = SDZ.add(cfg, "acronyms", acr)
outa = SDZ.fill(SDZ.path_of(cfg, a), a["map"], {}, os.path.join(tmp, "filled", "acr.docx"),
                rows=[["KSF", "Kestrel Support Facility"], ["TT&C", "Tracking, telemetry and command"], ["GSE", "Ground support equipment"]])
t = SDZ.read(outa)["tables"][0]
check("the sample row repeats once per entry, the header row kept", t["rows"] == 4 and t["header"] == ["Acronym", "Meaning"]
      and t["sample"] == ["KSF", "Kestrel Support Facility"], t)
# replace keeps the map
cover2 = make(os.path.join(tmp, "Kestrel Cover v2.docx"),
              p("Proposal Title Here", "AACoverTitle") + p("Volume Name Here", "AAVolumeName") + p("Prepared for the Program Office")
              + p("A-000", "AAANumber") + p("Draft date", "AACoverTitle"))
y = SDZ.replace(cfg, x["id"], cover2)
check("an updated file replaces it; the map keeps its rows and adds the new one", y["map"]["0"] == "title" and y["map"]["2"] == ""
      and y["map"]["4"] == "aa_cover_title", y["map"])
# split
two = make(os.path.join(tmp, "Kestrel Front Matter.docx"),
           p("Table of Contents", "AACoverTitle") + p("Entries", sect="<w:sectPr/>") + p("Acronyms and Abbreviations", "AACoverTitle")
           + p("Terms"))
files = SDZ.split(two, os.path.join(tmp, "split"))
check("a file with two Word sections splits into two designs", len(files) == 2
      and [q["text"] for q in SDZ.read(files[1])["paragraphs"]] == ["Acronyms and Abbreviations", "Terms"])
check("Keep or Skip each section", len(SDZ.split(two, os.path.join(tmp, "split2"), keep={2})) == 1)
check("Remove from the library", SDZ.remove(cfg, a["id"]) and SDZ.designs(cfg, "acronyms") == [])
check("the library index carries its format number", json.load(open(os.path.join(cfg, SDZ.FOLDER, "index.json")))["format"] == SDZ.FORMAT)


class M:
    setup, pending = None, False


m = M()
check("Setup picks a design per section", SDZ.pick(m, "cover", x["id"]) and SDZ.picked(m, "cover") == x["id"])
check("None leaves out an optional section", SDZ.pick(m, "cui", "none") and SDZ.picked(m, "cui") == "none")
check("... never the cover or the Table of Contents", not SDZ.pick(m, "cover", "none") and not SDZ.pick(m, "toc", "none"))

print(f"DESIGNS 387 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
