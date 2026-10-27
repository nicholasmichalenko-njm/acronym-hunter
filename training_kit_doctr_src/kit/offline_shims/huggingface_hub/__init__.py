"""Offline stand-in for huggingface_hub inside the Stationkeeper Training Kit.

docTR imports four names from huggingface_hub at start-up (for its optional "push to / load from Hugging Face Hub"
features). The kit never uses those features and must hold no network library, so the real package is not installed.
This file provides the four names; calling any of them raises an error. It contains no network code.
"""
__version__ = "0+offline-shim"


def _off(*_a, **_k):
    raise OSError("Hugging Face Hub is not available in the offline Training Kit.")


class HfApi:
    def __init__(self, *_a, **_k):
        _off()


get_token = hf_hub_download = login = _off
