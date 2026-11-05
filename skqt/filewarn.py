"""3.57.0: what lowers trust in a file just read (filesafety.warnings), said in the status bar and kept for the page."""
import os

import filesafety as FS


def say(host, paths):
    """Each file's warnings as 'name: sentence'; the first two go to the status bar. Returns them all."""
    from .modes import settings
    me = (settings() or {}).get("my_name", "")
    out = []
    for p in paths or []:
        try:
            out += [f"{os.path.basename(p)}: {w}" for w in FS.warnings(p, me)]
        except Exception:  # noqa: BLE001
            pass
    if out:
        host.status("  ".join(out[:2]) + (f"  (and {len(out) - 2} more)" if len(out) > 2 else ""))
    host.last_file_warnings = out
    return out
