"""Submission (2.37.0, phase 1): customer documents with their versions, and a clean compare.
2.39.0 (phase 2): Requirements first: what to deliver and how, read from every version (subreq.py), with its history.

Feature in the rail after Effort home. Steps: Requirements, Documents, Compare, Export.
- Requirements: due date, questions deadline, page limits per volume, font, margins, page size, spacing, file format,
  naming, copies, delivery and deliverables, each with where it was found and how it changed from version to version.
  A change stays marked until someone reviews it; confirm, edit, hide or type in requirements. The same summary shows
  as a bar across every feature and as the Submission card on Effort home.
- Documents: every customer document of the effort with its versions, newest first: when it arrived, who added it,
  the file, its SHA-256 fingerprint (a copy of its text is kept), what changed from the version before, and whether
  the change was reviewed. Add customer documents... reads each file and suggests which document it is a new version
  of (by name and by how much text is the same); you confirm. New files dropped in the customer documents folder
  show in a banner with Add them.
- Compare: any two versions of a document side by side, lined up sentence by sentence; removed words struck through
  in red, added words in green; Only changes, Only submission requirements; Up and Down jump between changes. Export
  a Word redline or an Excel list.
- Export: the version history of every document (Excel), with a sheet of changes for each new version.
Saved in the effort's folder as it happens (documents\\), like everything else. Rules and counts only (No AI).
"""
import datetime, os, shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
import diag
import docversions as DV
import subreq as SR

DOC_TYPES = (".docx", ".pdf", ".pptx", ".xlsx")


def _eng():
    import app_gui
    return app_gui


