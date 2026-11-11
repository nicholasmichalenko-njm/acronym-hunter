"""3.23.0 the Word check of a finished template: without Word it says so and does nothing; Word's answer is read per
Quick Part (fields, field errors, styles not in the template), one entry or many; the check in words names each part
with a problem; on Windows with Word (the build PC) it runs on a real template."""
import json, os, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
import prodwordgate as WG

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, "" if ok else info)


if not WG.available():
    check("without Word: it says so and does nothing", WG.gate("x.dotx")["ok"] is False and "Word" in WG.gate("x.dotx")["why"])
one = {"ok": True, "fields": 12, "field_errors": "STYLEREF \"Gone\"", "pages": 4,
       "entries": {"name": "Volume cover", "category": "01 Covers", "ok": False, "fields": 2, "errors": "SEQ Table", "styles_missing": ""}}
r1 = WG.gate("x.dotx", runner=lambda cmd, env, t: "noise\n" + json.dumps(one))
check("one entry from Word is read as a list, with its errors", r1["ok"] and r1["entries"][0]["errors"] == ["SEQ Table"]
      and r1["entries"][0]["styles_missing"] == [] and r1["field_errors"] == ['STYLEREF "Gone"'], r1)
many = {"ok": True, "fields": 3, "field_errors": [], "pages": 2, "entries": [
    {"name": "A", "category": "01", "ok": True, "fields": 1, "errors": [], "styles_missing": []},
    {"name": "B", "category": "02", "ok": False, "fields": 0, "errors": [], "styles_missing": ["Ghost"]}]}
r2 = WG.gate("x.dotx", runner=lambda cmd, env, t: json.dumps(many))
t2 = WG.text(r2)
check("the check in words names each part with a problem", "2 Quick Part(s) put in, 1 with a problem" in t2 and "02 / B: style Ghost not in the template" in t2, t2)
check("a Word that does not answer is reported", WG.gate("x.dotx", runner=lambda c, e, t: "")["ok"] is False)
check("the template path goes to PowerShell in the environment, never in the command",
      WG.gate("C:/t/x.dotx", runner=lambda cmd, env, t: (json.dumps(many) if env["SK_TPL"].endswith("x.dotx") and "x.dotx" not in " ".join(cmd) else ""))["ok"])
if WG.available():                                     # the build PC: Word's own check of a real template
    import prodrules as PRL, prodtemplate as PT, prodparts as PP, prodquickparts as QP
    from _qpfixture import with_glossary
    tmp = tempfile.mkdtemp()
    src = os.path.join(tmp, "Team.dotx")
    with_glossary(os.path.join(HERE, "pefix", "data", "PE_Master_Effort_Template.dotx"), src)
    cfg = os.path.join(tmp, "cfg"); k = QP.keep_source(cfg, src)
    std = PRL.for_effort(tempfile.mkdtemp()); std["_parts_dir"] = PP.parts_dir(cfg)
    std["quick_parts"] = {"one_gallery": True, "entries": [{"name": "Volume cover", "category": "01 Covers", "source": k},
                                                           {"name": "CUI header", "category": "04 Headers", "source": k}]}
    std["variables"].update(volume_name="Volume I", solicitation="FA8810", company="Acme")
    tj = PT.make(std, os.path.join(tmp, "out"))
    res = WG.gate(tj.copy)
    print(WG.text(res))
    check("Word checks a real template: every Quick Part goes in with its styles and fields", res.get("ok") and len(res["entries"]) == 2
          and all(e["ok"] for e in res["entries"]) and not res["field_errors"], res)
    import themebook as TB                              # 4.10.0: a theme filled in from the workbook's Theme sheet
    std2 = PRL.for_effort(tempfile.mkdtemp()); std2["variables"].update(volume_name="Volume I", solicitation="FA8810", company="Acme")
    std2["theme"], _p, _c = TB.apply(std2, [{"Name": "Accent 1", "Value": "1F3864"}, {"Name": "Body font", "Value": "Arial"}])
    tj2 = PT.make(std2, os.path.join(tmp, "out2"))
    res2 = WG.gate(tj2.copy)
    check("Word opens a template whose theme came from the Theme sheet (the base theme, edited)", res2.get("ok"), res2)
print(f"WORD GATE {'PASS' if all(checks) else 'FAIL'} ({sum(checks)}/{len(checks)})")
sys.exit(0 if all(checks) else 1)
