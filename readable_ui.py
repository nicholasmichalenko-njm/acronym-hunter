"""The readable copy on screen (2.46.0): kept current a few seconds after every saved change (readable.py), and
Effort > Open the readable copy folder. Rules only (No AI); nothing leaves the PC."""
import os, time
from tkinter import messagebox
import diag
import readable as RD

QUIET_S = 3.0                    # write once the files have been quiet this long, so a burst of changes writes once


class ReadableMixin:
    def readable_folder(self):
        L = getattr(self, "effort", None)
        return RD.folder_for(L.path, L.name) if L is not None else ""

    def _readable_sig(self):
        """The saved files' times: when any changes, the readable copy is out of date."""
        L = self.effort
        paths = [L.path]
        ws = getattr(self, "ws", None)
        if ws is not None:
            paths += [ws.p("record.json"), ws.p("documents", "index.json"), ws.p("documents", "register.json")]
        M = getattr(self, "matrix", None)
        if M is not None and getattr(M, "path", ""):
            paths.append(M.path)
        sig = []
        for p in paths:
            try:
                sig.append((p, os.path.getmtime(p)))
            except OSError:
                sig.append((p, 0))
        return tuple(sig)

    def readable_tick(self):
        """Called every 1.5 seconds: rewrite the copy once the saved files changed and then stayed quiet for a moment."""
        if getattr(self, "effort", None) is None:
            return False
        sig = self._readable_sig()
        if sig == getattr(self, "_rd_done", None):
            return False
        if sig != getattr(self, "_rd_seen", None):
            self._rd_seen, self._rd_since = sig, time.time()
            return False
        if time.time() - self._rd_since < QUIET_S:
            return False
        return self.readable_write_now(sig)

    def readable_write_now(self, sig=None):
        """Write the readable copy of the open effort now. Returns the folder, or False."""
        L = getattr(self, "effort", None)
        if L is None:
            return False
        try:
            reg = self.subreg() if hasattr(self, "subreg") else None
            rows = reg.rows(include_hidden=True) if reg is not None else []
            lib = self.doclib() if hasattr(self, "doclib") else None
            rec = self.effrec() if hasattr(self, "effrec") else None
            info = {"effort": L.name}
            app = __import__("app_gui")
            parts = RD.build(L, rec, lib, rows, getattr(self, "matrix", None), info, getattr(app, "APP_VERSION", ""))
            folder = self.readable_folder()
            RD.write(folder, parts, lib)
        except Exception:
            diag.swallowed()
            return False
        self._rd_done = sig or self._readable_sig()
        diag.activity("readable_written")
        return folder

    def readable_open(self):
        """Effort > Open the readable copy folder."""
        folder = self.readable_write_now() or self.readable_folder()
        if not folder or not os.path.isdir(folder):
            messagebox.showinfo("Readable copy", "Open an effort first.")
            return None
        try:
            os.startfile(folder)                       # noqa (Windows)
        except AttributeError:
            pass
        except OSError:
            diag.swallowed()
        return folder
