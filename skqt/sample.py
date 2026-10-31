"""Try the sample effort (3.2.0): a first effort to learn on. It makes the fictional Kestrel Thermal effort with its
request for proposal (bundled in the program, everything made up), a response structure, a due date, a small team that
shows only in this effort, a few tasks, a team question, a customer question, a win theme, a hot button and two
deliverables, then reads the documents into the review in the background. Nothing in it is real; delete it from All
Efforts when you are done (Archive)."""
import datetime, os, shutil, sys
import diag

NAME = "Kestrel Thermal (sample)"
TEAM = ("A. Rivera", "J. Garcia", "M. Chen")
OUTLINE = "Volume I Technical\n1.1 Thermal Design\n1.2 Risk Management\nVolume II Management\n2.1 Schedule\n2.2 Staffing"


def sample_dir():
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", "sample")


def documents():
    d = sample_dir()
    return sorted(os.path.join(d, f) for f in os.listdir(d) if f.lower().endswith((".pdf", ".docx"))) if os.path.isdir(d) else []


def free_name(registry):
    names = {n.casefold() for n in registry.names()}
    if NAME.casefold() not in names:
        return NAME
    k = 2
    while f"{NAME[:-1]} {k})".casefold() in names:
        k += 1
    return f"{NAME[:-1]} {k})"


def build(host, read=True):
    """Makes the sample effort and opens it. Returns its name, or None."""
    docs = documents()
    if not docs:
        host.status("The sample documents are missing from this copy of Stationkeeper.")
        return None
    import app_gui, datahome
    import effortfolders as EF
    name = free_name(host.efforts)
    base = datahome.efforts_dir(app_gui.DATA_DIR)
    values = {"name": name, "path": EF.new_list_path(base, name, {"Client": "Fictional Space Agency", "Solicitation": "SAMPLE-26-R-0001",
                                                                 "Internal": ""})[0],
              "client": "Fictional Space Agency", "solicitation": "SAMPLE-26-R-0001"}
    made = host.settings_page.new_effort(values)
    if not made:
        return None
    host.efforts.put(made, sample=True)
    try:
        import branding as BR, effortrec as RR, custqa as Q, custfocus as F, deliverables as DL, themes as TH
        ws = host.ws
        ws.set("outline_text", OUTLINE)
        cust = (host.efforts.get(made) or {}).get("customer_dir") or EF.folder(host.effort_path, "customer")
        os.makedirs(cust, exist_ok=True)
        copied = []
        for p in docs:
            dst = os.path.join(cust, os.path.basename(p))
            shutil.copy2(p, dst)
            copied.append(dst)
        for n in TEAM:                                   # the sample's people show only in the sample
            if not host.authors.find(n):
                host.authors.add(n, efforts=[made], source="sample")
            else:
                host.authors.show_in(n, made, True)
        rec = RR.Record(ws.root)
        due = datetime.date.today() + datetime.timedelta(days=45)
        while due.weekday() >= 5:
            due += datetime.timedelta(days=1)
        rec.set_due(f"{due.isoformat()}T14:00", "ET", zone_key="ET")
        BR.set_identity(rec, pm="A. Rivera", who="sample")
        rec = RR.Record(ws.root)
        soon = lambda d: (datetime.date.today() + datetime.timedelta(days=d)).isoformat()   # noqa: E731
        rec.add_task("Draft the thermal design approach (1.1)", owner="J. Garcia", due=soon(14), who="sample")
        rec.add_task("Build the integrated master schedule (2.1)", owner="M. Chen", due=soon(18), who="sample")
        rec.add_task("Read the RFP and decide every sentence in Review", owner="A. Rivera", due=soon(3), who="sample")
        nid = rec.add_note("Does the Volume II page limit include the resumes?", question=True, who="sample")
        rec.update_note(nid, assignee="A. Rivera", who="sample")
        rec.add_note("Sample effort: everything here is made up. Try anything; archive it from All Efforts when done.", who="sample")
        Q.add(rec, "Will the Government accept thermal analysis results in Excel format?", "", doc=os.path.basename(copied[0]),
              section="L", category="Technical", owner="J. Garcia", who="sample")
        F.add_factor(rec, "Technical Approach", importance="Significantly more important")
        F.add_factor(rec, "Management Approach", importance="More important")
        F.add_hot(rec, "Thermal margin under worst-case loads", quote="The Government places emphasis on thermal margin.")
        TH.add(rec, "Flight-proven thermal design lowers risk to orbit",
               "Our design has flown on four missions with margin to spare, so the Government carries less schedule risk.",
               discriminator="The only design with on-orbit thermal data at this power class",
               proof=["Four missions, zero thermal anomalies", "Test data at 120% of worst-case load"],
               sections=["1.1 Thermal Design", "1.2 Risk Management"], who="sample")
        DL.add(rec, "Volume I Technical", kind="Volume", owner="J. Garcia", limit="20 pages", who="sample")
        DL.add(rec, "Volume II Management", kind="Volume", owner="M. Chen", limit="15 pages", who="sample")
        diag.activity("sample_effort_made")
    except Exception:
        diag.swallowed()
        copied = []
    host.go("home")
    if read and copied:
        try:
            host.read_page.read(copied, host.out_path("compliance_matrix"), identities="suggested", start="typed")
        except Exception:
            diag.swallowed()
    host.toast(f"{made}: a fictional effort to learn on. Its RFP is being read into Review now.")
    return made
