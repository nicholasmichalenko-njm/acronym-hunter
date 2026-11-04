"""3.38.1 the house rules, checked on every build (CLAUDE.md lists them):
1. Offline only: no module in the program's own code imports networking (socket, ssl, urllib.request, http.client,
   requests and the like). The one exception is the engine's network guard, which imports socket and urllib.request
   to switch them off; it is named below with its reason.
2. No emoji in the program's text: no pictographic emoji (U+1F000 to U+1FAFF) and no emoji presentation selector
   (U+FE0F) in any string. Typographic marks (check marks, Word bullet characters) are plain text and allowed.
3. Every package in requirements.txt is on tools/approved_packages.csv with its use, editions, license and origin note;
   a package for the legacy edition only is left out of US editions in Stationkeeper.spec.
4. The approved list has no package requirements.txt does not ask for (no stale approvals)."""
import ast, csv, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {"tests", "tools", "prototypes", "training_kit_src", "training_kit_doctr_src", "venv", "build", "dist", ".git",
             "_local_sandbox", "test_samples", "__pycache__", "vendor", "logs", "internal_builds", "kit_build", "training_kit"}
NET = {"socket", "ssl", "urllib.request", "urllib3", "requests", "http.client", "http.server", "ftplib", "smtplib", "poplib",
       "imaplib", "telnetlib", "xmlrpc.client", "xmlrpc.server", "socketserver", "httpx", "aiohttp", "websocket", "websockets"}
NET_ALLOWED = {("app_gui.py", "socket"): "the network guard: replaces socket.connect and getaddrinfo with a refusal",
               ("app_gui.py", "urllib.request"): "the network guard: replaces urlopen and urlretrieve with a refusal"}
EMOJI = re.compile("[\U0001F000-\U0001FAFF️]")
EMOJI_ALLOWED = {("volcheck.py", "_placeholder"): "strips a warning sign older versions saved before a stand-in text"}

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info if not ok else "")


def app_files():
    for d, ds, fs in os.walk(ROOT):
        ds[:] = [x for x in ds if x not in SKIP_DIRS and not x.startswith(".")]
        for f in fs:
            if f.endswith(".py"):
                p = os.path.join(d, f)
                yield os.path.relpath(p, ROOT).replace(os.sep, "/"), p


net_bad, emoji_bad, n_files = [], [], 0
for rel, p in app_files():
    n_files += 1
    tree = ast.parse(open(p, encoding="utf-8").read(), rel)
    funcs = {}
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for n in ast.walk(fn):
                funcs.setdefault(id(n), fn.name)
    for n in ast.walk(tree):
        mods = []
        if isinstance(n, ast.Import):
            mods = [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            mods = [n.module] + [f"{n.module}.{a.name}" for a in n.names]
        for m in mods:
            if (m in NET or m.split(".")[0] in ("requests", "urllib3", "httpx", "aiohttp")) and (rel, m) not in NET_ALLOWED:
                net_bad.append(f"{rel}:{n.lineno} imports {m}")
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and EMOJI.search(n.value):
            if (rel, funcs.get(id(n), "")) not in EMOJI_ALLOWED:
                emoji_bad.append(f"{rel}:{n.lineno} {n.value[:40]!r}")
check(f"the program's own code was read ({n_files} files)", n_files > 150, n_files)
check("1. offline only: no networking import outside the network guard", not net_bad, net_bad[:8])
check("1. the network guard is still there (its exceptions are in use)", all(
    any(isinstance(x, ast.Import) and any(a.name == m for a in x.names) for x in ast.walk(ast.parse(open(os.path.join(ROOT, f), encoding="utf-8").read())))
    for f, m in NET_ALLOWED))
check("2. no emoji in the program's text", not emoji_bad, emoji_bad[:8])

req = []
for line in open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8"):
    line = line.split("#")[0].strip()
    if line:
        req.append(re.split(r"[=<>!~\[; ]", line, 1)[0])
norm = lambda s: re.sub(r"[-_.]+", "-", s).lower()
rows = list(csv.DictReader(open(os.path.join(ROOT, "tools", "approved_packages.csv"), encoding="utf-8")))
approved = {norm(r["package"]): r for r in rows}
missing = [p for p in req if norm(p) not in approved]
check("3. every package in requirements.txt is approved", req and not missing, missing)
check("3. every approval says its use, editions, license and origin", all(r["use"] in ("app", "build") and r["editions"] in
      ("all", "build only", "legacy only") and r["license"].strip() and r["origin_note"].strip() for r in rows),
      [r["package"] for r in rows if not (r["license"].strip() and r["origin_note"].strip())])
spec = open(os.path.join(ROOT, "Stationkeeper.spec"), encoding="utf-8").read()
m = re.search(r"_edition_excludes = \((\[[^\]]*\])", spec, re.S)
excl = set(ast.literal_eval(m.group(1))) if m else set()
IMPORT_NAME = {"rapidocr-onnxruntime": "rapidocr_onnxruntime", "pyyaml": "yaml"}
legacy = [norm(r["package"]) for r in rows if r["editions"] == "legacy only"]
not_out = [p for p in legacy if IMPORT_NAME.get(p, p.replace("-", "_")) not in excl]
check("3. a legacy-only package is left out of US editions", m and not not_out, not_out)
stale = [r["package"] for r in rows if norm(r["package"]) not in {norm(p) for p in req}]
check("4. no stale approvals: every approved package is still asked for", not stale, stale)

n = sum(checks)
print(f"HOUSE RULES {'PASS' if n == len(checks) else 'FAIL'} ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
