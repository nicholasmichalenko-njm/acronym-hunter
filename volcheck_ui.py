"""QA/QC of our own deliverables (2.7.0 volume check; a view of its own from 2.24.0). Checks the Word volumes we write
against the effort list: first use in the running text (acronyms), terms not in the effort list, not approved yet,
definitions that differ, list entries the volumes do not use, and each volume's acronym list. Word (.docx) only: a
PDF export loses the difference between running text, tables, captions, figures and headings, so first use would not
be judged accurately. Double-click a row to jump to it in the preview.
"""
import os, re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
import diag
import volcheck as V

TAG_COLORS = {V.BAD: "#FDE2E2", V.WARN: "#FEF3E2", V.INFO: "#E0F2FE", V.OK: "#DCFCE7"}
WORD_ONLY = ("QA/QC checks the Word documents we produce (.docx), never customer documents. Run it on the Word files, "
             "not on PDF exports: a PDF loses the difference between running text, tables, captions, figures and "
             "headings, so first-use results on a PDF would not be accurate.")


def _wrap_to(label, frame):
    """Wrap a label's text to its frame's width as the window is resized (works at any display scaling)."""
    def fit(e):
        if not label.winfo_exists():
            return
        sc = float(ctk.ScalingTracker.get_widget_scaling(label)) or 1.0
        label.configure(wraplength=max(200, int(e.width / sc) - 30))
    frame.bind("<Configure>", fit, add="+")


def _eng():
    import app_gui
    return app_gui


