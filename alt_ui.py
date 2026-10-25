"""Alternate forms and the master database's use history (2.26.0).

- Scan review > right-click > Effort list > Make an alt form of...: TTC becomes an alternate form of TT&C. It stays its
  own row in the results ("Alt form of TT&C" with TT&C's definition) and is never a row in the effort list.
- Effort list (home) > Alt forms...: add, change or remove a term's alternate forms.
- Effort > Add this effort to the master database...: one master row per term and meaning, with the efforts that used
  it, how many times and when last, and its alternate forms. Writes a new version of the team's master file (the old one
  is kept in "Master database backups" beside it) and loads it.
Every list the app writes shows the primary with its alternate forms in parentheses: "TT&C (TTC)".
"""
import os, re
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import diag
import alt_forms as AF


def _eng():
    import app_gui
    return app_gui


def _squash(t):
    return re.sub(r"[^A-Z0-9]", "", (t or "").upper())


class AltFormsMixin:
    # ------------------------------------------------------------ make an alt form (Scan review)
    def alt_candidates(self, alt):
        """Likely primaries for an alternate form: same letters without &, /, - or case first, then every other term."""
        L = self.effort
        pool = list(L.order) if L is not None else []
        pool += [t for t in self.results if t not in pool and not self.results[t].get("file_error")]
        pool = [t for t in pool if t != alt]
        sq = _squash(alt)
        close = [t for t in pool if _squash(t) == sq or _squash(t).startswith(sq) or sq.startswith(_squash(t)) and len(_squash(t)) >= 2]
        return close + [t for t in pool if t not in close]

    def alt_make_dialog(self, alt, primary=None):
        """Ask which term `alt` is an alternate form of. Returns the window (tests call win._api['ok'](name))."""
        if self.effort is None:
            messagebox.showinfo("Alt forms", "Open an effort first: alternate forms are kept in the effort list.")
            return None
        win = ctk.CTkToplevel(self); win.title("Make an alt form"); win.geometry("520x220"); win.transient(self)
        win.after(150, win.lift)
        ctk.CTkLabel(win, text=f"{alt} is another way of writing:", anchor="w").pack(fill="x", padx=14, pady=(14, 4))
        opts = self.alt_candidates(alt)[:300] or [""]
        var = tk.StringVar(value=primary or opts[0])
        box = ctk.CTkComboBox(win, values=opts, variable=var, width=320)
        box.pack(anchor="w", padx=14)
        ctk.CTkLabel(win, text=("It keeps its own row in the results, labelled with the primary and its definition, and the "
                                "effort list keeps it in the primary's Alt forms column. Lists show it as "
                                f"\"{var.get() or 'Primary'} ({alt})\"."), wraplength=480, justify="left",
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=14, pady=8)

        def ok(name=None):
            p = (name or var.get() or "").strip()
            if not p or p == alt:
                return False
            done = self.make_alt(alt, p)
            win.destroy()
            return done
        b = ctk.CTkFrame(win, fg_color="transparent"); b.pack(fill="x", padx=14, pady=8)
        ctk.CTkButton(b, text="Make alt form", fg_color="#0F766E", command=ok).pack(side="left")
        ctk.CTkButton(b, text="Cancel", fg_color="#475569", command=win.destroy).pack(side="right")
        win._api = {"ok": ok, "var": var}
        return win

    def make_alt(self, alt, primary):
        """`alt` becomes an alternate form of `primary` in the effort list (the primary is added as Proposed when needed)."""
        eng = _eng()
        L = self.effort
        if L is None or not alt or not primary or alt == primary:
            return False
        if primary not in L.rows:
            d = self.results.get(primary) or self.results.get(alt) or {}
            definition = self._definition_for(d) if d and hasattr(self, "_definition_for") else ""
            L.add_or_update(primary, change_note="added as the primary of an alt form (Proposed)",
                            Type=eng.base_type(d.get("category", "Acronym")) if d else "Acronym",
                            Definition=definition or None, Source="Alt form")
        folded = L.set_alts(primary, L.alts(primary) + [alt], note=f"alt form added: {alt}")
        diag.activity("alt_form_added", n=1 + len(folded))
        self._save_effort_list()
        self.apply_effort()
        self.update_effort_ui()
        if hasattr(self, "home_refresh"):
            self.home_refresh()
        self.status.configure(text=f"{alt} is now an alt form of {primary}. Lists show \"{AF.join_term(primary, L.alts(primary))}\".")
        return True

    def remove_alt(self, alt, primary):
        L = self.effort
        if L is None or primary not in L.rows:
            return False
        L.set_alts(primary, [a for a in L.alts(primary) if a != alt], note=f"alt form removed: {alt}")
        d = self.results.get(alt)
        if d is not None and d.get("alt_of") == primary:
            d.pop("alt_of", None)
        diag.activity("alt_form_removed")
        self._save_effort_list()
        self.apply_effort()
        self.update_effort_ui()
        return True

    def alt_context_menu(self, sub, iid):
        """Entries for the results table's Effort list menu."""
        d = self.results.get(iid) or {}
        L = self.effort
        if L is None or d.get("file_error"):
            return
        sub.add_separator()
        prim = d.get("alt_of")
        if prim and prim in L.rows and iid in L.alts(prim):
            sub.add_command(label=f"Not an alt form of {prim}", command=lambda: self.remove_alt(iid, prim))
        else:
            sub.add_command(label=f"Make {iid[:30]} an alt form of...", command=lambda: self.alt_make_dialog(iid))

    # ------------------------------------------------------------ edit alt forms (Effort list)
    def alt_edit_dialog(self, term=None):
        L = self.effort
        if L is None:
            return None
        term = term or (self.home_selected()[0] if hasattr(self, "home_selected") and self.home_selected() else None)
        if not term or term not in L.rows:
            messagebox.showinfo("Alt forms", "Select one term in the effort list first.")
            return None
        win = ctk.CTkToplevel(self); win.title(f"Alt forms: {term}"); win.geometry("520x230"); win.transient(self)
        win.after(150, win.lift)
        ctk.CTkLabel(win, text=f"Other ways {term} is written (separate with commas):", anchor="w").pack(fill="x", padx=14, pady=(14, 4))
        e = ctk.CTkEntry(win, width=480); e.pack(anchor="w", padx=14)
        e.insert(0, ", ".join(L.alts(term)))
        prev = ctk.CTkLabel(win, text="", anchor="w", text_color=("#0F766E", "#5EEAD4"))
        prev.pack(fill="x", padx=14, pady=(6, 0))
        ctk.CTkLabel(win, text=("An alt form that has its own row in the effort list is folded into this one. Lists show the "
                                "term with its alt forms in parentheses."), wraplength=480, justify="left",
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=14, pady=6)

        def show(*_a):
            prev.configure(text="Lists will show: " + AF.join_term(term, AF.parse_alts(e.get())))
        e.bind("<KeyRelease>", show); show()

        def ok(text=None):
            alts = AF.parse_alts(e.get() if text is None else text)
            folded = L.set_alts(term, alts, note="alt forms: " + (", ".join(alts) or "none"))
            diag.activity("alt_forms_edited", n=len(alts))
            self._save_effort_list()
            self.apply_effort()
            self.update_effort_ui()
            if hasattr(self, "home_refresh"):
                self.home_refresh()
            if folded:
                self.status.configure(text=f"Folded into {term}: {', '.join(folded)}")
            win.destroy()
            return folded
        b = ctk.CTkFrame(win, fg_color="transparent"); b.pack(fill="x", padx=14, pady=8)
        ctk.CTkButton(b, text="Save", fg_color="#0F766E", command=ok).pack(side="left")
        ctk.CTkButton(b, text="Cancel", fg_color="#475569", command=win.destroy).pack(side="right")
        win._api = {"ok": ok, "entry": e}
        return win

    # ------------------------------------------------------------ add the effort to the master database
    def master_add_effort(self, path=None, confirm=True):
        """Effort > Add this effort to the master database. Returns the combine report, or None."""
        import master_db as M
        L = self.effort
        if L is None:
            return None
        if L.pending:
            self._save_effort_list()
        info = M.master_info()
        path = path or (info.get("path") if info.get("path") and os.path.isfile(info.get("path", "")) else None)
        if not path:
            if not confirm:
                return None
            ans = messagebox.askyesnocancel(
                M.MASTER_NAME, f"Which {M.MASTER_NAME} file should this effort be added to?\n\n"
                "Yes: pick the team's master file (Excel or CSV).\nNo: start a new master file.\nCancel: stop.")
            if ans is None:
                return None
            if ans:
                path = filedialog.askopenfilename(title=M.MASTER_NAME, filetypes=[("Database", "*.xlsx *.csv")])
            else:
                path = filedialog.asksaveasfilename(title=f"New {M.MASTER_NAME}", defaultextension=".xlsx",
                                                    initialfile="Master_Acronym_Database.xlsx",
                                                    filetypes=[("Excel", "*.xlsx"), ("CSV", "*.csv")])
                if path and not os.path.exists(path):
                    M.write_master(path, [])
            if not path:
                return None
        try:
            current = M.read_master_file(path) if os.path.getsize(path) else []
        except Exception:
            diag.swallowed()
            messagebox.showerror(M.MASTER_NAME, f"Could not read {os.path.basename(path)}. Is it open in Excel? Close it and try again.")
            return None
        label = M.effort_label(L)
        rows, rep = M.combine(current, [L.rows[t] for t in L.order], label)
        n_appr = sum(1 for r in L.rows.values() if r.get("Status") == "Approved")
        summary = (f"{label} into {os.path.basename(path)}:\n"
                   f"{len(rep['added'])} new rows, {len(rep['updated'])} rows get this effort or new alt forms, "
                   f"{rep['same']} already up to date.\nOnly Approved terms with a definition go in ({n_appr} approved).")
        if confirm and not self._master_preview(summary, rep):
            return None
        if not rep["added"] and not rep["updated"]:
            if confirm:
                messagebox.showinfo(M.MASTER_NAME, "Nothing to add: the master already has this effort.")
            return rep
        try:
            backup = M.backup_master(path) if os.path.getsize(path) else ""
            M.write_master(path, rows)
        except PermissionError:
            messagebox.showerror(M.MASTER_NAME, "The master file is open in Excel. Close it, then try again.")
            return None
        info = self.master_load(path, ask=False)
        L._hist("(effort)", f"added to the {M.MASTER_NAME} ({os.path.basename(path)}, version "
                            f"{(info or {}).get('version', '?')}): {len(rep['added'])} new, {len(rep['updated'])} updated")
        self._save_effort_list()
        diag.activity("master_effort_added", added=len(rep["added"]), n=len(rep["updated"]))
        rep["backup"], rep["path"] = backup, path
        if confirm:
            messagebox.showinfo(M.MASTER_NAME, summary + (f"\n\nThe earlier file is kept in:\n{os.path.dirname(backup)}"
                                                              if backup else ""))
        return rep

    def _master_preview(self, summary, rep):
        import master_db as M
        win = ctk.CTkToplevel(self); win.title("Add this effort to the Acronyms, Abbreviations, Units and Symbols Master Database"); win.geometry("720x520")
        win.transient(self); win.after(150, win.lift)
        ctk.CTkLabel(win, text=summary, anchor="w", justify="left", wraplength=680).pack(fill="x", padx=14, pady=(12, 6))
        box = ctk.CTkTextbox(win, wrap="word"); box.pack(fill="both", expand=True, padx=14)
        lines = (["New rows:"] + [f"  {t}" for t in rep["added"]] + ["", "Rows that get this effort or new alt forms:"]
                 + [f"  {t}" for t in rep["updated"]])
        box.insert("1.0", "\n".join(lines)); box.configure(state="disabled")
        out = {"ok": False}
        b = ctk.CTkFrame(win, fg_color="transparent"); b.pack(fill="x", padx=14, pady=10)
        ctk.CTkButton(b, text="Save a new version of the master", fg_color="#0F766E",
                      command=lambda: (out.update(ok=True), win.destroy())).pack(side="left")
        ctk.CTkButton(b, text="Cancel", fg_color="#475569", command=win.destroy).pack(side="right")
        win.grab_set(); self.wait_window(win)
        return out["ok"]
