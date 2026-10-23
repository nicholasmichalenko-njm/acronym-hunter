"""Run a helper program inside a Windows AppContainer that has NO capabilities.

Windows denies every network operation (internet, local network, loopback) to an AppContainer process that was
not granted a network capability, and this launcher grants none. The block is enforced by the operating system
kernel, not by the helper program, so it holds even if the program contained network code.
No admin rights are needed: the AppContainer profile is per-user, and folder access is granted with icacls on
folders inside the app's own folder.

Used for Tesseract (tesseract.exe and its training tools). Image bytes go in on stdin, results come out on stdout.
"""
import ctypes
import ctypes.wintypes as wt
import os
import subprocess
import threading
import msvcrt
import _winapi

PROFILE = "AcronymHunter.OcrSandbox"
_ERR_EXISTS = ctypes.c_long(0x800700B7).value      # HRESULT_FROM_WIN32(ERROR_ALREADY_EXISTS)
_ATTR_SECURITY_CAPABILITIES = 0x00020009
_ATTR_HANDLE_LIST = 0x00020002
_EXTENDED_STARTUPINFO_PRESENT = 0x00080000
_CREATE_NO_WINDOW = 0x08000000
_CREATE_UNICODE_ENVIRONMENT = 0x00000400
_STARTF_USESTDHANDLES = 0x00000100
_HANDLE_FLAG_INHERIT = 0x00000001
_WAIT_TIMEOUT = 0x00000102

class _SECURITY_CAPABILITIES(ctypes.Structure):
    _fields_ = [("AppContainerSid", ctypes.c_void_p), ("Capabilities", ctypes.c_void_p),
                ("CapabilityCount", wt.DWORD), ("Reserved", wt.DWORD)]

class _STARTUPINFOW(ctypes.Structure):
    _fields_ = [("cb", wt.DWORD), ("lpReserved", wt.LPWSTR), ("lpDesktop", wt.LPWSTR), ("lpTitle", wt.LPWSTR),
                ("dwX", wt.DWORD), ("dwY", wt.DWORD), ("dwXSize", wt.DWORD), ("dwYSize", wt.DWORD),
                ("dwXCountChars", wt.DWORD), ("dwYCountChars", wt.DWORD), ("dwFillAttribute", wt.DWORD),
                ("dwFlags", wt.DWORD), ("wShowWindow", wt.WORD), ("cbReserved2", wt.WORD),
                ("lpReserved2", ctypes.c_void_p), ("hStdInput", wt.HANDLE), ("hStdOutput", wt.HANDLE),
                ("hStdError", wt.HANDLE)]

class _STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [("StartupInfo", _STARTUPINFOW), ("lpAttributeList", ctypes.c_void_p)]

class _PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wt.HANDLE), ("hThread", wt.HANDLE), ("dwProcessId", wt.DWORD), ("dwThreadId", wt.DWORD)]

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_userenv = ctypes.WinDLL("userenv")
_adv = ctypes.WinDLL("advapi32", use_last_error=True)
_userenv.CreateAppContainerProfile.restype = ctypes.c_long
_userenv.CreateAppContainerProfile.argtypes = [wt.LPCWSTR, wt.LPCWSTR, wt.LPCWSTR, ctypes.c_void_p, wt.DWORD, ctypes.POINTER(ctypes.c_void_p)]
_userenv.DeriveAppContainerSidFromAppContainerName.restype = ctypes.c_long
_userenv.DeriveAppContainerSidFromAppContainerName.argtypes = [wt.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)]
_adv.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wt.LPWSTR)]
_k32.InitializeProcThreadAttributeList.argtypes = [ctypes.c_void_p, wt.DWORD, wt.DWORD, ctypes.POINTER(ctypes.c_size_t)]
_k32.UpdateProcThreadAttribute.argtypes = [ctypes.c_void_p, wt.DWORD, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p, ctypes.c_void_p]
_k32.CreateProcessW.argtypes = [wt.LPCWSTR, wt.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wt.BOOL, wt.DWORD,
                                ctypes.c_void_p, wt.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p]
