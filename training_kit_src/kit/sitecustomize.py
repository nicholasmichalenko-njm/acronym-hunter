"""Stationkeeper Training Kit: network lockdown.

Python loads this file automatically at startup (it sits in the kit's site-packages), before PaddlePaddle,
PaddleOCR, or any training script runs, and in every worker process they start. It makes outbound network
access impossible for the whole kit: no connections, no DNS lookups, no UDP, no urllib. Loopback
(127.0.0.1 / ::1) stays allowed because Python's own multiprocessing uses it on Windows.

Every refused attempt is written to kit\\logs\\network_blocked.log with a stack trace, so a reviewer can see
exactly what tried to go online. An empty or missing log means nothing tried.
"""
import os, socket, sys, datetime, traceback

_LOOPBACK = {"127.0.0.1", "::1", "localhost", "0.0.0.0"}
def _kit_root():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(8):                       # works for python\ and export\python\ inside the kit
        if os.path.isfile(os.path.join(d, "kit", "train.py")):
            return d
        d = os.path.dirname(d)
    return os.path.dirname(os.path.abspath(__file__))
_LOG = os.path.join(_kit_root(), "kit", "logs", "network_blocked.log")

def _refuse(what, target):
    try:
        os.makedirs(os.path.dirname(_LOG), exist_ok=True)
        with open(_LOG, "a", encoding="utf-8") as f:
            tag = "SELF-TEST REFUSED" if os.environ.get("KIT_SELFTEST") == "1" else "REFUSED"
            f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] {tag} {what} -> {target} (pid {os.getpid()}, {' '.join(sys.argv)[:200]})\n")
            f.write("".join(traceback.format_stack(limit=12)) + "\n")
    except Exception:
        pass
    raise OSError(f"Training Kit offline lockdown: {what} to {target} is disabled.")

def _host(address):
    return address[0] if isinstance(address, tuple) and address else address

_real_connect, _real_connect_ex = socket.socket.connect, socket.socket.connect_ex
_real_sendto, _real_getaddrinfo = socket.socket.sendto, socket.getaddrinfo

def _connect(self, address, *a, **k):
    if self.family in (socket.AF_INET, socket.AF_INET6) and _host(address) not in _LOOPBACK:
        _refuse("connect", address)
    return _real_connect(self, address, *a, **k)

def _connect_ex(self, address, *a, **k):
    if self.family in (socket.AF_INET, socket.AF_INET6) and _host(address) not in _LOOPBACK:
        _refuse("connect", address)
    return _real_connect_ex(self, address, *a, **k)

def _sendto(self, data, *args):
    address = args[-1]
    if self.family in (socket.AF_INET, socket.AF_INET6) and _host(address) not in _LOOPBACK:
        _refuse("sendto", address)
    return _real_sendto(self, data, *args)

def _getaddrinfo(host, *a, **k):
    if host not in (None, "", *_LOOPBACK):
        _refuse("DNS lookup", host)
    return _real_getaddrinfo(host, *a, **k)

socket.socket.connect = _connect
socket.socket.connect_ex = _connect_ex
socket.socket.sendto = _sendto
socket.getaddrinfo = _getaddrinfo
socket.gethostbyname = lambda host, *a: _refuse("DNS lookup", host) if host not in _LOOPBACK else "127.0.0.1"
os.environ["NO_PROXY"] = "*"
os.environ["NO_ALBUMENTATIONS_UPDATE"] = "1"   # albumentations (PaddleOCR 3.x) otherwise checks PyPI for updates at import
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
KIT_NETWORK_LOCKDOWN = True
