"""Compliance in passes. 2.36.0: one Assign step, tied to the response structure.

Assign: the RFP reads like a page on the left; the response structure (the outline) is always on the right. Click any
sentence at any time to see how it is assigned and change it. Every choice counts at once and is saved like every
change (a recovery copy within half a second, the matrix file a few seconds later): there is no commit step.
- Compliance requirement (R): into a section of the structure. Click a section on the right to make it the target and
  press R, or press 1, 2 or 3 for the suggested sections (the rules' match and past proposals).
- Context (C): for the compliance requirements it supports (the nearest one to start; click others in the page to
  add or remove them) or for a section or subsection itself (click it on the right). Enter or Esc when done.
- Clear (X): not used. Split (S): where you clicked in the sentence. Combine (M): the sentences you dragged across.
A sentence that is not assigned is not used. Drag across several sentences to assign them together. Pointing at a
sentence lights up its links; the target section's sentences are underlined. The strip beside the page maps the file:
grey not used, green compliance requirement, blue context; click it to jump.

Place (the old second pass) is no longer a step; the setup board (order, direction, references) opens from the side.
Prove: owner, status and response page for each compliance requirement.
The hidden requirements table stays the selection model, so every existing action works the same.
"""
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
import compliance as C
import diag
import cwords as CW

DEC_BG = {"Keep": "#BBF7D0", "Context": "#BFDBFE", "Drop": "#F3F4F6"}
STRIP = {"": "#CBD5E1", "Drop": "#E2E8F0", "Keep": "#22C55E", "Context": "#3B82F6"}
NAME = {"Keep": "Compliance requirement", "Context": "Context", "Drop": "Not used", "": "Not used"}


def _tag(it):
    return "d_" + (it.get("decision") or "")


