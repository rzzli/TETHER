"""Restrict role outputs before generation while preserving all visible science.

The operational correction is explicit: reviewer/synthesis may remove prior IDs,
but cannot restore an ID the preceding accepted role removed. This is a trusted
payload constraint, not a scientific adjudication or a post-selection filter.
"""
from __future__ import annotations

import re

from tether_engine.local_model import LocalSelectionBackend, selection_payload, validate_selection_cap
from tether_engine.serde import ContractError, parse_json


ROLE_SELECTION_POLICY = 'science7-prior-stage-output-schema-v1'
STAGES = ('chief_of_staff', 'coordinator_delegate', 'mapped_specialist',
          'scientific_reviewer', 'coordinator_synthesize')


def role_allowed_ids(request, selection_cap=3):
    """Reconstruct a bounded output scope from the immutable request alone."""
    selection_cap = validate_selection_cap(selection_cap)
    visible = tuple(row.observation_id for row in request.evidence)
    if len(visible) != len(set(visible)):
        raise ContractError('Role request contains duplicate visible IDs')
    markers = re.findall(r'(?:^|\n)Role: ([a-z_]+); mapped upstream specialist:', request.instructions)
    if len(markers) != 1 or markers[0] not in STAGES:
        raise ContractError('Role request needs one explicit recognized stage')
    stage = markers[0]
    if len(request.feedback) > 1:
        raise ContractError('Role request feedback must contain one prior-role document')
    prior = []
    if request.feedback:
        document = parse_json(request.feedback[0])
        if not isinstance(document, dict) or set(document) != {'prior_role_choices'}:
            raise ContractError('Role feedback lacks the exact prior-role choices contract')
        prior = document['prior_role_choices']
        if not isinstance(prior, list) or not prior:
            raise ContractError('Role feedback must name its accepted prior stages')
    expected_count = STAGES.index(stage)
    if len(prior) != expected_count and not (stage == 'mapped_specialist' and not prior):
        raise ContractError('Role stage and prior-role history differ')
    for index, row in enumerate(prior):
        if (not isinstance(row, dict) or set(row) != {'role', 'observation_ids'} or
                row['role'] != STAGES[index] or not isinstance(row['observation_ids'], list)):
            raise ContractError('Role feedback must retain the exact accepted stage prefix')
        ids = row['observation_ids']
        if (any(not isinstance(identity, str) for identity in ids) or len(ids) > selection_cap or
                len(ids) != len(set(ids)) or set(ids) - set(visible)):
            raise ContractError('Role feedback contains unavailable, duplicate or unbounded IDs')
        if index == 3 and set(ids) - set(prior[index-1]['observation_ids']):
            raise ContractError('Accepted reviewer history restores an unaccepted specialist ID')
    if stage in ('scientific_reviewer', 'coordinator_synthesize'):
        accepted = set(prior[-1]['observation_ids'])
        return tuple(identity for identity in visible if identity in accepted)
    return visible


def role_selection_payload(request, maximum, seed, wire_format='canonical', selection_cap=3):
    """Change only the output schema; keep the complete candidate prompt intact."""
    allowed = role_allowed_ids(request, selection_cap)
    payload = selection_payload(request, maximum, seed, wire_format, selection_cap)
    output = payload['json_schema']['properties']['observation_ids']
    if allowed:
        output['items']['enum'] = list(allowed)
        output['maxItems'] = min(selection_cap, len(allowed))
    else:
        # Empty enums are not accepted by some native JSON grammars. The visible
        # enum is unchanged and maxItems=0 permits exactly the empty array.
        output['maxItems'] = 0
    return payload


class RoleSelectionBackend(LocalSelectionBackend):
    """Use one model/configuration and the same control rule for all arms."""

    output_scope_policy = 'native_json_schema_reviewed_subset_v1'

    def __init__(self, config_path):
        super().__init__(config_path)
        self.provenance['selection_policy'] = ROLE_SELECTION_POLICY

    def payload_for(self, request):
        return role_selection_payload(request, self.max_output, self.seed, self.policy.wire_format, self.selection_cap)
