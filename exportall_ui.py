"""Export all (2.31.0): every feature's outputs for the open effort in one folder.

Each feature keeps its own export; this one writes them together into a dated folder: the compliance matrix, the
coverage report, the Word outline and the setup documents; the acronym lists (Word and Excel); the QA/QC report and
its acronym lists; the keyword list. The person ticks what to include (everything available starts ticked).
Reached from File > Export all and from Effort home. Nothing leaves this PC.
"""
import datetime, os, re
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import diag

PARTS = (("status", "Effort status (Word)"), ("deliverables", "Deliverables checklist (Excel)"), ("requirements", "Submission requirements and their history (Excel)"),
         ("versions", "Customer document version history (Excel)"), ("matrix", "Compliance matrix (Excel)"), ("coverage", "Compliance coverage report (Word)"),
         ("setup", "Response Setup (Word)"),
         ("acronyms", "Acronym lists (Word and Excel)"), ("qaqc", "QA/QC report (Excel) and its acronym lists"),
         ("keywords", "Keyword list (Excel)"))


def _safe(s):
    return re.sub(r"[^A-Za-z0-9 _.-]+", "_", s or "").strip().replace(" ", "_") or "Effort"


class ExportAllMixin:
    def _xa_matrix(self):
        """A fresh copy of this effort's compliance matrix (saved first if it has unsaved changes), or None."""
        import compliance as C
        M = getattr(self, "matrix", None)
        if M is not None and getattr(M, "pending", False):
            try:
                self._c_save_now()
            except Exception:
                diag.swallowed()
        path = M.path if M is not None else (self.ws.get("compliance_path", "") if getattr(self, "ws", None) is not None else "")
        if not path or not os.path.isfile(path):
            return None
        try:
            return C.Matrix(path).load()
        except Exception:
            diag.swallowed()
            return None

    def export_all_available(self):
        """{part: (available, why not)} for the open effort."""
        L = getattr(self, "effort", None)
        M = self._xa_matrix()
        r = getattr(self, "volume_report", None)
        kws = [k for k in (L.keywords if L is not None else []) if k.get("Status") == "Keep"]
        lib = self.doclib() if hasattr(self, "doclib") else None
        return {
            "deliverables": (L is not None and hasattr(self, "effrec") and bool(__import__("deliverables").items(self.effrec())) if L is not None else False,
                             "no deliverables yet"),
            "status": (L is not None and hasattr(self, "status_export"), "no effort open"),
            "requirements": (bool(lib and lib.docs) and bool(self.subreg().rows(include_hidden=True)) if lib else False,
                             "no submission requirements found yet"),
            "versions": (bool(lib and lib.docs), "no customer documents in the history yet"),
            "matrix": (M is not None, "no compliance matrix for this effort"),
            "coverage": (M is not None and bool(M.items), "no compliance matrix for this effort"),
            "setup": (M is not None and bool(M.outline), "the matrix has no outline yet"),
            "acronyms": (L is not None and bool(L.order), "the effort list is empty"),
            "qaqc": (bool(r), "QA/QC has not been run in this session"),
            "keywords": (bool(kws), "no keywords marked Keep"),
        }

    def export_all(self, folder=None, picks=None):
        """Write the chosen parts into <folder>/<effort>_Export_<date>. Returns (subfolder, [files], [problems])."""
        import compliance as C, setupdoc as SD, volcheck as V
        L = getattr(self, "effort", None)
        if L is None:
            return None
        avail = self.export_all_available()
        picks = [p for p in (picks or [k for k, _l in PARTS]) if avail.get(p, (False,))[0]]
        if not picks:
            return None
        stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        sub = os.path.join(folder, f"{_safe(L.name)}_Export_{stamp}")
        os.makedirs(sub, exist_ok=True)
        made, problems = [], []
        M = self._xa_matrix() if any(p in picks for p in ("matrix", "coverage", "setup")) else None
        stem = _safe(M.name) if M is not None else ""
        try:
            if "matrix" in picks:
                src = M.path
                M.path = os.path.join(sub, os.path.basename(src))
                M.save()
                made.append(M.path)
            if "coverage" in picks:
                p = os.path.join(sub, f"{stem}_RFP_Coverage.docx"); C.write_coverage_docx(M, p); made.append(p)
            if "setup" in picks:
                made += SD.export(M, sub)          # the export record stays with this copy, not the working matrix
        except PermissionError:
            problems.append("A compliance file with the same name is open. Close it and export again.")
        if "acronyms" in picks:
            try:
                made += self.export_effort_lists(folder=sub) or []
            except Exception:
                diag.swallowed(); problems.append("The acronym lists could not be written.")
        if "qaqc" in picks:
            r = self.volume_report
            try:
                p = os.path.join(sub, f"{_safe(L.name)}_QAQC_Report.xlsx"); V.write_excel(r, p, L.name); made.append(p)
                for v in r["volumes"]:
                    p = os.path.join(sub, _safe(os.path.splitext(v)[0]) + "_Acronym_List.docx")
                    V.write_docx([(x["term"], x["definition"]) for x in r["lists"][v]], p); made.append(p)
            except Exception:
                diag.swallowed(); problems.append("The QA/QC report could not be written.")
        if "deliverables" in picks:
            try:
                p = os.path.join(sub, f"{_safe(L.name)}_Deliverables.xlsx"); self.dl_export(p); made.append(p)
            except Exception:
                diag.swallowed(); problems.append("The deliverables checklist could not be written.")
        if "status" in picks:
            try:
                p = os.path.join(sub, f"{_safe(L.name)}_Effort_Status.docx"); self.status_export(p); made.append(p)
            except Exception:
                diag.swallowed(); problems.append("The effort status could not be written.")
        if "requirements" in picks:
            try:
                p = os.path.join(sub, f"{_safe(L.name)}_Submission_Requirements.xlsx"); self.req_export(p); made.append(p)
            except Exception:
                diag.swallowed(); problems.append("The submission requirements could not be written.")
        if "versions" in picks:
            try:
                p = os.path.join(sub, f"{_safe(L.name)}_Customer_Document_Versions.xlsx"); self.sub_export_history(p); made.append(p)
            except Exception:
                diag.swallowed(); problems.append("The version history could not be written.")
        if "keywords" in picks:
            try:
                p = os.path.join(sub, f"{_safe(L.name)}_Keywords.xlsx"); self.kw_export(p, keep_only=True); made.append(p)
            except Exception:
                diag.swallowed(); problems.append("The keyword list could not be written.")
        diag.activity("export_all", files=len(made), n=len(picks))
        return sub, made, problems

    def export_all_dialog(self):
        """Pick what to include (everything available ticked), choose a folder, write them all."""
        L = getattr(self, "effort", None)
        if L is None:
            messagebox.showinfo("Export all", "Open an effort first (Effort box at the top).", parent=self); return None
        avail = self.export_all_available()
        w = ctk.CTkToplevel(self); w.title("Export all"); w.geometry("600x480"); w.after(150, w.lift)
        ctk.CTkLabel(w, text=f"Everything for {L.name} in one dated folder. Each feature also keeps its own export.",
                     wraplength=560, justify="left", anchor="w").pack(fill="x", padx=14, pady=(12, 8))
        vars_ = {}
        for key, label in PARTS:
            ok, why = avail[key]
            vars_[key] = tk.BooleanVar(value=ok)
            row = ctk.CTkFrame(w, fg_color="transparent"); row.pack(fill="x", padx=14, pady=2)
            cb = ctk.CTkCheckBox(row, text=label, variable=vars_[key], width=10)
            cb.pack(side="left")
            if not ok:
                cb.configure(state="disabled")
                ctk.CTkLabel(row, text=f"({why})", text_color=("#64748B", "#94A3B8")).pack(side="left", padx=8)
        ctk.CTkLabel(w, text="The files hold customer content: keep them on this PC or SharePoint.", anchor="w",
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=14, pady=(10, 0))

        def go():
            picks = [k for k, v in vars_.items() if v.get()]
            if not picks:
                return
            folder = filedialog.askdirectory(parent=w, title="Folder for the export",
                                             initialdir=os.path.dirname(L.path) or None)
            if not folder:
                return
            res = self.export_all(folder, picks)
            w.destroy()
            if not res:
                return
            sub, made, problems = res
            messagebox.showinfo("Export all", f"Saved {len(made)} file(s) in:\n{sub}"
                                + ("\n\n" + "\n".join(problems) if problems else ""), parent=self)

        bar = ctk.CTkFrame(w, fg_color="transparent"); bar.pack(fill="x", side="bottom", padx=14, pady=12)
        ctk.CTkButton(bar, text="Export", fg_color="#0F766E", command=go).pack(side="right")
        ctk.CTkButton(bar, text="Cancel", fg_color="#475569", command=w.destroy).pack(side="right", padx=6)
        w.api = {"vars": vars_, "go": go}
        return w
