"""Exports kept and backups on screen (2.46.0; keepsafe.py has the rules). Rules only (No AI); nothing leaves the PC
except to folders the person picks.

- Every export made while an effort is open is also kept, dated, in "<effort> - exports (Stationkeeper)" beside the
  effort list. The app's save windows are watched, so every export is covered.
- Advanced > Backup location...: a second copy of every effort outside its folder, for example Documents\\Stationkeeper
  backups (refreshed a few minutes after changes and when the effort closes; written in the background).
"""
import datetime, os, threading, time, tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import diag
import keepsafe as K

BACKUP_AFTER_S = 180.0           # a backup a few minutes after the last change, so a burst of work backs up once
_APP = [None]                    # the window whose open effort an export belongs to
_ORIG = {}


def _watch_dialogs(app):
    """Watch the save windows (once per process): any save window, and the folder windows exports use."""
    _APP[0] = app
    if _ORIG:
        return
    _ORIG["save"], _ORIG["dir"] = filedialog.asksaveasfilename, filedialog.askdirectory

    def save(*a, **k):
        p = _ORIG["save"](*a, **k)
        a_ = _APP[0]
        if p and a_ is not None:
            try:
                a_.keep_saw(p, k.get("title", ""), False)
            except Exception:
                diag.swallowed()
        return p

    def folder(*a, **k):
        p = _ORIG["dir"](*a, **k)
        a_ = _APP[0]
        if p and a_ is not None:
            try:
                a_.keep_saw(p, k.get("title", ""), True)
            except Exception:
                diag.swallowed()
        return p
    filedialog.asksaveasfilename, filedialog.askdirectory = save, folder


