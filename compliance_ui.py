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

ALL = "All"
LEVEL_COLORS = {"Keep": "#E7F6EC", "Drop": "#EEEEEE"}


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
        self.btn_compliance = ctk.CTkButton(toolbar, text="Compliance Matrix...", command=self.open_compliance, **button_kw)
        self.btn_compliance.pack(fill="x", padx=8, pady=2)

    # ------------------------------------------------------------ window
    def open_compliance(self):
        diag.activity("compliance_opened")
        if self._cwin is not None and self._cwin.winfo_exists():
            self._cwin.deiconify(); self._cwin.lift(); return self._cwin
        win = ctk.CTkToplevel(self); win.title("Compliance matrix")
        win.geometry("1400x820"); win.after(150, win.lift)
        diag.register(win, "compliance")
        self._cwin = win
        win.protocol("WM_DELETE_WINDOW", self._close_compliance)
        top = ctk.CTkFrame(win, fg_color="transparent"); top.pack(fill="x", padx=10, pady=(8, 2))
        B = dict(height=30, width=10)
        for text, cmd, color in (("New from RFP files...", self.compliance_new, "#9A3412"), ("Open matrix...", self.compliance_open, None),
                                 ("Add RFP files...", self.compliance_add_files, None), ("Re-read RFP (amendment)...", self.compliance_reread, None),
                                 ("Save", self.compliance_save, "#0F766E"), ("Open in Excel", self.compliance_excel, None),
                                 ("Word outline...", self.compliance_word, "#1E3A8A"), ("Learn from decisions", self.compliance_learn, "#6D28D9"),
                                 ("Amendment changes...", self.compliance_changes, None)):
            kw = dict(B); kw.update(fg_color=color) if color else None
            btn = ctk.CTkButton(top, text=text, command=cmd, **kw)
            btn.pack(side="left", padx=3)
            if cmd == self.compliance_learn:
                win.btn_learn = btn
        win.team_var = tk.BooleanVar(value=bool(self.ws.get("team_learning", True)) if getattr(self, "ws", None) is not None else True)
        win.chk_team = ctk.CTkCheckBox(top, text="Team learning", variable=win.team_var, command=self.compliance_team_toggle, width=10)
        win.chk_team.pack(side="left", padx=(8, 3))
        win.lbl_ai = ctk.CTkLabel(top, text="", font=("Segoe UI", 11))
        win.lbl_ai.pack(side="left", padx=6)
        win.lbl = ctk.CTkLabel(win, text="", anchor="w", justify="left", wraplength=1360)
        win.lbl.pack(fill="x", padx=12)
        flt = ctk.CTkFrame(win, fg_color="transparent"); flt.pack(fill="x", padx=10, pady=2)
        win.f_dec = tk.StringVar(value=ALL); win.f_type = tk.StringVar(value=ALL); win.f_sug = tk.StringVar(value=ALL)
        win.f_map = tk.StringVar(value=ALL); win.f_q = tk.StringVar(); win.f_learn = tk.StringVar(value=ALL)
        for lab, var, vals in (("Decision", win.f_dec, [ALL, "Undecided", "Keep", "Drop"]), ("Type", win.f_type, [ALL] + list(C.TYPES)),
                               ("Suggested", win.f_sug, [ALL, "Keep", "Drop", "Review"]), ("Learned", win.f_learn, [ALL, "Keep", "Drop", "Review"]),
                               ("Outline", win.f_map, [ALL, "Kept, not mapped", "Mapped"])):
            ctk.CTkLabel(flt, text=lab).pack(side="left", padx=(8, 3))
            ctk.CTkOptionMenu(flt, variable=var, values=vals, width=110, command=lambda _v: self._c_fill()).pack(side="left")
        ctk.CTkLabel(flt, text="Search").pack(side="left", padx=(12, 3))
        e = ctk.CTkEntry(flt, textvariable=win.f_q, width=200); e.pack(side="left")
        e.bind("<KeyRelease>", lambda _e: self._c_fill())
        win.btn_accept = ctk.CTkButton(flt, text="Accept suggestions (shown, undecided)", command=self.compliance_accept, width=10)
        win.btn_accept.pack(side="left", padx=10)
        tabs = ctk.CTkTabview(win); tabs.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        win.tabs = tabs
        self._c_build_requirements(tabs.add("Requirements"))
        self._c_build_outline(tabs.add("Outline"))
        self._s_build(tabs.add("Setup"))           # Setup Builder (2.13.0)
        last = self.ws.get("compliance_path", "") if getattr(self, "ws", None) is not None else ""   # per effort (2.11.0)
        if self.matrix is None and last and os.path.isfile(last):
            self._c_load(last, quiet=True)
        self._c_ai_state()
        self._c_refresh()
        return win

    def _close_compliance(self):
        if self.matrix is not None and self.matrix.pending:
            if not self._c_save_now():
                if not messagebox.askyesno("Compliance matrix", "Changes are not saved (the workbook is open in Excel). Close anyway?", parent=self._cwin):
                    return
        self._cwin.destroy()
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
        cols = [("id", "ID", 90), ("decision", "Decision", 70), ("suggest", "Suggested", 80), ("learned", "Learned", 90), ("type", "Type", 90),
                ("actor", "Actor", 85), ("strength", "Strength", 85), ("section", "Section", 70), ("map", "Outline section", 170),
                ("text", "Requirement", 520)]
        tv = ttk.Treeview(left, columns=[c[0] for c in cols], show="headings", selectmode="extended", style="Cm.Treeview")
        for k, h, w in cols:
            tv.heading(k, text=h, command=lambda k=k: self._c_sort(k)); tv.column(k, width=int(w * sc), minwidth=40, anchor="w", stretch=False)
        tv.tag_configure("Keep", background=LEVEL_COLORS["Keep"], foreground="#111827")
        tv.tag_configure("Drop", background=LEVEL_COLORS["Drop"], foreground="#6B7280")
        sb = ttk.Scrollbar(left, orient="vertical", command=tv.yview)
        hb = ttk.Scrollbar(left, orient="horizontal", command=tv.xview)
        tv.configure(yscrollcommand=sb.set, xscrollcommand=hb.set)
        sb.pack(side="right", fill="y"); hb.pack(side="bottom", fill="x"); tv.pack(fill="both", expand=True)
        tv.bind("<<TreeviewSelect>>", lambda _e: (self._c_show(), self.resume_changed() if hasattr(self, "resume_changed") else None))
        for key, dec in (("k", "Keep"), ("d", "Drop"), ("u", "")):
            tv.bind(f"<KeyPress-{key}>", lambda _e, dec=dec: self.compliance_decide(dec))
            tv.bind(f"<KeyPress-{key.upper()}>", lambda _e, dec=dec: self.compliance_decide(dec))
        tv.bind("<KeyPress-s>", lambda _e: self.compliance_split())
        tv.bind("<KeyPress-m>", lambda _e: self.compliance_merge())
        win.tv = tv
        win._sort = ("", False)
        win.d_head = ctk.CTkLabel(right, text="Select a requirement", font=("Arial", 14, "bold"), anchor="w", justify="left", wraplength=400)
        win.d_head.pack(fill="x", padx=10, pady=(8, 2))
        win.d_text = ctk.CTkTextbox(right, height=110, wrap="word"); win.d_text.pack(fill="x", padx=10)
        if hasattr(self, "kw_text_menu"):          # Keyword Harvest (2.18.0): selected words or the outline section
            win.d_text.bind("<Button-3>", lambda e: self.kw_text_menu(e, win.d_text._textbox, "Compliance requirement"))
            tv.bind("<Button-3>", self._c_kw_menu, add="+")
        bb = ctk.CTkFrame(right, fg_color="transparent"); bb.pack(fill="x", padx=10, pady=6)
        for text, cmd, color in (("Keep (K)", lambda: self.compliance_decide("Keep"), "#15803D"), ("Drop (D)", lambda: self.compliance_decide("Drop"), "#6B7280"),
                                 ("Undecided (U)", lambda: self.compliance_decide(""), "#475569"), ("Split (S)", self.compliance_split, "#9A3412"),
                                 ("Merge (M)", self.compliance_merge, "#9A3412")):
            ctk.CTkButton(bb, text=text, command=cmd, fg_color=color, width=72).pack(side="left", padx=2)
        win.d_src = ctk.CTkLabel(right, text="", anchor="w", justify="left", wraplength=400, text_color=("#475569", "#94A3B8"))
        win.d_src.pack(fill="x", padx=10)
        sbar = ctk.CTkFrame(right, fg_color="transparent"); sbar.pack(fill="x", padx=10, pady=(4, 0))
        ctk.CTkButton(sbar, text="Show page", width=100, command=self.compliance_show_page).pack(side="left")
        ctk.CTkButton(sbar, text="Open file", width=100, command=self.compliance_open_file).pack(side="left", padx=6)
        ctk.CTkLabel(right, text="Source passage", anchor="w").pack(fill="x", padx=10, pady=(6, 0))
        win.d_ctx = tk.Text(right, height=7, wrap="word", font=("Segoe UI", int(round(10 * dpi))), relief="flat", bg="#F8FAFC", fg="#111827")
        win.d_ctx.tag_configure("hit", background="#FDE68A")
        win.d_ctx.pack(fill="x", padx=10)
        mp = ctk.CTkFrame(right, fg_color="transparent"); mp.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(mp, text="Outline section").pack(anchor="w")
        win.d_map = ctk.CTkComboBox(mp, values=[""], width=300); win.d_map.pack(side="left")
        ctk.CTkButton(mp, text="Map", width=60, command=self.compliance_map).pack(side="left", padx=4)
        win.d_sug = ctk.CTkButton(right, text="", width=10, fg_color="#1E3A8A", command=self.compliance_accept_map)
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
        body = ctk.CTkFrame(fr, fg_color="transparent"); body.pack(fill="both", expand=True)
        left = ctk.CTkFrame(body, fg_color="transparent"); left.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(left, text="One section per line: 1.2 Management Approach, Volume I - Technical, or indent with 4 spaces.",
                     anchor="w").pack(fill="x")
        win.o_text = ctk.CTkTextbox(left, wrap="none", font=("Consolas", 13)); win.o_text.pack(fill="both", expand=True)
        rightf = ctk.CTkFrame(body, fg_color="transparent"); rightf.pack(side="right", fill="both", padx=(8, 0))
        ctk.CTkLabel(rightf, text="Kept requirements per section", anchor="w").pack(fill="x")
        win.o_tv = ttk.Treeview(rightf, columns=("sec", "n"), show="headings", height=20, style="Cm.Treeview")
        win.o_tv.heading("sec", text="Section"); win.o_tv.heading("n", text="Kept")
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
            if dec != ALL and (it["decision"] or "Undecided") != dec: continue
            if typ != ALL and it["type"] != typ: continue
            if sug != ALL and it["suggest"] != sug: continue
            if win.f_learn.get() != ALL and not str(it.get("learned", "")).startswith(win.f_learn.get()): continue
            if mp == "Kept, not mapped" and not (it["decision"] == "Keep" and not it["map"]): continue
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
            tv.insert("", "end", iid=it["id"], tags=(it["decision"],) if it["decision"] else (),
                      values=(it["id"], it["decision"] or "-", it["suggest"], it.get("learned", ""), it["type"], it["actor"], it["strength"], it["section"],
                              it["map"], (("[New] " if it.get("new") == "New in latest read" else "[Gone] " if it.get("new") else "") + txt)[:400]))
        keep = [s for s in sel if tv.exists(s)]
        if keep:
            tv.selection_set(keep); tv.see(keep[0])
        self._c_refresh_label()

    def _c_refresh_label(self):
        win, M = self._cwin, self.matrix
        if M is None:
            win.lbl.configure(text="No matrix open. New from RFP files reads the RFP (Word, PDF, Excel, PowerPoint) and lists every candidate requirement.")
            return
        c = M.counts()
        shown = len(win.tv.get_children())
        bits = [f"{M.name}  |  {os.path.basename(M.path)}", f"{c['total']} candidates ({shown} shown)",
                f"Keep {c['Keep']}  Drop {c['Drop']}  Undecided {c['']}", f"kept and mapped {c['mapped']}, kept not mapped {c['kept_unmapped']}"]
        if M.pending:
            bits.append("NOT SAVED yet" + (" (close the workbook in Excel, then Save)" if getattr(self, "_c_locked", False) else ""))
        win.lbl.configure(text="  |  ".join(bits))

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
        if not lab and _eng().ai_ml_on():
            lab, score = CL.map_from_neighbors(it, self.matrix.items)
        return lab, score

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
        win.o_text.delete("1.0", "end")
        if M:
            win.o_text.insert("1.0", C.outline_text(M.outline))
        win.o_tv.delete(*win.o_tv.get_children())
        if M:
            for o in M.outline:
                lab = C.outline_label(o)
                n = sum(1 for it in M.items if it["decision"] == "Keep" and it["map"] == lab)
                win.o_tv.insert("", "end", values=(("    " * (o["level"] - 1)) + lab, n))
            un = sum(1 for it in M.items if it["decision"] == "Keep" and not it["map"])
            win.o_tv.insert("", "end", values=("(kept, not mapped)", un))
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
        if len(sel) != 1:
            win.d_head.configure(text=f"{len(sel)} requirements selected: K / D / U apply to all" if sel else "Select a requirement")
            win.d_src.configure(text="")
            win.d_text.configure(state="disabled"); win.d_ctx.configure(state="disabled")
            return
        it = sel[0]
        win.d_head.configure(text=f"{it['id']}   {it['type']}   {it['actor']}   {it['strength']}" + ("   compound: S splits it" if it["compound"] else ""))
        win.d_text.insert("1.0", ((it["lead"] + "\n") if it["lead"] else "") + it["text"])
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

    # ------------------------------------------------------------ deciding
    def compliance_decide(self, decision):
        sel = self._c_selected()
        if not sel:
            return "break"
        for it in sel:
            if it["decision"] != decision:
                it["decision"] = decision
                self.matrix.log(it["id"], f"decision {decision or 'Undecided'}")
        diag.activity("compliance_decided", n=len(sel))
        tv = self._cwin.tv
        nxt = tv.next(sel[-1]["id"]) if len(sel) == 1 else ""
        self._c_changed()
        if nxt and tv.exists(nxt):
            tv.selection_set(nxt); tv.focus(nxt); tv.see(nxt)
        return "break"

    def compliance_split(self):
        sel = self._c_selected()
        if len(sel) != 1:
            return "break"
        it = sel[0]
        parts = C.split_text(it["text"])
        if len(parts) < 2:
            self._cwin.d_head.configure(text=f"{it['id']}: nothing to split (no '; ' or 'and shall')")
            return "break"
        i = self.matrix.items.index(it)
        new = []
        for n, p in enumerate(parts):
            x = dict(it)
            x.update(text=p, id=f"{it['id']}{chr(97 + n)}", key=C.text_key(p), compound=False, decision="")
            new.append(x)
        self.matrix.items[i:i + 1] = new
        self.matrix.log(it["id"], f"split into {len(new)}")
        diag.activity("compliance_split", n=len(new))
        self._c_changed()
        self._cwin.tv.selection_set(new[0]["id"]) if self._cwin.tv.exists(new[0]["id"]) else None
        return "break"

    def compliance_accept(self):
        if self.matrix is None:
            return
        n = learned = 0
        for it in self._c_visible():
            if it["decision"]:
                continue
            lab = str(it.get("learned", "")).split(" ")[0]
            if lab in ("Keep", "Drop"):
                it["decision"] = lab; n += 1; learned += 1
                self.matrix.log(it["id"], f"decision {lab} (accepted learned suggestion)")
            elif it["suggest"] in ("Keep", "Drop") and lab != "Review":
                it["decision"] = it["suggest"]; n += 1
                self.matrix.log(it["id"], f"decision {it['decision']} (accepted suggestion)")
        diag.activity("compliance_accepted", n=n, items=learned)
        self._c_changed()
        self._cwin.lbl.configure(text=self._cwin.lbl.cget("text") + f"  |  {n} suggestions accepted ({learned} learned); Review rows stay undecided")

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
            diag.activity("compliance_read", files=len(paths), items=len(items))
            msg = f"{len(items)} candidate requirements from {len(paths)} file(s)."
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
                    if L.learn(M.path, M.items):
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
        n = L.learn(M.path, M.items)
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
        messagebox.showinfo("Learn from decisions", msg, parent=self._cwin)

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