class SubmissionMixin:
    # ------------------------------------------------------------ the library of the open effort
    def doclib(self):
        ws = getattr(self, "ws", None)
        if ws is None or self.effort is None:
            return None
        folder = ws.p("documents")
        lib = getattr(self, "_doclib", None)
        if lib is None or lib.folder != folder:
            self._doclib = lib = DV.Library(folder).load()
        return lib

    def subreg(self):
        """The submission requirements of the open effort (2.39.0)."""
        lib = self.doclib()
        if lib is None:
            return None
        r = getattr(self, "_subreg", None)
        if r is None or r.lib is not lib:
            self._subreg = r = SR.Register(lib)
        return r

    def sub_customer_dir(self):
        L = self.effort
        info = (self.efforts.get(L.name) or {}) if L is not None else {}
        return info.get("customer_dir") or ""

    def sub_unadded(self):
        """Files in the customer documents folder that are not in the library yet (by fingerprint)."""
        lib, cd = self.doclib(), self.sub_customer_dir()
        if lib is None or not cd or not os.path.isdir(cd):
            return []
        have = {v.get("sha256") for d in lib.docs for v in d["versions"]}
        names = lib.files()
        out = []
        for f in sorted(os.listdir(cd), key=lambda f: os.path.getmtime(os.path.join(cd, f))):
            p = os.path.join(cd, f)
            if not (os.path.isfile(p) and f.lower().endswith(DOC_TYPES)) or f.startswith("~$"):
                continue
            if f.lower() in names:
                try:
                    if DV.sha256(p) in have:
                        continue
                except OSError:
                    continue
            out.append(p)
        return out

    # ------------------------------------------------------------ pages
    def _page_submission(self):
        A = dict(height=30, width=10)
        self._page_requirements()
        if hasattr(self, "_page_deliverables"):
            self._page_deliverables()                   # 2.41.0
        act = self.shell_actions("submission", "documents")
        ctk.CTkButton(act, text="Add customer documents...", command=self.sub_add_dialog, fg_color="#0F766E", **A).pack(side="left", padx=3)
        pg = self.shell_page("sub_docs")
        self._h(pg, "Customer documents", "Every customer document with its versions. A copy of each version's text and its "
                                          "fingerprint are kept, so the history holds up even if a file is replaced later.")
        self.sub_banner = ctk.CTkFrame(pg, corner_radius=10, fg_color=("#FFFBEB", "#422006"), border_width=1, border_color="#FCD34D")
        self.sub_banner_lbl = ctk.CTkLabel(self.sub_banner, text="", anchor="w")
        self.sub_banner_lbl.pack(side="left", padx=12, pady=8)
        ctk.CTkButton(self.sub_banner, text="Add them...", width=10, fg_color="#B45309",
                      command=lambda: self.sub_add_dialog(self.sub_unadded())).pack(side="left", padx=6)
        body = ctk.CTkFrame(pg, fg_color="transparent"); body.pack(fill="both", expand=True, padx=6, pady=6)
        self.sub_body = body
        self.sub_list = ctk.CTkScrollableFrame(body, width=330); self.sub_list.pack(side="left", fill="y")
        self.sub_detail = ctk.CTkScrollableFrame(body); self.sub_detail.pack(side="left", fill="both", expand=True, padx=(10, 0))
        self.sub_cur = None
        # Compare
        cp = self.shell_page("sub_compare")
        top = ctk.CTkFrame(cp, fg_color="transparent"); top.pack(fill="x", padx=6, pady=(10, 4))
        ctk.CTkLabel(top, text="Document").pack(side="left")
        self.cmp_doc = ctk.CTkOptionMenu(top, values=[""], width=260, command=lambda _v: self._cmp_doc_changed())
        self.cmp_doc.pack(side="left", padx=(6, 14))
        ctk.CTkLabel(top, text="From").pack(side="left")
        self.cmp_from = ctk.CTkOptionMenu(top, values=[""], width=200, command=lambda _v: self.cmp_refresh())
        self.cmp_from.pack(side="left", padx=(6, 14))
        ctk.CTkLabel(top, text="To").pack(side="left")
        self.cmp_to = ctk.CTkOptionMenu(top, values=[""], width=200, command=lambda _v: self.cmp_refresh())
        self.cmp_to.pack(side="left", padx=6)
        top2 = ctk.CTkFrame(cp, fg_color="transparent"); top2.pack(fill="x", padx=6)
        self.cmp_only = tk.BooleanVar(value=True)
        self.cmp_subonly = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(top2, text="Only changes", variable=self.cmp_only, command=self.cmp_refresh).pack(side="left")
        ctk.CTkCheckBox(top2, text="Only submission requirements", variable=self.cmp_subonly, command=self.cmp_refresh).pack(side="left", padx=14)
        ctk.CTkButton(top2, text="Export list (Excel)...", width=10, command=self.cmp_export_list).pack(side="right", padx=3)
        ctk.CTkButton(top2, text="Export redline (Word)...", width=10, command=self.cmp_export_redline).pack(side="right", padx=3)
        self.cmp_sum = ctk.CTkLabel(cp, text="", anchor="w", justify="left", wraplength=1000)
        self.cmp_sum.pack(fill="x", padx=8, pady=(6, 4))
        panes = tk.Frame(cp); panes.pack(fill="both", expand=True, padx=6, pady=(0, 8))
        panes.grid_columnconfigure(0, weight=1, uniform="p"); panes.grid_columnconfigure(1, weight=1, uniform="p")
        panes.grid_rowconfigure(1, weight=1)
        dpi = max(1.0, float(ctk.ScalingTracker.get_widget_scaling(cp)))
        size = int(round((getattr(self, "font_size", 13) + 1) * dpi))
        hf = ("Segoe UI", max(10, size - 2), "bold")             # scaled like the panes (2.37.0)
        self.cmp_hl = tk.Label(panes, text="", anchor="w", font=hf, bg="#F8FAFC", fg="#0F172A", padx=10, pady=6)
        self.cmp_hr = tk.Label(panes, text="", anchor="w", font=hf, bg="#F8FAFC", fg="#0F172A", padx=10, pady=6)
        self.cmp_hl.grid(row=0, column=0, sticky="ew"); self.cmp_hr.grid(row=0, column=1, sticky="ew")
        self.cmp_panes = []
        sb = ttk.Scrollbar(panes, orient="vertical", command=self._cmp_yview)
        for col in (0, 1):
            t = tk.Text(panes, wrap="word", relief="flat", bd=0, padx=14, pady=8, font=("Georgia", size), bg="#FFFFFF", fg="#1E293B",
                        spacing1=2, spacing3=int(6 * dpi), cursor="arrow", insertwidth=0, highlightthickness=0, exportselection=False,
                        yscrollcommand=lambda a, b, c=col: self._cmp_scrolled(c, a, b))
            t.grid(row=1, column=col, sticky="nsew", padx=(0, 1))
            t.tag_configure("head", font=("Segoe UI", max(9, size - 3), "bold"), spacing1=int(10 * dpi), foreground="#334155")
            t.tag_configure("del", background="#FEE2E2", foreground="#991B1B", overstrike=True)
            t.tag_configure("ins", background="#DCFCE7", foreground="#14532D", font=("Georgia", size, "bold"))
            t.tag_configure("gone", foreground="#94A3B8", font=("Georgia", size, "italic"))
            t.tag_configure("sub", lmargin1=0, lmargin2=0, background="#FFFBEB")
            t.tag_configure("cur", relief="solid", borderwidth=1)
            t.bind("<Key>", self._cmp_key)
            t.bind("<MouseWheel>", lambda e: (self._cmp_yview("scroll", int(-e.delta / 120), "units"), "break")[1])
            for seq in ("<Button-4>", "<Button-5>"):
                t.bind(seq, lambda e: (self._cmp_yview("scroll", -1 if e.num == 4 else 1, "units"), "break")[1])
            self.cmp_panes.append(t)
        sb.grid(row=1, column=2, sticky="ns")
        self.cmp_sb = sb
        self.cmp_rows, self.cmp_at = [], -1
        # Export
        ex = self.shell_page("sub_export")
        self._h(ex, "Export", "The version history of every customer document, with who added each version, when, its "
                              "file name and fingerprint, and a sheet of what changed in each new version.")
        c = self._card(ex)
        ctk.CTkButton(c, text="Version history (Excel)...", width=10, command=self.sub_export_history).pack(anchor="w", padx=14, pady=12)
        ctk.CTkLabel(ex, text="The files hold customer content: keep them on this PC or SharePoint.", anchor="w",
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=8, pady=6)

    # ------------------------------------------------------------ Requirements (2.39.0)
    REQ_SHOW = ("All requirements", "Changes to review", "Due dates and page limits", "Format and files", "Deliverables", "Hidden")

    def _page_requirements(self):
        A = dict(height=30, width=10)
        act = self.shell_actions("submission", "requirements")
        ctk.CTkButton(act, text="Add a requirement...", command=self.req_add_dialog, **A).pack(side="left", padx=3)
        ctk.CTkButton(act, text="Export (Excel)...", command=self.req_export, fg_color="#475569", **A).pack(side="left", padx=3)
        pg = self.shell_page("sub_reqs")
        self._h(pg, "Submission requirements", "What to deliver and how, read from every version of the customer documents. "
                                               "A change stays marked until someone reviews it. Rules only (No AI).")
        self.req_card = ctk.CTkFrame(pg, corner_radius=12, fg_color=("#FFFFFF", "#1F2937"), border_width=1,
                                     border_color=("#E2E8F0", "#334155"))
        self.req_card.pack(fill="x", padx=6, pady=(0, 6))
        self.req_cells = {}
        for i, (k, label) in enumerate((("due", "DUE"), ("pages", "PAGE LIMITS"), ("format", "FORMAT"), ("files", "FILES"),
                                       ("review", "TO REVIEW"))):
            self.req_card.grid_columnconfigure(i, weight=1, uniform="rc")
            cell = ctk.CTkFrame(self.req_card, fg_color="transparent")
            cell.grid(row=0, column=i, sticky="nsew", padx=12, pady=10)
            ctk.CTkLabel(cell, text=label, font=("Segoe UI", 10, "bold"), text_color=("#64748B", "#94A3B8"), anchor="w").pack(fill="x")
            v = ctk.CTkLabel(cell, text="", font=("Segoe UI", 14, "bold"), anchor="w", justify="left", wraplength=230)
            v.pack(fill="x")
            sub = ctk.CTkLabel(cell, text="", font=("Segoe UI", 11), anchor="w", justify="left", wraplength=230,
                               text_color=("#475569", "#94A3B8"))
            sub.pack(fill="x")
            self.req_cells[k] = (v, sub)
        bar = ctk.CTkFrame(pg, fg_color="transparent"); bar.pack(fill="x", padx=6)
        ctk.CTkLabel(bar, text="Show").pack(side="left")
        self.req_show = ctk.CTkOptionMenu(bar, values=list(self.REQ_SHOW), width=230, command=lambda _v: self.req_refresh())
        self.req_show.pack(side="left", padx=6)
        self.req_count = ctk.CTkLabel(bar, text="", text_color=("#475569", "#94A3B8"))
        self.req_count.pack(side="left", padx=10)
        body = ctk.CTkFrame(pg, fg_color="transparent"); body.pack(fill="both", expand=True, padx=6, pady=6)
        self.req_detail = ctk.CTkScrollableFrame(body, width=440)      # the history keeps its width; the table takes the rest
        self.req_detail.pack(side="right", fill="y", padx=(10, 0))
        left = tk.Frame(body); left.pack(side="left", fill="both", expand=True)
        cols = (("kind", "Kind", 100), ("subject", "Requirement", 150), ("value", "Says", 240), ("state", "Status", 140),
                ("src", "From", 200))
        self.req_tree = tv = ttk.Treeview(left, columns=[c[0] for c in cols], show="headings", selectmode="browse",
                                          style=getattr(self, "tree_style", "Treeview"))
        sc = float(ctk.ScalingTracker.get_widget_scaling(pg)) * getattr(self, "font_size", 13) / 13   # like the QA/QC tables
        for k, t, w in cols:
            tv.heading(k, text=t); tv.column(k, width=int(w * sc), minwidth=60, anchor="w", stretch=k == "value")
        tv.tag_configure("review", background="#FEF3C7", foreground="#78350F")
        tv.tag_configure("confirmed", background="#DCFCE7", foreground="#14532D")
        tv.tag_configure("manual", background="#E0F2FE", foreground="#0C4A6E")
        tv.tag_configure("removed", foreground="#94A3B8")
        sb = ttk.Scrollbar(left, orient="vertical", command=tv.yview); tv.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y"); tv.pack(fill="both", expand=True)
        tv.bind("<<TreeviewSelect>>", lambda _e: self._req_detail())

        self.req_rows, self.req_hist_at = {}, {}

    def _req_state(self, r):
        if r["manual"]:
            return "Typed in", "manual"
        if r["to_review"]:
            return ("Removed: review" if r["removed"] else "Changed: review"), "review"
        if r["hidden"]:
            return "Hidden", "removed"
        if r["removed"]:
            return "No longer in the documents", "removed"
        if r["confirmed"]:
            return "Confirmed", "confirmed"
        return "Found", ""

    def req_filter(self, rows, show):
        k = {"Due dates and page limits": ("Due", "Questions due", "Page limit"), "Format and files": ("Format", "File", "Copies", "Delivery"),
             "Deliverables": ("Deliverable",)}
        if show == "Changes to review":
            return [r for r in rows if r["to_review"]]
        if show == "Hidden":
            return [r for r in rows if r["hidden"]]
        if show in k:
            return [r for r in rows if r["kind"] in k[show] and not r["hidden"]]
        return [r for r in rows if not r["hidden"]]

    def req_refresh(self):
        """Fill the list and the summary card. Returns the rows shown."""
        if not hasattr(self, "req_tree"):
            return []
        reg = self.subreg()
        tv = self.req_tree
        keep = tv.selection()
        tv.delete(*tv.get_children())
        self.req_rows = {}
        if reg is None:
            self._req_card(None)
            self.req_count.configure(text="Open an effort first.")
            self._req_detail()
            return []
        allrows = reg.rows(include_hidden=True)
        self._req_card([r for r in allrows if not r["hidden"]])
        rows = self.req_filter(allrows, self.req_show.get())
        for r in rows:
            st, tag = self._req_state(r)
            src = "" if r["manual"] else f"{r['doc']}, {r['version']}"
            iid = tv.insert("", "end", values=(r["kind"], r["subject"], r["value"], st, src), tags=(tag,) if tag else ())
            self.req_rows[iid] = r
        n_rev = sum(1 for r in allrows if r["to_review"])
        lib = self.doclib()
        self.req_count.configure(text=(f"{len(rows)} shown of {sum(1 for r in allrows if not r['hidden'])}" +
                                       (f"  |  {n_rev} change{'s' if n_rev != 1 else ''} to review" if n_rev else "")
                                       if allrows else ("No customer documents yet: add them on Documents." if not lib.docs
                                                        else "No submission requirements found yet. Add a requirement... types one in.")))
        sel = [i for i in tv.get_children() if self.req_rows[i]["key"] in {self.req_rows.get(k, {}).get("key") for k in keep}] \
            if keep else []
        want = getattr(self, "_req_want", None)
        if want:
            sel = [i for i in tv.get_children() if self.req_rows[i]["key"] == want] or sel
            self._req_want = None
        if not sel and tv.get_children():
            sel = [tv.get_children()[0]]
        if sel:
            tv.selection_set(sel[0]); tv.see(sel[0])
        self._req_detail()
        return rows

    def req_summary_text(self, rows=None):
        """One line for the bar and the Effort home card: due date (days left), page limits, format, files, changes."""
        if rows is None:
            reg = self.subreg()
            rows = reg.rows() if reg else []
        if not rows:
            return ""
        s = SR.summary(rows)
        bits = []
        if s["due"]:
            n = SR.days_until(s["due"]["value"])
            bits.append(f"Due {s['due']['value']}" + ("" if n is None else " (due date passed)" if n < 0 else
                                                      " (today)" if n == 0 else f" ({n} day{'s' if n != 1 else ''})"))
        if s["pages"]:
            bits.append("Pages: " + ", ".join(f"{subj} {SR._limit_n(v)}" for subj, v, _r in s["pages"]))
        f = [r["value"] for r in s["format"] if r["subject"] in ("Font", "Margins")]
        if f:
            bits.append(", ".join(f))
        ff = [r["value"] for r in s["files"] if r["subject"] == "File format"]
        if ff:
            bits.append(ff[0])
        if s["to_review"]:
            n = len(s["to_review"])
            bits.append(f"{n} change{'s' if n != 1 else ''} to review")
        return "  |  ".join(bits)

    def _req_card(self, rows):
        cells = self.req_cells
        for v, sub in cells.values():
            v.configure(text="-"); sub.configure(text="")
        if not rows:
            return
        s = SR.summary(rows)
        if s["due"]:
            n = SR.days_until(s["due"]["value"])
            cells["due"][0].configure(text=s["due"]["value"])
            cells["due"][1].configure(text=("" if n is None else "The due date has passed" if n < 0 else "Today" if n == 0
                                            else f"{n} day{'s' if n != 1 else ''} from today") +
                                      ("" if not s["due"]["to_review"] else "  |  changed: review"))
        if s["pages"]:
            cells["pages"][0].configure(text="\n".join(f"{subj}: {v}" for subj, v, _r in s["pages"][:4]))
            cells["pages"][1].configure(text="changed: review" if any(r["to_review"] for _a, _b, r in s["pages"]) else "")
        if s["format"]:
            cells["format"][0].configure(text="\n".join(r["value"] for r in s["format"][:3]))
        if s["files"]:
            cells["files"][0].configure(text="\n".join(r["value"][:40] for r in s["files"][:3]))
        n = len(s["to_review"])
        cells["review"][0].configure(text=str(n) if n else "None", text_color=("#B45309", "#FBBF24") if n else ("#15803D", "#86EFAC"))
        cells["review"][1].configure(text=f"{len(s['deliverables'])} deliverable(s) found" if s["deliverables"] else "")

    def req_selected(self):
        sel = self.req_tree.selection() if hasattr(self, "req_tree") else ()
        return self.req_rows.get(sel[0]) if sel else None

    def _req_doc_of(self, vid):
        lib = self.doclib()
        for d in (lib.docs if lib else []):
            for i, v in enumerate(d["versions"]):
                if v["id"] == vid:
                    return d, i
        return None, -1

    def _req_detail(self):
        if not hasattr(self, "req_detail"):
            return
        for w in self.req_detail.winfo_children():
            w.destroy()
        r = self.req_selected()
        if r is None:
            return
        D = self.req_detail
        ctk.CTkLabel(D, text=r["subject"], font=("Segoe UI", 17, "bold"), anchor="w", justify="left", wraplength=400).pack(fill="x", padx=8, pady=(6, 0))
        st, _tag = self._req_state(r)
        ctk.CTkLabel(D, text=f"{r['kind']}  |  {st}", anchor="w", text_color=("#B45309", "#FBBF24") if r["to_review"]
                     else ("#475569", "#94A3B8")).pack(fill="x", padx=8)
        ctk.CTkLabel(D, text=r["value"], font=("Segoe UI", 15), anchor="w", justify="left", wraplength=400).pack(fill="x", padx=8, pady=(6, 0))
        if not r["manual"] and r["value"] != r["found"]:
            ctk.CTkLabel(D, text=f"Edited. The documents say: {r['found']}", anchor="w", justify="left", wraplength=400,
                         text_color=("#475569", "#94A3B8")).pack(fill="x", padx=8)
        if r["confirmed"]:
            ctk.CTkLabel(D, text=f"Confirmed {r['confirmed']}", anchor="w", text_color=("#15803D", "#86EFAC")).pack(fill="x", padx=8)
        if r["reviewed"] and not r["to_review"]:
            ctk.CTkLabel(D, text=f"Change reviewed {r['reviewed']}", anchor="w", text_color=("#15803D", "#86EFAC")).pack(fill="x", padx=8)
        row = ctk.CTkFrame(D, fg_color="transparent"); row.pack(fill="x", padx=4, pady=(8, 4))
        B = dict(width=10, height=28)
        if r["to_review"]:
            ctk.CTkButton(row, text="Mark reviewed", fg_color="#B45309", command=lambda: self.req_review(r["key"]), **B).pack(side="left", padx=3)
        if r["manual"]:
            ctk.CTkButton(row, text="Remove", fg_color="#B91C1C", command=lambda: self.req_remove(r["key"]), **B).pack(side="left", padx=3)
        else:
            if not r["confirmed"]:
                ctk.CTkButton(row, text="Confirm", fg_color="#15803D", command=lambda: self.req_confirm(r["key"]), **B).pack(side="left", padx=3)
            ctk.CTkButton(row, text="Edit...", command=lambda: self.req_edit(r["key"]), **B).pack(side="left", padx=3)
            ctk.CTkButton(row, text="Show again" if r["hidden"] else "Not a requirement", fg_color="#475569",
                          command=lambda: self.req_hide(r["key"], not r["hidden"]), **B).pack(side="left", padx=3)
        h = r["history"]
        if not h:
            return
        ctk.CTkLabel(D, text="HISTORY", font=("Segoe UI", 10, "bold"), text_color=("#64748B", "#94A3B8"), anchor="w").pack(fill="x", padx=8, pady=(12, 0))
        at = self.req_hist_at.get(r["key"], len(h) - 1)
        at = max(0, min(at, len(h) - 1))
        nav = ctk.CTkFrame(D, fg_color="transparent"); nav.pack(fill="x", padx=4)
        ctk.CTkButton(nav, text="< Previous", state="normal" if at > 0 else "disabled",
                      command=lambda: self.req_history(r["key"], at - 1), **B).pack(side="left", padx=3)
        ctk.CTkLabel(nav, text=f"Version {at + 1} of {len(h)}").pack(side="left", padx=8)
        ctk.CTkButton(nav, text="Next >", state="normal" if at < len(h) - 1 else "disabled",
                      command=lambda: self.req_history(r["key"], at + 1), **B).pack(side="left", padx=3)
        e = h[at]
        word = {"first": "First found", "same": "No change", "changed": "Changed", "removed": "Removed"}[e["change"]]
        card = ctk.CTkFrame(D, corner_radius=10, fg_color=("#FFFFFF", "#111827"), border_width=1,
                            border_color="#B45309" if e["change"] in ("changed", "removed") else ("#E2E8F0", "#334155"))
        card.pack(fill="x", padx=6, pady=6)
        ctk.CTkLabel(card, text=f"{e['doc']}, {e['version']}  |  {word}", font=("Segoe UI", 13, "bold"), anchor="w",
                     justify="left", wraplength=380).pack(fill="x", padx=12, pady=(8, 0))
        if e["change"] == "changed" and at > 0:
            ctk.CTkLabel(card, text=f"Was: {h[at - 1]['value'] or '(not stated)'}\nNow: {e['value']}", anchor="w", justify="left",
                         wraplength=380).pack(fill="x", padx=12, pady=(4, 0))
        elif e["change"] != "removed":
            ctk.CTkLabel(card, text=e["value"], anchor="w", justify="left", wraplength=380).pack(fill="x", padx=12, pady=(4, 0))
        if e["sentence"]:
            ctk.CTkLabel(card, text=f"“{e['sentence']}”", font=("Georgia", 12, "italic"), anchor="w", justify="left",
                         wraplength=380).pack(fill="x", padx=12, pady=(4, 0))
        if e["loc"]:
            ctk.CTkLabel(card, text=e["loc"], font=("Segoe UI", 11), anchor="w", justify="left", wraplength=380,
                         text_color=("#475569", "#94A3B8")).pack(fill="x", padx=12)
        ctk.CTkLabel(card, text=f"Added {e['added'].replace('T', ' ')} by {e['who']}  |  {e['file']}\n"
                                f"Fingerprint (SHA-256) {DV.short_sha(e['sha256'])}", font=("Segoe UI", 11), anchor="w",
                     justify="left", wraplength=380, text_color=("#475569", "#94A3B8")).pack(fill="x", padx=12, pady=(2, 0))
        d, i = self._req_doc_of(e["version_id"])
        if d is not None and i > 0 and e["change"] in ("changed", "removed"):
            ctk.CTkButton(card, text="Show the change", command=lambda: self.req_show_change(r["key"], at), **B).pack(anchor="w", padx=10, pady=8)
        else:
            ctk.CTkFrame(card, fg_color="transparent", height=6).pack()

    def req_history(self, key, at):
        self.req_hist_at[key] = at
        self._req_detail()
        return at

    def req_show_change(self, key, at=None):
        """Compare the version that changed a requirement with the one before it, on the changed sentence."""
        reg = self.subreg()
        r = next((x for x in reg.rows(include_hidden=True) if x["key"] == key), None) if reg else None
        if r is None or not r["history"]:
            return None
        at = len(r["history"]) - 1 if at is None else at
        e = r["history"][at]
        d, i = self._req_doc_of(e["version_id"])
        if d is None or i < 1:
            return None
        rows = self.sub_compare(d["id"], d["versions"][i - 1]["id"], e["version_id"])
        old = r["history"][at - 1]["sentence"] if at > 0 else ""
        hit = next((j for j, x in enumerate(rows) if x["kind"] != "same" and
                    ((e["sentence"] and x.get("new") == e["sentence"]) or (old and x.get("old") == old))), None)
        if hit is not None:
            self.cmp_at = hit - 1 if hit > 0 else -1
            self.cmp_at = hit
            for t in self.cmp_panes:
                t.tag_remove("cur", "1.0", "end")
                rg = t.tag_ranges("row:%d" % hit)
                if rg:
                    t.tag_add("cur", rg[0], rg[1]); t.see(rg[0])
        return hit

    def _req_trail(self, key, what):
        if hasattr(self, "rec_log"):
            kind, _sep, subject = key.partition(" | ")
            self.rec_log("requirement", f"{kind}, {subject}: {what}")

    def _req_after(self, key):
        self._req_want = key
        self.req_refresh()
        self.sub_bar_refresh() if hasattr(self, "sub_bar_refresh") else None

    def req_review(self, key):
        reg = self.subreg()
        if reg and reg.review(key):
            diag.activity("submission_requirement_reviewed")
            self._req_trail(key, "change reviewed")
            self._req_after(key)
            return True
        return False

    def req_confirm(self, key):
        reg = self.subreg()
        if reg and reg.confirm(key):
            diag.activity("submission_requirement_confirmed")
            self._req_trail(key, "confirmed")
            self._req_after(key)
            return True
        return False

    def req_edit(self, key, value=None):
        reg = self.subreg()
        r = next((x for x in reg.rows(include_hidden=True) if x["key"] == key), None) if reg else None
        if r is None:
            return False
        if value is None:
            from tkinter import simpledialog
            value = simpledialog.askstring("Edit requirement", f"{r['subject']} (leave empty to go back to what the documents say):",
                                           initialvalue=r["value"], parent=self)
            if value is None:
                return False
        reg.edit(key, value)
        diag.activity("submission_requirement_edited")
        self._req_trail(key, f"edited to: {value}" if " ".join((value or "").split()) else "back to what the documents say")
        self._req_after(key)
        return True

    def req_hide(self, key, hidden=True):
        reg = self.subreg()
        if reg and reg.hide(key, hidden):
            diag.activity("submission_requirement_hidden")
            self._req_trail(key, "marked not a requirement" if hidden else "shown again")
            self._req_after(key)
            return True
        return False

    def req_remove(self, key):
        reg = self.subreg()
        if reg and reg.remove_manual(key):
            diag.activity("submission_requirement_removed")
            self._req_after(None)
            return True
        return False

    def req_add_dialog(self, kind=None, subject=None, value=None):
        """Type in a requirement the documents do not state, or state in a way the rules miss."""
        reg = self.subreg()
        if reg is None:
            messagebox.showinfo("Add a requirement", "Open an effort first.")
            return None
        if value is not None:
            k = reg.add(kind or "Format", subject or "", value)
            if k:
                diag.activity("submission_requirement_added")
                self._req_trail(k, f"typed in: {value}")
                self._req_after(k)
            return k
        w = ctk.CTkToplevel(self); w.title("Add a requirement"); w.transient(self)
        w.geometry("520x260")
        ctk.CTkLabel(w, text="Kind").grid(row=0, column=0, sticky="w", padx=12, pady=(14, 4))
        om = ctk.CTkOptionMenu(w, values=list(SR.KINDS)); om.set("Page limit"); om.grid(row=0, column=1, sticky="w", padx=8, pady=(14, 4))
        ctk.CTkLabel(w, text="Requirement").grid(row=1, column=0, sticky="w", padx=12, pady=4)
        e1 = ctk.CTkEntry(w, width=320, placeholder_text="Volume II, Font, Attachment J-3..."); e1.grid(row=1, column=1, sticky="w", padx=8, pady=4)
        ctk.CTkLabel(w, text="Says").grid(row=2, column=0, sticky="w", padx=12, pady=4)
        e2 = ctk.CTkEntry(w, width=320, placeholder_text="15 pages"); e2.grid(row=2, column=1, sticky="w", padx=8, pady=4)

        def ok():
            k = reg.add(om.get(), e1.get(), e2.get())
            if k:
                diag.activity("submission_requirement_added")
                self._req_trail(k, f"typed in: {e2.get().strip()}")
                w.destroy()
                self._req_after(k)
        ctk.CTkButton(w, text="Add", command=ok).grid(row=3, column=1, sticky="w", padx=8, pady=14)
        e2.bind("<Return>", lambda _e: ok())
        w._api = {"kind": om, "subject": e1, "value": e2, "ok": ok}
        w.after(100, w.lift)
        return w

    def req_export(self, path=None):
        reg = self.subreg()
        if reg is None:
            return None
        rows = reg.rows(include_hidden=True)
        if path is None:
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                                initialfile=f"{self.effort.name}_Submission_Requirements.xlsx".replace(" ", "_"))
        if not path:
            return None
        SR.export_excel(path, rows, self.effort.name)
        diag.activity("submission_exported")
        self.status.configure(text="Submission requirements written.")
        return path

    # ------------------------------------------------------------ the bar across every feature (2.39.0)
    def sub_bar_build(self, M):
        self.subbar = ctk.CTkFrame(M, corner_radius=0, fg_color=("#F1F5F9", "#1E293B"), height=28)
        self.subbar_lbl = ctk.CTkLabel(self.subbar, text="", anchor="w", font=("Segoe UI", 12), cursor="hand2")
        self.subbar_lbl.pack(side="left", fill="x", expand=True, padx=18, pady=3)
        self.subbar_lbl.bind("<Button-1>", lambda _e: self.shell_go("submission", "requirements"))
        self.subbar.bind("<Button-1>", lambda _e: self.shell_go("submission", "requirements"))
        diag.register(self.subbar_lbl, "submission_bar") if hasattr(diag, "register") else None

    def sub_bar_refresh(self):
        """Show the submission summary under the step strip while an effort with requirements is open."""
        if not hasattr(self, "subbar"):
            return ""
        try:
            reg = self.subreg()
            rows = reg.rows() if reg else []
        except Exception:
            diag.swallowed(); rows = []
        text = self.req_summary_text(rows) if rows else ""
        if text:
            todo = any(r["to_review"] for r in rows)
            self.subbar.configure(fg_color=("#FEF3C7", "#422006") if todo else ("#F1F5F9", "#1E293B"))
            self.subbar_lbl.configure(text="SUBMISSION   " + text, text_color=("#78350F", "#FDE68A") if todo else ("#334155", "#CBD5E1"))
            if not self.subbar.winfo_manager():
                self.subbar.pack(fill="x", side="top", after=self.strip)
        elif self.subbar.winfo_manager():
            self.subbar.pack_forget()
        return text

    # ------------------------------------------------------------ Documents
    def sub_refresh(self):
        lib = self.doclib()
        if not hasattr(self, "sub_list"):
            return
        new = self.sub_unadded() if lib is not None else []
        if new:
            first = not (lib and lib.docs)
            self.sub_banner_lbl.configure(text=(f"{len(new)} customer document(s) are not in the history yet." if first else
                                                f"{len(new)} new file(s) in the customer documents folder."))
            if not self.sub_banner.winfo_manager():
                self.sub_banner.pack(fill="x", padx=6, pady=(0, 4), before=self.sub_body)
        elif self.sub_banner.winfo_manager():
            self.sub_banner.pack_forget()
        for w in self.sub_list.winfo_children():
            w.destroy()
        if lib is None:
            ctk.CTkLabel(self.sub_list, text="Open an effort first.").pack(anchor="w", padx=8, pady=8)
            return
        if not lib.docs:
            ctk.CTkLabel(self.sub_list, text="No customer documents yet.\nAdd customer documents... reads them.", justify="left").pack(anchor="w", padx=8, pady=8)
        if self.sub_cur not in [d["id"] for d in lib.docs]:
            self.sub_cur = lib.docs[0]["id"] if lib.docs else None
        for d in lib.docs:
            last = lib.latest(d)
            n = len(d["versions"])
            todo = sum(1 for v in d["versions"][1:] if not v.get("reviewed"))
            on = d["id"] == self.sub_cur
            txt = f"{d['name'][:34]}\n{n} version{'s' if n != 1 else ''}  |  latest {last['label']}, {last['added'][:10]}" + \
                  (f"\n{todo} change{'s' if todo != 1 else ''} not reviewed" if todo else "")
            ctk.CTkButton(self.sub_list, text=txt, anchor="w", width=310, height=58 if not todo else 76, border_width=2 if on else 1,
                          fg_color=("#EFF6FF", "#1E3A8A") if on else ("#FFFFFF", "#1F2937"), text_color=("#0F172A", "#F1F5F9"),
                          border_color="#1E3A8A" if on else ("#E2E8F0", "#334155"), hover_color=("#E2E8F0", "#334155"),
                          command=lambda i=d["id"]: self.sub_show(i)).pack(fill="x", pady=2)
        self._sub_detail()

    def sub_show(self, doc_id):
        self.sub_cur = doc_id
        self.sub_refresh()

    def _sub_change_text(self, d, i):
        """What changed from the version before (cached by the two version ids)."""
        if i == 0:
            return f"{d['versions'][0].get('sentences', 0)} sentences read."
        cache = self.__dict__.setdefault("_sub_sum", {})
        key = (d["versions"][i - 1]["id"], d["versions"][i]["id"])
        if key not in cache:
            lib = self.doclib()
            rows = DV.compare(lib.text(d["versions"][i - 1]), lib.text(d["versions"][i]))
            cache[key] = DV.summary_text(DV.summary(rows)) + "."
        return cache[key]

    def _sub_detail(self):
        for w in self.sub_detail.winfo_children():
            w.destroy()
        lib = self.doclib()
        d = lib.doc(self.sub_cur) if lib and self.sub_cur else None
        if d is None:
            return
        top = ctk.CTkFrame(self.sub_detail, fg_color="transparent"); top.pack(fill="x", padx=6, pady=(4, 8))
        ctk.CTkLabel(top, text=f"{d['name']}: version history", font=("Segoe UI", 18, "bold"), anchor="w").pack(side="left")
        ctk.CTkButton(top, text="Rename...", width=10, fg_color="#475569", command=lambda: self.sub_rename(doc_id=d["id"])).pack(side="right")
        vs = d["versions"]
        for i in range(len(vs) - 1, -1, -1):
            v = vs[i]
            card = ctk.CTkFrame(self.sub_detail, corner_radius=10, fg_color=("#FFFFFF", "#1F2937"), border_width=1,
                                border_color="#B45309" if i and not v.get("reviewed") else ("#E2E8F0", "#334155"))
            card.pack(fill="x", padx=6, pady=4)
            ctk.CTkLabel(card, text=f"{v['label']}", font=("Segoe UI", 15, "bold"), anchor="w").pack(fill="x", padx=14, pady=(10, 0))
            ctk.CTkLabel(card, text=f"Added {v['added'].replace('T', ' ')} by {v['who']}  |  {v['file']}", anchor="w",
                         text_color=("#475569", "#94A3B8")).pack(fill="x", padx=14)
            ctk.CTkLabel(card, text=self._sub_change_text(d, i), anchor="w", justify="left", wraplength=760).pack(fill="x", padx=14, pady=(4, 0))
            ctk.CTkLabel(card, text=f"Fingerprint (SHA-256) {DV.short_sha(v['sha256'])}  |  text copy kept", anchor="w",
                         font=("Segoe UI", 11), text_color=("#475569", "#94A3B8")).pack(fill="x", padx=14)
            if i:
                ctk.CTkLabel(card, text=(f"Reviewed {v['reviewed']}" if v.get("reviewed") else "Not reviewed yet"), anchor="w",
                             text_color=("#15803D", "#86EFAC") if v.get("reviewed") else ("#B45309", "#FBBF24")).pack(fill="x", padx=14)
            row = ctk.CTkFrame(card, fg_color="transparent"); row.pack(fill="x", padx=10, pady=(6, 10))
            if i:
                ctk.CTkButton(row, text=f"Compare with {vs[i - 1]['label']}", width=10,
                              command=lambda a=vs[i - 1]["id"], b=v["id"]: self.sub_compare(d["id"], a, b)).pack(side="left", padx=3)
                if not v.get("reviewed"):
                    ctk.CTkButton(row, text="Mark reviewed", width=10, fg_color="#B45309",
                                  command=lambda vid=v["id"]: self.sub_mark_reviewed(vid)).pack(side="left", padx=3)
            ctk.CTkButton(row, text="Rename...", width=10, fg_color="#475569",
                          command=lambda vid=v["id"]: self.sub_rename(vid=vid)).pack(side="left", padx=3)
            ctk.CTkButton(row, text="Move to document...", width=10, fg_color="#475569",
                          command=lambda vid=v["id"]: self.sub_move_dialog(vid)).pack(side="left", padx=3)
            ctk.CTkButton(row, text="Open file", width=10, fg_color="#475569",
                          command=lambda p=v.get("path", ""): self._sub_open(p)).pack(side="left", padx=3)

    def _sub_open(self, p):
        if p and os.path.isfile(p):
            try:
                os.startfile(p)                    # noqa (Windows)
            except Exception:
                diag.swallowed()
        else:
            messagebox.showinfo("Open file", "The file is no longer where it was added. The text copy is still kept, so Compare works.")

    def sub_mark_reviewed(self, vid):
        lib = self.doclib()
        if lib and lib.mark_reviewed(vid):
            diag.activity("submission_reviewed")
            d = next((x for x in lib.docs for v in x["versions"] if v["id"] == vid), None)
            v = next((v for v in (d["versions"] if d else []) if v["id"] == vid), None)
            if v is not None and hasattr(self, "rec_log"):
                self.rec_log("customer", f"{d['name']}: {v['label']} changes reviewed", ref={"version": vid})
            self.sub_refresh()
            self._shell_rail_style() if hasattr(self, "_shell_rail_style") else None
            return True
        return False

    def sub_rename(self, doc_id=None, vid=None, name=None):
        lib = self.doclib()
        if lib is None:
            return False
        if name is None:
            d = ctk.CTkInputDialog(title="Rename", text="New name:")
            name = d.get_input()
        if name and lib.rename(doc_id=doc_id, vid=vid, name=name):
            self.sub_refresh()
            return True
        return False

    def sub_move_dialog(self, vid, to_doc=None):
        """Make a version part of another document's history."""
        lib = self.doclib()
        if lib is None:
            return False
        others = [d for d in lib.docs if not any(v["id"] == vid for v in d["versions"])]
        if not others:
            messagebox.showinfo("A version of another document", "There is no other document yet.")
            return False
        if to_doc is None:
            w = ctk.CTkToplevel(self); w.title("A version of another document"); w.geometry("460x170"); w.transient(self); w.after(150, w.lift)
            ctk.CTkLabel(w, text="This file is a version of:").pack(anchor="w", padx=14, pady=(14, 4))
            names = [d["name"] for d in others]
            om = ctk.CTkOptionMenu(w, values=names, width=420); om.pack(padx=14)
            def ok():
                dst = others[names.index(om.get())]["id"]
                w.destroy()
                self.sub_move_dialog(vid, dst)
            ctk.CTkButton(w, text="Move", command=ok).pack(pady=12)
            return w
        ok = lib.move_version(vid, to_doc)
        if ok:
            diag.activity("submission_version_moved")
            self.sub_cur = to_doc
            self.sub_refresh()
        return ok

    # ------------------------------------------------------------ adding documents
    def sub_read(self, path):
        """The text of a file, sentence by sentence (typed text only)."""
        try:
            chunks = _eng().typed_chunks(path)
        except Exception:
            diag.swallowed()
            chunks = []
        return DV.snapshot(os.path.basename(path), chunks)

    def sub_plan(self, paths):
        """For each new file: its text and the suggested match. Files are taken oldest first so a later file can be
        matched to an earlier one in the same batch. Returns [entry]."""
        lib = self.doclib()
        plan = []
        for p in paths:
            try:
                h = DV.sha256(p)
            except OSError:
                continue
            got = lib.find_sha(h)
            if got:
                plan.append({"path": p, "sha": h, "dup": got, "sents": [], "choice": "skip"})
                continue
            sents = self.sub_read(p)
            cands = [(d, sc, how) for d, sc, how in lib.suggest(os.path.basename(p), [s["x"] for s in sents])]
            for k, e in enumerate(plan):           # earlier files in this batch that will become new documents
                if e.get("dup") or e["choice"] != "new":
                    continue
                ns = DV.name_similarity(os.path.basename(p), os.path.basename(e["path"]))
                ts = DV.text_similarity([s["x"] for s in sents], [s["x"] for s in e["sents"]])
                sc = round(max(ts, 0.5 * ns + 0.5 * ts), 3)
                cands.append(({"id": f"batch:{k}", "name": e["name"], "versions": []}, sc,
                              f"{int(round(ts * 100))}% of the text is the same" + ("; the name matches" if ns >= 0.9 else "")))
            cands.sort(key=lambda x: -x[1])
            best = cands[0] if cands and DV.Library.band(cands[0][1]) else None
            e = {"path": p, "sha": h, "sents": sents, "cands": cands, "best": best,
                 "choice": "version" if best and DV.Library.band(best[1]) == "strong" else "new",
                 "doc": best[0]["id"] if best else None,
                 "name": DV.display_name(p),
                 "label": ""}
            plan.append(e)
        return plan

    def sub_apply(self, plan):
        """Add the planned files: copy each into the customer documents folder, then record it. Returns [(doc, version)]."""
        lib = self.doclib()
        cd = self.sub_customer_dir()
        made, batch_doc = [], {}
        for k, e in enumerate(plan):
            if e.get("dup") or e["choice"] == "skip":
                continue
            src = e["path"]
            dest = src
            if cd and os.path.isdir(cd) and os.path.normcase(os.path.dirname(os.path.abspath(src))) != os.path.normcase(os.path.abspath(cd)):
                dest = os.path.join(cd, os.path.basename(src))
                if os.path.exists(dest) and DV.sha256(dest) != e["sha"]:
                    base, ext = os.path.splitext(dest)
                    dest = f"{base}_{datetime.datetime.now().strftime('%Y%m%d_%H%M')}{ext}"
                try:
                    if not os.path.exists(dest):
                        shutil.copy2(src, dest)
                except OSError:
                    diag.swallowed(); dest = src
            doc_id = e.get("doc") if e["choice"] == "version" else None
            if doc_id and str(doc_id).startswith("batch:"):
                doc_id = batch_doc.get(int(doc_id.split(":")[1]))
            d, v = lib.add(dest, e["sents"], doc_id=doc_id, doc_name=e.get("name", ""), label=e.get("label", ""), sha=e["sha"])
            batch_doc[k] = d["id"]
            made.append((d, v))
        if made:
            diag.activity("submission_added", n=len(made))
            self.sub_cur = made[-1][0]["id"]
            for d, v in made:                              # 2.40.0: the paper trail
                i = d["versions"].index(v)
                what = ""
                if i:
                    try:
                        what = "; " + DV.summary_text(DV.summary(DV.compare(lib.text(d["versions"][i - 1]), lib.text(v))))
                    except Exception:
                        diag.swallowed()
                self.rec_log("customer", f"{d['name']}: {v['label']} added ({v['file']}){what}" if i else
                             f"{d['name']} added ({v['file']}, {v.get('sentences', 0)} sentences)", ref={"version": v["id"]}) \
                    if hasattr(self, "rec_log") else None
        self.sub_refresh()
        if hasattr(self, "_shell_rail_style"):
            self._shell_rail_style()
        return made

    def sub_add_dialog(self, paths=None, wait=False):
        """Pick files (or take the ones given), show what each one is, and add them on Add."""
        if self.doclib() is None:
            messagebox.showinfo("Customer documents", "Open an effort first.")
            return None
        if paths is None:
            paths = list(filedialog.askopenfilenames(parent=self, title="Customer documents",
                                                     filetypes=[("Documents", "*.docx *.pdf *.pptx *.xlsx")]) or [])
        if not paths:
            return None
        try:
            paths = sorted(paths, key=os.path.getmtime)
        except OSError:
            pass
        self.status.configure(text=f"Reading {len(paths)} file(s)...")
        self.update_idletasks()
        plan = self.sub_plan(paths)
        win = ctk.CTkToplevel(self); win.title("Customer documents"); win.geometry("900x620"); win.transient(self); win.after(150, win.lift)
        diag.register(win, "submission_add")
        ctk.CTkLabel(win, text=f"{len(plan)} file(s). Check what each one is: the app matched them by name and by how much of the text is "
                               "the same.", anchor="w", justify="left", wraplength=860).pack(fill="x", padx=14, pady=(12, 6))
        sf = ctk.CTkScrollableFrame(win); sf.pack(fill="both", expand=True, padx=10)
        lib = self.doclib()
        win._rows = []
        for k, e in enumerate(plan):
            card = ctk.CTkFrame(sf, corner_radius=10, border_width=1, border_color=("#CBD5E1", "#334155"))
            card.pack(fill="x", pady=4, padx=2)
            head = ctk.CTkFrame(card, fg_color="transparent"); head.pack(fill="x", padx=12, pady=(8, 2))
            ctk.CTkLabel(head, text=os.path.basename(e["path"]), font=("Segoe UI", 14, "bold")).pack(side="left")
            if e.get("dup"):
                d, v = e["dup"]
                ctk.CTkLabel(card, text=f"Already in the history: {d['name']}, {v['label']} (same fingerprint). Skipped.", anchor="w",
                             text_color=("#475569", "#94A3B8")).pack(fill="x", padx=12, pady=(0, 8))
                win._rows.append(None)
                continue
            band = DV.Library.band(e["best"][1]) if e["best"] else ""
            ctk.CTkLabel(head, text=(f"{'Strong' if band == 'strong' else 'Possible'} match: {e['best'][2]}" if e["best"] else "No match: a new document"),
                         text_color=("#15803D", "#86EFAC") if band == "strong" else ("#475569", "#94A3B8")).pack(side="right")
            var = tk.StringVar(value=e["choice"])
            doc_names = [c[0]["name"] for c in e["cands"]]
            ids = [c[0]["id"] for c in e["cands"]]
            r1 = ctk.CTkFrame(card, fg_color="transparent"); r1.pack(fill="x", padx=12, pady=2)
            ctk.CTkRadioButton(r1, text="A new version of", variable=var, value="version",
                               state="normal" if ids else "disabled").pack(side="left")
            om = ctk.CTkOptionMenu(r1, values=doc_names or [""], width=280)
            om.set(e["best"][0]["name"] if e["best"] else (doc_names[0] if doc_names else ""))
            om.pack(side="left", padx=6)
            ctk.CTkLabel(r1, text="named").pack(side="left")
            lab = ctk.CTkEntry(r1, width=150)
            nxt = None
            if e["best"]:
                bd = lib.doc(e["best"][0]["id"])
                nxt = lib.next_label(bd) if bd else "Amendment 1"
            lab.insert(0, nxt or "Amendment 1")
            lab.pack(side="left", padx=6)
            r2 = ctk.CTkFrame(card, fg_color="transparent"); r2.pack(fill="x", padx=12, pady=(2, 10))
            ctk.CTkRadioButton(r2, text="A new document, named", variable=var, value="new").pack(side="left")
            nm = ctk.CTkEntry(r2, width=300); nm.insert(0, e["name"]); nm.pack(side="left", padx=6)
            subs = sum(1 for s in e["sents"] if DV.is_submission(s["x"]))
            ctk.CTkLabel(card, text=f"{len(e['sents'])} sentences read; {subs} look like submission requirements (format, page limits, "
                                    "due dates, files).", anchor="w", text_color=("#475569", "#94A3B8")).pack(fill="x", padx=12, pady=(0, 8))
            win._rows.append((var, om, ids, doc_names, lab, nm))

        def gather():
            for e, row in zip(plan, win._rows):
                if row is None:
                    continue
                var, om, ids, names, lab, nm = row
                e["choice"] = var.get()
                if e["choice"] == "version" and om.get() in names:
                    e["doc"] = ids[names.index(om.get())]
                e["label"] = lab.get().strip() if e["choice"] == "version" else "Original"
                e["name"] = nm.get().strip() or e["name"]
            return plan

        def add():
            made = self.sub_apply(gather())
            win.destroy()
            self.status.configure(text=f"Added {len(made)} customer document version(s).")
            if made and hasattr(self, "shell_go"):
                self.shell_go("submission", "documents")
            return made

        b = ctk.CTkFrame(win, fg_color="transparent"); b.pack(fill="x", padx=14, pady=10)
        ctk.CTkButton(b, text="Add and show the history", fg_color="#1E3A8A", command=add).pack(side="right")
        ctk.CTkButton(b, text="Cancel", fg_color="#475569", command=win.destroy).pack(side="right", padx=8)
        win._api = {"plan": plan, "gather": gather, "add": add, "rows": win._rows}
        self.status.configure(text="")
        return win

    # ------------------------------------------------------------ Compare
    def sub_compare(self, doc_id, a=None, b=None):
        """Open Compare on two versions (the last two by default)."""
        self._cmp_sel = (doc_id, a, b)
        if hasattr(self, "shell_go"):
            self.shell_go("submission", "compare")
        else:
            self.cmp_fill()
        return self.cmp_rows

    def _cmp_versions(self, d):
        return [f"{v['label']} ({v['added'][:10]})" for v in d["versions"]]

    def cmp_fill(self):
        lib = self.doclib()
        if lib is None or not hasattr(self, "cmp_doc"):
            return
        docs = [d for d in lib.docs if len(d["versions"]) >= 1]
        names = [d["name"] for d in docs] or [""]
        sel = getattr(self, "_cmp_sel", None) or (None, None, None)
        d = lib.doc(sel[0]) if sel[0] else None
        if d is None:
            d = next((x for x in docs if len(x["versions"]) > 1), docs[0] if docs else None)
        self.cmp_doc.configure(values=names)
        if d is None:
            self.cmp_doc.set(""); self.cmp_from.configure(values=[""]); self.cmp_to.configure(values=[""])
            self.cmp_sum.configure(text="No customer documents yet: add them on Documents.")
            self._cmp_render([], None, None)
            return
        self.cmp_doc.set(d["name"])
        vals = self._cmp_versions(d)
        self.cmp_from.configure(values=vals); self.cmp_to.configure(values=vals)
        ids = [v["id"] for v in d["versions"]]
        a = sel[1] if sel[1] in ids else (ids[-2] if len(ids) > 1 else ids[-1])
        b = sel[2] if sel[2] in ids else ids[-1]
        self.cmp_from.set(vals[ids.index(a)]); self.cmp_to.set(vals[ids.index(b)])
        self._cmp_sel = (d["id"], a, b)
        self.cmp_refresh()

    def _cmp_doc_changed(self):
        lib = self.doclib()
        d = next((x for x in lib.docs if x["name"] == self.cmp_doc.get()), None)
        self._cmp_sel = (d["id"] if d else None, None, None)
        self.cmp_fill()

    def _cmp_current(self):
        lib = self.doclib()
        d = next((x for x in lib.docs if x["name"] == self.cmp_doc.get()), None) if lib else None
        if d is None:
            return None, None, None
        vals = self._cmp_versions(d)
        try:
            va = d["versions"][vals.index(self.cmp_from.get())]
            vb = d["versions"][vals.index(self.cmp_to.get())]
        except ValueError:
            return d, None, None
        return d, va, vb

    def cmp_refresh(self):
        d, va, vb = self._cmp_current()
        if d is None or va is None:
            return []
        lib = self.doclib()
        self._cmp_sel = (d["id"], va["id"], vb["id"])
        rows = DV.compare(lib.text(va), lib.text(vb)) if va is not vb else []
        self.cmp_all = rows
        c = DV.summary(rows)
        self.cmp_sum.configure(text=(f"{DV.summary_text(c)} in {len(rows)} sentences.   Removed words struck through in red, added "
                                     "words in green; amber rows touch submission requirements. Up and Down jump between changes."
                                     if va is not vb else "Pick two different versions."))
        self._cmp_render(rows, va, vb)
        diag.activity("submission_compared", n=c["changed"] + c["added"] + c["removed"])
        return rows

    def _cmp_render(self, rows, va, vb):
        L, R = self.cmp_panes
        self.cmp_hl.configure(text=f"{va['label']}   {va['file']}" if va else "")
        self.cmp_hr.configure(text=f"{vb['label']}   {vb['file']}" if vb else "")
        shown = [r for r in rows if (not self.cmp_only.get() or r["kind"] != "same") and (not self.cmp_subonly.get() or r.get("submission"))]
        self.cmp_rows = shown
        self.cmp_at = -1
        for t in (L, R):
            t.configure(state="normal"); t.delete("1.0", "end")
        sec = None
        for i, r in enumerate(shown):
            if r["section"] and r["section"] != sec:
                for t in (L, R):
                    t.insert("end", r["section"] + "\n", ("head",))
                sec = r["section"]
            tags = ("row:%d" % i,) + (("sub",) if r.get("submission") else ())
            sl, sr = L.index("end-1c"), R.index("end-1c")
            if r["kind"] == "changed":
                for k, w in r["diff"]:
                    if k in ("=", "-"):
                        L.insert("end", w + " ", tags + (("del",) if k == "-" else ()))
                    if k in ("=", "+"):
                        R.insert("end", w + " ", tags + (("ins",) if k == "+" else ()))
            elif r["kind"] == "removed":
                L.insert("end", r["old"], tags + ("del",)); R.insert("end", "(removed)", tags + ("gone",))
            elif r["kind"] == "added":
                L.insert("end", "(not in this version)", tags + ("gone",)); R.insert("end", r["new"], tags + ("ins",))
            else:
                L.insert("end", r["old"], tags); R.insert("end", r["new"], tags)
            L.insert("end", "\n"); R.insert("end", "\n")
        if not shown and rows:
            for t in (L, R):
                t.insert("end", "No changes to show with these filters.", ("gone",))
        self._cmp_align(len(shown))
        for t in (L, R):
            t.configure(state="disabled")

    def _cmp_align(self, n):
        """Pad the shorter side of each row so both panes line up."""
        L, R = self.cmp_panes
        try:
            L.update_idletasks()
        except Exception:
            return
        for i in range(n - 1, -1, -1):
            a, b = L.tag_ranges("row:%d" % i), R.tag_ranges("row:%d" % i)
            if not a or not b:
                continue
            la = L.count(a[0], a[1], "displaylines")
            lb = R.count(b[0], b[1], "displaylines")
            la = (la[0] if isinstance(la, tuple) else la) or 0
            lb = (lb[0] if isinstance(lb, tuple) else lb) or 0
            if la > lb:
                R.insert(b[1], "\n" * (la - lb))
            elif lb > la:
                L.insert(a[1], "\n" * (lb - la))

    def _cmp_yview(self, *args):
        for t in self.cmp_panes:
            t.yview(*args)

    def _cmp_scrolled(self, col, a, b):
        self.cmp_sb.set(a, b)
        other = self.cmp_panes[1 - col]
        if abs(float(other.yview()[0]) - float(a)) > 1e-4:
            other.yview_moveto(a)

    def _cmp_key(self, e):
        k = (e.keysym or "").lower()
        if k in ("down", "next"):
            self.cmp_jump(+1)
        elif k in ("up", "prior"):
            self.cmp_jump(-1)
        else:
            return None
        return "break"

    def cmp_jump(self, d):
        """Next or previous change (skips sentences that are the same)."""
        rows = self.cmp_rows
        idx = [i for i, r in enumerate(rows) if r["kind"] != "same"]
        if not idx:
            return None
        if d > 0:
            nxt = next((i for i in idx if i > self.cmp_at), idx[0])
        else:
            nxt = next((i for i in reversed(idx) if i < self.cmp_at), idx[-1])
        self.cmp_at = nxt
        for t in self.cmp_panes:
            t.tag_remove("cur", "1.0", "end")
            r = t.tag_ranges("row:%d" % nxt)
            if r:
                t.tag_add("cur", r[0], r[1]); t.see(r[0])
        return nxt

    def cmp_export_redline(self, path=None):
        d, va, vb = self._cmp_current()
        if d is None or va is None or va is vb:
            return None
        if path is None:
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".docx", filetypes=[("Word", "*.docx")],
                                                initialfile=f"{d['name']}_{va['label']}_to_{vb['label']}_Redline.docx".replace(" ", "_"))
        if not path:
            return None
        DV.export_redline(path, d["name"], va, vb, getattr(self, "cmp_all", []), only_changes=bool(self.cmp_only.get()))
        diag.activity("submission_exported")
        self.status.configure(text="Redline written.")
        return path

    def cmp_export_list(self, path=None):
        d, va, vb = self._cmp_current()
        if d is None or va is None or va is vb:
            return None
        if path is None:
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                                initialfile=f"{d['name']}_{va['label']}_to_{vb['label']}_Changes.xlsx".replace(" ", "_"))
        if not path:
            return None
        DV.export_list(path, self.doclib(), doc=d, compares=[(d, va, vb, getattr(self, "cmp_all", []))])
        diag.activity("submission_exported")
        self.status.configure(text="Change list written.")
        return path

    # ------------------------------------------------------------ Export
    def sub_history_compares(self):
        lib = self.doclib()
        out = []
        for d in lib.docs:
            vs = d["versions"]
            for i in range(1, len(vs)):
                out.append((d, vs[i - 1], vs[i], DV.compare(lib.text(vs[i - 1]), lib.text(vs[i]))))
        return out

    def sub_export_history(self, path=None):
        lib = self.doclib()
        if lib is None or not lib.docs:
            messagebox.showinfo("Version history", "No customer documents in the history yet.")
            return None
        if path is None:
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                                initialfile=f"{self.effort.name}_Customer_Document_Versions.xlsx".replace(" ", "_"))
        if not path:
            return None
        DV.export_list(path, lib, compares=self.sub_history_compares())
        diag.activity("submission_exported")
        self.status.configure(text="Version history written.")
        return path
