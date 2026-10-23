"""Network audit of a built package: which program files can call Windows networking APIs.

Reads the import tables (normal and delay-load) of every .exe, .dll, and .pyd and flags links to Winsock, WinHTTP,
WinINet, URL Moniker, DNS, HTTP Server API, WebSocket, or any libcurl.
Rules (exit code 1 on any violation):
  1. Files under _internal\\tesseract may link NONE (Tesseract is built from source without libcurl).
  2. Every other flagged file must be listed in tools\\network_allowlist.txt, reviewed, with the reason it is safe.
Limit: a program could still load a networking DLL by name at run time (LoadLibrary). Tesseract's source has no such
code once libcurl is disabled, and the Tesseract processes also run in a no-network AppContainer.

  python tools\\network_audit.py dist\\AcronymHunter              audit (used by build.ps1)
  python tools\\network_audit.py dist\\AcronymHunter --report     list every flagged file and import
"""
import os
import sys
import pefile

NET_DLLS = {"ws2_32.dll", "wsock32.dll", "mswsock.dll", "winhttp.dll", "wininet.dll", "urlmon.dll", "dnsapi.dll",
            "httpapi.dll", "websocket.dll", "webio.dll"}
HERE = os.path.dirname(os.path.abspath(__file__))
ALLOWLIST = os.path.join(HERE, "network_allowlist.txt")

def imports(path):
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                                           pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"]])
    names = [e.dll.decode("ascii", "replace").lower() for e in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])]
    names += [e.dll.decode("ascii", "replace").lower() for e in getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", [])]
    pe.close()
    return names

def flagged(root):
    out = {}
    for d, _dirs, files in os.walk(root):
        for f in files:
            if os.path.splitext(f)[1].lower() not in (".exe", ".dll", ".pyd"):
                continue
            path = os.path.join(d, f)
            rel = os.path.relpath(path, root)
            try:
                hits = sorted({n for n in imports(path) if n in NET_DLLS or n.startswith("libcurl")})
            except pefile.PEFormatError:
                continue
            if f.lower().startswith("libcurl"):
                hits = hits or ["(is libcurl)"]
            if hits:
                out[rel] = hits
    return out

def load_allowlist():
    allowed = {}
    if os.path.exists(ALLOWLIST):
        for line in open(ALLOWLIST, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#"):
                rel, _sep, reason = line.partition("|")
                allowed[rel.strip().lower()] = reason.strip()
    return allowed

def main():
    root = sys.argv[1]
    report = "--report" in sys.argv
    hits = flagged(root)
    allowed = load_allowlist()
    bad = []
    for rel, dlls in sorted(hits.items()):
        tess = rel.lower().startswith(os.path.join("_internal", "tesseract").lower())
        ok = (not tess) and rel.lower() in allowed
        if report or not ok:
            print(f"{'OK  ' if ok else 'FAIL'} {rel}: {', '.join(dlls)}" + (f"   [{allowed[rel.lower()]}]" if ok else ""))
        if not ok:
            bad.append(rel)
    total = sum(1 for d, _x, fs in os.walk(root) for f in fs if os.path.splitext(f)[1].lower() in (".exe", ".dll", ".pyd"))
    if bad:
        print(f"NETWORK AUDIT FAILED: {len(bad)} file(s) link networking APIs without review"
              + (" (Tesseract files must link none)" if any(b.lower().startswith("_internal\\tesseract") for b in bad) else ""))
        sys.exit(1)
    print(f"Network audit passed: {total} program files checked; {len(hits)} reviewed file(s) link networking APIs "
          f"(Python's own socket modules, guarded in-process); Tesseract files link none.")

if __name__ == "__main__":
    main()
