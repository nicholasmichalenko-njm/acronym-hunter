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
