"""Update packs on the build PC (2.76.0).

  python tools\\make_update.py --new-key _local_sandbox\\keys\\update_signing_key.txt
      Make the publisher's signing key (once). Prints the public key for updatepack.PUBLIC_KEYS. The key file stays on
      the build PC: never in GitHub, never in a package. Back it up somewhere only you can reach.
  python tools\\make_update.py --manifest dist\\Stationkeeper --program Stationkeeper --edition us
      Write _internal\\program_manifest.json for a finished build (build.ps1 does this before zipping).
  python tools\\make_update.py --pack dist\\Stationkeeper --key <key file> --out Stationkeeper_US_Update_2.77.0.skupdate
      Write the signed update pack: every program file that differs from any release since 2.76.0 (tools\\manifests\\),
      and save this release's manifest there for the next pack. With no earlier release, only the manifest is saved.
"""
import argparse, glob, json, os, re, secrets, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
import updatepack as U  # noqa: E402

MANIFESTS = os.path.join(HERE, "manifests")


def app_version():
    with open(os.path.join(ROOT, "app_gui.py"), encoding="utf-8") as f:
        m = re.search(r'^APP_VERSION = "([0-9.]+)"', f.read(), re.M)
    return m.group(1)


def earlier_manifests(program, version, folder=MANIFESTS):
    out = []
    for p in glob.glob(os.path.join(folder, f"{program}-*.json")):
        with open(p, encoding="utf-8") as f:
            m = json.load(f)
        v = U.vtuple(m.get("version", "0"))
        if m.get("program") == program and U.vtuple(U.FIRST) <= v < U.vtuple(version):
            out.append(m)
    return sorted(out, key=lambda m: U.vtuple(m["version"]))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--new-key")
    ap.add_argument("--public")
    ap.add_argument("--manifest")
    ap.add_argument("--pack")
    ap.add_argument("--program")
    ap.add_argument("--edition", default="us")
    ap.add_argument("--version")
    ap.add_argument("--key")
    ap.add_argument("--out")
    ap.add_argument("--notes", default="")
    ap.add_argument("--always", nargs="*", default=[])
    ap.add_argument("--manifests", default=MANIFESTS)
    ap.add_argument("--no-save", action="store_true")
    a = ap.parse_args(argv)
    import edsign
    if a.new_key:
        if os.path.exists(a.new_key):
            print("REFUSED: a key file is already there; a new key would orphan every copy that trusts the old one.")
            return 1
        os.makedirs(os.path.dirname(os.path.abspath(a.new_key)), exist_ok=True)
        seed = secrets.token_bytes(32)
        with open(a.new_key, "w", encoding="ascii") as f:
            f.write(seed.hex() + "\n")
        print("PUBLIC KEY " + edsign.public_key(seed).hex())
        return 0
    if a.public:
        print("PUBLIC KEY " + edsign.public_key(U.load_secret(a.public)).hex())
        return 0
    version = a.version or app_version()
    if a.manifest:
        program = a.program or next(p for p in U.PROGRAMS[::-1] if os.path.isfile(os.path.join(a.manifest, p + ".exe")))
        m = U.write_manifest(a.manifest, program, version, a.edition)
        print(f"MANIFEST {program} {version}: {len(m['files'])} program files")
        return 0
    if a.pack:
        m = U.read_manifest(a.pack)
        if m is None:
            print("REFUSED: the build has no program manifest (run --manifest first)")
            return 1
        secret = U.load_secret(a.key)
        if edsign.public_key(secret).hex() not in U.PUBLIC_KEYS:
            print("REFUSED: this key is not one of the public keys in updatepack.PUBLIC_KEYS")
            return 1
        earlier = earlier_manifests(m["program"], m["version"], a.manifests)
        if earlier:
            info = U.make_pack(a.pack, a.out, secret, earlier, notes=a.notes, always=a.always)
            n = sum(x["size"] for x in info["payload"].values())
            print(f"UPDATE PACK {a.out}: {len(info['payload'])} files, {n / 1024 / 1024:.1f} MB, for copies from "
                  f"{', '.join(info['from_versions'])}")
        else:
            print(f"No update pack: {m['version']} is the first version that installs update packs.")
        if not a.no_save:
            os.makedirs(a.manifests, exist_ok=True)
            with open(os.path.join(a.manifests, f"{m['program']}-{m['version']}.json"), "w", encoding="utf-8", newline="\n") as f:
                json.dump(m, f, indent=1, sort_keys=True)
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
