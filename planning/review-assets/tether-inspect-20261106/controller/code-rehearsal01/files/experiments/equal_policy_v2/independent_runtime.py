"""Exact supported runtime pairs for the versioned comparison; no product imports."""
from equal_policy.independent import require
from equal_policy.independent_runtime import (
    package_root, capture, literal_version, distribution_versions,
)


SUPPORTED_PAIRS = frozenset({('0.5.1', '0.3.12'), ('0.5.2', '0.3.13')})


def approved_versions(versions):
    return (type(versions) is dict and set(versions) == {'tether', 'asof'}
            and type(versions['tether']) is str and type(versions['asof']) is str
            and (versions['tether'], versions['asof']) in SUPPORTED_PAIRS)


def launcher_proof(trusted):
    facade, core = package_root(trusted, 'tether'), package_root(trusted, 'asof')
    first = capture(facade, exclude_cache=True)
    require(first == capture(facade, exclude_cache=True), 'EP-VERIFY-03',
            'Installed launcher code changed during capture')
    versions = dict(tether=literal_version(facade), asof=literal_version(core))
    require(approved_versions(versions), 'EP-VERIFY-03', 'Unsupported installed package version')
    require(trusted.get('versions') == versions, 'EP-VERIFY-03',
            'Trusted runtime version differs from actual installed package')
    distributions = distribution_versions((facade, core))
    require(distributions['tether-target-agents'] in (None, versions['tether'])
            and distributions['asof-target-agents'] in (None, versions['asof']),
            'EP-VERIFY-03', 'Installed distribution version differs')
    return dict(schema_version=1, method='tether.launcher_code.v1',
                facade_version=versions['tether'], core_version=versions['asof'],
                installed_distributions=distributions, code=first)