class KeepSafeMixin:
    # ------------------------------------------------------------------ exports kept in the effort's folder
    def keep_start(self):
        self._keep = K.Watch()
        self._bk_thread, self._bk_result, self._bk_seen, self._bk_since, self._bk_done = None, None, None, 0.0, None
        _watch_dialogs(self)

    def exports_folder(self):
        L = getattr(self, "effort", None)
        return K.exports_folder(L.path, L.name) if L is not None else ""

    def _keep_skip(self):
        L, ws = self.effort, getattr(self, "ws", None)
        return [L.path, (ws.get("compliance_path", "") or "") if ws is not None else ""]

    def keep_saw(self, path, title, is_dir):
        """A save window returned a path: keep a dated copy once the export is written (only while an effort is open)."""
        if getattr(self, "effort", None) is None or not hasattr(self, "_keep"):
            return False
        if is_dir:
            return self._keep.saw_dir(path, title, self.exports_folder(), self._keep_skip())
        return self._keep.saw_file(path, title, self.exports_folder(), self._keep_skip())

    def keep_tick(self):
        """Called every 1.5 seconds: copy finished exports; start a backup once changes have been quiet a few minutes."""
        if not hasattr(self, "_keep"):
            return
        if self._keep.pending:
            made = self._keep.process()
            if made:
                diag.activity("exports_kept", files=len(made))
                if getattr(self, "status", None) is not None:
                    self.status.configure(text=f"A dated copy of the export is kept in {os.path.basename(os.path.dirname(made[0]))}")
        self.backup_tick()

    # ------------------------------------------------------------------ the backup location
    def backup_dir(self):
        return (getattr(self, "settings", {}) or {}).get("backup_dir", "") or ""

    def backup_set(self, path):
        """Turn backups on to a folder ("" turns them off)."""
        app = __import__("app_gui")
        if path:
            os.makedirs(path, exist_ok=True)
        self.settings["backup_dir"] = os.path.abspath(path) if path else ""
        app.save_settings(self.settings)
        self._bk_done = None
        if path:
            diag.activity("backup_location_set")
        else:
            diag.activity("backup_location_off")
        return self.settings["backup_dir"]

    def _backup_args(self):
        """What the backup needs, gathered on the main thread (the files themselves are read in the background)."""
        L, ws = getattr(self, "effort", None), getattr(self, "ws", None)
        if L is None or ws is None or not self.backup_dir():
            return None
        app = __import__("app_gui")
        info = dict(self.efforts.get(L.name) or {})
        r = self.effrec() if hasattr(self, "effrec") else None
        rd = self.readable_write_now() or "" if hasattr(self, "readable_write_now") else ""
        rd = rd or (self.readable_folder() if hasattr(self, "readable_folder") else "")
        return dict(backup_dir=self.backup_dir(), effort_name=L.name, list_path=L.path, data_dir=ws.root,
                    matrix_path=ws.get("compliance_path", "") or "", customer_dir=info.get("customer_dir", ""),
                    volumes_dir=info.get("volumes_dir", ""), readable_dir=rd if os.path.isdir(rd) else "",
                    exports_dir=self.exports_folder(),
                    extra_files=[dl.get("file") for dl in (r.data.get("deliverables", []) if r else []) if dl.get("file")],
                    info={**info, "name": L.name, "client": L.client, "solicitation": L.solicitation,
                          "internal_no": L.internal_no, "first_use": L.first_use},
                    stage=r.stage()["name"] if r else "", app_version=getattr(app, "APP_VERSION", ""),
                    config_dir=getattr(app, "CONFIG_DIR", ""), settings_file=getattr(app, "SETTINGS_FILE", ""))

    def backup_now(self, wait=False):
        """Back up the open effort now, in the background (wait: finish before returning; used on close and in tests).
        Returns the thread, or None."""
        if self._bk_thread is not None and self._bk_thread.is_alive():
            if wait:
                self._bk_thread.join()
            else:
                return None
        try:
            args = self._backup_args()
        except Exception:
            diag.swallowed()
            return None
        if not args:
            return None
        sig = self._readable_sig() if hasattr(self, "_readable_sig") else None

        def run():
            try:
                out = K.backup_effort(**args)
                self._bk_result = {"ok": True, "when": datetime.datetime.now(), "out": out, "sig": sig}
            except Exception as e:
                diag.swallowed()
                self._bk_result = {"ok": False, "when": datetime.datetime.now(), "error": type(e).__name__, "sig": sig}
        self._bk_thread = threading.Thread(target=run, name="stationkeeper-backup")   # not a daemon: a backup finishes
        self._bk_thread.start()
        if wait:
            self._bk_thread.join()
            self._backup_seen()
        return self._bk_thread

    def _backup_seen(self):
        res = self._bk_result
        if not res or res.get("noted"):
            return
        res["noted"] = True
        if res["ok"]:
            self._bk_done = res["sig"]
            diag.activity("backup_written")
        else:
            diag.activity("backup_failed")
        self.settings["backup_last"] = res["when"].isoformat(timespec="minutes") if res["ok"] else self.settings.get("backup_last", "")
        __import__("app_gui").save_settings(self.settings)

    def backup_tick(self):
        if self._bk_thread is not None and not self._bk_thread.is_alive():
            self._backup_seen()
        if not self.backup_dir() or getattr(self, "effort", None) is None or not hasattr(self, "_readable_sig"):
            return False
        sig = self._readable_sig()
        if sig == self._bk_done:
            return False
        if sig != self._bk_seen:
            self._bk_seen, self._bk_since = sig, time.time()
            return False
        if time.time() - self._bk_since < BACKUP_AFTER_S:
            return False
        return self.backup_now() is not None

    def backup_on_leave(self):
        """The effort is closing (its work just saved): back it up if anything changed since the last backup."""
        try:
            if self.backup_dir() and getattr(self, "effort", None) is not None:
                sig = self._readable_sig() if hasattr(self, "_readable_sig") else None
                if sig != self._bk_done:
                    self.backup_now(wait=True)
        except Exception:
            diag.swallowed()

    def backup_status(self):
        d = self.backup_dir()
        if not d:
            return "Backups are off. Choose a folder outside the effort's folder, for example in Documents."
        last = self.settings.get("backup_last", "")
        when = ""
        if last:
            try:
                when = datetime.datetime.fromisoformat(last).strftime("%b %d, %Y %I:%M %p").replace(" 0", " ")
            except ValueError:
                when = last
        return f"Backing up to {d}" + (f"\nLast backup: {when}" if when else "\nNo backup yet.")

    def backup_location_dialog(self):
        """Advanced > Backup location..."""
        w = ctk.CTkToplevel(self); w.title("Backup location"); w.transient(self); w.geometry("700x430")
        ctk.CTkLabel(w, text="Backup location", font=("Segoe UI", 16, "bold"), anchor="w").pack(fill="x", padx=16, pady=(14, 2))
        ctk.CTkLabel(w, anchor="w", justify="left", wraplength=660, text=(
            "A second copy of every effort, kept outside the effort's folder, in case that folder is deleted or damaged. "
            "For each effort: the whole effort as an effort package (File > Import effort package... picks up exactly where "
            "it was), one dated package per day for 30 days, the readable copy and the dated exports. The app's settings, "
            "banned words, keyword knowledge and master database are kept beside them. Written a few minutes after changes "
            "and when an effort closes, in the background.")).pack(fill="x", padx=16)
        st = ctk.CTkLabel(w, anchor="w", justify="left", wraplength=660, text=self.backup_status(), font=("Segoe UI", 12, "bold"))
        st.pack(fill="x", padx=16, pady=(10, 0))
        warn = ctk.CTkLabel(w, anchor="w", justify="left", wraplength=660, text="", text_color=("#B45309", "#FBBF24"))
        warn.pack(fill="x", padx=16, pady=(6, 0))

        def show():
            st.configure(text=self.backup_status())
            d = self.backup_dir()
            warn.configure(text=("This folder is synced by OneDrive (or a similar service), so the backups leave this PC "
                                 "for that service's cloud. Use it only if your company allows proposal data there; "
                                 "otherwise choose a folder that is not synced.") if K.synced(d) else "")

        def choose():
            d = filedialog.askdirectory(parent=w, title="Backup location", initialdir=os.path.dirname(self.backup_dir() or K.default_backup_dir()))
            if d:
                self.backup_set(d); show()

        def suggested():
            self.backup_set(K.default_backup_dir()); show()

        def off():
            self.backup_set(""); show()

        def now():
            if getattr(self, "effort", None) is None:
                messagebox.showinfo("Backup location", "Open an effort first.", parent=w)
                return
            self.backup_now(wait=True); show()

        def open_():
            d = self.backup_dir()
            if d and os.path.isdir(d):
                try:
                    os.startfile(d)                    # noqa (Windows)
                except (AttributeError, OSError):
                    pass
        row = ctk.CTkFrame(w, fg_color="transparent"); row.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkButton(row, text="Use Documents\\Stationkeeper backups", command=suggested, fg_color="#0F766E").pack(side="left")
        ctk.CTkButton(row, text="Choose a folder...", command=choose).pack(side="left", padx=8)
        ctk.CTkButton(row, text="Turn off", command=off, fg_color="#64748B").pack(side="left")
        row2 = ctk.CTkFrame(w, fg_color="transparent"); row2.pack(fill="x", padx=16, pady=4)
        ctk.CTkButton(row2, text="Back up now", command=now).pack(side="left")
        ctk.CTkButton(row2, text="Open the backup folder", command=open_, fg_color="#64748B").pack(side="left", padx=8)
        ctk.CTkButton(w, text="Close", command=w.destroy, fg_color="#64748B").pack(side="right", padx=16, pady=14)
        show()
        w._api = {"suggested": suggested, "off": off, "now": now, "status": st, "warn": warn, "show": show}
        w.after(100, w.lift)
        return w
