"""Effort profiles in the app (2.11.0): top bar switcher, resume per effort, session saved as you work, recovery of
unsaved work after a crash, backups and Restore earlier version, archive, and the one-window-per-effort lock.

Each effort has its own Workspace (workspace.py). With no effort open, the app uses config\\no_effort.
"""
import datetime, json, os, shutil, time
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import diag
import workspace as W

NO_EFFORT = "(No effort)"
HEARTBEAT_MS = 10 * 60 * 1000


def _eng():
    import app_gui
    return app_gui


def when_text(dt):
    """'today 4:12 PM', 'yesterday 9:05 AM', 'Oct 21, 2:30 PM'."""
    if dt is None:
        return ""
    clock = dt.strftime("%I:%M %p").lstrip("0")
    days = (datetime.date.today() - dt.date()).days
    if days == 0:
        return f"today {clock}"
    if days == 1:
        return f"yesterday {clock}"
    return f"{dt.strftime('%b')} {dt.day}, {clock}"


class WorkspaceMixin:
    """Mixed into AcronymAppGUI (before EffortMixin's helpers are used)."""

    # ------------------------------------------------------------ setup
    def workspace_init(self):
        eng = _eng()
        self.ws = W.Workspace(os.path.join(eng.CONFIG_DIR, "no_effort"), "", choices_file=eng.CHOICES_FILE)
        self._ws_after = None
        self._ws_resume_after = None
        self._ws_beat = None
        self._ws_restoring = False
        bar = ctk.CTkFrame(self, corner_radius=0, height=38, fg_color=("#E2E8F0", "#0F172A"))
        bar.pack(side="top", fill="x", before=self.body)
        self.topbar = bar
        ctk.CTkLabel(bar, text="Effort", font=("Segoe UI", 12, "bold"), text_color=("#334155", "#CBD5E1")).pack(side="left", padx=(12, 6), pady=5)
        self.effort_var = tk.StringVar(value=NO_EFFORT)
        self.opt_effort = ctk.CTkOptionMenu(bar, variable=self.effort_var, values=[NO_EFFORT], width=260, dynamic_resizing=False,
                                            command=self._switch_from_bar)
        self.opt_effort.pack(side="left", pady=5)
        ctk.CTkButton(bar, text="Start an effort...", width=130, height=28, command=lambda: self.open_wizard(),
                      fg_color=("#CBD5E1", "#334155"), hover_color=("#94A3B8", "#475569"),
                      text_color=("#0F172A", "#F1F5F9")).pack(side="left", padx=8, pady=5)
        self.topbar_right = ctk.CTkFrame(bar, fg_color="transparent")
        self.topbar_right.pack(side="right", padx=8)
        self.refresh_effort_bar()

    def refresh_effort_bar(self):
        names = [n for n in self.efforts.names() if not (self.efforts.get(n) or {}).get("archived")]
        self.opt_effort.configure(values=[NO_EFFORT] + names)
        self.effort_var.set(self.effort.name if self.effort is not None else NO_EFFORT)
        eng = _eng()
        if self.effort is not None:
            self.title(f"Acronym Hunter {eng.APP_VERSION} | Effort: {self.effort.name}")
        else:
            self.title(f"Acronym Hunter {eng.APP_VERSION}: acronyms, abbreviations and units (100% local)")

    def _switch_from_bar(self, value):
        if self.effort is not None and value == self.effort.name or self.effort is None and value == NO_EFFORT:
            return
        ok = self.close_effort() if value == NO_EFFORT else self.open_effort(value)
        if not ok:
            self.refresh_effort_bar()

    def busy(self):
        return str(self.btn_project.cget("state")) == "disabled"

    # ------------------------------------------------------------ start
    def workspace_startup(self):
        """Run once after the window is built: one-time move of PC-wide data, then resume the last effort."""
        self._migrate_2_11()
        cur = self.efforts.current
        if cur and not (self.efforts.get(cur) or {}).get("archived"):
            if self.open_effort(cur, quiet=True, startup=True):
                return
        self.enter_workspace(startup=True)
        if not self.efforts.names() and not os.environ.get("AH_TEST") and hasattr(self, "open_wizard"):
            self.after(400, self.open_wizard)          # first start: set up the first effort (2.14.0)

    def _migrate_2_11(self):
        """2.11.0: choices and the compliance matrix path were PC-wide. They now belong to an effort. The effort open at
        upgrade time gets a copy (it is the one they were most likely made in); scans with no effort keep the originals."""
        reg = self.efforts
        if reg.data.get("migrated_2_11"):
            return
        eng = _eng()
        cpath = self.settings.get("compliance_path", "")
        try:
            if cpath and not self.ws.get("compliance_path"):
                self.ws.set("compliance_path", cpath)
            cur = reg.current
            info = reg.get(cur) if cur else None
            if info and info.get("path"):
                ws = W.Workspace(W.data_dir_for(info["path"]), cur)
                if not ws.load_choices():
                    old = self.ws.load_choices()
                    if old:
                        W.write_json(ws.choices_file, old)
                if cpath and not ws.get("compliance_path"):
                    ws.set("compliance_path", cpath)
        except Exception:
            diag.swallowed()
        reg.data["migrated_2_11"] = eng.APP_VERSION
        reg.save()

    # ------------------------------------------------------------ leave and enter
    def leave_workspace(self):
        """Save everything for the current effort and close its windows. Nothing is shared with the next one."""
        if getattr(self, "ws", None) is None:
            return
        for attr in ("_ws_after", "_ws_resume_after", "_c_snap_after"):   # done now instead of in a moment
            job = getattr(self, attr, None)
            if job:
                try:
                    self.after_cancel(job)
                except Exception:
                    diag.swallowed()
                setattr(self, attr, None)
        self.flush_session()
        self.save_resume_now()
        cw = getattr(self, "_cwin", None)
        if cw is not None and cw.winfo_exists():
            if self.matrix is not None and self.matrix.pending:
                if getattr(self, "_c_after", None):
                    try:
                        self.after_cancel(self._c_after)
                    except Exception:
                        diag.swallowed()
                if not self._c_save_now():
                    self._c_snapshot()              # could not save (Excel): keep the recovery copy current
            cw.destroy()
        self._cwin = None
        self.matrix = None
        vw = getattr(self, "_volwin", None)
        if vw is not None:
            try:
                if vw.winfo_exists():
                    vw.destroy()
            except tk.TclError:
                pass
        self._volwin = None
        self.volume_report = None
        self._last_effort_scan = None
        if self.project is not None:
            self.close_project()
        if self._ws_beat:
            try:
                self.after_cancel(self._ws_beat)
            except Exception:
                diag.swallowed()
            self._ws_beat = None
        self.ws.release_lock()

    def enter_workspace(self, startup=False):
        """Show the current workspace's last session and put the user back where they were."""
        self._ws_restoring = True
        if hasattr(self, "ai_load_for_workspace"):
            self.ai_load_for_workspace()          # this effort's AI and ML setting, before anything is shown (2.12.0)
        try:
            self.results, self.manual_items, self.selected_term = {}, {}, None
            try:                                          # the effort's client lists (2.14.0)
                self.set_client_lists(self.ws.get("client_lists", []) or [])
            except Exception:
                diag.swallowed()
            self.last_scan = None
            self.session_decisions = {}
            s = self.ws.load_session()
            if s:
                try:
                    self.results = s.get("results") or {}
                    self.manual_items = s.get("manual_items") or {}
                    ls = s.get("last_scan")
                    if ls and ls.get("paths"):
                        self.last_scan = {"paths": ls["paths"], "folder": ls.get("folder"), "cache": {}}
                        self.scanned_paths.update({os.path.basename(f): f for f in ls["paths"]})
                    self.session_decisions = s.get("session_decisions") or {}
                    vr = s.get("volume_report")
                    self.volume_report = vr if vr else None
                    diag.activity("session_restored", terms=len(self.results))
                except Exception:
                    diag.swallowed()
                    self.results = {}
            self.apply_effort()
            self.refresh_type_options()
            self.reset_ui()
            self.populate_table()
            r = self.ws.load_resume()
            self._restore_view(r)
            if hasattr(self, "home_restore"):
                self.home_restore((r or {}).get("home"))
        finally:
            self._ws_restoring = False
        self.refresh_effort_bar()
        self.update_effort_ui()
        when = when_text(self.ws.last_worked())
        if self.effort is not None:
            msg = f"Resumed {self.effort.name}" + (f", last worked {when}." if when else ".")
        else:
            msg = "No effort open." + (f" Showing the last scan from {when}." if self.results and when else "")
        self.status.configure(text=msg + " Running offline: nothing leaves this PC.")
        self._status_hold = time.time() + 5          # keep "Resumed <effort>" on screen for a few seconds
        if self.effort is not None:
            self._ws_beat = self.after(HEARTBEAT_MS, self._heartbeat)

    def _heartbeat(self):
        try:
            self.ws.refresh_lock()
        except Exception:
            diag.swallowed()
        self._ws_beat = self.after(HEARTBEAT_MS, self._heartbeat)

    # ------------------------------------------------------------ session (saved as you work)
    def session_changed(self):
        """Something in the results changed: save the session in a moment (several changes, one write)."""
        if self._ws_restoring or getattr(self, "ws", None) is None:
            return
        if self._ws_after:
            try:
                self.after_cancel(self._ws_after)
            except Exception:
                diag.swallowed()
        self._ws_after = self.after(1500, self.flush_session)

    def flush_session(self):
        self._ws_after = None
        if getattr(self, "ws", None) is None:
            return
        ls = getattr(self, "last_scan", None) or {}
        vr = getattr(self, "volume_report", None)
        try:
            json.dumps(vr, default=W._default)
        except Exception:
            vr = None
        data = {"effort": self.effort.name if self.effort is not None else "",
                "results": {k: v for k, v in self.results.items()},
                "manual_items": self.manual_items,
                "last_scan": {"paths": ls.get("paths", []), "folder": ls.get("folder")} if ls else None,
                "session_decisions": getattr(self, "session_decisions", {}),
                "volume_report": vr}
        try:
            self.ws.save_session(data)
        except Exception:
            diag.swallowed()

    # ------------------------------------------------------------ resume (where you were)
    def resume_changed(self):
        if self._ws_restoring or getattr(self, "ws", None) is None:
            return
        if self._ws_resume_after:
            try:
                self.after_cancel(self._ws_resume_after)
            except Exception:
                diag.swallowed()
        self._ws_resume_after = self.after(1000, self.save_resume_now)

    def save_resume_now(self):
        self._ws_resume_after = None
        if getattr(self, "ws", None) is None:
            return
        r = {"selected_term": self.selected_term or "", "search": self.search_var.get(), "type": self.type_var.get(),
             "status": self.status_var.get(), "show_excluded": bool(self.show_exc_var.get()),
             "sort": [self.sort_col, bool(self.sort_desc)]}
        if hasattr(self, "home_state"):
            r["home"] = self.home_state()          # the effort home: view, filter, search, selection (2.14.0)
        cw = getattr(self, "_cwin", None)
        if cw is not None and cw.winfo_exists():
            sel = cw.tv.selection()
            r["compliance"] = {"open": True, "selected": sel[0] if sel else "",
                               "filters": [v.get() for v in (cw.f_dec, cw.f_type, cw.f_sug, cw.f_learn, cw.f_map, cw.f_q)],
                               "tab": cw.tabs.get()}
        try:
            self.ws.save_resume(r)
        except Exception:
            diag.swallowed()

    def _restore_view(self, r):
        if not r:
            return
        try:
            eng = _eng()
            if r.get("type") and r["type"] in (self.opt_type.cget("values") or [eng.ALL_TYPES]):
                self.type_var.set(r["type"])
            if r.get("status") in eng.STATUS_FILTERS:
                self.status_var.set(r["status"])
            self.show_exc_var.set(bool(r.get("show_excluded")))
            if isinstance(r.get("sort"), list) and len(r["sort"]) == 2:
                self.sort_col, self.sort_desc = r["sort"][0], bool(r["sort"][1])
            self.search_var.set(r.get("search", ""))          # refills the table
            self.populate_table()
            t = r.get("selected_term")
            if t and self.tree.exists(t):
                self.tree.selection_set(t); self.tree.focus(t); self.tree.see(t)
                self.on_select(None)
            c = r.get("compliance") or {}
            if c.get("open"):
                cw = self.open_compliance(show=False)
                if not hasattr(cw, "cp_text"):                   # the Page view shows every sentence (2.32.0)
                    for var, val in zip((cw.f_dec, cw.f_type, cw.f_sug, cw.f_learn, cw.f_map, cw.f_q), c.get("filters") or []):
                        var.set(val)
                if c.get("tab") and not hasattr(self, "shell_go"):
                    try:
                        cw.tabs.set(c["tab"])
                    except Exception:
                        diag.swallowed()
                self._c_fill()
                if c.get("selected") and cw.tv.exists(c["selected"]):
                    cw.tv.selection_set(c["selected"]); cw.tv.see(c["selected"]); self._c_show()
        except Exception:
            diag.swallowed()

    # ------------------------------------------------------------ recovery helpers
    def ask_recover(self, what, rec, extra=""):
        try:
            t = datetime.datetime.fromisoformat(rec["time"])
        except (KeyError, ValueError):
            t = None
        return messagebox.askyesno("Recover unsaved work",
                                   f"The {what} has changes from {when_text(t)} that were not saved"
                                   f"{extra}. The app closed before it could save, or the file was open in Excel.\n\n"
                                   "Recover them now?")

    # ------------------------------------------------------------ backups
    def restore_dialog(self):
        """File > Restore an earlier version: pick a dated copy of the Effort List or compliance matrix."""
        diag.activity("restore_opened")
        rows = []
        if self.effort is not None:
            rows += [("effort", r) for r in self.ws.backups("effort")]
        cpath = (self.matrix.path if getattr(self, "matrix", None) is not None else "") or self.ws.get("compliance_path", "")
        if cpath:
            stem = os.path.splitext(os.path.basename(cpath))[0]
            rows += [("matrix", r) for r in self.ws.backups("matrix") if r[2] == stem]
        win = ctk.CTkToplevel(self); win.title("Restore an earlier version")
        win.geometry("620x420"); win.transient(self); win.after(150, win.lift)
        diag.register(win, "restore")
        who = self.effort.name if self.effort is not None else "scans with no effort"
        ctk.CTkLabel(win, text=f"Saved copies for {who}. The current file is copied first, so a restore can be undone.",
                     wraplength=580, justify="left").pack(anchor="w", padx=14, pady=(12, 6))
        lb = tk.Listbox(win, font=("Segoe UI", max(10, getattr(self, "font_size", 13) - 2)), activestyle="none", exportselection=False)
        lb.pack(fill="both", expand=True, padx=14, pady=4)
        label = {"effort": "Effort List", "matrix": "Compliance matrix"}
        rows.sort(key=lambda kr: kr[1][3], reverse=True)
        for kind, r in rows:
            lb.insert("end", f"{label[kind]:<20}  {r[3].strftime('%Y-%m-%d %H:%M:%S')}   ({when_text(r[3])})")
        if not rows:
            lb.insert("end", "No saved copies yet. A copy is kept at most every 10 minutes while you work.")
        msg = ctk.CTkLabel(win, text="", text_color="#B91C1C"); msg.pack(anchor="w", padx=14)

        def do():
            sel = lb.curselection()
            if not sel or not rows:
                return
            kind, r = rows[sel[0]]
            try:
                if kind == "effort":
                    self.ws.restore(r[0], self.effort.path)
                    self.ws.clear_recovery("effort", self.effort.path)
                    self.open_effort(self.effort.name)       # same effort: reloads the list
                else:
                    dest = cpath
                    self.ws.restore(r[0], dest)
                    self.ws.clear_recovery("matrix", dest)
                    if getattr(self, "_cwin", None) is not None and self._cwin.winfo_exists():
                        self._c_load(dest)
                    else:
                        self.matrix = None
            except PermissionError:
                msg.configure(text="That file is open in Excel. Close it, then try again."); return
            except OSError as ex:
                diag.swallowed()
                msg.configure(text=f"Could not restore ({type(ex).__name__})."); return
            diag.activity("backup_restored")
            win.destroy()
            self.status.configure(text=f"Restored the {label[kind]} saved {when_text(r[3])}.")
        b = ctk.CTkFrame(win, fg_color="transparent"); b.pack(fill="x", padx=14, pady=10)
        ctk.CTkButton(b, text="Restore selected", command=do).pack(side="left")
        ctk.CTkButton(b, text="Close", fg_color="#475569", command=win.destroy).pack(side="right")
        win._api = {"list": lb, "rows": rows, "do": do}
        return win

    # ------------------------------------------------------------ archive
    def archive_effort(self):
        if self.effort is None:
            return
        name = self.effort.name
        if not messagebox.askyesno("Archive effort", f"Hide '{name}' from the effort list? Nothing is deleted; reopen it any "
                                   "time from Effort > Archived efforts."):
            return
        if not self.close_effort():
            return
        self.efforts.put(name, archived=True)
        diag.activity("effort_archived")
        self.refresh_effort_bar()

    def unarchive_effort(self, name):
        self.efforts.put(name, archived=False)
        self.refresh_effort_bar()
        self.open_effort(name)

    # ------------------------------------------------------------ moving an effort's folder with its list
    @staticmethod
    def move_data_dir(old_list, new_list):
        old, new = W.data_dir_for(old_list), W.data_dir_for(new_list)
        if os.path.normcase(old) == os.path.normcase(new) or not os.path.isdir(old):
            return
        shutil.copytree(old, new, dirs_exist_ok=True)
        try:
            os.remove(os.path.join(new, "lock.json"))
        except OSError:
            pass
