"""Submission > Deliverables (2.41.0): what we owe the customer and where each stands (deliverables.py).

A list (suggested ones from the customer documents at the bottom, in blue) and a panel for the one picked: status,
owner, format, limit, our file and its page count, what changed it, the customer form it is filled on with every
version (fill the newest; compare), done for this stage, notes."""
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
import diag
import deliverables as D


class DeliverablesMixin:
    def _dl_ctx(self):
        r = self.effrec() if hasattr(self, "effrec") else None
        reg = self.subreg() if hasattr(self, "subreg") else None
        rows = reg.rows(include_hidden=True) if reg is not None else []
        lib = self.doclib() if hasattr(self, "doclib") else None
        vols = self.volumes() if hasattr(self, "volumes") else []
        return r, [x for x in rows if not x.get("hidden")], lib, vols

    def _page_deliverables(self):
        A = dict(height=30, width=10)
        act = self.shell_actions("submission", "deliverables")
        ctk.CTkButton(act, text="Add a deliverable...", command=self.dl_edit_dialog, **A).pack(side="left", padx=3)
        ctk.CTkButton(act, text="Checklist (Excel)...", command=self.dl_export, fg_color="#475569", **A).pack(side="left", padx=3)
        pg = self.shell_page("sub_deliv")
        self._h(pg, "Deliverables", "What we owe the customer, read from the documents and confirmed by the team: format, limit, "
                                    "owner, status, and what changed it. Rules only (No AI).")
        self.dl_chips = ctk.CTkFrame(pg, fg_color="transparent"); self.dl_chips.pack(fill="x", padx=6, pady=(0, 6))
        body = ctk.CTkFrame(pg, fg_color="transparent"); body.pack(fill="both", expand=True, padx=6, pady=6)
        self.dl_detail = ctk.CTkScrollableFrame(body, width=430); self.dl_detail.pack(side="right", fill="y", padx=(10, 0))
        left = tk.Frame(body); left.pack(side="left", fill="both", expand=True)
        cols = (("name", "Deliverable", 190), ("setby", "Set by", 150), ("format", "Format", 140), ("limit", "Limit", 80),
                ("owner", "Owner", 100), ("state", "Status", 190))
        self.dl_tree = tv = ttk.Treeview(left, columns=[c[0] for c in cols], show="headings", selectmode="browse",
                                         style=getattr(self, "tree_style", "Treeview"))
        sc = float(ctk.ScalingTracker.get_widget_scaling(pg)) * getattr(self, "font_size", 13) / 13
        for k, t, w in cols:
            tv.heading(k, text=t); tv.column(k, width=int(w * sc), minwidth=50, anchor="w", stretch=k == "name")
        tv.tag_configure("over", background="#FEE2E2", foreground="#7F1D1D")
        tv.tag_configure("changed", background="#FEF3C7", foreground="#78350F")
        tv.tag_configure("suggested", background="#E0F2FE", foreground="#0C4A6E")
        tv.tag_configure("final", foreground="#15803D")
        sb = ttk.Scrollbar(left, orient="vertical", command=tv.yview); tv.configure(yscrollcommand=sb.set)
        hb = ttk.Scrollbar(left, orient="horizontal", command=tv.xview); tv.configure(xscrollcommand=hb.set)
        sb.pack(side="right", fill="y"); hb.pack(side="bottom", fill="x"); tv.pack(fill="both", expand=True)
        tv.bind("<<TreeviewSelect>>", lambda _e: self._dl_detail())
        tv.bind("<Double-1>", lambda _e: self.dl_edit_dialog(self.dl_selected_id()))
        self.dl_rows = {}

    def dl_refresh(self):
        if not hasattr(self, "dl_tree"):
            return []
        r, rows, lib, vols = self._dl_ctx()
        tv = self.dl_tree
        keep = tv.selection()
        keep_key = self.dl_rows.get(keep[0], ("", ""))[1] if keep else ""
        tv.delete(*tv.get_children())
        self.dl_rows = {}
        for w in self.dl_chips.winfo_children():
            w.destroy()
        if r is None:
            self._dl_detail()
            return []
        for d in D.items(r):
            st = D.state(d, rows, lib, vols, r)
            tag = "over" if st["over"] else "changed" if st["changed"] else "final" if d["status"] in ("Final", "Submitted") else ""
            iid = tv.insert("", "end", values=(d["name"], st["set_by"] or "typed in", d["format"], st["limit"], d["owner"] or "(nobody)",
                                               D.status_text(d, st)), tags=(tag,) if tag else ())
            self.dl_rows[iid] = ("d", d["id"])
        for s in D.suggestions(r, rows):
            iid = tv.insert("", "end", values=(s["subject"], f"{s['doc']}, {s['version']}", "", "", "", "Suggested: add it?"), tags=("suggested",))
            self.dl_rows[iid] = ("s", s["key"])
        sm = D.summary(r, rows, lib, vols)
        for text, fg, bg in ((f"{sm['count']} deliverables", ("#0F172A", "#F1F5F9"), ("#FFFFFF", "#1F2937")),
                             (f"{sm['final']} final", ("#14532D", "#DCFCE7"), ("#DCFCE7", "#14532D")),
                             (f"{sm['over']} over a limit", ("#7F1D1D", "#FEE2E2"), ("#FEE2E2", "#7F1D1D")),
                             (f"{sm['changed']} changed by a customer document", ("#78350F", "#FEF3C7"), ("#FEF3C7", "#78350F")),
                             (f"{sm['noowner']} with no owner", ("#334155", "#E2E8F0"), ("#E2E8F0", "#334155")),
                             (f"{sm['suggested']} suggested, not confirmed", ("#0C4A6E", "#E0F2FE"), ("#E0F2FE", "#0C4A6E"))):
            ctk.CTkLabel(self.dl_chips, text=text, fg_color=bg, text_color=fg, corner_radius=12, padx=10, pady=3).pack(side="left", padx=3)
        want = getattr(self, "_dl_want", None) or keep_key
        self._dl_want = None
        sel = next((i for i, v in self.dl_rows.items() if v[1] == want), None) or (tv.get_children()[0] if tv.get_children() else None)
        if sel:
            tv.selection_set(sel); tv.see(sel)
        self._dl_detail()
        return list(self.dl_rows.values())

    def dl_selected_id(self):
        sel = self.dl_tree.selection() if hasattr(self, "dl_tree") else ()
        v = self.dl_rows.get(sel[0]) if sel else None
        return v[1] if v and v[0] == "d" else None

    def _dl_after(self, key=None):
        self._dl_want = key
        self.dl_refresh()
        self._rec_force() if hasattr(self, "_rec_force") else None

    def _dl_detail(self):
        if not hasattr(self, "dl_detail"):
            return
        P = self.dl_detail
        for w in P.winfo_children():
            w.destroy()
        sel = self.dl_tree.selection()
        v = self.dl_rows.get(sel[0]) if sel else None
        r, rows, lib, vols = self._dl_ctx()
        if v is None or r is None:
            ctk.CTkLabel(P, text="No deliverables yet. Add a deliverable..., or add the ones the customer documents name.",
                         anchor="w", justify="left", wraplength=400).pack(fill="x", padx=8, pady=8)
            return
        B = dict(width=10, height=28)
        if v[0] == "s":
            s = next((x for x in rows if x["key"] == v[1]), None)
            if s is None:
                return
            ctk.CTkLabel(P, text=s["subject"], font=("Segoe UI", 17, "bold"), anchor="w").pack(fill="x", padx=8, pady=(6, 0))
            ctk.CTkLabel(P, text=f"The customer documents name it ({s['doc']}, {s['version']}):", anchor="w", justify="left",
                         wraplength=400, text_color=("#475569", "#94A3B8")).pack(fill="x", padx=8)
            if s.get("sentence"):
                ctk.CTkLabel(P, text=f"“{s['sentence']}”", font=("Georgia", 12, "italic"), anchor="w", justify="left",
                             wraplength=400).pack(fill="x", padx=8, pady=4)
            row = ctk.CTkFrame(P, fg_color="transparent"); row.pack(fill="x", padx=4, pady=6)
            ctk.CTkButton(row, text="Add as a deliverable", fg_color="#0F766E", command=lambda: self.dl_add_suggested(s["key"]), **B).pack(side="left", padx=3)
            ctk.CTkButton(row, text="Not ours", fg_color="#475569", command=lambda: self.dl_dismiss(s["key"]), **B).pack(side="left", padx=3)
            return
        d = D.get(r, v[1])
        st = D.state(d, rows, lib, vols, r)
        ctk.CTkLabel(P, text=d["name"], font=("Segoe UI", 17, "bold"), anchor="w", justify="left", wraplength=400).pack(fill="x", padx=8, pady=(6, 0))
        ctk.CTkLabel(P, text=f"{d['kind']}  |  set by {st['set_by'] or 'the team (typed in)'}", anchor="w", wraplength=400, justify="left",
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=8)
        row = ctk.CTkFrame(P, fg_color="transparent"); row.pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkLabel(row, text="Status").pack(side="left")
        om = ctk.CTkOptionMenu(row, values=list(D.STATUSES), width=150, command=lambda val: (D.update(r, d["id"], status=val), self._dl_after(d["id"])))
        om.set(d["status"]); om.pack(side="left", padx=8)
        lines = [("Owner", d["owner"] or "nobody yet"), ("Format", d["format"] or "-"),
                 ("Limit", (st["limit"] + (f"  ({st['limit_from']})" if st["limit_from"] else "")) if st["limit"] else "-"),
                 ("Our file", os.path.basename(d["file"]) if d.get("file") else "none set")]
        if st["pages"] is not None:
            lines.append(("Pages", f"{st['pages']} (as Word last saved it)"))
        for k, val in lines:
            ln = ctk.CTkFrame(P, fg_color="transparent"); ln.pack(fill="x", padx=8)
            ctk.CTkLabel(ln, text=k, width=70, anchor="w", text_color=("#475569", "#94A3B8")).pack(side="left")
            ctk.CTkLabel(ln, text=val, anchor="w", justify="left", wraplength=320,
                         text_color=("#B91C1C", "#FCA5A5") if k == "Pages" and st["over"] else ("#0F172A", "#F1F5F9")).pack(side="left")
        for c in st["changed"]:
            ctk.CTkLabel(P, text="Changed: " + c, anchor="w", justify="left", wraplength=400, text_color=("#B45309", "#FBBF24")).pack(fill="x", padx=8, pady=(4, 0))
        row = ctk.CTkFrame(P, fg_color="transparent"); row.pack(fill="x", padx=4, pady=(8, 2))
        ctk.CTkButton(row, text="Edit...", command=lambda: self.dl_edit_dialog(d["id"]), **B).pack(side="left", padx=3)
        ctk.CTkButton(row, text="Set our file...", fg_color="#475569", command=lambda: self.dl_set_file(d["id"]), **B).pack(side="left", padx=3)
        if d.get("file"):
            ctk.CTkButton(row, text="Open", fg_color="#475569", command=lambda: self._sub_open(d["file"]), **B).pack(side="left", padx=3)
        row = ctk.CTkFrame(P, fg_color="transparent"); row.pack(fill="x", padx=4, pady=2)
        here = r.stage()["name"]
        ctk.CTkButton(row, text=(f"Not done for {here}" if st["done_here"] else f"Done for {here}"), fg_color="#15803D" if not st["done_here"] else "#475569",
                      command=lambda: (D.mark_stage(r, d["id"], not st["done_here"]), self._dl_after(d["id"])), **B).pack(side="left", padx=3)
        ctk.CTkButton(row, text="Add note...", fg_color="#7C3AED",
                      command=lambda: self.rec_note_dialog(on="deliverable", on_id=d["id"], label=d["name"]), **B).pack(side="left", padx=3)
        # the customer form it is filled on
        ctk.CTkLabel(P, text="CUSTOMER FORM OR TEMPLATE", font=("Segoe UI", 10, "bold"), text_color=("#64748B", "#94A3B8"), anchor="w").pack(fill="x", padx=8, pady=(12, 0))
        f = st["form"]
        if f is None:
            docs = [x for x in (lib.docs if lib else [])]
            if docs:
                fr = ctk.CTkFrame(P, fg_color="transparent"); fr.pack(fill="x", padx=4)
                fom = ctk.CTkOptionMenu(fr, values=[x["name"][:40] for x in docs], width=260); fom.pack(side="left", padx=3)
                ctk.CTkButton(fr, text="Link", command=lambda: self.dl_link_form(d["id"], docs[[x["name"][:40] for x in docs].index(fom.get())]["id"]),
                              **B).pack(side="left", padx=3)
            else:
                ctk.CTkLabel(P, text="Add the customer's form on Documents, then link it here.", anchor="w").pack(fill="x", padx=8)
        else:
            for vid, label, added, sha in reversed(f["versions"]):
                cur = vid == f["latest_id"]
                working = label == f["working"]
                c = ctk.CTkFrame(P, corner_radius=8, border_width=2 if cur else 1, fg_color=("#FFFFFF", "#111827"),
                                 border_color="#0F766E" if cur else ("#E2E8F0", "#334155"))
                c.pack(fill="x", padx=6, pady=2)
                ctk.CTkLabel(c, text=f"{label}, {added}" + ("   CURRENT: FILL THIS" if cur else "   replaced") + ("   (we are on this one)" if working and not cur else ""),
                             anchor="w", font=("Segoe UI", 12, "bold"), text_color=("#0F766E", "#5EEAD4") if cur else ("#64748B", "#94A3B8")).pack(fill="x", padx=10, pady=(4, 0))
                ctk.CTkLabel(c, text=f"Fingerprint {sha[:16].upper()}", anchor="w", font=("Segoe UI", 11), text_color=("#64748B", "#94A3B8")).pack(fill="x", padx=10, pady=(0, 4))
            row = ctk.CTkFrame(P, fg_color="transparent"); row.pack(fill="x", padx=4, pady=4)
            if f["newer"]:
                ctk.CTkButton(row, text="We moved to the newest version", fg_color="#B45309",
                              command=lambda: (D.update(r, d["id"], form_version=f["latest_id"]), self._dl_after(d["id"])), **B).pack(side="left", padx=3)
            if len(f["versions"]) > 1:
                wid = d.get("form_version") if d.get("form_version") != f["latest_id"] else f["versions"][-2][0]
                ctk.CTkButton(row, text="Compare versions", command=lambda: self.sub_compare(d["doc_id"], wid, f["latest_id"]), **B).pack(side="left", padx=3)
        ns = r.notes(on="deliverable", on_id=d["id"])
        if ns:
            ctk.CTkLabel(P, text="NOTES", font=("Segoe UI", 10, "bold"), text_color=("#64748B", "#94A3B8"), anchor="w").pack(fill="x", padx=8, pady=(12, 0))
            for n in ns:
                ctk.CTkLabel(P, text=("Question: " if n["question"] and not n["resolved"] else "") + n["text"], anchor="w", justify="left",
                             wraplength=400).pack(fill="x", padx=8)
        if d.get("notes"):
            ctk.CTkLabel(P, text=d["notes"], anchor="w", justify="left", wraplength=400, text_color=("#475569", "#94A3B8")).pack(fill="x", padx=8, pady=(6, 0))
        ctk.CTkButton(P, text="Remove this deliverable", fg_color="#B91C1C", command=lambda: self.dl_remove(d["id"]), **B).pack(anchor="w", padx=8, pady=12)

    # ------------------------------------------------------------ actions
    def dl_add_suggested(self, key):
        r, rows, lib, vols = self._dl_ctx()
        s = next((x for x in rows if x["key"] == key), None)
        if r is None or s is None:
            return None
        kind = D.kind_of(s["subject"])
        did = D.add(r, s["subject"], kind=kind, req_key=key, fmt=D.default_format(kind, rows))
        diag.activity("deliverable_added")
        self._dl_after(did)
        return did

    def dl_dismiss(self, key):
        r, rows, _lib, _v = self._dl_ctx()
        s = next((x for x in rows if x["key"] == key), None)
        D.dismiss(r, key, s["subject"] if s else "")
        diag.activity("deliverable_dismissed")
        self._dl_after()
        return True

    def dl_remove(self, did):
        r = self.effrec()
        if r and messagebox.askyesno("Remove deliverable", "Remove this deliverable from the list? The timeline keeps a record."):
            D.remove(r, did)
            self._dl_after()
            return True
        return False

    def dl_link_form(self, did, doc_id):
        r, _rows, lib, _v = self._dl_ctx()
        doc = lib.doc(doc_id) if lib else None
        if r is None or doc is None:
            return False
        D.update(r, did, doc_id=doc_id, form_version=doc["versions"][-1]["id"])
        self._dl_after(did)
        return True

    def dl_set_file(self, did, path=None):
        r = self.effrec()
        if r is None:
            return False
        if path is None:
            info = (self.efforts.get(self.effort.name) or {}) if self.effort else {}
            path = filedialog.askopenfilename(title="Our working file for this deliverable", initialdir=info.get("volumes_dir") or None)
            if not path:
                return False
        D.update(r, did, file=os.path.abspath(path))
        self._dl_after(did)
        return True

    def dl_edit_dialog(self, did=None, values=None):
        """Add or edit a deliverable: name, kind, format, limit, owner, notes. values (tests): save at once."""
        r, rows, _lib, _v = self._dl_ctx()
        if r is None:
            messagebox.showinfo("Deliverable", "Open an effort first.")
            return None
        d = D.get(r, did) if did else None

        def save(v):
            if d is None:
                kind = v.get("kind") or D.kind_of(v.get("name", ""))
                new = D.add(r, v.get("name", ""), kind=kind, fmt=v.get("format") or D.default_format(kind, rows), limit=v.get("limit", ""),
                            owner=v.get("owner", ""), notes=v.get("notes", ""))
                res = new
            else:
                D.update(r, d["id"], **{k: v[k] for k in ("name", "kind", "format", "limit", "owner", "notes") if k in v})
                res = d["id"]
            diag.activity("deliverable_saved")
            self._dl_after(res)
            return res

        if values is not None:
            return save(values)
        w = ctk.CTkToplevel(self); w.title("Deliverable" if d else "New deliverable"); w.transient(self); w.geometry("640x480")
        ents = {}
        people = self.rec_people() if hasattr(self, "rec_people") else []
        for i, (k, lab, hint) in enumerate((("name", "Deliverable", "Volume II Management"), ("format", "Format", "Word, sent as searchable PDF"),
                                             ("limit", "Limit and rules (empty: from the requirements)", "15 pages"),
                                             ("owner", "Owner", ", ".join(people[:3]) or "a name"))):
            ctk.CTkLabel(w, text=lab, anchor="w").grid(row=i, column=0, sticky="w", padx=14, pady=(12 if i == 0 else 4, 0))
            e = ctk.CTkEntry(w, width=360, placeholder_text=hint)
            if d:
                e.insert(0, d[k])
            e.grid(row=i, column=1, sticky="w", padx=8, pady=(12 if i == 0 else 4, 0))
            ents[k] = e
        ctk.CTkLabel(w, text="Kind", anchor="w").grid(row=4, column=0, sticky="w", padx=14, pady=4)
        ko = ctk.CTkOptionMenu(w, values=list(D.KINDS), width=200); ko.set(d["kind"] if d else "Volume")
        ko.grid(row=4, column=1, sticky="w", padx=8, pady=4)
        ctk.CTkLabel(w, text="Notes", anchor="w").grid(row=5, column=0, sticky="nw", padx=14, pady=4)
        nb = ctk.CTkTextbox(w, width=360, height=100); nb.grid(row=5, column=1, sticky="w", padx=8, pady=4)
        if d:
            nb.insert("1.0", d["notes"])

        def ok():
            if save({**{k: e.get() for k, e in ents.items()}, "kind": ko.get(), "notes": nb.get("1.0", "end")}):
                w.destroy()
        ctk.CTkButton(w, text="Save", command=ok, fg_color="#1E3A8A").grid(row=6, column=1, sticky="e", padx=14, pady=12)
        w._api = {"entries": ents, "kind": ko, "notes": nb, "ok": ok}
        w.after(100, w.lift)
        return w

    def dl_export(self, path=None):
        r, rows, lib, vols = self._dl_ctx()
        if r is None:
            return None
        if path is None:
            path = filedialog.asksaveasfilename(parent=self, defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                                initialfile=f"{self.effort.name}_Deliverables.xlsx".replace(" ", "_"))
            if not path:
                return None
        D.export_excel(path, r, rows, lib, vols, self.effort.name)
        diag.activity("deliverables_exported")
        self.status.configure(text="Deliverables checklist written.")
        return path
