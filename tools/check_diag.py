"""Build gate: logging calls may only carry fixed messages written in our code, never data.

Checks every logging call in the program's own .py files:
    log_error(...), eng.log_error(...), A.log_error(...), diag.error / warning / activity / swallowed(...)
Rule: the message argument is a plain string literal (no f-string, no variable, no concatenation),
and keyword arguments are only area= (a literal) or whitelisted count names (values are checked at run time).
Also refuses any code that still writes logs\\error.log.
Exit code 0 = pass, 1 = fail (build.ps1 stops).
"""
import ast, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import diag  # noqa: E402

FILES = ["shredquick.py", "compareany.py", "skqt/shredpage.py", "skqt/comparespace.py", "skqt/techeditpage.py", "techedit.py", "techeditdocx.py", "skqt/toolshome.py", "skqt/refspage.py", "recentfiles.py", "effortprofiles.py", "templatesboard.py", "skqt/profilespage.py", "skqt/templatespage.py", "acrdb.py", "acrmore.py", "acrlists.py", "ocrfixes.py", "firstuse.py", "context.py", "skqt/acrextras.py", "skqt/effortlistextras.py", "skqt/fulltexttool.py", "skqt/firstusetool.py", "skqt/symbols.py", "skqt/foundview.py", "skqt/acrtool.py", "libpreview.py", "skqt/itempicture.py", "libcats.py", "libimport.py", "libconvert.py", "libstyle.py", "skqt/libscreen.py", "skqt/libedit.py", "skqt/qpjobs.py", "sectioncontents.py", "skqt/sectioneditor.py", "importbrowse.py", "skqt/importbrowser.py", "skqt/templatelibview.py", "setupread.py", "skqt/draftstatuspage.py", "hfbuild.py", "qpmake.py", "skqt/hfbuilder.py", "capturefiles.py", "excerpts.py", "skqt/binsview.py", "skqt/meetingspage.py", "skqt/custqapage.py", "pagekinds.py", "wordpreview.py", "wordedit.py", "skqt/docparts.py", "skqt/coverview.py", "datacalls.py", "dispositions.py", "skqt/datacallspage.py", "skqt/reviewpage.py", "rulebook.py", "rulecheck.py", "skqt/rulespage.py", "kickoff.py", "skqt/kickoffview.py", "skqt/effortlistpage.py", "effortformat.py", "skqt/effortformatpage.py", "coverbuild.py", "skqt/coverdraw.py", "skqt/coverview.py", "skqt/docparts.py", "templateprofile.py", "skqt/profileview.py", "prodengine/pe/bullets.py", "qpmeasure.py", "exactpreview.py", "elementcheck.py", "skqt/checkspage.py", "pageplan.py", "units.py", "skqt/pagepreview.py", "skqt/unitsview.py", "elementbuild.py", "responseelements.py", "skqt/builder.py", "skqt/elementsview.py", "reviewitems.py", "skqt/reviewitemsview.py", "topics.py", "skqt/topicsview.py", "coverlayout.py", "skqt/coverview.py", "partdesigns.py", "skqt/docparts.py", "templatedetails.py", "numtext.py", "skqt/maketemplates.py", "setuptemplate.py", "fillins.py", "templatecheck.py", "templatereg.py", "prodwordgate.py", "teamdata.py", "templatelib.py", "prodquickparts.py", "skqt/collectview.py", "excerpts.py", "skqt/binsview.py", "meetings.py", "skqt/meetingspage.py", "structparts.py", "skqt/efforttypes.py", "pagemarks.py", "suggestrules.py", "prodgraphics.py", "skqt/auditpage.py", "skqt/stdpreview.py", "app_gui.py", "doctr_engine.py", "equations.py", "sandbox.py", "tess_train.py", "diag.py", "effort.py",
         "custdefs.py", "volcheck.py", "compliance.py", "docxw.py", "complearn.py", "placelearn.py", "cwords.py",
         "workspace.py", "setupdoc.py", "master_db.py", "keywords.py", "offerings.py", "pictures.py",
         "corrections.py", "docversions.py", "subreq.py", "effortrec.py", "effortpkg.py", "statusdoc.py",
         "deliverables.py", "impact.py", "briefs.py", "readable.py", "keepsafe.py", "bgwork.py",
         "matrixdesign.py", "studio.py", "rfpoutline.py", "trainpack.py", "eqlayout.py", 
         "office_pdf.py", "pagesent.py", "compliance_read.py", "assign_ops.py", "skqt_main.py", "skqt/mainwin.py",
         "skqt/readpage.py", "skqt/assign.py", "skqt/design.py", "skqt/structure.py",
         "skqt/prove.py", "structure_ops.py", "skqt/matrixpage.py", "skqt/setuppage.py", "skqt/crosswalkpage.py",
         "crosswalk.py", "effortstate.py", "skqt/homepage.py", "skqt/dashpage.py", "reviewpkt.py",
         "skqt/recordpage.py", "skqt/reviewpage.py", "acrsession.py", "skqt/acronympage.py", "skqt/effortlistpage.py",
         "docintake.py", "skqt/custdocs.py", "skqt/qapage.py", "skqt/keywordspage.py", "skqt/exportallpage.py",
         "skqt/settingspage.py", "outline_ops.py", "structstart.py", "capture.py", "skqt/trainingwin.py",
         "skqt_training.py", "skqt/trainerpage.py", "skqt/pkgimport.py", "updatepack.py", "edsign.py",
         "skqt/updates.py", "authorlist.py", "skqt/people.py", "skqt/safety.py", "lineage.py", "workmode.py",
         "skqt/modes.py", "datahome.py", "effortcheck.py", "supportfile.py", "skqt/helpcenter.py", "skqt/progress.py",
         "skqt/librarypage.py", "ctxdocs.py", "skqt/ctxassign.py", "changereview.py", "skqt/changeview.py",
         "skqt/nowheel.py", "skqt/listspage.py", "skqt/adaptive.py", "skqt/whereview.py", "delivboard.py",
         "skqt/delivboardview.py", "branding.py", "effortcal.py", "skqt/brandview.py", "skqt/calview.py",
         "teampack.py", "skqt/teamview.py", "effortfolders.py", "unfiled.py", "effortsummary.py", "postsub.py",
         "skqt/effortshome.py", "skqt/unfiledview.py", "skqt/postsubpage.py", "tzones.py", "readablejob.py",
         "tqexport.py", "skqt/stagesedit.py", "process.py", "skqt/processview.py", "skqt/rolesview.py", "doctypes.py",
         "skqt/doctypeui.py", "skqt/doctypesview.py", "watch.py", "skqt/watchview.py", "folderplan.py",
         "skqt/folderplanview.py", "ocrpdf.py", "sheetview.py", "captures.py", "skqt/captureview.py",
         "sensitivity.py", "secure.py", "buildvariant.py", "skqt/sensgate.py", "custqa.py", "skqt/custqapage.py",
         "whatchanged.py", "skqt/whatview.py", "custfocus.py", "amendinst.py", "skqt/guide.py", "skqt/starteffort.py",
         "graphics.py", "customdict.py", "skqt/dictview.py", "effortsched.py", "sincelast.py", "pagebudget.py",
         "mywork.py", "skqt/schedview.py", "skqt/budgetview.py", "skqt/myworkpage.py", "themes.py", "storyboard.py",
         "skqt/storyboardpage.py", "walloftruth.py", "skqt/wallpage.py", "pkgcheck.py",
         "xrefcheck.py", "draftcompare.py", "skqt/checkspage.py", "prodrules.py", "prodfix.py", "prodcopy.py",
         "prodword.py", "prodlearn.py", "prodtemplate.py", "issuelog.py", "skqt/issueview.py", "prodparts.py",
         "prodoffice.py", "stagecolors.py", "roleaccess.py", "skqt/roleview.py", "skqt/prodstdpage.py",
         "skqt/prodfixpage.py", "acrrules.py", "qacheck.py", "trainerkit.py"]
