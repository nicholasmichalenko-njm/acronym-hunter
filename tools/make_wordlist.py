"""Builds assets\\common_words.txt from SCOWL (Spell Checker Oriented Word Lists, Kevin Atkinson, US; permissive license).

Only 2-6 letter lowercase words are kept: those are the only words the abbreviation rule can confuse with "abc."
Levels 10-50 of the English and American word lists = common words. Used so an ordinary word ending a sentence
("award.") is not reported as an abbreviation.
  python tools\\make_wordlist.py <path to scowl-2020.12.07\\final>
"""
import os
import re
import sys

final = sys.argv[1]
words = set()
for name in os.listdir(final):
    m = re.match(r"(english|american)-words\.(\d+)$", name)
    if m and int(m.group(2)) <= 50:
        for w in open(os.path.join(final, name), encoding="latin-1"):
            w = w.strip()
            if re.fullmatch(r"[a-z]{2,6}", w):
                words.add(w)
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "common_words.txt")
header = """# Common English words of 2-6 letters, from SCOWL 2020.12.07 (english/american-words levels 10-50).
# SCOWL: Copyright 2000-2018 by Kevin Atkinson. Permission to use, copy, modify, distribute and sell these word
# lists, the associated scripts, the output created from the scripts, and its documentation for any purpose is
# hereby granted without fee, provided that the above copyright notice appears in all copies and that both that
# copyright notice and this permission notice appear in supporting documentation. Kevin Atkinson makes no
# representations about the suitability of this array for any purpose. It is provided "as is" without express or
# implied warranty. (Full notice and component credits: http://wordlist.aspell.net/scowl-readme/)
"""
with open(out, "w", encoding="utf-8", newline="\n") as f:
    f.write(header + "\n".join(sorted(words)) + "\n")
print(f"{len(words)} words -> {out}")
