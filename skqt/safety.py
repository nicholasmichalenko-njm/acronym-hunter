"""Never lose work (2.78.0): what keeps an effort safe in the Qt window, which became the main window in 2.74.0 and had
lost the classic window's automatic protection.

- Automatic backups: a few minutes after the last change, and when the effort closes, the whole effort goes to the
  backup folder as "<effort> - latest.skpkg" plus one copy per day (kept 30 days), with the app's settings and team lists
  (keepsafe.backup_effort, the same backup the classic window made). Written in the background.
- Dated copies in the effort's own folder: the compliance matrix and the effort list after a save (at most one every
  10 minutes; the last 10 and one per day for 14 days), so a bad change can be put back without the backup folder.
- A recovery copy of the matrix with every change; if Stationkeeper or Windows stops before the save, the next opening
  offers to put those changes back.
- Restore points: every dated copy and every backup package, newest first; restoring keeps the current state as a backup.
- Where you were: the page, the sentence, the volume, the structure target and the file come back when the effort opens.
- The crash screen: on an unexpected error the work is saved first, then a plain message says it is safe.
Offline; files go only to the effort's folder and the backup folder the person chose.
"""
import datetime, os, shutil, sys, threading, time
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox
import diag

BACKUP_AFTER_S = 180.0          # a burst of work backs up once, a few minutes after it stops
TICK_MS = 15000
_SKIP_DIRS = {"backups", "recovery", "__pycache__"}
_SKIP_FILES = {"lock.json", "qt_view.json", "revision.json"}


def _nice(dt):
    if dt is None:
        return ""
    today = datetime.date.today()
    day = "Today" if dt.date() == today else "Yesterday" if dt.date() == today - datetime.timedelta(days=1) else dt.strftime("%b %d, %Y")
    return f"{day} {dt.strftime('%I:%M %p').lstrip('0')}"


