"""Source-inclusive verification of relocated receipts under the v0.2 admission policy.

Only caller-approved archive files are read. Original JSON, logical path strings,
and receipt fingerprints are never rewritten. Archived Python is hashed as data.
This module does not execute an archived verifier or attest scientific validity.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import replace
from datetime import datetime
from pathlib import Path, PurePosixPath, PureWindowsPath

from asof.chrono import EvidenceStore, Exclusion
from asof.contracts import (Availability, Case, Category, Citation, Claim, EvidencePacket, EvidenceStatus,
                            GroundedObservation, Profile, Snapshot, validate_observation)
from asof.features import FeatureVector, build_features
from asof.provenance import InputGraph, catalog_index, check_role
from asof.scorer import Prediction, ScorerArtifact, abstain, score
from asof.semantics import check_execution
from asof.serde import (ContractError, MAX_LEDGER_JSON_BYTES, MAX_NORMALIZED_JSON_BYTES,
                        decode, encode, fingerprint, freeze, parse_json)

POLICY = 'v0.2-compatibility-20261026'
LEGACY_FILES = ('run.json', 'inputs.json', 'ledger.json', 'features.json',
                'prediction.json', 'trace.jsonl', 'dossier.md')
V2_FILES = LEGACY_FILES + ('journal.jsonl',)


def _dependency_functions():
    return (InputGraph.__init__, InputGraph.closure, InputGraph.exclusion,
            Availability.exclusion, Case.validate, validate_observation, EvidenceStore.query,
            build_features, score, abstain, check_execution)


def _load_dependency_guard():
    """Identify the supported executing implementation, not archived Python execution."""
    resource = Path(__file__).with_name('semantic_dependencies.json')
    payload = resource.read_bytes()
    declarations = parse_json(payload)
    minimum = {'chrono.py', 'contracts.py', 'provenance.py', 'features.py', 'scorer.py',
               'serde.py', 'workflow.py', 'semantics.py', 'local_model.py', 'retrieval.py', 'agents.py'}
    if (type(declarations.get('schema_version')) is not int or declarations['schema_version'] != 1 or
            declarations.get('policy') != POLICY or not isinstance(declarations.get('modules'), dict) or
            not minimum <= set(declarations['modules'])):
        raise ContractError('Incomplete compatibility dependency resource')
    root = Path(__file__).resolve().parents[1]
    mismatches = []
    for name, expected in declarations['modules'].items():
        if ('/' in name or '\\' in name or not name.endswith('.py') or
                not isinstance(expected, str) or not re.fullmatch('[0-9a-f]{64}', expected)):
            raise ContractError('Invalid compatibility dependency resource')
        with (root / name).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                mismatches.append(name)
    return hashlib.sha256(payload).hexdigest(), tuple(mismatches), _dependency_functions()


_DEPENDENCY_RESOURCE_SHA256, _DEPENDENCY_MISMATCHES, _DEPENDENCY_FUNCTIONS = _load_dependency_guard()


def ensure_supported_semantics():
    need(not _DEPENDENCY_MISMATCHES, 'Unsupported executing semantic dependencies: ' + ', '.join(_DEPENDENCY_MISMATCHES))
    need(_dependency_functions() == _DEPENDENCY_FUNCTIONS, 'Executing semantic dependency changed after import')


def need(condition, message):
    if not condition:
        raise ContractError(message)


def logical(value):
    text = str(value)
    return PureWindowsPath(text) if PureWindowsPath(text).drive else PurePosixPath(text)


def child(base, relative):
    """Canonical original-host spelling; actual reads still use the resolver allowlist."""
    text = str(relative).replace('\\', '/')
    need(text and not text.startswith('/') and ':' not in text and
         all(p not in ('', '.', '..') for p in text.split('/')), 'Unsafe archive member')
    return str(logical(base).joinpath(*text.split('/')))


def read_json(resolver, path, limit=MAX_NORMALIZED_JSON_BYTES):
    payload = resolver.read_bytes(str(path), maximum_bytes=limit)
    need(len(payload) <= limit, 'Archived JSON exceeds its input bound')
    return parse_json(payload)


def chain_bytes(payload, allow_incomplete_tail=False):
    """Parse the exact verified bytes, rather than reopening a path after hashing."""
    events, previous = [], None
    lines = payload.splitlines()
    for index, line in enumerate(lines):
        if allow_incomplete_tail and index == len(lines)-1 and not payload.endswith(b'\n'):
            break
        event = parse_json(line)
        need(isinstance(event, dict), 'Invalid archive journal event')
        digest = event.pop('sha256', None)
        need(event.get('sequence') == len(events) and event.get('previous_sha256') == previous and
             digest == fingerprint(event), 'Archive journal chain mismatch')
        event['sha256'] = digest
        events.append(freeze(event))
        previous = digest
    return tuple(events)


def pinned(resolver, path, expected, size=None):
    entries = {resolver.logical_key(item['logical_path']): item for item in resolver.file_entries}
    item = entries.get(resolver.logical_key(str(path)))
    need(item is not None and item['sha256'] == expected and
         (size is None or type(size) is int and size == item['bytes']),
         'Archive declaration differs from original pin: ' + str(path))
    return resolver.verify_file(str(path))


class ArchiveGraph(InputGraph):
    """Original lineage semantics, mapped IO, and original proof identity strings."""

    def __init__(self, snapshot, case, logical_root, catalog, resolver):
        self.logical_root, self.resolver, self.case = str(logical(logical_root)), resolver, case
        super().__init__(snapshot, resolver.layout_path(self.logical_root), catalog)

    def original_path(self, node):
        base = self.logical_root if node.computed_at is not None else (self.snapshot.raw_root or self.logical_root)
        return child(base, node.path)

    def path(self, node):
        # The constructor validates even excluded future nodes; this maps layout
        # without granting permission to open an unregistered future source.
        return self.resolver.layout_path(self.original_path(node))

    def verify(self, refs, already):
        proofs = []
        for key in self.closure(refs):
            if key not in already:
                node = self.nodes[key]
                source = self.original_path(node)
                physical = pinned(self.resolver, source, node.sha256)
                proof = dict(artifact_id=key, dataset_id=node.dataset_id, release_id=node.release_id,
                             path=source, sha256=node.sha256, role=node.role, parents=node.parents)
                if node.receipt_path:
                    receipt_path = child(self.snapshot.raw_root or self.logical_root, node.receipt_path)
                    need(node.receipt_sha256 is not None, 'Input receipt checksum missing')
                    pinned(self.resolver, receipt_path, node.receipt_sha256)
                    receipt = read_json(self.resolver, receipt_path)
                    relative = receipt.get('relative_path')
                    need(isinstance(relative, str) and receipt.get('status') == 'completed' and
                         receipt.get('sha256') == node.sha256 and receipt.get('dataset_id') == node.dataset_id and
                         receipt.get('release_id') == node.release_id and receipt.get('bytes') == physical.stat().st_size and
                         self.resolver.logical_key(child(self.snapshot.raw_root or self.logical_root, relative)) ==
                         self.resolver.logical_key(source), 'Input receipt identity/status mismatch')
                    if node.availability.basis == 'public_download_receipt':
                        observed = decode(datetime, receipt.get('completed_at_utc'))
                        need(node.availability.known_public_by is not None and
                             node.availability.known_public_by >= observed and
                             node.availability.evidence_ref == node.receipt_sha256 and
                             node.source_url == receipt.get('url'),
                             'Contemporary availability bound differs from archived receipt')
                    proof.update(receipt_path=receipt_path, receipt_sha256=node.receipt_sha256)
                elif self.snapshot.profile != Profile.DEMO and node.computed_at is None:
                    raise ContractError('Real raw inputs require archived public-download receipts')
                already[key] = proof
            proofs.append(already[key])
        return tuple(proofs)


def observation_exclusion(observation, artifact, graph, case, artifact_inputs=None):
    """Frozen pre-recovery policy; a future live-policy change cannot alter old receipts."""
    validate_observation(observation)
    if observation.program_id is not None and case.program is not None and case.program.mapping_confidence == 0:
        return 'unresolved_program_mapping'
    artifact_inputs = artifact_inputs if artifact_inputs is not None else frozenset(graph.closure(artifact.input_refs))
    need(set(graph.closure(observation.input_refs)).issubset(artifact_inputs),
         "Observation lineage escapes its artifact's declared inputs")
    reason = graph.exclusion(observation.input_refs, case)
    if not reason and observation.source_kind != 'computed':
        reason = observation.availability.exclusion(case.cutoff)
    if not reason and (observation.publication_date is not None and observation.publication_date > case.origin or
                       observation.publication_year is not None and observation.publication_year > case.origin.year):
        reason = 'publication_after_origin'
    return reason


def eligible_artifacts(snapshot, graph, case):
    identifiers, paths = set(), set()
    for artifact in snapshot.artifacts:
        need(artifact.artifact_id.strip() and artifact.release_id.strip() and
             artifact.artifact_id not in identifiers and artifact.path not in paths and
             artifact.artifact_id not in graph.nodes, 'Artifact IDs/paths/releases are not unique')
        identifiers.add(artifact.artifact_id)
        paths.add(artifact.path)
        need(bool(re.fullmatch('[0-9a-f]{64}', artifact.sha256)), 'Invalid artifact SHA256')
        need(artifact.role == 'agent_evidence', 'Evaluator/reference-only artifact denied')
        graph.resolver.layout_path(child(graph.logical_root, artifact.path))
        if not artifact.access_approved:
            yield artifact, 'access_denied'
            continue
        check_role(artifact.dataset_id, artifact.role, graph.catalog)
        yield artifact, graph.exclusion(artifact.input_refs, case)


def rebuild_values(case, snapshot, logical_root, policy, resolver):
    ensure_supported_semantics()
    case.validate()
    need(snapshot.schema_version == 2 and snapshot.snapshot_id.strip(), 'Archive requires v2 snapshot')
    need(snapshot.origin == case.origin and snapshot.origin_at == case.origin_at, 'Snapshot origin differs')
    need(snapshot.profile == Profile.DEMO or policy is not None, 'Missing archived effective catalog')
    catalog = catalog_index(policy) if snapshot.profile != Profile.DEMO else None
    graph = ArchiveGraph(snapshot, case, logical_root, catalog, resolver)
    records, exclusions, proofs, parents, seen = [], [], [], {}, set()
    for artifact, reason in eligible_artifacts(snapshot, graph, case):
        if reason:
            exclusions.append(Exclusion(artifact.artifact_id, 'artifact', reason))
            continue
        path = child(logical_root, artifact.path)
        payload = resolver.read_bytes(path, maximum_bytes=MAX_NORMALIZED_JSON_BYTES)
        need(len(payload) <= MAX_NORMALIZED_JSON_BYTES and hashlib.sha256(payload).hexdigest() == artifact.sha256,
             'Archived artifact checksum/size differs')
        packet = decode(EvidencePacket, parse_json(payload), artifact.artifact_id)
        need(packet.schema_version == 2, 'Unsupported evidence-packet version')
        proofs.append(dict(artifact_id=artifact.artifact_id, dataset_id=artifact.dataset_id,
                           release_id=artifact.release_id, path=path, sha256=artifact.sha256))
        citation = Citation(artifact.artifact_id, artifact.dataset_id, artifact.release_id, artifact.sha256, artifact.source_url)
        artifact_inputs = frozenset(graph.closure(artifact.input_refs))
        for observation in packet.observations:
            need(observation.observation_id not in seen, 'Duplicate observation ID')
            seen.add(observation.observation_id)
            reason = observation_exclusion(observation, artifact, graph, case, artifact_inputs)
            if reason:
                exclusions.append(Exclusion(observation.observation_id, 'observation', reason))
                continue
            records.append(GroundedObservation(observation, citation))
            graph.verify(observation.input_refs, parents)
        graph.verify(artifact.input_refs, parents)
    store = EvidenceStore(snapshot, tuple(records), tuple(exclusions), tuple(proofs)+tuple(parents.values()), policy,
                          snapshot_base=resolver.layout_path(logical_root))
    store.snapshot_base = str(logical(logical_root))
    store.archive_graph = graph
    return store


def rebuild_store(source, resolver):
    """Re-admit an interpretation source archive without modifying its path identities."""
    expected = [source['case_path'], source['snapshot_path']] + ([source['catalog_path']] if source['catalog_path'] else [])
    need(isinstance(source['inputs'], list) and [p.get('path') for p in source['inputs']] == expected,
         'Foreign/missing source input pins')
    for proof in source['inputs']:
        pinned(resolver, proof['path'], proof['sha256'], proof['bytes'])
    case = decode(Case, read_json(resolver, source['case_path']))
    snapshot = decode(Snapshot, read_json(resolver, source['snapshot_path']))
    policy = read_json(resolver, source['catalog_path']) if snapshot.profile != Profile.DEMO and source['catalog_path'] else None
    store = rebuild_values(case, snapshot, str(logical(source['snapshot_path']).parent), policy, resolver)
    need(fingerprint(store.source_proofs) == fingerprint(source['source_proofs']) and
         fingerprint(store.catalog_policy) == fingerprint(source['effective_catalog']),
         'Rebuilt source proof inventory/policy differs')
    return case, store


def verify_core_archive(logical_run, resolver, expected_receipt_sha256, *, code_root):
    """Verify immutable original receipts using mapped sources and frozen v0.2 rules."""
    ensure_supported_semantics()
    receipt_payload = resolver.read_bytes(child(logical_run, 'receipt.json'), maximum_bytes=MAX_NORMALIZED_JSON_BYTES)
    need(hashlib.sha256(receipt_payload).hexdigest() == expected_receipt_sha256,
         'External receipt anchor mismatch')
    receipt = parse_json(receipt_payload)
    legacy = receipt.get('schema_version') == 1
    need(type(receipt.get('schema_version')) is int and receipt['schema_version'] in (1, 2), 'Invalid receipt version')
    required = LEGACY_FILES if legacy else V2_FILES
    need(set(receipt.get('outputs', {})) == set(required), 'Incomplete receipt output set')
    for name, expected in receipt['outputs'].items():
        pinned(resolver, child(logical_run, name), expected)
    auxiliary = receipt.get('auxiliary_outputs', {})
    need(isinstance(auxiliary, dict) and not set(auxiliary)-{'request.json', 'backend-execution.json'}, 'Invalid auxiliary inventory')
    for name, expected in auxiliary.items():
        pinned(resolver, child(logical_run, name), expected)
    inputs = read_json(resolver, child(logical_run, 'inputs.json'))
    need(fingerprint(inputs) == receipt['input_fingerprint'], 'Input fingerprint mismatch')
    trace_payload = resolver.read_bytes(child(logical_run, 'trace.jsonl'))
    trace = chain_bytes(trace_payload)
    if not legacy:
        need(resolver.read_bytes(child(logical_run, 'journal.jsonl')) == trace_payload, 'Durable journal/trace mismatch')
    code = receipt.get('code')
    minimum = {'__init__.py', '__main__.py', 'agents.py', 'artifacts.py', 'chrono.py', 'cli.py',
               'contracts.py', 'evaluation.py', 'features.py', 'ledger.py', 'scorer.py', 'serde.py', 'workflow.py'}
    if not legacy:
        minimum.update({'journal.py', 'provenance.py', 'semantics.py'})
    need(isinstance(code, dict) and minimum <= set(code), 'Missing original code inventory')
    for name, expected in code.items():
        pinned(resolver, child(code_root, name), expected)
    if legacy:
        for proof in receipt['sources']:
            path = proof['path'] if logical(proof['path']).is_absolute() else child(logical_run, proof['path'])
            pinned(resolver, path, proof['sha256'])
            if proof.get('receipt_path'):
                pinned(resolver, proof['receipt_path'], proof['receipt_sha256'])
    else:
        case, snapshot = decode(Case, inputs['case']), decode(Snapshot, inputs['snapshot'])
        policy = inputs['catalog_policy']
        store = rebuild_values(case, snapshot, inputs['snapshot_base'], policy, resolver)
        actual, expected = ({p['artifact_id']: p for p in values} for values in (receipt['sources'], store.source_proofs))
        need(len(actual) == len(receipt['sources']) and fingerprint(actual) == fingerprint(expected),
             'Eligible artifact/ancestor proof inventory differs')
        need(fingerprint(store.admitted_fingerprints) == fingerprint(receipt['admitted_fingerprints']),
             'Source-to-admission fingerprints differ')
        run = read_json(resolver, child(logical_run, 'run.json'))
        ledger = read_json(resolver, child(logical_run, 'ledger.json'), MAX_LEDGER_JSON_BYTES)
        need(ledger.get('schema_version') == 2 and run['input_fingerprint'] == receipt['input_fingerprint'],
             'Run/ledger schema or input fingerprint mismatch')
        claims = decode(tuple[Claim, ...], ledger['claims'])
        need(fingerprint(store.exclusions) == fingerprint(run['exclusions']), 'Source exclusions differ')
        for category, coverage in run['coverage'].items():
            records = store.query(case, Category(category))
            nonobserved = [dict(observation_id=r.observation.observation_id, status=r.observation.status.value,
                                reason=r.observation.statement) for r in records if r.observation.status != EvidenceStatus.OBSERVED]
            need(coverage['available_observations'] == sum(r.observation.status == EvidenceStatus.OBSERVED for r in records)
                 and fingerprint(nonobserved) == fingerprint(coverage['nonobserved'])
                 and fingerprint(snapshot.coverage) == fingerprint(coverage['source_coverage']), 'Source coverage differs')
        if run['backend_id'] == 'local-structured-selection-v1':
            from asof.local_model import verify_backend_execution
            from asof.retrieval import RetrievalPolicy, verify_retrieval_trace
            need('backend-execution.json' in auxiliary, 'Missing sealed backend archive')
            verify_backend_execution(read_json(resolver, child(logical_run, 'backend-execution.json')),
                                     trace, inputs['configuration'])
            verify_retrieval_trace(case, store, trace, RetrievalPolicy(**inputs['configuration']['backend_provenance']['config']['retrieval']))
        model = decode(ScorerArtifact, inputs['scorer']) if inputs['scorer'] else None
        check_execution(run, case, snapshot, inputs['configuration'], claims, trace)
        _check_semantics(case, snapshot, claims,
                         decode(FeatureVector, read_json(resolver, child(logical_run, 'features.json'))),
                         decode(Prediction, read_json(resolver, child(logical_run, 'prediction.json'))),
                         run['coverage'], inputs['configuration'], run['status'], model,
                         receipt['admitted_fingerprints'], policy, store.archive_graph, trace)
    return dict(status='relocated_receipt_verified', byte_integrity='verified',
                semantic_consistency='unavailable_legacy_v1' if legacy else 'verified',
                source_binding='relocated_verified_original_bytes', source_artifacts_checked=len(receipt['sources']),
                code_archive_integrity='verified_original_pins', code_files_checked=len(receipt.get('code', {})),
                executing_policy=POLICY, executing_dependency_resource_sha256=_DEPENDENCY_RESOURCE_SHA256,
                archived_code_executed=False, external_anchor_checked=True,
                scientific_validity='not_established', trace_events=len(trace))


# Frozen v0.2 semantic rules; all lineage IO is supplied by ArchiveGraph.
def _check_semantics(case, snapshot, claims, features, prediction, coverage, configuration,
                    status, model, admitted, catalog_policy, graph, trace):
    case.validate()
    if snapshot.schema_version != 2 or snapshot.origin_at != case.origin_at or snapshot.origin != case.origin:
        raise ContractError("Semantic case/snapshot origin mismatch")
    if snapshot.profile != Profile.DEMO and not catalog_policy:
        raise ContractError("Semantic real-data snapshot requires archived catalog policy")
    seen = set()
    artifacts = {item.artifact_id: item for item, reason in eligible_artifacts(snapshot, graph, case) if reason is None}
    artifact_inputs = {key: frozenset(graph.closure(item.input_refs)) for key, item in artifacts.items()}
    for claim in claims:
        observation, citation = claim.evidence.observation, claim.evidence.citation
        digest = fingerprint(claim.evidence)
        if digest != claim.admitted_fingerprint or digest != admitted.get(observation.observation_id):
            raise ContractError("Semantic source-to-claim fingerprint mismatch")
        if observation.observation_id in seen:
            raise ContractError("Semantic duplicate claim")
        seen.add(observation.observation_id)
        if (observation.target_id != case.hypothesis.target_id or observation.indication_id != case.hypothesis.indication_id or
                claim.specialist != observation.category or
                not case.permits_program(observation.program_id)):
            raise ContractError("Semantic claim outside hypothesis/program capability")
        artifact = artifacts.get(citation.artifact_id)
        if (artifact is None or citation.artifact_sha256 != artifact.sha256 or
                citation.dataset_id != artifact.dataset_id or citation.release_id != artifact.release_id or
                citation.source_url != artifact.source_url):
            raise ContractError("Semantic citation mismatch")
        if (observation_exclusion(observation, artifact, graph, case, artifact_inputs[artifact.artifact_id]) or
                observation.status != EvidenceStatus.OBSERVED):
            raise ContractError("Semantic claim contains ineligible information")
        expected_id = "claim-" + fingerprint({"case": case.case_id, "evidence": claim.evidence})[:20]
        if claim.claim_id != expected_id or claim.extraction_mode != "verbatim_source_selection":
            raise ContractError("Semantic claim identity mismatch")
    counts = Counter(claim.specialist.value for claim in claims)
    for category, item in coverage.items():
        if item["selected_observations"] != counts[category]:
            raise ContractError("Semantic coverage/ledger mismatch")
    missingness = {category: tuple(item["status"] for item in value["nonobserved"])
                   + (("source_incomplete",) if snapshot.coverage and
                      snapshot.coverage.get("source_completeness") != "complete" else ())
                   for category, value in coverage.items()}
    rebuilt = build_features(claims, case, missingness)
    if fingerprint(rebuilt) != fingerprint(features):
        raise ContractError("Semantic ledger-to-feature mismatch")
    expected = abstain(case, "run_incomplete", model) if status != "completed" else score(case, snapshot.profile, rebuilt, model)
    if snapshot.profile == Profile.DEMO:
        expected = replace(expected, synthetic=True)
    if fingerprint(expected) != fingerprint(prediction):
        raise ContractError("Semantic feature-to-prediction mismatch")
    if not trace or trace[-1]["event"] != "finalize":
        raise ContractError("Semantic final trace event missing")
    final = trace[-1]["details"]
    if (final["feature_sha256"] != fingerprint(features) or
            final["prediction_sha256"] != fingerprint(prediction) or final["status"] != status):
        raise ContractError("Semantic trace/output fingerprint mismatch")
    if configuration.get("hypothesis_key") != case.hypothesis.key:
        raise ContractError("Semantic hypothesis key mismatch")
