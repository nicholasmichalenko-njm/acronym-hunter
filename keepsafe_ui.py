"""Exports kept and backups on screen (2.46.0; keepsafe.py has the rules). Rules only (No AI); nothing leaves the PC
except to folders the person picks.

- Every export made while an effort is open is also kept, dated, in "<effort> - exports (Stationkeeper)" beside the
  effort list. The app's save windows are watched, so every export is covered.
- File > Backup location...: a second copy of every effort outside its folder, for example Documents\\Stationkeeper
  backups (refreshed a few minutes after changes and when the effort closes; written in the background).
"""
import datetime, os, threading, time, tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import diag
import keepsafe as K
import bgwork

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
                bgwork.wait(self._bk_thread)
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
        self._bk_thread = bgwork.start(run, "stationkeeper-backup")     # not a daemon: a backup finishes
        if wait:
            bgwork.wait(self._bk_thread)
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
        """File > Backup location..."""
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
        ctk.CTkButton(row2, text="Restore from a backup folder...", command=lambda: (w.destroy(), self.backup_restore_dialog()),
                      fg_color="#64748B").pack(side="left")
        ctk.CTkButton(w, text="Close", command=w.destroy, fg_color="#64748B").pack(side="right", padx=16, pady=14)
        show()
        w._api = {"suggested": suggested, "off": off, "now": now, "status": st, "warn": warn, "show": show}
        w.after(100, w.lift)
        return w

    # ------------------------------------------------------------------ first start, and restoring from a backup folder
    def backup_first_run(self, force=False):
        """The first time the app starts with no backup location (a new PC, or the app folder was replaced): one window,
        "Select a backup location or select an existing backup folder". Never blocking: Not now closes it, and File >
        Backup location... is always there."""
        if not force and (self.backup_dir() or self.settings.get("backup_asked") or os.environ.get("AH_TEST")):
            return None
        w = ctk.CTkToplevel(self); w.title("Backup location"); w.transient(self); w.geometry("660x330")
        ctk.CTkLabel(w, text="Select a backup location or select an existing backup folder", font=("Segoe UI", 16, "bold"),
                     anchor="w", wraplength=620, justify="left").pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(w, anchor="w", justify="left", wraplength=620, text=(
            "A backup location keeps a second copy of every effort outside the app's folder, so nothing is lost if the "
            "app's folder or an effort's folder is deleted. If you used Stationkeeper before on this PC or another, select "
            "your existing backup folder to bring your efforts and settings back where you left off.")).pack(fill="x", padx=16)

        def done():
            self.settings["backup_asked"] = True
            __import__("app_gui").save_settings(self.settings)
            w.destroy()

        def suggested():
            self.backup_set(K.default_backup_dir()); done()

        def choose():
            d = filedialog.askdirectory(parent=w, title="Backup location", initialdir=os.path.dirname(K.default_backup_dir()))
            if d:
                self.backup_set(d); done()

        def existing():
            done()
            self.backup_restore_dialog()
        col = ctk.CTkFrame(w, fg_color="transparent"); col.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkButton(col, text="Use Documents\\Stationkeeper backups", command=suggested, fg_color="#0F766E").pack(anchor="w", pady=3)
        ctk.CTkButton(col, text="Choose a backup location...", command=choose).pack(anchor="w", pady=3)
        ctk.CTkButton(col, text="Select an existing backup folder...", command=existing).pack(anchor="w", pady=3)
        ctk.CTkButton(w, text="Not now", command=done, fg_color="#64748B").pack(side="right", padx=16, pady=12)
        ctk.CTkLabel(w, text="File > Backup location... sets this up any time.", anchor="w",
                     text_color=("#475569", "#94A3B8")).pack(side="left", padx=16, pady=12)
        w.protocol("WM_DELETE_WINDOW", done)
        w._api = {"suggested": suggested, "existing": existing, "not_now": done}
        w.after(100, w.lift)
        return w

    def backup_restore(self, backup_dir, names=None, settings=True, dest=""):
        """Bring efforts (and the app's settings) back from a backup folder. An effort whose folder is still where it was
        is simply listed again; one whose folder is gone is restored from its latest package into dest. The folder then
        becomes the backup location. Returns {"settings": files, "relinked": [...], "restored": [...], "skipped": [...]}."""
        app = __import__("app_gui")
        import effort as E
        out = {"settings": 0, "relinked": [], "restored": [], "skipped": []}
        found = [b for b in K.find_backups(backup_dir) if names is None or b["name"] in names]
        if getattr(self, "effort", None) is not None and hasattr(self, "leave_workspace"):
            self.leave_workspace()
            self.effort = None
        zp = K.latest_settings(backup_dir) if settings else ""
        if zp:
            out["settings"] = K.restore_settings(zp, app.CONFIG_DIR, app.SETTINGS_FILE)
            self.efforts = E.Registry(os.path.join(app.CONFIG_DIR, "efforts.json"))
            self.settings = app.load_settings()
        for b in found:
            have = self.efforts.get(b["name"]) or {}
            if have.get("path") and os.path.isfile(have["path"]):
                out["relinked"].append(b["name"])
                continue
            if b["original_list"] and os.path.isfile(b["original_list"]):
                inf = __import__("effortpkg").read_manifest(b["package"]).get("info", {})
                keep = {k: inf.get(k) for k in ("customer_dir", "volumes_dir", "first_use", "client", "solicitation",
                                                "internal_no", "list_format") if inf.get(k) is not None}
                self.efforts.put(b["name"], path=b["original_list"], **keep)
                out["relinked"].append(b["name"])
                continue
            if not dest:
                out["skipped"].append(b["name"])
                continue
            got = self.pkg_import_dialog(path=b["package"], dest=dest, mode="replace" if b["name"] in self.efforts.names() else None)
            (out["restored"] if got else out["skipped"]).append(b["name"])
        self.backup_set(backup_dir)
        self.settings["backup_asked"] = True
        app.save_settings(self.settings)
        diag.activity("backup_restored", items=len(out["restored"]) + len(out["relinked"]), files=out["settings"])
        return out

    def backup_restore_dialog(self, folder=None):
        """File > Restore from a backup folder...: pick the folder, see what it holds, restore."""
        if folder is None:
            folder = filedialog.askdirectory(title="Select an existing backup folder", initialdir=os.path.dirname(K.default_backup_dir()))
            if not folder:
                return None
        found = K.find_backups(folder)
        zp = K.latest_settings(folder)
        if not found and not zp:
            messagebox.showinfo("Restore from a backup folder", "That folder holds no Stationkeeper backups. Choose the folder "
                                "that holds 'READ ME.txt' and one folder per effort.")
            return None
        w = ctk.CTkToplevel(self); w.title("Restore from a backup folder"); w.transient(self); w.geometry("760x520")
        ctk.CTkLabel(w, text="Restore from a backup folder", font=("Segoe UI", 16, "bold"), anchor="w").pack(fill="x", padx=16, pady=(14, 2))
        ctk.CTkLabel(w, text=folder, anchor="w", text_color=("#475569", "#94A3B8")).pack(fill="x", padx=16)
        box = ctk.CTkScrollableFrame(w, height=260); box.pack(fill="both", expand=True, padx=16, pady=8)
        picks = {}
        for b in found:
            here = (self.efforts.get(b["name"]) or {}).get("path", "")
            if here and os.path.isfile(here):
                how = "already on this PC: listed as it is"
            elif b["original_list"] and os.path.isfile(b["original_list"]):
                how = "its folder is still there: listed again"
            else:
                how = "restored from the backup"
            when = b["saved_at"].replace("T", " ")
            picks[b["name"]] = tk.BooleanVar(value=True)
            ctk.CTkCheckBox(box, variable=picks[b["name"]], text=f"{b['name']}   (backed up {when}"
                            + (f", {b['stage']}" if b["stage"] else "") + f"; {how})").pack(anchor="w", pady=2)
        sv = tk.BooleanVar(value=bool(zp))
        cb = ctk.CTkCheckBox(w, variable=sv, text="Also restore the app's settings, banned words, keyword knowledge and master database"
                             + (f" ({os.path.basename(zp)[len('Stationkeeper settings and team lists '):-4]})" if zp else ""))
        cb.pack(anchor="w", padx=16, pady=(4, 0))
        if not zp:
            cb.configure(state="disabled")
        ctk.CTkLabel(w, text="This folder becomes the backup location.", anchor="w",
                     text_color=("#475569", "#94A3B8")).pack(fill="x", padx=16, pady=(4, 0))

        def go(dest=None):
            names = [n for n, v in picks.items() if v.get()]
            need = [b for b in found if b["name"] in names and not ((self.efforts.get(b["name"]) or {}).get("path") and
                    os.path.isfile((self.efforts.get(b["name"]) or {}).get("path"))) and not (b["original_list"] and os.path.isfile(b["original_list"]))]
            if need and dest is None:
                dest = filedialog.askdirectory(parent=w, title="Where should the restored efforts go?",
                                               initialdir=os.path.dirname(K.default_backup_dir()))
                if not dest:
                    return None
            w.destroy()
            res = self.backup_restore(folder, names=names, settings=sv.get(), dest=dest or "")
            msg = []
            if res["restored"]:
                msg.append("Restored from the backup: " + ", ".join(res["restored"]))
            if res["relinked"]:
                msg.append("Listed again (their folders were still there): " + ", ".join(res["relinked"]))
            if res["skipped"]:
                msg.append("Not restored: " + ", ".join(res["skipped"]))
            if res["settings"]:
                msg.append("The app's settings, banned words, keyword knowledge and master database are restored; restart "
                           "Stationkeeper to use all of them.")
            messagebox.showinfo("Restore from a backup folder", "\n\n".join(msg) or "Nothing was restored.")
            if res["restored"] or res["relinked"]:
                n = (res["restored"] or res["relinked"])[0]
                if getattr(self, "effort", None) is None:
                    self.open_effort(n)
            return res
        bar = ctk.CTkFrame(w, fg_color="transparent"); bar.pack(fill="x", side="bottom", padx=16, pady=12)
        ctk.CTkButton(bar, text="Restore", fg_color="#0F766E", command=go).pack(side="right")
        ctk.CTkButton(bar, text="Cancel", fg_color="#64748B", command=w.destroy).pack(side="right", padx=6)
        w._api = {"picks": picks, "settings": sv, "go": go}
        w.after(100, w.lift)
        return w
