"""Setup tab in the compliance window (2.13.0): drag RFP text onto the proposal outline, set references, type
management direction, and export plain Word setup documents (purple RFP text, green direction).

Left: the pool (kept requirements, evaluation rows and context paragraphs not placed yet). Right: the outline with
what is placed under each section. Drag from the pool onto a section (Shift+drag adds a copy), or drag inside the
outline to reorder or move. Everything is saved with the matrix (autosave, recovery copy, backups).
"""
import os, re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import customtkinter as ctk
import diag
import setupdoc as SD

ALL = "All"


def _eng():
    import app_gui
    return app_gui


class SetupMixin:
    # ------------------------------------------------------------ building
    def _s_build(self, fr):
        win = self._cwin
        size = getattr(self, "font_size", 13)
        bar = ctk.CTkFrame(fr, fg_color="transparent"); bar.pack(fill="x", pady=(2, 4))
        win.s_kind = tk.StringVar(value=ALL); win.s_q = tk.StringVar()
        ctk.CTkLabel(bar, text="Show").pack(side="left", padx=(4, 3))
        ctk.CTkOptionMenu(bar, variable=win.s_kind, values=[ALL, "Requirement", "Evaluation", "Context"], width=120,
                          command=lambda _v: self._s_fill()).pack(side="left")
        ctk.CTkLabel(bar, text="Search").pack(side="left", padx=(10, 3))
        e = ctk.CTkEntry(bar, textvariable=win.s_q, width=170); e.pack(side="left")
        e.bind("<KeyRelease>", lambda _e: self._s_fill())
        B = dict(height=28, width=10)
        for text, cmd, color in (("Accept suggestions", self.setup_accept, None), ("Add context from RFP...", self.setup_add_context, None),
                                 ("References...", self.setup_references, None), ("Export setup...", self.setup_export, "#7030A0"),
                                 ("Export changes only...", self.setup_export_changes, None),
                                 ("Compare a setup document...", self.setup_compare, None)):
            kw = dict(B); kw.update(fg_color=color) if color else None
            ctk.CTkButton(bar, text=text, command=cmd, **kw).pack(side="left", padx=3)
        win.s_lbl = ctk.CTkLabel(fr, text="", anchor="w", justify="left")
        win.s_lbl.pack(fill="x", padx=4)
        pw = tk.PanedWindow(fr, orient="horizontal", sashwidth=6, bd=0, bg="#CBD5E1")
        pw.pack(fill="both", expand=True, pady=(4, 0))
        left = ctk.CTkFrame(pw, fg_color="transparent"); right = ctk.CTkFrame(pw, fg_color="transparent")
        pw.add(left, minsize=320, width=700); pw.add(right, minsize=360)
        vf = getattr(self, "tree_font", None)
        st = ttk.Style(fr)
        if vf is not None:
            st.configure("Su.Treeview", font=vf, rowheight=vf.metrics("linespace") + int(max(8, size // 2) * getattr(self, "dpi", 1.0)))
        ctk.CTkLabel(left, text="RFP text not placed yet (drag onto a section; Shift+drag adds a copy)", anchor="w").pack(fill="x")
        cols = (("ref", "Reference", 90), ("kind", "Kind", 100), ("sug", "Suggested", 130), ("text", "RFP text", 420))
        pool = ttk.Treeview(left, columns=[c[0] for c in cols], show="headings", style="Su.Treeview", selectmode="extended")
        for c, h, w in cols:
            pool.heading(c, text=h); pool.column(c, width=w, minwidth=60, stretch=(c == "text"))
        ys = ttk.Scrollbar(left, orient="vertical", command=pool.yview); pool.configure(yscrollcommand=ys.set)
        ys.pack(side="right", fill="y"); pool.pack(fill="both", expand=True)
        win.s_pool = pool
        ctk.CTkLabel(right, text="Proposal outline (every heading exports, even with nothing under it)", anchor="w").pack(fill="x")
        tf = ctk.CTkFrame(right, fg_color="transparent"); tf.pack(fill="both", expand=True)
        out = ttk.Treeview(tf, columns=("ref",), show="tree headings", style="Su.Treeview", selectmode="extended")
        out.heading("#0", text="Section / RFP text"); out.heading("ref", text="Reference")
        out.column("#0", width=520, stretch=True); out.column("ref", width=110, stretch=False)
        out.tag_configure("section", font=(vf.actual("family"), vf.actual("size"), "bold") if vf is not None else None)
        out.tag_configure("copy", foreground="#7C3AED")
        out.tag_configure("noref", foreground="#B45309")
        ys2 = ttk.Scrollbar(tf, orient="vertical", command=out.yview); out.configure(yscrollcommand=ys2.set)
        ys2.pack(side="right", fill="y"); out.pack(fill="both", expand=True)
        win.s_out = out
        row = ctk.CTkFrame(right, fg_color="transparent"); row.pack(fill="x", pady=(4, 2))
        for text, cmd in (("Up", lambda: self.setup_move(-1)), ("Down", lambda: self.setup_move(1)), ("Remove", self.setup_remove)):
            ctk.CTkButton(row, text=text, width=70, height=26, command=cmd).pack(side="left", padx=2)
        ctk.CTkLabel(row, text="Reference").pack(side="left", padx=(12, 3))
        win.s_ref = ctk.CTkEntry(row, width=130); win.s_ref.pack(side="left")
        ctk.CTkButton(row, text="Set", width=50, height=26, command=self.setup_set_ref).pack(side="left", padx=3)
        ctk.CTkButton(row, text="Fill down", width=80, height=26, command=self.setup_fill_down).pack(side="left", padx=3)
        win.s_ref_src = ctk.CTkLabel(row, text="", text_color=("#475569", "#94A3B8")); win.s_ref_src.pack(side="left", padx=6)
        win.s_note_lbl = ctk.CTkLabel(right, text="Management direction: select a section", anchor="w", text_color=("#047857", "#34D399"))
        win.s_note_lbl.pack(fill="x", pady=(4, 0))
        win.s_note = tk.Text(right, height=4, wrap="word", font=("Segoe UI", max(9, int(size * 0.9 * getattr(self, "dpi", 1.0)))),
                             relief="solid", bd=1, fg="#047857")
        win.s_note.pack(fill="x", pady=(2, 4))
        win.s_note.bind("<KeyRelease>", lambda _e: self._s_note_changed())
        win.s_target = None
        # drag and drop between the two trees, and inside the outline
        for tv in (pool, out):
            tv.bind("<ButtonPress-1>", self._s_press, add="+")
            tv.bind("<B1-Motion>", self._s_motion, add="+")
            tv.bind("<ButtonRelease-1>", self._s_release, add="+")
        out.bind("<<TreeviewSelect>>", lambda _e: self._s_show())
        if hasattr(self, "kw_quick"):                # Keyword Harvest (2.18.0): a heading as a keyword
            out.bind("<Button-3>", self._s_kw_menu, add="+")
        pool.bind("<Return>", lambda _e: self.setup_place_selected())
        win.s_drag = None

    # ------------------------------------------------------------ filling
    def _s_ready(self):
        win = getattr(self, "_cwin", None)
        return win is not None and win.winfo_exists() and hasattr(win, "s_pool") and self.matrix is not None

    def _s_fill(self):
        if not self._s_ready():
            return
        win, M = self._cwin, self.matrix
        S = SD.setup_of(M)
        inh = SD.inherited_sections(M)
        q = win.s_q.get().strip().lower()
        kind = win.s_kind.get()
        pool = win.s_pool
        pool.delete(*pool.get_children())
        stats = None
        import compliance as C
        for it in SD.unplaced(M):
            k = SD.kind_of(it)
            if kind != ALL and k != kind:
                continue
            if q and q not in it["text"].lower() and q not in it["id"].lower():
                continue
            sug = ""
            if k != "Context" and M.outline:
                if stats is None:
                    stats = C.word_df(M.items)
                sug = self._c_suggest(it, stats)[0] if hasattr(self, "_c_suggest") else ""
            ref, _src = SD.ref_of(M, it, inh)
            pool.insert("", "end", iid=it["id"], values=(ref or "-", k, sug, it["text"]))
        out = win.s_out
        open_state = {i: out.item(i, "open") for i in out.get_children()}
        sel = out.selection()
        out.delete(*out.get_children())
        P = SD.placed_in(M)
        B = SD.by_id(M)
        for o in M.outline:
            lab = C.outline_label(o)
            sid = "S::" + lab
            mg = " [direction]" if S["mgmt"].get(lab, "").strip() else ""
            out.insert("", "end", iid=sid, text=("    " * (o.get("level", 1) - 1)) + lab + mg, values=("",), tags=("section",),
                       open=open_state.get(sid, True))
            for i in P.get(lab, []):
                it = B[i]
                ref, _src = SD.ref_of(M, it, inh)
                tags = []
                if it.get("map") != lab:
                    tags.append("copy")
                if not ref:
                    tags.append("noref")
                note = "  [note]" if S["notes"].get(i, "").strip() else ""
                out.insert(sid, "end", iid=f"I::{lab}::{i}", text=it["text"][:220] + note, values=(ref or SD.MISSING,), tags=tags)
        for s in sel:
            if out.exists(s):
                out.selection_add(s)
        chk = SD.export_check(M)
        kept = sum(1 for it in M.items if it.get("decision") in ("Keep", "Context"))
        win.s_lbl.configure(text=f"{kept - len(chk['unplaced'])} of {kept} Keep and Context rows placed  |  {chk['blocks']} blocks  |  "
                                 f"{len(chk['no_ref'])} without a reference  |  {len(S['context'])} context paragraphs  |  "
                                 f"References: {SD.REF_FORMAT_LABELS[S['ref_format']]}")

    # ------------------------------------------------------------ selection helpers
    def _s_kw_menu(self, event):
        win = self._cwin
        iid = win.s_out.identify_row(event.y)
        if not iid:
            return
        kind, lab, _i = self._s_parse(iid)
        m = tk.Menu(win, tearoff=0)
        if kind == "section":
            head = re.sub(r"^[\dA-Z]+(\.[\dA-Z]+)*\s+", "", lab.strip())
            m.add_command(label=f"Add heading as keyword: {head[:50]}", state="normal" if self.effort is not None else "disabled",
                          command=lambda: self.kw_quick(head, source=f"Setup outline {lab}"))
        else:
            m.add_command(label="Add as keyword: right-click a heading", state="disabled")
        m.tk_popup(event.x_root, event.y_root)

    def _s_parse(self, iid):
        """('section', label, None) or ('item', label, id)."""
        if iid.startswith("S::"):
            return "section", iid[3:], None
        if iid.startswith("I::"):
            lab, i = iid[3:].rsplit("::", 1)
            return "item", lab, i
        return None, None, None

    def _s_target_section(self):
        sel = self._cwin.s_out.selection()
        if not sel:
            return None
        return self._s_parse(sel[0])[1]

    def _s_show(self):
        win = self._cwin
        sel = win.s_out.selection()
        S = SD.setup_of(self.matrix)
        win.s_note.delete("1.0", "end")
        win.s_ref.delete(0, "end")
        win.s_ref_src.configure(text="")
        if not sel:
            win.s_target = None
            win.s_note_lbl.configure(text="Management direction: select a section")
            return
        kind, lab, i = self._s_parse(sel[0])
        if kind == "section":
            win.s_target = ("mgmt", lab)
            win.s_note_lbl.configure(text=f"Management direction for {lab} (green, below its RFP text)")
            win.s_note.insert("1.0", S["mgmt"].get(lab, ""))
        else:
            win.s_target = ("note", i)
            win.s_note_lbl.configure(text=f"Note for {i} (green, right after this RFP text)")
            win.s_note.insert("1.0", S["notes"].get(i, ""))
            it = SD.by_id(self.matrix)[i]
            ref, src = SD.ref_of(self.matrix, it)
            win.s_ref.insert(0, ref)
            win.s_ref_src.configure(text=src)

    def _s_note_changed(self):
        win = self._cwin
        if not win.s_target or self.matrix is None:
            return
        S = SD.setup_of(self.matrix)
        kind, key = win.s_target
        text = win.s_note.get("1.0", "end").strip()
        (S["mgmt"] if kind == "mgmt" else S["notes"])[key] = text
        self.matrix.pending = True
        self._c_changed(refill=False)

    # ------------------------------------------------------------ actions
    def setup_place(self, ids, label, before=None, copy=False):
        if not ids or not label or self.matrix is None:
            return
        for i in ids:
            SD.place(self.matrix, i, label, before=before, copy=copy)
        diag.activity("setup_placed", n=len(ids))
        self._c_changed(refill=False)
        self._s_fill()
        self._c_fill()

    def setup_place_selected(self, copy=False):
        lab = self._s_target_section()
        ids = list(self._cwin.s_pool.selection())
        if not lab:
            messagebox.showinfo("Setup", "Select a section on the right first.", parent=self._cwin); return
        self.setup_place(ids, lab, copy=copy)

    def setup_accept(self):
        """Place every unplaced kept row where the rules (or similar mapped rows) suggest."""
        M = self.matrix
        if M is None or not M.outline:
            return
        import compliance as C
        stats = C.word_df(M.items)
        n = 0
        for it in SD.unplaced(M, kinds=("Requirement", "Evaluation")):
            lab = self._c_suggest(it, stats)[0]
            if lab:
                SD.place(M, it["id"], lab); n += 1
        diag.activity("setup_accepted", n=n)
        self._c_changed(refill=False); self._s_fill(); self._c_fill()
        self._cwin.s_lbl.configure(text=self._cwin.s_lbl.cget("text") + f"  |  {n} suggestions placed")

    def setup_remove(self):
        M = self.matrix
        n = 0
        for iid in self._cwin.s_out.selection():
            kind, lab, i = self._s_parse(iid)
            if kind == "item":
                SD.unplace(M, i, lab); n += 1
        if n:
            diag.activity("setup_removed", n=n)
            self._c_changed(refill=False); self._s_fill(); self._c_fill()

    def setup_move(self, delta):
        sel = self._cwin.s_out.selection()
        if not sel:
            return
        kind, lab, i = self._s_parse(sel[0])
        if kind != "item":
            return
        SD.move(self.matrix, i, lab, delta)
        self._c_changed(refill=False); self._s_fill()
        iid = f"I::{lab}::{i}"
        if self._cwin.s_out.exists(iid):
            self._cwin.s_out.selection_set(iid); self._cwin.s_out.see(iid)

    def _s_selected_items(self):
        out = []
        for iid in self._cwin.s_out.selection():
            kind, _lab, i = self._s_parse(iid)
            if kind == "item" and i not in out:
                out.append(i)
        return out

    def setup_set_ref(self):
        ids = self._s_selected_items()
        if not ids:
            return
        v = self._cwin.s_ref.get().strip()
        S = SD.setup_of(self.matrix)
        for i in ids:
            S["refs"][i] = v
            self.matrix.log(i, f"setup: reference {v or '(none)'}")
        diag.activity("setup_reference_set", n=len(ids))
        self._c_changed(refill=False); self._s_fill()

    def setup_fill_down(self):
        """Give the selected rows the reference of the first selected row."""
        ids = self._s_selected_items()
        if len(ids) < 2:
            messagebox.showinfo("Fill down", "Select a row with the right reference, then the rows below it that should share it.",
                                parent=self._cwin); return
        M = self.matrix
        ref = SD.ref_of(M, SD.by_id(M)[ids[0]])[0]
        S = SD.setup_of(M)
        for i in ids[1:]:
            S["refs"][i] = ref
        self._c_changed(refill=False); self._s_fill()

    def setup_add_context(self):
        """Keep the RFP's other paragraphs (SOW text, evaluation criteria) as Context items you can place."""
        M = self.matrix
        if M is None:
            return
        eng = _eng()
        n = files = 0
        for src in M.sources:
            name = src[0]
            path = M.path_of(name)
            if not path:
                continue
            try:
                n += SD.context_from_chunks(M, name, eng.typed_chunks(path)); files += 1
            except Exception:
                diag.swallowed()
        diag.activity("setup_context_added", n=n, files=files)
        self.matrix.pending = True
        self._c_changed(refill=False); self._s_fill()
        messagebox.showinfo("Context", f"{n} paragraphs added as Context from {files} RFP file(s). Show > Context lists them."
                            + ("" if files else "\n\nThe RFP files were not found at the paths in the Sources sheet."), parent=self._cwin)

    def setup_references(self):
        """Reference format and a rule per RFP file for numbers without a section letter (Attachment 3 = L)."""
        M = self.matrix
        if M is None:
            return
        S = SD.setup_of(M)
        win = ctk.CTkToplevel(self._cwin); win.title("References"); win.geometry("640x460"); win.transient(self._cwin)
        win.after(150, win.lift)
        diag.register(win, "setup_references")
        ctk.CTkLabel(win, text="Each RFP block starts with its reference, on the same line. Format:", anchor="w").pack(fill="x", padx=14, pady=(12, 4))
        fmt = tk.StringVar(value=S["ref_format"])
        ff = ctk.CTkFrame(win, fg_color="transparent"); ff.pack(fill="x", padx=14)
        for k, lab in SD.REF_FORMAT_LABELS.items():
            ctk.CTkRadioButton(ff, text=lab, variable=fmt, value=k).pack(side="left", padx=(0, 14))
        ctk.CTkLabel(win, text="Files numbered 1.2, 3.4 without a section letter: the letter to put in front (blank = none).",
                     anchor="w", wraplength=600, justify="left").pack(fill="x", padx=14, pady=(14, 4))
        box = ctk.CTkScrollableFrame(win, fg_color="transparent", height=220); box.pack(fill="both", expand=True, padx=14)
        box.grid_columnconfigure(0, weight=1)
        files = sorted({it.get("file", "") for it in M.items if it.get("file")} | {c.get("file", "") for c in S["context"] if c.get("file")})
        entries = {}
        for r, f in enumerate(files):
            ctk.CTkLabel(box, text=f, anchor="w").grid(row=r, column=0, sticky="w", pady=2)
            e = ctk.CTkEntry(box, width=80)
            e.insert(0, S["rules"].get(f, SD.suggest_prefix(f) if f not in S["rules"] else ""))
            e.grid(row=r, column=1, padx=6, pady=2)
            entries[f] = e
        ctk.CTkLabel(win, text="Suggested letters come from the file name; check them before saving.", anchor="w",
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=14)

        def save():
            S["ref_format"] = fmt.get()
            S["rules"] = {f: e.get().strip() for f, e in entries.items()}
            self.matrix.log("(setup)", "setup: reference settings changed")
            diag.activity("setup_references_saved", n=len(files))
            self._c_changed(refill=False); self._s_fill()
            win.destroy()
        b = ctk.CTkFrame(win, fg_color="transparent"); b.pack(fill="x", padx=14, pady=10)
        ctk.CTkButton(b, text="Save", command=save).pack(side="left")
        ctk.CTkButton(b, text="Cancel", fg_color="#475569", command=win.destroy).pack(side="right")
        win._api = {"fmt": fmt, "entries": entries, "save": save}
        return win

    def setup_export(self):
        M = self.matrix
        if M is None or not M.outline:
            messagebox.showinfo("Export setup", "Set the outline first (Outline tab).", parent=self._cwin); return
        chk = SD.export_check(M)
        if chk["unplaced"] or chk["no_ref"]:
            msg = []
            if chk["unplaced"]:
                msg.append(f"{len(chk['unplaced'])} kept requirement(s) are not placed under any section.")
            if chk["no_ref"]:
                msg.append(f"{len(chk['no_ref'])} block(s) have no reference; they print as {SD.MISSING}.")
            if not messagebox.askyesno("Export setup", "\n".join(msg) + "\n\nExport anyway?", parent=self._cwin):
                return
        folder = filedialog.askdirectory(parent=self._cwin, title="Folder for the setup documents",
                                         initialdir=os.path.dirname(M.path) or None)
        if not folder:
            return
        try:
            paths = SD.export(M, folder)
        except PermissionError:
            messagebox.showerror("Export setup", "A file with that name is open in Word. Close it, then export again.", parent=self._cwin)
            return
        diag.activity("setup_exported", files=len(paths))
        self._c_changed(refill=False); self._s_fill()
        messagebox.showinfo("Export setup", "Saved:\n" + "\n".join(os.path.basename(p) for p in paths) +
                            "\n\nRFP text is purple and management direction is green. Click one purple paragraph, then Home > "
                            "Select > Select Text with Similar Formatting, and apply your style; the same for green.\n\n"
                            "They hold customer content: keep them on this PC or SharePoint.", parent=self._cwin)
        return paths

    def setup_export_changes(self):
        M = self.matrix
        if M is None:
            return
        ch = SD.changes_since_last(M)
        if ch is None:
            messagebox.showinfo("Export changes only", "Export the setup once first; changes are counted from that export.",
                                parent=self._cwin); return
        if not ch:
            messagebox.showinfo("Export changes only", "Nothing changed since the last export.", parent=self._cwin); return
        stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", os.path.splitext(os.path.basename(M.path))[0])
        import datetime
        p = filedialog.asksaveasfilename(parent=self._cwin, title="Setup changes", defaultextension=".docx",
                                         initialdir=os.path.dirname(M.path) or None,
                                         initialfile=f"{stem}_Setup_changes_{datetime.datetime.now().strftime('%Y-%m-%d_%H%M')}.docx",
                                         filetypes=[("Word", "*.docx")])
        if not p:
            return
        SD.export_changes(M, p)
        diag.activity("setup_changes_exported", n=len(ch))
        self._c_changed(refill=False)
        messagebox.showinfo("Export changes only", f"{len(ch)} change(s) saved:\n{os.path.basename(p)}", parent=self._cwin)
        return p

    def setup_compare(self):
        M = self.matrix
        if M is None:
            return
        p = filedialog.askopenfilename(parent=self._cwin, title="A setup document (styled or not)", filetypes=[("Word", "*.docx")])
        if not p:
            return
        try:
            rows = SD.compare(M, p)
        except Exception as ex:
            diag.swallowed()
            messagebox.showerror("Compare", f"The document could not be read ({type(ex).__name__}).", parent=self._cwin); return
        diag.activity("setup_compared", rows=len(rows))
        win = ctk.CTkToplevel(self._cwin); win.title("Compare setup with matrix"); win.geometry("1000x520"); win.transient(self._cwin)
        win.after(150, win.lift)
        diag.register(win, "setup_compare")
        ctk.CTkLabel(win, text=("Everything in the setup is in the document, under the right headings." if not rows else
                                f"{len(rows)} difference(s) between the document and the setup:"), anchor="w").pack(fill="x", padx=12, pady=(10, 4))
        tv = ttk.Treeview(win, columns=("sec", "prob", "id", "text"), show="headings", style="Su.Treeview")
        for c, h, w in (("sec", "Section", 220), ("prob", "Problem", 260), ("id", "ID", 100), ("text", "RFP text", 400)):
            tv.heading(c, text=h); tv.column(c, width=w, stretch=(c == "text"))
        for r in rows:
            tv.insert("", "end", values=r)
        tv.pack(fill="both", expand=True, padx=12, pady=4)
        ctk.CTkButton(win, text="Close", command=win.destroy).pack(anchor="e", padx=12, pady=10)
        win._rows = rows
        return win

    # ------------------------------------------------------------ drag and drop
    def _s_press(self, e):
        tv = e.widget
        iid = tv.identify_row(e.y)
        if not iid:
            self._cwin.s_drag = None; return
        kind = "pool" if tv is self._cwin.s_pool else "out"
        if kind == "out" and not iid.startswith("I::"):
            self._cwin.s_drag = None; return
        sel = tv.selection()
        ids = list(sel) if iid in sel else [iid]
        self._cwin.s_drag = {"from": kind, "ids": ids, "x": e.x_root, "y": e.y_root, "moved": False}

    def _s_motion(self, e):
        d = self._cwin.s_drag
        if not d:
            return
        if abs(e.x_root - d["x"]) + abs(e.y_root - d["y"]) > 6:
            d["moved"] = True
            e.widget.configure(cursor="hand2")

    def _s_release(self, e):
        d, win = self._cwin.s_drag, self._cwin
        self._cwin.s_drag = None
        e.widget.configure(cursor="")
        if not d or not d["moved"]:
            return
        target = win.winfo_containing(e.x_root, e.y_root)
        out = win.s_out
        if target is not out:
            if target is win.s_pool and d["from"] == "out":         # dragged back to the pool: remove
                for iid in d["ids"]:
                    kind, lab, i = self._s_parse(iid)
                    if kind == "item":
                        SD.unplace(self.matrix, i, lab)
                self._c_changed(refill=False); self._s_fill(); self._c_fill()
            return
        y = e.y_root - out.winfo_rooty()
        tid = out.identify_row(y)
        if not tid:
            return
        kind, lab, before = self._s_parse(tid)
        copy = bool(e.state & 0x0001)                              # Shift held: add a copy
        if d["from"] == "pool":
            self.setup_place(d["ids"], lab, before=before, copy=copy)
        else:
            ids = []
            for iid in d["ids"]:
                k, old_lab, i = self._s_parse(iid)
                if k != "item" or i == before:
                    continue
                if old_lab != lab and not copy:
                    SD.unplace(self.matrix, i, old_lab)
                ids.append(i)
            self.setup_place(ids, lab, before=before, copy=copy)
