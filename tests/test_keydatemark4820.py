"""4.82.0 (K1): the Submission Formatting Requirements pass, Key Date, the logic. The kind read from the words, the date
written the effort's way, a calendar entry that keeps the piece it came from, an amendment's date in the place of the
earlier one, the mark taken off, the pass's next pieces and each document's state, the calendar's way back, and
Questions due on the calendar from Customer information. Fictional (Kestrel)."""
import datetime, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"
import custinfo as CI, effortrec as R, effortstate as ES, keydatemark as KM

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


class Mx:
    def __init__(self, items):
        self.items, self.setup, self.outline, self.pending = items, {}, [], False

    def log(self, *a):
        pass


check("seven kinds, in the agreed order", [n for _k, n in KM.KINDS] == ["Proposal due", "Questions due", "Answers expected", "Intent to bid due",
                                                                         "Site visit or industry day", "Oral presentations", "Other"])
reads = {"Questions are due no later than March 1, 2027 at 2:00 PM Eastern Time.": "questions",
         "Proposals shall be received by 4:00 p.m. MT on December 15, 2026.": "proposal",
         "Answers to questions will be posted on or about 15 January 2027.": "answers",
         "Notice of intent to propose is due by January 5, 2027.": "intent",
         "A site visit will be held on 01/20/2027 at 10:00 AM CST.": "visit",
         "Oral presentations will be scheduled the week of February 8, 2027.": "orals",
         "Contract award is expected by June 1, 2027.": ""}
got = {t: KM.kind_read(t) for t in reads}
check("the kind is read from the words; nothing is guessed when the words say none", got == reads, got)
v = KM.read("Questions are due no later than March 1, 2027 at 2:00 PM Eastern Time.")
check("the date, the time and the time zone are read", v == {"date": "2027-03-01", "start": "14:00", "zone": "ET", "kind": "questions"}, v)
check("words with no date read as nothing", KM.read("The Offeror shall describe its approach.") is None)
check("written the effort's way, with and without a time", KM.when_text(v) == "Mar 1, 2027, 2:00 p.m. ET"
      and KM.when_text({"date": "2027-02-08", "start": "", "zone": ""}) == "Feb 8, 2027", KM.when_text(v))
check("a typed date reads the same way", KM.when_of("Feb 2, 2027 9:30 AM MT") == {"date": "2027-02-02", "start": "09:30", "zone": "MT"},
      KM.when_of("Feb 2, 2027 9:30 AM MT"))

tmp = tempfile.mkdtemp()
rec = R.Record(tmp)
items = [{"id": "P1", "file": "L.pdf", "text": "A site visit will be held on 01/20/2027 at 10:00 AM CT."},
         {"id": "P2", "file": "L.pdf", "text": "Answers to questions will be posted on or about 15 January 2027."},
         {"id": "P3", "file": "L.pdf", "text": "The Offeror shall describe its approach."},
         {"id": "P4", "file": "Amendment.pdf", "text": "Answers to questions will now be posted on or about 22 January 2027."},
         {"id": "P5", "file": "L.pdf", "text": "Key dates are listed in the table below.", "piece": "date"},
         {"id": "P6", "file": "L.pdf", "type": "Heading", "text": "L.2 Schedule, March 3, 2027"}]
M = Mx(items)
check("the pass's next: pieces with a date, and pieces typed Key Date before; headings out",
      [it["id"] for it in KM.open_rows(M, "L.pdf")] == ["P1", "P2", "P5"], [it["id"] for it in KM.open_rows(M, "L.pdf")])
check("a piece typed Key Date before is 'kind not said'", KM.older(M, items[4]) and not KM.older(M, items[0]))
src = {"doc": "L.pdf", "page": "4"}
v1 = KM.read(items[0]["text"])
eid = KM.file_event(rec, M, items[0], "visit", v1, source=src)
KM.mark(M, items[0], "visit", v1, eid=eid)
e = next(x for x in rec.data["events"] if x["id"] == eid)
check("a site visit is on the calendar, keeping the piece it came from", e["kind"] == "Meeting" and e["title"] == "Site visit or industry day"
      and e["key_kind"] == "visit" and e["key_sid"] == "P1" and e["key_doc"] == "L.pdf" and e["key_page"] == "4" and e["start"] == "10:00"
      and "From L.pdf, page 4" in e["details"], e)
