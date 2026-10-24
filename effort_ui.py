"""Effort List inside the app (2.4.0): Effort menu, setup window, Add to effort list, status and approvers,
and the scan step that marks every term already in the effort's list.

Definition order when an effort is open: Effort List (approved) > customer documents > client lists > database.
"""
import datetime, os, re
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import customtkinter as ctk
import diag
import effort as E

EFFORT_MARK = "📋"


def _eng():
    import app_gui
    return app_gui


class EffortMixin:
    """Mixed into AcronymAppGUI."""

    # ------------------------------------------------------------ setup
    def effort_init(self, toolbar, button_kw):
        eng = _eng()
        self.efforts = E.Registry(os.path.join(eng.CONFIG_DIR, "efforts.json"))
        self.effort = None
        self.btn_effort = ctk.CTkButton(toolbar, text="Effort ▾", command=self.show_effort_menu, fg_color="#0F766E", width=96, **button_kw)
        self.btn_effort.pack(side="left", padx=4, pady=8)
        self.effort_menu = tk.Menu(self, tearoff=0)
        self.lbl_effort = ctk.CTkLabel(self, text="", font=("Arial", 12), text_color=("#0F766E", "#5EEAD4"))
        if self.efforts.current:
            self.after(300, lambda: self.open_effort(self.efforts.current, quiet=True))

    def effort_actionbar(self, act):
        self.btn_effort_add = ctk.CTkButton(act, text=f"{EFFORT_MARK} Add to effort list", command=self.add_to_effort, state="disabled",
                                            fg_color="#0F766E", width=150)
        self.btn_effort_add.pack(side="left", padx=5, pady=12)

    def update_effort_ui(self):
        L = self.effort
        if L is None:
            self.lbl_effort.pack_forget()
            self.btn_effort.configure(text="Effort ▾")
        else:
            counts = {s: 0 for s in E.STATUSES}
            for r in L.rows.values():
                counts[r["Status"]] = counts.get(r["Status"], 0) + 1
            bits = [f"Effort: {L.name}", os.path.basename(L.path), f"{len(L.rows)} terms",
                    f"{counts['Approved']} approved, {counts['Needs author']} need an author, {counts['Proposed']} proposed",
                    "first use " + ("per volume" if L.first_use == "volume" else "across the submission")]
            if L.pending:
                bits.append("NOT SAVED (close the list in Excel, then Effort > Save list now)")
            self.lbl_effort.configure(text="  |  ".join(bits))
            self.lbl_effort.pack(pady=(0, 2), before=self.status)
            self.btn_effort.configure(text=f"{L.name[:12]} ▾")
        self.update_effort_buttons()

    def update_effort_buttons(self):
        sel = [t for t in self.tree.selection() if t in self.results] if hasattr(self, "tree") else []
        ok = self.effort is not None and bool(sel)
        self.btn_effort_add.configure(state="normal" if ok else "disabled",
                                      text=f"{EFFORT_MARK} Add {len(sel)} to effort list" if ok and len(sel) > 1 else f"{EFFORT_MARK} Add to effort list")

    # ------------------------------------------------------------ menu
    def show_effort_menu(self):
        diag.activity("effort_menu_opened")
        m = self.effort_menu
        m.delete(0, "end")
        m.add_command(label="New effort...", command=self.new_effort_dialog)
        m.add_command(label="Open an existing effort list...", command=self.open_effort_file)
        names = [n for n in self.efforts.names() if not self.effort or n != self.effort.name]
        if names:
            sub = tk.Menu(m, tearoff=0)
            for n in names[:20]:
                sub.add_command(label=n, command=lambda n=n: self.open_effort(n))
            m.add_cascade(label="Switch to", menu=sub)
        has = self.effort is not None
        st = "normal" if has else "disabled"
        m.add_separator()
        m.add_command(label="Open the list in Excel", command=self.open_effort_in_excel, state=st)
        m.add_command(label="Reload the list (after editing in Excel)", command=self.reload_effort, state=st)
        m.add_command(label="Save list now", command=self.save_effort, state="normal" if has and self.effort.pending else "disabled")
        m.add_command(label="Export for approvals (Needs author, Conflicts, Approved)...", command=self.export_effort, state=st)
        m.add_command(label="Effort settings...", command=lambda: self.new_effort_dialog(edit=True), state=st)
        m.add_separator()
        m.add_command(label="Close effort", command=self.close_effort, state=st)
        m.tk_popup(self.btn_effort.winfo_rootx(), self.btn_effort.winfo_rooty() + self.btn_effort.winfo_height())

    def new_effort_dialog(self, edit=False):
        if edit:
            diag.activity("effort_settings_opened")
        else:
            diag.activity("effort_new_opened")
        cur = self.efforts.get(self.effort.name) if edit and self.effort else {}
        win = ctk.CTkToplevel(self); win.title("Effort settings" if edit else "New effort")
        win.geometry("640x430"); win.transient(self); win.after(150, win.lift); win.grab_set()
        diag.register(win, "effort_setup")
        f = ctk.CTkFrame(win, fg_color="transparent"); f.pack(fill="both", expand=True, padx=16, pady=12)
        f.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(f, text="One list per proposal. It keeps every term found, chosen and approved for this effort.",
                     wraplength=600, justify="left").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 10))
        ctk.CTkLabel(f, text="Effort name").grid(row=1, column=0, sticky="w", pady=4)
        e_name = ctk.CTkEntry(f); e_name.grid(row=1, column=1, columnspan=2, sticky="ew", pady=4)
        ctk.CTkLabel(f, text="List file").grid(row=2, column=0, sticky="w", pady=4)
        e_path = ctk.CTkEntry(f); e_path.grid(row=2, column=1, sticky="ew", pady=4)
        def browse_list():
            p = filedialog.asksaveasfilename(parent=win, title="Where should the effort list live?", defaultextension=".xlsx",
                                             initialfile=os.path.basename(e_path.get()) or "Effort_List.xlsx",
                                             initialdir=os.path.dirname(e_path.get()) or None, filetypes=[("Excel", "*.xlsx")],
                                             confirmoverwrite=False)
            if p:
                e_path.delete(0, "end"); e_path.insert(0, p)
        ctk.CTkButton(f, text="Browse...", width=90, command=browse_list).grid(row=2, column=2, padx=(6, 0))
        ctk.CTkLabel(f, text="Tip: a OneDrive-synced SharePoint folder lets the team see the same list.",
                     text_color=("#475569", "#94A3B8")).grid(row=3, column=1, columnspan=2, sticky="w")
        ctk.CTkLabel(f, text="First use").grid(row=4, column=0, sticky="w", pady=(10, 4))
        rule = tk.StringVar(value=(cur or {}).get("first_use", "volume"))
        rf = ctk.CTkFrame(f, fg_color="transparent"); rf.grid(row=4, column=1, columnspan=2, sticky="w", pady=(10, 4))
        ctk.CTkRadioButton(rf, text="Restarts in each volume", variable=rule, value="volume").pack(side="left")
        ctk.CTkRadioButton(rf, text="Runs across the whole submission", variable=rule, value="submission").pack(side="left", padx=12)
        dirs = {}
        for r, (key, label) in enumerate((("customer_dir", "Customer documents folder"), ("volumes_dir", "Volumes folder")), start=5):
            ctk.CTkLabel(f, text=label).grid(row=r, column=0, sticky="w", pady=4)
            e = ctk.CTkEntry(f, placeholder_text="optional"); e.grid(row=r, column=1, sticky="ew", pady=4)
            def pick(e=e):
                d = filedialog.askdirectory(parent=win)
                if d:
                    e.delete(0, "end"); e.insert(0, d)
            ctk.CTkButton(f, text="Browse...", width=90, command=pick).grid(row=r, column=2, padx=(6, 0))
            dirs[key] = e
        msg = ctk.CTkLabel(f, text="", text_color="#B91C1C"); msg.grid(row=8, column=0, columnspan=3, sticky="w", pady=6)
        if edit and self.effort:
            e_name.insert(0, self.effort.name); e_name.configure(state="disabled")
            e_path.insert(0, self.effort.path)
            for k, e in dirs.items():
                if cur.get(k):
                    e.insert(0, cur[k])
        else:
            desk = os.path.join(os.path.expanduser("~"), "Desktop")
            e_path.insert(0, os.path.join(desk if os.path.isdir(desk) else os.path.expanduser("~"), "Effort_List.xlsx"))
            def name_changed(*_):
                n = re.sub(r"[^A-Za-z0-9 _.-]+", "", e_name.get()).strip().replace(" ", "_")
                d = os.path.dirname(e_path.get())
                if n and os.path.basename(e_path.get()).endswith("Effort_List.xlsx"):
                    e_path.delete(0, "end"); e_path.insert(0, os.path.join(d, f"{n}_Effort_List.xlsx"))
            e_name.bind("<KeyRelease>", name_changed)

        def ok():
            name = e_name.get().strip()
            path = e_path.get().strip()
            if not name or not path.lower().endswith(".xlsx"):
                msg.configure(text="Give the effort a name and an .xlsx file for its list."); return
            if not edit and name in self.efforts.names():
                msg.configure(text="An effort with that name already exists. Pick it under Switch to."); return
            try:
                if edit and self.effort and os.path.abspath(path) != os.path.abspath(self.effort.path):
                    self.effort.path = path            # move: write the current list to the new place
                    self.effort.first_use = rule.get()
                    self._save_effort_list()
                L = E.EffortList(path, name, rule.get()).load()
                L.name, L.first_use = name, rule.get()
                if not os.path.isfile(path) or edit:
                    L.pending = True
                    self.effort = L
                    if not self._save_effort_list():
                        return
            except Exception as ex:
                diag.swallowed()
                msg.configure(text=f"Could not create the list: {type(ex).__name__}"); return
            self.efforts.put(name, path=path, first_use=rule.get(), **{k: e.get().strip() for k, e in dirs.items()})
            win.destroy()
            self.open_effort(name)
        b = ctk.CTkFrame(win, fg_color="transparent"); b.pack(fill="x", padx=16, pady=(0, 14))
        ctk.CTkButton(b, text="Save" if edit else "Create effort", command=ok).pack(side="left")
        ctk.CTkButton(b, text="Cancel", fg_color="#475569", command=win.destroy).pack(side="right")
        e_name.focus_set()
        win._api = {"name": e_name, "path": e_path, "rule": rule, "dirs": dirs, "ok": ok, "msg": msg}
        return win

    def open_effort_file(self):
        p = filedialog.askopenfilename(title="Open an effort list", filetypes=[("Excel", "*.xlsx")])
        if not p:
            return
        L = E.EffortList(p).load()
        name = L.name
        while name in self.efforts.names() and os.path.abspath(self.efforts.get(name).get("path", "")) != os.path.abspath(p):
            name += " (2)"
        self.efforts.put(name, path=p, first_use=L.first_use)
        self.open_effort(name)

    def open_effort(self, name, quiet=False):
        info = self.efforts.get(name)
        if not info:
            return
        try:
            L = E.EffortList(info["path"], name, info.get("first_use", "volume")).load()
        except Exception as ex:
            diag.swallowed()
            if not quiet:
                messagebox.showerror("Effort list", f"The list could not be read ({type(ex).__name__}).\n{info['path']}")
            return
        self.effort = L
        self.efforts.current = name
        diag.activity("effort_opened", terms=len(L.rows))
        self.apply_effort()
        self.update_effort_ui()

    def close_effort(self):
        if self.effort and self.effort.pending and not messagebox.askyesno(
                "Close effort", "The list has changes that are not saved yet (Excel had it open). Close anyway and lose them?"):
            return
        self.effort = None
        self.efforts.current = ""
        diag.activity("effort_closed")
        self.apply_effort()
        self.update_effort_ui()

    def reload_effort(self):
        if self.effort is None:
            return
        if self.effort.pending and not messagebox.askyesno("Reload", "Unsaved changes in the app will be lost. Reload from the file?"):
            return
        self.open_effort(self.effort.name)

    def open_effort_in_excel(self):
        if self.effort is None:
            return
        diag.activity("effort_opened_in_excel")
        if not os.path.isfile(self.effort.path):
            self._save_effort_list()
        try:
            os.startfile(self.effort.path)          # Windows: opens in Excel
        except AttributeError:
            messagebox.showinfo("Effort list", self.effort.path)

    def export_effort(self):
        if self.effort is None:
            return
        default = f"{re.sub(r'[^A-Za-z0-9_-]+', '_', self.effort.name)}_Approvals_{datetime.date.today().isoformat()}.xlsx"
        p = filedialog.asksaveasfilename(title="Export for approvals", defaultextension=".xlsx", initialfile=default,
                                         initialdir=os.path.dirname(self.effort.path), filetypes=[("Excel", "*.xlsx")])
        if not p:
            return
        counts = self.effort.export_views(p)
        diag.activity("effort_exported", rows=counts.get("All", 0))
        messagebox.showinfo("Exported", "Saved with these sheets:\n" + "\n".join(f"{k}: {v}" for k, v in counts.items()))

    # ------------------------------------------------------------ saving
    def _save_effort_list(self):
        """Save, asking to close Excel when it holds the file. False = still not saved (kept pending)."""
        L = self.effort
        while True:
            try:
                L.save()
                return True
            except E.ListLocked:
                if not messagebox.askretrycancel("Effort list is open",
                                                 "The effort list is open in Excel, so it cannot be saved.\n\n"
                                                 "Close it in Excel, then click Retry. Cancel keeps the change in the app "
                                                 "until you save (Effort > Save list now)."):
                    return False
            except OSError as ex:
                diag.swallowed()
                messagebox.showerror("Effort list", f"Could not save the list ({type(ex).__name__}). The change is kept in the app.")
                return False

    def save_effort(self):
        if self.effort is not None:
            self._save_effort_list()
            self.update_effort_ui()

    # ------------------------------------------------------------ adding and approving
    def _definition_for(self, d):
        sd = (d.get("selected_definition") or "").strip()
        if not sd or sd.startswith(("[", "⚠", "MULTIPLE", "Rescan")):
            return ""
        return sd

    def _source_for(self, d, definition):
        if d.get("custdef_source") and definition in d.get("customer_definitions", []):
            return "Customer document"
        if d.get("client") and definition in d.get("client_definitions", []):
            return "Client list"
        if d.get("in_db") and definition:
            return "Database"
        if d.get("manual"):
            return "Added manually"
        return "Author" if definition else ""

    def add_to_effort(self, terms=None):
        if self.effort is None:
            return
        eng = _eng()
        terms = [t for t in (terms or self.tree.selection()) if t in self.results]
        if not terms:
            return
        typed = ""
        if len(terms) == 1:                      # a definition typed in the bottom box goes into the list
            try:
                typed = self.entry_def.get().strip() if str(self.entry_def.cget("state")) == "normal" else ""
            except Exception:
                diag.swallowed()
        added = updated = 0
        for t in terms:
            d = self.results[t]
            if d.get("file_error"):
                continue
            definition = typed or self._definition_for(d)
            cust = next((h for h in d.get("custdef_all", []) if h["definition"] == definition), None) or {}
            fields = dict(Type=eng.base_type(d.get("category", "")), Source=self._source_for(d, definition),
                          **{"First use": "; ".join(eng.first_use_lines(d))[:400]})
            if definition:
                fields["Definition"] = definition
            if cust and definition in d.get("customer_definitions", []):
                fields["Customer document"] = cust.get("where", "")
                fields["Customer wording"] = cust.get("sentence", "")[:500]
            others = [x for x in d.get("customer_definitions", []) + d.get("definitions", []) if x and x != definition]
            if others:
                fields["Other definitions"] = " | ".join(dict.fromkeys(others))[:500]
            r = self.effort.add_or_update(t, **fields)
            added += r == "added"; updated += r == "updated"
        if typed:
            self.entry_def.delete(0, "end")      # used once; never carried over to the next term
        diag.activity("effort_add", added=added, n=updated)
        self._save_effort_list()
        self.apply_effort()
        self.update_effort_ui()
        self.status.configure(text=f"Effort list: {added} added, {updated} updated." + ("" if not self.effort.pending else " NOT SAVED yet: close the list in Excel."))

    def set_effort_status(self, status, terms=None):
        if self.effort is None:
            return
        terms = [t for t in (terms or self.tree.selection()) if t in self.results]
        missing = [t for t in terms if t not in self.effort.rows]
        if missing:
            self.add_to_effort(missing)
        approver = None
        if status == "Approved":
            last = getattr(self, "_last_approver", "")
            approver = simpledialog.askstring("Approve", "SS Approver (one name, or several separated by ;):", initialvalue=last, parent=self)
            if approver is None:
                return
            approver = approver.strip()
            self._last_approver = approver
        n = self.effort.set_status(terms, status, approver=approver or None)
        if status == "Approved":
            diag.activity("effort_approved", n=n)
        elif status == "Rejected":
            diag.activity("effort_rejected", n=n)
        elif status == "Needs author":
            diag.activity("effort_needs_author", n=n)
        else:
            diag.activity("effort_proposed", n=n)
        self._save_effort_list()
        self.apply_effort()
        self.update_effort_ui()

    def remove_from_effort(self, terms=None):
        if self.effort is None:
            return
        terms = [t for t in (terms or self.tree.selection()) if t in self.effort.rows]
        for t in terms:
            self.effort.remove(t)
        diag.activity("effort_remove", n=len(terms))
        self._save_effort_list()
        self.apply_effort()
        self.update_effort_ui()

    def effort_context_menu(self, menu, iid):
        """Entries for the results table's right-click menu."""
        if self.effort is None:
            menu.add_command(label="Effort list (open or create an effort first)", state="disabled")
            return
        sel = [t for t in self.tree.selection() if t in self.results] or [iid]
        n = len(sel)
        sub = tk.Menu(menu, tearoff=0)
        sub.add_command(label=f"Add to effort list ({n})", command=lambda: self.add_to_effort(sel))
        sub.add_command(label=f"Approve... ({n})", command=lambda: self.set_effort_status("Approved", sel))
        sub.add_command(label=f"Needs an author ({n})", command=lambda: self.set_effort_status("Needs author", sel))
        sub.add_command(label=f"Not a term in this effort ({n})", command=lambda: self.set_effort_status("Rejected", sel))
        sub.add_command(label=f"Back to Proposed ({n})", command=lambda: self.set_effort_status("Proposed", sel))
        sub.add_separator()
        sub.add_command(label=f"Remove from effort list ({n})", command=lambda: self.remove_from_effort(sel))
        menu.add_cascade(label=f"{EFFORT_MARK} Effort list", menu=sub)

    # ------------------------------------------------------------ customer documents (2.5.0)
    def customer_files(self):
        """Files in the effort's customer documents folder (Word, PowerPoint, Excel, PDF)."""
        if self.effort is None:
            return []
        info = self.efforts.get(self.effort.name) or {}
        d = info.get("customer_dir") or ""
        if not d or not os.path.isdir(d):
            return []
        out = []
        for root, _dirs, fs in os.walk(d):
            for f in fs:
                if not f.startswith("~$") and os.path.splitext(f)[1].lower() in (".docx", ".pptx", ".xlsx", ".pdf"):
                    out.append(os.path.join(root, f))
        return sorted(out)

    def customer_definitions(self):
        """{term: [definition hits]} from the customer documents, cached per file until the file changes."""
        import custdefs
        eng = _eng()
        cache = getattr(self, "_custdef_cache", {})
        self._custdef_cache = cache
        merged = {}
        for path in self.customer_files():
            try:
                st = os.stat(path)
                key = (path, st.st_size, st.st_mtime)
                if key not in cache:
                    cache[key] = custdefs.extract(eng.typed_chunks(path) + custdefs.table_chunks(path))
                for term, hits in cache[key].items():
                    lst = merged.setdefault(term, [])
                    for h in hits:
                        if not any(x["definition"].lower() == h["definition"].lower() for x in lst):
                            lst.append(h)
            except Exception:
                diag.swallowed()
        return merged

    def apply_customer_defs(self):
        """The customer's own definition outranks the database. Several different ones: the user chooses."""
        import custdefs
        eng = _eng()
        defs = self.customer_definitions() if self.effort is not None else {}
        n = custdefs.merge_into(self.results, defs, folded=lambda t: eng.fold(t).strip())
        diag.activity("customer_definitions_applied", terms=n, files=len(self.customer_files()) if defs else 0)
        for term, d in self.results.items():
            cdefs = d.get("customer_definitions")
            if not cdefs or d.get("excluded") or d.get("file_error"):
                continue
            db = [x for x in d.get("definitions", []) if x not in cdefs]
            d["db_or_client_definitions"] = db
            d["definitions"] = list(cdefs) + db
            d["cust_db_differ"] = bool(db)
            if len(cdefs) == 1:
                d["selected_definition"] = cdefs[0]
                d["status"] = "📄 Customer document" + (" (database differs)" if db else "")
            else:
                d["selected_definition"] = "MULTIPLE: " + " | ".join(cdefs)
                d["status"] = f"⚠️ CUSTOMER DOCS DIFFER ({len(cdefs)})"
        return n

    # ------------------------------------------------------------ the scan step
    def apply_effort(self, reload=False):
        """Mark results with the effort list: approved definitions win; rejected terms are hidden for this effort."""
        if reload and self.effort is not None and not self.effort.pending:
            try:
                self.effort.load()
            except Exception:
                diag.swallowed()
        L = self.effort
        for term, d in self.results.items():
            pre = d.get("_pre_effort")
            row = L.rows.get(term) if L is not None else None
            if row is None:
                if pre:                                     # left the list, or the effort was closed: restore
                    d["status"], d["selected_definition"], d["excluded"] = pre
                    d.pop("_pre_effort", None); d.pop("effort", None)
                continue
            if not pre:
                d["_pre_effort"] = (d.get("status", ""), d.get("selected_definition", ""), d.get("excluded", False))
                pre = d["_pre_effort"]
            st = row["Status"]
            d["effort"] = st
            d["excluded"] = pre[2] or st == "Rejected"
            if st == "Rejected":
                d["status"] = "🚫 Not a term in this effort"
                d["selected_definition"] = pre[1]
            else:
                d["status"] = f"{EFFORT_MARK} {st} (effort list)"
                d["selected_definition"] = row["Definition"] or pre[1]
        if hasattr(self, "tree"):
            self.populate_table()
