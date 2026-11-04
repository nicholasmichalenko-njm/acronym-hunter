"""2.71.0 a GUI test that stops moving fails instead of freezing the build: after its time limit it prints where every
thread waits, then a FAIL line the build counts, and exits."""
import faulthandler, os, sys, threading


def arm(name, secs=480, info=None):
    def fire():
        try:
            print(f"\nHANG: {name} did not finish in {secs} s. Where it waits:", flush=True)
            if info is not None:
                print("  state:", info(), flush=True)
            faulthandler.dump_traceback(file=sys.stdout, all_threads=True)
            print(f"{name} FAIL (timeout after {secs} s)", flush=True)
        finally:
            os._exit(3)
    t = threading.Timer(secs, fire)
    t.daemon = True
    t.start()
    return t


def end(code):
    """3.37.0 leave a GUI test at once with its result. The result line is already printed; Qt's teardown on Windows can
    crash while the process unloads (exit 0xC0000005) after every check passed, and the release gate counts any non-zero
    exit. On Windows the process is ended by TerminateProcess, which runs no unload work and keeps the exit code; elsewhere
    os._exit. A crash during the checks still ends the test with an error before it gets here."""
    try:
        sys.stdout.flush(); sys.stderr.flush()
    except Exception:  # noqa: BLE001
        pass
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.GetCurrentProcess.restype = wintypes.HANDLE          # a 64-bit pseudo handle; untyped ctypes cuts it to 32 bits
        k.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
        k.TerminateProcess.restype = wintypes.BOOL
        k.TerminateProcess(k.GetCurrentProcess(), int(code) & 0xFFFFFFFF)
    os._exit(int(code))
