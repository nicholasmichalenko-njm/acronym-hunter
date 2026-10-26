"""Compliance in passes (2.32.0): Decide in Page view, Place one sentence at a time, details on Prove.

Decide: the RFP reads like a page. Each sentence is shaded by its decision (green Keep, blue Context, grey Drop,
amber underline while undecided), the current one is outlined, compliance words show in the user's style. A dock at
the bottom: Accept the suggestion (Enter), Keep (K), Context (C), Drop (D), Back (Backspace), Split (S); after each
decision the next undecided sentence comes up. Click a sentence to jump to it; click between two of its words (or
select words) and press S to split there.

Place (a second pass): one Keep or Context sentence at a time, with the sentences around it faded; the top 3 sections
from past proposals (and the rules' match) on keys 1, 2 and 3; place a whole run of the same RFP paragraph at once.

Prove: owner, status and response page for each kept requirement, set here instead of during triage.
The hidden requirements table stays the selection model, so every existing action works the same.
"""
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
import diag
import cwords as CW

DEC_BG = {"Keep": "#BBF7D0", "Context": "#BFDBFE", "Drop": "#E5E7EB"}
WHY = {"Keep": "reads as a requirement", "Context": "not a requirement, may help the authors", "Drop": "boilerplate or marking",
       "Review": "unclear: your call"}


