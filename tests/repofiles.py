"""3.38.1 the program's own Python files, as git sees them (tracked, or new and not ignored), so build output, venvs and
bundled packages on the build PC are never measured. Without git: a walk that skips those folders."""
import os, subprocess


def py_files(root, skip_dirs):
    """[(path relative to root with /, absolute path)] of the program's .py files outside skip_dirs."""
    rel = None
    try:
        r = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "*.py"], cwd=root,
                           capture_output=True, text=True, timeout=60)
        if r.returncode == 0 and r.stdout:
            rel = [p for p in r.stdout.split("\0") if p]
    except (OSError, subprocess.SubprocessError):
        rel = None
    if rel is None:
        rel = []
        for d, ds, fs in os.walk(root):
            ds[:] = [x for x in ds if x not in skip_dirs and not x.startswith((".", "dist", "build"))]
            rel += [os.path.relpath(os.path.join(d, f), root).replace(os.sep, "/") for f in fs if f.endswith(".py")]
    out = []
    for p in sorted(set(rel)):
        parts = p.split("/")
        if any(x in skip_dirs or x.startswith(".") for x in parts[:-1]):
            continue
        a = os.path.join(root, *parts)
        if os.path.isfile(a):
            out.append((p, a))
    return out
