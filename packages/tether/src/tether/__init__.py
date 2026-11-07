"""TETHER: Target Evidence Tracking Harness for Evaluation and Reproducibility.

The public namespace shares module and class identities with the separately
versioned TETHER engine. Earlier package proofs require their original checkout.
"""
from __future__ import annotations

from tether_engine import __version__ as __core_version__

__version__ = "0.6.0"

if __core_version__ != "0.4.0":
    raise ImportError("TETHER 0.6.0 requires the pinned engine 0.4.0")

from ._aliases import install as _install_aliases, public_roots as _public_roots

_install_aliases()


def __getattr__(name: str):
    if name not in _public_roots():
        raise AttributeError(f"module 'tether' has no attribute {name!r}")
    from importlib import import_module
    return import_module("tether." + name)


__all__ = ["__version__", "__core_version__"]
