"""D1 (2026-11-18): no Qt test ends with a bare os._exit. On Windows a process that has made the main window and then
calls os._exit crashes while it unloads its libraries (exit 0xC0000005) after every check passed: qt_homes4510 did so
in 5 runs of 5 on the build PC, and stopped three of four builds of 4.56.1. hangguard.end (3.37.0) ends a test without
that unload work, and a normal sys.exit was clean in 6 runs of 6. This check keeps the bare form out of tests/qt_*.py."""
import ast, glob, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
bad = []
for path in sorted(glob.glob(os.path.join(HERE, "qt_*.py"))):
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "_exit"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "os"):
            bad.append(f"{os.path.basename(path)}:{node.lineno}")
ok = not bad
print("PASS" if ok else "FAIL", "no Qt test ends with a bare os._exit; use hangguard.end", "" if ok else bad)
print("TEST ENDINGS PASS" if ok else "TEST ENDINGS FAIL")
sys.exit(0 if ok else 1)
