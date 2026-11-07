"""Fixed, inspectable aggregation with explicit evidence dependence/missingness."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import mean
from collections.abc import Mapping

from .contracts import Case, Claim, FEATURE_CATEGORIES
from .serde import Frozen


FEATURE_SCHEMA = "tether-features-v2"


@dataclass(frozen=True)
class Feature(Frozen):
    value: float | None
    status: str
    dependency_groups: int
    observation_ids: tuple[str, ...]
    excluded_groups: tuple[str, ...]
    missing_reasons: tuple[str, ...] = ()


@dataclass(frozen=True)
class FeatureVector(Frozen):
    schema_version: str
    aggregation: str
    values: Mapping[str, Feature]


def build_features(claims: tuple[Claim, ...], case: Case, missingness: Mapping | None = None) -> FeatureVector:
    # Join known dependence through explicit groups, study identity and shared cohorts.
    # Different names do not prove independent sampling; unknown overlap still needs review.
    observations = [claim.evidence.observation for claim in claims]
    parent = {item.observation_id: item.observation_id for item in observations}

    def find(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    identities = {}
    for item in observations:
        keys = []
        if item.dependency_group:
            keys.append(("group", item.dependency_group))
        if item.study_id:
            keys.append(("study", item.study_id))
        keys.extend(("cohort", cohort) for cohort in item.context.cohort_ids)
        for key in keys:
            if key in identities:
                parent[find(item.observation_id)] = find(identities[key])
            else:
                identities[key] = item.observation_id
    labels = {}
    for item in observations:
        representative = find(item.observation_id)
        label = item.dependency_group or "unknown-dependence:" + item.observation_id
        labels[representative] = min(labels.get(representative, label), label)
    # Conflicting values inside a component are not averaged.
    groups = defaultdict(lambda: defaultdict(list))
    for claim in claims:
        observation = claim.evidence.observation
        if observation.feature_scope != case.hypothesis.key:
            continue
        for name, value in observation.features.items():
            group = labels[find(observation.observation_id)]
            groups[name][group].append((observation.observation_id, value))
    features = {}
    for name in FEATURE_CATEGORIES:
        admitted, excluded, observation_ids = [], [], []
        for group, entries in sorted(groups[name].items()):
            unique = {value for _, value in entries}
            if len(unique) != 1:
                excluded.append(group)
                continue
            admitted.append(next(iter(unique)))
            observation_ids.extend(item[0] for item in entries)
        status = "observed" if admitted else ("conflicting" if excluded else "not_measured")
        reasons = set((missingness or {}).get(FEATURE_CATEGORIES[name].value, ())) if not admitted else set()
        if any(name in item.features and item.feature_scope != case.hypothesis.key for item in observations):
            reasons.add("outside_applicability")
        features[name] = Feature(mean(admitted) if admitted else None, status, len(admitted),
                                 tuple(sorted(observation_ids)), tuple(excluded), tuple(sorted(reasons)))
    return FeatureVector(FEATURE_SCHEMA, "mean_of_unique_dependency_groups_v2", features)

