"""Second vulnerability source (2.22.0): check every Python package in the release SBOMs against the OSV database
(osv.dev, Google; covers PyPI advisories, GitHub advisories and more). Run on the build PC, which has internet; the app
itself never runs this and never connects to anything.

    venv\\Scripts\\python.exe tools\\osv_check.py Stationkeeper_US_SBOM.cdx.json Stationkeeper_US_Training_SBOM.cdx.json

Sends package names and versions only (public facts, the same as the published SBOM). Prints one line per package
with known advisories and exits 1 when any are found, 0 when none, 2 when OSV could not be reached.
"""
import json, sys, urllib.request, urllib.error

API = "https://api.osv.dev/v1/querybatch"


def packages(sbom_paths):
    seen = {}
    for p in sbom_paths:
        doc = json.load(open(p, encoding="utf-8"))
        for c in doc.get("components", []):
            purl = c.get("purl", "")
            if purl.startswith("pkg:pypi/") and c.get("version"):
                seen[(c["name"].lower(), c["version"])] = purl
    return seen


def query(pkgs):
    body = {"queries": [{"package": {"name": n, "ecosystem": "PyPI"}, "version": v} for n, v in pkgs]}
    req = urllib.request.Request(API, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r).get("results", [])


def main(paths):
    pkgs = sorted(packages(paths))
    if not pkgs:
        print("OSV CHECK: no PyPI packages found in", paths)
        return 2
    try:
        results = query(pkgs)
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"OSV CHECK: could not reach osv.dev ({type(e).__name__}: {e})")
        return 2
    found = 0
    for (name, ver), res in zip(pkgs, results):
        ids = [v["id"] for v in res.get("vulns", [])]
        if ids:
            found += 1
            print(f"  {name} {ver}: {len(ids)} advisory(ies): {', '.join(ids[:8])}{' ...' if len(ids) > 8 else ''}")
    print(f"OSV CHECK: {len(pkgs)} packages checked, {found} with known advisories")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["Stationkeeper_US_SBOM.cdx.json", "Stationkeeper_US_Training_SBOM.cdx.json"]))
