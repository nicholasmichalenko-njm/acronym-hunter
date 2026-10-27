"""2.51.0 nothing is missed: a fictional RFP with the cases the reader used to drop (a lead-in line with no list after
it and the contact lines under it, a phone number, a sentence the RFP says twice, two lists with the same lead-in,
table cells with numbers, a short formatting line without a period) is read into the review in full, in Word and in
PDF; the text check proves it; a re-read keeps both copies of a repeated sentence."""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
os.environ["AH_TEST"] = "1"; os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A, compliance as C, textcheck as TC
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


D = os.path.join(os.path.dirname(HERE), "test_samples", "rfp_stress")
for name in ("Stress_RFP.docx", "Stress_RFP.pdf"):
    p = os.path.join(D, name)
    heads = []
    items = C.extract([(name, A.rfp_chunks(p))], heads)
    texts = [it["text"] for it in items]
    r = TC.check(p, items, heads)
    check(f"{name}: every word is in the review", r["missing"] == 0, [l for l in r["lines"] if l[2] == "missing"][:5])
    check(f"{name}: a lead-in with no list after it stays", "Submit questions to:" in texts)
    check(f"{name}: the phone number stays", any("555-0142" in t for t in texts))
    check(f"{name}: a sentence said twice is two rows", texts.count("The Offeror shall describe the thermal design.") == 2)
    check(f"{name}: two lists with the same lead-in keep their items", sum(1 for it in items if it["lead"].startswith("The Offeror shall provide the following")) == 5)
    check(f"{name}: a short formatting line is its own row", "Font: 12 point Times New Roman" in texts and "Margins: 1 inch" in texts, [t for t in texts if t.startswith("Font")])
    merged = C.merge_reread(items, C.extract([(name, A.rfp_chunks(p))]))
    check(f"{name}: a re-read keeps both copies, nothing new", sum(1 for it in merged if it["text"] == "The Offeror shall describe the thermal design.") == 2
          and not any(it.get("new") for it in merged), [it["new"] for it in merged if it.get("new")])
n = sum(checks)
print(f"COMPLETE PASS ({n}/{len(checks)})" if n == len(checks) else f"COMPLETE FAIL ({n}/{len(checks)})")
