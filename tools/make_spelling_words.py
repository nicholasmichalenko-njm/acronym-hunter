"""Builds assets\\spelling_words.txt (3.54.0) from the English Speller Database (SCOWL, Kevin Atkinson, US; permissive
license in the file): data/scowl-pre.txt from github.com/en-wl/wordlist, American spellings, sizes up to 70, with their
inflections. Reads the data file only: python tools/make_spelling_words.py <scowl-pre.txt> assets/spelling_words.txt"""
import os, re, sys

src, dst = sys.argv[1], sys.argv[2]
words = set()
with open(src, encoding="utf-8") as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        parts = line.split(": ")
        m = re.match(r"(\d+)", parts[0])
        if not m or int(m.group(1)) > 70:
            continue
        rest = parts[1:]
        if rest and re.fullmatch(r"(?:[A-Z][vV]?\s*)+", rest[0]):
            if not any(d.startswith("A") for d in rest[0].split()):
                continue
            rest = rest[1:]
        if not rest:
            continue
        head = rest[0].split(" <")[0].split(" {")[0].strip()
        cands = [head] + ([x.strip() for x in rest[1].split(",")] if len(rest) > 1 else [])
        for w in cands:
            if w and w != "-" and re.fullmatch(r"[A-Za-z][A-Za-z'\-]*", w):
                words.add(w.lower())
check = ["program", "manager", "reliability", "validated", "engineers", "telemetry", "payload", "colour", "color"]
print(len(words), [w for w in check if w not in words])
with open(dst, "w", encoding="utf-8") as f:
    f.write("# English words for Technical Edit's spelling check (3.54.0), from the English Speller Database (SCOWL), American\n"
            "# spellings, sizes up to 70, with their inflections. Copyright 2000-2026 by Kevin Atkinson. Permission to use, copy,\n"
            "# modify, distribute, and sell any part of the English Speller Database (ESDB, previously known as SCOWLv2), or word\n"
            "# lists created from it, is hereby granted without fee, provided that the above copyright notice appears in all copies\n"
            "# and that both the above copyright notice and this notice appear in supporting documentation. Kevin Atkinson makes no\n"
            "# representations about the suitability of this database for any purpose. It is provided \"as is\" without express or\n"
            "# implied warranty.\n")
    for w in sorted(words):
        f.write(w + "\n")
print(os.path.getsize(dst))