class CompliancePageMixin:
    # ------------------------------------------------------------ Assign: build
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
        win.cp_mode = None            # ("req", ids): pick a section; ("ctx", ids): pick requirements or a section
        win.cp_target = None          # the outline section R assigns to
        win.cp_sugg = []
        win.cp_osig = None
        win.cp_orows = {}
        dock = ctk.CTkFrame(rq, corner_radius=10, fg_color=("#0F172A", "#0B1220"))
        dock.pack(side="bottom", fill="x", pady=(6, 0), before=body)
        info = ctk.CTkFrame(dock, fg_color="transparent"); info.pack(side="top", fill="x", padx=14, pady=(8, 0))
        keys = ctk.CTkFrame(dock, fg_color="transparent"); keys.pack(side="top", fill="x", padx=10, pady=(2, 8))
        win.cp_l0 = ctk.CTkLabel(info, text="", anchor="w", text_color="#86EFAC", font=("Segoe UI", 12, "bold"))
        win.cp_l1 = ctk.CTkLabel(info, text="", anchor="w", text_color="#E2E8F0", font=("Segoe UI", 14))
        win.cp_l1.pack(fill="x")
        win.cp_l2 = ctk.CTkLabel(info, text="", anchor="w", text_color="#94A3B8", font=("Segoe UI", 12))
        win.cp_l2.pack(fill="x")
        win.cp_l3 = ctk.CTkLabel(info, text="", anchor="w", text_color="#93C5FD", font=("Segoe UI", 12), justify="left", wraplength=720)
        B = dict(height=40, font=("Segoe UI", 14, "bold"), width=10)
        win.cp_req_btn = ctk.CTkButton(keys, text="Compliance requirement  R", command=self.cp_req, fg_color="#15803D", **B)
        win.cp_req_btn.pack(side="left", padx=4)
        win.cp_ctx_btn = ctk.CTkButton(keys, text="Context  C", command=self.cp_ctx, fg_color="#1D4ED8", **B)
        win.cp_ctx_btn.pack(side="left", padx=4)
        G = dict(height=40, width=10, fg_color="transparent", border_width=1, border_color="#334155", text_color="#CBD5E1",
                 hover_color="#1E293B")
        ctk.CTkButton(keys, text="Clear  X", command=self.cp_clear, **G).pack(side="left", padx=(12, 4))
        ctk.CTkButton(keys, text="Split  S", command=self.cp_split, **G).pack(side="left", padx=4)
        ctk.CTkButton(keys, text="Combine  M", command=self.cp_combine, **G).pack(side="left", padx=4)
        win.cp_done_btn = ctk.CTkButton(keys, text="Done  Enter", command=self.cp_mode_end, height=40, width=10,
                                        fg_color="transparent", border_width=2, border_color="#93C5FD", text_color="#BFDBFE",
                                        hover_color="#1E3A8A", font=("Segoe UI", 13, "bold"))

        wrap = ctk.CTkFrame(body, fg_color="transparent"); wrap.pack(fill="both", expand=True)
        side = ctk.CTkScrollableFrame(wrap, width=330); side.pack(side="right", fill="y", padx=(8, 0))
        win.cp_sidef = side
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
        t.tag_configure("insec", underline=True)
        try:
            t.tag_configure("insec", underlinefg="#0F766E")
        except tk.TclError:
            diag.swallowed()
        t.tag_configure("rng", background="#FDE68A")
        t.tag_configure("cur", relief="solid", borderwidth=2, background="#FEF3C7")
        t.tag_configure("linked", relief="ridge", borderwidth=2, foreground="#1E3A8A")
        t.tag_configure("hov", relief="ridge", borderwidth=2, foreground="#7C2D12")
        t.tag_raise("rng")
        t.tag_raise("cur")
        t.bind("<ButtonRelease-1>", self._cp_click)
        t.bind("<Key>", self._cp_key)
        t.bind("<Motion>", self._cp_motion)
        t.bind("<Leave>", lambda _e: self._cp_hover(None))
        for seq in ("<Control-c>", "<Control-a>"):
            t.bind(seq, lambda _e: None)
        win.cp_head = ctk.CTkLabel(side, text="", font=("Segoe UI", 14, "bold"), anchor="w", justify="left", wraplength=310)
        win.cp_head.pack(fill="x", padx=8, pady=(6, 0))
        win.cp_where = ctk.CTkLabel(side, text="", anchor="w", justify="left", wraplength=310, text_color=("#475569", "#94A3B8"))
        win.cp_where.pack(fill="x", padx=8)
        r = ctk.CTkFrame(side, fg_color="transparent"); r.pack(fill="x", padx=8, pady=(6, 4))
        ctk.CTkButton(r, text="Show page", width=90, command=self.compliance_show_page).pack(side="left")
        ctk.CTkButton(r, text="Open file", width=90, command=self.compliance_open_file).pack(side="left", padx=6)
        self._cp_card_title(side, "Response structure")
        win.cp_ohint = ctk.CTkLabel(side, text="", anchor="w", justify="left", wraplength=310, text_color=("#475569", "#94A3B8"))
        win.cp_ohint.pack(fill="x", padx=8)
        win.cp_outline = ctk.CTkFrame(side, fg_color="transparent"); win.cp_outline.pack(fill="x", padx=4, pady=(4, 0))
        orow = ctk.CTkFrame(side, fg_color="transparent"); orow.pack(fill="x", padx=8, pady=(6, 0))
        ctk.CTkButton(orow, text="Edit the structure", width=10, fg_color="#475569",
                      command=lambda: self.shell_go("compliance", "outline") if hasattr(self, "shell_go") else None).pack(side="left")
        ctk.CTkButton(orow, text="Arrange the setup...", width=10, fg_color="#475569",
                      command=lambda: self._cwin.tabs.set("Setup")).pack(side="left", padx=6)
        win.cp_next_var = tk.BooleanVar(value=self._c_auto_next() if hasattr(self, "_c_auto_next") else True)
        ctk.CTkCheckBox(side, text="After assigning a requirement, go to the\nnext sentence that is not assigned",
                        variable=win.cp_next_var, command=self._cp_auto_next_set).pack(anchor="w", padx=8, pady=(10, 0))
        self._cp_card_title(side, "Highlighter key")
        for txt, bg in (("Compliance requirement", DEC_BG["Keep"]), ("Context", DEC_BG["Context"]), ("Not used (not assigned)", "#FFFFFF")):
            row = ctk.CTkFrame(side, fg_color="transparent"); row.pack(fill="x", padx=8, pady=1)
            ctk.CTkLabel(row, text="", width=26, height=14, fg_color=bg, corner_radius=3, border_width=1,
                         border_color="#CBD5E1").pack(side="left", padx=(0, 8))
            ctk.CTkLabel(row, text=txt, anchor="w").pack(side="left")
        ctk.CTkLabel(side, text="Underlined: in the target section. The strip beside the page: grey not used, green "
                                "compliance requirement, blue context.", anchor="w", justify="left", wraplength=310,
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=8, pady=(4, 0))
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

    # ------------------------------------------------------------ Assign: render
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
        font, fg, bg = CW.tk_font_options(cfg, "Georgia", 16)
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
        win.cp_src.configure(text=f"{win.cp_file}: {len(rows)} sentences. Click any sentence to see or change it; drag across "
                                  "several to assign them together; click between two words, then S, to split.")
        self._cp_insec()
        sel = self._c_selected()
        if sel:
            self._cp_mark(sel[0])
        self._cp_strip()

    def _cp_shade(self, rows):
        t = self._cwin.cp_text
        for dec in ("Keep", "Context", "Drop", ""):
            t.tag_remove("d_" + dec, "1.0", "end")
        for tag in [x for x in t.tag_names() if x.startswith("p_")]:      # 2.35.0 draft tags, if any are left
            t.tag_remove(tag, "1.0", "end")
        for it in rows:
            r = t.tag_ranges("r:" + it["id"])
            if r:
                t.tag_add(_tag(it), r[0], r[1])
        self._cp_insec()
        self._cp_strip()

    def _cp_insec(self):
        """Underline the sentences of this file that are in the target section."""
        win = self._cwin
        t = win.cp_text
        t.tag_remove("insec", "1.0", "end")
        if not win.cp_target or win.cp_file is None:
            return
        for it in self._cp_items_of(win.cp_file):
            if it.get("map") == win.cp_target and it["decision"] in ("Keep", "Context"):
                r = t.tag_ranges("r:" + it["id"])
                if r:
                    t.tag_add("insec", r[0], r[1])

    def _cp_mark(self, it):
        win = self._cwin
        t = win.cp_text
        t.tag_remove("cur", "1.0", "end")
        r = t.tag_ranges("r:" + it["id"])
        if r:
            t.tag_add("cur", r[0], r[1])
            t.see(r[0])

    def _cp_strip(self):
        """The file at a glance: one mark per sentence, grey not used, green compliance requirement, blue context."""
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
            y0 = i * step
            cv.create_rectangle(2, y0, w - 2, y0 + max(2.0, step - (1 if step > 3 else 0)),
                                fill=STRIP.get(it.get("decision", ""), STRIP[""]), width=0)
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

    # ------------------------------------------------------------ Assign: the response structure panel
    def _cp_outline_rows(self):
        M = self.matrix
        return [(C.outline_label(o), o["level"]) for o in (M.outline if M else [])]

    def _cp_side(self):
        win, M = self._cwin, self.matrix
        labs = self._cp_outline_rows()
        sig = tuple(labs)
        if sig != win.cp_osig:                       # rebuild the section rows only when the structure changed
            for w in win.cp_outline.winfo_children():
                w.destroy()
            win.cp_orows = {}
            for lab, lvl in labs:
                b = ctk.CTkButton(win.cp_outline, text=lab, anchor="w", height=28, width=10,
                                  font=("Segoe UI", 12, "bold" if lvl == 1 else "normal"), border_width=1,
                                  command=lambda lab=lab: self.cp_section_click(lab))
                b.pack(fill="x", padx=(4 + 14 * max(0, lvl - 1), 4), pady=1)
                win.cp_orows[lab] = b
            win.cp_osig = sig
        if not labs:
            win.cp_ohint.configure(text="No structure yet. Set the response structure first (Edit the structure); every "
                                        "requirement goes into one of its sections.")
        elif win.cp_mode and win.cp_mode[0] == "req":
            win.cp_ohint.configure(text="Click the section for this requirement.")
        elif win.cp_mode and win.cp_mode[0] == "ctx":
            win.cp_ohint.configure(text="Click a section to make this context for the section itself.")
        else:
            win.cp_ohint.configure(text="Click a section to make it the target: R then assigns there.")
        sel = self._c_selected()
        here = sel[0].get("map") if sel and sel[0]["decision"] in ("Keep", "Context") else None
        counts = {}
        for it in M.items:
            if it["decision"] in ("Keep", "Context") and it.get("map"):
                k = counts.setdefault(it["map"], [0, 0])
                k[0 if it["decision"] == "Keep" else 1] += 1
        for lab, b in win.cp_orows.items():
            nk, nc = counts.get(lab, [0, 0])
            txt = lab + (f"    {nk} req" if nk else "") + (f", {nc} ctx" if nc else "")
            on = lab == win.cp_target
            b.configure(text=txt, fg_color=("#DCFCE7", "#14532D") if on else ("#FFFFFF", "#1F2937"),
                        text_color=("#0F172A", "#F1F5F9"), hover_color=("#E2E8F0", "#334155"),
                        border_color="#0F766E" if lab == here else ("#15803D" if on else ("#E2E8F0", "#334155")),
                        border_width=2 if lab == here or on else 1)
        for w in win.cp_files.winfo_children():
            w.destroy()
        for f in self._cp_files():
            rows = self._cp_items_of(f)
            nk = sum(1 for it in rows if it["decision"] == "Keep")
            nc = sum(1 for it in rows if it["decision"] == "Context")
            on = f == win.cp_file
            ctk.CTkButton(win.cp_files, text=f"{f[:28]}   {nk} req, {nc} ctx", anchor="w", width=300, height=28,
                          fg_color=("#DBEAFE", "#1E3A8A") if on else "transparent", text_color=("#0F172A", "#F1F5F9"),
                          hover_color=("#E2E8F0", "#334155"), command=lambda f=f: self.cp_open_file(f)).pack(fill="x", pady=1)

    def _cp_suggestions(self, it):
        """Up to 3 sections for a sentence: the rules' match, then past proposals."""
        if self.matrix is None or not self.matrix.outline:
            return []
        out = []
        try:
            rule, _s = self._c_suggest(it)
            if rule:
                out.append(rule)
            for lab, _sc in (self._c_learned_places(it) if hasattr(self, "_c_learned_places") else []):
                if lab not in out:
                    out.append(lab)
        except Exception:
            diag.swallowed()
        known = {C.outline_label(o) for o in self.matrix.outline}
        return [x for x in out if x in known][:3]

    def _cp_show(self, it):
        """The current sentence changed: outline it, follow its file, say how it is assigned."""
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
        d = it["decision"]
        if d == "Keep":
            state = f"Compliance requirement in {it['map']}" if it.get("map") else "Compliance requirement, no section yet"
        elif d == "Context":
            state = C.context_label(it) + (f" (in {it['map']})" if it.get("context_for") and it.get("map") else "")
        else:
            state = "Not assigned (not used)"
        if win.cp_range:
            win.cp_l1.configure(text=f"{len(win.cp_range)} sentences selected: R, C or X assigns them all; M combines them. Esc clears.")
        else:
            win.cp_l1.configure(text=f"{it['id']}: {state}")
        win.cp_sugg = self._cp_suggestions(it)
        tgt = f"Target: {win.cp_target} (R assigns here)" if win.cp_target else "No target section: click one on the right"
        sug = "   Suggested: " + "   ".join(f"{k}  {lab}" for k, lab in enumerate(win.cp_sugg, 1)) if win.cp_sugg else ""
        win.cp_l2.configure(text=f"Sentence {n} of {len(rows)} in {win.cp_file}.   {tgt}.{sug}")
        win.cp_head.configure(text=f"{it['id']}   {it['type']}" + (f"   {it['actor']}" if it.get("actor") else ""))
        t = win.cp_text
        t.tag_remove("linked", "1.0", "end")
        ids = []
        if win.cp_mode:
            self._cp_mode_line()
        elif d == "Context" and it.get("context_for"):
            ids = C.cf_ids(it["context_for"])
            win.cp_l3.configure(text=f"Supports {', '.join(ids[:6])}" + (" ..." if len(ids) > 6 else "")
                                + ".   C changes what it supports.")
            win.cp_l3.pack(fill="x")
        elif d == "Keep":
            ids = [x["id"] for x in self.matrix.items if x["decision"] == "Context" and it["id"] in C.cf_ids(x.get("context_for", ""))]
            win.cp_l3.configure(text=(f"Context for it: {', '.join(ids[:6])}" + (" ..." if len(ids) > 6 else "")) if ids
                                else "No context for it yet. Select a sentence, press C, then click this requirement.")
            win.cp_l3.pack(fill="x")
        else:
            win.cp_l3.pack_forget()
        for i in ids:
            r = t.tag_ranges("r:" + i)
            if r:
                t.tag_add("linked", r[0], r[1])
        sec = " ".join(x for x in (it.get("section", ""), it.get("section_title", "")) if x)
        win.cp_where.configure(text=(it.get("loc") or "") + (f"\nRFP section {sec}" if sec else ""))
        self._cp_side()

    def _cp_flash(self, text):
        """Say what just changed on the dock for a few seconds."""
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
        win.cp_msg_after = win.after(7000, lambda: win.winfo_exists() and win.cp_l0.pack_forget())

    # ------------------------------------------------------------ Assign: pointing and ranges
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
        if it["decision"] == "Context":
            ids = C.cf_ids(it.get("context_for", ""))
        elif it["decision"] == "Keep":
            ids = [x["id"] for x in self.matrix.items if x["decision"] == "Context" and iid in C.cf_ids(x.get("context_for", ""))]
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

    def _cp_rows(self):
        """The sentences an action applies to: the dragged ones, else the current one."""
        win = self._cwin
        if win.cp_range:
            return [x for x in (self._c_item(i) for i in win.cp_range) if x]
        return self._c_selected()[:1]

    # ------------------------------------------------------------ Assign: navigation
    def cp_open_file(self, f):
        win = self._cwin
        win.cp_file = f
        if win.cp_range:
            self.cp_set_range([])
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
        rng = self._cp_range_from_sel() if not win.cp_mode else []
        if rng:                                      # dragged across several sentences: assign them together
            t.tag_remove("sel", "1.0", "end")
            sel = self._c_selected()
            if not sel or sel[0]["id"] not in rng:
                self._cp_select(rng[0])
            self.cp_set_range(rng)
            return
        hit = self._cp_hit(ix)
        if not hit:
            return
        if win.cp_mode and win.cp_mode[0] == "ctx":  # choosing what this context supports: each click adds or removes
            self.cp_ctx_click(hit)
            return
        if win.cp_mode:
            self.cp_mode_end()
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
        win = self._cwin
        if k in ("return", "kp_enter", "escape") and win.cp_mode:
            self.cp_mode_end()
        elif k == "r":
            self.cp_req()
        elif k == "c":
            self.cp_ctx()
        elif k in ("x", "delete"):
            self.cp_clear()
        elif k == "s":
            self.cp_split()
        elif k == "m":
            self.cp_combine()
        elif k in ("1", "2", "3", "kp_1", "kp_2", "kp_3"):
            self.cp_pick(int(k[-1]))
        elif k == "escape":
            if win.cp_range:
                self.cp_set_range([])
            sel = self._c_selected()
            if sel:
                self._cp_show(sel[0])
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

    # ------------------------------------------------------------ Assign: actions (each one counts at once)
    def _cp_after(self, rows, text, advance=False):
        diag.activity("compliance_assigned", n=len(rows))
        self._cp_flash(text)
        self._c_changed()
        win = self._cwin
        if advance and len(rows) == 1 and not win.cp_range and bool(win.cp_next_var.get()):
            self.compliance_next_undecided(after=rows[0]["id"])
        else:
            sel = self._c_selected()
            if sel:
                self._cp_show(sel[0])
        win.cp_text.focus_set()

    def cp_assign_req(self, rows, label):
        """Rows become compliance requirements in a section of the structure."""
        M = self.matrix
        known = {C.outline_label(o) for o in M.outline}
        if not rows or label not in known:
            return 0
        C.assign_requirement(M.items, rows, label)
        for it in rows:
            M.log(it["id"], f"compliance requirement in {label}")
        who = rows[0]["id"] if len(rows) == 1 else f"{len(rows)} sentences"
        self._cp_after(rows, f"{who}: compliance requirement in {label}", advance=True)
        return len(rows)

    def cp_req(self):
        """R: into the target section; with no target, the next section clicked (or 1, 2, 3)."""
        win = self._cwin
        rows = self._cp_rows()
        if not rows:
            return 0
        if not self.matrix.outline:
            win.cp_l3.configure(text="Set the response structure first: Edit the structure on the right.")
            win.cp_l3.pack(fill="x")
            return 0
        if win.cp_mode:
            self.cp_mode_end(quiet=True)
        if win.cp_target:
            return self.cp_assign_req(rows, win.cp_target)
        win.cp_mode = ("req", [r["id"] for r in rows])
        self._cp_mode_line()
        self._cp_side()
        return 0

    def cp_pick(self, k):
        """1, 2, 3: a compliance requirement in that suggested section (or, choosing context, context for it)."""
        win = self._cwin
        if not (1 <= k <= len(win.cp_sugg)):
            return 0
        lab = win.cp_sugg[k - 1]
        if win.cp_mode and win.cp_mode[0] == "ctx":
            return self.cp_section_click(lab)
        rows = [x for x in (self._c_item(i) for i in win.cp_mode[1])] if win.cp_mode else self._cp_rows()
        win.cp_mode = None
        win.cp_done_btn.pack_forget()
        return self.cp_assign_req([r for r in rows if r], lab)

    def cp_ctx(self):
        """C: Context. It starts out supporting the nearest compliance requirement; click others in the page to add or
        remove them, or a section on the right for the section itself. Enter or Esc when done."""
        win, M = self._cwin, self.matrix
        rows = self._cp_rows()
        if not rows:
            return None
        if win.cp_mode:
            self.cp_mode_end(quiet=True)
        for it in rows:
            if it["decision"] == "Context":
                continue                              # already Context: keep what it supports, change it with clicks
            d = C.default_context_for(M.items, it)
            if d:
                C.assign_context(M.items, [it], [d])
            elif win.cp_target:
                C.assign_context(M.items, [it], section=win.cp_target)
            else:
                C.assign_context(M.items, [it], [])
            M.log(it["id"], "context " + (f"for {it['context_for']}" if it["context_for"] else f"for section {it['map']}" if it["map"] else ""))
        win.cp_mode = ("ctx", [r["id"] for r in rows])
        diag.activity("compliance_assigned", n=len(rows))
        self._c_changed()
        self._cp_mode_line()
        self._cp_side()
        win.cp_text.focus_set()
        return "ctx"

    def cp_ctx_click(self, hit):
        """A click while choosing context: a compliance requirement is added or removed. Returns 'added', 'removed' or
        a reason it did nothing."""
        win, M = self._cwin, self.matrix
        rows = [r for r in (self._c_item(i) for i in win.cp_mode[1]) if r and r["id"] != hit]
        x = self._c_item(hit)
        if x is None or not rows:
            return "none"
        if x["decision"] != "Keep":
            win.cp_l3.configure(text=f"{hit} is not a compliance requirement. Click a green sentence, a section on the right, "
                                     "or Enter when done.")
            return "not a requirement"
        have = all(hit in C.cf_ids(r.get("context_for", "")) for r in rows)
        for r in rows:
            ids = C.cf_ids(r.get("context_for", ""))
            ids = [i for i in ids if i != hit] if have else ids + [hit]
            C.assign_context(M.items, [r], ids)
            M.log(r["id"], f"context for {r['context_for'] or 'nothing yet'}")
        diag.activity("compliance_context_linked")
        self._c_changed()
        self._cp_mode_line()
        return "removed" if have else "added"

    def cp_section_click(self, label):
        """A section on the right: the target for R, or where the waiting requirement or context goes."""
        win, M = self._cwin, self.matrix
        mode = win.cp_mode
        if mode and mode[0] == "req":
            rows = [r for r in (self._c_item(i) for i in mode[1]) if r]
            win.cp_mode = None
            win.cp_done_btn.pack_forget()
            return self.cp_assign_req(rows, label)
        if mode and mode[0] == "ctx":
            rows = [r for r in (self._c_item(i) for i in mode[1]) if r]
            C.assign_context(M.items, rows, section=label)
            for r in rows:
                M.log(r["id"], f"context for section {label}")
            win.cp_mode = None
            win.cp_done_btn.pack_forget()
            who = rows[0]["id"] if len(rows) == 1 else f"{len(rows)} sentences"
            self._cp_after(rows, f"{who}: context for section {label}")
            return len(rows)
        win.cp_target = None if win.cp_target == label else label
        self._cp_insec()
        sel = self._c_selected()
        if sel:
            self._cp_show(sel[0])
        else:
            self._cp_side()
        win.cp_text.focus_set()
        return 0

    def _cp_mode_line(self):
        win = self._cwin
        mode, ids = win.cp_mode
        t = win.cp_text
        t.tag_remove("linked", "1.0", "end")
        who = ids[0] if len(ids) == 1 else f"{len(ids)} sentences"
        if mode == "req":
            win.cp_l3.configure(text=f"{who}: click the section on the right for this compliance requirement"
                                     + (", or press 1, 2 or 3 for a suggestion" if win.cp_sugg else "") + ". Esc cancels.")
        else:
            rows = [r for r in (self._c_item(i) for i in ids) if r]
            links = []
            for r in rows:
                links += [i for i in C.cf_ids(r.get("context_for", "")) if i not in links]
            secs = {r["map"] for r in rows if not r.get("context_for") and r.get("map")}
            now = (f"supports {', '.join(links)}" if links else
                   f"context for section {', '.join(sorted(secs))}" if secs else "not attached yet")
            win.cp_l3.configure(text=f"Context, {who}: {now}. Click compliance requirements in the page to add or remove them, "
                                     "or a section on the right for the section itself. Enter when done.")
            for i in links:
                r = t.tag_ranges("r:" + i)
                if r:
                    t.tag_add("linked", r[0], r[1])
        win.cp_l3.pack(fill="x")
        if not win.cp_done_btn.winfo_ismapped():
            win.cp_done_btn.pack(side="left", padx=(12, 4))

    def cp_mode_end(self, quiet=False):
        win = self._cwin
        if win.cp_mode and win.cp_mode[0] == "ctx" and not quiet:
            rows = [r for r in (self._c_item(i) for i in win.cp_mode[1]) if r]
            if rows:
                self._cp_flash(f"{rows[0]['id'] if len(rows) == 1 else str(len(rows)) + ' sentences'}: {C.context_label(rows[0])}")
        win.cp_mode = None
        win.cp_done_btn.pack_forget()
        sel = self._c_selected()
        if sel and not quiet:
            self._cp_show(sel[0])

    def cp_clear(self):
        """X: not used (no decision, no section, no links)."""
        rows = self._cp_rows()
        if not rows:
            return 0
        win = self._cwin
        if win.cp_mode:
            self.cp_mode_end(quiet=True)
        C.clear_assignment(self.matrix.items, rows)
        for it in rows:
            self.matrix.log(it["id"], "not used (cleared)")
        self._cp_after(rows, (rows[0]["id"] if len(rows) == 1 else f"{len(rows)} sentences") + ": not used")
        return len(rows)

    def cp_combine(self):
        """M: the dragged sentences become one."""
        win = self._cwin
        rows = self._cp_rows()
        if len(rows) < 2:
            win.cp_l3.configure(text="Drag across two or more sentences, then Combine (M).")
            win.cp_l3.pack(fill="x")
            return None
        tv = win.tv
        ids = [r["id"] for r in rows if tv.exists(r["id"])]
        tv.selection_set(ids)
        win.cp_range = []
        self.compliance_merge()
        win.cp_text.tag_remove("rng", "1.0", "end")
        sel = self._c_selected()
        if sel:
            self._cp_flash(f"Combined {len(ids)} sentences into {sel[0]['id']}")
            self._cp_show(sel[0])
        win.cp_text.focus_set()
        return sel[0]["id"] if sel else None

    def cp_split(self):
        self.compliance_split()
        self._cwin.cp_text.focus_set()

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
