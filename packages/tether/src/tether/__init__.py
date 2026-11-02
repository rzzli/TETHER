"""TETHER: Target Evidence Tracking Harness for Evaluation and Reproducibility.

The public namespace uses the pinned AsOf 0.3.11 scientific engine. Legacy
module objects and serialized identities remain intact for compatibility.
"""
from __future__ import annotations

from asof import __version__ as __core_version__

__version__ = "0.4.2"

if __core_version__ != "0.3.11":
    raise ImportError("TETHER 0.4.2 requires the pinned legacy engine 0.3.11")

from ._aliases import install as _install_aliases, public_roots as _public_roots

_install_aliases()


def __getattr__(name: str):
    if name not in _public_roots():
        raise AttributeError(f"module 'tether' has no attribute {name!r}")
    from importlib import import_module
    return import_module("tether." + name)


__all__ = ["__version__", "__core_version__"]
