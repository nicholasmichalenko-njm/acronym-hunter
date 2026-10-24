"""Software Bill of Materials (CycloneDX 1.5 JSON) for a finished build, from what actually ships.

    venv\\Scripts\\python.exe tools\\make_sbom.py dist\\AcronymHunter AcronymHunter_US_SBOM.cdx.json "US"

Sources of truth:
  - Python modules bundled inside AcronymHunter.exe (PyInstaller's embedded archive) and the folders and binaries in
    _internal, mapped to the installed distributions that own them (name, version, license, PyPI purl).
  - Native parts: Python runtime, Tcl/Tk, Tesseract (from its SOURCE.txt), Google's eng.traineddata, the docTR ONNX
    models (doctr_models.json), PDFium (pypdfium2), ONNX Runtime.
  - SHA-256 of every program file (.exe, .dll, .pyd) and model file that ships.
No network. Output holds package names, versions, licenses and hashes only: safe to publish with the release.
"""
import datetime, hashlib, importlib.metadata as md, json, os, re, sys, uuid

PROGRAM_EXT = (".exe", ".dll", ".pyd")
MODEL_EXT = (".onnx", ".traineddata")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def bundled_modules(exe):
    """Top-level module names inside the exe's embedded Python archive (PyInstaller 6)."""
    names = set()
    try:
        from PyInstaller.archive.readers import CArchiveReader
        arch = CArchiveReader(exe)
        for entry in arch.toc:
            if entry.lower().endswith(".pyz") or entry.upper().startswith("PYZ"):
                pyz = arch.open_embedded_archive(entry)
                names |= {m.split(".")[0] for m in pyz.toc}
    except Exception as ex:                                  # older or unusual builds: fall back to the folder scan
        print(f"note: embedded archive not read ({type(ex).__name__}); using the _internal folder only")
    return names


def internal_names(internal):
    out = set()
    for n in os.listdir(internal):
        base = n.split(".")[0]
        out.add(base)
        if n.endswith(".libs"):
            out.add(n[:-5])
    return out


def license_of(dist):
    m = dist.metadata
    lic = (m.get("License-Expression") or "").strip()
    if not lic:
        raw = (m.get("License") or "").strip()
        lic = raw if raw and len(raw) < 80 and "\n" not in raw else ""
    if not lic:
        cls = [c.split("::")[-1].strip() for c in (m.get_all("Classifier") or []) if c.startswith("License ::")]
        lic = "; ".join(cls)
    return lic


def python_components(names):
    pkg_map = md.packages_distributions()
    seen, comps = {}, []
    for top in sorted(names):
        for dname in pkg_map.get(top, []):
            if dname.lower() in seen:
                continue
            try:
                d = md.distribution(dname)
            except md.PackageNotFoundError:
                continue
            name, ver = d.metadata["Name"], d.version
            if name.lower() in ("pyinstaller", "pyinstaller-hooks-contrib", "altgraph", "pefile", "pywin32-ctypes", "setuptools", "pip"):
                continue                                     # build tools, not shipped code
            seen[dname.lower()] = True
            c = {"type": "library", "name": name, "version": ver, "purl": f"pkg:pypi/{name.lower().replace('_', '-')}@{ver}",
                 "bom-ref": f"pypi:{name.lower()}@{ver}"}
            lic = license_of(d)
            if lic:
                spdx = re.fullmatch(r"[A-Za-z0-9.\-+]+(?:\s+(?:OR|AND|WITH)\s+[A-Za-z0-9.\-+]+)*", lic)
                c["licenses"] = [{"expression": lic}] if spdx else [{"license": {"name": lic[:120]}}]
            home = d.metadata.get("Home-page") or ""
            if home:
                c["externalReferences"] = [{"type": "website", "url": home}]
            comps.append(c)
    return comps


