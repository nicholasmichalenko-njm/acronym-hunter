"""Compliance in passes (2.32.0): Decide in Page view, Place one sentence at a time, details on Prove.

Decide: the RFP reads like a page. Each sentence is shaded by its decision (green Keep, blue Context, grey Drop,
pale amber while undecided), the current one is outlined, compliance words show in the user's style. A dock at
the bottom: Accept the suggestion (Enter), Keep (K), Context (C), Drop (D), Link (L), Back, Split (S), Commit.
Click a sentence to jump to it; click between two of its words (or select words) and press S to split there.

2.35.0 draft and commit: every decision is first a draft (lighter shading, underlined in the decision's color), saved
like any change, and counts once committed (solid shading). Commit what is on screen (Ctrl+Enter), the selected
sentences, the RFP section, the file or every draft; the dock says what was committed and how many drafts are left.
Drag across several sentences and one key decides, links or commits them all. Link mode stays open: L on a Context
sentence, then click every requirement it explains (click again to remove), Enter or Esc when done; L on a requirement
picks its Context sentences the same way. Pointing at a sentence lights up its links. The strip beside the page maps
the file: grey undecided, amber draft, green committed; click it to jump.

Place (a second pass): one Keep or Context sentence at a time, with the sentences around it faded; the top 3 sections
from past proposals (and the rules' match) on keys 1, 2 and 3; place a whole run of the same RFP paragraph at once.

Prove: owner, status and response page for each kept requirement, set here instead of during triage.
The hidden requirements table stays the selection model, so every existing action works the same.
"""
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
import compliance as C
import diag
import cwords as CW

DEC_BG = {"Keep": "#BBF7D0", "Context": "#BFDBFE", "Drop": "#E5E7EB"}
DRAFT_BG = {"Keep": "#E9FBEF", "Context": "#E6F0FE", "Drop": "#F3F4F6"}
DRAFT_LINE = {"Keep": "#15803D", "Context": "#1D4ED8", "Drop": "#6B7280"}
UNDECIDED_BG = "#FFFBEB"
STRIP = {"": "#CBD5E1", "draft": "#F59E0B", "done": "#22C55E"}
WHY = {"Keep": "reads as a requirement", "Context": "not a requirement, may help the authors", "Drop": "boilerplate or marking",
       "Review": "unclear: your call"}


