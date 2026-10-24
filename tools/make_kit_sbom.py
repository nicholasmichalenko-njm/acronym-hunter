"""SBOM (CycloneDX 1.5 JSON) of a docTR Training Kit, run with the kit's own embedded Python so it lists exactly the
packages inside the kit:  <kit>\\python\\python.exe tools\\make_kit_sbom.py <kit folder> <out.json>
Adds the embedded Python, the starting weights and base models with SHA-256. No network."""
import datetime, hashlib, importlib.metadata as md, json, os, sys, uuid


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    kit, out = sys.argv[1], sys.argv[2]
    comps = []
    for d in sorted(md.distributions(), key=lambda d: (d.metadata["Name"] or "").lower()):
        name, ver = d.metadata["Name"], d.version
        if not name or name.lower() in ("pip", "setuptools", "wheel"):
            continue
        lic = (d.metadata.get("License-Expression") or "").strip() or \
            "; ".join(c.split("::")[-1].strip() for c in (d.metadata.get_all("Classifier") or []) if c.startswith("License ::"))
        c = {"type": "library", "name": name, "version": ver, "purl": f"pkg:pypi/{name.lower().replace('_', '-')}@{ver}",
             "bom-ref": f"pypi:{name.lower()}@{ver}"}
        if name.lower() == "huggingface-hub" or "offline-shim" in ver:
            c["description"] = "Offline stand-in written by this project: every call raises an error."
        if lic:
            c["licenses"] = [{"license": {"name": lic[:120]}}]
        comps.append(c)
    v = sys.version_info
    comps.append({"type": "platform", "name": "CPython (embedded)", "version": f"{v.major}.{v.minor}.{v.micro}", "bom-ref": "cpython"})
    for sub, kind, supplier in (("weights/models", "starting weights", "Mindee (docTR), Apache-2.0"),
                                ("base_models", "app's bundled docTR models", "Mindee (docTR), exported to ONNX by this project")):
        folder = os.path.join(kit, *sub.split("/"))
        for f in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            p = os.path.join(folder, f)
            if os.path.isfile(p):
                comps.append({"type": "machine-learning-model" if f.endswith((".pt", ".onnx")) else "file", "name": f"{sub}/{f}",
                              "bom-ref": f"file:{sub}/{f}", "description": kind, "supplier": {"name": supplier},
                              "hashes": [{"alg": "SHA-256", "content": sha256(p)}]})
    bom = {"bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{uuid.uuid4()}", "version": 1,
           "metadata": {"timestamp": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
                        "component": {"type": "application", "name": os.path.basename(os.path.normpath(kit)), "bom-ref": "kit",
                                      "description": "Acronym Hunter docTR Training Kit. Runs offline; every network call is refused."}},
           "components": comps, "dependencies": [{"ref": "kit", "dependsOn": [c["bom-ref"] for c in comps]}]}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(bom, f, indent=1)
    print(f"Kit SBOM written: {out} ({len(comps)} components)")


if __name__ == "__main__":
    main()