class Safety:
    def __init__(self, host):
        self.host = host
        self.thread = None
        self.result = None
        self.done_sig = None            # the state the last good backup holds
        self.seen_sig, self.seen_at = None, 0.0
        self.list_mtime = None
        self.recovery_answer = None     # tests: "restore" or "discard"
        self.crash_answer = None        # tests: "keep" or "restart"
        self._last_crash = 0.0
        self.test_dir = None
        self.recovered_text = ""
        self.rev_sig = None
        self.issues = []
        self.disk_mtime = self.disk_sha = None
        self.conflict_answer = None     # tests: "mine" or "theirs"
        self.snap_timer = QTimer(host, singleShot=True, interval=400, timeout=self.snapshot)
        self.timer = QTimer(host, interval=TICK_MS, timeout=self.tick)
        self.timer.start()

    # ------------------------------------------------------------ settings
    def settings(self):
        try:
            import app_gui
            return app_gui.load_settings() or {}
        except Exception:
            diag.swallowed()
            return {}

    def backup_dir(self):
        if os.environ.get("AH_TEST") and self.test_dir is None:
            return ""                             # tests never write to a real backup folder; qt_safety sets test_dir
        if self.test_dir:
            return self.test_dir
        import workmode as WM                     # 2.79.0: Connected mode with no folder chosen: the team folder's Backups
        return WM.backup_dir(self.settings())

    def last_backup(self):
        v = self.settings().get("backup_last", "")
        try:
            return datetime.datetime.fromisoformat(v) if v else None
        except ValueError:
            return None

    def status_text(self):
        d = self.backup_dir()
        if not d:
            return ("Backups are off. Choose a folder (the approved SharePoint folder, or one outside the effort's folder) "
                    "so every effort is copied there automatically.")
        last = self.last_backup()
        res = self.result or {}
        import workmode as WM
        warn = WM.folder_warning(self.settings(), d)
        if warn:
            return f"Backups go to {d}. {warn}"
        if res.get("ok") is False:
            return f"The last backup to {d} did not finish ({res.get('error', 'error')}). It is tried again after the next change."
        return f"Backups go to {d}" + (f"; the last one was {_nice(last)}." if last else "; none yet.") + \
            " The latest copy follows each change within minutes; one copy a day is kept for 30 days."

    # ------------------------------------------------------------ what changed
    def signature(self):
        h = self.host
        if h.ws is None:
            return None
        parts = []
        paths = [h.effort_path, h.ws.get("compliance_path", "") or ""]
        for d, dirs, files in os.walk(h.ws.root):
            dirs[:] = [x for x in dirs if x not in _SKIP_DIRS]
            for f in files:
                if f not in _SKIP_FILES and not f.endswith(".tmp"):
                    paths.append(os.path.join(d, f))
        for p in paths:
            try:
                st = os.stat(p)
                parts.append((p, int(st.st_mtime), st.st_size))
            except OSError:
                pass
        return hash(tuple(sorted(parts)))

    def args(self):
        """What the backup needs, gathered here (the files are read in the background)."""
        h = self.host
        import app_gui
        import keepsafe as K
        info = dict(h.efforts.get(h.effort_name) or {})
        rec = None
        try:
            import effortrec as RR
            rec = RR.Record(h.ws.root)
        except Exception:
            diag.swallowed()
        L = None
        try:
            import effort as E
            L = E.EffortList(h.effort_path).load()
        except Exception:
            diag.swallowed()
        ex = K.exports_folder(h.effort_path, h.effort_name)
        return dict(backup_dir=self.backup_dir(), effort_name=h.effort_name, list_path=h.effort_path, data_dir=h.ws.root,
                    matrix_path=h.ws.get("compliance_path", "") or "", customer_dir=info.get("customer_dir", ""),
                    volumes_dir=info.get("volumes_dir", ""), exports_dir=ex if os.path.isdir(ex) else "",
                    extra_files=[dl.get("file") for dl in (rec.data.get("deliverables", []) if rec else []) if dl.get("file")],
                    info={**info, "name": h.effort_name, "client": getattr(L, "client", ""), "solicitation": getattr(L, "solicitation", ""),
                          "internal_no": getattr(L, "internal_no", ""), "first_use": getattr(L, "first_use", "volume")},
                    stage=rec.stage()["name"] if rec else "", app_version=h.version,
                    config_dir=getattr(app_gui, "CONFIG_DIR", ""), settings_file=getattr(app_gui, "SETTINGS_FILE", ""))

    # ------------------------------------------------------------ automatic backups
    def backup_now(self, wait=False, force=False):
        """Back up the open effort (in the background unless wait). Returns True when one started."""
        h = self.host
        if h.ws is None or not self.backup_dir():
            return False
        if self.thread is not None and self.thread.is_alive():
            if not wait:
                return False
            self.thread.join()
        h.save_now()
        sig = self.signature()
        if not force and sig == self.done_sig:
            return False
        try:
            a = self.args()
        except Exception:
            diag.swallowed()
            return False

        def run():
            import keepsafe as K
            try:
                K.backup_effort(**a)
                self.result = {"ok": True, "when": datetime.datetime.now(), "sig": sig}
            except Exception as e:
                diag.swallowed()
                self.result = {"ok": False, "when": datetime.datetime.now(), "error": type(e).__name__, "sig": sig}
        self.thread = threading.Thread(target=run, name="stationkeeper-backup", daemon=False)    # a backup finishes
        self.thread.start()
        if wait:
            self.thread.join()
            self.noted()
        return True

    def noted(self):
        res = self.result
        if not res or res.get("noted"):
            return
        res["noted"] = True
        if res["ok"]:
            self.done_sig = res["sig"]
            diag.activity("qt_backup_auto")
            try:
                import app_gui
                st = app_gui.load_settings() or {}
                st["backup_last"] = res["when"].isoformat(timespec="minutes")
                app_gui.save_settings(st)
            except Exception:
                diag.swallowed()
        else:
            diag.activity("qt_backup_failed")
            self.host.status(self.status_text())

    def tick(self):
        """Every few seconds: note a finished backup; back up once the work has been quiet for a few minutes; keep a dated
        copy of the effort list when it changed."""
        if self.thread is not None and not self.thread.is_alive():
            self.noted()
        h = self.host
        if h.ws is None:
            return False
        self.list_copy()
        self.save_view()
        self.revise()
        self.presence()
        if not self.backup_dir():
            return False
        sig = self.signature()
        if sig == self.done_sig:
            return False
        if sig != self.seen_sig:
            self.seen_sig, self.seen_at = sig, time.time()
            return False
        if time.time() - self.seen_at < BACKUP_AFTER_S:
            return False
        return self.backup_now()

    def list_copy(self):
        """A dated copy of the effort list in the effort's folder when it changed (at most one every 10 minutes)."""
        h = self.host
        try:
            m = os.path.getmtime(h.effort_path)
        except OSError:
            return None
        if self.list_mtime is None:
            self.list_mtime = m
            return None
        if m == self.list_mtime:
            return None
        got = h.ws.backup(h.effort_path, "effort")
        if got:
            self.list_mtime = m
        return got

    # ------------------------------------------------------------ 2.79.0: revisions and who has it open
    def revise(self, force=False):
        """A new revision when the saved work changed since the last one (one per burst of work). Returns it or None."""
        h = self.host
        if h.ws is None:
            return None
        sig = self.signature()
        if not force and sig == self.rev_sig:
            return None
        self.rev_sig = sig
        try:
            import lineage as LG
            return LG.bump(h.ws.root)
        except Exception:
            diag.swallowed()
            return None

    def presence(self):
        """Connected mode: keep the team folder's marker saying this effort is open here."""
        h = self.host
        import workmode as WM
        team = WM.team_dir(self.settings())
        if h.ws is None or not team:
            return None
        try:
            return WM.mark(team, h.effort_name, h.version)
        except OSError:
            diag.swallowed()
            return None

    # ------------------------------------------------------------ the matrix: recovery copy and dated copies
    def changed(self):
        self.snap_timer.start()

    def snapshot(self):
        h = self.host
        if h.ws is None or h.review is None or not h.review.M.pending:
            return False
        M = h.review.M
        try:
            h.ws.write_recovery("matrix", M.path, {k: v for k, v in vars(M).items() if k not in ("path", "pending")})
            return True
        except Exception:
            diag.swallowed()
            return False

    @staticmethod
    def _sha(path):
        import hashlib
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        return h.hexdigest()

    def loaded(self, path):
        try:
            self.disk_mtime, self.disk_sha = os.path.getmtime(path), self._sha(path)
        except OSError:
            self.disk_mtime, self.disk_sha = None, None

    def before_save(self, M):
        """2.80.0 check before overwrite: when the matrix on disk changed since it was loaded or saved here (another PC,
        or OneDrive brought a newer copy), ask before overwriting. True: go ahead and save. conflict_answer (tests):
        'mine' or 'theirs'."""
        try:
            cur = os.path.getmtime(M.path)
        except OSError:
            return True
        if self.disk_mtime is None or abs(cur - self.disk_mtime) < 0.001:
            return True
        try:
            if self._sha(M.path) == self.disk_sha:     # touched (a sync tool), not changed
                self.disk_mtime = cur
                return True
        except OSError:
            return True
        h = self.host
        ans = self.conflict_answer
        if ans is None:
            box = QMessageBox(h); box.setWindowTitle("The matrix changed on disk")
            box.setText("The compliance matrix was saved by another copy since you opened it (another PC, or OneDrive brought "
                        "a newer copy). Keep yours (theirs is kept as a dated copy), or open theirs (yours is kept as a copy "
                        "beside it, to compare).")
            mine = box.addButton("Keep mine", QMessageBox.AcceptRole); box.addButton("Open theirs", QMessageBox.RejectRole)
            box.exec()
            ans = "mine" if box.clickedButton() is mine else "theirs"
        diag.activity("qt_disk_conflict")
        if ans == "mine":
            if h.ws is not None:
                h.ws.backup(M.path, "matrix", force=True)
            return True
        import getpass
        stem, ext = os.path.splitext(M.path)
        mine_path = f"{stem} (yours {getpass.getuser()} {datetime.datetime.now():%Y-%m-%d %H%M}){ext}"
        real = M.path
        try:
            M.path = mine_path
            M.save()
        finally:
            M.path = real
        import compliance as C
        name = h.effort_name
        h.review.M.pending = False
        h.close_effort()
        h.open_effort(name)
        h.status(f"Opened the newer copy. Yours is kept as {os.path.basename(mine_path)}.")
        return False

    def saved(self, path):
        h = self.host
        self.loaded(path)
        if h.ws is None:
            return
        try:
            h.ws.clear_recovery("matrix", path)
            h.ws.backup(path, "matrix")
        except Exception:
            diag.swallowed()

    def offer_recovery(self, M):
        """The matrix just opened: changes written to the recovery copy after its last save come back if wanted."""
        h = self.host
        rec = h.ws.read_recovery("matrix", M.path) if h.ws is not None else None
        if not rec:
            return False
        n = max(0, len(rec["state"].get("history", [])) - len(getattr(M, "history", []) or []))
        when = rec.get("time", "")[11:16]
        ans = self.recovery_answer
        if ans is None:
            box = QMessageBox(h); box.setWindowTitle("Unsaved changes found")
            box.setText(f"Stationkeeper closed before {n or 'some'} change(s) to the compliance matrix were saved "
                        f"(last at {when}). Put them back?")
            put = box.addButton("Put them back", QMessageBox.AcceptRole); box.addButton("Leave them out", QMessageBox.RejectRole)
            box.exec()
            ans = "restore" if box.clickedButton() is put else "discard"
        if ans != "restore":
            h.ws.clear_recovery("matrix", M.path)
            return False
        for k, v in rec["state"].items():
            setattr(M, k, v)
        M.pending = True
        diag.activity("qt_recovery_used", n=n)
        self.recovered_text = f"{n} unsaved change(s) put back." if n else "Unsaved changes put back."
        return True

    # ------------------------------------------------------------ where you were
    def view(self):
        h = self.host
        a = h.assign_page
        key = next((k for k, pg in h.pages.items() if pg is h.stack.currentWidget()), "")
        return {"page": key, "sentence": a.cur or "", "volume": a.volume.currentData() or "", "target": a.target or "",
                "file": getattr(a, "file", "") or "", "at": datetime.datetime.now().isoformat(timespec="seconds")}

    def save_view(self):
        h = self.host
        if h.ws is None:
            return None
        try:
            v = self.view()
            if v["page"] == "settings":
                return None
            import workspace as W
            W.write_json(h.ws.p("qt_view.json"), v)      # its own file: moving around is not a change to back up
            return v
        except Exception:
            diag.swallowed()
            return None

    def restore_view(self, v=None):
        """Back to where you were in this effort (or the view v, from a package). Returns the view used."""
        h = self.host
        if h.ws is None:
            return None
        if v is None:
            import workspace as W
            v = W.read_json(h.ws.p("qt_view.json"), None) or {}
        if not isinstance(v, dict) or not v:
            return None
        a = h.assign_page
        try:
            if v.get("volume") and a.volume.findData(v["volume"]) >= 0:
                a.volume.setCurrentIndex(a.volume.findData(v["volume"]))
                a.pick_volume(v["volume"])
            if v.get("page") in h.pages and v["page"] != "settings":
                h.go(v["page"])
            if v.get("target") and h.review is not None:
                a.set_target(v["target"])
            if v.get("sentence") and h.review is not None and h.review.item(v["sentence"]) is not None:
                a.select(v["sentence"])
        except Exception:
            diag.swallowed()
        return v

    # ------------------------------------------------------------ opening and closing
    def opened(self):
        h = self.host
        self.done_sig = self.signature()          # what is on disk now is what the next backup compares with
        self.rev_sig = self.done_sig
        self.seen_sig, self.list_mtime, self.result = None, None, None
        try:
            import lineage as LG
            LG.ensure(h.ws.root)
        except Exception:
            diag.swallowed()
        self.presence()
        if not self.backup_dir():
            h.status("Backups are off: choose a folder in Settings > Backups so your work is copied there automatically.")

    def closing(self):
        """The effort is closing (its work just saved): back it up if anything changed, and remember where you were."""
        self.save_view()
        self.revise()
        try:
            if self.backup_dir():
                self.backup_now(wait=True)
        except Exception:
            diag.swallowed()
        try:
            import workmode as WM
            team = WM.team_dir(self.settings())
            if team:
                WM.unmark(team, self.host.effort_name)
        except Exception:
            diag.swallowed()

    # ------------------------------------------------------------ 2.80.0: effort health and repairs
    def health(self, repair=True):
        """Check the open effort; with repair, a list or matrix that cannot be read is replaced by its newest good dated copy
        (the damaged file is kept beside it). Returns (issues left, what was repaired)."""
        import effortcheck as EC
        h = self.host
        if h.ws is None:
            return [], []
        info = h.efforts.get(h.effort_name) or {}
        mp = h.ws.get("compliance_path", "") or ""
        issues = EC.check(h.ws, h.effort_path, mp, info.get("customer_dir", ""), info.get("volumes_dir", ""))
        fixed = []
        if repair:
            for i in [x for x in issues if x["fix"] in ("restore_list", "restore_matrix")]:
                kind, target = ("effort", h.effort_path) if i["fix"] == "restore_list" else ("matrix", mp)
                used = EC.restore_copy(h.ws, kind, target)
                if used:
                    fixed.append(("The effort list" if kind == "effort" else "The compliance matrix")
                                 + " could not be read, so its newest good copy was put back; the damaged file is kept beside it.")
                    diag.activity("qt_health_repaired")
            if fixed:
                issues = EC.check(h.ws, h.effort_path, mp, info.get("customer_dir", ""), info.get("volumes_dir", ""))
        self.issues = issues
        return issues, fixed

    def move_to_pc(self, dest_root=None):
        """Move the open effort into Stationkeeper Data\\Efforts on this PC (through its package; the old folder is backed
        up first and left in place). Returns the new list path or None."""
        import tempfile
        import app_gui, datahome
        h = self.host
        if h.ws is None:
            return None
        dest_root = dest_root or datahome.efforts_dir(app_gui.DATA_DIR)
        rp = h.record_page
        pk = os.path.join(tempfile.mkdtemp(), "move.skpkg")
        if not rp.save_package(pk):
            return None
        got = h.import_package(pk, dest=dest_root, mode="replace")
        if got:
            diag.activity("qt_effort_moved_local")
            h.toast(f"{h.effort_name} now lives on this PC: {os.path.dirname(got['list'])}")
            return got["list"]
        return None

    # ------------------------------------------------------------ restore points
    def points(self):
        """[{kind, label, when, path}] newest first: the effort's dated copies and the backup folder's packages."""
        h = self.host
        out = []
        if h.ws is None:
            return out
        for path, kind, _stem, when in h.ws.backups():
            out.append({"kind": kind, "label": ("Compliance matrix" if kind == "matrix" else "Effort list") + " copy",
                        "when": when, "path": path})
        bd = self.backup_dir()
        if bd:
            import keepsafe as K
            root = os.path.join(bd, K._safe(h.effort_name))
            if os.path.isdir(root):
                for f in os.listdir(root):
                    if f.lower().endswith(".skpkg"):
                        p = os.path.join(root, f)
                        out.append({"kind": "package", "label": "Whole effort (backup package)" + (": latest" if " - latest" in f else ""),
                                    "when": datetime.datetime.fromtimestamp(os.path.getmtime(p)), "path": p})
        out.sort(key=lambda r: r["when"], reverse=True)
        return out

    def restore(self, point):
        """Put a restore point back; the current state is kept as a dated copy (or a backup) first. Returns True."""
        h = self.host
        if h.ws is None:
            return False
        name = h.effort_name
        if point["kind"] == "package":
            got = h.import_package(point["path"], dest=os.path.dirname(os.path.dirname(h.effort_path)) or None, mode="replace")
            ok = bool(got)
        else:
            target = h.ws.get("compliance_path", "") if point["kind"] == "matrix" else h.effort_path
            if not target:
                return False
            h.save_now()
            h.ws.backup(target, point["kind"], force=True)
            h.close_effort()
            try:
                shutil.copy2(point["path"], target)
                ok = True
            except OSError:
                diag.swallowed()
                ok = False
            h.open_effort(name)
        diag.activity("qt_restore_point_used")
        if ok:
            h.toast(f"Put back: {point['label']} from {_nice(point['when'])}")
        return ok

    # ------------------------------------------------------------ the crash screen
    def install_crash_screen(self):
        prev = sys.excepthook

        def hook(t, e, tb):
            try:
                prev(t, e, tb)                    # the content-free log entry (diag) comes first
            except Exception:
                pass
            self.crashed(t)
        sys.excepthook = hook
        return hook

    def crashed(self, exc_type=None):
        """Save first, then say the work is safe. Returns what the person chose ('keep' or 'restart')."""
        now = time.time()
        if now - self._last_crash < 5:            # one message for a burst of errors
            return "keep"
        self._last_crash = now
        h = self.host
        saved = True
        try:
            h.save_now()
            self.snapshot()
        except Exception:
            saved = False
        try:
            diag.activity("qt_crash_screen")
        except Exception:
            pass
        ans = self.crash_answer
        if ans is None:
            box = QMessageBox(h); box.setWindowTitle("Stationkeeper hit a problem")
            box.setIcon(QMessageBox.Warning)
            box.setText(("Your work is saved. " if saved else "Your recent changes are kept in the recovery copy. ")
                        + "Something unexpected went wrong in Stationkeeper (it is recorded in the logs, without any "
                          "document content). You can keep working. If it happens again, restart Stationkeeper: it "
                          "opens where you were.")
            keep = box.addButton("Keep working", QMessageBox.AcceptRole); box.addButton("Restart Stationkeeper", QMessageBox.DestructiveRole)
            box.exec()
            ans = "keep" if box.clickedButton() is keep else "restart"
        if ans == "restart":
            try:
                h.close()
                import updatepack as U
                from . import updates as UP
                U.restart(UP.app_dir(), UP.program_name())
                QApplication.instance().quit()
            except Exception:
                diag.swallowed()
        return ans