class VolumeCheckMixin:
    """Mixed into AcronymAppGUI after EffortMixin."""

    def volume_files(self):
        info = (self.efforts.get(self.effort.name) or {}) if self.effort else {}
        d = info.get("volumes_dir") or ""
        return d if d and os.path.isdir(d) else ""

    # ------------------------------------------------------------ the QA/QC view (2.24.0)
    def qa_build(self, M):
        self.qa_view = Q = ctk.CTkFrame(M, fg_color="transparent")
        top = ctk.CTkFrame(Q, fg_color="transparent"); top.pack(fill="x")
        ctk.CTkLabel(top, text="QA/QC: our Word deliverables", font=("Arial", 15, "bold"), anchor="w").pack(side="left", padx=4)
        ctk.CTkButton(top, text="Check Word deliverables...", fg_color="#15803D", width=200,
                      command=self.check_volumes).pack(side="right", padx=4)
        note = ctk.CTkLabel(Q, text=WORD_ONLY, anchor="w", justify="left", wraplength=900, text_color=("#475569", "#94A3B8"))
        note.pack(fill="x", padx=4, pady=(2, 6))
        _wrap_to(note, Q)
        self.qa_body = ctk.CTkFrame(Q, fg_color="transparent"); self.qa_body.pack(fill="both", expand=True)
        self._qa_empty()

    def _qa_empty(self):
        for w in self.qa_body.winfo_children():
            w.destroy()
        intro = ctk.CTkLabel(self.qa_body, anchor="w", justify="left", wraplength=900, text=(
            "Pick the final Word volumes (the file names set the submission order: Vol 2 before Vol 10). The check finds "
            "each acronym's first use in the running text and marks it:\n"
            "    \u2713  defined at first use (green)\n"
            "    \u2717  not defined at first use, or never defined (red)\n"
            "    !  defined, but check it: the words differ from the effort list, or no spelled-out words before (ACR) (amber)\n"
            "    i  a note: defined again later, or used only in figures or tables (blue)\n"
            "Tables, figures, captions, headers and footers never count as a first use; the In figures or tables column "
            "shows where a term also appears in one.\n"
            "It also flags an acronym defined at first use but never used again (spell it out instead), and checks each "
            "volume's own acronym list: acronyms used but not listed, listed but not used, and list definitions that differ "
            "from the effort list."))
        intro.pack(fill="x", padx=8, pady=8)
        _wrap_to(intro, self.qa_view)

    def open_qa(self):
        if self.effort is None:
            return
        import effort_home as H
        self.show_view(H.VIEW_QA)

    def check_volumes(self, paths=None):
        if self.effort is None:
            return
        eng = _eng()
        if hasattr(self, "qa_view"):
            self.open_qa()
        if paths is None:
            paths = filedialog.askopenfilenames(
                title="Word deliverables to check (submission order follows the file names)",
                initialdir=self.volume_files() or self.start_dir(),
                filetypes=[("Word documents", "*.docx"), ("All files", "*.*")])
        paths = sorted({os.path.abspath(p) for p in paths or []}, key=lambda p: V.natural_key(os.path.basename(p)))
        other = [os.path.basename(p) for p in paths if not p.lower().endswith(".docx")]
        paths = [p for p in paths if p.lower().endswith(".docx")]
        if other:
            messagebox.showwarning("QA/QC", "Left out (not Word documents):\n" + "\n".join(other[:10]) + "\n\n" + WORD_ONLY)
        if not paths:
            return
        names = [os.path.basename(p) for p in paths]
        if len(set(names)) != len(names):
            messagebox.showwarning("Check volumes", "Two volumes have the same file name. Rename one so the report can tell them apart.")
            return
        diag.activity("volume_check_started", files=len(paths))
        self._volcheck = {"paths": paths, "names": names, "defs": {}, "lists": {}}

        def after(cb):
            import custdefs
            for p in paths:
                eng.check_cancel()
                try:
                    self._volcheck["defs"][os.path.basename(p)] = custdefs.extract(eng.typed_chunks(p) + custdefs.table_chunks(p))
                except Exception:
                    diag.swallowed()
                try:                                        # the volume's own acronym list (2.25.0)
                    self._volcheck["lists"][os.path.basename(p)] = custdefs.acronym_list(p)
                except Exception:
                    diag.swallowed()
        self.start_batch(paths, after=after)

    def volume_check_after_scan(self):
        """True when the scan just finished was a QA/QC check (the QA/QC view shows it, not Scan review)."""
        vc = getattr(self, "_volcheck", None)
        self._volcheck = None
        if not vc or self.effort is None:
            return False
        eng = _eng()
        report = V.build({t: d for t, d in self.results.items() if not d.get("known")}, self.effort.rows,   # known names stay off
                         vc["names"], self.effort.first_use, vc["defs"],
                         file_of=eng._file_of, in_picture=lambda loc: bool(eng._OCR_LOC.search(loc)),
                         vol_lists=vc.get("lists"))
        self.volume_report = report
        s = report["summary"]
        diag.activity("volume_check_report", terms=s["terms_used"], rows=len(report["first_use"]), items=s["missing"])
        self.show_volume_report(report)
        return True

    # ------------------------------------------------------------ the report (in the QA/QC view)
    def show_volume_report(self, report):
        if not report:
            return None
        if not hasattr(self, "qa_body"):
            return None
        for w in self.qa_body.winfo_children():
            w.destroy()
        win = ctk.CTkFrame(self.qa_body, fg_color="transparent"); win.pack(fill="both", expand=True)
        self._volwin = win
        self.open_qa()
        s = report["summary"]
        rule = V.RULE_SHORT.get(s["rule"], s["rule"])
        c = s.get("checks", {})
        head = (f"First use {rule}:   \u2713 {c.get(V.OK, 0)} defined at first use     \u2717 {c.get(V.BAD, 0)} to fix     "
                f"! {c.get(V.WARN, 0)} to check     i {c.get(V.INFO, 0)} notes")
        lc = s.get("list_checks", {})
        head += (f"          Acronym list:  \u2713 {lc.get(V.OK, 0)}   \u2717 {lc.get(V.BAD, 0)}   ! {lc.get(V.WARN, 0)}"
                 if report.get("acronym_list") else "")
        more = (f"{s['volumes']} volume(s), {s['terms_used']} terms used  |  defined but never used again {s.get('used_once', 0)}  |  "
                f"not in effort list {s['missing']}  |  "
                f"not approved {s['not_approved']}  |  definition differs {s['differs']}  |  in the list, not used {s['unused']}")
        for text, font in ((head, ("Arial", 14, "bold")), (more, ("Arial", 12))):
            lb = ctk.CTkLabel(win, text=text, font=font, wraplength=900, justify="left", anchor="w")
            lb.pack(fill="x", padx=12, pady=(8 if font[1] == 14 else 0, 0))
            _wrap_to(lb, win)
        note = ("     Rescan the volumes to check first use by section: some results were saved before 2.22.0."
                if s.get("rescan_for_sections") else "")
        ctk.CTkLabel(win, text="Order: " + "  >  ".join(report["volumes"]) + "     Double-click a row to jump to it." + note,
                     text_color=("#475569", "#94A3B8"), wraplength=900, justify="left", anchor="w").pack(fill="x", padx=12, pady=(0, 4))
        b = ctk.CTkFrame(win, fg_color="transparent"); b.pack(side="bottom", fill="x", padx=10, pady=8)
        tabs = ctk.CTkTabview(win); tabs.pack(fill="both", expand=True, padx=8)
        win._trees = {}
        sc = ctk.ScalingTracker.get_widget_scaling(win)
        size = getattr(self, "font_size", 13)
        st = ttk.Style(win)
        from tkinter import font as tkfont
        vf = getattr(self, "tree_font", None) or tkfont.Font(win, family="Segoe UI", size=size)   # the results table's text size
        st.configure("Vol.Treeview", font=vf, rowheight=vf.metrics("linespace") + max(8, size // 2))
        st.configure("Vol.Treeview.Heading", font=getattr(self, "head_font", None) or vf)

        def table(tab, cols, rows, keys, widths, level=False, jump=True):
            fr = tabs.add(tab)
            tv = ttk.Treeview(fr, columns=keys, show="headings", selectmode="extended", style="Vol.Treeview")
            for c, k, w in zip(cols, keys, widths):
                tv.heading(k, text=c); tv.column(k, width=int(w * sc * size / 13), minwidth=40, anchor="w", stretch=False)
            for lv, color in TAG_COLORS.items():
                tv.tag_configure(lv, background=color, foreground="#111827")
            sb = ttk.Scrollbar(fr, orient="vertical", command=tv.yview)
            hb = ttk.Scrollbar(fr, orient="horizontal", command=tv.xview)
            tv.configure(yscrollcommand=sb.set, xscrollcommand=hb.set)
            sb.pack(side="right", fill="y"); hb.pack(side="bottom", fill="x"); tv.pack(fill="both", expand=True)
            data = {}
            for r in rows:
                iid = tv.insert("", "end", values=[r.get(k, "") for k in keys], tags=(r.get("level", ""),) if level else ())
                data[iid] = r
            if jump:
                tv.bind("<Double-1>", lambda e, tv=tv, data=data: self._volume_jump(data.get(tv.focus())))
            win._trees[tab] = (tv, data)
            return tv

        if s["rule"] == "section":
            table("First use", ["Check", "Volume", "Section", "Acronym", "Result", "First use in text", "In figures or tables",
                                "Written as", "Effort list says", "Also defined at"],
                  report["first_use"], ["check", "volume", "section", "term", "state", "loc", "in_figures", "written",
                                        "list_definition", "also_defined"], [70, 170, 80, 100, 330, 260, 260, 190, 190, 200],
                  level=True)
        else:
            table("First use", ["Check", "Volume", "Acronym", "Result", "First use in text", "In figures or tables", "Written as",
                                "Effort list says", "Also defined at"],
                  report["first_use"], ["check", "volume", "term", "state", "loc", "in_figures", "written", "list_definition",
                                        "also_defined"], [70, 170, 100, 330, 260, 260, 190, 190, 200], level=True)
        if report.get("acronym_list"):
            table("Acronym list", ["Check", "Volume", "Acronym", "Result", "In the list as", "Effort list says",
                                   "Uses outside the list"],
                  report["acronym_list"], ["check", "volume", "term", "state", "listed_as", "list_definition", "uses"],
                  [70, 170, 100, 380, 260, 260, 120], level=True)
        table("Not in effort list", ["Term", "Type", "Count", "Volumes", "Suggested definition", "First found at"],
              report["missing"], ["term", "type", "count", "volumes", "suggestion", "loc"], [90, 90, 60, 220, 300, 300])
        table("Not approved", ["Term", "Status", "Definition", "Volumes", "First found at"],
              report["not_approved"], ["term", "status", "definition", "volumes", "loc"], [90, 100, 320, 220, 300])
        table("Definition differs", ["Term", "Volume", "Volume says", "Effort list says", "Where"],
              report["differs"], ["term", "volume", "written", "list_definition", "loc"], [90, 160, 280, 280, 300])
        table("Unused", ["Term", "Type", "Status", "Definition"], report["unused"], ["term", "type", "status", "definition"],
              [100, 100, 110, 600], jump=False)
        for i, v in enumerate(report["volumes"], 1):
            table(f"List {i}: {v[:24]}", ["Term", "Definition", "Status"], report["lists"][v],
                  ["term", "definition", "status"], [110, 640, 160])

        ctk.CTkButton(b, text="Export report (Excel)...", command=self.export_volume_report).pack(side="left", padx=4)
        ctk.CTkButton(b, text="Acronym lists for Word...", command=self.export_volume_lists).pack(side="left", padx=4)
        ctk.CTkButton(b, text=f"Add {s['missing']} missing to the effort list", fg_color="#0F766E",
                      state="normal" if s["missing"] else "disabled", command=self.add_volume_missing).pack(side="left", padx=4)
        ctk.CTkButton(b, text="Record in the effort list", fg_color="#0F766E",
                      command=self.record_volume_use).pack(side="left", padx=4)
        if s["first_use_problems"] == 0 and s["missing"]:
            tabs.set("Not in effort list")
        return win

    def _volume_jump(self, row):
        """Select the term in the results table and show that location in the preview."""
        if not row or row.get("term") not in self.results:
            return
        term, loc = row["term"], row.get("loc", "") or row.get("in_figures", "").split(": ", 1)[-1]
        diag.activity("volume_check_jump")
        import effort_home as H
        self.show_view(H.VIEW_SCAN)                    # the preview lives in Scan review; QA/QC is one click back
        if not self.tree.exists(term):
            self.clear_filters()
        if not self.tree.exists(term):
            return
        self.tree.selection_set(term); self.tree.see(term); self.tree.focus(term)
        self.on_select(None)
        if loc and self.preview_var.get():
            self.after(80, lambda: self.preview.show_at(loc))
        self.status.configure(text=f"{term}: {loc}")

    # ------------------------------------------------------------ outputs
    def _report_name(self, what, ext):
        r = self.volume_report
        stem = re.sub(r"[^A-Za-z0-9_-]+", "_", self.effort.name) if self.effort else "Effort"
        vol = os.path.splitext(r["volumes"][0])[0] if len(r["volumes"]) == 1 else f"{len(r['volumes'])}_volumes"
        return f"{stem}_{re.sub(r'[^A-Za-z0-9_-]+', '_', vol)}_{what}.{ext}"

    def export_volume_report(self):
        r = getattr(self, "volume_report", None)
        if not r:
            return
        p = filedialog.asksaveasfilename(parent=self._volwin, title="Save the volume check", defaultextension=".xlsx",
                                         initialfile=self._report_name("Volume_Check", "xlsx"),
                                         initialdir=os.path.dirname(self.effort.path), filetypes=[("Excel", "*.xlsx")])
        if not p:
            return
        try:
            V.write_excel(r, p, self.effort.name)
        except PermissionError:
            messagebox.showerror("Volume check", "That file is open in Excel. Close it, then save again.", parent=self._volwin); return
        diag.activity("volume_check_exported", rows=len(r["first_use"]))
        messagebox.showinfo("Volume check", f"Saved:\n{p}\n\nIt holds customer content: keep it on this PC or SharePoint.", parent=self._volwin)

    def export_volume_lists(self):
        r = getattr(self, "volume_report", None)
        if not r:
            return
        d = filedialog.askdirectory(parent=self._volwin, title="Folder for the acronym lists (one Word file per volume)",
                                    initialdir=os.path.dirname(self.effort.path))
        if not d:
            return
        written, open_items = [], 0
        sets = [(v, r["lists"][v]) for v in r["volumes"]]
        if len(sets) > 1:
            combo = {}
            for _v, rows in sets:
                for x in rows:
                    combo.setdefault(x.get("key", x["term"]), x)
            sets.append(("All volumes", sorted(combo.values(), key=lambda x: (x["term"].lower(), x["term"]))))
        try:
            for v, rows in sets:
                p = os.path.join(d, re.sub(r"[^A-Za-z0-9 _.-]+", "_", os.path.splitext(v)[0]) + "_Acronym_List.docx")
                V.write_docx([(x["term"], x["definition"]) for x in rows], p)
                written.append(os.path.basename(p))
                if v != "All volumes":
                    open_items += sum(1 for x in rows if x["status"] != "Approved" or not x["definition"])
        except PermissionError:
            messagebox.showerror("Acronym lists", "A list with that name is open in Word. Close it, then try again.", parent=self._volwin); return
        diag.activity("volume_lists_exported", files=len(written))
        note = (f"\n\n{open_items} entries are not approved yet or have no definition: they are in the lists with the "
                "definition the app has. Check them on the Not approved and Not in effort list tabs.") if open_items else ""
        messagebox.showinfo("Acronym lists", "Saved in " + d + ":\n" + "\n".join(written) + note, parent=self._volwin)

    def add_volume_missing(self):
        r = getattr(self, "volume_report", None)
        if not r or self.effort is None:
            return
        n = 0
        for m in r["missing"]:
            res = self.effort.add_or_update(m["term"], change_note="added by volume check (Proposed)", Type=m["type"],
                                            Definition=m["suggestion"] or None, Source="Volume check",
                                            **{"Used in volumes": m["volumes"]})
            n += res == "added"
        diag.activity("volume_missing_added", added=n)
        self._save_effort_list()
        self.apply_effort()
        self.update_effort_ui()
        messagebox.showinfo("Effort list", f"{n} terms added as Proposed. Approve them in the app or in Excel.", parent=self._volwin)

    def record_volume_use(self):
        r = getattr(self, "volume_report", None)
        if not r or self.effort is None:
            return
        n = 0
        for term, fields in V.effort_updates(r).items():
            if term in self.effort.rows:
                n += self.effort.add_or_update(term, change_note="volume check: volumes and first use", **fields) == "updated"
        diag.activity("volume_use_recorded", n=n)
        self._save_effort_list()
        self.update_effort_ui()
        messagebox.showinfo("Effort list", f"Used in volumes and First use updated for {n} terms.", parent=self._volwin)