class CompliancePageMixin:
    # ------------------------------------------------------------ Decide: build
    def _cp_build_decide(self, rq, body):
        win = self._cwin
        win.c_flt.pack_forget()
        win.c_left.pack_forget()
        win.c_right.pack_forget()
        win.cp_file = None
        win.cp_sig = None
        win.cp_hist = []
        dock = ctk.CTkFrame(rq, corner_radius=10, fg_color=("#0F172A", "#0B1220"))
        dock.pack(side="bottom", fill="x", pady=(6, 0), before=body)
        info = ctk.CTkFrame(dock, fg_color="transparent"); info.pack(side="left", fill="x", expand=True, padx=14, pady=8)
        win.cp_l1 = ctk.CTkLabel(info, text="", anchor="w", text_color="#94A3B8", font=("Segoe UI", 12))
        win.cp_l1.pack(fill="x")
        win.cp_l2 = ctk.CTkLabel(info, text="", anchor="w", text_color="#E2E8F0", font=("Segoe UI", 14))
        win.cp_l2.pack(fill="x")
        B = dict(height=40, font=("Segoe UI", 14, "bold"), width=10)
        win.cp_accept = ctk.CTkButton(dock, text="Accept  (Enter)", command=self.cp_accept, fg_color="#F8FAFC",
                                      text_color="#0F172A", hover_color="#E2E8F0", **B)
        win.cp_accept.pack(side="left", padx=4, pady=8)
        for text, dec, color in (("Keep  K", "Keep", "#15803D"), ("Context  C", "Context", "#1D4ED8"), ("Drop  D", "Drop", "#475569")):
            ctk.CTkButton(dock, text=text, command=lambda d=dec: self.cp_decide(d), fg_color=color, **B).pack(side="left", padx=4)
        G = dict(height=40, width=10, fg_color="transparent", border_width=1, border_color="#334155", text_color="#CBD5E1",
                 hover_color="#1E293B")
        ctk.CTkButton(dock, text="Back", command=self.cp_back, **G).pack(side="left", padx=4)
        ctk.CTkButton(dock, text="Split  S", command=self.cp_split, **G).pack(side="left", padx=(4, 12))

        wrap = ctk.CTkFrame(body, fg_color="transparent"); wrap.pack(fill="both", expand=True)
        side = ctk.CTkScrollableFrame(wrap, width=290); side.pack(side="right", fill="y", padx=(8, 0))
        page = ctk.CTkFrame(wrap, corner_radius=12, fg_color=("#FFFFFF", "#111827")); page.pack(side="left", fill="both", expand=True)
        win.cp_src = ctk.CTkLabel(page, text="", anchor="w", text_color=("#64748B", "#94A3B8"))
        win.cp_src.pack(fill="x", padx=18, pady=(10, 0))
        dpi = max(1.0, float(ctk.ScalingTracker.get_widget_scaling(page)))
        size = int(round((getattr(self, "font_size", 13) + 3) * dpi))
        t = tk.Text(page, wrap="word", relief="flat", bd=0, padx=26, pady=12, font=("Georgia", size), spacing1=2,
                    spacing2=int(6 * dpi), spacing3=int(4 * dpi), bg="#FFFFFF", fg="#1E293B", cursor="arrow",
                    insertwidth=0, highlightthickness=0, exportselection=False)
        sb = ttk.Scrollbar(page, orient="vertical", command=t.yview); t.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); t.pack(fill="both", expand=True, pady=(0, 8))
        win.cp_text = t
        t.tag_configure("head", font=("Segoe UI", max(10, size - 3), "bold"), spacing1=int(14 * dpi), spacing3=int(2 * dpi))
        for dec, bg in DEC_BG.items():
            t.tag_configure("d_" + dec, background=bg)
        t.tag_configure("d_Drop", foreground="#6B7280")
        t.tag_configure("d_", background="#FFFBEB", underline=True)
        try:
            t.tag_configure("d_", underlinefg="#F59E0B")
        except tk.TclError:
            diag.swallowed()
        t.tag_configure("cur", relief="solid", borderwidth=2, background="#FEF3C7")
        t.tag_raise("cur")
        t.bind("<ButtonRelease-1>", self._cp_click)
        t.bind("<Key>", self._cp_key)
        for seq in ("<Control-c>", "<Control-a>"):
            t.bind(seq, lambda _e: None)
        win.cp_head = ctk.CTkLabel(side, text="", font=("Segoe UI", 14, "bold"), anchor="w", justify="left", wraplength=270)
        win.cp_head.pack(fill="x", padx=8, pady=(6, 2))
        win.cp_where = ctk.CTkLabel(side, text="", anchor="w", justify="left", wraplength=270, text_color=("#475569", "#94A3B8"))
        win.cp_where.pack(fill="x", padx=8)
        r = ctk.CTkFrame(side, fg_color="transparent"); r.pack(fill="x", padx=8, pady=(6, 10))
        ctk.CTkButton(r, text="Show page", width=90, command=self.compliance_show_page).pack(side="left")
        ctk.CTkButton(r, text="Open file", width=90, command=self.compliance_open_file).pack(side="left", padx=6)
        self._cp_card_title(side, "Highlighter key")
        for txt, bg in (("Keep: a requirement", "#BBF7D0"), ("Context: authors need it", "#BFDBFE"), ("Drop: not needed", "#E5E7EB"),
                        ("Not decided yet", "#FFFBEB")):
            row = ctk.CTkFrame(side, fg_color="transparent"); row.pack(fill="x", padx=8, pady=1)
            ctk.CTkLabel(row, text="", width=26, height=14, fg_color=bg, corner_radius=3).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(row, text=txt, anchor="w").pack(side="left")
        self._cp_card_title(side, "Clear the easy ones first")
        win.cp_boiler = ctk.CTkLabel(side, text="", anchor="w", justify="left", wraplength=270)
        win.cp_boiler.pack(fill="x", padx=8)
        win.cp_boiler_btn = ctk.CTkButton(side, text="Drop them all...", command=self.cp_drop_boilerplate, width=10,
                                          fg_color=("#E2E8F0", "#334155"), text_color=("#0F172A", "#F1F5F9"),
                                          hover_color=("#CBD5E1", "#475569"))
        win.cp_boiler_btn.pack(anchor="w", padx=8, pady=(4, 0))
        self._cp_card_title(side, "Files")
        win.cp_files = ctk.CTkFrame(side, fg_color="transparent"); win.cp_files.pack(fill="x", padx=4)

    @staticmethod
    def _cp_card_title(parent, text):
        ctk.CTkLabel(parent, text=text, font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x", padx=8, pady=(12, 4))

    # ------------------------------------------------------------ Decide: render
    def _cp_items_of(self, f):
        return [it for it in self.matrix.items if it.get("file", "") == f]

    def _cp_files(self):
        out = []
        for it in self.matrix.items:
            f = it.get("file", "")
            if f not in out:
                out.append(f)
        return out

    def _cp_sync(self):
        """Redraw the page when its sentences changed; otherwise just refresh the shading and the side panel."""
        win = self._cwin
        if win is None or not hasattr(win, "cp_text"):
            return
        M = self.matrix
        if M is None or not M.items:
            win.cp_text.configure(state="normal"); win.cp_text.delete("1.0", "end"); win.cp_text.configure(state="disabled")
            win.cp_l1.configure(text="No matrix yet"); win.cp_l2.configure(text="Read the RFP first (step 1).")
            return
        files = self._cp_files()
        if win.cp_file not in files:
            sel = self._c_selected()
            win.cp_file = sel[0].get("file", "") if sel else files[0]
        rows = self._cp_items_of(win.cp_file)
        sig = (win.cp_file, tuple((it["id"], it["text"]) for it in rows))
        if sig != win.cp_sig:
            self._cp_render(rows)
            win.cp_sig = sig
        else:
            self._cp_shade(rows)
        self._cp_side()

    def _cp_render(self, rows):
        win = self._cwin
        t = win.cp_text
        t.configure(state="normal")
        t.delete("1.0", "end")
        cfg = CW.load()
        font, fg, bg = CW.tk_font_options(cfg, "Georgia", int(t.cget("font").split()[-1]) if str(t.cget("font")).split()[-1].isdigit() else 16)
        try:
            import tkinter.font as tkfont
            f = tkfont.Font(font=t.cget("font"))
            font, fg, bg = CW.tk_font_options(cfg, f.actual("family"), f.actual("size"))
        except Exception:
            diag.swallowed()
        opts = {"font": font}
        if fg:
            opts["foreground"] = fg
        if bg:
            opts["background"] = bg
        t.tag_configure("cword", **opts)
        t.tag_raise("cword")
        head = None
        for it in rows:
            h = " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
            if h and h != head:
                if t.index("end-1c") != "1.0":
                    t.insert("end", "\n")
                t.insert("end", h + "\n", ("head",))
                head = h
            start = t.index("end-1c")
            for piece, w in CW.segments(it["text"], cfg):
                t.insert("end", piece, ("cword",) if w else ())
            end = t.index("end-1c")
            t.tag_add("r:" + it["id"], start, end)
            t.tag_add("d_" + (it["decision"] or ""), start, end)
            t.insert("end", "  ")
        t.tag_raise("cur")
        t.configure(state="disabled")
        win.cp_src.configure(text=f"{win.cp_file}: {len(rows)} sentences. Click a sentence to jump to it; click between two of "
                                  "its words, then S, to split.")
        sel = self._c_selected()
        if sel:
            self._cp_mark(sel[0])

    def _cp_shade(self, rows):
        t = self._cwin.cp_text
        for dec in ("Keep", "Context", "Drop", ""):
            t.tag_remove("d_" + dec, "1.0", "end")
        for it in rows:
            r = t.tag_ranges("r:" + it["id"])
            if r:
                t.tag_add("d_" + (it["decision"] or ""), r[0], r[1])

    def _cp_mark(self, it):
        win = self._cwin
        t = win.cp_text
        t.tag_remove("cur", "1.0", "end")
        r = t.tag_ranges("r:" + it["id"])
        if r:
            t.tag_add("cur", r[0], r[1])
            t.see(r[0])

    def _cp_side(self):
        win, M = self._cwin, self.matrix
        boiler = [it for it in M.items if not it["decision"] and it.get("type") == "Context" and it.get("suggest") == "Drop"]
        win.cp_boiler.configure(text=f"{len(boiler)} page headers, page numbers and markings look like boilerplate."
                                if boiler else "No undecided boilerplate left.")
        win.cp_boiler_btn.configure(state="normal" if boiler else "disabled",
                                    text=f"Drop all {len(boiler)}..." if boiler else "Drop them all...")
        for w in win.cp_files.winfo_children():
            w.destroy()
        for f in self._cp_files():
            rows = self._cp_items_of(f)
            done = sum(1 for it in rows if it["decision"])
            pct = int(done * 100 / len(rows)) if rows else 0
            on = f == win.cp_file
            ctk.CTkButton(win.cp_files, text=f"{f[:30]}   {pct}%", anchor="w", width=270, height=28,
                          fg_color=("#DBEAFE", "#1E3A8A") if on else "transparent", text_color=("#0F172A", "#F1F5F9"),
                          hover_color=("#E2E8F0", "#334155"), command=lambda f=f: self.cp_open_file(f)).pack(fill="x", pady=1)

    def _cp_show(self, it):
        """The current sentence changed (selection): move the outline, follow its file, update the dock."""
        win = self._cwin
        if not hasattr(win, "cp_text"):
            return
        if it.get("file", "") != win.cp_file:
            win.cp_file = it.get("file", "")
            self._cp_sync()
        self._cp_mark(it)
        rows = self._cp_items_of(win.cp_file)
        n = next((i for i, x in enumerate(rows, 1) if x["id"] == it["id"]), 0)
        sug = it.get("suggest", "")
        win.cp_l1.configure(text=f"Sentence {n} of {len(rows)} in {win.cp_file}" + (f", now {it['decision']}" if it["decision"] else ", not decided"))
        win.cp_l2.configure(text=f"Suggested: {sug}  ({WHY.get(sug, '')})" if sug else "No suggestion")
        win.cp_accept.configure(text=f"Accept {sug}  (Enter)" if sug in ("Keep", "Context", "Drop") else "Accept  (Enter)",
                                state="normal" if sug in ("Keep", "Context", "Drop") else "disabled")
        win.cp_head.configure(text=f"{it['id']}   {it['type']}" + (f"   {it['actor']}" if it.get("actor") else ""))
        sec = " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
        win.cp_where.configure(text=(it.get("loc") or "") + (f"\nSection {sec}" if sec else ""))

    # ------------------------------------------------------------ Decide: actions
    def cp_open_file(self, f):
        win = self._cwin
        win.cp_file = f
        self._cp_sync()
        rows = self._cp_items_of(f)
        first = next((it for it in rows if not it["decision"]), rows[0] if rows else None)
        if first is not None:
            self._cp_select(first["id"])

    def _cp_select(self, iid):
        tv = self._cwin.tv
        if tv.exists(iid):
            tv.selection_set(iid); tv.focus(iid)
            self._c_show()

    def _cp_click(self, e):
        win = self._cwin
        t = win.cp_text
        t.focus_set()
        ix = t.index(f"@{e.x},{e.y}")
        hit = next((tag[2:] for tag in t.tag_names(ix) if tag.startswith("r:")), None)
        if not hit:
            return
        sel = self._c_selected()
        if sel and sel[0]["id"] == hit:              # a click inside the current sentence: where to split
            r = t.tag_ranges("r:" + hit)
            def off(i):
                return int(t.count(r[0], i, "chars")[0]) if t.compare(i, ">", r[0]) else 0
            if t.tag_ranges("sel") and t.compare("sel.first", ">=", r[0]) and t.compare("sel.last", "<=", r[1]):
                self._c_split_at = (off("sel.first"), off("sel.last"))
            else:
                self._c_split_at = (off(ix), None)
            return
        self._cp_select(hit)

    def _cp_key(self, e):
        k = (e.keysym or "").lower()
        if k in ("k", "c", "d"):
            self.cp_decide({"k": "Keep", "c": "Context", "d": "Drop"}[k])
        elif k == "u":
            self.compliance_decide("")
        elif k in ("return", "kp_enter"):
            self.cp_accept()
        elif k == "backspace":
            self.cp_back()
        elif k == "s":
            self.cp_split()
        elif k == "m":
            self.compliance_merge()
        elif k == "n":
            self.compliance_next_undecided()
        elif k in ("down", "right"):
            self._cp_step(+1)
        elif k in ("up", "left"):
            self._cp_step(-1)
        elif k in ("next", "prior", "home", "end"):
            return None
        return "break"

    def _cp_step(self, d):
        sel = self._c_selected()
        rows = self._cp_items_of(self._cwin.cp_file)
        if not rows:
            return
        i = next((i for i, x in enumerate(rows) if sel and x["id"] == sel[0]["id"]), -1)
        j = max(0, min(len(rows) - 1, i + d))
        self._cp_select(rows[j]["id"])

    def cp_decide(self, decision):
        sel = self._c_selected()
        if len(sel) == 1:
            self._cwin.cp_hist.append(sel[0]["id"])
        self.compliance_decide(decision)
        self._cwin.cp_text.focus_set()

    def cp_accept(self):
        sel = self._c_selected()
        if len(sel) == 1 and sel[0].get("suggest") in ("Keep", "Context", "Drop"):
            self.cp_decide(sel[0]["suggest"])

    def cp_back(self):
        h = self._cwin.cp_hist
        while h:
            iid = h.pop()
            if self._cwin.tv.exists(iid):
                self._cp_select(iid)
                return

    def cp_split(self):
        self.compliance_split()
        self._cwin.cp_text.focus_set()

    def cp_drop_boilerplate(self, ask=True):
        M = self.matrix
        rows = [it for it in M.items if not it["decision"] and it.get("type") == "Context" and it.get("suggest") == "Drop"]
        if not rows:
            return 0
        if ask:
            sample = "\n".join(f"  {it['text'][:70]}" for it in rows[:12]) + (f"\n  ... and {len(rows) - 12} more" if len(rows) > 12 else "")
            if not messagebox.askyesno("Clear the easy ones", f"Drop these {len(rows)} sentences?\n\n{sample}", parent=self._cwin):
                return 0
        for it in rows:
            it["decision"] = "Drop"
            M.log(it["id"], "decision Drop (boilerplate, accepted)")
        diag.activity("compliance_boilerplate_dropped", n=len(rows))
        self._c_changed()
        return len(rows)

    # ------------------------------------------------------------ Place: a second pass
    def _cp_build_place(self, fr):
        win = self._cwin
        win.pl_cur = None
        top = ctk.CTkFrame(fr, fg_color="transparent"); top.pack(fill="x")
        win.pl_count = ctk.CTkLabel(top, text="", font=("Segoe UI", 14, "bold"), anchor="w")
        win.pl_count.pack(side="left", padx=6, pady=(4, 6))
        ctk.CTkButton(top, text="Arrange the setup (order, direction, references)...", width=10, fg_color="#475569",
                      command=lambda: self._cwin.tabs.set("Setup")).pack(side="right", padx=6)
        body = ctk.CTkFrame(fr, fg_color="transparent"); body.pack(fill="both", expand=True)
        out = ctk.CTkScrollableFrame(body, width=330); out.pack(side="right", fill="y", padx=(8, 0))
        win.pl_outline = out
        card = ctk.CTkFrame(body, corner_radius=12, fg_color=("#FFFFFF", "#111827")); card.pack(side="left", fill="both", expand=True)
        win.pl_card = card
        win.pl_kind = ctk.CTkLabel(card, text="", anchor="w", font=("Segoe UI", 13, "bold"))
        win.pl_kind.pack(fill="x", padx=22, pady=(16, 4))
        mut = ("#94A3B8", "#64748B")
        win.pl_before = ctk.CTkLabel(card, text="", anchor="w", justify="left", wraplength=760, text_color=mut, font=("Georgia", 14))
        win.pl_before.pack(fill="x", padx=22)
        win.pl_text = ctk.CTkLabel(card, text="", anchor="w", justify="left", wraplength=760, font=("Georgia", 20))
        win.pl_text.pack(fill="x", padx=22, pady=8)
        win.pl_after = ctk.CTkLabel(card, text="", anchor="w", justify="left", wraplength=760, text_color=mut, font=("Georgia", 14))
        win.pl_after.pack(fill="x", padx=22)
        win.pl_band = ctk.CTkLabel(card, text="", anchor="w", font=("Segoe UI", 13, "bold"))
        win.pl_band.pack(fill="x", padx=22, pady=(16, 4))
        win.pl_choices = ctk.CTkFrame(card, fg_color="transparent"); win.pl_choices.pack(fill="x", padx=18)
        row = ctk.CTkFrame(card, fg_color="transparent"); row.pack(fill="x", padx=22, pady=(10, 16))
        win.pl_run = ctk.CTkButton(row, text="", command=self.pl_place_run, fg_color=("#EFF6FF", "#1E3A8A"),
                                   text_color=("#1E3A8A", "#DBEAFE"), border_width=1, border_color="#1E3A8A", width=10)
        win.pl_run.pack(side="left")
        win.pl_other = ctk.CTkComboBox(row, values=[""], width=300)
        win.pl_other.pack(side="left", padx=(14, 4))
        ctk.CTkButton(row, text="Place here", width=90, command=lambda: self.pl_place(win.pl_other.get().strip())).pack(side="left")
        ctk.CTkButton(row, text="Later  (Space)", width=10, command=self.pl_skip, fg_color="transparent", border_width=1,
                      text_color=("#334155", "#CBD5E1")).pack(side="left", padx=10)
        tk.Misc.bind(card, "<Key>", self._pl_key)          # the frame itself takes the focus and the keys
        for w in (card, win.pl_text, win.pl_before, win.pl_after):
            w.bind("<Button-1>", lambda _e: self._cwin.pl_card.focus_set(), add="+")

    def _pl_queue(self):
        M = self.matrix
        return [it for it in M.items if it["decision"] in ("Keep", "Context") and not it["map"]]

    def pl_refresh(self):
        """Show the next sentence that needs a home (or the current one if it still needs one)."""
        win, M = self._cwin, self.matrix
        if win is None or not hasattr(win, "pl_card"):
            return
        labels = [o["num"] + " " + o["title"] if o["num"] else o["title"] for o in (M.outline if M else [])]
        win.pl_other.configure(values=[""] + labels)
        self._pl_outline()
        if M is None or not M.items:
            win.pl_count.configure(text="No matrix yet.")
            return
        if not M.outline:
            win.pl_count.configure(text="Set the outline first (step 3).")
            return
        q = self._pl_queue()
        win.pl_count.configure(text=(f"{len(q)} Keep and Context sentences still need a home" if q
                                     else "✓ Every Keep and Context sentence has a home."))
        cur = next((it for it in q if it["id"] == win.pl_cur), None) or (q[0] if q else None)
        win.pl_cur = cur["id"] if cur else None
        for w in win.pl_choices.winfo_children():
            w.destroy()
        if cur is None:
            for w in (win.pl_kind, win.pl_before, win.pl_text, win.pl_after, win.pl_band):
                w.configure(text="")
            win.pl_run.configure(text="Nothing left to place", state="disabled")
            return
        rows = self._cp_items_of(cur.get("file", ""))
        i = next((k for k, x in enumerate(rows) if x["id"] == cur["id"]), 0)
        win.pl_kind.configure(text=f"{cur['decision']}   {cur['id']}   " + " ".join(x for x in (cur.get("section", ""), cur.get("section_title", "")) if x),
                              text_color="#15803D" if cur["decision"] == "Keep" else "#1D4ED8")
        win.pl_before.configure(text=rows[i - 1]["text"] if i > 0 else "")
        win.pl_text.configure(text=cur["text"])
        win.pl_after.configure(text=rows[i + 1]["text"] if i + 1 < len(rows) else "")
        choices = []
        ranked = self._c_learned_places(cur) if hasattr(self, "_c_learned_places") else []
        band = __import__("placelearn").Placer.band(ranked) if ranked else ""
        rule, _s = self._c_suggest(cur)
        if rule:
            choices.append((rule, "the rules: same RFP number or title words"))
        for lab, sc in ranked:
            if lab not in [c[0] for c in choices]:
                choices.append((lab, "from past proposals" + (" (strong)" if band == "strong" and lab == ranked[0][0] else "")))
        choices = choices[:3]
        win.pl_band.configure(text=("Press 1, 2 or 3, or pick another section." if choices
                                    else "No suggestion: pick a section below, or drag it on the Setup board."))
        win.pl_keys = [c[0] for c in choices]
        for k, (lab, why) in enumerate(choices, 1):
            b = ctk.CTkButton(win.pl_choices, text=f"{k}.  {lab}        {why}", anchor="w", height=44, font=("Segoe UI", 14),
                              fg_color=("#F0FDF4", "#14532D") if k == 1 else ("#FFFFFF", "#1F2937"), border_width=1,
                              border_color="#15803D" if k == 1 else "#CBD5E1", text_color=("#0F172A", "#F1F5F9"),
                              hover_color=("#E2E8F0", "#334155"), command=lambda lab=lab: self.pl_place(lab))
            b.pack(fill="x", padx=4, pady=3)
        run = self._pl_run_rows(cur)
        win.pl_run.configure(text=f"Place all {len(run)} sentences of {cur.get('section') or 'this paragraph'} in choice 1"
                             if len(run) > 1 and choices else "Place the run (needs a choice 1)",
                             state="normal" if len(run) > 1 and choices else "disabled")
        win.pl_card.focus_set()

    def _pl_run_rows(self, cur):
        """Sentences around this one that come from the same RFP section and still need a home."""
        sec, f = cur.get("section", ""), cur.get("file", "")
        return [it for it in self._pl_queue() if it.get("file", "") == f and it.get("section", "") == sec] if sec else [cur]

    def _pl_outline(self):
        win, M = self._cwin, self.matrix
        for w in win.pl_outline.winfo_children():
            w.destroy()
        ctk.CTkLabel(win.pl_outline, text="Proposal outline", font=("Segoe UI", 13, "bold"), anchor="w").pack(fill="x", padx=4, pady=(4, 6))
        if M is None:
            return
        for o in M.outline:
            lab = (o["num"] + " " + o["title"]).strip()
            n = sum(1 for it in M.items if it["decision"] in ("Keep", "Context") and it["map"] == lab)
            row = ctk.CTkFrame(win.pl_outline, fg_color=("#DCFCE7", "#14532D") if lab == getattr(win, "pl_flash", "") else "transparent")
            row.pack(fill="x", padx=(4 + 14 * max(0, o["level"] - 1), 4), pady=1)
            ctk.CTkLabel(row, text=lab, anchor="w", font=("Segoe UI", 12, "bold" if o["level"] == 1 else "normal")).pack(side="left")
            ctk.CTkLabel(row, text=str(n), anchor="e").pack(side="right")

    def pl_place(self, label, rows=None):
        win, M = self._cwin, self.matrix
        known = {(o["num"] + " " + o["title"]).strip() for o in M.outline}
        if not label or label not in known:
            return 0
        cur = next((it for it in M.items if it["id"] == win.pl_cur), None)
        rows = rows or ([cur] if cur else [])
        for it in rows:
            it["map"] = label
            M.log(it["id"], f"mapped to {label} (placed)")
        win.pl_flash = label
        diag.activity("compliance_placed", n=len(rows))
        self._c_changed(refill=False)
        win.pl_cur = None
        self.pl_refresh()
        return len(rows)

    def pl_place_run(self):
        win = self._cwin
        cur = next((it for it in self.matrix.items if it["id"] == win.pl_cur), None)
        if cur is None or not getattr(win, "pl_keys", None):
            return 0
        return self.pl_place(win.pl_keys[0], self._pl_run_rows(cur))

    def pl_skip(self):
        win = self._cwin
        q = self._pl_queue()
        ids = [it["id"] for it in q]
        if win.pl_cur in ids and len(ids) > 1:
            win.pl_cur = ids[(ids.index(win.pl_cur) + 1) % len(ids)]
        self.pl_refresh()

    def _pl_key(self, e):
        k = (e.keysym or "").lower()
        win = self._cwin
        if k in ("1", "2", "3", "kp_1", "kp_2", "kp_3"):
            i = int(k[-1]) - 1
            if i < len(getattr(win, "pl_keys", [])):
                self.pl_place(win.pl_keys[i])
        elif k == "space":
            self.pl_skip()
        return "break"

    # ------------------------------------------------------------ Prove: owner, status, response page
    def _cp_build_details(self, fr):
        win = self._cwin
        ctk.CTkLabel(fr, text="Owner, status and response page", font=("Segoe UI", 15, "bold"), anchor="w").pack(fill="x", padx=6, pady=(16, 2))
        ctk.CTkLabel(fr, text="Select one or more kept requirements, type, then Apply.", anchor="w",
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=6)
        tf = tk.Frame(fr); tf.pack(fill="both", expand=True, padx=6, pady=4)
        cols = (("id", "ID", 90), ("text", "Requirement", 520), ("map", "Section", 180), ("owner", "Owner", 110),
                ("status", "Status", 100), ("response_page", "Page", 70))
        tv = ttk.Treeview(tf, columns=[c[0] for c in cols], show="headings", height=8, style="Cm.Treeview")
        for k, h, w in cols:
            tv.heading(k, text=h); tv.column(k, width=w, anchor="w", stretch=k == "text")
        sb = ttk.Scrollbar(tf, orient="vertical", command=tv.yview); tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); tv.pack(fill="both", expand=True)
        win.pv_tv = tv
        row = ctk.CTkFrame(fr, fg_color="transparent"); row.pack(fill="x", padx=6, pady=(4, 8))
        win.pv_fields = {}
        for lab, key, w in (("Owner", "owner", 150), ("Status", "status", 130), ("Response page", "response_page", 90), ("Notes", "notes", 240)):
            ctk.CTkLabel(row, text=lab).pack(side="left", padx=(8, 4))
            e = ctk.CTkEntry(row, width=w); e.pack(side="left")
            win.pv_fields[key] = e
        ctk.CTkButton(row, text="Apply to selected", width=10, command=self.pv_apply).pack(side="left", padx=10)
        tv.bind("<<TreeviewSelect>>", lambda _e: self._pv_fill_fields())

    def pv_refresh(self):
        win, M = self._cwin, self.matrix
        if win is None or not hasattr(win, "pv_tv"):
            return
        tv = win.pv_tv
        sel = tv.selection()
        tv.delete(*tv.get_children())
        if M is None:
            return
        for it in M.items:
            if it["decision"] == "Keep":
                tv.insert("", "end", iid=it["id"], values=(it["id"], it["text"][:200], it["map"], it.get("owner", ""),
                                                           it.get("status", ""), it.get("response_page", "")))
        keep = [s for s in sel if tv.exists(s)]
        if keep:
            tv.selection_set(keep)

    def _pv_fill_fields(self):
        win = self._cwin
        sel = win.pv_tv.selection()
        items = [self._c_item(i) for i in sel]
        for key, e in win.pv_fields.items():
            e.delete(0, "end")
            vals = {it.get(key, "") for it in items if it}
            if len(vals) == 1:
                e.insert(0, vals.pop())

    def pv_apply(self):
        win, M = self._cwin, self.matrix
        sel = [self._c_item(i) for i in win.pv_tv.selection()]
        sel = [it for it in sel if it]
        if not sel:
            return 0
        for key, e in win.pv_fields.items():
            v = e.get().strip()
            for it in sel:
                if v != it.get(key, "") and (v or len(sel) == 1):
                    it[key] = v
                    M.log(it["id"], f"{key} set")
        diag.activity("compliance_details_set", n=len(sel))
        self._c_changed(refill=False)
        self.pv_refresh()
        return len(sel)
