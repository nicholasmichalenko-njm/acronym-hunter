"""Export all in Qt (2.66.0): every feature's outputs for the open effort in one dated folder: effort status,
deliverables, submission requirements, customer document versions, the compliance matrix, coverage and Response Setup,
the acronym lists, the QA/QC report and the keyword list. Tick what to include (everything available starts ticked).
Nothing leaves the PC."""
import datetime, os
from PySide6.QtWidgets import QCheckBox, QFileDialog, QHBoxLayout, QVBoxLayout, QWidget
import diag
import effortfolders as EF
import exportall_ui as XA
from . import design as D


class ExportAllPage(QWidget):
    def __init__(self, host):
        super().__init__()
        self.setObjectName("page")
        self.host = host
        v = QVBoxLayout(self)
        v.setContentsMargins(D.SPACE["xl"], D.SPACE["l"], D.SPACE["xl"], D.SPACE["l"]); v.setSpacing(D.SPACE["m"])
        card = D.Card("What to include", "Each part is written as its own feature writes it, together in one dated folder.")
        self.boxes = {}
        for key, label in XA.PARTS:
            cb = QCheckBox(label); self.boxes[key] = cb; card.add(cb)
        v.addWidget(card)
        row = QHBoxLayout(); v.addLayout(row)
        row.addStretch(1)
        row.addWidget(D.button("Export all...", "primary", lambda: self.export()))
        self.result = D.label("", "muted"); v.addWidget(self.result)
        v.addStretch(1)

    # ------------------------------------------------------------ what each part needs
    def available(self):
        h = self.host
        out = {k: (False, "no effort open") for k, _l in XA.PARTS}
        if h.ws is None:
            return out
        import deliverables as DL
        import effortrec as R
        from .custdocs import Ctx
        c = Ctx(h)
        s = h.acronym_page.session
        L = s.effort if s is not None else None
        M = h.review.M if h.review is not None else None
        kws = [k for k in (L.keywords if L is not None else []) if k.get("Status") == "Keep"]
        out.update({
            "status": (True, ""),
            "deliverables": (bool(DL.items(R.Record(h.ws.root))), "no deliverables yet"),
            "requirements": (bool(c.reg.rows(include_hidden=True)), "no submission requirements found yet"),
            "versions": (bool(c.lib.docs), "no customer documents in the history yet"),
            "matrix": (M is not None, "no compliance matrix for this effort"),
            "coverage": (M is not None and bool(M.items), "no compliance matrix for this effort"),
            "setup": (M is not None and bool(M.outline), "the matrix has no outline yet"),
            "acronyms": (L is not None and bool(L.order), "the effort list is empty"),
            "qaqc": (bool(s is not None and s.volume_report), "QA/QC has not checked the drafts yet"),
            "keywords": (bool(kws), "no keywords marked Keep")})
        return out

    def refresh(self):
        h = self.host
        if h.ws is not None and h.acronym_page.session is None:
            h.acronym_page.load()
        self.setEnabled(h.ws is not None)
        av = self.available()
        for k, cb in self.boxes.items():
            ok, why = av[k]
            cb.setEnabled(ok); cb.setChecked(ok)
            cb.setToolTip("" if ok else f"Not available: {why}")
            label = dict(XA.PARTS)[k]
            cb.setText(label if ok else f"{label}  ({why})")

    # ------------------------------------------------------------ export
    def export(self, folder=None, picks=None):
        h = self.host
        if h.ws is None:
            return None
        if folder is None:
            folder = QFileDialog.getExistingDirectory(self, "Folder for the export", h.out_path("export_all") if h.effort_path else "")
            if not folder:
                return None
        av = self.available()
        picks = [p for p in (picks or [k for k, cb in self.boxes.items() if cb.isChecked()]) if av.get(p, (False,))[0]]
        if not picks:
            return None
        h.save_now()
        name = XA._safe(h.effort_name)
        sub = os.path.join(folder, f"{name}_Export_{datetime.datetime.now():%Y-%m-%d_%H%M}")
        os.makedirs(sub, exist_ok=True)
        made, problems = [], []

        def part(label, fn):
            try:
                out = fn()
                if out:
                    made.extend(out if isinstance(out, list) else [out])
            except PermissionError:
                problems.append(f"{label}: a file with the same name is open. Close it and export again.")
            except Exception:
                diag.swallowed()
                problems.append(f"{label} could not be written.")
        s = h.acronym_page.session
        if "status" in picks:
            part("The effort status", lambda: h.record_page.status_export(os.path.join(sub, f"{name}_Effort_Status.docx")))
        if "deliverables" in picks:
            part("The deliverables checklist", lambda: h.deliverables_page.refresh() or h.deliverables_page.export(os.path.join(sub, f"{name}_Deliverables.xlsx")))
        if "requirements" in picks:
            part("The submission requirements", lambda: h.requirements_page.refresh() and None or
                 h.requirements_page.export(os.path.join(sub, f"{name}_Submission_Requirements.xlsx")))
        if "versions" in picks:
            def versions():
                import docversions as DV
                from .custdocs import Ctx
                lib = Ctx(h).lib
                cmps = [(d, d["versions"][i - 1], d["versions"][i], DV.compare(lib.text(d["versions"][i - 1]), lib.text(d["versions"][i])))
                        for d in lib.docs for i in range(1, len(d["versions"]))]
                p = os.path.join(sub, f"{name}_Customer_Document_Versions.xlsx")
                DV.export_list(p, lib, compares=cmps)
                return p
            part("The version history", versions)
        if any(p in picks for p in ("matrix", "coverage", "setup")):
            def compliance():
                import compliance as C
                import setupdoc as SD
                M = C.Matrix(h.review.M.path).load()             # a fresh copy: the working matrix keeps its own export record
                out = []
                stem = XA._safe(M.name)
                if "matrix" in picks:
                    src = M.path
                    M.path = os.path.join(sub, os.path.basename(src)); M.save(); out.append(M.path)
                if "coverage" in picks:
                    p = os.path.join(sub, f"{stem}_RFP_Coverage.docx"); C.write_coverage_docx(M, p); out.append(p)
                if "setup" in picks:
                    import ctxdocs as CX
                    out += SD.export(M, sub, context=CX.section_context(self.host.ws.root))
                return out
            part("The compliance files", compliance)
        if "acronyms" in picks and s is not None:
            part("The acronym lists", lambda: s.export_effort_lists(folder=sub) or [])
        if "qaqc" in picks and s is not None:
            def qaqc():
                import volcheck as V
                r = s.volume_report
                out = [os.path.join(sub, f"{name}_QAQC_Report.xlsx")]
                V.write_excel(r, out[0], h.effort_name)
                for vol in r["volumes"]:
                    p = os.path.join(sub, XA._safe(os.path.splitext(vol)[0]) + "_Acronym_List.docx")
                    V.write_docx([(x["term"], x["definition"]) for x in r["lists"][vol]], p); out.append(p)
                return out
            part("The QA/QC report", qaqc)
        if "keywords" in picks and s is not None:
            def kws():
                p = os.path.join(sub, f"{name}_Keywords.xlsx"); s.kw_export(p, keep_only=True); return p
            part("The keyword list", kws)
        diag.activity("qt_export_all", files=len(made), n=len(picks))
        self.result.setText(f"{len(made)} file(s) written to {sub}" + ("\n" + "\n".join(problems) if problems else ""))
        h.toast(f"Export all: {len(made)} file(s)")
        return sub, made, problems
