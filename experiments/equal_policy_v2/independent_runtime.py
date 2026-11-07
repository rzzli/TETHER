"""Exact supported runtime pairs for the versioned comparison; no product imports."""
from equal_policy.independent import require
from equal_policy.independent_runtime import (
    package_root, capture, literal_version, distribution_versions,
)


SUPPORTED_PAIRS = frozenset({('0.6.0', '0.4.0')})


def approved_versions(versions):
    return (type(versions) is dict and set(versions) == {'tether', 'tether_engine'}
            and type(versions['tether']) is str and type(versions['tether_engine']) is str
            and (versions['tether'], versions['tether_engine']) in SUPPORTED_PAIRS)


def launcher_proof(trusted):
    facade, core = package_root(trusted, 'tether'), package_root(trusted, 'tether_engine')
    first = capture(facade, exclude_cache=True)
    require(first == capture(facade, exclude_cache=True), 'EP-VERIFY-03',
            'Installed launcher code changed during capture')
    versions = dict(tether=literal_version(facade), tether_engine=literal_version(core))
    require(approved_versions(versions), 'EP-VERIFY-03', 'Unsupported installed package version')
    require(trusted.get('versions') == versions, 'EP-VERIFY-03',
            'Trusted runtime version differs from actual installed package')
    distributions = distribution_versions((facade, core))
    require(distributions['tether-target-agents'] in (None, versions['tether'])
            and distributions['tether-target-engine'] in (None, versions['tether_engine']),
            'EP-VERIFY-03', 'Installed distribution version differs')
    return dict(schema_version=1, method='tether.launcher_code.v2',
                facade_version=versions['tether'], core_version=versions['tether_engine'],
                installed_distributions=distributions, code=first)
