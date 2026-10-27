"""The readable copy on screen (2.46.0): kept current a few seconds after every saved change (readable.py), and
Effort > Open the readable copy folder. Rules only (No AI); nothing leaves the PC.

2.47.0: written in the background from the saved files themselves (the effort list, record.json, the customer document
library and the compliance matrix workbook), so a large effort never holds up the window."""
import os, time
from tkinter import messagebox
import diag
import readable as RD
import bgwork

QUIET_S = 3.0                    # write once the files have been quiet this long, so a burst of changes writes once


def _write_from_disk(job):
    """Load what the effort has saved and write the readable copy (any thread: nothing on screen is touched)."""
    import effort as E, effortrec as ER, docversions as DV, subreq as SR, compliance as C
    L = E.EffortList(job["list"], job["name"], client=job["client"], solicitation=job["solicitation"],
                     internal_no=job["internal_no"]).load()
    rec = ER.Record(job["data"]) if job["data"] and os.path.isdir(job["data"]) else None
    lib = DV.Library(os.path.join(job["data"], "documents")).load() if job["data"] else None
    rows = SR.Register(lib).rows(include_hidden=True) if lib is not None else []
    M = C.Matrix(job["matrix"]).load() if job["matrix"] and os.path.isfile(job["matrix"]) else None
    parts = RD.build(L, rec, lib, rows, M, {"effort": job["name"]}, job["version"])
    RD.write(job["folder"], parts, lib)
    return job["folder"]


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
            mp = ws.get("compliance_path", "") or ""
            if mp:
                paths.append(mp)
        M = getattr(self, "matrix", None)
        if M is not None and getattr(M, "path", "") and M.path not in paths:
            paths.append(M.path)
        sig = []
        for p in paths:
            try:
                sig.append((p, os.path.getmtime(p)))
            except OSError:
                sig.append((p, 0))
        return tuple(sig)

    def _readable_job(self):
        L, ws = getattr(self, "effort", None), getattr(self, "ws", None)
        if L is None:
            return None
        M = getattr(self, "matrix", None)
        mp = (getattr(M, "path", "") if M is not None else "") or ((ws.get("compliance_path", "") or "") if ws is not None else "")
        return {"list": L.path, "name": L.name, "client": L.client, "solicitation": L.solicitation, "internal_no": L.internal_no,
                "data": ws.root if ws is not None else "", "matrix": mp, "folder": self.readable_folder(),
                "version": getattr(__import__("app_gui"), "APP_VERSION", "")}

    def readable_tick(self):
        """Called every 1.5 seconds: once the saved files changed and then stayed quiet for a moment, rewrite the copy in
        the background. Returns True when a write started."""
        if getattr(self, "effort", None) is None:
            return False
        t = getattr(self, "_rd_thread", None)
        if t is not None and t.is_alive():
            return False
        sig = self._readable_sig()
        if sig == getattr(self, "_rd_done", None):
            return False
        if sig != getattr(self, "_rd_seen", None):
            self._rd_seen, self._rd_since = sig, time.time()
            return False
        if time.time() - self._rd_since < QUIET_S:
            return False
        job = self._readable_job()
        if job is None:
            return False

        def run():
            try:
                _write_from_disk(job)
            except Exception:
                diag.swallowed()                     # the next saved change tries again
            self._rd_done = sig
        self._rd_thread = bgwork.start(run, "stationkeeper-readable")
        diag.activity("readable_written")
        return True

    def readable_wait(self, timeout=120):
        bgwork.wait(getattr(self, "_rd_thread", None), timeout)

    def readable_write_now(self, sig=None):
        """Write the readable copy of the open effort now, from its saved files (waits). Returns the folder, or False."""
        self.readable_wait()
        job = self._readable_job()
        if job is None:
            return False
        sig = sig or self._readable_sig()
        try:
            _write_from_disk(job)
        except Exception:
            diag.swallowed()
            return False
        self._rd_done = sig
        diag.activity("readable_written")
        return job["folder"]

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
