"""Fixed scopes and budgets for the separately authorized SC05 condition.

Low-level immutable file proofs are shared with the established reader. Old
recovery authorities and continuation schedules are deliberately not reused.
"""
from pathlib import Path
from uuid import UUID

from tether_engine.serde import freeze
from experiments.litqa_refinement_recovery.contracts import (
    capture, finite, fingerprint, need, path, read, write,
)

ROOT = Path(__file__).resolve().parents[2]
PHASES = ('repair', 'removal')
PURPOSES = ('production', 'fictional_qualification')
TERMINAL_STATUSES = ('completed', 'capacity', 'codec_failure')
CELL_LIMITS = freeze(dict(generation_calls=1, reserved_input_tokens=16128,
                         reserved_output_tokens=256, source_http_requests=0,
                         safety_accounted_bytes=0, provider_cost_usd=0))


def schedule(ids, purpose):
    ids = tuple(ids)
    need(purpose in PURPOSES, 'Explicit evidence-first purpose required')
    need(len(ids) == (199 if purpose == 'production' else 6) and
         len(set(ids)) == len(ids), 'Complete unique evidence-first schedule required')
    need(all(isinstance(value, str) and str(UUID(value)) == value for value in ids),
         'Canonical scheduled identities required')
    return ids


def budgets(purpose):
    need(purpose in PURPOSES, 'Unknown evidence-first budget purpose')
    production = purpose == 'production'
    calls = 398 if production else 12
    return freeze(dict(
        generation_calls=calls, reserved_input_tokens=calls * 16128,
        reserved_output_tokens=calls * 256, source_http_requests=0, provider_cost_usd=0,
        phase_seconds=dict(repair=6419 if production else 1200,
                           removal=7200 if production else 1200),
        repair_stage_seconds=6401 if production else 1200,
        outer_seconds=39018 if production else 3600,
        call_seconds=120, automatic_retry=False))


def identity(parent_identity, method_identity):
    """One logical experiment regardless of output path or process restart."""
    for value in (parent_identity, method_identity):
        need(isinstance(value, str) and len(value) == 64 and
             all(c in '0123456789abcdef' for c in value), 'Canonical SHA256 identity required')
    return fingerprint(dict(kind='evidence_first_authority_v1',
                            parent=parent_identity, method=method_identity))


def authority_registry(purpose):
    need(purpose in PURPOSES, 'Unknown authority purpose')
    return path(ROOT / 'data/benchmark/litqa_evidence_first/authority' / purpose)