def native_components(root, internal):
    comps = []
    v = sys.version_info
    comps.append({"type": "platform", "name": "CPython", "version": f"{v.major}.{v.minor}.{v.micro}", "bom-ref": "cpython",
                  "licenses": [{"expression": "PSF-2.0"}], "supplier": {"name": "Python Software Foundation"}})
    try:
        import tkinter
        comps.append({"type": "library", "name": "Tcl/Tk", "version": str(tkinter.TkVersion), "bom-ref": "tcltk",
                      "licenses": [{"expression": "TCL"}]})
    except Exception:
        pass
    tdir = os.path.join(internal, "tesseract")
    if os.path.isdir(tdir):
        src = ""
        try:
            src = open(os.path.join(tdir, "SOURCE.txt"), encoding="utf-8", errors="replace").read()
        except OSError:
            pass
        m = re.search(r"tesseract[^\n]*?(\d+\.\d+\.\d+)", src, re.I)
        c = {"type": "application", "name": "Tesseract OCR", "version": m.group(1) if m else "", "bom-ref": "tesseract",
             "licenses": [{"expression": "Apache-2.0"}], "description": "Built from source without network support (DISABLE_CURL=ON)." if "DISABLE_CURL=ON" in src else ""}
        exe = os.path.join(tdir, "tesseract.exe")
        if os.path.isfile(exe):
            c["hashes"] = [{"alg": "SHA-256", "content": sha256(exe)}]
        comps.append(c)
        eng = os.path.join(tdir, "tessdata", "eng.traineddata")
        if os.path.isfile(eng):
            comps.append({"type": "machine-learning-model", "name": "tessdata_best eng.traineddata", "bom-ref": "tessdata-eng",
                          "supplier": {"name": "Google (tesseract-ocr/tessdata_best)"}, "licenses": [{"expression": "Apache-2.0"}],
                          "hashes": [{"alg": "SHA-256", "content": sha256(eng)}]})
    ddir = os.path.join(internal, "doctr")
    if os.path.isfile(os.path.join(ddir, "doctr_models.json")):
        try:
            info = json.load(open(os.path.join(ddir, "doctr_models.json"), encoding="utf-8"))
        except ValueError:
            info = {}
        for key, meta in (info.get("models") or {}).items():
            f = os.path.join(ddir, key + ".onnx")
            comps.append({"type": "machine-learning-model", "name": f"docTR {meta.get('arch', key)}", "bom-ref": f"doctr-{key}",
                          "supplier": {"name": "Mindee (docTR), exported to ONNX by this project"},
                          "licenses": [{"expression": "Apache-2.0"}],
                          "hashes": [{"alg": "SHA-256", "content": sha256(f)}] if os.path.isfile(f) else []})
    try:
        import pypdfium2
        ver = getattr(pypdfium2, "PDFIUM_INFO", None) or getattr(getattr(pypdfium2, "version", None), "PDFIUM_INFO", "")
        comps.append({"type": "library", "name": "PDFium", "version": str(ver).split()[0] if ver else "", "bom-ref": "pdfium",
                      "supplier": {"name": "Google (via pypdfium2 binaries)"}, "licenses": [{"expression": "BSD-3-Clause"}]})
    except Exception:
        pass
    return comps


def file_components(root):
    out = []
    for dp, _dn, fs in os.walk(root):
        for f in sorted(fs):
            if f.lower().endswith(PROGRAM_EXT + MODEL_EXT):
                p = os.path.join(dp, f)
                rel = os.path.relpath(p, root).replace("\\", "/")
                out.append({"type": "file", "name": rel, "bom-ref": "file:" + rel, "hashes": [{"alg": "SHA-256", "content": sha256(p)}]})
    return out


def build(root, edition, version):
    exe = os.path.join(root, "AcronymHunter.exe")
    internal = os.path.join(root, "_internal")
    names = bundled_modules(exe) | internal_names(internal)
    comps = python_components(names) + native_components(root, internal)
    files = file_components(root)
    app = {"type": "application", "name": "Acronym Hunter", "version": version, "bom-ref": "acronym-hunter",
           "description": f"{edition} edition. Runs fully offline; makes no network connections.",
           "supplier": {"name": "Nicholas Michalenko"}}
    if os.path.isfile(exe):
        app["hashes"] = [{"alg": "SHA-256", "content": sha256(exe)}]
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "serialNumber": f"urn:uuid:{uuid.uuid4()}", "version": 1,
            "metadata": {"timestamp": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
                         "tools": {"components": [{"type": "application", "name": "Acronym Hunter tools/make_sbom.py"}]},
                         "component": app},
            "components": comps + files,
            "dependencies": [{"ref": "acronym-hunter", "dependsOn": [c["bom-ref"] for c in comps]}]}


def main():
    root, out, edition = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "US")
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    version = ""
    try:
        src = open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app_gui.py"), encoding="utf-8").read()
        version = re.search(r'^APP_VERSION = "([^"]+)"', src, re.M).group(1)
    except Exception:
        pass
    bom = build(root, edition, version)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(bom, f, indent=1)
    libs = [c for c in bom["components"] if c["type"] != "file"]
    files = [c for c in bom["components"] if c["type"] == "file"]
    print(f"SBOM written: {out} ({len(libs)} components, {len(files)} program and model files with SHA-256)")


if __name__ == "__main__":
    main()
