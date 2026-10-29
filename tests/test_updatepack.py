"""2.76.0 update packs: Ed25519 (RFC 8032 vectors); every build lists its program files; a pack holds only the files
that changed since 2.76.0 and is signed; it installs only when the signature matches a publisher key, every path is a
program file, it is for this program, newer than this copy and holds what this copy lacks; config, the database and
efforts are never touched; a pack serves a copy that skipped a version; a failure part-way puts everything back, and so
does the next start after a crash; Undo last update brings the version before back; Check program files finds
changed, missing and planted files; tools/make_update.py builds the pack and keeps the manifests."""
import json, os, shutil, sys, tempfile, zipfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import edsign
import updatepack as U

checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


def raises(fn, *words):
    try:
        fn()
    except U.UpdateError as e:
        return all(w in str(e) for w in words) or str(e)
    return False


# RFC 8032 section 7.1, tests 1-3
V = [("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60", "", "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
     ("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb", "72", "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
     ("c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7", "af82", "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a")]
check("Ed25519 signs the RFC 8032 test vectors", all(edsign.sign(bytes.fromhex(s), bytes.fromhex(m)).hex() == sig for s, m, sig in V))
s0 = bytes.fromhex(V[0][0])
check("and verifies them; one changed byte fails", all(edsign.verify(edsign.public_key(bytes.fromhex(s)), bytes.fromhex(m), bytes.fromhex(sig))
                                                         for s, m, sig in V)
      and not edsign.verify(edsign.public_key(s0), b"x", bytes.fromhex(V[0][2])) and not edsign.verify(b"1" * 32, b"", b"2" * 64))
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    ok = all(Ed25519PrivateKey.from_private_bytes(bytes([i]) * 32).sign(b"pack %d" % i) == edsign.sign(bytes([i]) * 32, b"pack %d" % i)
             for i in range(5))
    check("matches an independent Ed25519 (cryptography)", ok)
except ImportError:
    pass

KEY = bytes(range(32))
U.PUBLIC_KEYS = [edsign.public_key(KEY).hex()]
OTHER = bytes(range(1, 33))
tmp = tempfile.mkdtemp()


def build(folder, version, files):
    """A built program folder: the exe, _internal files, the documents, and the shipped data."""
    shutil.rmtree(folder, ignore_errors=True)
    for rel, text in files.items():
        p = os.path.join(folder, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w", encoding="utf-8").write(text)
    os.makedirs(os.path.join(folder, "config"), exist_ok=True)
    open(os.path.join(folder, "config", "app_settings.json"), "w").write("{}")
    open(os.path.join(folder, "acronym_database.csv"), "w").write("Term\nSOW\n")
    return U.write_manifest(folder, "Stationkeeper", version)


F76 = {"Stationkeeper.exe": "exe 2.76", "_internal/python311.dll": "python", "_internal/qt/Qt6Core.dll": "qt core",
       "_internal/base_library.zip": "lib 2.76", "_internal/old/gone.pyd": "old module", "README.txt": "readme 2.76"}
F77 = dict(F76, **{"Stationkeeper.exe": "exe 2.77", "_internal/base_library.zip": "lib 2.77", "README.txt": "readme 2.77"})
F78 = dict(F77, **{"Stationkeeper.exe": "exe 2.78", "_internal/new/added.pyd": "new module"})
del F78["_internal/old/gone.pyd"]
M76 = build(os.path.join(tmp, "b76"), "2.76.0", F76)
M77 = build(os.path.join(tmp, "b77"), "2.77.0", F77)
M78 = build(os.path.join(tmp, "b78"), "2.78.0", F78)
check("the manifest lists the program files, never config or the database", set(M76["files"]) == set(F76)
      and not any(r.startswith("config") or r == "acronym_database.csv" for r in M76["files"]))
P77 = os.path.join(tmp, "Stationkeeper_US_Update_2.77.0.skupdate")
info = U.make_pack(os.path.join(tmp, "b77"), P77, KEY, [M76])
check("a pack holds only the files changed since 2.76.0, and the manifest", sorted(info["payload"]) ==
      sorted(["Stationkeeper.exe", "_internal/base_library.zip", "README.txt", U.MANIFEST]), sorted(info["payload"]))
P78 = os.path.join(tmp, "Stationkeeper_US_Update_2.78.0.skupdate")
info78 = U.make_pack(os.path.join(tmp, "b78"), P78, KEY, [M76, M77])
check("a cumulative pack: anything changed since any release from 2.76.0", sorted(info78["payload"]) ==
      sorted(["Stationkeeper.exe", "_internal/base_library.zip", "README.txt", "_internal/new/added.pyd", U.MANIFEST]),
      sorted(info78["payload"]))
check("a pack reads back with its signature", U.read_pack(P77)["version"] == "2.77.0")

# the installed copy (2.76.0) with the user's data
APP = os.path.join(tmp, "app")
shutil.copytree(os.path.join(tmp, "b76"), APP)
open(os.path.join(APP, "acronym_database.csv"), "w").write("Term\nSOW\nCDR\nMY OWN ROW\n")
open(os.path.join(APP, "config", "app_settings.json"), "w").write('{"mine": true}')
os.makedirs(os.path.join(APP, "config", "efforts")); open(os.path.join(APP, "config", "efforts", "Heron.json"), "w").write("{}")


def snapshot(d):
    out = {}
    for root, _dirs, names in os.walk(d):
        for nm in names:
            p = os.path.join(root, nm)
            rel = os.path.relpath(p, d).replace("\\", "/")
            if not rel.startswith(U.UPDATE_DIR + "/"):
                out[rel] = open(p, "rb").read()
    return out


before = snapshot(APP)
# ------------------------------------------------ refused packs (nothing changes)
check("not a pack", raises(lambda: U.check(os.path.join(tmp, "nope.skupdate"), APP, "Stationkeeper"), "not a Stationkeeper update pack"))
bad = os.path.join(tmp, "other_key.skupdate"); U.make_pack(os.path.join(tmp, "b77"), bad, OTHER, [M76])
check("signed by someone else: refused", raises(lambda: U.check(bad, APP, "Stationkeeper"), "not signed by the Stationkeeper publisher"))


def rewrite(src, dst, change):
    with zipfile.ZipFile(src) as z:
        items = {n: z.read(n) for n in z.namelist()}
    change(items)
    with zipfile.ZipFile(dst, "w") as z:
        for n, b in items.items():
            z.writestr(n, b)
    return dst


t1 = rewrite(P77, os.path.join(tmp, "t1.skupdate"), lambda it: it.__setitem__("update_info.json", it["update_info.json"].replace(b"2.77.0", b"2.79.0")))
check("one changed byte in the list: refused", raises(lambda: U.check(t1, APP, "Stationkeeper"), "changed after it was made"))
t2 = rewrite(P77, os.path.join(tmp, "t2.skupdate"), lambda it: it.__setitem__("payload/Stationkeeper.exe", b"evil 2.77"))
check("a payload file swapped (same size): caught when unpacking, nothing installed",
      raises(lambda: U.stage(U.check(t2, APP, "Stationkeeper"), t2, APP), "does not match its signed checksum")
      and snapshot(APP) == before)
t3 = rewrite(P77, os.path.join(tmp, "t3.skupdate"), lambda it: it.__setitem__("payload/../../evil.exe", b"x"))
check("an extra file in the zip (a path out of the folder): refused", raises(lambda: U.check(t3, APP, "Stationkeeper"), "does not list"))


def signed_info(change):
    """A pack whose signed list itself names a forbidden path (the publisher's key, so only the path rules stop it)."""
    with zipfile.ZipFile(P77) as z:
        items = {n: z.read(n) for n in z.namelist()}
    inf = json.loads(items["update_info.json"]); change(inf, items)
    data = json.dumps(inf, indent=1, sort_keys=True).encode()
    items["update_info.json"] = data; items["update_info.sig"] = U.sign_bytes(KEY, data).hex().encode()
    p = os.path.join(tmp, "signed_bad.skupdate")
    with zipfile.ZipFile(p, "w") as z:
        for n, b in items.items():
            z.writestr(n, b)
    return p


def to_db(inf, items):
    meta = {"sha256": "0" * 64, "size": 3}
    inf["files"]["acronym_database.csv"] = meta; inf["payload"]["acronym_database.csv"] = meta
    items["payload/acronym_database.csv"] = b"bad"


def to_config(inf, items):
    meta = {"sha256": "0" * 64, "size": 3}
    inf["files"]["config/app_settings.json"] = meta; inf["payload"]["config/app_settings.json"] = meta
    items["payload/config/app_settings.json"] = b"bad"


def traversal(inf, items):
    meta = {"sha256": "0" * 64, "size": 3}
    inf["files"]["_internal/../../x.exe"] = meta; inf["payload"]["_internal/../../x.exe"] = meta
    items["payload/_internal/../../x.exe"] = b"bad"


check("even signed: the database is not a program file", raises(lambda: U.check(signed_info(to_db), APP, "Stationkeeper"), "not a program file"))
check("even signed: config is not a program file", raises(lambda: U.check(signed_info(to_config), APP, "Stationkeeper"), "not a program file"))
check("even signed: no path leaves the folder", raises(lambda: U.check(signed_info(traversal), APP, "Stationkeeper"), "outside the program folder"))
check("drive letters, reserved names and backslash tricks are refused", all(raises(lambda r=r: U.norm(r)) for r in
      ("C:/Windows/x.dll", "/abs", "_internal\\..\\x", "_internal/con.txt", "_internal/a /b", "_internal/./x", "")))
check("for the other program: refused", raises(lambda: U.check(P77, APP, "StationkeeperTraining"), "for Stationkeeper"))
noman = os.path.join(tmp, "noman"); shutil.copytree(os.path.join(tmp, "b76"), noman); os.remove(os.path.join(noman, *U.MANIFEST.split("/")))
check("a copy older than 2.76.0 (no manifest): download the full copy once", raises(lambda: U.check(P77, noman, "Stationkeeper"), "older than 2.76.0"))
mixed = os.path.join(tmp, "mixed"); shutil.copytree(os.path.join(tmp, "b76"), mixed)
open(os.path.join(mixed, "_internal", "python311.dll"), "w").write("someone changed this")
check("a copy whose files differ from 2.76.0: the pack lacks what it needs, refused with the reason",
      raises(lambda: U.check(P77, mixed, "Stationkeeper"), "does not hold 1 program file"))
check("nothing was changed by any refused pack", snapshot(APP) == before)

# ------------------------------------------------ a failure part-way puts everything back
plan = U.check(P77, APP, "Stationkeeper")
check("the plan: three files and the manifest to copy, the rest stay", sorted(plan["replace"]) ==
      sorted(["Stationkeeper.exe", "_internal/base_library.zip", "README.txt", U.MANIFEST]) and plan["keep"] == 3
      and plan["replace"][-1] == "Stationkeeper.exe", plan["replace"])
check("the summary says what happens", "from 2.76.0 to 2.77.0" in U.summary(plan) and "4 program file(s)" in U.summary(plan))
U.stage(plan, P77, APP)
check("stopped part-way: everything put back", raises(lambda: U.apply(plan, APP, fail_after=5), "put back") and snapshot(APP) == before)
# a crash part-way (the program ended): the next start puts it back
U.stage(plan, P77, APP)
try:
    U._swap(APP, {"kind": "update", "from": "2.76.0", "to": "2.77.0", "program": "Stationkeeper", "out": plan["replace"],
                  "in": plan["replace"], "new": "staged", "old": "backup"}, U._udir(APP, "staged"), U._udir(APP, "backup"), fail_after=6)
except OSError:
    pass
j = U.read_journal(APP); j["state"] = "applying"; U._journal(APP, j)           # as if the program ended before putting back
for rel in plan["replace"][:2]:                                                   # half moved again
    if os.path.isfile(os.path.join(APP, *rel.split("/"))):
        U._move(os.path.join(APP, *rel.split("/")), os.path.join(U._udir(APP, "backup"), *rel.split("/")))
check("a crash part-way: the next start puts it back", U.recover(APP) == "put back" and snapshot(APP) == before)

# ------------------------------------------------ install
U.recover(APP)
plan = U.check(P77, APP, "Stationkeeper")
U.stage(plan, P77, APP)
res = U.apply(plan, APP)
after = snapshot(APP)
check("installed: the program files are 2.77.0", after["Stationkeeper.exe"] == b"exe 2.77" and U.installed_version(APP) == "2.77.0"
      and after["_internal/base_library.zip"] == b"lib 2.77", res)
check("the user's database, settings and efforts are untouched", after["acronym_database.csv"] == before["acronym_database.csv"]
      and after["config/app_settings.json"] == b'{"mine": true}' and "config/efforts/Heron.json" in after)
check("Check program files: all match", (lambda r: not (r["changed"] or r["missing"] or r["extra"]) and r["ok"] == len(F77))(U.check_files(APP)))
check("the same pack again: already has it", raises(lambda: U.check(P77, APP, "Stationkeeper"), "already has version 2.77.0"))
# undo
u = U.undo(APP, "Stationkeeper")
check("Undo last update: 2.76.0 is back, data untouched", u == {"from": "2.77.0", "to": "2.76.0"} and snapshot(APP) == before, u)
check("undo once only", raises(lambda: U.undo(APP, "Stationkeeper"), "no update to undo"))
U.recover(APP)
# skipping a version: 2.76.0 straight to 2.78.0 (a file removed, one added)
plan = U.check(P78, APP, "Stationkeeper")
U.stage(plan, P78, APP); U.apply(plan, APP)
a78 = snapshot(APP)
check("2.76.0 straight to 2.78.0: added, removed, replaced", a78["Stationkeeper.exe"] == b"exe 2.78" and "_internal/new/added.pyd" in a78
      and "_internal/old/gone.pyd" not in a78 and not os.path.isdir(os.path.join(APP, "_internal", "old"))
      and a78["acronym_database.csv"] == before["acronym_database.csv"])
check("an older pack after that: refused (no downgrade)", raises(lambda: U.check(P77, APP, "Stationkeeper"), "older than this copy", "Undo last update"))
U.undo(APP, "Stationkeeper")
check("undo brings back the removed file and takes away the added one", snapshot(APP) == before)
U.recover(APP)
check("leftovers are cleared at start", not os.path.isdir(U._udir(APP, "staged")) and not os.path.isdir(U._udir(APP, "undone")))

# ------------------------------------------------ Check program files
open(os.path.join(APP, "_internal", "python311.dll"), "w").write("tampered")
os.remove(os.path.join(APP, "README.txt"))
open(os.path.join(APP, "_internal", "planted.dll"), "w").write("x")
r = U.check_files(APP)
check("Check program files: changed, missing and planted files", r["changed"] == ["_internal/python311.dll"] and r["missing"] == ["README.txt"]
      and r["extra"] == ["_internal/planted.dll"] and "Not part of this version (1)" in U.check_text(r), r)

# ------------------------------------------------ tools/make_update.py
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools"))
import make_update as MU
kf = os.path.join(tmp, "keys", "update_signing_key.txt")
check("a new key: made once, never overwritten", MU.main(["--new-key", kf]) == 0 and MU.main(["--new-key", kf]) == 1)
U.PUBLIC_KEYS = [edsign.public_key(U.load_secret(kf)).hex()]
md = os.path.join(tmp, "manifests")
check("the first release: no pack, its manifest kept", MU.main(["--pack", os.path.join(tmp, "b76"), "--key", kf, "--out", os.path.join(tmp, "x.skupdate"),
                                                               "--manifests", md]) == 0
      and not os.path.exists(os.path.join(tmp, "x.skupdate")) and os.path.isfile(os.path.join(md, "Stationkeeper-2.76.0.json")))
out = os.path.join(tmp, "y.skupdate")
check("the next release: a signed pack", MU.main(["--pack", os.path.join(tmp, "b77"), "--key", kf, "--out", out, "--manifests", md]) == 0
      and U.read_pack(out)["version"] == "2.77.0")
check("a key that is not built into the program: refused", MU.main(["--pack", os.path.join(tmp, "b77"), "--key", kf, "--out", out,
                                                                     "--manifests", md]) == 0 and (setattr(U, "PUBLIC_KEYS", ["00" * 32]) or True)
      and MU.main(["--pack", os.path.join(tmp, "b77"), "--key", kf, "--out", out, "--manifests", md]) == 1)
src = open(os.path.join(os.path.dirname(HERE), "updatepack.py"), encoding="utf-8").read()
check("the shipped program trusts exactly one publisher key", src.count('PUBLIC_KEYS = ["') == 1 and "PENDING" not in src)
shutil.rmtree(tmp, ignore_errors=True)
n = sum(checks)
print(f"UPDATE PACK PASS ({n}/{len(checks)})" if n == len(checks) else f"UPDATE PACK FAIL ({n}/{len(checks)})")
sys.exit(0 if n == len(checks) else 1)
