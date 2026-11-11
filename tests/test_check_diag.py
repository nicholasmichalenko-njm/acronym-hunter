"""The build's logging check (tools/check_diag.py) runs in the suite too, so a log call that carries data stops here
and not at the end of a PC build (4.4.0: two count names in Drafts stopped the build)."""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run():
    p = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "check_diag.py")], capture_output=True, text=True, cwd=ROOT)
    assert p.returncode == 0, p.stdout + p.stderr
    print("ok test_check_diag")


if __name__ == "__main__":
    run()
