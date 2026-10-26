"""Compliance matrix window (2.8.0): Compliance button. Rules gather every candidate requirement from the RFP with
its source; the person keeps or drops each one (K / D / U, S splits), builds or imports the proposal outline, maps the
keepers, and exports the Excel matrix (the working file itself) and an annotated Word outline. No language model.
"""
import datetime, hashlib, os, re, threading, zipfile
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
import diag
import compliance as C
import complearn as CL
import placelearn as PL
import cwords as CW

ALL = "All"
LEVEL_COLORS = {"Keep": "#E7F6EC", "Context": "#E0F2FE", "Drop": "#EEEEEE"}


def _eng():
    import app_gui
    return app_gui


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest().upper()


class ComplianceMixin:
    """Mixed into AcronymAppGUI."""

    def compliance_init(self, toolbar, button_kw):
        self.matrix = None
        self._cwin = None
        if toolbar is not None:
            self.btn_compliance = ctk.CTkButton(toolbar, text="Compliance Matrix...", command=self.open_compliance, **button_kw)
            self.btn_compliance.pack(fill="x", padx=8, pady=2)

    # ------------------------------------------------------------ window
    def open_compliance(self, show=True):
        """The compliance matrix, inside the main window (2.32.0). Returns its frame."""
        diag.activity("compliance_opened")
        if hasattr(self, "shell_go"):
            win = self._comp_ensure()
            if show:
                self.shell_go("compliance", "decide" if self.matrix is not None and self.matrix.items else None)
            return win
        return self._comp_build()

    def _comp_build(self):
        import shell_ui
        win = shell_ui.EmbeddedWindow(self.main, fg_color="transparent") if hasattr(self, "shell_go") else ctk.CTkToplevel(self)
        win.title("Compliance matrix")
        win.geometry("1400x820"); win.after(150, win.lift)
        diag.register(win, "compliance")
        self._cwin = win
        win.protocol("WM_DELETE_WINDOW", self._close_compliance)
        win.lbl = ctk.CTkLabel(win, text="", anchor="w", justify="left", wraplength=1360)
        win.lbl.pack(fill="x", padx=4, pady=(0, 2))
        tabs = ctk.CTkTabview(win); tabs.pack(fill="both", expand=True, padx=0, pady=(0, 4))
        win.tabs = tabs

        def _set_now(name, _t=tabs):
            """CTkTabview.set hides the other tabs 100 ms later; two quick sets then hide both. Hide them now."""
            if name not in _t._tab_dict:
                raise ValueError(f"no tab named {name!r}")
            _t._current_name = name
            _t._segmented_button.set(name)
            _t._set_grid_current_tab()
            _t._grid_forget_all_tabs(exclude_name=name)
        tabs.set = _set_now
        rd = tabs.add("Read RFP")
        rq = tabs.add("Requirements")
        flt = ctk.CTkFrame(rq, fg_color="transparent"); flt.pack(fill="x", pady=(0, 4))
        win.c_flt = flt
        win.f_dec = tk.StringVar(value=ALL); win.f_type = tk.StringVar(value=ALL); win.f_sug = tk.StringVar(value=ALL)
        win.f_map = tk.StringVar(value=ALL); win.f_q = tk.StringVar(); win.f_learn = tk.StringVar(value=ALL)
        for lab, var, vals in (("Decision", win.f_dec, [ALL, "Undecided", "Keep", "Context", "Drop"]), ("Type", win.f_type, [ALL] + list(C.TYPES)),
                               ("Suggested", win.f_sug, [ALL, "Keep", "Context", "Drop", "Review"]), ("Learned", win.f_learn, [ALL, "Keep", "Drop", "Review"]),
                               ("Outline", win.f_map, [ALL, "Needs a home", "Kept, not mapped", "Mapped"])):
            ctk.CTkLabel(flt, text=lab).pack(side="left", padx=(8, 3))
            ctk.CTkOptionMenu(flt, variable=var, values=vals, width=110, command=lambda _v: self._c_fill()).pack(side="left")
        ctk.CTkLabel(flt, text="Search").pack(side="left", padx=(12, 3))
        e = ctk.CTkEntry(flt, textvariable=win.f_q, width=200); e.pack(side="left")
        e.bind("<KeyRelease>", lambda _e: self._c_fill())
        win.btn_accept = ctk.CTkButton(flt, text="Accept suggestions (shown, undecided)", command=self.compliance_accept, width=10)
        win.btn_accept.pack(side="left", padx=10)
        body = ctk.CTkFrame(rq, fg_color="transparent"); body.pack(fill="both", expand=True)
        self._c_build_requirements(body)
        if hasattr(self, "_cp_build_decide"):            # 2.32.0: Decide in Page view, always
            self._cp_build_decide(rq, body)
        self._c_build_outline(tabs.add("Outline"))
        if hasattr(self, "_cp_build_place"):            # 2.32.0: Place, a second pass, one sentence at a time
            self._cp_build_place(tabs.add("Place"))
        self._s_build(tabs.add("Setup"))           # Setup Builder (2.13.0)
        pv = tabs.add("Prove")
        ex = tabs.add("Export")
        self._c_build_read(rd)
        self._c_build_prove(pv)
        self._c_build_export(ex)
        if hasattr(self, "shell_go"):
            try:
                tabs._segmented_button.grid_forget()      # the step strip at the top chooses the tab
            except Exception:
                diag.swallowed()
        last = self.ws.get("compliance_path", "") if getattr(self, "ws", None) is not None else ""   # per effort (2.11.0)
        if self.matrix is None and last and os.path.isfile(last):
            self._c_load(last, quiet=True)
        self._c_ai_state()
        self._c_refresh()
        tabs.set("Requirements" if self.matrix is not None and self.matrix.items else "Read RFP")
        return win

    def _c_build_read(self, fr):
        """Compliance > Read RFP: start a matrix from the RFP files, or open one."""
        win = self._cwin
        ctk.CTkLabel(fr, text="Read the RFP", font=("Segoe UI", 20, "bold"), anchor="w").pack(fill="x", padx=6, pady=(8, 2))
        ctk.CTkLabel(fr, text="Pick the instructions, evaluation criteria, SOW and attachments. Every sentence becomes a row, in "
                              "reading order, for you to decide in the next step.", anchor="w", justify="left", wraplength=900,
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=6, pady=(0, 10))
        row = ctk.CTkFrame(fr, fg_color="transparent"); row.pack(fill="x", padx=6)
        big = dict(height=44, font=("Segoe UI", 15, "bold"), width=200)
        ctk.CTkButton(row, text="New from RFP files...", command=self.compliance_new, fg_color="#9A3412", **big).pack(side="left", padx=(0, 10))
        ctk.CTkButton(row, text="Open a matrix...", command=self.compliance_open, **big).pack(side="left", padx=(0, 10))
        win.lbl_read = ctk.CTkLabel(fr, text="", anchor="w", justify="left", wraplength=900)
        win.lbl_read.pack(fill="x", padx=6, pady=(14, 4))
        ctk.CTkLabel(fr, text="Amendment? Re-read RFP keeps your decisions for unchanged sentences (buttons above, in the strip).",
                     anchor="w", text_color=("#475569", "#94A3B8")).pack(fill="x", padx=6)

    def _c_build_prove(self, fr):
        """Compliance > Prove: every sentence decided and placed; learning; owner, status and page."""
        win = self._cwin
        ctk.CTkLabel(fr, text="Prove nothing was missed", font=("Segoe UI", 20, "bold"), anchor="w").pack(fill="x", padx=6, pady=(8, 2))
        win.lbl_prove = ctk.CTkLabel(fr, text="", anchor="w", justify="left", font=("Segoe UI", 15))
        win.lbl_prove.pack(fill="x", padx=6, pady=(4, 8))
        win.prove_rows = ctk.CTkFrame(fr, fg_color="transparent"); win.prove_rows.pack(fill="x", padx=6)
        row = ctk.CTkFrame(fr, fg_color="transparent"); row.pack(fill="x", padx=6, pady=(12, 4))
        ctk.CTkButton(row, text="Save the coverage report (Word)...", command=self.compliance_coverage, fg_color="#1E3A8A",
                      height=40, font=("Segoe UI", 14, "bold")).pack(side="left")
        lr = ctk.CTkFrame(fr, fg_color="transparent"); lr.pack(fill="x", padx=6, pady=(14, 4))
        win.btn_learn = ctk.CTkButton(lr, text="Learn from decisions", command=self.compliance_learn, fg_color="#6D28D9", width=10)
        win.btn_learn.pack(side="left")
        win.team_var = tk.BooleanVar(value=bool(self.ws.get("team_learning", True)) if getattr(self, "ws", None) is not None else True)
        win.chk_team = ctk.CTkCheckBox(lr, text="Team learning", variable=win.team_var, command=self.compliance_team_toggle, width=10)
        win.chk_team.pack(side="left", padx=(12, 3))
        win.lbl_ai = ctk.CTkLabel(lr, text="", font=("Segoe UI", 11))
        win.lbl_ai.pack(side="left", padx=6)
        if hasattr(self, "_cp_build_details"):          # 2.32.0: owner, status and page are set here, not during triage
            self._cp_build_details(fr)

    def _c_goto_decide(self, iid):
        """Open Decide on one sentence."""
        if hasattr(self, "shell_go"):
            self.shell_go("compliance", "decide")
        if self._cwin.tv.exists(iid):
            self._cwin.tv.selection_set(iid); self._cwin.tv.focus(iid); self._cwin.tv.see(iid)
            self._c_show()

    def _c_build_export(self, fr):
        win = self._cwin
        ctk.CTkLabel(fr, text="Export the compliance work", font=("Segoe UI", 20, "bold"), anchor="w").pack(fill="x", padx=6, pady=(8, 2))
        ctk.CTkLabel(fr, text="Compliance words appear in your chosen style in every file (Compliance word style...).", anchor="w",
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=6, pady=(0, 10))
        for text, cmd in (("Matrix: open in Excel", self.compliance_excel),
                          ("Coverage report (Word)...", self.compliance_coverage),
                          ("Word outline with requirements...", self.compliance_word),
                          ("Setup documents for authors (Word)...", self.setup_export),
                          ("Setup changes since the last export...", self.setup_export_changes)):
            ctk.CTkButton(fr, text=text, command=cmd, height=40, width=300, anchor="w").pack(anchor="w", padx=6, pady=4)

    def _c_prove_refresh(self):
        win, M = self._cwin, self.matrix
        if win is None or not hasattr(win, "lbl_prove"):
            return
        for w in win.prove_rows.winfo_children():
            w.destroy()
        if M is None or not M.items:
            win.lbl_prove.configure(text="No matrix yet: start one on the Read RFP step.")
            if hasattr(win, "lbl_read"):
                win.lbl_read.configure(text="")
            return
        c = M.counts()
        und = c[""]
        home = c.get("needs_home", 0)
        kc = c["Keep"] + c["Context"]
        win.lbl_prove.configure(text=("\u2713 All " if not und else "") + f"{len(M.items) - und} of {len(M.items)} sentences have a decision"
                                + f"   |   {kc - home} of {kc} Keep and Context sentences have a home")
        hdr = ("File", "Sentences", "Keep", "Context", "Drop", "Undecided", "Placed", "Need a home")
        g = ctk.CTkFrame(win.prove_rows, fg_color="transparent"); g.pack(fill="x")
        for j, h in enumerate(hdr):
            ctk.CTkLabel(g, text=h, font=("Segoe UI", 12, "bold"), anchor="w").grid(row=0, column=j, sticky="w", padx=(0, 18))
        for i, r in enumerate(M.coverage(), 1):
            vals = (r["file"], r["total"], r["Keep"], r["Context"], r["Drop"], r[""], r["placed"], r["needs_home"])
            for j, v in enumerate(vals):
                ctk.CTkLabel(g, text=str(v), anchor="w", font=("Segoe UI", 12, "bold" if r["file"] == "Total" else "normal")
                             ).grid(row=i, column=j, sticky="w", padx=(0, 18))
        probs = C.context_problems(M.items)          # 2.33.0: Context with its requirement
        nctx = c["Context"]
        pr = ctk.CTkFrame(win.prove_rows, fg_color="transparent"); pr.pack(fill="x", pady=(10, 0))
        ctk.CTkLabel(pr, text=(f"\u2713 All {nctx} Context sentences are linked to their requirement and placed with it." if not probs
                               else f"{len(probs)} of {nctx} Context sentences are not with their requirement: "
                                    + "; ".join(f"{it['id']} ({why})" for it, why in probs[:3]) + (" ..." if len(probs) > 3 else "")),
                     anchor="w", justify="left", wraplength=900, font=("Segoe UI", 13, "bold" if probs else "normal"),
                     text_color=("#B45309", "#FBBF24") if probs else ("#15803D", "#86EFAC")).pack(side="left")
        if probs:
            ctk.CTkButton(pr, text="Show the first", width=10, command=lambda i=probs[0][0]["id"]: self._c_goto_decide(i)).pack(side="left", padx=10)
        win.prove_problems = probs
        nd = c.get("drafts", 0)                      # 2.35.0: drafts are not counted until committed
        dr = ctk.CTkFrame(win.prove_rows, fg_color="transparent"); dr.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(dr, text=("\u2713 No drafts: every decision is committed." if not nd else
                               f"{nd} draft decision{'s' if nd != 1 else ''} not committed yet: the counts above, Place and the "
                               "exports use committed decisions only."),
                     anchor="w", justify="left", wraplength=900, font=("Segoe UI", 13, "bold" if nd else "normal"),
                     text_color=("#B45309", "#FBBF24") if nd else ("#15803D", "#86EFAC")).pack(side="left")
        if nd:
            first = C.drafts(M.items)[0]["id"]
            ctk.CTkButton(dr, text="Show the first", width=10, command=lambda i=first: self._c_goto_decide(i)).pack(side="left", padx=10)
            ctk.CTkButton(dr, text=f"Commit all {nd}", width=10, fg_color="#15803D",
                          command=lambda: (self.compliance_commit(), self._c_prove_refresh())).pack(side="left")
        if hasattr(win, "lbl_read"):
            win.lbl_read.configure(text=f"Open matrix: {os.path.basename(M.path)}, {len(M.items)} sentences from "
                                        f"{len(M.sources)} file(s). Next: Decide.")
        if getattr(self, "shell_step", "") == "prove" and hasattr(self, "pv_refresh"):
            self.pv_refresh()

    def _close_compliance(self):
        if self.matrix is not None and self.matrix.pending:
            if not self._c_save_now():
                if not messagebox.askyesno("Compliance matrix", "Changes are not saved (the workbook is open in Excel). Close anyway?", parent=self._cwin):
                    return
        self._cwin.destroy()
        self._cwin = None
        if getattr(self, "shell_feature", "") == "compliance":
            self.shell_go("home" if getattr(self, "effort", None) is not None else "acronyms", save=False)
        if hasattr(self, "resume_changed"):
            self.resume_changed()

    def _c_build_requirements(self, fr):
        win = self._cwin
        size = getattr(self, "font_size", 13)
        from tkinter import font as tkfont
        vf = getattr(self, "tree_font", None) or tkfont.Font(fr, family="Segoe UI", size=size)   # the results table's text size (A- / A+)
        hf = getattr(self, "head_font", None) or vf
        st = ttk.Style(fr)
        st.configure("Cm.Treeview", font=vf, rowheight=vf.metrics("linespace") + int(max(8, size // 2) * getattr(self, "dpi", 1.0)))
        st.configure("Cm.Treeview.Heading", font=hf)
        dpi = max(1.0, float(ctk.ScalingTracker.get_widget_scaling(fr)))   # raw Tk text is not scaled by CustomTkinter
        sc = size / 13 * getattr(self, "dpi", 1.0)   # columns follow the text size and display scaling, like the results table
        right = ctk.CTkScrollableFrame(fr, width=440); right.pack(side="right", fill="y", padx=(8, 0))
        left = ctk.CTkFrame(fr, fg_color="transparent"); left.pack(side="left", fill="both", expand=True)
        win.c_left, win.c_right = left, right            # 2.32.0: the Page view replaces both on the Decide step
        cols = [("id", "ID", 90), ("decision", "Decision", 70), ("suggest", "Suggested", 80), ("learned", "Learned", 90), ("type", "Type", 90),
                ("actor", "Actor", 85), ("strength", "Strength", 85), ("section", "Section", 70), ("map", "Outline section", 170),
                ("text", "Requirement", 520)]
        tv = ttk.Treeview(left, columns=[c[0] for c in cols], show="headings", selectmode="extended", style="Cm.Treeview")
        for k, h, w in cols:
            tv.heading(k, text=h, command=lambda k=k: self._c_sort(k)); tv.column(k, width=int(w * sc), minwidth=40, anchor="w", stretch=False)
        tv.tag_configure("Keep", background=LEVEL_COLORS["Keep"], foreground="#111827")
        tv.tag_configure("Drop", background=LEVEL_COLORS["Drop"], foreground="#6B7280")
        tv.tag_configure("Context", background=LEVEL_COLORS["Context"], foreground="#111827")
        sb = ttk.Scrollbar(left, orient="vertical", command=tv.yview)
        hb = ttk.Scrollbar(left, orient="horizontal", command=tv.xview)
        tv.configure(yscrollcommand=sb.set, xscrollcommand=hb.set)
        sb.pack(side="right", fill="y"); hb.pack(side="bottom", fill="x"); tv.pack(fill="both", expand=True)
        tv.bind("<<TreeviewSelect>>", lambda _e: (self._c_show(), self.resume_changed() if hasattr(self, "resume_changed") else None))
        for key, dec in (("k", "Keep"), ("c", "Context"), ("d", "Drop"), ("u", "")):
            tv.bind(f"<KeyPress-{key}>", lambda _e, dec=dec: self.compliance_decide(dec))
            tv.bind(f"<KeyPress-{key.upper()}>", lambda _e, dec=dec: self.compliance_decide(dec))
        tv.bind("<KeyPress-n>", lambda _e: self.compliance_next_undecided())
        tv.bind("<KeyPress-N>", lambda _e: self.compliance_next_undecided())
        tv.bind("<KeyPress-s>", lambda _e: self.compliance_split())
        tv.bind("<KeyPress-m>", lambda _e: self.compliance_merge())
        win.tv = tv
        win._sort = ("", False)
        win.d_head = ctk.CTkLabel(right, text="Select a requirement", font=("Arial", 14, "bold"), anchor="w", justify="left", wraplength=400)
        win.d_head.pack(fill="x", padx=10, pady=(8, 2))
        win.d_text = ctk.CTkTextbox(right, height=110, wrap="word"); win.d_text.pack(fill="x", padx=10)
        win.d_text._textbox.bind("<ButtonRelease-1>", self._c_text_click, add="+")   # 2.31.0: where to split
        win.d_text._textbox.bind("<KeyRelease>", self._c_text_click, add="+")
        for k in ("s", "S"):
            win.d_text._textbox.bind(f"<KeyPress-{k}>", lambda _e: self.compliance_split())
        if hasattr(self, "kw_text_menu"):          # Keyword Harvest (2.18.0): selected words or the outline section
            win.d_text.bind("<Button-3>", lambda e: self.kw_text_menu(e, win.d_text._textbox, "Compliance requirement"))
            tv.bind("<Button-3>", self._c_kw_menu, add="+")
        bb = ctk.CTkFrame(right, fg_color="transparent"); bb.pack(fill="x", padx=10, pady=6)
        for text, cmd, color in (("Keep (K)", lambda: self.compliance_decide("Keep"), "#15803D"),
                                 ("Context (C)", lambda: self.compliance_decide("Context"), "#0369A1"),
                                 ("Drop (D)", lambda: self.compliance_decide("Drop"), "#6B7280"),
                                 ("Undecided (U)", lambda: self.compliance_decide(""), "#475569")):
            ctk.CTkButton(bb, text=text, command=cmd, fg_color=color, width=72).pack(side="left", padx=2)
        bb2 = ctk.CTkFrame(right, fg_color="transparent"); bb2.pack(fill="x", padx=10, pady=(0, 6))
        for text, cmd, color in (("Next undecided (N)", self.compliance_next_undecided, "#1E3A8A"),
                                 ("Split (S)", self.compliance_split, "#9A3412"), ("Merge (M)", self.compliance_merge, "#9A3412")):
            ctk.CTkButton(bb2, text=text, command=cmd, fg_color=color, width=72).pack(side="left", padx=2)
        win.d_src = ctk.CTkLabel(right, text="", anchor="w", justify="left", wraplength=400, text_color=("#475569", "#94A3B8"))
        win.d_src.pack(fill="x", padx=10)
        sbar = ctk.CTkFrame(right, fg_color="transparent"); sbar.pack(fill="x", padx=10, pady=(4, 0))
        ctk.CTkButton(sbar, text="Show page", width=100, command=self.compliance_show_page).pack(side="left")
        ctk.CTkButton(sbar, text="Open file", width=100, command=self.compliance_open_file).pack(side="left", padx=6)
        ctk.CTkButton(sbar, text="Compliance word style...", width=10, command=self.compliance_word_style).pack(side="left")
        ctk.CTkLabel(right, text="Source passage", anchor="w").pack(fill="x", padx=10, pady=(6, 0))
        win.d_ctx = tk.Text(right, height=7, wrap="word", font=("Segoe UI", int(round(10 * dpi))), relief="flat", bg="#F8FAFC", fg="#111827")
        win.d_ctx.tag_configure("hit", background="#FDE68A")
        win.d_ctx.pack(fill="x", padx=10)
        mp = ctk.CTkFrame(right, fg_color="transparent"); mp.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(mp, text="Outline section").pack(anchor="w")
        win.d_map = ctk.CTkComboBox(mp, values=[""], width=300); win.d_map.pack(side="left")
        ctk.CTkButton(mp, text="Map", width=60, command=self.compliance_map).pack(side="left", padx=4)
        win.d_sug = ctk.CTkButton(right, text="", width=10, fg_color="#1E3A8A", command=self.compliance_accept_map)
        win.d_learn = ctk.CTkFrame(right, fg_color="transparent")      # 2.30.0: top 3 from past proposals
        win.d_sug_anchor = ctk.CTkFrame(right, fg_color="transparent", height=4); win.d_sug_anchor.pack(fill="x")
        win.fields = {}
        for lab, key in (("Owner", "owner"), ("Status", "status"), ("Response page", "response_page"), ("Notes", "notes")):
            row = ctk.CTkFrame(right, fg_color="transparent"); row.pack(fill="x", padx=10, pady=1)
            ctk.CTkLabel(row, text=lab, width=100, anchor="w").pack(side="left")
            ent = ctk.CTkEntry(row); ent.pack(side="left", fill="x", expand=True)
            ent.bind("<FocusOut>", lambda _e, key=key, ent=ent: self._c_field(key, ent.get()))
            ent.bind("<Return>", lambda _e, key=key, ent=ent: self._c_field(key, ent.get()))
            win.fields[key] = ent

    def _c_build_outline(self, fr):
        win = self._cwin
        bar = ctk.CTkFrame(fr, fg_color="transparent"); bar.pack(fill="x", pady=(2, 6))
        win.o_letter = tk.StringVar(value="L")
        ctk.CTkButton(bar, text="From RFP headings in Section", command=self.compliance_outline_from_rfp, width=10).pack(side="left", padx=3)
        ctk.CTkOptionMenu(bar, variable=win.o_letter, values=["L", "M", "C", "All"], width=70).pack(side="left")
        ctk.CTkButton(bar, text="From a Word outline (.docx headings)...", command=self.compliance_outline_from_word, width=10).pack(side="left", padx=8)
        ctk.CTkButton(bar, text="Apply outline", command=self.compliance_outline_apply, fg_color="#0F766E", width=10).pack(side="left", padx=3)
        ctk.CTkButton(bar, text="Suggest sections for kept items", command=self.compliance_suggest_all, fg_color="#1E3A8A", width=10).pack(side="left", padx=8)
        ctk.CTkButton(bar, text="Section word synonyms...", command=self.compliance_synonyms, width=10).pack(side="left", padx=3)
        win.o_learn = ctk.CTkLabel(fr, text="", anchor="w", justify="left", wraplength=1300, text_color=("#475569", "#94A3B8"))
        win.o_learn.pack(fill="x", pady=(0, 4))
        body = ctk.CTkFrame(fr, fg_color="transparent"); body.pack(fill="both", expand=True)
        left = ctk.CTkFrame(body, fg_color="transparent"); left.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(left, text="One section per line: 1.2 Management Approach, Volume I - Technical, or indent with 4 spaces.",
                     anchor="w").pack(fill="x")
        win.o_text = ctk.CTkTextbox(left, wrap="none", font=("Consolas", 13)); win.o_text.pack(fill="both", expand=True)
        rightf = ctk.CTkFrame(body, fg_color="transparent"); rightf.pack(side="right", fill="both", padx=(8, 0))
        ctk.CTkLabel(rightf, text="Keep and Context rows per section", anchor="w").pack(fill="x")
        win.o_tv = ttk.Treeview(rightf, columns=("sec", "n"), show="headings", height=20, style="Cm.Treeview")
        win.o_tv.heading("sec", text="Section"); win.o_tv.heading("n", text="Rows")
        win.o_tv.column("sec", width=360, anchor="w"); win.o_tv.column("n", width=60, anchor="center")
        win.o_tv.pack(fill="both", expand=True)

    # ------------------------------------------------------------ showing
    def _c_visible(self):
        win, M = self._cwin, self.matrix
        if M is None:
            return []
        dec, typ, sug, mp, q = win.f_dec.get(), win.f_type.get(), win.f_sug.get(), win.f_map.get(), win.f_q.get().strip().casefold()
        out = []
        for it in M.items:
            if dec != ALL and (C.eff(it) or "Undecided") != dec: continue
            if typ != ALL and it["type"] != typ: continue
            if sug != ALL and it["suggest"] != sug: continue
            if win.f_learn.get() != ALL and not str(it.get("learned", "")).startswith(win.f_learn.get()): continue
            if mp == "Kept, not mapped" and not (it["decision"] == "Keep" and not it["map"]): continue
            if mp == "Needs a home" and not (it["decision"] in ("Keep", "Context") and not it["map"]): continue
            if mp == "Mapped" and not it["map"]: continue
            if q and q not in (it["text"] + " " + it["id"] + " " + it["section"] + " " + it["lead"]).casefold(): continue
            out.append(it)
        k, desc = win._sort
        if k:
            key = (lambda it: C.sec_key(it["section"] or "~")) if k in ("section", "id") else (lambda it: str(it.get(k, "")).lower())
            out.sort(key=key, reverse=desc)
        return out

    def _c_sort(self, k):
        win = self._cwin
        win._sort = (k, not win._sort[1] if win._sort[0] == k else False)
        self._c_fill()

    def _c_fill(self, keep_sel=True):
        win = self._cwin
        if win is None or not win.winfo_exists():
            return
        tv = win.tv
        sel = tv.selection() if keep_sel else ()
        tv.delete(*tv.get_children())
        for it in self._c_visible():
            txt = ((it["lead"] + " ") if it["lead"] else "") + it["text"]
            d = C.eff(it)
            tv.insert("", "end", iid=it["id"], tags=(d,) if d else (),
                      values=(it["id"], (d or "-") + (" (draft)" if it.get("draft") else ""), it["suggest"], it.get("learned", ""), it["type"], it["actor"], it["strength"], it["section"],
                              it["map"], (("[New] " if it.get("new") == "New in latest read" else "[Gone] " if it.get("new") else "") + txt)[:400]))
        keep = [s for s in sel if tv.exists(s)]
        if keep:
            tv.selection_set(keep); tv.see(keep[0])
        self._c_refresh_label()
        if hasattr(self, "_cp_sync"):
            self._cp_sync()

    def _c_refresh_label(self):
        win, M = self._cwin, self.matrix
        if M is None:
            win.lbl.configure(text="No matrix open. New from RFP files reads the RFP (Word, PDF, Excel, PowerPoint) and lists every candidate requirement.")
            self._c_prove_refresh()
            return
        c = M.counts()
        shown = len(win.tv.get_children())
        pct = int(c["decided"] * 100 / c["total"]) if c["total"] else 0
        bits = [f"{M.name}  |  {os.path.basename(M.path)}", f"{c['total']} sentences ({shown} shown)",
                f"Every sentence: {c['decided']} decided ({pct}%), {c['']} undecided" + ("  \u2713 all decided" if c["total"] and not c[""] else ""),
                f"Keep {c['Keep']}  Context {c['Context']}  Drop {c['Drop']}",
                f"placed {c['placed']}, need a home {c['needs_home']}"]
        if c.get("drafts"):
            bits.insert(2, f"{c['drafts']} draft{'s' if c['drafts'] != 1 else ''} not committed (counts and outputs use committed decisions)")
        if M.pending:
            bits.append("NOT SAVED yet" + (" (close the workbook in Excel, then Save)" if getattr(self, "_c_locked", False) else ""))
        win.lbl.configure(text="  |  ".join(bits))
        self._c_prove_refresh()

    def _c_learning_on(self):
        """Learned suggestions need AI and ML on and this effort's Team learning on (2.12.0)."""
        team = bool(self.ws.get("team_learning", True)) if getattr(self, "ws", None) is not None else True
        return _eng().ai_ml_on() and team

    def _c_ai_state(self):
        win = self._cwin
        if win is None or not win.winfo_exists():
            return
        on = _eng().ai_ml_on()
        win.btn_learn.configure(state="normal" if self._c_learning_on() else "disabled")
        win.chk_team.configure(state="normal" if on else "disabled")
        win.lbl_ai.configure(text="Rules: No AI  |  Learned column: ML" + ("" if self._c_learning_on() else
                             (" (off: AI and ML are off)" if not on else " (off: Team learning is off)")))

    def compliance_team_toggle(self):
        on = bool(self._cwin.team_var.get())
        try:
            self.ws.set("team_learning", on)
        except Exception:
            diag.swallowed()
        if on:
            diag.activity("team_learning_on")
        else:
            diag.activity("team_learning_off")
        self._c_ai_state()
        self._c_refresh()

    def _c_learner(self):
        if getattr(self, "_learner", None) is None:
            self._learner = CL.Learner(os.path.join(_eng().CONFIG_DIR, "compliance_learned.json"))
        return self._learner

    def _c_score(self):
        """Fill the Learned column from the model trained on the team's decisions (empty until it has enough)."""
        if self.matrix is None:
            return
        if not self._c_learning_on():                  # AI and ML off, or Team learning off: no learned scores
            for it in self.matrix.items:
                it["learned"] = ""
            return
        L = self._c_learner()
        for it in self.matrix.items:
            p = L.p_keep(it)
            it["learned"] = "" if p is None else f"{CL.Learner.label(p)} {int(round(p * 100))}%"

    def _c_suggest(self, it, stats=None):
        """Section suggestion: the rules first (same number, title words), then the most similar rows already mapped."""
        lab, score = C.suggest_map(it, self.matrix.outline, stats or C.word_df(self.matrix.items))
        if lab or not _eng().ai_ml_on():
            return lab, score
        lab, score = CL.map_from_neighbors(it, self.matrix.items)
        if self._c_learning_on() and (not lab or score < 0.6):   # 2.30.0: where the team placed sentences like this
            ranked = self._c_learned_places(it)
            if PL.Placer.band(ranked) == "strong":
                return ranked[0]
        return lab, score

    def _c_learned_places(self, it):
        """Top 3 sections from placement learning across proposals, [] when off or not enough placed yet."""
        if self.matrix is None or not self.matrix.outline or not self._c_learning_on():
            return []
        nb = getattr(self, "_c_nb", None)
        if nb is None or nb[0] is not self.matrix or nb[1] != len(self.matrix.items):
            self._c_nb = nb = (self.matrix, len(self.matrix.items), PL.neighbors_of(self.matrix.items))
        try:
            pl = self._c_learner().placer()
            sig = (id(pl), pl.matrices(), id(self.matrix), tuple((o["num"], o["title"], o["level"]) for o in self.matrix.outline))
            cache = getattr(self, "_c_place_cache", None)
            if cache is None or cache[0] != sig:      # ranks stay valid while the outline and the learned matrices stay
                self._c_place_cache = cache = (sig, {})
            key = (it["id"], it["text"])
            if key not in cache[1]:
                cache[1][key] = pl.rank(it, self.matrix.outline, nb[2].get(it["id"], []))
            return cache[1][key]
        except Exception:
            diag.swallowed()
            return []

    def _c_refresh(self):
        win = self._cwin
        if win is None or not win.winfo_exists():
            return
        self._c_score()
        self._c_fill()
        if hasattr(self, "_s_fill"):
            self._s_fill()
        M = self.matrix
        labels = [""] + [C.outline_label(o) for o in (M.outline if M else [])]
        win.d_map.configure(values=labels)
        try:
            win.o_learn.configure(text=self._c_place_text() if self._c_learning_on() else
                                  "Placement across proposals is off (AI and ML switch, or Team learning).")
        except Exception:
            diag.swallowed()
        win.o_text.delete("1.0", "end")
        if M:
            win.o_text.insert("1.0", C.outline_text(M.outline))
        win.o_tv.delete(*win.o_tv.get_children())
        if M:
            for o in M.outline:
                lab = C.outline_label(o)
                n = sum(1 for it in M.items if it["decision"] in ("Keep", "Context") and it["map"] == lab)
                win.o_tv.insert("", "end", values=(("    " * (o["level"] - 1)) + lab, n))
            un = sum(1 for it in M.items if it["decision"] in ("Keep", "Context") and not it["map"])
            win.o_tv.insert("", "end", values=("(needs a home)", un))
        self._c_show()

    def _c_kw_menu(self, event):
        """Right-click a requirement: its outline section, or words selected in the requirement text, as a keyword."""
        win = self._cwin
        iid = win.tv.identify_row(event.y)
        if not iid:
            return
        win.tv.selection_set(iid); self._c_show()
        it = self._c_item(iid) or {}
        m = tk.Menu(win, tearoff=0)
        sec = re.sub(r"^[\dA-Z]+(\.[\dA-Z]+)*\s+", "", (it.get("map") or "").strip())
        m.add_command(label=(f"Add outline section as keyword: {sec[:50]}" if sec else "Add outline section as keyword (not mapped yet)"),
                      state="normal" if sec and self.effort is not None else "disabled",
                      command=lambda: self.kw_quick(sec, source=f"Compliance outline {it.get('map', '')}"))
        m.add_command(label="Select words in the requirement text, then right-click there to add them", state="disabled")
        m.tk_popup(event.x_root, event.y_root)

    def _c_item(self, iid):
        return next((it for it in self.matrix.items if it["id"] == iid), None) if self.matrix else None

    def _c_selected(self):
        return [it for it in (self._c_item(i) for i in self._cwin.tv.selection()) if it]

    def _c_show(self):
        win = self._cwin
        sel = self._c_selected()
        win.d_text.configure(state="normal"); win.d_text.delete("1.0", "end")
        win.d_ctx.configure(state="normal"); win.d_ctx.delete("1.0", "end")
        for e in win.fields.values():
            e.delete(0, "end")
        win.d_sug.pack_forget()
        win.d_learn.pack_forget()
        if len(sel) != 1:
            win.d_head.configure(text=f"{len(sel)} requirements selected: K / D / U apply to all" if sel else "Select a requirement")
            win.d_src.configure(text="")
            win.d_text.configure(state="disabled"); win.d_ctx.configure(state="disabled")
            return
        it = sel[0]
        win.d_head.configure(text=f"{it['id']}   {it['type']}   {it['actor']}   {it['strength']}" + ("   compound: S splits it" if it["compound"] else ""))
        win.d_text.insert("1.0", ((it["lead"] + "\n") if it["lead"] else "") + it["text"])
        self._c_split_at = None
        self._c_tag_words(win.d_text._textbox)
        win.d_text.configure(state="disabled")
        sec = " ".join(x for x in (it["section"], it["section_title"]) if x)
        win.d_src.configure(text=f"{it['loc']}" + (f"\nSection {sec}" if sec else "") +
                            (f"\nCross-references: {it['xrefs']}" if it["xrefs"] else "") + (f"\nLinked: {it['links']}" if it["links"] else "") +
                            (f"\n{it['new']}" if it.get("new") else ""))
        ctx = it.get("context") or it["text"]
        win.d_ctx.insert("1.0", ctx)
        probe = it["text"][:60].replace("(a) ", "").strip()
        i = ctx.find(probe[:40]) if probe else -1
        if i >= 0:
            win.d_ctx.tag_add("hit", f"1.0+{i}c", f"1.0+{i + len(it['text'])}c")
            win.d_ctx.see(f"1.0+{i}c")
        win.d_ctx.configure(state="disabled")
        win.d_map.set(it["map"])
        for k, e in win.fields.items():
            e.insert(0, it.get(k, ""))
        lab, score = self._c_suggest(it)
        if lab and lab != it["map"]:
            win.d_sug.configure(text=f"Suggested: {lab}  (click to map)")
            win.d_sug.pack(anchor="w", padx=10, pady=(2, 4), before=win.d_sug_anchor)
        self._c_show_learned(it)
        if hasattr(self, "_cp_show"):
            self._cp_show(it)

    def _c_show_learned(self, it):
        """'From past proposals': the top 3 sections, each a button that maps the row; or 'no strong match'."""
        win = self._cwin
        for w in win.d_learn.winfo_children():
            w.destroy()
        if self.matrix is None or not self.matrix.outline or not self._c_learning_on():
            return
        pl = self._c_learner().placer()
        if not pl.ready():
            return
        ranked = self._c_learned_places(it)
        band = PL.Placer.band(ranked)
        head = {"strong": "From past proposals (strong match):", "possible": "From past proposals (possible):",
                "": "From past proposals: no strong match"}[band]
        ctk.CTkLabel(win.d_learn, text=head, anchor="w").pack(side="left")
        if band:
            for k, (lab, _s) in enumerate(ranked, 1):
                ctk.CTkButton(win.d_learn, text=f"{k}. {lab}", width=10, height=24, fg_color="#475569",
                              command=lambda lab=lab: (win.d_map.set(lab), self.compliance_map())).pack(side="left", padx=2)
        win.d_learn.pack(fill="x", padx=10, pady=(0, 4), before=win.d_sug_anchor)

    # ------------------------------------------------------------ deciding
    def compliance_decide(self, decision, rows=None):
        """2.35.0: pencil the decision as a draft (saved like any change); Commit makes it count. After a single Keep or
        Drop the next undecided sentence comes up; after Context the sentence stays, so L can link more requirements."""
        sel = rows if rows is not None else self._c_selected()
        if not sel:
            return "break"
        M = self.matrix
        for it in sel:
            cf = None
            if decision == "Context" and not C.eff_cf(it):
                d = C.default_context_for(M.items, it, dec=C.eff)
                cf = [d] if d else []
            if C.set_draft(it, decision, cf):
                M.log(it["id"], f"draft {decision or 'Undecided'}" + (f" (context for {C.eff_cf(it)})" if decision == "Context" and C.eff_cf(it) else ""))
        diag.activity("compliance_decided", n=len(sel))
        last = sel[-1]["id"]
        self._c_changed()
        if len(sel) == 1 and decision in ("Keep", "Drop") and self._c_auto_next():   # on to the next undecided (2.29.0)
            self.compliance_next_undecided(after=last)
        return "break"

    def _c_auto_next(self):
        try:
            return bool(self.ws.get("compliance_auto_next", True)) if getattr(self, "ws", None) is not None else True
        except Exception:
            return True

    def compliance_commit(self, rows=None, scope="all"):
        """Commit the drafts in rows (all drafts by default). Returns the result dict; the message goes on the dock
        and the status line."""
        M = self.matrix
        if M is None:
            return None
        rows = C.drafts(M.items) if rows is None else [it for it in rows if it.get("draft")]
        r = C.commit(rows)
        for it in rows:
            M.log(it["id"], f"committed {it['decision'] or 'Undecided'}" + (f" (context for {it['context_for']})" if it["context_for"] else ""))
        left = len(C.drafts(M.items))
        r["text"] = C.commit_text(r, left)
        r["left"] = left
        if r["n"]:
            diag.activity("compliance_committed", n=r["n"])
            self._c_changed()
        self._c_last_commit = r["text"]
        try:
            self.status.configure(text=r["text"])
        except Exception:
            diag.swallowed()
        if hasattr(self, "_cp_commit_msg"):
            self._cp_commit_msg(r["text"])
        return r

    def compliance_next_undecided(self, after=None):
        """Select the next undecided sentence (in the order shown), wrapping to the top. A draft counts as decided.
        Returns its ID or None."""
        if self.matrix is None:
            return None
        tv = self._cwin.tv
        rows = list(tv.get_children())
        if not rows:
            return None
        cur = after or (tv.selection()[0] if tv.selection() else None)
        start = rows.index(cur) + 1 if cur in rows else 0
        for iid in rows[start:] + rows[:start]:
            it = self._c_item(iid)
            if it is not None and not C.eff(it):
                tv.selection_set(iid); tv.focus(iid); tv.see(iid)
                return iid
        self._cwin.d_head.configure(text="Every sentence shown has a decision.")
        return None

    def _c_text_click(self, _e=None):
        """Remember the clicked point, or the selected words, inside the sentence (not its lead-in) for Split."""
        tb = self._cwin.d_text._textbox
        sel = self._c_selected()
        if len(sel) != 1:
            return
        start = "2.0" if sel[0]["lead"] else "1.0"
        def off(ix):
            return int(tb.count(start, ix, "chars")[0]) if tb.compare(ix, ">", start) else 0
        try:
            if tb.tag_ranges("sel"):
                self._c_split_at = (off("sel.first"), off("sel.last"))
            else:
                self._c_split_at = (off("insert"), None)
        except Exception:
            diag.swallowed()
            self._c_split_at = None

    def _c_tag_words(self, tb):
        """Show the compliance words in the sentence in the user's style (bold by default)."""
        import tkinter.font as tkfont
        try:
            cfg = CW.load()
            f = tkfont.Font(font=tb.cget("font"))
            font, fg, bg = CW.tk_font_options(cfg, f.actual("family"), f.actual("size"))
            opts = {"font": font}
            if fg:
                opts["foreground"] = fg
            if bg:
                opts["background"] = bg
            tb.tag_configure("cword", **opts)
            pos = 0
            for t, w in CW.segments(tb.get("1.0", "end-1c"), cfg):
                if w:
                    tb.tag_add("cword", f"1.0+{pos}c", f"1.0+{pos + len(t)}c")
                pos += len(t)
        except Exception:
            diag.swallowed()

    @staticmethod
    def _c_cut(text, at):
        """Parts of a sentence cut where the person clicked (at = (offset, None)) or around the words they selected
        (at = (start, end)); cuts snap to the nearest gap between words. [] when the cut would leave nothing."""
        def snap(i):
            i = max(0, min(len(text), i))
            if 0 < i < len(text) and not text[i - 1].isspace() and not text[i].isspace():
                left = text.rfind(" ", 0, i); right = text.find(" ", i)
                cands = [c for c in (left, right) if c > 0]
                i = min(cands, key=lambda c: abs(c - i)) if cands else i
            return i
        a, b = at
        cuts = sorted({snap(a)} | ({snap(b)} if b is not None else set()))
        pieces, prev = [], 0
        for c in cuts + [len(text)]:
            pieces.append(text[prev:c].strip())
            prev = c
        pieces = [p for p in pieces if len(p) > 2]
        return pieces if len(pieces) >= 2 else []

    def compliance_split(self):
        """Split the selected sentence where the person clicked in its text (or around the words they selected);
        with no point chosen, where the rules see two requirements ('; ' or 'and shall'). Each part is its own row
        with its own decision and outline section (2.31.0: split at the chosen point)."""
        sel = self._c_selected()
        if len(sel) != 1:
            return "break"
        it = sel[0]
        at = getattr(self, "_c_split_at", None)
        parts = self._c_cut(it["text"], at) if at else []
        how = "at the chosen point" if parts else "where the rules see two requirements"
        if not parts:
            parts = C.split_text(it["text"])
        if len(parts) < 2:
            self._cwin.d_head.configure(text=f"{it['id']}: click between two words in the sentence (or select words), then Split")
            return "break"
        i = self.matrix.items.index(it)
        new = []
        for n, p in enumerate(parts):
            x = dict(it)
            x.update(text=p, id=f"{it['id']}{chr(97 + n)}", key=C.text_key(p), compound=False, decision="", context_for="",
                     draft="", draft_cf="")
            new.append(x)
        self.matrix.items[i:i + 1] = new
        C.remap_context_for(self.matrix.items, it["id"], new[0]["id"])     # Context for the old row: the first part
        self.matrix.log(it["id"], f"split into {len(new)} {how}")
        self._c_split_at = None
        diag.activity("compliance_split", n=len(new))
        self._c_changed()
        if self._cwin.tv.exists(new[0]["id"]):
            self._cwin.tv.selection_set(new[0]["id"]); self._cwin.tv.see(new[0]["id"])
        return "break"

    def compliance_word_style(self, cfg=None):
        """Pick how compliance words look on screen and in every output (2.31.0). cfg= saves without a window."""
        def done(c):
            CW.save(c)
            diag.activity("compliance_word_style_saved")
            if self._cwin is not None and self._cwin.winfo_exists():
                self._c_show()
        if cfg is not None:
            done(cfg); return None
        cur = CW.load()
        parent = self._cwin if self._cwin is not None and self._cwin.winfo_exists() else self
        w = ctk.CTkToplevel(parent); w.title("Compliance word style"); w.geometry("620x620"); w.after(150, w.lift)
        ctk.CTkLabel(w, text="Compliance words (shall, must, will, should, may, required, not exceed, and order verbs such as "
                             "describe or provide at the start of a sentence or after shall) are shown in this style on screen "
                             "and in the Excel matrix, setup documents, coverage report and Word outline.",
                     wraplength=580, justify="left", anchor="w").pack(fill="x", padx=14, pady=(12, 6))
        row = ctk.CTkFrame(w, fg_color="transparent"); row.pack(fill="x", padx=14)
        v = {k: tk.BooleanVar(value=cur["style"][k]) for k in ("bold", "italic", "underline")}
        for k, lab in (("bold", "Bold"), ("italic", "Italic"), ("underline", "Underline")):
            ctk.CTkCheckBox(row, text=lab, variable=v[k], command=lambda: preview(), width=10).pack(side="left", padx=(0, 12))
        row2 = ctk.CTkFrame(w, fg_color="transparent"); row2.pack(fill="x", padx=14, pady=6)
        name_of = lambda table, hexv: next((n for n, h in table.items() if h == hexv), "None")
        color = tk.StringVar(value=name_of(CW.COLORS, cur["style"]["color"]))
        hl = tk.StringVar(value=name_of(CW.HIGHLIGHTS, cur["style"]["highlight"]))
        ctk.CTkLabel(row2, text="Color").pack(side="left")
        ctk.CTkOptionMenu(row2, variable=color, values=list(CW.COLORS), command=lambda _v: preview(), width=130).pack(side="left", padx=(6, 18))
        ctk.CTkLabel(row2, text="Highlight").pack(side="left")
        ctk.CTkOptionMenu(row2, variable=hl, values=list(CW.HIGHLIGHTS), command=lambda _v: preview(), width=130).pack(side="left", padx=6)
        ctk.CTkLabel(w, text="Excel cells cannot highlight single words, so the matrix uses the other choices.",
                     anchor="w", text_color=("#475569", "#94A3B8")).pack(fill="x", padx=14)
        pv = tk.Text(w, height=3, wrap="word", relief="flat", bg="#F8FAFC", fg="#111827", font=("Segoe UI", 11))
        pv.pack(fill="x", padx=14, pady=8)
        ctk.CTkLabel(w, text="Words, one per line (phrases allowed):", anchor="w").pack(fill="x", padx=14)
        box = ctk.CTkTextbox(w, height=180, wrap="none"); box.pack(fill="both", expand=True, padx=14)
        box.insert("1.0", "\n".join(cur["words"]))
        def gather():
            words = [x.strip() for x in box.get("1.0", "end").splitlines() if x.strip()]
            return {"style": {"bold": v["bold"].get(), "italic": v["italic"].get(), "underline": v["underline"].get(),
                              "color": CW.COLORS[color.get()], "highlight": CW.HIGHLIGHTS[hl.get()]}, "words": words}
        def preview():
            pv.configure(state="normal"); pv.delete("1.0", "end")
            pv.insert("1.0", "The Offeror shall describe the thermal design. Proposals shall not exceed 25 pages. "
                             "Provide resumes for key personnel.")
            cfg2 = CW._clean(gather())
            font, fg, bg = CW.tk_font_options(cfg2, "Segoe UI", 11)
            pv.tag_configure("cword", font=font, foreground=fg or "#111827", background=bg or "#F8FAFC")
            pos = 0
            for t, wd in CW.segments(pv.get("1.0", "end-1c"), cfg2):
                if wd:
                    pv.tag_add("cword", f"1.0+{pos}c", f"1.0+{pos + len(t)}c")
                pos += len(t)
            pv.configure(state="disabled")
        bar = ctk.CTkFrame(w, fg_color="transparent"); bar.pack(fill="x", padx=14, pady=10)
        ctk.CTkButton(bar, text="Save", fg_color="#0F766E", command=lambda: (done(gather()), w.destroy())).pack(side="right")
        ctk.CTkButton(bar, text="Cancel", command=w.destroy).pack(side="right", padx=6)
        def reset():
            for k in v:
                v[k].set(CW.DEFAULT_STYLE[k])
            color.set("None"); hl.set("None")
            box.delete("1.0", "end"); box.insert("1.0", "\n".join(CW.DEFAULT_WORDS)); preview()
        ctk.CTkButton(bar, text="Back to the defaults", command=reset).pack(side="left")
        preview()
        w.api = {"vars": v, "color": color, "highlight": hl, "box": box, "preview": pv, "gather": gather}
        return w

    def compliance_accept(self):
        """Accept the suggestions of every undecided sentence shown, as drafts (2.35.0)."""
        if self.matrix is None:
            return
        n = learned = 0
        for it in self._c_visible():
            if C.eff(it):
                continue
            lab = str(it.get("learned", "")).split(" ")[0] if it.get("type") != "Context" else ""
            if it.get("type") == "Context" and it["suggest"] in ("Context", "Drop"):
                d = it["suggest"]
            elif lab in ("Keep", "Drop"):
                d = lab; learned += 1
            elif it["suggest"] in ("Keep", "Drop") and lab != "Review":
                d = it["suggest"]
            else:
                continue
            cf = None
            if d == "Context":
                x = C.default_context_for(self.matrix.items, it, dec=C.eff)
                cf = [x] if x else []
            C.set_draft(it, d, cf); n += 1
            self.matrix.log(it["id"], f"draft {d} (accepted " + ("learned " if d == lab else "") + "suggestion)")
        diag.activity("compliance_accepted", n=n, items=learned)
        self._c_changed()
        self._cwin.lbl.configure(text=self._cwin.lbl.cget("text") + f"  |  {n} suggestions accepted as drafts ({learned} learned); "
                                 "Review rows stay undecided; Commit makes them count")

    def compliance_map(self):
        lab = self._cwin.d_map.get().strip()
        sel = self._c_selected()
        for it in sel:
            it["map"] = lab
            self.matrix.log(it["id"], f"mapped to {lab or '(none)'}")
        diag.activity("compliance_mapped", n=len(sel))
        self._c_changed()

    def compliance_accept_map(self):
        sel = self._c_selected()
        if len(sel) == 1:
            lab, _s = self._c_suggest(sel[0])
            self._cwin.d_map.set(lab)
            self.compliance_map()

    def _c_field(self, key, value):
        sel = self._c_selected()
        if len(sel) == 1 and sel[0].get(key, "") != value.strip():
            sel[0][key] = value.strip()
            self.matrix.log(sel[0]["id"], f"{key} set")
            self._c_changed(refill=False)

    # ------------------------------------------------------------ outline
    def compliance_outline_from_rfp(self):
        if self.matrix is None:
            return
        letter = self._cwin.o_letter.get()
        ol = C.outline_from_headings(self.matrix.headings, "" if letter == "All" else letter)
        if not ol:
            messagebox.showinfo("Outline", f"No numbered headings found in Section {letter}.", parent=self._cwin); return
        self._cwin.o_text.delete("1.0", "end"); self._cwin.o_text.insert("1.0", C.outline_text(ol))
        diag.activity("compliance_outline_rfp", items=len(ol))

    def compliance_outline_from_word(self):
        p = filedialog.askopenfilename(parent=self._cwin, title="Word outline (headings become sections)", filetypes=[("Word", "*.docx")])
        if not p:
            return
        try:
            with zipfile.ZipFile(p) as z:
                ol = C.outline_from_docx_xml(z.read("word/document.xml"))
        except Exception as ex:
            diag.swallowed()
            messagebox.showerror("Outline", f"Could not read the headings ({type(ex).__name__}).", parent=self._cwin); return
        if not ol:
            messagebox.showinfo("Outline", "That document has no Heading 1-6 paragraphs.", parent=self._cwin); return
        self._cwin.o_text.delete("1.0", "end"); self._cwin.o_text.insert("1.0", C.outline_text(ol))
        diag.activity("compliance_outline_word", items=len(ol))

    def compliance_outline_apply(self):
        if self.matrix is None:
            return
        ol = C.parse_outline(self._cwin.o_text.get("1.0", "end"))
        self.matrix.outline = ol
        labels = {C.outline_label(o) for o in ol}
        lost = 0
        for it in self.matrix.items:
            if it["map"] and it["map"] not in labels:
                it["map"] = ""; lost += 1
        self.matrix.log("outline", f"outline set: {len(ol)} sections" + (f"; {lost} mappings cleared" if lost else ""))
        diag.activity("compliance_outline_applied", items=len(ol), removed=lost)
        self._c_changed()
        if lost:
            messagebox.showinfo("Outline", f"{lost} requirements were mapped to sections that are no longer in the outline. They are unmapped now.", parent=self._cwin)

    def compliance_suggest_all(self):
        if self.matrix is None or not self.matrix.outline:
            return
        n = 0
        stats = C.word_df(self.matrix.items)
        for it in self.matrix.items:
            if it["decision"] == "Keep" and not it["map"]:
                lab, _s = self._c_suggest(it, stats)
                if lab:
                    it["map"] = lab; n += 1
                    self.matrix.log(it["id"], f"mapped to {lab} (suggested)")
        diag.activity("compliance_suggested", n=n)
        self._c_changed()
        messagebox.showinfo("Outline", f"{n} kept requirements got a suggested section. Check them on the Requirements tab "
                                       "(filter Outline: Mapped); the rest stay unmapped.", parent=self._cwin)

    def compliance_synonyms(self, text=None):
        """Edit the team list of words that mean the same thing in section titles (2.30.0). text= saves without a window."""
        path = PL.synonyms_path(_eng().CONFIG_DIR)
        def save(t):
            PL.save_synonyms(path, t)
            self._c_learner().placer(reload=True)
            diag.activity("compliance_synonyms_saved")
            if self._cwin is not None and self._cwin.winfo_exists():
                self._c_fill()
        if text is not None:
            save(text); return None
        w = ctk.CTkToplevel(self._cwin); w.title("Section word synonyms"); w.geometry("640x520"); w.after(150, w.lift)
        ctk.CTkLabel(w, text="One group per line, words separated by commas. Placement learning treats the words in a group as "
                             "one word, so 'Technical Solution' and 'Technical Methodology' count as the same section title. "
                             "Shared with the team in Knowledge Packs.", wraplength=600, justify="left", anchor="w").pack(fill="x", padx=12, pady=(10, 4))
        box = ctk.CTkTextbox(w, wrap="none", font=("Consolas", 13)); box.pack(fill="both", expand=True, padx=12)
        box.insert("1.0", PL.load_synonyms(path))
        bar = ctk.CTkFrame(w, fg_color="transparent"); bar.pack(fill="x", padx=12, pady=8)
        ctk.CTkButton(bar, text="Save", fg_color="#0F766E", command=lambda: (save(box.get("1.0", "end")), w.destroy())).pack(side="right")
        ctk.CTkButton(bar, text="Cancel", command=w.destroy).pack(side="right", padx=6)
        w.box = box
        return w

    # ------------------------------------------------------------ files
    def _c_pick_rfp(self, title):
        d = ""
        if getattr(self, "effort", None) is not None:
            d = (self.efforts.get(self.effort.name) or {}).get("customer_dir", "")
        return filedialog.askopenfilenames(parent=self._cwin, title=title, initialdir=d or self.start_dir(),
                                           filetypes=[("RFP documents", "*.docx *.pdf *.xlsx *.pptx")])

    def _c_read(self, paths, done):
        """Read RFP files on a worker thread (typed text), then call done(files_chunks, headings, sources)."""
        eng = _eng()
        win = self._cwin
        win.lbl.configure(text=f"Reading {len(paths)} RFP file(s)...")
        res = {}

        def work():
            try:
                fc, src = [], []
                for p in paths:
                    fc.append((os.path.basename(p), eng.typed_chunks(p)))
                    src.append([os.path.basename(p), _sha256(p), datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), os.path.abspath(p)])
                res["fc"], res["src"] = fc, src
            except Exception as ex:
                diag.swallowed()
                res["err"] = type(ex).__name__

        t = threading.Thread(target=work, daemon=True); t.start()

        def poll():
            if t.is_alive():
                win.after(200, poll); return
            if "err" in res:
                messagebox.showerror("Compliance matrix", f"An RFP file could not be read ({res['err']}).", parent=win)
                self._c_refresh_label(); return
            heads = []
            items = C.extract(res["fc"], heads)
            empty = [n for n, ch in res["fc"] if not any(t for _l, t in ch)]
            done(items, heads, res["src"], empty)
        poll()

    def compliance_new(self):
        paths = self._c_pick_rfp("RFP files: instructions, evaluation criteria, SOW, attachments")
        if not paths:
            return
        stem = re.sub(r"[^A-Za-z0-9_-]+", "_", self.effort.name) if getattr(self, "effort", None) else "RFP"
        base = os.path.dirname(self.effort.path) if getattr(self, "effort", None) else self.start_dir()
        out = filedialog.asksaveasfilename(parent=self._cwin, title="Where should the compliance matrix live?", defaultextension=".xlsx",
                                           initialfile=f"{stem}_Compliance_Matrix.xlsx", initialdir=base, filetypes=[("Excel", "*.xlsx")])
        if not out:
            return
        diag.activity("compliance_new", files=len(paths))

        def done(items, heads, src, empty):
            M = C.Matrix(out, os.path.splitext(os.path.basename(out))[0].replace("_Compliance_Matrix", ""))
            M.items, M.headings, M.sources = items, heads, src
            typed = (self.ws.get("outline_text") or "").strip() if getattr(self, "ws", None) else ""
            M.outline = C.parse_outline(typed) if typed else C.outline_from_headings(heads, "L")   # 2.28.0
            M.log("matrix", f"read {len(paths)} RFP file(s): {len(items)} candidates")
            self.matrix = M
            self._c_save_now()
            self._c_remember(out)
            self._c_refresh()
            if hasattr(self, "shell_go"):
                self.shell_go("compliance", "decide")          # straight on to deciding (2.32.0)
            diag.activity("compliance_read", files=len(paths), items=len(items))
            nreq = sum(1 for it in items if it.get("type") != "Context")
            msg = f"{len(items)} sentences from {len(paths)} file(s); {nreq} look like requirements. Every sentence gets a decision."
            if empty:
                msg += f"\n\n{len(empty)} file(s) have no typed text (scanned pages?): " + ", ".join(empty[:5]) + \
                       ". Scan them in the main window first, or ask for a typed copy."
            src = ("the response structure set in Start an effort" if typed else "the Section L headings")
            messagebox.showinfo("Compliance matrix", msg + f"\n\nThe starting outline comes from {src}; edit it on the Outline tab.", parent=self._cwin)
        self._c_read(paths, done)

    def compliance_add_files(self):
        if self.matrix is None:
            return self.compliance_new()
        paths = self._c_pick_rfp("More RFP files (amendments, attachments)")
        if not paths:
            return

        def done(items, heads, src, empty):
            have = {(it["file"], it["key"]) for it in self.matrix.items}
            add = [it for it in items if (it["file"], it["key"]) not in have]
            for it in add:
                it["id"] = ""
            self.matrix.items += add
            C.assign_ids(self.matrix.items); C.link_items(self.matrix.items)
            self.matrix.headings += heads; self.matrix.sources += src
            self.matrix.log("matrix", f"added {len(paths)} file(s): {len(add)} candidates")
            diag.activity("compliance_files_added", files=len(paths), added=len(add))
            self._c_changed()
            messagebox.showinfo("Compliance matrix", f"{len(add)} candidates added.", parent=self._cwin)
        self._c_read(paths, done)

    def compliance_reread(self):
        if self.matrix is None:
            return
        paths = self._c_pick_rfp("Re-read the RFP (all files, including the amendment)")
        if not paths:
            return

        def done(items, heads, src, empty):
            merged = C.merge_reread(self.matrix.items, items)
            new = sum(1 for it in merged if it.get("new") == "New in latest read")
            gone = sum(1 for it in merged if it.get("new") == "Not in the latest read")
            self.matrix.items, self.matrix.headings = merged, heads
            self.matrix.sources = src
            self.matrix.log("matrix", f"re-read {len(paths)} file(s): {new} new, {gone} no longer present")
            diag.activity("compliance_reread", files=len(paths), added=new, removed=gone)
            self._c_changed()
            messagebox.showinfo("Re-read", f"Decisions, mapping and notes kept for unchanged sentences.\n\n{new} new or changed "
                                           f"sentences are marked [New]; {gone} sentences no longer in the RFP are marked [Gone].", parent=self._cwin)
        self._c_read(paths, done)

    def compliance_open(self):
        p = filedialog.askopenfilename(parent=self._cwin, title="Open a compliance matrix", filetypes=[("Excel", "*.xlsx")])
        if p:
            self._c_load(p)

    def _c_load(self, path, quiet=False):
        try:
            self.matrix = C.Matrix(path).load()
        except Exception as ex:
            diag.swallowed()
            if not quiet:
                messagebox.showerror("Compliance matrix", f"The workbook could not be read ({type(ex).__name__}).", parent=self._cwin)
            return
        self._c_remember(path)
        diag.activity("compliance_loaded", items=len(self.matrix.items))
        rec = self.ws.read_recovery("matrix", path) if getattr(self, "ws", None) is not None else None
        if rec:
            n = max(0, len(rec["state"].get("history", [])) - len(self.matrix.history))
            if self.ask_recover("compliance matrix", rec, f" ({n} changes)" if n else ""):
                for k, v in rec["state"].items():
                    setattr(self.matrix, k, v)
                self.matrix.pending = True
                diag.activity("recovery_used")
                self._c_changed()
                return
            self.ws.clear_recovery("matrix", path)
        self._c_refresh()
        if not quiet and hasattr(self, "shell_go"):
            self.shell_go("compliance", "decide")

    def _c_remember(self, path):
        """The matrix belongs to the open effort (2.11.0); with no effort open, to scans with no effort."""
        try:
            self.ws.set("compliance_path", path)
        except Exception:
            diag.swallowed()

    # ------------------------------------------------------------ saving
    def _c_snapshot(self):
        """Copy of the unsaved matrix in the effort's recovery folder, so a crash before the save loses nothing."""
        self._c_snap_after = None
        M = self.matrix
        if M is None or getattr(self, "ws", None) is None:
            return
        try:
            self.ws.write_recovery("matrix", M.path, {k: v for k, v in vars(M).items() if k not in ("path", "pending")})
        except Exception:
            diag.swallowed()

    def _c_changed(self, refill=True):
        if self.matrix is not None:
            C.link_contexts(self.matrix.items)       # 2.33.0: every Context sentence has a requirement where one is near
        if getattr(self, "_c_snap_after", None):
            try:
                self.after_cancel(self._c_snap_after)
            except Exception:
                diag.swallowed()
        self._c_snap_after = self.after(400, self._c_snapshot)
        self.resume_changed() if hasattr(self, "resume_changed") else None
        if refill:
            self._c_refresh()
        else:
            self._c_refresh_label()
        if getattr(self, "_c_after", None):
            try:
                self.after_cancel(self._c_after)
            except Exception:
                diag.swallowed()
        self._c_after = self.after(2500, self._c_save_now)

    def _c_save_now(self):
        self._c_after = None
        M = self.matrix
        if M is None:
            return True
        try:
            M.save()
            self._c_locked = False
            ok = True
            if getattr(self, "ws", None) is not None:
                if getattr(self, "_c_snap_after", None):
                    try:
                        self.after_cancel(self._c_snap_after)
                    except Exception:
                        diag.swallowed()
                    self._c_snap_after = None
                self.ws.clear_recovery("matrix", M.path)
                try:
                    self.ws.backup(M.path, "matrix")
                except OSError:
                    diag.swallowed()
            try:                                     # keep learning from the decisions (hashed counts only)
                if self._c_learning_on():
                    L = self._c_learner()
                    if L.learn(M.path, M.items, M.outline):
                        L.save()
            except Exception:
                diag.swallowed()
        except C.Locked:
            self._c_locked = True
            ok = False
        except OSError:
            diag.swallowed()
            ok = False
        if self._cwin is not None and self._cwin.winfo_exists():
            self._c_refresh_label()
        return ok

    def compliance_save(self):
        if self.matrix is not None and not self._c_save_now() and getattr(self, "_c_locked", False):
            messagebox.showwarning("Compliance matrix", "The workbook is open in Excel. Close it there, then click Save. Your changes are kept.", parent=self._cwin)

    def compliance_excel(self):
        if self.matrix is None:
            return
        self._c_save_now()
        try:
            os.startfile(self.matrix.path)
        except AttributeError:
            messagebox.showinfo("Compliance matrix", self.matrix.path, parent=self._cwin)

    def compliance_word(self):
        M = self.matrix
        if M is None:
            return
        p = filedialog.asksaveasfilename(parent=self._cwin, title="Annotated Word outline", defaultextension=".docx",
                                         initialfile=f"{re.sub(r'[^A-Za-z0-9_-]+', '_', M.name)}_Outline_with_Requirements.docx",
                                         initialdir=os.path.dirname(M.path), filetypes=[("Word", "*.docx")])
        if not p:
            return
        try:
            info = C.write_outline_docx(M, p)
        except PermissionError:
            messagebox.showerror("Word outline", "That file is open in Word. Close it, then try again.", parent=self._cwin); return
        diag.activity("compliance_word_outline", items=info["mapped"], rows=info["unmapped"])
        messagebox.showinfo("Word outline", f"Saved:\n{p}\n\n{info['sections']} sections, {info['mapped']} kept requirements mapped, "
                                            f"{info['unmapped']} kept but not mapped (listed at the end).", parent=self._cwin)

    def compliance_coverage(self, p=None):
        """Every sentence of the RFP, highlighted by its decision and where it was placed (2.29.0). Returns the counts."""
        M = self.matrix
        if M is None:
            return None
        p = p or filedialog.asksaveasfilename(parent=self._cwin, title="RFP coverage report", defaultextension=".docx",
                                              initialfile=f"{re.sub(r'[^A-Za-z0-9_-]+', '_', M.name)}_RFP_Coverage.docx",
                                              initialdir=os.path.dirname(M.path), filetypes=[("Word", "*.docx")])
        if not p:
            return None
        try:
            info = C.write_coverage_docx(M, p)
        except PermissionError:
            messagebox.showerror("Coverage report", "That file is open in Word. Close it, then try again.", parent=self._cwin); return None
        diag.activity("compliance_coverage", rows=info["sentences"], n=info["undecided"])
        messagebox.showinfo("Coverage report", f"Saved:\n{p}\n\n{info['sentences']} sentences from {info['files']} file(s): "
                            + ("every one has a decision" if not info["undecided"] else f"{info['undecided']} still undecided (red)")
                            + (f"; {info['needs_home']} Keep or Context sentences not placed yet." if info["needs_home"] else "; all placed.")
                            + "\n\nIt holds RFP text: keep it on this PC or SharePoint.", parent=self._cwin)
        return info

    # ------------------------------------------------------------ learning (C3), merge, source page, amendment changes
    def compliance_learn(self):
        M = self.matrix
        if M is None:
            return
        if not self._c_learning_on():
            messagebox.showinfo("Learn from decisions", "Learning is off for this effort (AI and ML switch, or Team learning). "
                                "Decisions stay in the matrix; nothing is learned from them.", parent=self._cwin)
            return
        L = self._c_learner()
        pl = L.placer()
        chk = pl.check(CL.Learner.source_id(M.path), M.items, M.outline) if M.outline else None
        n = L.learn(M.path, M.items, M.outline)
        L.save()
        cv = CL.Learner.cross_check(M.items)
        self._c_refresh()
        s = L.summary()
        diag.activity("compliance_learned", rows=n, items=s["decisions"])
        msg = (f"Learned from {n} decisions in this matrix ({s['decisions']} decisions across {s['matrices']} matrices on this PC).\n\n"
               "The model stores numbered word buckets and counts only, never RFP text, in config\\compliance_learned.json.")
        if cv:
            agree, total, rule = cv
            msg += (f"\n\nCheck on this matrix (each row predicted by a model that did not see it): the learned model agrees with "
                    f"your decision on {agree} of {total} rows; the rule suggestions agree on {rule} of {total}.")
        if not L.ready():
            msg += "\n\nThe Learned column fills in once there are at least 5 Keep and 3 Drop decisions."
        msg += "\n\n" + self._c_place_text(chk)
        messagebox.showinfo("Learn from decisions", msg, parent=self._cwin)

    def _c_place_text(self, chk=None):
        """Plain summary of placement learning across proposals and its self-check (2.30.0)."""
        pl = self._c_learner().placer()
        t = (f"Placement across proposals: {pl.placed()} placed rows from {pl.matrices()} matrices"
             + ("." if pl.ready() else f"; suggestions start at {PL.MIN_PLACED} placed rows."))
        if chk:
            t += (f" Check on this matrix, using only what the other matrices taught: your section was in the top 3 "
                  f"suggestions for {chk['top3']} of {chk['total']} placed rows ({round(100 * chk['top3'] / chk['total'])}%), "
                  f"first choice for {chk['top1']}.")
        hist = pl.history()
        if len(hist) > 1:
            t += " Earlier checks: " + ", ".join(f"{d} {round(100 * a / b)}%" for d, a, b in hist[-6:]) + "."
        return t

    def compliance_merge(self):
        sel = self._c_selected()
        if len(sel) < 2:
            self._cwin.d_head.configure(text="Select two or more rows to merge (Ctrl+click), then M.")
            return "break"
        ids = [it["id"] for it in sel]
        first = C.merge_items(self.matrix.items, ids)
        self.matrix.log(first["id"], f"merged {len(ids)} rows")
        diag.activity("compliance_merged", n=len(ids))
        self._c_changed()
        if self._cwin.tv.exists(first["id"]):
            self._cwin.tv.selection_set(first["id"])
        return "break"

    def _c_source_path(self, it):
        p = self.matrix.path_of(it["file"])
        if p:
            return p
        p = filedialog.askopenfilename(parent=self._cwin, title=f"Where is {it['file']} now?",
                                       filetypes=[("RFP document", "*" + os.path.splitext(it["file"])[1])])
        if p and os.path.basename(p) == it["file"]:
            self.matrix.sources.append([it["file"], _sha256(p), datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), os.path.abspath(p)])
            self.matrix.pending = True
            return p
        return ""

    def compliance_open_file(self):
        sel = self._c_selected()
        if len(sel) != 1:
            return
        p = self._c_source_path(sel[0])
        if not p:
            return
        diag.activity("compliance_open_file")
        try:
            os.startfile(p)
        except AttributeError:
            messagebox.showinfo("Open file", p, parent=self._cwin)

    def compliance_show_page(self):
        """The PDF page a row came from, with the sentence highlighted. Other files: the passage is in the panel; Open file."""
        sel = self._c_selected()
        if len(sel) != 1:
            return
        it = sel[0]
        if not it["file"].lower().endswith(".pdf") or not it.get("page"):
            messagebox.showinfo("Show page", "Pages are shown for PDF files. For Word, Excel and PowerPoint the source passage is "
                                             "in the panel; Open file opens the document.", parent=self._cwin)
            return
        p = self._c_source_path(it)
        if not p:
            return
        try:
            img = C.render_page(p, int(it["page"]), it["text"])
        except Exception as ex:
            diag.swallowed()
            messagebox.showerror("Show page", f"The page could not be shown ({type(ex).__name__}).", parent=self._cwin)
            return
        diag.activity("compliance_show_page")
        w = ctk.CTkToplevel(self._cwin); w.title(f"{it['id']}: {it['file']} page {it['page']}")
        sc = ctk.ScalingTracker.get_window_scaling(w)
        maxh = int(w.winfo_screenheight() * 0.85)
        ratio = min(1.0, maxh / img.height)
        shown = img.resize((int(img.width * ratio), int(img.height * ratio)))
        from PIL import ImageTk
        photo = ImageTk.PhotoImage(shown)
        cv = tk.Canvas(w, width=shown.width, height=shown.height, highlightthickness=0)
        cv.pack()
        cv.create_image(0, 0, image=photo, anchor="nw")
        cv._photo = photo
        w.after(150, w.lift)

    def compliance_changes(self):
        M = self.matrix
        if M is None:
            return
        ch = C.amendment_changes(M.items)
        if not ch:
            messagebox.showinfo("Amendment changes", "No changes to show. Re-read RFP (amendment) marks new and removed sentences; "
                                                     "this view pairs them.", parent=self._cwin)
            return
        diag.activity("compliance_changes", rows=len(ch))
        w = ctk.CTkToplevel(self._cwin); w.title("Amendment changes"); w.geometry("1200x600"); w.after(150, w.lift)
        k = {x: sum(1 for c in ch if c["kind"] == x) for x in ("Changed", "Added", "Removed")}
        ctk.CTkLabel(w, text=f"Changed {k['Changed']}  |  Added {k['Added']}  |  Removed {k['Removed']}     "
                             "Word differences: [-removed-] {+added+}. Double-click a row to select it in the matrix.",
                     anchor="w").pack(fill="x", padx=12, pady=(10, 4))
        fr = ctk.CTkFrame(w, fg_color="transparent"); fr.pack(fill="both", expand=True, padx=10)
        cols = [("kind", "Change", 90), ("id", "New ID", 100), ("old_id", "Old ID", 100), ("section", "Section", 80),
                ("decision", "Earlier decision", 110), ("diff", "Text and differences", 900)]
        tv = ttk.Treeview(fr, columns=[c[0] for c in cols], show="headings", style="Cm.Treeview")
        sc = getattr(self, "font_size", 13) / 13 * getattr(self, "dpi", 1.0)
        for c, h, wd in cols:
            tv.heading(c, text=h); tv.column(c, width=int(wd * sc), anchor="w", stretch=c == "diff")
        sb = ttk.Scrollbar(fr, orient="vertical", command=tv.yview); tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); tv.pack(fill="both", expand=True)
        rows = {}
        for c in ch:
            text = c["diff"] or c["new"] or c["old"]
            rows[tv.insert("", "end", values=(c["kind"], c["id"], c["old_id"], c["section"], c["decision"], text[:600]))] = c

        def jump(_e=None):
            c = rows.get(tv.focus())
            iid = c and (c["id"] or c["old_id"])
            if iid:
                self._cwin.f_dec.set(ALL); self._cwin.f_q.set(""); self._c_fill()
                if self._cwin.tv.exists(iid):
                    self._cwin.tv.selection_set(iid); self._cwin.tv.see(iid); self._cwin.lift()
        tv.bind("<Double-1>", jump)

        def export():
            p = filedialog.asksaveasfilename(parent=w, title="Save the amendment changes", defaultextension=".xlsx",
                                             initialfile=f"{re.sub(r'[^A-Za-z0-9_-]+', '_', M.name)}_Amendment_Changes.xlsx",
                                             initialdir=os.path.dirname(M.path), filetypes=[("Excel", "*.xlsx")])
            if p:
                C.write_changes_excel(ch, p, M.name)
                diag.activity("compliance_changes_exported", rows=len(ch))
                messagebox.showinfo("Amendment changes", f"Saved:\n{p}", parent=w)
        ctk.CTkButton(w, text="Export (Excel)...", command=export).pack(anchor="w", padx=12, pady=8)
        w._api = {"tv": tv, "rows": rows, "jump": jump, "export": export}
        return w
