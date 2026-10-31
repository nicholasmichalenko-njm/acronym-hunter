"""3.0.4 custom dictionaries (customdict.py): named dictionaries kept in the config folder, words unique and sorted, no
spaces inside a word, import of Word .dic files in UTF-16 (with or without a byte order mark), UTF-8 and the Windows code
page, export as Word writes it (UTF-16 LE with a byte order mark, CRLF), the dated export name and the dated copy kept,
and the effort's approved acronyms."""
import os, sys, tempfile, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import customdict as CD
import effort as E

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


tmp = tempfile.mkdtemp()
cfg = os.path.join(tmp, "config"); data = os.path.join(tmp, "data")
s = CD.Store(cfg)
check("no dictionaries to start", s.dicts == [] and not os.path.exists(s.path))
a = s.add("Sierra Space Custom", ["CDRL", "Dream Chaser", "cdrl", "CDRL", "  LIFE  "])
check("a new dictionary: words unique (case kept), sorted, none with a space", s.get(a)["words"] == ["CDRL", "cdrl", "LIFE"], s.get(a)["words"])
check("a name already used is refused", s.add("sierra space custom") == "" and s.add("  ") == "")
check("adding words counts only the new ones", s.add_words(a, ["Tenacity", "LIFE", "ISS"]) == 2)
check("removing words", s.remove_words(a, ["cdrl"]) == 1 and "cdrl" not in s.get(a)["words"])
check("changing a spelling; one with a space is refused", s.replace_word(a, "ISS", "ISS-1") and not s.replace_word(a, "LIFE", "two words"))
check("kept in the config folder (the backups carry it)", CD.Store(cfg).get(a)["words"] == s.get(a)["words"]
      and os.path.isfile(os.path.join(cfg, CD.FILE)))
b = s.add("Program names")
check("renaming; to a used name is refused", s.rename(b, "Programs") and not s.rename(b, "Sierra Space Custom"))
# imports
words = ["Zeta", "alpha", "Beta"]
for enc, name in (("utf-16", "u16.dic"), ("utf-8-sig", "u8bom.dic"), ("utf-8", "u8.dic"), ("cp1252", "ansi.dic")):
    with open(os.path.join(tmp, name), "w", encoding=enc, newline="\r\n") as f:
        f.write("#LID 1033\n" + "\n".join(words + ["café"]) + "\n\n")
    got = CD.read_dic(os.path.join(tmp, name))
    check(f"import a .dic in {enc}", got == words + ["café"], got)
with open(os.path.join(tmp, "u16le.dic"), "wb") as f:
    f.write("One\r\nTwo\r\n".encode("utf-16-le"))
check("import UTF-16 with no byte order mark", CD.read_dic(os.path.join(tmp, "u16le.dic")) == ["One", "Two"])
# export
p = os.path.join(tmp, "out.dic")
n = s.export(a, p, data)
raw = open(p, "rb").read()
check("export as Word writes it: UTF-16 LE, byte order mark, CRLF, sorted", raw.startswith(b"\xff\xfe")
      and raw[2:].decode("utf-16-le") == "".join(w + "\r\n" for w in s.get(a)["words"]) and n == len(s.get(a)["words"]))
check("... reads back the same", CD.read_dic(p) == s.get(a)["words"])
kept = os.listdir(os.path.join(data, CD.EXPORTS))
check("... and a dated copy is kept in the data folder", len(kept) == 1 and kept[0].endswith(" out.dic"), kept)
check("... the export is noted", s.get(a)["exports"][-1]["words"] == n and s.get(a)["exports"][-1]["file"] == "out.dic")
d = datetime.date(2026, 10, 30)
check("the export name: the dictionary and the date", s.export_name(a, when=d) == "Sierra Space Custom 2026-10-30.dic")
check("... with the effort's name when chosen", s.export_name(a, "Kestrel", when=d) == "Sierra Space Custom Kestrel 2026-10-30.dic")
# the effort's acronyms
L = E.EffortList(os.path.join(tmp, "K.xlsx"), "K")
L.rows = {"CDRL": {"Status": "Approved"}, "IMS": {"Status": "Proposed"}, "TBD": {"Status": "Rejected"}}
check("the effort's approved acronyms", CD.from_effort(L) == ["CDRL"] and CD.from_effort(L, include_proposed=True) == ["CDRL", "IMS"])
check("removing a dictionary", s.remove(b) and CD.Store(cfg).get(b) is None)
t = sum(checks)
print(f"CUSTOM DICTIONARIES {'PASS' if t == len(checks) else 'FAIL'} ({t}/{len(checks)})")
sys.exit(0 if t == len(checks) else 1)
