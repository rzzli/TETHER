"""Finite, lazy public aliases that preserve legacy module and class identity.

A temporary wrapper module is replaced after import initialization. Returning an
already loaded legacy module from create_module would let import machinery alter
its metadata, so this loader deliberately creates a fresh temporary module.
"""
from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.util
from importlib import import_module
from pathlib import Path
import sys

# Reviewed public inventory; no runtime discovery, arbitrary target imports, or
# eager import of scientific modules/optional dependencies occurs.
_LEGACY_MODULES = frozenset(('agents',
 'process_tree',
 'source_access',
 'file_proofs',
 'stable_read',
 'archive',
 'archive.core',
 'archive.interpretation',
 'archive.paths',
 'archive.restore',
 'artifacts',
 'atomic',
 'bundle',
 'bundle_files',
 'chrono',
 'contracts',
 'derivations',
 'evaluation',
 'evaluation_binding',
 'dossier_verification',
 'execution_states',
 'verification_policy',
 'temporal',
 'features',
 'generated_claims',
 'ingest',
 'journal',
 'ledger',
 'local_model',
 'maintenance',
 'money',
 'provenance',
 'rendering',
 'replay_validation',
 'retrieval',
 'scorer',
 'semantics',
 'serde',
 'wire',
 'workflow',
 'study',
 'study.proofs',
 'study.stable_read',
 'demo',
 'demo.v2'))
_CANONICAL_ALIASES = {"cli": "tether._cli"}
_OWN_MODULES = frozenset(("tether.__main__", "tether.api", "tether._aliases", "tether._cli", "tether._presentation", "tether._semantics", "tether._process", "tether._catalog_policy", "tether._catalog_binding"))
_ENTRYPOINTS = {'tether.archive.__main__': ('archive', '__main__.py')}


def public_roots():
    return frozenset(name.partition(".")[0] for name in _LEGACY_MODULES) | frozenset(_CANONICAL_ALIASES)


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, target):
        self.target = target

    def create_module(self, spec):
        return None

    def exec_module(self, temporary):
        sys.modules[temporary.__name__] = import_module(self.target)


class _AliasFinder(importlib.abc.MetaPathFinder):
    _tether_alias_finder = True

    def find_spec(self, fullname, path=None, target=None):
        if not fullname.startswith("tether."):
            return None
        if fullname in _OWN_MODULES:
            return None
        if fullname in _ENTRYPOINTS:
            entrypoint = Path(__file__).parent.joinpath(*_ENTRYPOINTS[fullname])
            return importlib.util.spec_from_file_location(fullname, entrypoint)
        suffix = fullname[len("tether."):]
        if suffix in _CANONICAL_ALIASES:
            legacy_name = _CANONICAL_ALIASES[suffix]
        elif suffix in _LEGACY_MODULES:
            legacy_name = "tether_engine." + suffix
        else:
            # Do not fall through to a legacy package __path__, which could
            # execute an unapproved module under the new public namespace.
            raise ModuleNotFoundError(f"{fullname!r} is not in the TETHER public module inventory", name=fullname)
        source = importlib.util.find_spec(legacy_name)
        if source is None:
            raise ModuleNotFoundError(f"Required TETHER engine module is unavailable: {legacy_name}", name=legacy_name)
        return importlib.machinery.ModuleSpec(fullname, _AliasLoader(legacy_name),
            is_package=source.submodule_search_locations is not None)


def install():
    if not any(getattr(finder, "_tether_alias_finder", False) for finder in sys.meta_path):
        sys.meta_path.insert(0, _AliasFinder())
