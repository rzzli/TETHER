"""Read current installed code as data, without importing either product.

The experiment supplies trusted package entry paths. Historical proof fields
are not a substitute for these per-validation reads of the actual payload.
"""
from __future__ import annotations

import ast
import hashlib
from importlib import metadata
import os
from pathlib import Path
import re
import stat

from .independent import bounded_stable_bytes, require


def package_root(trusted, package):
    paths = trusted.get('runtime_paths') if type(trusted) is dict else None
    value = paths.get(package + '_file') if type(paths) is dict else None
    require(type(value) is str and Path(value).is_absolute() and Path(value).name == '__init__.py',
            'EP-VERIFY-03', 'Trusted installed package entry path required')
    path = Path(value)
    bounded_stable_bytes(path)
    return path.parent


def inventory(root, *, exclude_cache):
    members = []
    for directory, children, names in os.walk(root, followlinks=False):
        for name in (*children, *names):
            path = Path(directory) / name
            info = path.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                    'EP-IO-01', 'Installed package link/reparse path')
        if exclude_cache:
            children[:] = [name for name in children if name != '__pycache__']
        members.extend(Path(directory) / name for name in names if name.endswith('.py'))
    names = sorted(p.relative_to(root).as_posix() for p in members)
    require('__init__.py' in names and len({name.casefold() for name in names}) == len(names),
            'EP-VERIFY-03', 'Installed package source inventory invalid')
    return names


def capture(root, *, exclude_cache):
    names = inventory(root, exclude_cache=exclude_cache)
    result = {}
    for name in names:
        payload = bounded_stable_bytes(root / name)
        result[name] = dict(path=name, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))
    require(names == inventory(root, exclude_cache=exclude_cache), 'EP-VERIFY-03', 'Installed package inventory changed')
    return result


def core_code(trusted):
    root = package_root(trusted, 'tether_engine')
    return {name: proof['sha256'] for name, proof in capture(root, exclude_cache=False).items()}


def literal_version(root):
    tree = ast.parse(bounded_stable_bytes(root / '__init__.py'), filename=str(root / '__init__.py'))
    values = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '__version__' for t in node.targets):
            require(isinstance(node.value, ast.Constant) and type(node.value.value) is str,
                    'EP-VERIFY-03', 'Package version must be a literal')
            values.append(node.value.value)
    require(len(values) == 1, 'EP-VERIFY-03', 'Package version missing or ambiguous')
    return values[0]


def distribution_versions(roots):
    wanted = {'tether-target-agents', 'tether-target-engine'}
    found = {}
    for distribution in metadata.distributions(path=sorted({str(root.parent) for root in roots})):
        name = re.sub(r'[-_.]+', '-', distribution.metadata.get('Name', '')).lower()
        if name in wanted:
            require(name not in found, 'EP-VERIFY-03', 'Duplicate installed distribution metadata')
            found[name] = distribution.version
    return {name: found.get(name) for name in sorted(wanted)}


def launcher_proof(trusted):
    facade, core = package_root(trusted, 'tether'), package_root(trusted, 'tether_engine')
    first = capture(facade, exclude_cache=True)
    second = capture(facade, exclude_cache=True)
    require(first == second, 'EP-VERIFY-03', 'Installed launcher code changed during capture')
    versions = dict(tether=literal_version(facade), tether_engine=literal_version(core))
    require(versions == {'tether': '0.6.0', 'tether_engine': '0.4.0'}, 'EP-VERIFY-03', 'Unsupported installed package version')
    distributions = distribution_versions((facade, core))
    require(distributions['tether-target-agents'] in (None, '0.6.0') and
            distributions['tether-target-engine'] in (None, '0.4.0'), 'EP-VERIFY-03', 'Installed distribution version differs')
    return dict(schema_version=1, method='tether.launcher_code.v2', facade_version=versions['tether'],
        core_version=versions['tether_engine'], installed_distributions=distributions, code=first)
