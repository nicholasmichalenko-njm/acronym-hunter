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
import volcheck as V

EFFORT_MARK = ""   # no emoji in the interface (2.7.0)


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
        self.btn_effort = ctk.CTkButton(toolbar, text="Effort", command=self.show_effort_menu, **button_kw)
        self.btn_effort.pack(fill="x", padx=8, pady=2)
        self.btn_volcheck = ctk.CTkButton(toolbar, text="QA/QC Deliverables...", command=self.check_volumes, state="disabled", **button_kw)
        self.btn_volcheck.pack(fill="x", padx=8, pady=2)
        self.effort_menu = tk.Menu(self, tearoff=0)
        self.lbl_effort = ctk.CTkLabel(getattr(self, "main", self), text="", font=("Arial", 12), text_color=("#0F766E", "#5EEAD4"))
        # 2.11.0: the last effort is resumed by workspace_startup once the window is built

    def effort_actionbar(self, act):
        """Keep, Not a term and Omit sit on their own row under the action bar while an effort is open (2.14.0)."""
        self.act_effort = row = ctk.CTkFrame(act.master, fg_color="transparent")
        self._act_main = act
        ctk.CTkLabel(row, text="Effort decision:", anchor="w").pack(side="left", padx=(5, 4), pady=(0, 8))
        self.btn_effort_add = ctk.CTkButton(row, text="Add to effort list", command=self.add_to_effort, state="disabled",
                                            fg_color="#0F766E", width=150)
        self.btn_effort_add.pack(side="left", padx=5, pady=(0, 8))
        self.btn_effort_rej = ctk.CTkButton(row, text="Not a term", command=lambda: self.set_effort_status("Rejected"),
                                            state="disabled", fg_color="#B91C1C", width=100)
        self.btn_effort_rej.pack(side="left", padx=5, pady=(0, 8))
        self.btn_effort_omit = ctk.CTkButton(row, text="Omit...", command=self.mark_known, state="disabled", fg_color="#6B21A8", width=80)
        self.btn_effort_omit.pack(side="left", padx=5, pady=(0, 8))

    def update_effort_ui(self):
        L = self.effort
        if L is None:
            self.lbl_effort.pack_forget()
            self.btn_effort.configure(text="Effort")
            self.btn_volcheck.configure(state="disabled")
        else:
            counts = {s: 0 for s in E.STATUSES}
            for r in L.rows.values():
                counts[r["Status"]] = counts.get(r["Status"], 0) + 1
            bits = [f"Effort: {L.name}", os.path.basename(L.path), f"{len(L.rows)} terms",
                    f"{counts['Approved']} approved, {counts['Needs author']} need an author, {counts['Proposed']} proposed",
                    "first use " + V.RULE_SHORT.get(L.first_use, "per volume")]
            if L.client or L.solicitation:
                bits.insert(1, " ".join(x for x in (L.client, L.solicitation) if x))
            rec = getattr(self, "_last_effort_scan", None)
            if rec:
                bits.append(f"last scan: {rec['new']} new, {rec['gone']} no longer found")
            if L.pending:
                bits.append("NOT SAVED (close the list in Excel, then Effort > Save list now)")
            self.lbl_effort.configure(text="  |  ".join(bits))
            self.lbl_effort.pack(pady=(0, 2), before=self.status)
            self.btn_effort.configure(text=f"Effort: {L.name[:18]}")
            self.btn_volcheck.configure(state="normal")
        self.update_effort_buttons()
        if hasattr(self, "home_update"):
            self.home_update()

    def update_effort_buttons(self):
        sel = [t for t in self.tree.selection() if t in self.results] if hasattr(self, "tree") else []
        ok = self.effort is not None and bool(sel)
        self.btn_effort_add.configure(state="normal" if ok else "disabled",
                                      text=f"Add {len(sel)} to effort list" if ok and len(sel) > 1 else "Add to effort list")
        if hasattr(self, "btn_effort_omit"):
            if self.effort is None:                  # the effort decision row belongs to an effort's Scan review
                self.act_effort.pack_forget()
            elif not self.act_effort.winfo_manager():
                self.act_effort.pack(fill="x", after=self._act_main)
            can = bool(sel) and all(not self.results[t].get("file_error") and not self.results[t].get("manual") for t in sel)
            self.btn_effort_omit.configure(state="normal" if can else "disabled")
            self.btn_effort_rej.configure(state="normal" if ok else "disabled")

    # ------------------------------------------------------------ menu
    def show_effort_menu(self, menu=None):
        diag.activity("effort_menu_opened")
        m = menu or self.effort_menu
        m.delete(0, "end")
        m.add_command(label="Start a new effort...", command=self.open_wizard)
        m.add_command(label="Open an existing effort list...", command=self.open_effort_file)
        names = [n for n in self.efforts.names() if (not self.effort or n != self.effort.name)
                 and not (self.efforts.get(n) or {}).get("archived")]
        if names:
            sub = tk.Menu(m, tearoff=0)
            for n in names:
                sub.add_command(label=n, command=lambda n=n: self.open_effort(n))
            m.add_cascade(label="Switch to", menu=sub)
        arch = [n for n in self.efforts.names() if (self.efforts.get(n) or {}).get("archived")]
        if arch:
            sub2 = tk.Menu(m, tearoff=0)
            for n in arch:
                sub2.add_command(label=f"Reopen {n}", command=lambda n=n: self.unarchive_effort(n))
            m.add_cascade(label="Archived efforts", menu=sub2)
        has = self.effort is not None
        st = "normal" if has else "disabled"
        m.add_separator()
        m.add_command(label="Add customer documents...", command=self.add_customer_documents, state=st)
        m.add_command(label="Review new terms (not in the list)...", command=self.review_new_terms, state=st)
        m.add_command(label="Activity (what was added, from where)...", command=self.show_activity, state=st)
        m.add_command(label="Go to the effort list (home)", command=lambda: self.show_view("Effort list (home)"), state=st)
        m.add_command(label="Export terms (choose columns and volumes)...", command=self.export_picker, state=st)
        m.add_command(label="Keywords (for SharePoint tags)", command=lambda: self.show_view("Keywords"), state=st)
        m.add_command(label="Suggest keywords...", command=self.kw_suggest_dialog, state=st)
        m.add_command(label="Attach offerings...", command=self.attach_offerings_dialog, state=st)
        m.add_command(label="Offerings catalog...", command=self.offerings_window)
        m.add_command(label="Export the acronym lists as set in the wizard (Word and Excel)...", command=self.export_effort_lists_ui, state=st)
        m.add_command(label="Name volumes...", command=self.edit_volumes, state=st)
        m.add_command(label="Import a volume's acronym list...", command=self.import_volume_list, state=st)
        m.add_command(label="Export all efforts in one workbook...", command=self.export_all_efforts_ui)
        m.add_separator()
        m.add_command(label="Open the list in Excel", command=self.open_effort_in_excel, state=st)
        m.add_command(label="Reload the list (after editing in Excel)", command=self.reload_effort, state=st)
        m.add_command(label="Save list now", command=self.save_effort, state="normal" if has and self.effort.pending else "disabled")
        m.add_command(label="Export for approvals (Needs author, Conflicts, Approved)...", command=self.export_effort, state=st)
        m.add_command(label="Add this effort to the Acronyms, Abbreviations, Units and Symbols Master Database...",
                      command=self.master_add_effort, state=st)
        m.add_separator()
        m.add_command(label="QA/QC: check our Word deliverables (first use, missing, acronym lists)...", command=self.check_volumes,
                      state=st)
        m.add_command(label="Show QA/QC", command=self.open_qa, state=st)
        m.add_command(label="Effort settings...", command=lambda: self.new_effort_dialog(edit=True), state=st)
        m.add_command(label="Restore an earlier version...", command=self.restore_dialog)
        m.add_separator()
        m.add_command(label="Archive this effort...", command=self.archive_effort, state=st)
        m.add_command(label="Close effort", command=self.close_effort, state=st)
        if menu is None:
            m.tk_popup(self.btn_effort.winfo_rootx() + self.btn_effort.winfo_width(), self.btn_effort.winfo_rooty())

    def new_effort_dialog(self, edit=False):
        if edit:
            diag.activity("effort_settings_opened")
        else:
            diag.activity("effort_new_opened")
        cur = self.efforts.get(self.effort.name) if edit and self.effort else {}
        win = ctk.CTkToplevel(self); win.title("Effort settings" if edit else "New effort")
        win.geometry("640x620"); win.transient(self); win.after(150, win.lift); win.grab_set()
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
        for k, lab in E.FIRST_USE_RULES.items():
            ctk.CTkRadioButton(rf, text=lab, variable=rule, value=k).pack(anchor="w", pady=1)
        dirs = {}
        for r, (key, label) in enumerate((("client", "Client (short name)"), ("solicitation", "Solicitation number"),
                                          ("internal_no", "Internal number")), start=9):
            ctk.CTkLabel(f, text=label).grid(row=r, column=0, sticky="w", pady=4)
            e = ctk.CTkEntry(f); e.grid(row=r, column=1, columnspan=2, sticky="ew", pady=4)
            dirs[key] = e
        for r, (key, label) in enumerate((("customer_dir", "Customer documents folder"), ("volumes_dir", "Volumes folder")), start=5):
            ctk.CTkLabel(f, text=label).grid(row=r, column=0, sticky="w", pady=4)
            e = ctk.CTkEntry(f, placeholder_text="optional"); e.grid(row=r, column=1, sticky="ew", pady=4)
            def pick(e=e):
                d = filedialog.askdirectory(parent=win)
                if d:
                    e.delete(0, "end"); e.insert(0, d)
            ctk.CTkButton(f, text="Browse...", width=90, command=pick).grid(row=r, column=2, padx=(6, 0))
            dirs[key] = e
        msg = ctk.CTkLabel(f, text="", text_color="#B91C1C"); msg.grid(row=12, column=0, columnspan=3, sticky="w", pady=6)
        if edit and self.effort:
            e_name.insert(0, self.effort.name); e_name.configure(state="disabled")
            e_path.insert(0, self.effort.path)
            for k, e in dirs.items():
                if cur.get(k):
                    e.insert(0, cur[k])
        else:
            desk = os.path.join(os.path.expanduser("~"), "Desktop")
            e_path.insert(0, os.path.join(desk if os.path.isdir(desk) else os.path.expanduser("~"), "Effort_List.xlsx"))
            base_dir = os.path.dirname(e_path.get())
            def name_changed(*_):
                n = re.sub(r"[^A-Za-z0-9 _.-]+", "", e_name.get()).strip().replace(" ", "_")
                if n and os.path.basename(e_path.get()).endswith("Effort_List.xlsx"):   # one folder per effort
                    e_path.delete(0, "end"); e_path.insert(0, os.path.join(base_dir, n, f"{n}_Effort_List.xlsx"))
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
                    self.flush_session(); self.save_resume_now()
                    self.move_data_dir(self.effort.path, path)   # the effort's folder moves with its list
                    self.effort.path = path            # move: write the current list to the new place
                    self.effort.first_use = rule.get()
                    self._save_effort_list()
                L = E.EffortList(path, name, rule.get()).load()
                L.name, L.first_use = name, rule.get()
                if not os.path.isfile(path) or edit:
                    L.pending = True
                    if edit and self.effort is not None:
                        self.effort = L
                    if not self._save_effort_list(L, backup=False):
                        return
            except Exception as ex:
                diag.swallowed()
                msg.configure(text=f"Could not create the list: {type(ex).__name__}"); return
            self.efforts.put(name, path=path, first_use=rule.get(), **{k: e.get().strip() for k, e in dirs.items()})
            if self.effort is not None and self.effort.name == name:      # the list's About sheet and every row (2.14.0)
                self.effort.client, self.effort.solicitation, self.effort.internal_no = (
                    dirs["client"].get().strip(), dirs["solicitation"].get().strip(), dirs["internal_no"].get().strip())
                self.effort.pending = True
                self._save_effort_list()
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

    def open_effort(self, name, quiet=False, startup=False):
        """Open an effort with its own saved work. Opening the effort that is already open reloads its list.
        Returns True when the effort is open."""
        import workspace as W
        info = self.efforts.get(name)
        if not info:
            return False
        if self.busy():
            if not quiet:
                messagebox.showwarning("Busy", "Wait for the scan to finish, then switch efforts.")
            return False
        root = W.data_dir_for(info["path"])
        same = self.effort is not None and self.effort.name == name and \
            os.path.normcase(getattr(self.ws, "root", "")) == os.path.normcase(root)
        ws = self.ws if same else W.Workspace(root, name)
        if not same and not ws.acquire_lock():
            who = ws.locked_by or {}
            since = who.get("time", "")[11:16]
            text = (f"'{name}' is open in another Acronym Hunter window by {who.get('user', '?')} on {who.get('computer', '?')}"
                    + (f" (since {since})" if since else "") + ".")
            if quiet:
                self.status.configure(text=text + " Pick it again from the Effort list to open it here.")
                return False
            if not messagebox.askyesno("Effort in use", text + "\n\nTwo windows on one effort can overwrite each other's "
                                       "work. Open it here anyway?"):
                return False
            ws.acquire_lock(force=True)
        try:
            L = E.EffortList(info["path"], name, info.get("first_use", "volume"), client=info.get("client", ""),
                             solicitation=info.get("solicitation", ""), internal_no=info.get("internal_no", "")).load()
        except Exception as ex:
            diag.swallowed()
            if not same:
                ws.release_lock()
            if not quiet:
                messagebox.showerror("Effort list", f"The list could not be read ({type(ex).__name__}).\n{info['path']}")
            return False
        rec = ws.read_recovery("effort", L.path)
        if not same:
            self.leave_workspace()
            self.ws = ws
        self.effort = L
        self.efforts.current = name
        if rec:
            if self.ask_recover("Effort List", rec):
                st = rec["state"]
                L.rows, L.order, L.history = st.get("rows", {}), st.get("order", []), st.get("history", [])
                L.keywords = st.get("keywords", L.keywords)
                L.pending = True
                diag.activity("recovery_used")
                self._save_effort_list()
            else:
                ws.clear_recovery("effort", L.path)
        if same:
            diag.activity("effort_opened", terms=len(L.rows))
            self.apply_effort()
            self.update_effort_ui()
        else:
            diag.activity("effort_switched", terms=len(L.rows))
            self.enter_workspace(startup=startup)
        self.refresh_effort_bar()
        return True

    def export_effort_lists_ui(self):
        if self.effort is None:
            return
        info = self.efforts.get(self.effort.name) or {}
        made = self.export_effort_lists(scope=info.get("list_format", "whole"))
        if made:
            messagebox.showinfo("Acronym lists", "Saved:\n" + "\n".join(os.path.basename(p) for p in made) +
                                "\n\nRejected terms and the omit list are left out. The Excel file has Found in for every term.")

    def export_all_efforts_ui(self):
        got = self.export_all_efforts()
        if got:
            messagebox.showinfo("All efforts", f"{got[1]} rows from {got[2]} efforts saved:\n{got[0]}")

    def close_effort(self):
        """Back to no effort. Returns False when the user cancels."""
        import workspace as W
        if self.effort is None:
            return True
        if self.busy():
            messagebox.showwarning("Busy", "Wait for the scan to finish, then close the effort.")
            return False
        if self.effort.pending and not self._save_effort_list() and not messagebox.askyesno(
                "Close effort", "The list could not be saved (Excel has it open). Its changes stay in the effort's recovery "
                "copy and come back when you reopen it. Close anyway?"):
            return False
        self.leave_workspace()
        eng = _eng()
        self.effort = None
        self.efforts.current = ""
        self.ws = W.Workspace(os.path.join(eng.CONFIG_DIR, "no_effort"), "", choices_file=eng.CHOICES_FILE)
        diag.activity("effort_closed")
        self.enter_workspace()
        return True

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
    def _save_effort_list(self, L=None, backup=True):
        """Save, asking to close Excel when it holds the file. False = still not saved (kept pending, and kept in the
        effort's recovery copy so a crash loses nothing)."""
        L = L or self.effort
        ws = getattr(self, "ws", None) if L is self.effort else None
        if ws is not None and L.pending:
            try:
                ws.write_recovery("effort", L.path, {"rows": L.rows, "order": L.order, "history": L.history, "keywords": L.keywords})
            except Exception:
                diag.swallowed()
        while True:
            try:
                L.save()
                if ws is not None:
                    ws.clear_recovery("effort", L.path)
                    if backup:
                        try:
                            ws.backup(L.path, "effort")
                        except OSError:
                            diag.swallowed()
                return True
            except E.ListLocked:
                if not messagebox.askretrycancel("Effort list is open",
                                                 "The effort list is open in Excel, so it cannot be saved.\n\n"
                                                 "Close it in Excel, then click Retry. Cancel keeps the change in the app "
                                                 "(and in the effort's recovery copy) until you save (Effort > Save list now)."):
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
        if not sd or _eng().status_text(sd).startswith(("[", "MULTIPLE", "Rescan")):
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
            fields = dict(Type=eng.base_type(d.get("category", "")), Source=self._source_for(d, definition))
            # First use is checked only in our own Word deliverables (QA/QC tab), never from a scan of other files (2.24.0)
            if definition:
                fields["Definition"] = definition
            if cust and definition in d.get("customer_definitions", []):
                fields["Customer document"] = cust.get("where", "")
                fields["Customer wording"] = cust.get("sentence", "")[:500]
            others = [x for x in d.get("customer_definitions", []) + d.get("definitions", []) if x and x != definition]
            if others:
                fields["Other definitions"] = " | ".join(dict.fromkeys(others))[:500]
            docs = sorted({eng._file_of(l) for l in d.get("locations", []) if l and not l.startswith("Added manually")}, key=str.lower)
            if docs:
                row = self.effort.rows.get(t, {})
                had = [x for x in re.split(r"\s*;\s*", row.get("Found in", "")) if x]
                fields["Found in"] = "; ".join(sorted(set(had) | set(docs), key=str.lower))
                fields["Last found"] = E.today()
                if not row.get("First found"):
                    fields["First found"] = E.today()
            note = (f"added from {', '.join(docs)[:120]}" + (f": {definition[:60]}" if definition else "")) if docs and t not in self.effort.rows else None
            r = self.effort.add_or_update(t, change_note=note, **fields)
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
        if hasattr(self, "alt_context_menu"):          # alternate forms (2.26.0)
            self.alt_context_menu(sub, iid)
        menu.add_cascade(label="Effort list", menu=sub)

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
                d["status"] = "Customer document" + (" (database differs)" if db else "")
            else:
                d["selected_definition"] = "MULTIPLE: " + " | ".join(cdefs)
                d["status"] = f"CUSTOMER DOCS DIFFER ({len(cdefs)})"
        return n

    # ------------------------------------------------------------ the scan step
    def apply_effort(self, reload=False):
        """Mark results with the effort list: approved definitions win; rejected terms are hidden for this effort."""
        eng = _eng()
        if reload and self.effort is not None and not self.effort.pending:
            try:
                self.effort.load()
            except Exception:
                diag.swallowed()
        L = self.effort
        alt_map = L.alt_map() if L is not None else {}
        for term, d in self.results.items():
            pre = d.get("_pre_effort")
            row = L.rows.get(term) if L is not None else None
            primary = alt_map.get(term) if row is None else None
            if primary is not None and primary in L.rows:    # an alt form of a term in the effort list (2.26.0)
                if not pre:
                    d["_pre_effort"] = (d.get("status", ""), d.get("selected_definition", ""), d.get("excluded", False))
                    pre = d["_pre_effort"]
                prow = L.rows[primary]
                d["effort"] = prow["Status"]
                d["alt_of"] = primary
                d["excluded"] = pre[2]
                d["status"] = f"{eng.ALT_STATUS} {primary} (effort list: {prow['Status']})"
                d["selected_definition"] = prow["Definition"] or pre[1]
                continue
            if row is None:
                if pre:                                     # left the list, or the effort was closed: restore
                    d["status"], d["selected_definition"], d["excluded"] = pre
                    d.pop("_pre_effort", None); d.pop("effort", None)
                    if d.get("alt_of") and not str(pre[0]).startswith(eng.ALT_STATUS):
                        d.pop("alt_of", None)
                continue
            if not pre:
                d["_pre_effort"] = (d.get("status", ""), d.get("selected_definition", ""), d.get("excluded", False))
                pre = d["_pre_effort"]
            st = row["Status"]
            d["effort"] = st
            d["excluded"] = pre[2] or st == "Rejected"
            if st == "Rejected":
                d["status"] = "Not a term in this effort"
                d["selected_definition"] = pre[1]
            else:
                d["status"] = f"Effort list: {st}"
                d["selected_definition"] = row["Definition"] or pre[1]
        if hasattr(self, "tree"):
            self.populate_table()
        if hasattr(self, "session_changed"):
            self.session_changed()
