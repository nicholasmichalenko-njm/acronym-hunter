"""The app shell (2.32.0): one feature at a time.

A dark rail on the left lists the features in work order: Effort home, Compliance, Acronyms, QA/QC, Keywords.
Only the open feature's tools show. Across the top, the feature's steps (done steps green, the current step blue)
and that step's actions; each feature ends in its own Export step. One status line at the bottom.
The compliance matrix lives inside the main window (no separate window).
"""
import os
import tkinter as tk
import customtkinter as ctk
import diag

FEATURES = (("home", "Effort home"), ("submission", "Submission"), ("compliance", "Compliance"), ("acronyms", "Acronyms"), ("qaqc", "QA/QC"),
            ("keywords", "Keywords"))
STEPS = {
    "home": (("overview", "Overview"),),
    "submission": (("requirements", "Requirements"), ("deliverables", "Deliverables"), ("documents", "Documents"), ("impact", "Impact"), ("compare", "Compare"), ("export", "Export")),  # 2.39.0; Impact 2.42.0
    "compliance": (("read", "Read RFP"), ("outline", "Structure"), ("decide", "Assign"),
                   ("prove", "Prove"), ("export", "Export")),             # 2.36.0: Assign places as it decides
    "acronyms": (("scan", "Scan"), ("review", "Review"), ("approve", "Define and approve"), ("export", "Export")),
    "qaqc": (("check", "Check Word files"), ("export", "Export")),
    "keywords": (("decide", "Collect and decide"), ("export", "Export")),
}
COMP_TABS = {"read": "Read RFP", "decide": "Requirements", "outline": "Outline", "place": "Place", "prove": "Prove",
             "export": "Export"}
AI_SECTION = {"submission": "EFFORT", "compliance": "COMPLIANCE", "acronyms": "SCAN", "qaqc": "EFFORT", "keywords": "EFFORT", "home": "EFFORT"}
NEEDS_EFFORT = {("submission", "requirements"), ("submission", "deliverables"), ("submission", "documents"), ("submission", "impact"), ("submission", "compare"), ("submission", "export"), ("acronyms", "approve"), ("qaqc", "check"), ("qaqc", "export"), ("keywords", "decide"), ("keywords", "export")}

RAIL_BG = ("#0F172A", "#0B1220")
RAIL_ON = "#1E3A8A"
PILL = {"on": ("#1E3A8A", "#FFFFFF"), "done": ("#DCFCE7", "#14532D"), "todo": ("#F1F5F9", "#475569")}


class EmbeddedWindow(ctk.CTkFrame):
    """The compliance matrix as a frame in the main window. It answers the window calls the compliance code makes
    (title, geometry, lift, protocol...) so the same code runs either way."""

    def title(self, *_a):
        return ""

    def geometry(self, *_a):
        return ""

    def deiconify(self):
        return None

    def lift(self, *_a):
        return None

    def protocol(self, *_a):
        return None

    def state(self, *_a):
        return "normal"

    def transient(self, *_a):
        return None