_k32.SetHandleInformation.argtypes = [wt.HANDLE, wt.DWORD, wt.DWORD]
_k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
_k32.WaitForSingleObject.restype = wt.DWORD
_k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
_k32.TerminateProcess.argtypes = [wt.HANDLE, wt.UINT]
_k32.CloseHandle.argtypes = [wt.HANDLE]

_sid_ptr = None
_sid_str = None
_granted = set()
_lock = threading.Lock()

def container_sid():
    """(SID pointer, SID string) of the per-user AppContainer profile, created on first use."""
    global _sid_ptr, _sid_str
    with _lock:
        if _sid_ptr is None:
            sid = ctypes.c_void_p()
            hr = _userenv.CreateAppContainerProfile(PROFILE, "Acronym Hunter OCR sandbox",
                                                    "Runs Tesseract with no network access", None, 0, ctypes.byref(sid))
            if hr == _ERR_EXISTS:
                hr = _userenv.DeriveAppContainerSidFromAppContainerName(PROFILE, ctypes.byref(sid))
            if hr != 0:
                raise OSError(f"Could not create the OCR sandbox profile (HRESULT 0x{hr & 0xFFFFFFFF:08X})")
            text = wt.LPWSTR()
            if not _adv.ConvertSidToStringSidW(sid, ctypes.byref(text)):
                raise ctypes.WinError(ctypes.get_last_error())
            _sid_ptr, _sid_str = sid, text.value
    return _sid_ptr, _sid_str

def grant(folder, write=False):
    """Let the sandbox read (or read and write) one folder and everything in it. Done once per session."""
    folder = os.path.abspath(folder)
    key = (os.path.normcase(folder), write)
    if key in _granted:
        return
    os.makedirs(folder, exist_ok=True)
    _sid, sid = container_sid()
    r = subprocess.run(["icacls", folder, "/grant", f"*{sid}:(OI)(CI)({'M' if write else 'RX'})", "/T", "/C", "/Q"],
                       capture_output=True, creationflags=_CREATE_NO_WINDOW)
    if r.returncode != 0:
        raise OSError(f"Could not give the OCR sandbox access to {folder}: "
                      + r.stdout.decode("mbcs", "replace").strip()[-200:])
    _granted.add(key)

def _inheritable_pipe():
    r, w = _winapi.CreatePipe(None, 0)
    return r, w