def _tag(it):
    """The shading tag of a row: d_<decision> when committed (d_ when undecided), p_<decision> while a draft."""
    if it.get("draft"):
        return "p_" + C.eff(it)
    return "d_" + (it.get("decision") or "")


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
        win.cp_range = []
        win.cp_hover = None
        win.cp_msg_after = None
        dock = ctk.CTkFrame(rq, corner_radius=10, fg_color=("#0F172A", "#0B1220"))
        dock.pack(side="bottom", fill="x", pady=(6, 0), before=body)
        info = ctk.CTkFrame(dock, fg_color="transparent"); info.pack(side="top", fill="x", padx=14, pady=(8, 0))
        keys = ctk.CTkFrame(dock, fg_color="transparent"); keys.pack(side="top", fill="x", padx=10, pady=(2, 8))
        win.cp_l0 = ctk.CTkLabel(info, text="", anchor="w", text_color="#86EFAC", font=("Segoe UI", 12, "bold"))
        win.cp_l1 = ctk.CTkLabel(info, text="", anchor="w", text_color="#94A3B8", font=("Segoe UI", 12))
        win.cp_l1.pack(fill="x")
        win.cp_l2 = ctk.CTkLabel(info, text="", anchor="w", text_color="#E2E8F0", font=("Segoe UI", 14))
        win.cp_l2.pack(fill="x")
        win.cp_l3 = ctk.CTkLabel(info, text="", anchor="w", text_color="#93C5FD", font=("Segoe UI", 12), justify="left", wraplength=640)
        win.cp_linking = None
        B = dict(height=40, font=("Segoe UI", 14, "bold"), width=10)
        win.cp_accept = ctk.CTkButton(keys, text="Accept  (Enter)", command=self.cp_accept, fg_color="#F8FAFC",
                                      text_color="#0F172A", hover_color="#E2E8F0", **B)
        win.cp_accept.pack(side="left", padx=4)
        for text, dec, color in (("Keep  K", "Keep", "#15803D"), ("Context  C", "Context", "#1D4ED8"), ("Drop  D", "Drop", "#475569")):
            ctk.CTkButton(keys, text=text, command=lambda d=dec: self.cp_decide(d), fg_color=color, **B).pack(side="left", padx=4)
        G = dict(height=40, width=10, fg_color="transparent", border_width=1, border_color="#334155", text_color="#CBD5E1",
                 hover_color="#1E293B")
        win.cp_link_btn = ctk.CTkButton(keys, text="Link  L", command=self.cp_link_start, **G)
        win.cp_link_btn.pack(side="left", padx=4)
        ctk.CTkButton(keys, text="Back", command=self.cp_back, **G).pack(side="left", padx=4)
        ctk.CTkButton(keys, text="Split  S", command=self.cp_split, **G).pack(side="left", padx=4)
        win.cp_commit_btn = ctk.CTkButton(keys, text="Commit  Ctrl+Enter", command=self.cp_commit_default, height=40, width=10,
                                          fg_color="transparent", border_width=2, border_color="#22C55E", text_color="#86EFAC",
                                          hover_color="#14532D", font=("Segoe UI", 13, "bold"))
        win.cp_commit_btn.pack(side="left", padx=(12, 4))

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
        sb.pack(side="right", fill="y")
        strip = tk.Canvas(page, width=int(14 * dpi), highlightthickness=0, bd=0, bg="#F8FAFC", cursor="hand2")
        strip.pack(side="right", fill="y", pady=(0, 8))
        win.cp_strip = strip
        strip.bind("<Configure>", lambda _e: self._cp_strip())
        strip.bind("<Button-1>", self._cp_strip_click)
        t.pack(fill="both", expand=True, pady=(0, 8))
        win.cp_text = t
        t.tag_configure("head", font=("Segoe UI", max(10, size - 3), "bold"), spacing1=int(14 * dpi), spacing3=int(2 * dpi))
        for dec, bg in DEC_BG.items():
            t.tag_configure("d_" + dec, background=bg)
        t.tag_configure("d_Drop", foreground="#6B7280")
        t.tag_configure("d_", background=UNDECIDED_BG)
        t.tag_configure("p_", background=UNDECIDED_BG)
        for dec, bg in DRAFT_BG.items():
            t.tag_configure("p_" + dec, background=bg, underline=True)
            try:
                t.tag_configure("p_" + dec, underlinefg=DRAFT_LINE[dec])
            except tk.TclError:
                diag.swallowed()
        t.tag_configure("p_Drop", foreground="#6B7280")
        t.tag_configure("rng", background="#FDE68A")
        t.tag_configure("cur", relief="solid", borderwidth=2, background="#FEF3C7")
        t.tag_configure("linked", relief="ridge", borderwidth=2, foreground="#1E3A8A")   # the requirements a Context explains
        t.tag_configure("hov", relief="ridge", borderwidth=2, foreground="#7C2D12")
        t.tag_raise("rng")
        t.tag_raise("cur")
        t.bind("<ButtonRelease-1>", self._cp_click)
        t.bind("<Key>", self._cp_key)
        t.bind("<Motion>", self._cp_motion)
        t.bind("<Leave>", lambda _e: self._cp_hover(None))
        for seq in ("<Control-c>", "<Control-a>"):
            t.bind(seq, lambda _e: None)
        win.cp_head = ctk.CTkLabel(side, text="", font=("Segoe UI", 14, "bold"), anchor="w", justify="left", wraplength=270)
        win.cp_head.pack(fill="x", padx=8, pady=(6, 2))
        win.cp_where = ctk.CTkLabel(side, text="", anchor="w", justify="left", wraplength=270, text_color=("#475569", "#94A3B8"))
        win.cp_where.pack(fill="x", padx=8)
        r = ctk.CTkFrame(side, fg_color="transparent"); r.pack(fill="x", padx=8, pady=(6, 10))
        ctk.CTkButton(r, text="Show page", width=90, command=self.compliance_show_page).pack(side="left")
        ctk.CTkButton(r, text="Open file", width=90, command=self.compliance_open_file).pack(side="left", padx=6)
        self._cp_card_title(side, "Commit")
        win.cp_dcount = ctk.CTkLabel(side, text="", anchor="w", justify="left", wraplength=270)
        win.cp_dcount.pack(fill="x", padx=8)
        win.cp_cbtns = {}
        for key, label in (("screen", "What is on screen  (Ctrl+Enter)"), ("selected", "The selected sentences"),
                           ("section", "This RFP section"), ("file", "This file"), ("all", "Every draft")):
            b = ctk.CTkButton(side, text=label, anchor="w", width=10, height=26, fg_color=("#DCFCE7", "#14532D"),
                              text_color=("#14532D", "#DCFCE7"), hover_color=("#BBF7D0", "#166534"),
                              command=lambda k=key: self.cp_commit(k))
            b.pack(fill="x", padx=8, pady=1)
            win.cp_cbtns[key] = b
        win.cp_next_var = tk.BooleanVar(value=self._c_auto_next() if hasattr(self, "_c_auto_next") else True)
        ctk.CTkCheckBox(side, text="After Keep or Drop, go to the next\nundecided sentence", variable=win.cp_next_var,
                        command=self._cp_auto_next_set).pack(anchor="w", padx=8, pady=(6, 0))
        self._cp_card_title(side, "Highlighter key")
        for txt, bg, line in (("Keep: a requirement", DEC_BG["Keep"], False), ("Context: authors need it", DEC_BG["Context"], False),
                              ("Drop: not needed", DEC_BG["Drop"], False), ("Draft: underlined, lighter", DRAFT_BG["Keep"], True),
                              ("Not decided yet", UNDECIDED_BG, False)):
            row = ctk.CTkFrame(side, fg_color="transparent"); row.pack(fill="x", padx=8, pady=1)
            ctk.CTkLabel(row, text="__" if line else "", width=26, height=14, fg_color=bg, corner_radius=3,
                         text_color=DRAFT_LINE["Keep"]).pack(side="left", padx=(0, 8))
            ctk.CTkLabel(row, text=txt, anchor="w").pack(side="left")
        ctk.CTkLabel(side, text="The strip beside the page: grey undecided, amber draft, green committed.", anchor="w",
                     justify="left", wraplength=270, text_color=("#475569", "#94A3B8")).pack(fill="x", padx=8, pady=(4, 0))
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

    def _cp_auto_next_set(self):
        try:
            self.ws.set("compliance_auto_next", bool(self._cwin.cp_next_var.get()))
        except Exception:
            diag.swallowed()

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
            t.tag_add(_tag(it), start, end)
            t.insert("end", "  ")
        t.tag_raise("rng")
        t.tag_raise("cur")
        t.configure(state="disabled")
        win.cp_range = [i for i in win.cp_range if t.tag_ranges("r:" + i)]
        win.cp_src.configure(text=f"{win.cp_file}: {len(rows)} sentences. Click a sentence to jump to it; drag across several "
                                  "to decide them together; click between two words, then S, to split.")
        sel = self._c_selected()
        if sel:
            self._cp_mark(sel[0])
        self._cp_strip()

    def _cp_shade(self, rows):
        t = self._cwin.cp_text
        for dec in ("Keep", "Context", "Drop", ""):
            t.tag_remove("d_" + dec, "1.0", "end")
            t.tag_remove("p_" + dec, "1.0", "end")
        for it in rows:
            r = t.tag_ranges("r:" + it["id"])
            if r:
                t.tag_add(_tag(it), r[0], r[1])
        self._cp_strip()

    def _cp_mark(self, it):
        win = self._cwin
        t = win.cp_text
        t.tag_remove("cur", "1.0", "end")
        r = t.tag_ranges("r:" + it["id"])
        if r:
            t.tag_add("cur", r[0], r[1])
            t.see(r[0])

    def _cp_strip(self):
        """The file at a glance: one mark per sentence, grey undecided, amber draft, green committed."""
        win = self._cwin
        cv = getattr(win, "cp_strip", None)
        if cv is None or self.matrix is None or not cv.winfo_exists():
            return
        cv.delete("all")
        rows = self._cp_items_of(win.cp_file) if win.cp_file is not None else []
        h, w = max(1, cv.winfo_height()), max(4, cv.winfo_width())
        n = len(rows)
        if not n:
            return
        step = h / n
        sel = self._c_selected()
        cur = sel[0]["id"] if sel else None
        for i, it in enumerate(rows):
            kind = "draft" if it.get("draft") else ("done" if it.get("decision") else "")
            y0 = i * step
            cv.create_rectangle(2, y0, w - 2, y0 + max(2.0, step - (1 if step > 3 else 0)), fill=STRIP[kind], width=0)
            if it["id"] == cur:
                cv.create_rectangle(0, y0 - 1, w, y0 + max(3.0, step) + 1, outline="#0F172A", width=2)

    def _cp_strip_click(self, e):
        win = self._cwin
        rows = self._cp_items_of(win.cp_file) if win.cp_file is not None else []
        if not rows:
            return None
        h = max(1, win.cp_strip.winfo_height())
        i = max(0, min(len(rows) - 1, int(e.y * len(rows) / h)))
        self._cp_select(rows[i]["id"])
        return rows[i]["id"]

    def _cp_side(self):
        win, M = self._cwin, self.matrix
        boiler = [it for it in M.items if not C.eff(it) and it.get("type") == "Context" and it.get("suggest") == "Drop"]
        win.cp_boiler.configure(text=f"{len(boiler)} page headers, page numbers and markings look like boilerplate."
                                if boiler else "No undecided boilerplate left.")
        win.cp_boiler_btn.configure(state="normal" if boiler else "disabled",
                                    text=f"Drop all {len(boiler)}..." if boiler else "Drop them all...")
        nall = len(C.drafts(M.items))
        nfile = len(C.drafts(self._cp_items_of(win.cp_file))) if win.cp_file is not None else 0
        win.cp_dcount.configure(text=(f"{nall} draft{'s' if nall != 1 else ''} not committed ({nfile} in this file). Drafts are saved "
                                      "as you go; committed decisions are what Place and the exports use.") if nall
                                else "No drafts: every decision is committed.")
        for k, b in win.cp_cbtns.items():
            b.configure(state="normal" if nall else "disabled")
        win.cp_commit_btn.configure(state="normal" if nall else "disabled")
        for w in win.cp_files.winfo_children():
            w.destroy()
        for f in self._cp_files():
            rows = self._cp_items_of(f)
            done = sum(1 for it in rows if it["decision"] and not it.get("draft"))
            nd = sum(1 for it in rows if it.get("draft"))
            pct = int(done * 100 / len(rows)) if rows else 0
            on = f == win.cp_file
            ctk.CTkButton(win.cp_files, text=f"{f[:26]}   {pct}%" + (f"  +{nd} draft" if nd else ""), anchor="w", width=270, height=28,
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
        self._cp_strip()
        rows = self._cp_items_of(win.cp_file)
        n = next((i for i, x in enumerate(rows, 1) if x["id"] == it["id"]), 0)
        sug = it.get("suggest", "")
        d = C.eff(it)
        state = (f", draft {d or 'undecided'}" + (f" (committed: {it['decision']})" if it["decision"] else "") if it.get("draft")
                 else (f", {d} (committed)" if d else ", not decided"))
        if win.cp_range:
            win.cp_l1.configure(text=f"{len(win.cp_range)} sentences selected: K, C or D decides them all, L links them, "
                                     "Ctrl+Enter commits them. Esc clears.")
        else:
            win.cp_l1.configure(text=f"Sentence {n} of {len(rows)} in {win.cp_file}{state}")
        win.cp_l2.configure(text=f"Suggested: {sug}  ({WHY.get(sug, '')})" if sug else "No suggestion")
        win.cp_accept.configure(text=f"Accept {sug}  (Enter)" if sug in ("Keep", "Context", "Drop") else "Accept  (Enter)",
                                state="normal" if sug in ("Keep", "Context", "Drop") else "disabled")
        win.cp_head.configure(text=f"{it['id']}   {it['type']}" + (f"   {it['actor']}" if it.get("actor") else ""))
        t = win.cp_text
        t.tag_remove("linked", "1.0", "end")
        if win.cp_linking:
            self._cp_link_line()
        elif d == "Context":
            ids = C.cf_ids(C.eff_cf(it))
            if ids:
                first = self._c_item(ids[0])
                shown = ", ".join(ids[:5]) + (f" and {len(ids) - 5} more" if len(ids) > 5 else "")
                win.cp_l3.configure(text=f"Context for {shown}" + (f": {first['text'][:60]}" if first and len(ids) == 1 else "")
                                    + "   (L links more requirements or removes one)")
            else:
                win.cp_l3.configure(text="Context for: no requirement yet. Press L, then click each requirement it explains.")
            win.cp_l3.pack(fill="x")
            for cf in ids:
                r = t.tag_ranges("r:" + cf)
                if r:
                    t.tag_add("linked", r[0], r[1])
        elif d == "Keep":
            ctx = [x["id"] for x in self.matrix.items if C.eff(x) == "Context" and it["id"] in C.cf_ids(C.eff_cf(x))]
            win.cp_l3.configure(text=(f"Context for it: {', '.join(ctx[:6])}" + (" ..." if len(ctx) > 6 else "") if ctx
                                      else "No Context sentences yet.") + "   (L picks its Context sentences)")
            win.cp_l3.pack(fill="x")
            for cid in ctx:
                r = t.tag_ranges("r:" + cid)
                if r:
                    t.tag_add("linked", r[0], r[1])
        else:
            win.cp_l3.pack_forget()
        win.cp_link_btn.configure(state="normal")
        sec = " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
        win.cp_where.configure(text=(it.get("loc") or "") + (f"\nSection {sec}" if sec else ""))

    def _cp_commit_msg(self, text):
        """Show what was committed on the dock for a few seconds."""
        win = self._cwin
        if win is None or not hasattr(win, "cp_l0"):
            return
        win.cp_l0.configure(text=text)
        win.cp_l0.pack(fill="x", before=win.cp_l1)
        if win.cp_msg_after:
            try:
                win.after_cancel(win.cp_msg_after)
            except Exception:
                diag.swallowed()
        win.cp_msg_after = win.after(9000, lambda: win.winfo_exists() and win.cp_l0.pack_forget())

    # ------------------------------------------------------------ Decide: pointing and ranges
    def _cp_hit(self, ix):
        return next((tag[2:] for tag in self._cwin.cp_text.tag_names(ix) if tag.startswith("r:")), None)

    def _cp_motion(self, e):
        t = self._cwin.cp_text
        self._cp_hover(self._cp_hit(t.index(f"@{e.x},{e.y}")))

    def _cp_hover(self, iid):
        """Pointing at a sentence lights up its links: a Context sentence's requirements, a requirement's Context."""
        win = self._cwin
        if win is None or not hasattr(win, "cp_text") or iid == win.cp_hover:
            return
        win.cp_hover = iid
        t = win.cp_text
        t.tag_remove("hov", "1.0", "end")
        it = self._c_item(iid) if iid else None
        if it is None:
            return []
        d = C.eff(it)
        if d == "Context":
            ids = C.cf_ids(C.eff_cf(it))
        elif d == "Keep":
            ids = [x["id"] for x in self.matrix.items if C.eff(x) == "Context" and iid in C.cf_ids(C.eff_cf(x))]
        else:
            ids = []
        for i in ids:
            r = t.tag_ranges("r:" + i)
            if r:
                t.tag_add("hov", r[0], r[1])
        return ids

    def _cp_range_from_sel(self):
        """IDs of the sentences the dragged selection touches (in page order), [] for one sentence or none."""
        t = self._cwin.cp_text
        if not t.tag_ranges("sel"):
            return []
        a, b = t.index("sel.first"), t.index("sel.last")
        out = []
        for it in self._cp_items_of(self._cwin.cp_file):
            r = t.tag_ranges("r:" + it["id"])
            if r and t.compare(r[0], "<", b) and t.compare(r[1], ">", a):
                out.append(it["id"])
        return out if len(out) > 1 else []

    def cp_set_range(self, ids):
        win = self._cwin
        t = win.cp_text
        win.cp_range = list(ids)
        t.tag_remove("rng", "1.0", "end")
        for i in win.cp_range:
            r = t.tag_ranges("r:" + i)
            if r:
                t.tag_add("rng", r[0], r[1])
        sel = self._c_selected()
        if sel:
            self._cp_show(sel[0])

    def _cp_range_rows(self):
        return [x for x in (self._c_item(i) for i in self._cwin.cp_range) if x]

    # ------------------------------------------------------------ Decide: actions
    def cp_open_file(self, f):
        win = self._cwin
        win.cp_file = f
        self.cp_set_range([]) if win.cp_range else None
        self._cp_sync()
        rows = self._cp_items_of(f)
        first = next((it for it in rows if not C.eff(it)), rows[0] if rows else None)
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
        rng = self._cp_range_from_sel() if not win.cp_linking else []
        if rng:                                      # dragged across several sentences: decide them together
            t.tag_remove("sel", "1.0", "end")
            self._cp_select(rng[0]) if not self._c_selected() or self._c_selected()[0]["id"] not in rng else None
            self.cp_set_range(rng)
            return
        hit = self._cp_hit(ix)
        if not hit:
            return
        if win.cp_linking:                           # Link mode: each click adds or removes a link, the mode stays
            self.cp_link_click(hit)
            return
        if win.cp_range:
            self.cp_set_range([])
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
        ctrl = bool(e.state & 0x4)
        win = self._cwin
        if k in ("return", "kp_enter") and ctrl:
            self.cp_commit_default()
        elif win.cp_linking and k in ("return", "kp_enter", "escape", "l"):
            self.cp_link_end()
        elif k in ("k", "c", "d"):
            self.cp_decide({"k": "Keep", "c": "Context", "d": "Drop"}[k])
        elif k == "u":
            self.cp_decide("")
        elif k in ("return", "kp_enter"):
            self.cp_accept()
        elif k == "backspace":
            self.cp_back()
        elif k == "s":
            self.cp_split()
        elif k == "l":
            self.cp_link_start()
        elif k == "escape":
            if win.cp_range:
                self.cp_set_range([])
            sel = self._c_selected()
            if sel:
                self._cp_show(sel[0])
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
        win = self._cwin
        if win.cp_range:                             # the dragged sentences, all at once; the range stays
            rows = self._cp_range_rows()
            self.compliance_decide(decision, rows=rows)
            self.cp_set_range([r["id"] for r in rows])
            win.cp_text.focus_set()
            return len(rows)
        sel = self._c_selected()
        if len(sel) == 1:
            win.cp_hist.append(sel[0]["id"])
        self.compliance_decide(decision)
        win.cp_text.focus_set()
        return len(sel)

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

    # ------------------------------------------------------------ Decide: linking (2.35.0: many, and it stays open)
    def cp_link_start(self):
        """L. On Context sentences (the current one, or the dragged ones): each click on a requirement adds or removes
        it. On a requirement: each click on a sentence makes it Context for this requirement, or removes it. A sentence
        that is not decided yet becomes Context first. Stays open until Enter, Esc or L."""
        win = self._cwin
        rows = self._cp_range_rows() if win.cp_range else self._c_selected()[:1]
        if not rows:
            return None
        if len(rows) == 1 and C.eff(rows[0]) == "Keep":
            win.cp_linking = ("rev", rows[0]["id"])
        else:
            rows = [r for r in rows if C.eff(r) != "Keep"]
            if not rows:
                return None
            for r in rows:
                if C.eff(r) != "Context":
                    C.set_draft(r, "Context", [])
                    self.matrix.log(r["id"], "draft Context")
            win.cp_linking = ("fwd", [r["id"] for r in rows])
            self._c_changed(refill=False)
        self._cp_link_line()
        win.cp_text.focus_set()
        return win.cp_linking[0]

    def _cp_link_line(self):
        win = self._cwin
        mode, what = win.cp_linking
        t = win.cp_text
        t.tag_remove("linked", "1.0", "end")
        if mode == "fwd":
            rows = [x for x in (self._c_item(i) for i in what) if x]
            ids = []
            for r in rows:
                ids += [i for i in C.cf_ids(C.eff_cf(r)) if i not in ids]
            who = rows[0]["id"] if len(rows) == 1 else f"{len(rows)} sentences"
            win.cp_l3.configure(text=f"Linking {who}: click each requirement it explains; click again to remove. Enter or Esc "
                                     f"when done.   Context for: {', '.join(ids) if ids else 'none yet'}")
        else:
            ids = [x["id"] for x in self.matrix.items if C.eff(x) == "Context" and what in C.cf_ids(C.eff_cf(x))]
            win.cp_l3.configure(text=f"Picking Context for {what}: click each sentence that explains it; click again to remove. "
                                     f"Enter or Esc when done.   Context: {', '.join(ids[:8]) if ids else 'none yet'}"
                                     + (" ..." if len(ids) > 8 else ""))
        win.cp_l3.pack(fill="x")
        for i in ids:
            r = t.tag_ranges("r:" + i)
            if r:
                t.tag_add("linked", r[0], r[1])

    def cp_link_click(self, hit):
        """One click in link mode. Returns 'added', 'removed' or a reason it did nothing."""
        win = self._cwin
        mode, what = win.cp_linking
        M = self.matrix
        x = self._c_item(hit)
        if x is None:
            return "none"
        if mode == "fwd":
            if C.eff(x) != "Keep":
                win.cp_l3.configure(text=f"{hit} is not a requirement (Keep). Click a green sentence, or Enter when done.")
                return "not a requirement"
            rows = [r for r in (self._c_item(i) for i in what) if r and r["id"] != hit]
            have = all(hit in C.cf_ids(C.eff_cf(r)) for r in rows)
            for r in rows:
                ids = [i for i in C.cf_ids(C.eff_cf(r)) if i != hit] if have else C.cf_ids(C.eff_cf(r)) + [hit]
                C.set_draft(r, "Context", ids)
                M.log(r["id"], f"draft context for {C.eff_cf(r) or 'none'}")
            res = "removed" if have else "added"
        else:
            if hit == what:
                return "itself"
            if C.eff(x) == "Keep":
                win.cp_l3.configure(text=f"{hit} is a requirement. Click the sentences that explain {what}, or Enter when done.")
                return "a requirement"
            ids = C.cf_ids(C.eff_cf(x)) if C.eff(x) == "Context" else []
            res = "removed" if what in ids else "added"
            ids = [i for i in ids if i != what] if res == "removed" else ids + [what]
            C.set_draft(x, "Context", ids)
            M.log(x["id"], f"draft context for {C.eff_cf(x) or 'none'}")
        diag.activity("compliance_context_linked")
        self._c_changed(refill=False)
        self._cp_link_line()
        return res

    def cp_link_end(self):
        win = self._cwin
        win.cp_linking = None
        sel = self._c_selected()
        if sel:
            self._cp_show(sel[0])

    def cp_link_to(self, req_id):
        """Link the current Context sentence to one more requirement (it must be Keep). Returns True when linked."""
        sel = self._c_selected()
        req = self._c_item(req_id)
        if len(sel) != 1 or C.eff(sel[0]) != "Context" or req is None:
            return False
        if C.eff(req) != "Keep":
            self._cwin.cp_l3.configure(text=f"{req_id} is not a requirement (Keep). Press L and click a green sentence.")
            return False
        it = sel[0]
        ids = C.cf_ids(C.eff_cf(it))
        if req_id not in ids:
            C.set_draft(it, "Context", ids + [req_id])
            self.matrix.log(it["id"], f"draft context for {C.eff_cf(it)}")
            diag.activity("compliance_context_linked")
            self._c_changed(refill=False)
        self._cp_show(it)
        return True

    # ------------------------------------------------------------ Decide: commit
    def _cp_scope_rows(self, scope):
        win, M = self._cwin, self.matrix
        t = win.cp_text
        sel = self._c_selected()
        if scope == "selected":
            return self._cp_range_rows() if win.cp_range else sel[:1]
        if scope == "section":
            if not sel:
                return []
            f, sec = sel[0].get("file", ""), sel[0].get("section", "")
            return [it for it in M.items if it.get("file", "") == f and it.get("section", "") == sec]
        if scope == "file":
            return self._cp_items_of(win.cp_file)
        if scope == "screen":
            top, bot = t.index("@0,0"), t.index(f"@0,{max(1, t.winfo_height())}")
            out = []
            for it in self._cp_items_of(win.cp_file):
                r = t.tag_ranges("r:" + it["id"])
                if r and t.compare(r[1], ">", top) and t.compare(r[0], "<", f"{bot} lineend"):
                    out.append(it)
            return out
        return None                                   # all

    def cp_commit(self, scope="screen"):
        """Commit the drafts in a scope: screen, selected, section, file or all."""
        rows = self._cp_scope_rows(scope)
        r = self.compliance_commit(rows, scope)
        if r is not None and self._cwin is not None and hasattr(self._cwin, "cp_text"):
            sel = self._c_selected()
            if sel:
                self._cp_show(sel[0])
            self._cwin.cp_text.focus_set()
        return r

    def cp_commit_default(self):
        """Ctrl+Enter: the dragged sentences when there are any, else what is on screen."""
        return self.cp_commit("selected" if self._cwin.cp_range else "screen")

    def cp_split(self):
        self.compliance_split()
        self._cwin.cp_text.focus_set()

    def cp_drop_boilerplate(self, ask=True):
        M = self.matrix
        rows = [it for it in M.items if not C.eff(it) and it.get("type") == "Context" and it.get("suggest") == "Drop"]
        if not rows:
            return 0
        if ask:
            sample = "\n".join(f"  {it['text'][:70]}" for it in rows[:12]) + (f"\n  ... and {len(rows) - 12} more" if len(rows) > 12 else "")
            if not messagebox.askyesno("Clear the easy ones", f"Drop these {len(rows)} sentences (as drafts)?\n\n{sample}", parent=self._cwin):
                return 0
        for it in rows:
            C.set_draft(it, "Drop")
            M.log(it["id"], "draft Drop (boilerplate, accepted)")
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
        if cur["decision"] == "Context":
            for rid in C.cf_ids(cur.get("context_for", "")):
                req = self._c_item(rid)
                if req is not None and req.get("map") and req["map"] not in [c[0] for c in choices]:
                    choices.append((req["map"], f"with its requirement {req['id']}"))
        ranked = self._c_learned_places(cur) if hasattr(self, "_c_learned_places") else []
        band = __import__("placelearn").Placer.band(ranked) if ranked else ""
        rule, _s = self._c_suggest(cur)
        if rule and rule not in [c[0] for c in choices]:
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
        ids = {it["id"] for it in rows}
        follow = [x for x in M.items if x["decision"] == "Context" and set(C.cf_ids(x.get("context_for", ""))) & ids
                  and not x["map"] and x["id"] not in ids]   # 2.33.0: Context goes with the requirement it explains
        for it in rows + follow:
            it["map"] = label
            M.log(it["id"], f"mapped to {label} (placed" + (" with its requirement)" if it in follow else ")"))
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