class ShellMixin:
    # ------------------------------------------------------------ build
    def shell_build_rail(self, side):
        """The feature rail, in work order, with a one-line status under each feature."""
        side.configure(fg_color=RAIL_BG)
        ctk.CTkLabel(side, text="WORK IN ORDER", font=("Segoe UI", 10, "bold"), text_color="#94A3B8",
                     anchor="w").pack(fill="x", padx=18, pady=(16, 6))
        self._rail = {}
        for i, (key, name) in enumerate(FEATURES, 1):
            b = ctk.CTkButton(side, text=f"{i:02d}   {name}", anchor="w", height=56, corner_radius=8,
                              font=("Segoe UI", 14, "bold"), fg_color="transparent", hover_color="#1E293B",
                              text_color="#E2E8F0", command=lambda k=key: self.shell_go(k))
            b.pack(fill="x", padx=10, pady=(2, 0))
            sub = ctk.CTkLabel(side, text="", font=("Segoe UI", 11), text_color="#94A3B8", anchor="w", height=14)
            sub.pack(fill="x", padx=50, pady=(0, 4))
            sub.bind("<Button-1>", lambda _e, k=key: self.shell_go(k))
            diag.register(b, f"rail_{key}")
            self._rail[key] = (b, sub)
        self.shell_feature, self.shell_step = "acronyms", "scan"
        self._shell_last = {k: STEPS[k][0][0] for k, _n in FEATURES}

    def shell_build_strip(self, M):
        """The step strip across the top of the work area: feature name, its AI and ML labels, its steps, actions."""
        self.strip = st = ctk.CTkFrame(M, corner_radius=0, fg_color=("#FFFFFF", "#111827"))
        st.pack(fill="x", side="top")
        self.strip_title = ctk.CTkLabel(st, text="", font=("Segoe UI", 18, "bold"))
        self.strip_title.pack(side="left", padx=(18, 8), pady=10)
        if hasattr(self, "rec_strip_build"):
            self.rec_strip_build(st)               # 2.40.0: days and hours to go, top right (packed early: it keeps its room)
        self.strip_badges = ctk.CTkFrame(st, fg_color="transparent", height=28)
        self.strip_badges.pack(side="left", padx=(0, 10))
        self._badge_rows = {}
        for key, _n in FEATURES:
            self._badge_rows[key] = self.ai_section_header(self.strip_badges, AI_SECTION[key], show_title=False) \
                if hasattr(self, "ai_section_header") else None
            if self._badge_rows[key] is not None:
                self._badge_rows[key].pack_forget()
        self.strip_pills = ctk.CTkFrame(st, fg_color="transparent", height=34)
        self.strip_pills.pack(side="left", pady=8)
        self.strip_act = ctk.CTkFrame(st, fg_color="transparent", height=34)
        self.strip_act.pack(side="right", padx=12)
        self._acts = {}
        if hasattr(self, "sub_bar_build"):
            self.sub_bar_build(M)                  # 2.39.0: due date, page limits, format, changes to review

    def shell_actions(self, feature, step):
        """The frame for one step's actions in the strip (made once, shown while that step is open)."""
        key = (feature, step)
        if key not in self._acts:
            self._acts[key] = ctk.CTkFrame(self.strip_act, fg_color="transparent", height=34)
        return self._acts[key]

    def shell_page(self, name):
        """A plain page in the work area (made once)."""
        if not hasattr(self, "_pages"):
            self._pages = {}
        if name not in self._pages:
            self._pages[name] = ctk.CTkFrame(self.main, fg_color="transparent")
        return self._pages[name]

    def shell_build_pages(self):
        """Pages for steps that are not one of the existing views: the overview, Scan, the Export steps, no effort."""
        self._page_overview()
        self._page_no_effort()
        self._page_scan()
        self._page_acronyms_export()
        self._page_qa_export()
        self._page_kw_export()
        self._page_compliance_actions()
        if hasattr(self, "_page_submission"):
            self._page_submission()

    # ------------------------------------------------------------ pages
    @staticmethod
    def _h(parent, text, sub=""):
        ctk.CTkLabel(parent, text=text, font=("Segoe UI", 20, "bold"), anchor="w").pack(fill="x", padx=6, pady=(14, 2))
        if sub:
            lab = ctk.CTkLabel(parent, text=sub, anchor="w", justify="left", wraplength=900, text_color=("#475569", "#94A3B8"))
            lab.pack(fill="x", padx=6, pady=(0, 10))
            return lab
        return None

    def _card(self, parent):
        c = ctk.CTkFrame(parent, corner_radius=12, fg_color=("#FFFFFF", "#1F2937"), border_width=1,
                         border_color=("#E2E8F0", "#334155"))
        c.pack(fill="x", padx=6, pady=6)
        return c

    def _page_overview(self):
        P = ctk.CTkScrollableFrame(self.shell_page("overview"), fg_color="transparent")   # fits small windows
        P.pack(fill="both", expand=True)
        self.ov_head = ctk.CTkLabel(P, text="", font=("Segoe UI", 20, "bold"), anchor="w")
        self.ov_head.pack(fill="x", padx=6, pady=(14, 2))
        self.ov_sub = ctk.CTkLabel(P, text="", anchor="w", justify="left", text_color=("#475569", "#94A3B8"))
        self.ov_sub.pack(fill="x", padx=6, pady=(0, 8))
        self.ov_next = ctk.CTkButton(P, text="", height=40, fg_color="#1E3A8A", font=("Segoe UI", 14, "bold"),
                                     command=lambda: self.shell_go(*self._ov_target))
        self.ov_next.pack(anchor="w", padx=6, pady=(0, 10))
        if hasattr(self, "rec_build_home"):
            self.rec_build_home(P)                 # 2.40.0: stage, gate goals, tasks, notes, timeline
        self._ov_target = ("acronyms", "scan")
        self.ov_rows = {}
        for key, name in FEATURES[1:]:
            c = self._card(P)
            ctk.CTkLabel(c, text=name, font=("Segoe UI", 15, "bold"), width=140, anchor="w").pack(side="left", padx=(16, 8), pady=12)
            lab = ctk.CTkLabel(c, text="", anchor="w", justify="left")
            lab.pack(side="left", fill="x", expand=True)
            ctk.CTkButton(c, text="Open", width=90, command=lambda k=key: self.shell_go(k)).pack(side="right", padx=12)
            self.ov_rows[key] = lab
        c = self._card(P)
        ctk.CTkLabel(c, text="Export all", font=("Segoe UI", 15, "bold"), width=140, anchor="w").pack(side="left", padx=(16, 8), pady=12)
        ctk.CTkLabel(c, text="Every feature's outputs for this effort in one dated folder (each feature also has its own Export step).",
                     anchor="w", justify="left").pack(side="left", fill="x", expand=True)
        self.btn_ov_xall = ctk.CTkButton(c, text="Export all...", width=110, fg_color="#0F766E",
                                         command=lambda: self.export_all_dialog())
        self.btn_ov_xall.pack(side="right", padx=12)

    def _page_no_effort(self):
        P = self.shell_page("noeffort")
        self.ne_head = ctk.CTkLabel(P, text="", font=("Segoe UI", 20, "bold"), anchor="w")
        self.ne_head.pack(fill="x", padx=6, pady=(14, 2))
        ctk.CTkLabel(P, text="This step keeps its work in an effort. Start one, or pick one in the Effort box at the top.",
                     anchor="w", text_color=("#475569", "#94A3B8")).pack(fill="x", padx=6, pady=(0, 10))
        ctk.CTkButton(P, text="Start an effort...", height=40, fg_color="#1E3A8A", font=("Segoe UI", 14, "bold"),
                      command=lambda: self.open_wizard()).pack(anchor="w", padx=6)

    def _page_scan(self):
        """Acronyms > Scan: what to read. The buttons the sidebar used to hold."""
        P = self.shell_page("scan")
        self._h(P, "Scan documents", "Pick Word, PDF, Excel or PowerPoint files, or a folder. Results open in Review.")
        row = ctk.CTkFrame(P, fg_color="transparent"); row.pack(fill="x", padx=6, pady=4)
        big = dict(height=44, font=("Segoe UI", 15, "bold"), width=180)
        self.btn_files = ctk.CTkButton(row, text="Select Files...", command=self.select_files, **big)
        self.btn_files.pack(side="left", padx=(0, 10))
        self.btn_folder = ctk.CTkButton(row, text="Scan Folder...", command=self.select_folder, **big)
        self.btn_folder.pack(side="left", padx=(0, 10))
        sec = dict(height=44, width=150, fg_color=("#E2E8F0", "#334155"), hover_color=("#CBD5E1", "#475569"),
                   text_color=("#0F172A", "#F1F5F9"), text_color_disabled=("#94A3B8", "#64748B"))
        self.btn_again = ctk.CTkButton(row, text="Scan Again", command=self.scan_again, state="disabled", **sec)
        self.btn_again.pack(side="left", padx=(0, 10))
        self.btn_project = ctk.CTkButton(row, text="Project", command=self.show_project_menu, **sec)
        self.btn_project.pack(side="left")
        self.project_menu = tk.Menu(self, tearoff=0)
        self.lbl_project = ctk.CTkLabel(P, text="", font=("Arial", 13, "bold"), text_color="#1E3A8A", anchor="w")
        self.lbl_project_anchor = ctk.CTkFrame(P, fg_color="transparent", height=2)
        self.lbl_project_anchor.pack(fill="x")
        self.lbl_scan_last = ctk.CTkLabel(P, text="", anchor="w", justify="left", text_color=("#475569", "#94A3B8"))
        self.lbl_scan_last.pack(fill="x", padx=6, pady=(10, 4))
        self._h(P, "Also", "")
        more = ctk.CTkFrame(P, fg_color="transparent"); more.pack(fill="x", padx=6)
        self.btn_add = ctk.CTkButton(more, text="Add Item...", command=self.open_add_item, **sec)
        self.btn_add.pack(side="left", padx=(0, 10))
        self.btn_client = ctk.CTkButton(more, text="Client Lists...", command=self.open_client_lists, **sec)
        self.btn_client.pack(side="left", padx=(0, 10))
        self.btn_tools = ctk.CTkButton(more, text="Tools", command=self.show_tools_menu, **sec)
        self.btn_tools.pack(side="left", padx=(0, 10))
        self.btn_improve_top = ctk.CTkButton(more, text="Improve Reading...", command=self.open_improve, **sec)
        self.tools_menu = tk.Menu(self, tearoff=0)
        self.btn_db = self.btn_know = self.btn_fixes = self.btn_trainer = None

    def _page_acronyms_export(self):
        P = self.shell_page("acr_export")
        self._h(P, "Export acronyms", "The effort's list for the proposal, or the scan results.")
        sec = dict(height=40, width=260, anchor="w")
        rows = (("Acronym list for the proposal (pick columns, volumes, format)...", lambda: self.export_picker(), "btn_xa_pick"),
                ("Acronym lists, Word and Excel (whole effort or per volume)...", lambda: self.export_effort_lists_ui(), "btn_xa_lists"),
                ("Sheets for approvals (Needs author, Conflicts, Approved, All)...", lambda: self.export_effort(), "btn_xa_appr"),
                ("Scan results as CSV...", lambda: self.export_csv(), "btn_export"))
        for text, cmd, attr in rows:
            b = ctk.CTkButton(P, text=text, command=cmd, **sec)
            b.pack(anchor="w", padx=6, pady=4)
            setattr(self, attr, b)
        self.btn_export.configure(state="disabled")

    def _page_qa_export(self):
        P = self.shell_page("qa_export")
        self._h(P, "Export QA/QC", "The last QA/QC check of our Word deliverables.")
        for text, cmd in (("QA/QC report (Excel)...", lambda: self.export_volume_report()),
                          ("Acronym lists for Word (one per volume)...", lambda: self.export_volume_lists())):
            ctk.CTkButton(P, text=text, command=cmd, height=40, width=260, anchor="w").pack(anchor="w", padx=6, pady=4)
        self.lbl_qa_export = ctk.CTkLabel(P, text="", anchor="w", text_color=("#475569", "#94A3B8"))
        self.lbl_qa_export.pack(fill="x", padx=6, pady=8)

    def _page_kw_export(self):
        P = self.shell_page("kw_export")
        self._h(P, "Export keywords", "Excel or CSV in the SharePoint columns: Keep only, or Keep and Proposed.")
        ctk.CTkButton(P, text="Keyword list...", command=lambda: self.kw_export_dialog(), height=40, width=260,
                      anchor="w").pack(anchor="w", padx=6, pady=4)

    def _page_compliance_actions(self):
        """Each compliance step's actions in the strip (the old window's toolbar, split by step)."""
        A = dict(height=30, width=10)
        act = self.shell_actions("compliance", "read")
        for text, cmd, color in (("New from RFP files...", self.compliance_new, "#9A3412"), ("Open matrix...", self.compliance_open, None),
                                 ("Add RFP files...", self.compliance_add_files, None),
                                 ("Re-read RFP (amendment)...", self.compliance_reread, None),
                                 ("Amendment changes...", self.compliance_changes, None),
                                 ("Text check...", self.compliance_text_check, "#15803D")):
            kw = dict(A); kw.update(fg_color=color) if color else None
            ctk.CTkButton(act, text=text, command=cmd, **kw).pack(side="left", padx=3)
        act = self.shell_actions("compliance", "decide")
        ctk.CTkButton(act, text="Compliance word style...", command=self.compliance_word_style, **A).pack(side="left", padx=3)
        ctk.CTkButton(act, text="Save", command=self.compliance_save, fg_color="#0F766E", **A).pack(side="left", padx=3)
        act = self.shell_actions("compliance", "export")
        ctk.CTkButton(act, text="Save", command=self.compliance_save, fg_color="#0F766E", **A).pack(side="left", padx=3)

    # ------------------------------------------------------------ status line
    def shell_build_statusbar(self, M):
        self.statusbar = ctk.CTkFrame(M, corner_radius=0, fg_color=("#FFFFFF", "#111827"), height=26)
        self.statusbar.pack(side="bottom", fill="x")
        return self.statusbar

    # ------------------------------------------------------------ navigation
    def _shell_frames(self):
        fr = [getattr(self, n, None) for n in ("scan_view", "home_view", "kw_view", "qa_view")]
        fr += list(getattr(self, "_pages", {}).values())
        cw = getattr(self, "_cwin", None)
        if cw is not None and cw.winfo_exists() and isinstance(cw, EmbeddedWindow):
            fr.append(cw)
        return [f for f in fr if f is not None]

    def _shell_target(self, f, s):
        if self.effort is None and (f, s) in NEEDS_EFFORT:
            self.ne_head.configure(text=f"{dict(FEATURES)[f]}: open an effort first")
            return self.shell_page("noeffort")
        if f == "home":
            return self.shell_page("overview") if self.effort is not None else self.shell_page("noeffort")
        if f == "compliance":
            win = self._comp_ensure()
            try:
                win.tabs.set(COMP_TABS[s])
            except Exception:
                diag.swallowed()
            return win
        if f == "submission":
            return self.shell_page({"requirements": "sub_reqs", "deliverables": "sub_deliv", "documents": "sub_docs", "impact": "sub_impact", "compare": "sub_compare", "export": "sub_export"}[s])
        return {("acronyms", "scan"): self.shell_page("scan"), ("acronyms", "review"): self.scan_view,
                ("acronyms", "approve"): self.home_view, ("acronyms", "export"): self.shell_page("acr_export"),
                ("qaqc", "check"): getattr(self, "qa_view", None), ("qaqc", "export"): self.shell_page("qa_export"),
                ("keywords", "decide"): getattr(self, "kw_view", None), ("keywords", "export"): self.shell_page("kw_export")}[(f, s)]

    def shell_go(self, feature, step=None, save=True):
        """Open one feature at one step (its last step when none is given)."""
        if feature not in STEPS:
            return
        steps = [k for k, _l in STEPS[feature]]
        if feature == "acronyms" and step is None and self.effort is not None and self._shell_last.get("acronyms") == "scan":
            step = "review"                    # 2.38.0: with an effort open, straight to what was found in its documents
        if feature == "submission" and step is None and self._shell_last.get("submission") == "requirements":
            try:                               # 2.39.0: nothing read yet: start where customer documents are added
                lib = self.doclib()
                if lib is not None and not lib.docs:
                    step = "documents"
            except Exception:
                diag.swallowed()
        step = step if step in steps else self._shell_last.get(feature, steps[0])
        if feature == "home" and self.effort is None:
            self.ne_head.configure(text="No effort open")
        target = self._shell_target(feature, step)
        self.shell_feature, self.shell_step = feature, step
        self._shell_last[feature] = step
        for f in self._shell_frames():
            if f is not target and f.winfo_manager():
                f.pack_forget()
        if target is not None and not target.winfo_manager():
            if target is self.scan_view:
                target.pack(fill="both", expand=True)
            else:
                target.pack(fill="both", expand=True, padx=15, pady=(4, 10))
        legacy = {("acronyms", "review"): "Scan review", ("acronyms", "approve"): "Effort list (home)",
                  ("keywords", "decide"): "Keywords", ("qaqc", "check"): "QA/QC"}.get((feature, step))
        if hasattr(self, "view_var"):
            self.view_var.set(legacy or f"{feature}:{step}")
        if (feature, step) == ("acronyms", "approve") and self.effort is not None:
            self.home_refresh()
        elif (feature, step) == ("acronyms", "review"):
            self.rv_scan_offer()
        elif feature == "keywords" and step == "decide" and self.effort is not None:
            self.kw_refresh()
        elif feature == "home":
            self.shell_overview_refresh()
        elif feature == "submission":
            try:
                if step == "requirements":
                    self.req_refresh()
                elif step == "deliverables" and hasattr(self, "dl_refresh"):
                    self.dl_refresh()
                if step == "documents":
                    self.sub_refresh()
                elif step == "impact" and hasattr(self, "impact_refresh"):
                    self.impact_refresh()
                elif step == "compare":
                    self.cmp_fill()
            except Exception:
                diag.swallowed()
        elif feature == "compliance":
            try:
                if step == "decide" and hasattr(self, "_cp_sync"):
                    self._cp_sync()
                    sel = self._c_selected()
                    if not sel and self.matrix is not None and self.matrix.items:
                        self.compliance_next_undecided()
                    self.after(50, lambda: self._cwin is not None and hasattr(self._cwin, "cp_text") and self._cwin.cp_text.focus_set())
                elif step == "place" and hasattr(self, "pl_refresh"):
                    self.pl_refresh()
                elif step == "prove" and hasattr(self, "pv_refresh"):
                    self.pv_refresh()
            except Exception:
                diag.swallowed()
        self._shell_strip()
        self._shell_rail_style()
        for key, (_b, sub) in self._rail.items():             # the rail's status lines, now (not at the next tick)
            t = self.shell_status(key)
            if sub.cget("text") != t:
                sub.configure(text=t)
        diag.menu(f"view_{feature}_{step}")         # the step opened (internal names only)
        if save and hasattr(self, "resume_changed"):
            self.resume_changed()

    def effort_doc_paths(self):
        """The open effort's documents: its customer documents and our volumes, [(path, kind)] (2.38.0)."""
        if self.effort is None or not hasattr(self, "kw_sources"):
            return []
        return list(self.kw_sources())

    def rv_scan_offer(self):
        """Acronyms > Review with an effort open: one button scans the effort's documents (customer and ours); shown
        while nothing has been found yet. Returns the offer text, '' when hidden."""
        bar = getattr(self, "rv_scanbar", None)
        if bar is None:
            return ""
        docs = self.effort_doc_paths() if self.effort is not None and not self.results and not self.busy() else []
        if not docs:
            if bar.winfo_manager():
                bar.pack_forget()
            return ""
        nc = sum(1 for _p, k in docs if k == "customer")
        text = f"Nothing found yet for {self.effort.name}. Its documents: {nc} customer, {len(docs) - nc} ours."
        self.rv_scanlbl.configure(text=text)
        self.btn_rv_scan.configure(text=f"Scan this effort's {len(docs)} document{'s' if len(docs) != 1 else ''}")
        if not bar.winfo_manager():
            bar.pack(fill="x", padx=15, pady=(0, 6), before=self.rv_filters)
        return text

    def acronyms_effort_scan(self, force=False):
        """Scan the open effort's documents (customer documents and our volumes) without picking files. Returns the
        number of files started, 0 when nothing was started."""
        if self.effort is None or (self.results and not force) or self.busy():
            return 0
        docs = self.effort_doc_paths()
        if not docs:
            self.status.configure(text="This effort has no documents yet: add customer documents (Start an effort, or Submission) "
                                       "and our volumes (Effort > Volumes).")
            return 0
        if getattr(self, "rv_scanbar", None) is not None and self.rv_scanbar.winfo_manager():
            self.rv_scanbar.pack_forget()
        nc = sum(1 for _p, k in docs if k == "customer")
        self.status.configure(text=f"Scanning this effort's documents: {nc} customer, {len(docs) - nc} ours...")
        diag.activity("acronyms_effort_scan", files=len(docs))
        self.start_batch([p for p, _k in docs])
        return len(docs)

    def _shell_done(self, f, s):
        """Whether a step has work done (green pill)."""
        try:
            if f == "acronyms":
                if s == "scan":
                    return bool(self.results)
                if s == "review":
                    return self.effort is not None and bool(self.effort.rows)
                if s == "approve":
                    return self.effort is not None and bool(self.effort.rows) and all(
                        r["Status"] in ("Approved", "Rejected") for r in self.effort.rows.values())
            if f == "compliance" and self.matrix is not None:
                c = self.matrix.counts()
                return {"read": bool(self.matrix.items), "outline": bool(self.matrix.outline),
                        "decide": c["Keep"] + c["Context"] > 0 and not c["needs_home"]}.get(s, False)
            if f == "qaqc" and s == "check":
                return bool(getattr(self, "volume_report", None))
            if f == "submission" and s == "requirements":
                reg = self.subreg()
                rows = reg.rows() if reg else []
                return bool(rows) and not any(r["to_review"] for r in rows)
            if f == "submission" and s == "documents":
                lib = self.doclib()
                return bool(lib and lib.docs) and not lib.counts()["unreviewed"]
            if f == "submission" and s == "impact":
                lib = self.doclib()
                return bool(lib and any(len(d["versions"]) > 1 for d in lib.docs)) and not lib.counts()["unreviewed"]
        except Exception:
            diag.swallowed()
        return False

    def _shell_strip(self):
        f, s = self.shell_feature, self.shell_step
        self.strip_title.configure(text=dict(FEATURES)[f])
        for key, row in self._badge_rows.items():
            if row is not None:
                if key == f and not row.winfo_manager():
                    row.pack(side="left")
                elif key != f and row.winfo_manager():
                    row.pack_forget()
        for w in self.strip_pills.winfo_children():
            w.destroy()
        if len(STEPS[f]) > 1:
            for i, (k, label) in enumerate(STEPS[f], 1):
                kind = "on" if k == s else "done" if self._shell_done(f, k) else "todo"
                bg, fg = PILL[kind]
                txt = f"{i} {label}" + ("  ✓" if kind == "done" else "")
                b = ctk.CTkButton(self.strip_pills, text=txt, height=30, width=10, corner_radius=15, fg_color=bg,
                                  text_color=fg, hover_color=("#CBD5E1" if kind != "on" else "#1E40AF"),
                                  font=("Segoe UI", 13, "bold" if kind == "on" else "normal"),
                                  command=lambda k=k: self.shell_go(f, k))
                b.pack(side="left", padx=3)
        for key, fr in self._acts.items():
            if key == (f, s):
                if not fr.winfo_manager():
                    fr.pack(side="right")
            elif fr.winfo_manager():
                fr.pack_forget()

    def _shell_rail_style(self):
        for key, (b, _sub) in self._rail.items():
            b.configure(fg_color=RAIL_ON if key == self.shell_feature else "transparent",
                        text_color="#FFFFFF" if key == self.shell_feature else "#CBD5E1")

    def shell_status(self, key):
        """The one-line status under a feature in the rail."""
        L = self.effort
        try:
            if key == "home":
                return L.name[:28] if L is not None else "No effort open"
            if key == "submission":
                lib = self.doclib() if hasattr(self, "doclib") else None
                if lib is None or not lib.docs:
                    return "No customer documents yet"
                c = lib.counts()
                if c["unreviewed"]:
                    return f"{c['unreviewed']} change{'s' if c['unreviewed'] != 1 else ''} to review"
                reg = self.subreg()
                n = sum(1 for r in reg.rows() if r["to_review"]) if reg else 0
                return (f"{n} requirement{'s' if n != 1 else ''} changed" if n
                        else f"{c['docs']} documents, {c['versions']} versions")
            if key == "compliance":
                M = self.matrix
                if M is None or not M.items:
                    return "No matrix yet"
                c = M.counts()
                return f"{c['Keep']} requirements, {c['Context']} context"
            if key == "acronyms":
                if L is not None:
                    ok = sum(1 for r in L.rows.values() if r["Status"] == "Approved")
                    return f"{len(L.rows)} terms, {ok} approved"
                return f"{len(self.results)} found" if self.results else "Nothing scanned yet"
            if key == "qaqc":
                r = getattr(self, "volume_report", None)
                return f"{len(r.get('volumes', []))} file(s) checked" if r else "Word files only"
            if key == "keywords":
                if L is None:
                    return "Needs an effort"
                kw = L.keywords or []
                return f"{sum(1 for k in kw if k.get('Status') == 'Keep')} kept, {sum(1 for k in kw if k.get('Status') == 'Proposed')} proposed"
        except Exception:
            diag.swallowed()
        return ""

    def shell_tick(self):
        """Keep the rail's status lines and the pills current (cheap; every 1.5 seconds)."""
        try:
            for key, (_b, sub) in self._rail.items():
                t = self.shell_status(key)
                if sub.cget("text") != t:
                    sub.configure(text=t)
            sig = tuple(self._shell_done(self.shell_feature, k) for k, _l in STEPS[self.shell_feature])
            if sig != getattr(self, "_shell_sig", None):
                self._shell_sig = sig
                self._shell_strip()
            if self.shell_feature == "home":
                self.shell_overview_refresh()
            if hasattr(self, "sub_bar_refresh"):
                self.sub_bar_refresh()
            if hasattr(self, "rec_strip_refresh"):
                self.rec_strip_refresh()
        except Exception:
            diag.swallowed()
        self.after(1500, self.shell_tick)

    def shell_overview_refresh(self):
        L = self.effort
        if L is None or not hasattr(self, "ov_head"):
            return
        self.ov_head.configure(text=L.name)
        self.ov_sub.configure(text="  |  ".join(x for x in (L.client, L.solicitation, L.internal_no, os.path.basename(L.path)) if x))
        if hasattr(self, "rec_refresh"):
            self.rec_refresh()
        for key, lab in self.ov_rows.items():
            t = self.shell_status(key)
            if key == "submission" and hasattr(self, "req_summary_text"):      # 2.39.0: the Submission card
                more = self.req_summary_text()
                t = t + ("\n" + more.replace("  |  ", "\n") if more else "")
            lab.configure(text=t)
        M = self.matrix
        pend = []
        try:
            import impact as IM
            lib = self.doclib() if hasattr(self, "doclib") else None
            pend = IM.pending(lib) if lib is not None else []
        except Exception:
            diag.swallowed()
        if pend:                                     # 2.42.0: a new customer version comes first
            d, v = pend[0]
            self._ov_target, text = ("submission", "impact"), f"Next: Submission, review what {v['label']} of {d['name'][:40]} touched"
        elif M is None or not M.items:
            self._ov_target, text = ("compliance", "read"), "Next: Compliance, read the RFP"
        elif not M.outline:
            self._ov_target, text = ("compliance", "outline"), "Next: Compliance, set the response structure"
        elif not (M.counts()["Keep"] + M.counts()["Context"]):
            self._ov_target, text = ("compliance", "decide"), "Next: Compliance, assign requirements and context"
        elif not L.rows:
            self._ov_target, text = ("acronyms", "scan"), "Next: Acronyms, scan our documents"
        else:
            self._ov_target, text = ("acronyms", "approve"), "Next: Acronyms, define and approve"
        self.ov_next.configure(text=text)

    # ------------------------------------------------------------ compliance inside the window
    def _comp_ensure(self):
        cw = getattr(self, "_cwin", None)
        if cw is None or not cw.winfo_exists():
            self._comp_build()
        return self._cwin


