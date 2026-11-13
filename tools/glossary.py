"""4.20.0: one word for one thing (claude/stationkeeper-glossary-4.20.md). Finds retired words in the text the program
shows: every string in the program's files that still uses a word the glossary retired. A string kept on purpose (a
saved name, a file's column, a word used in its plain meaning) is listed in tools/glossary_allow.json with its reason.

    python tools/glossary.py                 every program file; prints file:line: [rule] the string; exit 1 if any
    python tools/glossary.py skqt/assign.py  only these files
    python tools/glossary.py --count         the count per rule and file

tests/test_glossary4200.py runs this in the suite: a retired word that comes back stops the release."""
import ast
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOW = os.path.join(ROOT, "tools", "glossary_allow.json")
SKIP_DIRS = {"tests", "tools", ".git", "_local_sandbox", "build", "dist", "__pycache__", "test_samples", "prototypes",
             "training_kit_src", "claude", "docs"}
# What's new keeps each release's words as they were; the Trainer is its own program with its own steps
SKIP_FILES = {"supportfile.py", "trainerkit.py", "skqt_training.py", "formats.py", os.path.join("skqt", "trainingwin.py")}

# (rule, what to say instead, the retired use, the uses that stay)
RULES = [
    ("review", "Shred (the page), the shred (its content)",
     r"\bReview\b|\bthe review\b",
     r"Color Reviews?|Impact Review|Design Review|Review packet|the review packet|Review > |Review (it |them|the |each |every |"
     r"missing|changes|by hand)|the review (dates|comments)"),
    ("library", "Documents (the page); the Library stays the name of the effort's folders on disk",
     r"\bLibrary\b",
     r"(Effort|Team|[Tt]emplate|Production|Styles|Parts|Bidders|SK) Library|Library (folders?|files|item|content|Context|moves|parts)"),
    ("production-menu", "Team > ...", r"Production > ", r"$^"),
    ("global", "Company Standards (the column, the value); Make it a standard",
     r"\b[Gg]lobal(ly)?\b", r"$^"),
    ("sentence", "piece (anything in the shred); requirement only once a piece is typed Requirement",
     r"\b[Ss]entences?\b|\b[Ss]entence\(s\)", r"$^"),
    ("sorted", "shredded (a piece that has a type); placed (a piece in a section)",
     r"\b(not |all )?sorted\b", r"sorted (by|in|on|into)\b"),
    ("acronyms-page", "Acronyms (every page name; 4.29.0, the naming plan); Acronym Finder, Acronym List",
     r"Acros (&|&&) Abs|[Aa]cros and abs", r"$^"),
    ("volume-parts", "sections (what a volume is made of); Quick Parts and Standards > Parts keep their names",
     r"[Pp]arts and numbering|usual parts", r"$^"),
    ("compare-page", "Amendments (the page; 4.29.0)",
     r"\bCompare\b|\b(in|Open|>) Changes\b", r"Compare (two|the two|with|each|it|them)\b"),
    ("names-4290", "Overview (was Dashboard); Submission Checklist (was Rules & Dates); Crosswalk (was L to M); Themes (was Theme tags)",
     r"\bDashboard\b|Rules (&|&&) Dates|\bL to M\b|Theme tags", r"$^"),
]
RULES = [(k, say, re.compile(bad), re.compile(ok)) for k, say, bad, ok in RULES]


def files(only=None):
    if only:
        return [os.path.relpath(os.path.abspath(p), ROOT) for p in only]
    try:                                    # the program's own files: what git tracks (a build PC also holds dist folders,
        import subprocess                   # sandboxes and other programs' code beside them)
        got = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True, timeout=60)
        tracked = [os.path.normpath(x) for x in got.stdout.splitlines() if x.strip()] if got.returncode == 0 else []
    except (OSError, ValueError, subprocess.SubprocessError):
        tracked = []
    if tracked:
        return sorted(rel for rel in tracked if rel not in SKIP_FILES and not (set(rel.split(os.sep)[:-1]) & SKIP_DIRS))
    out = []
    for d, ds, fs in os.walk(ROOT):
        ds[:] = sorted(x for x in ds if x not in SKIP_DIRS and not x.startswith(("dist", "build", "_", ".")))
        for f in sorted(fs):
            rel = os.path.relpath(os.path.join(d, f), ROOT)
            if f.endswith(".py") and rel not in SKIP_FILES:
                out.append(rel)
    return out


def strings(rel):
    """Every string the file holds apart from its docstrings: (line, text)."""
    try:
        tree = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace").read())
    except SyntaxError:
        return []
    doc = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and n.body:
            b = n.body[0]
            if isinstance(b, ast.Expr) and isinstance(getattr(b, "value", None), ast.Constant) and isinstance(b.value.value, str):
                doc.add(id(b.value))
    return [(n.lineno, n.value) for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in doc]


def allowed():
    """{file: {rule: [the start of a kept string]}}"""
    out = {}
    for p in (ALLOW, os.environ.get("GLOSSARY_ALLOW_EXTRA", "")):      # the second: a sweep's own list, before it is merged
        try:
            for f, rules in json.load(open(p, encoding="utf-8")).items():
                for rule, ents in rules.items():
                    out.setdefault(f, {}).setdefault(rule, []).extend(ents)
        except (OSError, ValueError):
            pass
    return out


def hits(only=None):
    """[(file, line, rule, say, string)] for every retired word not kept on purpose."""
    keep, out = allowed(), []
    for rel in files(only):
        k = keep.get(rel.replace(os.sep, "/"), {})
        for line, s in strings(rel):
            for rule, say, bad, ok in RULES:
                if not bad.search(ok.sub("", s)):
                    continue
                if any(s.startswith(e["s"]) for e in k.get(rule, [])):
                    continue
                out.append((rel, line, rule, say, s))
    return out


def main(argv):
    count = "--count" in argv
    only = [a for a in argv if not a.startswith("--")]
    got = hits(only or None)
    if count:
        by = {}
        for rel, _l, rule, _s, _t in got:
            by.setdefault(rule, {}).setdefault(rel, 0)
            by[rule][rel] += 1
        for rule, d in by.items():
            print(rule, sum(d.values()), "in", len(d), "file(s)")
    else:
        for rel, line, rule, _say, s in got:
            print(f"{rel}:{line}: [{rule}] {s[:160]!r}")
    print(f"{len(got)} retired word(s)")
    return 1 if got else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
