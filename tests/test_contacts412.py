"""4.12.0 contacts built a piece at a time: several phones, e-mails and addresses with labels and where each came from;
a filed name changes only with Replace; a repeated value is not added twice; a contact saved before 4.12.0 reads its
phone as the first value (Main); editing a value in place, taking one out; the single fields mirror the first value.
Fictional content."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import contactcard as CC, effortrec as ER


def run():
    d = tempfile.mkdtemp()
    rec = ER.Record(d)
    # an old contact, saved the 4.11 way
    old = rec.save_contact({"name": "Dana Reyes", "phone": "(555) 010-2000", "email": "dana.reyes@kestrel.example"})
    c = rec.contact(old)
    assert "multi" not in c
    assert CC.values(c, "phone") == [{"label": "Main", "value": "(555) 010-2000", "source": None}]
    assert CC.card_of(c)["email"][0]["value"] == "dana.reyes@kestrel.example"
    # a new card from two picks pages apart
    s1 = {"doc": "Kestrel RFP", "page": "3", "text": "Contracting Officer: Sam Ortiz", "sid": "L.1.2"}
    s2 = {"doc": "Kestrel RFP", "page": "41", "text": "Phone (555) 010-3100", "sid": "L.9.4"}
    card = CC.blank()
    card["name"] = "Sam Ortiz"; card["title"] = "Contracting Officer"
    card["sources"] = {"name": [s1], "title": [s1]}
    card["phone"] = [{"label": "Office", "value": "(555) 010-3100", "source": s2}]
    cid = CC.save_card(rec, card)
    c = rec.contact(cid)
    assert c["name"] == "Sam Ortiz" and c["phone"] == "(555) 010-3100" and c["field_sources"]["name"][0]["sid"] == "L.1.2"
    assert c["multi"]["phone"][0]["source"]["page"] == "41" and c["multi"]["phone"][0]["label"] == "Office"
    # a second phone and a different name guess: the phone adds, the name stays without Replace
    more = CC.blank()
    more["name"] = "Ortiz Sam"
    more["phone"] = [{"label": "Mobile", "value": "(555) 010-3199"}, {"label": "Main", "value": "(555)010-3100"}]
    more["email"] = [{"label": "", "value": "sam.ortiz@kestrel.example"}]
    assert CC.save_card(rec, more, cid=cid) == cid
    c = rec.contact(cid)
    assert c["name"] == "Sam Ortiz", c["name"]
    assert [v["value"] for v in CC.values(c, "phone")] == ["(555) 010-3100", "(555) 010-3199"]
    assert CC.values(c, "email")[0]["label"] == "Main" and c["email"] == "sam.ortiz@kestrel.example"
    # Replace changes the filed name
    CC.save_card(rec, {"name": "Samuel Ortiz"}, cid=cid, replace=("name",))
    assert rec.contact(cid)["name"] == "Samuel Ortiz"
    # edit in place, relabel, take out
    assert CC.edit_value(rec, cid, "phone", 1, label="Fax")
    assert CC.values(rec.contact(cid), "phone")[1]["label"] == "Fax"
    assert CC.edit_value(rec, cid, "phone", 0, value="")
    c = rec.contact(cid)
    assert c["phone"] == "(555) 010-3199" and len(CC.values(c, "phone")) == 1
    assert CC.set_single(rec, cid, "title", "Contracting Officer (CO)") and rec.contact(cid)["title"] == "Contracting Officer (CO)"
    # the old contact becomes lists on its first change, keeping its phone first
    CC.save_card(rec, {"phone": [{"label": "Mobile", "value": "(555) 010-2001"}]}, cid=old)
    c = rec.contact(old)
    assert [v["label"] for v in CC.values(c, "phone")] == ["Main", "Mobile"] and c["phone"] == "(555) 010-2000"
    # lines and summary; an empty card files nothing
    assert ("Phone (Mobile)", "(555) 010-2001") in CC.lines(c)
    assert "(+1)" in CC.summary(c)
    assert CC.save_card(rec, CC.blank()) is None
    # kept across a reload
    rec2 = ER.Record(d)
    assert CC.values(rec2.contact(cid), "phone")[0]["value"] == "(555) 010-3199"
    json.dumps(rec2.data)
    print("test_contacts412: all checks passed")


if __name__ == "__main__":
    run()