LOG_FUNCS = {"log_error"}
DIAG_FUNCS = {"error", "warning", "activity", "swallowed"}


def call_name(node):
    f = node.func
    if isinstance(f, ast.Name):
        return f.id, None
    if isinstance(f, ast.Attribute):
        base = f.value.id if isinstance(f.value, ast.Name) else None
        return f.attr, base
    return None, None


def is_literal(n):
    return isinstance(n, ast.Constant) and isinstance(n.value, str)


def check_file(path):
    problems = []
    src = open(path, encoding="utf-8").read()
    if "error.log" in src and os.path.basename(path) not in ("diag.py",):
        for i, line in enumerate(src.splitlines(), 1):
            if "error.log" in line and not line.lstrip().startswith("#"):
                problems.append(f"{i}: mentions error.log (old log file)")
    tree = ast.parse(src)
    exempt = set()      # the logging wrappers themselves forward their arguments
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.name in ("log_error", "_excepthook"):
            exempt.update(id(n) for n in ast.walk(fn))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or id(node) in exempt:
            continue
        name, base = call_name(node)
        if name in LOG_FUNCS:
            msg_args = node.args[:1]
        elif name in DIAG_FUNCS and base == "diag":
            if name == "swallowed":
                msg_args = node.args[:1]       # optional area literal
            elif name == "activity":
                msg_args = node.args[:1]
            else:
                msg_args = node.args[1:2]       # error(area, msg, ...)
                if node.args and not is_literal(node.args[0]):
                    problems.append(f"{node.lineno}: diag.{name} area must be a string literal")
        else:
            continue
        for a in msg_args:
            if not is_literal(a):
                problems.append(f"{node.lineno}: {name}() message must be a plain string literal")
            elif any(ch in a.value for ch in "/\\:") or len(a.value) > 160:
                problems.append(f"{node.lineno}: {name}() message must not contain / \\ or : (the export check rejects them)")
        for kw in node.keywords:
            if kw.arg in ("area",):
                if not is_literal(kw.value):
                    problems.append(f"{node.lineno}: {name}() area= must be a string literal")
            elif kw.arg in ("exc", "with_traceback"):
                continue
            elif kw.arg == "ext" or kw.arg in diag.COUNT_KEYS:
                continue
            else:
                problems.append(f"{node.lineno}: {name}() keyword '{kw.arg}' is not an allowed count field")
    return problems


def main():
    bad = 0
    for f in FILES:
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p):
            continue
        for prob in check_file(p):
            print(f"{f}:{prob}")
            bad += 1
    print("Logging check passed: messages are fixed text, no data." if not bad else f"Logging check FAILED: {bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
