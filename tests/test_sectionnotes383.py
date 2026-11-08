"""3.83.0 the section panel's records: guidance saved as typed, references and notes for authors (a file with where to
look, or a note), the section's notes and context (notes pointed at it, meeting topics aimed at it, captures placed in
it) copied into the guidance or sent to the authors, the unassigned tray and Point at, and notes following a section
renamed or taken out. Fictional content (the Kestrel set)."""
import datetime, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import effortrec as RR, excerpts as EX, meetings as MT, quicknote as QN, outline_ops as O, setupdoc as SD
import sectionnotes as SN

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


class M:                                            # the matrix's parts this module uses
    def __init__(self):
        self.items, self.setup, self.pending = [], None, False


tmp = tempfile.mkdtemp()
rec = RR.Record(tmp)
m = M()

# guidance
check("no guidance yet reads empty", SN.guidance(m, "3.1") == "")
check("typing saves it", SN.set_guidance(m, "3.1", "Lead with the transition plan.") and m.pending)
check("it reads back", SN.guidance(m, "3.1") == "Lead with the transition plan.")
check("the same words again change nothing", SN.set_guidance(m, "3.1", "Lead with the transition plan.") is False)
check("it is the setup's management guidance", SD.setup_of(m)["mgmt"]["3.1"] == "Lead with the transition plan.")
SN.set_guidance(m, "3.9", "x"); SN.set_guidance(m, "3.9", "  ")
check("an emptied box takes it out", "3.9" not in SD.setup_of(m)["mgmt"])

# references
r1 = SN.add_ref(m, "3.1", path=r"C:\Kestrel\Library\Our Documents\Kestrel Transition Plan.docx", where="pages 4 to 6",
                origin="library")
r2 = SN.add_ref(m, "3.1", note="Use the 30-60-90 day framing.")
check("a file and a note become references", r1 and r2 and len(SN.refs(m, "3.1")) == 2)
check("nothing at all is not a reference", SN.add_ref(m, "3.1") is None)
check("the same file twice is one reference",
      SN.add_ref(m, "3.1", path=r"C:\Kestrel\Library\Our Documents\Kestrel Transition Plan.docx") == r1 and len(SN.refs(m, "3.1")) == 2)
f = SN.refs(m, "3.1")[0]
check("a file keeps its name and where it came from", f["name"] == "Kestrel Transition Plan.docx" and f["origin"] == "library")
check("the Word comment names the file and where to look",
      SN.comment_text(f) == "Reference: Kestrel Transition Plan.docx (pages 4 to 6)", SN.comment_text(f))
check("a note's comment is the note", SN.comment_text(SN.refs(m, "3.1")[1]) == "Use the 30-60-90 day framing.")
check("where to look can change", SN.update_ref(m, "3.1", r1, where="section 2") and SN.refs(m, "3.1")[0]["where"] == "section 2")
check("ids stay unique across sections", SN.add_ref(m, "3.2", note="Short.") not in (r1, r2))
check("a reference comes out", SN.remove_ref(m, "3.2", SN.refs(m, "3.2")[0]["id"]) and SN.refs(m, "3.2") == [])

# notes and context
n1 = SN.note_on(rec, "3.1", "The customer asked about weekend coverage at the orals.")
mid = MT.add_meeting(rec, "Kickoff", datetime.date.today().isoformat())
MT.add_topic(rec, mid, "Show the staffing ramp by month.", target="3.1")
MT.add_topic(rec, mid, "Not this section.", target="3.2")
EX.add(rec, "objective", [{"text": "Reduce transition risk to zero lost tickets."}], sections=["3.1"])
ctx = SN.context(rec, "3.1")
check("the section's note, topic and capture all show", sorted(c["kind"] for c in ctx) == ["capture", "note", "topic"],
      [c["kind"] for c in ctx])
check("another section's topic does not", not any(c["text"] == "Not this section." for c in ctx))
note_key = next(c["key"] for c in ctx if c["kind"] == "note")
got = SN.copy_into_guidance(m, rec, "3.1", note_key)
check("Copy into guidance adds the words after the guidance",
      got == "Lead with the transition plan.\n\nThe customer asked about weekend coverage at the orals.", repr(got))
check("copying twice does not repeat them", SN.copy_into_guidance(m, rec, "3.1", note_key) == got)
check("the item says it was used", next(c for c in SN.context(rec, "3.1") if c["key"] == note_key)["used"] == "guidance")
topic_key = next(c["key"] for c in ctx if c["kind"] == "topic")
rid = SN.send_to_authors(m, rec, "3.1", topic_key)
check("Send to authors makes a note for the authors",
      rid and any(r["note"] == "Show the staffing ramp by month." and r["origin"] == "context" for r in SN.refs(m, "3.1")))
SN.mark_used(rec, topic_key, "")
check("a mark clears", next(c for c in SN.context(rec, "3.1") if c["key"] == topic_key)["used"] == "")

# the tray
qid = QN.add(rec, "Ask the pricing lead about the option years.")
check("a quick note waits in the tray", any(n["id"] == qid for n in SN.unassigned(rec)))
check("a section is a place a note can go", QN.send(rec, "Direct to 3.3.", "section:3.3") is not None)
check("Point at sends it to the section", SN.point_at(rec, qid, "3.2"))
check("it leaves the tray", not any(n["id"] == qid for n in SN.unassigned(rec)))
check("and shows under the section", any(c["text"] == "Ask the pricing lead about the option years." for c in SN.context(rec, "3.2")))

# following the structure
O.relabel(m, {"3.1": "3.4"})
check("guidance and references follow a renumbered section", SN.guidance(m, "3.4").startswith("Lead with") and SN.refs(m, "3.4"))
check("notes follow it too", SN.relabel(rec, {"3.1": "3.4"}) == 1 and any(c["kind"] == "note" for c in SN.context(rec, "3.4")))
SN.relabel(rec, {"3.2": ""})
check("a section taken out leaves its notes on the effort",
      any(n["text"].startswith("Ask the pricing") and n["on"] == "effort" for n in RR.Record(tmp).notes()))

print(f"SECTION NOTES 383 {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
