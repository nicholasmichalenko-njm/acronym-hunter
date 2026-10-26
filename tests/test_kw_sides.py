"""2.34.0 keywords from both sides: the customer's words used in our volumes are Shared language; a phrase only in our
volumes is tied to the customer ask it answers (the matrix placement first, else the customer's emphasized phrase in
our section) and is Our response; the list keeps a share of each side."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import keywords as K, effort as E

CUST = [("RFP.docx (section 'L.4.2 Thermal Management', paragraph 3)",
         "The offeror shall describe thermal management of the radiator panels. Thermal management will be evaluated for margin.", "customer"),
        ("RFP.docx (section 'L.4.3 Power Generation', paragraph 1)",
         "The offeror shall describe power generation capacity. Power generation must meet the load.", "customer")]
OURS = [("Vol.docx (section '3.2 Thermal Management Approach', paragraph 2)",
         "Our loop heat pipe network moves heat to the deployable radiator wings. The loop heat pipe network has flight heritage. "
         "Thermal management margin is 20 percent.", "ours"),
        ("Vol.docx (section '3.3 Power', paragraph 1)",
         "Triple junction cells feed the regulated bus. Triple junction cells degrade slowly.", "ours")]


def by_phrase(items):
    return {i["phrase"].lower(): i for i in items}


def run():
    assert K.heading_matches("3.3 Power", "3.3 Electrical Power")            # same number
    assert K.heading_matches("Thermal Control", "4.1 Thermal Control")        # same title
    assert not K.heading_matches("3.3 Power", "3.4 Power Budget")
    assert not K.heading_matches("Power", "Power Budget")                    # too short to call a match
    got = by_phrase(K.suggest(CUST + OURS, base={}, learned={}))
    tm = got["thermal management"]
    assert tm["side"] == "both" and any("the customer's words, used in our volumes" in w for w in tm["why"]), tm
    pg = got["power generation"]
    assert pg["side"] == "customer" and any("not yet in our volumes" in w for w in pg["why"]), pg["why"]
    lhp = got["loop heat pipe network"]
    assert lhp["side"] == "ours" and lhp["bucket"] == "Our response" and lhp["answers"] == ["'Thermal management'"], lhp
    assert any("answer the customer's 'Thermal management'" in w for w in lhp["why"])
    tj = got["triple junction cells"]
    assert tj["answers"] == [] and tj["bucket"] != "Our response"            # no customer ask uses its section's words
    # the matrix placement ties it, and says so
    got = by_phrase(K.suggest(CUST + OURS, base={}, learned={}, asks=[("L.4.3-01", "3.3 Power")]))
    tj = got["triple junction cells"]
    assert tj["answers"] == ["L.4.3-01 (3.3 Power)"] and tj["bucket"] == "Our response", tj
    assert any("placed there in the compliance matrix" in w for w in tj["why"])
    # tied and both-sides phrases score up
    plain = by_phrase(K.suggest(CUST + OURS, base={}, learned={}))["triple junction cells"]["score"]
    assert tj["score"] == round(plain + 1.0, 2), (tj["score"], plain)
    # new compared with past proposals still makes it a Differentiator
    base = {"docs": 4, "df": {}}
    assert by_phrase(K.suggest(CUST + OURS, base=base, learned={}))["loop heat pipe network"]["bucket"] == "Differentiator"
    # balance: many strong customer phrases never crowd out our side
    many = [(f"RFP.docx (section 'L.{i} Topic{i} Area', paragraph 1)",
             f"The offeror shall describe zeta{i} kappa{i} lambda{i}. Zeta{i} kappa{i} lambda{i} will be evaluated.", "customer")
            for i in range(40)]
    out = K.suggest(many + OURS, base={}, learned={}, limit=10)
    assert len(out) == 10 and sum(1 for o in out if o["side"] == "ours") >= 2, [(o["phrase"], o["side"]) for o in out]
    for b in ("Shared language", "Our response"):
        assert b in E.KW_CATEGORIES and b in K.BUCKETS
    print("KW SIDES PASS")


if __name__ == "__main__":
    run()
