"""4.12.0 deliverables: delete keeps a copy (deliverables_removed) and restore puts it back where it was, whole; the
confirmation names what goes with it; a piece of the solicitation attaches to one deliverable at a time (attaching it
elsewhere moves it), is listed on the deliverable and taken off. Fictional content."""
import os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import deliverables as DL, effortrec as ER


def run():
    d = tempfile.mkdtemp()
    rec = ER.Record(d)
    a = DL.add(rec, "Volume I Technical", "Volume", owner="A. Lee")
    b = DL.add(rec, "CDRL A001 Program Management Plan", "Plan")
    c = DL.add(rec, "SF 33", "Form")
    DL.update(rec, b, notes="Due with the proposal")
    DL.get(rec, b)["dates"] = [{"id": "x1", "date": "2026-12-01", "what": "Pink team"}]
    piece = {"sid": "F.3.1", "doc": "Kestrel RFP", "page": "12", "text": "The Contractor shall deliver CDRL A001."}
    assert DL.attach_piece(rec, b, piece)
    assert not DL.attach_piece(rec, b, piece)
    assert DL.of_piece(rec, "F.3.1")["id"] == b and DL.pieces_of(rec, b)[0]["page"] == "12"
    bits = DL.what_goes(DL.get(rec, b))
    assert "1 date" in bits and "1 piece of the solicitation" in bits and "its notes" in bits, bits
    # attaching to another moves it
    assert DL.attach_piece(rec, a, piece)
    assert DL.of_piece(rec, "F.3.1")["id"] == a and not DL.pieces_of(rec, b)
    assert DL.detach(rec, "F.3.1") and DL.of_piece(rec, "F.3.1") is None
    DL.attach_piece(rec, b, piece)
    # delete and restore
    assert DL.remove(rec, b, who="pm")
    assert DL.get(rec, b) is None and DL.removed(rec)[0]["id"] == b and DL.removed(rec)[0]["removed_by"] == "pm"
    assert DL.of_piece(rec, "F.3.1") is None
    assert any(e["text"] == "Deliverable removed: CDRL A001 Program Management Plan" for e in rec.data["timeline"])
    rec2 = ER.Record(d)
    assert DL.restore(rec2, b)
    assert [x["id"] for x in DL.items(rec2)] == [a, b, c]
    x = DL.get(rec2, b)
    assert x["notes"] == "Due with the proposal" and x["dates"][0]["what"] == "Pink team" and "removed" not in x and "board_place" not in x
    assert DL.of_piece(rec2, "F.3.1")["id"] == b
    assert not DL.removed(rec2) and not DL.restore(rec2, b)
    assert not DL.remove(rec2, "nope")
    print("test_deliverables412: all checks passed")


if __name__ == "__main__":
    run()