class RhythmMixin:
    """One decision, then the next (2.32.0): the same rhythm in Acronyms > Review, Keywords and the QA/QC fix list."""

    def shell_bind_rhythm(self):
        tv = self.tree
        for k in ("a", "A"):
            tv.bind(f"<KeyPress-{k}>", lambda _e: (self.rv_add(), "break")[1])
        for k in ("x", "X"):
            tv.bind(f"<KeyPress-{k}>", lambda _e: (self.rv_reject(), "break")[1])
        tv.bind("<space>", lambda _e: (self.rv_next(), "break")[1])
        kt = getattr(self, "kw_tree", None)
        if kt is not None:
            for k, st in (("k", "Keep"), ("K", "Keep"), ("r", "Reject"), ("R", "Reject")):
                kt.bind(f"<KeyPress-{k}>", lambda _e, st=st: (self.kw_decide_next(st), "break")[1])
            kt.bind("<space>", lambda _e: (self._tree_next(kt), "break")[1])

    @staticmethod
    def _tree_next(tv):
        rows = list(tv.get_children())
        if not rows:
            return None
        sel = tv.selection()
        i = rows.index(sel[-1]) + 1 if sel and sel[-1] in rows else 0
        nxt = rows[min(i, len(rows) - 1)]
        tv.selection_set(nxt); tv.focus(nxt); tv.see(nxt)
        return nxt

    def rv_next(self):
        nxt = self._tree_next(self.tree)
        if nxt is not None:
            self.on_select(None)
        return nxt

    def rv_add(self):
        """A: add the selected term to the effort list (Include in DB with no effort), then the next one."""
        if not [t for t in self.tree.selection() if t in self.results]:
            return
        if self.effort is not None:
            self.add_to_effort()
        elif str(self.btn_save.cget("state")) == "normal":
            self.save_candidate()
        self.rv_next()

    def rv_reject(self):
        """X: not a term for this effort (Exclude with no effort), then the next one."""
        sel = [t for t in self.tree.selection() if t in self.results]
        if not sel:
            return
        if self.effort is not None:
            self.set_effort_status("Rejected")
        else:
            self.exclude_term()
        self.rv_next()

    def rv_more_menu(self, widget=None):
        """The rarer Review actions in one menu: Include in DB, Exclude everywhere, Omit, Fix OCR."""
        m = tk.Menu(self, tearoff=0)
        for label, btn in (("Include in the database", self.btn_save), ("Exclude (all places, this scan)", self.btn_exc),
                           ("Omit (a name, not an acronym)...", getattr(self, "btn_effort_omit", None)),
                           ("Fix OCR", self.btn_ocr if self.advanced_on else None)):
            if btn is not None:
                m.add_command(label=label, command=btn.cget("command"), state=str(btn.cget("state")))
        w = widget or self.btn_rv_more
        try:
            m.tk_popup(w.winfo_rootx(), w.winfo_rooty() + w.winfo_height())
        finally:
            m.grab_release()
        return m

    def kw_decide_next(self, status):
        n = self.kw_set_status(status)
        self._tree_next(self.kw_tree)
        return n

    # ------------------------------------------------------------ QA/QC: worst first, one fix at a time
    def qa_next_fix(self):
        """Select the next row to fix (red) across First use, Banned words and Acronym list; returns (tab, row) or None."""
        win = getattr(self, "_volwin", None)
        if win is None or not win.winfo_exists() or not hasattr(win, "_trees"):
            return None
        order = [t for t in ("First use", "Banned words", "Acronym list") if t in win._trees]
        tabs = win._qa_tabs
        cur_tab = tabs.get() if tabs.get() in order else order[0] if order else None
        if cur_tab is None:
            return None
        start = order.index(cur_tab)
        for k in range(len(order) + 1):
            tab = order[(start + k) % len(order)]
            tv, data = win._trees[tab]
            rows = list(tv.get_children())
            sel = tv.selection()
            i = rows.index(sel[-1]) + 1 if k == 0 and sel and sel[-1] in rows else 0
            for iid in rows[i:]:
                if data.get(iid, {}).get("level") == "bad":
                    tabs.set(tab)
                    tv.selection_set(iid); tv.focus(iid); tv.see(iid)
                    r = data[iid]
                    self.status.configure(text=f"Fix: {r.get('term') or r.get('found', '')}  {r.get('state') or r.get('phrase', '')}"
                                               + (f"  ({r.get('loc') or r.get('where', '')})" if (r.get('loc') or r.get('where')) else ""))
                    return tab, r
        self.status.configure(text="✓ Nothing left to fix in this QA/QC check.")
        return None