check("the marked piece leaves the pass's next; the document has finds", [it["id"] for it in KM.open_rows(M, "L.pdf")] == ["P2", "P5"]
      and KM.docs(M)[0]["state"] == "Has finds (1)" and KM.count(M) == 1, KM.docs(M))
cal = R.Record(tmp).calendar()
check("on the calendar it says its kind, as a key date", ("key", "Site visit or industry day 10:00 a.m. CST") in cal.get(datetime.date(2027, 1, 20), []),
      cal.get(datetime.date(2027, 1, 20)))
check("the calendar's way back names the piece", KM.sources_on(R.Record(tmp), datetime.date(2027, 1, 20)) ==
      [{"text": "Site visit or industry day", "sid": "P1", "file": "L.pdf", "page": "4"}], KM.sources_on(R.Record(tmp), datetime.date(2027, 1, 20)))
check("several site visits: none is 'earlier' (more than one date of that kind)", KM.earlier(rec, "visit", "P9") is None)

v2 = KM.read(items[1]["text"])
e2 = KM.file_event(rec, M, items[1], "answers", v2, source={"doc": "L.pdf"})
KM.mark(M, items[1], "answers", v2, eid=e2)
old = KM.earlier(rec, "answers", "P4")
check("Answers expected holds one date: another piece finds the earlier one", old is not None and old["id"] == e2)
v4 = KM.read(items[3]["text"])
e4 = KM.file_event(rec, M, items[3], "answers", v4, source={"doc": "Amendment.pdf"}, replace=old)
KM.mark(M, items[3], "answers", v4, eid=e4, was=KM.when_text(old))
cal = R.Record(tmp).calendar()
check("the amendment's date is shown, saying what it replaced; the earlier is not", ("key", "Answers expected (replaces Jan 15, 2027)") in cal.get(datetime.date(2027, 1, 22), [])
      and not cal.get(datetime.date(2027, 1, 15)), (cal.get(datetime.date(2027, 1, 22)), cal.get(datetime.date(2027, 1, 15))))
check("... and it has no way back on the old day", KM.sources_on(R.Record(tmp), datetime.date(2027, 1, 15)) == [])
out = KM.unmark(rec, M, items[3])
cal = R.Record(tmp).calendar()
check("taking the amendment's mark off puts the earlier date back", out == "off" and ("key", "Answers expected") in cal.get(datetime.date(2027, 1, 15), [])
      and not cal.get(datetime.date(2027, 1, 22)) and KM.of_piece(M, items[3]) is None and "P4" not in KM.marks(M), cal.get(datetime.date(2027, 1, 15)))

v9 = {"date": "2027-06-01", "start": "", "zone": ""}
e9 = KM.file_event(rec, M, items[2], "other", v9, name="Award", source={"doc": "L.pdf"})
check("Other is named, and the name is offered again in the effort", next(x for x in rec.data["events"] if x["id"] == e9)["title"] == "Award"
      and KM.own_names(R.Record(tmp)) == ["Award"])
KM.add_own(rec, "award")
check("... once", KM.own_names(rec) == ["Award"])

KM.mark(M, items[4], "questions", v, eid="fact")
check("a fact's mark comes off and the fact stays", KM.unmark(rec, M, items[4]) == "fact" and KM.of_piece(M, items[4]) is None)
CI.set_fact(rec, "Questions due", KM.fact_value(v), "captured", source={"doc": "L.pdf", "page": "2", "sid": "P5"})
q = KM.questions_from_fact(rec)
check("Questions due on the calendar comes from Customer information", q == (datetime.date(2027, 3, 1), "questions", "2:00 p.m. ET"), q)
check("... and the way back follows the fact's source", {"text": "Questions due", "sid": "P5", "file": "L.pdf", "page": "2"} in KM.sources_on(rec, datetime.date(2027, 3, 1)))
import subreq as SR
SR.summary = lambda rows: {"questions_due": {"value": "February 2, 2027"}}          # the reader's own finding, stood in for
x = ES.cal_extra_of(rec, [{}])
check("the date the reader found is not shown beside the fact's", [t for t in x if t[1] == "questions"] == [q], x)
CI.set_fact(rec, "Questions due", "", "typed")
x = ES.cal_extra_of(rec, [{}])
check("with the fact empty the reader's date shows as before", [t for t in x if t[1] == "questions"] ==
      [(datetime.date(2027, 2, 2), "questions", "Questions due to the customer")], x)
print(f"{sum(checks)}/{len(checks)}")
if not all(checks):
    sys.exit(1)
print("ok test_keydatemark4820")