def run(cmd, input_bytes=b"", timeout=180, env=None, cwd=None, on_line=None, cancel=None):
    """Run cmd (list) in the sandbox. Returns (exit code, stdout bytes, stderr bytes). Raises TimeoutError.
    on_line(bytes): called for each stdout line as it arrives. cancel: threading.Event that stops the program."""
    sid, _s = container_sid()
    in_r, in_w = _inheritable_pipe(); out_r, out_w = _inheritable_pipe(); err_r, err_w = _inheritable_pipe()
    child_ends = (in_r, out_w, err_w)
    for h in child_ends:
        _k32.SetHandleInformation(h, _HANDLE_FLAG_INHERIT, _HANDLE_FLAG_INHERIT)
    caps = _SECURITY_CAPABILITIES(sid, None, 0, 0)     # no capabilities at all: no network of any kind
    handles = (wt.HANDLE * 3)(*child_ends)               # the child inherits only its 3 pipe ends
    size = ctypes.c_size_t()
    _k32.InitializeProcThreadAttributeList(None, 2, 0, ctypes.byref(size))
    attrs = ctypes.create_string_buffer(size.value)
    if not _k32.InitializeProcThreadAttributeList(attrs, 2, 0, ctypes.byref(size)):
        raise ctypes.WinError(ctypes.get_last_error())
    if not _k32.UpdateProcThreadAttribute(attrs, 0, _ATTR_SECURITY_CAPABILITIES, ctypes.byref(caps), ctypes.sizeof(caps), None, None) \
            or not _k32.UpdateProcThreadAttribute(attrs, 0, _ATTR_HANDLE_LIST, handles, ctypes.sizeof(handles), None, None):
        raise ctypes.WinError(ctypes.get_last_error())
    si = _STARTUPINFOEXW()
    si.StartupInfo.cb = ctypes.sizeof(si)
    si.StartupInfo.dwFlags = _STARTF_USESTDHANDLES
    si.StartupInfo.hStdInput, si.StartupInfo.hStdOutput, si.StartupInfo.hStdError = child_ends
    si.lpAttributeList = ctypes.cast(attrs, ctypes.c_void_p)
    env = dict(os.environ if env is None else env)
    block = ctypes.create_unicode_buffer("".join(f"{k}={v}\0" for k, v in sorted(env.items())) + "\0")
    cmdline = ctypes.create_unicode_buffer(subprocess.list2cmdline(cmd))
    pi = _PROCESS_INFORMATION()
    ok = _k32.CreateProcessW(cmd[0], cmdline, None, None, True,
                             _EXTENDED_STARTUPINFO_PRESENT | _CREATE_NO_WINDOW | _CREATE_UNICODE_ENVIRONMENT,
                             block, cwd, ctypes.byref(si), ctypes.byref(pi))
    err = ctypes.get_last_error()
    for h in child_ends:
        _winapi.CloseHandle(h)
    if not ok:
        for h in (in_w, out_r, err_r):
            _winapi.CloseHandle(h)
        raise ctypes.WinError(err)
    _k32.CloseHandle(pi.hThread)
    f_in = os.fdopen(msvcrt.open_osfhandle(in_w, 0), "wb")
    f_out = os.fdopen(msvcrt.open_osfhandle(out_r, os.O_RDONLY), "rb")
    f_err = os.fdopen(msvcrt.open_osfhandle(err_r, os.O_RDONLY), "rb")
    result = {}
    def feed():
        try:
            f_in.write(input_bytes)
        except OSError:
            pass
        finally:
            try:
                f_in.close()
            except OSError:
                pass
    def read_out():
        if on_line is None:
            result["out"] = f_out.read(); return
        parts = []
        for line in iter(f_out.readline, b""):
            parts.append(line)
            try:
                on_line(line)
            except Exception:
                pass
        result["out"] = b"".join(parts)
    readers = [threading.Thread(target=feed, daemon=True),
               threading.Thread(target=read_out, daemon=True),
               threading.Thread(target=lambda: result.__setitem__("err", f_err.read()), daemon=True)]
    for t in readers:
        t.start()
    try:
        waited = 0.0
        while _k32.WaitForSingleObject(pi.hProcess, 250) == _WAIT_TIMEOUT:
            waited += 0.25
            if cancel is not None and cancel.is_set():
                _k32.TerminateProcess(pi.hProcess, 1)
                raise InterruptedError(f"{os.path.basename(cmd[0])} stopped")
            if waited >= timeout:
                _k32.TerminateProcess(pi.hProcess, 1)
                raise TimeoutError(f"{os.path.basename(cmd[0])} did not finish within {timeout} s")
        for t in readers:
            t.join(10)
        code = wt.DWORD()
        _k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
        return code.value, result.get("out", b""), result.get("err", b"")
    finally:
        _k32.CloseHandle(pi.hProcess)
        for f in (f_out, f_err):
            try:
                f.close()
            except OSError:
                pass

def network_probe():
    """Proof for the self-test: Windows' own curl.exe, run in the same sandbox, must fail to reach the internet."""
    curl = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "curl.exe")
    if not os.path.isfile(curl):
        return "skipped (curl.exe not present)"
    try:
        code, out, err = run([curl, "-s", "-S", "-m", "8", "-o", "NUL", "https://www.microsoft.com"], timeout=20)
    except Exception as e:
        return f"blocked (launch refused: {type(e).__name__})"
    return f"BLOCKED (curl exit {code}: {err.decode('utf-8', 'replace').strip()[:80]})" if code != 0 else "NOT BLOCKED"
