"""Standalone equal-policy validator, implemented without product imports.

Only the Python standard library and the experiment's own contract tables are
used. This module reads existing inputs and produces no model calls or runtime
artifacts. Validation results are technical policy decisions, not scientific
judgments. See the separately frozen policy/oracle before benchmark scoring.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time as clock

from .independent_schema import (CATEGORIES, FEATURES, SIGNED_FEATURES,
                                 PolicyError, decode, require, timestamp)

NORMAL_LIMIT = 64 * 1024 * 1024
LEDGER_LIMIT = 256 * 1024 * 1024
SHA = re.compile(r'[0-9a-f]{64}\Z')
FEATURE_SCHEMA = 'tether-features-v2'
AGGREGATION = 'mean_of_unique_dependency_groups_v2'
RUN_FILES = ('run.json', 'inputs.json', 'ledger.json', 'features.json',
             'prediction.json', 'trace.jsonl', 'dossier.md', 'journal.jsonl')


class UnsupportedPolicy(Exception):
    """Explicitly unavailable interface, never an admissible policy decision."""


def object_fields(value, fields, obligation, location):
    require(type(value) is dict and set(fields) <= value.keys(), obligation,
            location + ': missing required object fields')
    return value


def descriptor_contract(value):
    object_fields(value, ('schema_version', 'control_id', 'operation', 'variant', 'paths', 'options', 'anchors'), 'EP-WIRE-01', 'Descriptor')
    require(set(value) == {'schema_version', 'control_id', 'operation', 'variant', 'paths', 'options', 'anchors'}
        and type(value['schema_version']) is int and value['schema_version'] == 1
        and type(value['control_id']) is str and bool(value['control_id'].strip()), 'EP-WIRE-01', 'Invalid descriptor identity/keys')
    require(value['operation'] in ('prepare_run', 'verify_run', 'inspect_run')
        and value['variant'] in ('core_v2_catalog1', 'artifact_policy_v2'), 'EP-WIRE-01', 'Invalid operation/variant')
    allowed = dict(paths={'case', 'snapshot', 'catalog', 'scorer', 'replay', 'local_model', 'catalog_policy', 'policy_roots', 'run_dir', 'trusted_runtime'},
        options={'budget', 'disabled', 'review_enabled', 'process_limits', 'policy_use'},
        anchors={'receipt_sha256', 'frame_sha256'})
    result = dict(value)
    for section, names in allowed.items():
        document = value[section]
        require(type(document) is dict and not set(document) - names, 'EP-WIRE-01', 'Invalid descriptor ' + section)
        result[section] = {key: item for key, item in document.items() if item is not None or section != 'paths'}
    paths, options, anchors = result['paths'], result['options'], result['anchors']
    for key, path in paths.items():
        require(type(path) is str and bool(path), 'EP-WIRE-01', 'Invalid path: ' + key)
        pieces = path.replace('\\', '/').split('/')
        require(not path.startswith(('/', '\\')) and ':' not in path and all(x not in ('', '.', '..') for x in pieces),
                'EP-WIRE-01', 'Unsafe descriptor path')
    required = ('case', 'snapshot') if result['operation'] == 'prepare_run' else ('run_dir',)
    require(all(key in paths for key in required), 'EP-WIRE-01', 'Required operation path missing')
    require(all(type(v) is str and SHA.fullmatch(v) for v in anchors.values()), 'EP-WIRE-01', 'Malformed descriptor anchor')
    validate_budget(options.get('budget', {}))
    require('process_limits' not in options or type(options['process_limits']) is dict,
            'EP-WIRE-01', 'Process limits must be an object')
    validate_process_limits(options.get('process_limits'))
    require(type(options.get('disabled', [])) is list and all(type(x) is str and x in CATEGORIES for x in options.get('disabled', []))
        and type(options.get('review_enabled', True)) is bool, 'EP-WIRE-01', 'Invalid specialist/review configuration')
    require('policy_use' not in options or (type(options['policy_use']) is str and options['policy_use']), 'EP-WIRE-01', 'Invalid policy use')
    if result['variant'] == 'core_v2_catalog1':
        require(not any(key in paths for key in ('catalog_policy', 'policy_roots')) and 'policy_use' not in options
            and 'frame_sha256' not in anchors, 'EP-WIRE-01', 'Artifact-policy options on core variant')
    if result['operation'] != 'prepare_run':
        require(not set(paths) - {'run_dir', 'trusted_runtime'} and not options and 'frame_sha256' not in anchors,
                'EP-WIRE-01', 'Preparation fields supplied to read-only operation')
    else:
        require('run_dir' not in paths and 'receipt_sha256' not in anchors, 'EP-WIRE-01', 'Execution output fields on preparation')
        if result['variant'] == 'artifact_policy_v2':
            require({'catalog', 'catalog_policy', 'policy_roots'} <= paths.keys()
                and 'policy_use' in options and 'frame_sha256' in anchors,
                'EP-WIRE-01', 'Required artifact-policy preparation controls are missing')
    return result


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def parse(payload):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'EP-WIRE-01', 'Duplicate JSON property')
            result[key] = value
        return result

    def invalid(value):
        raise PolicyError('EP-WIRE-01', 'Nonfinite JSON constant')

    try:
        return json.loads(payload.decode('utf-8-sig') if isinstance(payload, bytes) else payload,
                          object_pairs_hook=pairs, parse_constant=invalid)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise PolicyError('EP-WIRE-01', 'Invalid JSON syntax/encoding') from error


def bytes_digest(payload):
    return hashlib.sha256(payload).hexdigest()


def file_digest(path):
    hasher = hashlib.sha256()
    try:
        with Path(path).open('rb') as stream:
            while chunk := stream.read(1024 * 1024):
                hasher.update(chunk)
    except FileNotFoundError as error:
        raise PolicyError('EP-IO-01', 'Required file missing: ' + str(path)) from error
    return hasher.hexdigest()


def read_json(path, maximum=NORMAL_LIMIT):
    path = Path(path)
    try:
        require(path.stat().st_size <= maximum, 'EP-IO-01', 'JSON size limit')
        with path.open('rb') as stream:
            payload = stream.read(maximum + 1)
    except FileNotFoundError as error:
        raise PolicyError('EP-IO-01', 'Required JSON file missing: ' + str(path)) from error
    require(len(payload) <= maximum, 'EP-IO-01', 'JSON size limit during read')
    return parse(payload)


def bounded_stable_bytes(path, maximum=NORMAL_LIMIT):
    """Facade metadata read bound, identity check and no-link boundary."""
    path = Path(path).absolute()
    deadline = clock.monotonic() + 300

    def no_links():
        for part in (*reversed(path.parents), path):
            info = part.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                    'EP-IO-01', 'Metadata path has symlink/reparse point')

    def identity(info):
        return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns

    try:
        no_links()
        before = path.stat()
        require(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, 'EP-IO-01', 'Nonregular/oversized metadata')
        chunks, size = [], 0
        with path.open('rb') as stream:
            require(identity(os.fstat(stream.fileno())) == identity(before), 'EP-IO-01', 'Metadata changed before read')
            while True:
                require(clock.monotonic() < deadline, 'EP-IO-01', 'Metadata read deadline exceeded')
                block = stream.read(min(1024 * 1024, maximum + 1 - size))
                if not block:
                    break
                size += len(block)
                require(size <= maximum, 'EP-IO-01', 'Metadata grew beyond read bound')
                chunks.append(block)
            after = os.fstat(stream.fileno())
        no_links()
        require(identity(before) == identity(after) == identity(path.stat()) and size == before.st_size,
                'EP-IO-01', 'Metadata changed during read')
        return b''.join(chunks)
    except FileNotFoundError as error:
        raise PolicyError('EP-IO-01', 'Required metadata missing: ' + str(path)) from error


def _ordinary_windows_path(path):
    spelling = str(path)
    if os.name != 'nt':
        return Path(path)
    require(not spelling.startswith(('\\\\.\\', '\\??\\')), 'EP-IO-01', 'Device path denied')
    if not spelling.startswith('\\\\?\\'):
        return Path(path)
    tail = spelling[4:]
    pieces = tail.split('\\')
    for index, piece in enumerate(pieces):
        if not piece and index == len(pieces) - 1:
            continue
        require(bool(piece) and not piece.endswith(('.', ' ')), 'EP-IO-01', 'Non-equivalent extended path')
        require(':' not in piece or (index == 0 and len(piece) == 2 and piece[1] == ':'),
                'EP-IO-01', 'Extended path component denied')
    if tail[:4].upper() == 'UNC\\':
        require(len(tail[4:].split('\\')) >= 2 and all(x not in ('', '.', '..')
            for x in tail[4:].split('\\')[:2]), 'EP-IO-01', 'Invalid UNC path')
        return Path('\\\\' + tail[4:])
    require(bool(re.match(r'^[A-Za-z]:\\', tail)), 'EP-IO-01', 'Extended device path denied')
    return Path(tail)


def child(root, relative):
    require(type(relative) is str and relative and not relative.startswith(('/', '\\'))
            and ':' not in relative, 'EP-IO-01', 'Relative file path required')
    parts = relative.replace('\\', '/').split('/')
    require(all(x not in ('', '.', '..') for x in parts), 'EP-IO-01', 'Unsafe relative path')
    root = _ordinary_windows_path(Path(root)).resolve()
    resolved = _ordinary_windows_path(root.joinpath(*parts).resolve())
    require(resolved.is_relative_to(_ordinary_windows_path(root)), 'EP-IO-01', 'Path escapes root')
    return resolved


def hypothesis_key(case):
    return digest({key: case['hypothesis'][key] for key in (
        'target_id', 'indication_id', 'target_namespace_version', 'indication_namespace_version',
        'intended_action', 'modality', 'tissue')})


def availability_reason(availability, cutoff):
    cutoff = timestamp(cutoff) if isinstance(cutoff, str) else cutoff
    values = [date.fromisoformat(availability[key]) for key in (
        'first_public_at', 'release_public_at', 'record_public_at', 'annotation_public_at')
        if availability[key] is not None]
    if not availability['basis'].strip():
        return 'availability_unverified'
    if any(datetime.combine(value, time.max, timezone.utc) > cutoff for value in values):
        return 'available_after_origin'
    retrieved = date.fromisoformat(availability['retrieved_at'])
    if any(value > retrieved for value in values):
        return 'availability_after_retrieval'
    if availability['known_public_by'] is not None:
        observed = timestamp(availability['known_public_by'])
        if not availability['evidence_ref']:
            return 'availability_proof_invalid'
        if observed > cutoff:
            return 'available_after_origin'
        if observed.date() > retrieved:
            return 'availability_after_retrieval'
    elif len(values) != 4:
        return 'availability_unverified'
    return None


def validate_case(case):
    require(case['schema_version'] == 2 and case['task'] in ('T1', 'T6'), 'EP-CASE-01', 'Unsupported case')
    require(case['origin_at'] is not None and timestamp(case['origin_at']).date().isoformat() == case['origin'],
            'EP-CASE-01', 'Exact origin date/timestamp mismatch')
    hypothesis = case['hypothesis']
    require(all(value.strip() for value in [case['case_id']] + [hypothesis[key] for key in (
        'target_id', 'indication_id', 'target_namespace_version', 'indication_namespace_version',
        'intended_action', 'modality')]), 'EP-CASE-01', 'Empty identity/hypothesis')
    require(availability_reason(hypothesis['availability'], case['origin_at']) is None,
            'EP-TIME-01', 'Unavailable hypothesis normalization')
    program = case['program']
    if program is not None:
        require(availability_reason(program['availability'], case['origin_at']) is None,
                'EP-PROGRAM-01', 'Unavailable program information')
        require(all(program[key].strip() for key in ('program_id', 'molecule_id', 'sponsor', 'status_at_origin')),
                'EP-PROGRAM-01', 'Empty program identity')
        require(0 <= program['phase_at_origin'] <= 4 and 0 <= program['mapping_confidence'] <= 1,
                'EP-PROGRAM-01', 'Program phase/confidence invalid')
        require(program['eligible_since'] <= case['origin'], 'EP-PROGRAM-01', 'Program not yet eligible')
    if case['task'] == 'T1':
        endpoint = case['endpoint']
        require(program is not None and endpoint is not None, 'EP-PROGRAM-01', 'T1 program/endpoint missing')
        phase = program['phase_at_origin']
        require(phase in (1, 2) and endpoint['name'] == f'phase_{phase}_to_{phase + 1}'
                and endpoint['horizon_months'] > 0 and program['status_at_origin'] == 'active'
                and program['mapping_confidence'] > 0, 'EP-PROGRAM-01', 'T1 endpoint/eligibility invalid')


def catalog_index(catalog):
    if catalog is None:
        return None
    require(type(catalog) is dict and catalog.get('schema_version') == 1, 'EP-DAG-01', 'Unsupported source catalog')
    rows = catalog.get('datasets', [])
    require(type(rows) is list and all(type(row) is dict and 'dataset_id' in row for row in rows),
            'EP-DAG-01', 'Invalid catalog dataset inventory')
    result = {row['dataset_id']: row for row in rows}
    require(len(result) == len(rows), 'EP-DAG-01', 'Duplicate catalog product')
    return result


def check_role(dataset, role, catalog):
    require(role in ('agent_evidence', 'reference'), 'EP-DAG-01', 'Evaluator/unsupported source role')
    if catalog is not None:
        require(dataset in catalog, 'EP-DAG-01', 'Unregistered product')
        roles = catalog[dataset].get('roles', [])
        require('evaluation_only' not in roles and role in roles, 'EP-DAG-01', 'Catalog access denied')


class InputGraph:
    """Independent DAG traversal and exact byte/receipt verification."""
    def __init__(self, snapshot, root, catalog):
        self.snapshot = snapshot
        self.root = Path(root).resolve()
        self.raw_root = Path(snapshot['raw_root'] or self.root)
        self.catalog = catalog
        self.nodes = {node['source_id']: node for node in snapshot['sources']}
        require(self.nodes and len(self.nodes) == len(snapshot['sources']), 'EP-DAG-01', 'Unique source nodes required')
        self._closures = {}
        colors = {}

        def visit(key):
            require(key in self.nodes, 'EP-DAG-01', 'Missing source parent')
            require(colors.get(key) != 'active', 'EP-DAG-01', 'Source graph cycle')
            if colors.get(key) == 'done':
                return
            colors[key] = 'active'
            node = self.nodes[key]
            check_role(node['dataset_id'], node['role'], catalog)
            require(node['source_id'].strip() and node['release_id'] and SHA.fullmatch(node['sha256']),
                    'EP-DAG-01', 'Source identity/release/hash invalid')
            if node['computed_at'] is not None:
                require(node['parents'] and node['method_id'] and node['method_version'],
                        'EP-DAG-01', 'Computed parent/method missing')
            else:
                require(not node['parents'], 'EP-DAG-01', 'Derived node computation time missing')
            self.path(node)
            for parent in node['parents']:
                visit(parent)
            colors[key] = 'done'
        for key in self.nodes:
            visit(key)

    def path(self, node):
        return child(self.root if node['computed_at'] is not None else self.raw_root, node['path'])

    def closure(self, references):
        require(bool(references), 'EP-DAG-01', 'Input lineage missing')
        key = tuple(references)
        if key not in self._closures:
            pending, seen = list(references), set()
            while pending:
                source = pending.pop()
                require(source in self.nodes, 'EP-DAG-01', 'Unknown input reference')
                if source not in seen:
                    seen.add(source)
                    pending.extend(self.nodes[source]['parents'])
            self._closures[key] = tuple(sorted(seen))
        return self._closures[key]

    def exclusion(self, references, case):
        for key in self.closure(references):
            node = self.nodes[key]
            if node['computed_at'] is not None:
                continue
            reason = availability_reason(node['availability'], case['origin_at'])
            if reason:
                return reason
            temporal = node['temporal_classification']
            if self.snapshot['profile'] == 'historical_benchmark':
                if temporal == 'reconstructed':
                    if not self.snapshot['allow_reconstructed']:
                        return 'reconstructed_history_not_approved'
                elif temporal != 'verified_historical':
                    return 'not_verified_historical'
            elif temporal == 'unverified':
                return 'temporal_classification_unverified'
        return None

    def proof(self, key, verify=True):
        node = self.nodes[key]
        path = self.path(node)
        if verify:
            require(path.is_file() and file_digest(path) == node['sha256'], 'EP-SOURCE-01', 'Source byte mismatch')
        proof = dict(artifact_id=key, dataset_id=node['dataset_id'], release_id=node['release_id'],
            path=str(path), sha256=node['sha256'], role=node['role'], parents=node['parents'])
        if node['receipt_path']:
            require(bool(node['receipt_sha256']), 'EP-SOURCE-01', 'Receipt hash missing')
            receipt_path = child(self.raw_root, node['receipt_path'])
            proof.update(receipt_path=str(receipt_path), receipt_sha256=node['receipt_sha256'])
            if verify:
                require(file_digest(receipt_path) == node['receipt_sha256'], 'EP-SOURCE-01', 'Receipt checksum mismatch')
                receipt = read_json(receipt_path)
                require(receipt.get('status') == 'completed' and receipt.get('sha256') == node['sha256']
                    and receipt.get('dataset_id') == node['dataset_id'] and receipt.get('release_id') == node['release_id']
                    and child(self.raw_root, receipt.get('relative_path', '')) == path
                    and receipt.get('bytes') == path.stat().st_size, 'EP-SOURCE-01', 'Receipt identity mismatch')
                self.receipt_availability(node, receipt)
        elif self.snapshot['profile'] != 'synthetic_demo' and node['computed_at'] is None:
            raise PolicyError('EP-SOURCE-01', 'Real raw source lacks archived receipt')
        return proof

    @staticmethod
    def receipt_availability(node, receipt):
        availability = node['availability']
        if availability['basis'] == 'public_download_receipt':
            completed = timestamp(receipt.get('completed_at_utc'))
            require(availability['known_public_by'] is not None
                and timestamp(availability['known_public_by']) >= completed
                and availability['evidence_ref'] == node['receipt_sha256']
                and node['source_url'] == receipt.get('url'), 'EP-SOURCE-01', 'Receipt availability contradiction')


def observation_validity(observation):
    o = observation
    require(all(o[key].strip() for key in ('observation_id', 'target_id', 'indication_id', 'statement')),
            'EP-OBS-01', 'Observation identity/statement missing')
    require(bool(o['input_refs']), 'EP-OBS-01', 'Observation lineage missing')
    require(o['source_kind'] in ('primary', 'integrated', 'computed', 'clinical'), 'EP-OBS-01', 'Unsupported source kind')
    if o['source_kind'] == 'computed':
        require(o['computed_at'] is not None and o['method']['code_id'] and o['method']['version'],
                'EP-OBS-01', 'Computed observation method/time missing')
    require(o['mechanism_direction'] in ('inhibit', 'activate', 'degrade', 'uncertain', 'not_applicable')
            and o['method']['qc_status'] in ('passed', 'failed', 'not_run'), 'EP-OBS-01', 'Invalid method/direction')
    q = o['quantitative']
    require(q['standard_error'] is None or q['standard_error'] > 0, 'EP-OBS-01', 'Nonpositive uncertainty')
    require(q['sample_size'] is None or q['sample_size'] > 0, 'EP-OBS-01', 'Nonpositive sample size')
    require(q['adjusted_p_value'] is None or 0 <= q['adjusted_p_value'] <= 1, 'EP-OBS-01', 'Invalid p value')
    require((q['ci_lower'] is None) == (q['ci_upper'] is None)
            and (q['ci_lower'] is None or q['ci_lower'] <= q['ci_upper']), 'EP-OBS-01', 'Invalid confidence interval')
    if o['features']:
        require(o['status'] == 'observed' and o['method']['qc_status'] == 'passed'
            and o['source_kind'] != 'clinical' and o['category'] != 'clinical' and o['feature_scope']
            and o['method']['code_id'].strip() and o['method']['version'].strip(),
            'EP-OBS-01', 'Unqualified numerical features')
        for name, value in o['features'].items():
            require(name in FEATURES and FEATURES[name] == o['category']
                and (-1 if name in SIGNED_FEATURES else 0) <= value <= 1,
                'EP-OBS-01', 'Invalid numerical feature/category/range')


def observation_reason(o, artifact, graph, case):
    observation_validity(o)
    if o['program_id'] is not None and case['program'] is not None and case['program']['mapping_confidence'] == 0:
        return 'unresolved_program_mapping'
    require(set(graph.closure(o['input_refs'])) <= set(graph.closure(artifact['input_refs'])),
            'EP-OBS-01', 'Observation lineage escapes packet')
    reason = graph.exclusion(o['input_refs'], case)
    if reason is None and o['source_kind'] != 'computed':
        reason = availability_reason(o['availability'], case['origin_at'])
    if reason is not None:
        return reason
    published, year = o['publication_date'], o['publication_year']
    require(year is None or 1 <= year <= 9999, 'EP-OBS-01', 'Invalid publication year')
    if published is not None and year is not None and int(published[:4]) != year:
        return 'publication_metadata_inconsistent'
    if (published is not None and published > case['origin']) or (year is not None and year > int(case['origin'][:4])):
        return 'publication_after_origin'
    return None


def permitted(case, record, category=None):
    o = record['observation']
    program = case['program']
    return (o['target_id'] == case['hypothesis']['target_id'] and o['indication_id'] == case['hypothesis']['indication_id']
        and (category is None or o['category'] == category) and (o['program_id'] is None
        or (program is not None and program['mapping_confidence'] > 0 and program['program_id'] == o['program_id'])))


def admit(case, snapshot, root, catalog=None):
    validate_case(case)
    require(snapshot['schema_version'] == 2 and snapshot['snapshot_id'].strip(), 'EP-PACKET-01', 'Invalid snapshot identity')
    require(snapshot['origin'] == case['origin'] and snapshot['origin_at'] == case['origin_at'],
            'EP-CASE-01', 'Snapshot/case origin mismatch')
    if snapshot['profile'] != 'synthetic_demo':
        require(catalog is not None, 'EP-DAG-01', 'Real-data catalog missing')
    graph = InputGraph(snapshot, root, catalog_index(catalog) if snapshot['profile'] != 'synthetic_demo' else None)
    records, exclusions, proofs = {}, [], []
    artifact_ids, paths, observation_ids, parents = set(), set(), set(), set()
    eligible = {}
    for artifact in snapshot['artifacts']:
        key = artifact['artifact_id']
        require(key.strip() and artifact['release_id'].strip() and key not in artifact_ids
            and artifact['path'] not in paths and key not in graph.nodes and SHA.fullmatch(artifact['sha256']),
            'EP-PACKET-01', 'Invalid/duplicate artifact identity/path')
        artifact_ids.add(key)
        paths.add(artifact['path'])
        require(artifact['role'] == 'agent_evidence', 'EP-PACKET-01', 'Non-evidence artifact')
        path = child(root, artifact['path'])
        if not artifact['access_approved']:
            reason = 'access_denied'
        else:
            check_role(artifact['dataset_id'], artifact['role'], graph.catalog)
            reason = graph.exclusion(artifact['input_refs'], case)
        if reason:
            exclusions.append(dict(item_id=key, level='artifact', reason=reason))
            continue
        eligible[key] = artifact
        require(path.is_file() and path.stat().st_size <= NORMAL_LIMIT, 'EP-PACKET-01', 'Missing/oversize packet')
        payload = path.read_bytes()
        require(bytes_digest(payload) == artifact['sha256'], 'EP-PACKET-01', 'Packet checksum mismatch')
        packet = decode('Packet', parse(payload))
        require(packet['schema_version'] == 2, 'EP-PACKET-01', 'Unsupported packet version')
        proofs.append(dict(artifact_id=key, dataset_id=artifact['dataset_id'], release_id=artifact['release_id'],
                           path=str(path), sha256=artifact['sha256']))
        citation = dict(artifact_id=key, dataset_id=artifact['dataset_id'], release_id=artifact['release_id'],
                        artifact_sha256=artifact['sha256'], source_url=artifact['source_url'])
        parents.update(graph.closure(artifact['input_refs']))
        for o in packet['observations']:
            require(o['observation_id'] not in observation_ids, 'EP-PACKET-01', 'Duplicate observation ID')
            observation_ids.add(o['observation_id'])
            reason = observation_reason(o, artifact, graph, case)
            if reason:
                exclusions.append(dict(item_id=o['observation_id'], level='observation', reason=reason))
            else:
                records[o['observation_id']] = dict(observation=o, citation=citation)
    proofs.extend(graph.proof(key) for key in sorted(parents))
    return dict(records=records, exclusions=exclusions, proofs=proofs, graph=graph, eligible=eligible,
                admitted_fingerprints={key: digest(value) for key, value in records.items()})


def validate_usage(value):
    result = decode('Usage', value)
    require(all(result[key] >= 0 for key in result), 'EP-EXEC-04', 'Negative usage')
    return result


def validate_budget(value):
    result = decode('Budget', value)
    require(all(result[key] >= 0 for key in ('max_calls', 'max_input_tokens', 'max_output_tokens', 'max_retries', 'max_cost_usd'))
        and result['max_seconds'] > 0, 'EP-EXEC-01', 'Invalid resource budget')
    return result


def validate_process_limits(value):
    value = {} if value is None else value
    require(type(value) is dict and not set(value) - {'timeout_seconds', 'max_output_bytes'},
            'EP-EXEC-01', 'Invalid process limit fields')
    timeout, maximum = value.get('timeout_seconds', 3600.0), value.get('max_output_bytes', 16 * 1024 * 1024)
    require(type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0
        and type(maximum) is int and 1 <= maximum <= 64 * 1024 * 1024,
        'EP-EXEC-01', 'Invalid process resource bounds')


def scorer_preflight(case, profile, scorer):
    if scorer is None:
        return 'dossier_audit_has_no_clinical_probability' if case['task'] == 'T6' else 'no_frozen_scorer_configured'
    m = scorer
    require(m['schema_version'] == 2 and m['kind'] in ('synthetic_demo', 'frozen_model')
        and m['feature_schema'] == FEATURE_SCHEMA and m['aggregation'] == AGGREGATION,
        'EP-SCORER-01', 'Unsupported scorer schema')
    require(m['model_id'].strip() and m['coefficients'], 'EP-SCORER-01', 'Empty scorer identity/coefficients')
    names = set(m['coefficients'])
    require(names <= FEATURES.keys() and set(m['required_features']) <= names and set(m['missing_values']) <= names,
            'EP-SCORER-01', 'Scorer feature schema mismatch')
    require(SHA.fullmatch(m['training_manifest_sha256']) and 0 <= m['minimum_coverage'] <= 1,
            'EP-SCORER-01', 'Scorer training identity/coverage invalid')
    require(all((-1 if name in SIGNED_FEATURES else 0) <= value <= 1 for name, value in m['missing_values'].items()),
            'EP-SCORER-01', 'Invalid frozen imputation')
    require(m['calibration'] in ('none', 'held_out_logistic') and
        (m['calibration'] == 'none' or m['calibration_label_available_max'] is not None),
        'EP-SCORER-01', 'Calibration identity/cutoff missing')
    require((m['kind'] == 'synthetic_demo') == (profile == 'synthetic_demo'),
            'EP-SCORER-01', 'Scorer/profile mismatch')
    require(all(value is None or value < case['origin'] for value in (m['training_origin_max'],
        m['training_label_available_max'], m['calibration_label_available_max'])),
        'EP-SCORER-01', 'Training/calibration reaches origin')
    if case['task'] == 'T6':
        return 'dossier_audit_has_no_clinical_probability'
    h, endpoint, program = case['hypothesis'], case['endpoint'], case['program']
    if (endpoint['name'] != m['endpoint'] or endpoint['horizon_months'] != m['horizon_months']
        or program['phase_at_origin'] not in m['phases'] or h['modality'] not in m['modalities']
        or h['intended_action'] not in m['intended_actions'] or h['target_namespace_version'] not in m['target_namespace_versions']
        or h['indication_namespace_version'] not in m['indication_namespace_versions']):
        return 'outside_scorer_applicability'
    return None


def build_features(case, claims, missingness=None):
    observations = [claim['evidence']['observation'] for claim in claims]
    # Build undirected components independently instead of sharing runtime union-find.
    adjacency = {o['observation_id']: set() for o in observations}
    groups = defaultdict(list)
    for o in observations:
        keys = ([('group', o['dependency_group'])] if o['dependency_group'] else [])
        keys += [('study', o['study_id'])] if o['study_id'] else []
        keys += [('cohort', value) for value in o['context']['cohort_ids']]
        for key in keys:
            groups[key].append(o['observation_id'])
    for members in groups.values():
        for member in members:
            adjacency[member].add(members[0])
            adjacency[members[0]].add(member)
    by_id = {o['observation_id']: o for o in observations}
    labels = {}
    for key in adjacency:
        if key in labels:
            continue
        connected, pending = set(), [key]
        while pending:
            current = pending.pop()
            if current not in connected:
                connected.add(current)
                pending.extend(adjacency[current])
        label = min(by_id[item]['dependency_group'] or 'unknown-dependence:' + item for item in connected)
        labels.update({item: label for item in connected})
    hypothesis = hypothesis_key(case)
    output = {}
    for name, category in FEATURES.items():
        collected = defaultdict(list)
        for o in observations:
            if o['feature_scope'] == hypothesis and name in o['features']:
                collected[labels[o['observation_id']]].append((o['observation_id'], o['features'][name]))
        values, ids, excluded = [], [], []
        for label, entries in sorted(collected.items()):
            unique = {item[1] for item in entries}
            if len(unique) > 1:
                excluded.append(label)
            else:
                values.append(next(iter(unique)))
                ids.extend(item[0] for item in entries)
        reasons = set((missingness or {}).get(category, [])) if not values else set()
        if any(name in o['features'] and o['feature_scope'] != hypothesis for o in observations):
            reasons.add('outside_applicability')
        # statistics.mean uses exact rational accumulation of represented floats.
        value = float(sum((Fraction(item) for item in values), Fraction()) / len(values)) if values else None
        output[name] = dict(value=value, status='observed' if values else 'conflicting' if excluded else 'not_measured',
            dependency_groups=len(values), observation_ids=sorted(ids), excluded_groups=excluded, missing_reasons=sorted(reasons))
    return dict(schema_version=FEATURE_SCHEMA, aggregation=AGGREGATION, values=output)


def prediction(case, profile, features, scorer, run_status='completed'):
    reason = scorer_preflight(case, profile, scorer) if run_status == 'completed' else 'run_incomplete'
    coverage = None
    contributions, intercept, probability = {}, None, None
    if run_status != 'completed':
        reason = 'run_incomplete'
    elif reason is None:
        require(features['schema_version'] == scorer['feature_schema'] and features['aggregation'] == scorer['aggregation'],
                'EP-SCORER-02', 'Feature/scorer contract differs')
        values = features['values']
        coverage = sum(values[name]['value'] is not None for name in scorer['coefficients']) / len(scorer['coefficients'])
        if any(values[name]['value'] is None for name in scorer['required_features']):
            reason = 'required_features_missing'
        elif coverage < scorer['minimum_coverage']:
            reason = 'insufficient_feature_coverage'
        else:
            for name, coefficient in sorted(scorer['coefficients'].items()):
                imputed = values[name]['value'] is None
                if imputed and name not in scorer['missing_values']:
                    reason = 'missing_feature_without_frozen_imputation'
                    contributions = {}
                    break
                value = scorer['missing_values'][name] if imputed else values[name]['value']
                contributions[name] = dict(value=value, coefficient=coefficient, log_odds=value * coefficient,
                    imputed=imputed, observation_ids=values[name]['observation_ids'])
            if reason is None:
                intercept = scorer['intercept']
                logit = intercept + sum(item['log_odds'] for item in contributions.values())
                require(math.isfinite(logit), 'EP-SCORER-02', 'Scorer arithmetic overflow')
                probability = 1 / (1 + math.exp(-logit)) if logit >= 0 else math.exp(logit) / (1 + math.exp(logit))
    endpoint = case['endpoint']
    return dict(case_id=case['case_id'], origin=case['origin'], endpoint=endpoint['name'] if endpoint else None,
        horizon_months=endpoint['horizon_months'] if endpoint else None,
        status='scored' if reason is None else 'audit_only' if case['task'] == 'T6' else 'abstained',
        probability=probability, reason=reason, scorer_id=scorer['model_id'] if scorer else None,
        synthetic=profile == 'synthetic_demo' or (scorer is not None and scorer['kind'] == 'synthetic_demo'),
        calibration=scorer['calibration'] if scorer else None, feature_coverage=coverage,
        intercept=intercept, contributions=contributions)


def read_chain(path, partial=False):
    return parse_chain(Path(path).read_bytes(), partial=partial)


def parse_chain(payload, partial=False):
    lines = payload.splitlines()
    events = []
    previous = None
    for index, line in enumerate(lines):
        if partial and index == len(lines) - 1 and not payload.endswith(b'\n'):
            break
        event = parse(line)
        object_fields(event, ('sha256', 'sequence', 'event', 'details', 'previous_sha256'), 'EP-EXEC-04', 'Journal event')
        require(type(event['details']) is dict and type(event['event']) is str, 'EP-EXEC-04', 'Malformed journal payload')
        body = {key: value for key, value in event.items() if key != 'sha256'}
        require(event.get('sequence') == len(events) and event.get('previous_sha256') == previous
            and digest(body) == event['sha256'], 'EP-EXEC-04', 'Journal chain mismatch')
        previous = event['sha256']
        events.append(event)
    require(bool(events), 'EP-EXEC-04', 'Empty journal')
    return events


def _sum_usage(left, right):
    return {key: left[key] + right[key] for key in ('input_tokens', 'output_tokens', 'cost_usd')}


def _zero_usage():
    return dict(input_tokens=0, output_tokens=0, cost_usd=0.0)


def execution_accounting(run, case, snapshot, configuration, claims, trace):
    require(run.get('schema_version') == 2 and run.get('case_id') == case['case_id']
        and run.get('snapshot_id') == snapshot['snapshot_id'] and run.get('profile') == snapshot['profile']
        and run.get('backend_id') == configuration.get('backend_id'), 'EP-EXEC-01', 'Run identity mismatch')
    budget = validate_budget(run['budget'])
    require(budget == validate_budget(configuration.get('budget')), 'EP-EXEC-01', 'Budget/configuration mismatch')
    plans = [event['details'] for event in trace if event['event'] == 'plan']
    require(len(plans) == 1 and plans[0].get('snapshot_id') == snapshot['snapshot_id']
        and digest(plans[0].get('configuration')) == digest(configuration)
        and digest(plans[0].get('steps')) == digest(run.get('plan')), 'EP-EXEC-01', 'Plan/configuration mismatch')
    require([step['category'] for step in run['plan']] == list(CATEGORIES)
        and set(run['coverage']) == set(CATEGORIES), 'EP-EXEC-01', 'Specialist inventory mismatch')
    for step in run['plan']:
        available = run['coverage'][step['category']]['available_observations']
        initial = 'disabled' if step['category'] in configuration['disabled'] else 'ready' if available else 'no_observed_evidence'
        require(step['observed_records'] == available and step['initial_status'] == initial,
                'EP-EXEC-01', 'Plan/coverage status mismatch')
    attempts, accounted, committed = {}, set(), []
    total, measured, estimated = _zero_usage(), _zero_usage(), _zero_usage()
    for event in trace:
        detail = event['details']
        if event['event'] == 'dispatch':
            key = detail['attempt_id']
            require(key not in attempts and set(attempts) == accounted, 'EP-EXEC-04', 'Overlapping/duplicate dispatch')
            reserved = validate_usage(detail['reserved'])
            require(detail['category'] in run['coverage'] and detail['category'] not in configuration['disabled']
                and 1 <= detail['attempt'] <= budget['max_retries'] + 1
                and key == f"{detail['category']}:{detail['attempt']}", 'EP-EXEC-04', 'Invalid specialist attempt')
            require(len(attempts) < budget['max_calls'] and total['input_tokens'] + reserved['input_tokens'] <= budget['max_input_tokens']
                and total['output_tokens'] + reserved['output_tokens'] <= budget['max_output_tokens']
                and total['cost_usd'] + reserved['cost_usd'] <= budget['max_cost_usd'], 'EP-EXEC-04', 'Unreservable dispatch')
            attempts[key] = reserved
        elif event['event'] == 'attempt_accounted':
            key = detail['attempt_id']
            require(key in attempts and key not in accounted, 'EP-EXEC-04', 'Unmatched/duplicate account')
            used = validate_usage(detail['usage'])
            if detail['basis'] == 'adapter_reported':
                measured = _sum_usage(measured, used)
            else:
                require(detail['basis'] == 'quoted_upper_bound_not_measured' and used == attempts[key],
                        'EP-EXEC-04', 'Unknown account basis/reservation')
                estimated = _sum_usage(estimated, used)
            total = _sum_usage(total, used)
            accounted.add(key)
        elif event['event'] == 'claim_committed':
            committed.append(detail['claim'])
    require(set(attempts) == accounted, 'EP-EXEC-04', 'Finalized run contains unresolved dispatch')
    require(type(run['calls']) is int and run['calls'] == len(attempts)
        and total == decode('Usage', run['usage']) and measured == decode('Usage', run['measured_usage'])
        and estimated == decode('Usage', run['estimated_usage']), 'EP-EXEC-04', 'Run/journal accounting mismatch')
    require(digest(committed) == digest(claims), 'EP-EXEC-03', 'Journal claims differ from ledger')
    return dict(calls=len(attempts), usage=total, measured_usage=measured, estimated_usage=estimated)


def execution_states(run, trace, configuration):
    """Reconstruct category lifecycle using independent event transactions."""
    obligation = 'EP-EXEC-04'
    initial = {row['category']: row['initial_status'] for row in run['plan']}
    state = {key: 'not_run' if value == 'ready' else value for key, value in initial.items()}
    require(type(configuration['review_enabled']) is bool, 'EP-EXEC-01', 'Review flag must be boolean')
    history, retrievals, failures, closed = [], {}, [], set()
    attempts = Counter()
    terminal = exhausted = plan = finalized = False
    preambles, current = set(), None

    def finish(next_category=None):
        if current is None:
            return
        require(current['usage'] is not None and (current['review'] or current['terminal']),
                obligation, 'Attempt lacks accounted terminal/review')
        if current['review'] and current['selected'] is None and configuration['review_enabled']:
            require(next_category == current['category'] or attempts[current['category']] == run['budget']['max_retries'] + 1,
                    obligation, 'Required retry abandoned')
        if current['selected'] is not None:
            require(current['committed'] == current['selected'][:len(current['committed'])]
                and (current['partial'] or current['committed'] == current['selected']),
                'EP-EXEC-03', 'Claim sequence incomplete or differs from review')

    def check_category(details):
        name = details['category']
        require(name in state and initial[name] == 'ready' and name not in closed,
                obligation, 'Event for inactive/failed category')
        return name

    fatal_names = {'OSError', 'PermissionError', 'FileNotFoundError', 'KeyError', 'TypeError',
                   'AttributeError', 'AssertionError', 'MemoryError', 'Exception'}
    handled_names = {'BackendFailure', 'ContractError', 'TimeoutError', 'ConnectionError',
                     'ValueError', 'RuntimeError', 'RecursionError'}
    for event in trace:
        kind, detail = event['event'], event['details']
        require(not finalized and (not terminal or kind == 'finalize'), obligation, 'Event after terminal state')
        if kind in ('run_reserved', 'inputs_archived'):
            require(not plan and kind not in preambles, obligation, 'Invalid preamble')
            preambles.add(kind)
            continue
        if kind == 'plan':
            require(not plan, obligation, 'Duplicate plan')
            plan = True
            continue
        require(plan, obligation, 'Event before plan')
        if kind in ('bounded_retrieval', 'backend_quote_failed', 'budget_denied', 'dispatch'):
            name = check_category(detail)
            require(not exhausted and state[name] not in ('completed', 'no_records_within_retrieval_budget'),
                    obligation, 'Preparation after terminal category')
            finish(name)
            current = None
            if kind in ('bounded_retrieval', 'dispatch'):
                require(type(detail['attempt']) is int and detail['attempt'] == attempts[name] + 1,
                        obligation, 'Attempt sequence mismatch')
            if kind == 'bounded_retrieval':
                ids = detail['selected_ids']
                require(type(ids) is list and all(type(x) is str for x in ids) and len(ids) == len(set(ids)),
                        'EP-EXEC-02', 'Invalid retrieval selections')
                retrievals[name] = {k: v for k, v in detail.items() if k not in ('category', 'attempt')}
                if not ids:
                    state[name] = 'no_records_within_retrieval_budget'
            elif kind == 'backend_quote_failed':
                state[name] = 'failed'
                closed.add(name)
            elif kind == 'budget_denied':
                state[name], exhausted = 'budget_exhausted', True
            else:
                attempts[name] += 1
                if name not in history:
                    history.append(name)
                require(history[-1] == name, obligation, 'Returned to previous category')
                state[name] = 'failed'
                current = dict(category=name, attempt_id=detail['attempt_id'], usage=None, selected=None,
                    review=False, committed=[], partial=False, terminal=False)
        elif kind == 'attempt_accounted':
            require(current is not None and current['attempt_id'] == detail['attempt_id'] and current['usage'] is None,
                    obligation, 'Account outside active attempt')
            current['usage'] = detail['usage']
        elif kind in ('backend_failed', 'backend_usage_contract_violated', 'wall_time_budget_exceeded'):
            name = check_category(detail)
            require(current is not None and current['category'] == name and current['usage'] is not None,
                    obligation, 'Failure outside accounted attempt')
            current['terminal'] = True
            if kind == 'wall_time_budget_exceeded':
                exhausted = True
                if detail.get('stage') == 'claim_commit':
                    require(current['selected'] is not None, obligation, 'Commit timeout before selection')
                    current['partial'] = True
                    state[name] = 'budget_exhausted'
                else:
                    require(not current['review'], obligation, 'Pre-review timeout after review')
                    state[name] = 'failed'
            else:
                require(not current['review'], obligation, 'Failure after review')
                state[name] = 'failed'
                if kind == 'backend_failed':
                    failures.append(detail['error_class'])
                    closed.add(name)
                    terminal = detail['error_class'] in fatal_names | {'KeyboardInterrupt'}
                else:
                    exhausted = True
        elif kind == 'review':
            name = check_category(detail)
            require(current is not None and current['category'] == name and current['usage'] is not None
                and not current['review'] and not exhausted, 'EP-EXEC-03', 'Review outside accounted attempt')
            require(canonical(current['usage']) == canonical(detail['usage']), 'EP-EXEC-03', 'Review usage differs')
            ids, problems = detail['selected'], detail['problems']
            require(type(ids) is list and all(type(x) is str for x in ids)
                and type(problems) is list and all(type(x) is str for x in problems), 'EP-EXEC-03', 'Malformed review')
            current['review'] = True
            if problems:
                if not configuration['review_enabled']:
                    closed.add(name)
            else:
                require(len(ids) == len(set(ids)) and (name not in retrievals or set(ids) <= set(retrievals[name]['selected_ids'])),
                        'EP-EXEC-03', 'Review selection duplicate/outside retrieval')
                current['selected'] = ids
                state[name] = 'completed'
        elif kind == 'claim_committed':
            require(current is not None and current['selected'] is not None and not current['partial']
                and not exhausted and current['category'] not in closed, 'EP-EXEC-03', 'Claim outside accepted review')
            claim = detail['claim']
            require(claim['specialist'] == current['category'], 'EP-EXEC-03', 'Cross-category claim')
            current['committed'].append(claim['evidence']['observation']['observation_id'])
            require(current['committed'] == current['selected'][:len(current['committed'])], 'EP-EXEC-03', 'Unselected claim')
        elif kind == 'finalize':
            finish()
            finalized = True
        else:
            raise PolicyError(obligation, 'Unsupported workflow event: ' + kind)
    require(history == [row['category'] for row in run['plan'] if row['category'] in history],
            obligation, 'Category order mismatch')
    for name in state:
        if exhausted and state[name] == 'not_run':
            state[name] = 'not_run_budget_exhausted'
        require(run['coverage'][name]['status'] == state[name], obligation, 'Coverage state mismatch')
        require(('retrieval' in run['coverage'][name]) == (name in retrievals), 'EP-EXEC-02', 'Retrieval coverage inventory mismatch')
        if name in retrievals:
            require(canonical(run['coverage'][name]['retrieval']) == canonical(retrievals[name]),
                    'EP-EXEC-02', 'Retrieval coverage differs')
    status = run['status']
    require(status in ('completed', 'partial', 'budget_exhausted', 'failed', 'interrupted'), obligation, 'Unknown run status')
    if 'KeyboardInterrupt' in failures:
        require(status == 'interrupted', obligation, 'Interrupt/status mismatch')
    elif any(name in fatal_names for name in failures):
        require(status == 'failed', obligation, 'Fatal/status mismatch')
    if status == 'interrupted':
        require(any(name not in handled_names | fatal_names for name in failures), obligation, 'Unjustified interrupt')
    if status == 'failed':
        require(any(name not in handled_names | {'KeyboardInterrupt'} for name in failures), obligation, 'Unjustified fatal')
    require((status == 'budget_exhausted') == exhausted, obligation, 'Budget/status mismatch')
    if status == 'completed':
        require(all(value in ('completed', 'disabled', 'no_observed_evidence', 'no_records_within_retrieval_budget')
                    for value in state.values()), obligation, 'Completed run has incomplete categories')
    elif status == 'partial':
        require('failed' in state.values() and 'not_run' not in state.values(), obligation, 'Unjustified partial')
    elif status in ('failed', 'interrupted'):
        require(failures and 'failed' in state.values(), obligation, 'Missing failed attempt')
    return state


def verify_core(run_dir, receipt_sha256=None, *, canonical_facade=True, trusted_runtime=None):
    root = Path(run_dir).resolve()
    receipt_path = root / 'receipt.json'
    if canonical_facade:
        for name in ('journal.jsonl', 'trace.jsonl'):
            if (root / name).exists():
                bounded_stable_bytes(root / name)
    if receipt_sha256 is not None:
        require(file_digest(receipt_path) == receipt_sha256, 'EP-VERIFY-01', 'External receipt anchor mismatch')
    receipt = read_json(receipt_path)
    object_fields(receipt, ('schema_version', 'outputs', 'sources', 'input_fingerprint'), 'EP-VERIFY-01', 'Receipt')
    legacy = receipt.get('schema_version') == 1
    if legacy and canonical_facade:
        raise UnsupportedPolicy('Legacy v1 has receipt-only verification through a separate interface; current-v2 semantic parity unavailable')
    required = RUN_FILES[:-1] if legacy else RUN_FILES
    require(receipt.get('schema_version') in (1, 2) and set(receipt.get('outputs', {})) == set(required),
            'EP-VERIFY-01', 'Receipt version/output inventory invalid')
    for name, expected in receipt['outputs'].items():
        path = child(root, name)
        require(path.is_file() and file_digest(path) == expected, 'EP-VERIFY-01', 'Output checksum mismatch: ' + name)
    auxiliary = receipt.get('auxiliary_outputs', {})
    require(type(auxiliary) is dict and not set(auxiliary) - {'request.json', 'backend-execution.json'},
            'EP-VERIFY-01', 'Invalid auxiliary inventory')
    for name, expected in auxiliary.items():
        require(file_digest(child(root, name)) == expected, 'EP-VERIFY-01', 'Auxiliary checksum mismatch')
    inputs = read_json(root / 'inputs.json')
    object_fields(inputs, ('case', 'snapshot', 'scorer', 'catalog_policy', 'configuration', 'snapshot_base'),
                  'EP-VERIFY-02', 'Archived inputs')
    require(digest(inputs) == receipt['input_fingerprint'], 'EP-VERIFY-01', 'Input fingerprint mismatch')
    trace = read_chain(root / 'trace.jsonl')
    if legacy:
        for proof in receipt['sources']:
            path = Path(proof['path'])
            if not path.is_absolute():
                path = child(root, proof['path'])
            require(file_digest(path) == proof['sha256'], 'EP-SOURCE-01', 'Legacy source mismatch')
            if proof.get('receipt_path'):
                require(file_digest(Path(proof['receipt_path'])) == proof['receipt_sha256'],
                        'EP-SOURCE-01', 'Legacy receipt mismatch')
        return dict(semantic_consistency='unavailable_legacy_v1', trace_events=len(trace),
                    receipt_sha256=file_digest(receipt_path))
    require((root / 'journal.jsonl').read_bytes() == (root / 'trace.jsonl').read_bytes(),
            'EP-VERIFY-02', 'Durable journal differs from final trace')
    case = decode('Case', inputs['case'])
    snapshot = decode('Snapshot', inputs['snapshot'])
    scorer = decode('Scorer', inputs['scorer']) if inputs['scorer'] else None
    source = admit(case, snapshot, Path(inputs['snapshot_base']), inputs['catalog_policy'])
    ledger = read_json(root / 'ledger.json', LEDGER_LIMIT)
    require(ledger.get('schema_version') == 2, 'EP-VERIFY-02', 'Ledger schema mismatch')
    claims = decode('[Claim]', ledger['claims'])
    run = read_json(root / 'run.json')
    object_fields(run, ('schema_version', 'case_id', 'snapshot_id', 'profile', 'backend_id', 'input_fingerprint',
        'budget', 'calls', 'status', 'usage', 'measured_usage', 'estimated_usage', 'plan', 'coverage', 'exclusions'),
        'EP-VERIFY-02', 'Run')
    configuration = inputs['configuration']
    object_fields(configuration, ('budget', 'disabled', 'review_enabled', 'backend_id', 'backend_provenance', 'hypothesis_key'),
                  'EP-EXEC-01', 'Configuration')
    require(run['input_fingerprint'] == receipt['input_fingerprint'], 'EP-VERIFY-02', 'Run input fingerprint differs')
    actual_proofs = {proof['artifact_id']: proof for proof in receipt['sources']}
    expected_proofs = {proof['artifact_id']: proof for proof in source['proofs']}
    require(len(actual_proofs) == len(receipt['sources']) and digest(actual_proofs) == digest(expected_proofs),
            'EP-SOURCE-01', 'Source proof closure differs')
    require(digest(source['admitted_fingerprints']) == digest(receipt['admitted_fingerprints']),
            'EP-VERIFY-02', 'Admitted source fingerprints differ')
    require(digest(source['exclusions']) == digest(run['exclusions']), 'EP-VERIFY-02', 'Source exclusions differ')
    seen = set()
    for claim in claims:
        grounded = claim['evidence']
        o, citation = grounded['observation'], grounded['citation']
        key = o['observation_id']
        require(key not in seen and digest(grounded) == claim['admitted_fingerprint']
            and digest(grounded) == source['admitted_fingerprints'].get(key), 'EP-VERIFY-02', 'Claim/source binding mismatch')
        seen.add(key)
        require(permitted(case, grounded, claim['specialist']), 'EP-SCOPE-01', 'Claim outside case/category/program')
        artifact = source['eligible'].get(citation['artifact_id'])
        require(artifact is not None and citation['artifact_sha256'] == artifact['sha256']
            and all(citation[key] == artifact[key] for key in ('dataset_id', 'release_id', 'source_url')),
            'EP-VERIFY-02', 'Citation mismatch')
        require(observation_reason(o, artifact, source['graph'], case) is None and o['status'] == 'observed',
                'EP-OBS-01', 'Ineligible claim')
        require(claim['claim_id'] == 'claim-' + digest(dict(case=case['case_id'], evidence=grounded))[:20]
            and claim['extraction_mode'] == 'verbatim_source_selection', 'EP-EXEC-03', 'Invalid claim identity/extraction')
    counts = Counter(claim['specialist'] for claim in claims)
    missingness = {}
    for category, coverage in run['coverage'].items():
        require(category in CATEGORIES, 'EP-VERIFY-02', 'Unknown coverage category')
        records = [record for record in source['records'].values() if permitted(case, record, category)]
        observed = sum(record['observation']['status'] == 'observed' for record in records)
        other = [dict(observation_id=r['observation']['observation_id'], status=r['observation']['status'],
            reason=r['observation']['statement']) for r in records if r['observation']['status'] != 'observed']
        require(coverage['available_observations'] == observed and digest(coverage['nonobserved']) == digest(other)
            and digest(coverage['source_coverage']) == digest(snapshot['coverage'])
            and coverage['selected_observations'] == counts[category], 'EP-VERIFY-02', 'Source/ledger coverage mismatch')
        missingness[category] = [item['status'] for item in other]
        if snapshot['coverage'] and snapshot['coverage'].get('source_completeness') != 'complete':
            missingness[category].append('source_incomplete')
    features = decode('FeatureVector', read_json(root / 'features.json'))
    rebuilt = build_features(case, claims, missingness)
    require(digest(features) == digest(rebuilt), 'EP-FEATURE-01', 'Ledger/feature mismatch')
    predicted = decode('Prediction', read_json(root / 'prediction.json'))
    expected = prediction(case, snapshot['profile'], rebuilt, scorer, run['status'])
    require(digest(predicted) == digest(expected), 'EP-SCORER-02', 'Prediction/contributions differ')
    require(trace[-1]['event'] == 'finalize', 'EP-EXEC-04', 'Final event missing')
    final = trace[-1]['details']
    require(final['feature_sha256'] == digest(features) and final['prediction_sha256'] == digest(predicted)
        and final['status'] == run['status'], 'EP-VERIFY-02', 'Final trace/output mismatch')
    require(configuration.get('hypothesis_key') == hypothesis_key(case), 'EP-SCOPE-01', 'Configured hypothesis differs')
    accounting = execution_accounting(run, case, snapshot, configuration, claims, trace)
    if run['backend_id'] == 'local-structured-selection-v1':
        require('backend-execution.json' in auxiliary, 'EP-EXEC-02', 'Local execution archive unsealed')
        from .independent_local import verify_local
        verify_local(read_json(root / 'backend-execution.json'), trace, configuration, case, source)
    elif run['backend_id'] == 'recorded-selection-replay-v1':
        from .independent_local import verify_replay
        verify_replay(trace, configuration, case, source)
    if canonical_facade:
        for name in ('receipt.json', 'run.json', 'inputs.json', 'features.json', 'prediction.json', 'ledger.json', 'dossier.md'):
            bounded_stable_bytes(root / name, LEDGER_LIMIT if name in ('ledger.json', 'dossier.md') else NORMAL_LIMIT)
        decode('[PlanStep]', run['plan'])
        decode('[Exclusion]', run['exclusions'])
        execution_states(run, trace, configuration)
        from .independent_render import render_dossier
        expected_text = render_dossier(case, snapshot, run, claims, predicted)
        actual = (root / 'dossier.md').read_bytes()
        require(actual in (expected_text, expected_text.replace(b'\n', b'\r\n')),
                'EP-VERIFY-03', 'Dossier differs from deterministic rendering')
    if trusted_runtime is not None:
        from .independent_runtime import core_code
        current_code = core_code(trusted_runtime)
    return dict(semantic_consistency='verified', receipt_sha256=file_digest(receipt_path),
        code_matches_current=(receipt.get('code') == current_code) if trusted_runtime is not None else None,
        admitted_observation_ids=sorted(source['records']), selected_observation_ids=sorted(c['evidence']['observation']['observation_id'] for c in claims),
        exclusions=source['exclusions'], features=rebuilt, prediction=predicted, status=run['status'],
        accounting=[event['details'] for event in trace if event['event'] == 'attempt_accounted'],
        dispatches=[event['details'] for event in trace if event['event'] == 'dispatch'], **accounting)


def inspect_core(run_dir):
    root = Path(run_dir)
    trace = parse_chain(bounded_stable_bytes(root / 'journal.jsonl'), partial=True)
    if trace[0]['event'] == 'build_reserved':
        stage, progress, failure = None, {}, None
        for event in trace:
            if event['event'] == 'build_stage':
                stage = event['details']['stage']
            elif event['event'] == 'build_progress':
                progress = event['details']
            elif event['event'] in ('build_failed', 'build_interrupted'):
                failure = event['details']
        return dict(schema_version=2, kind='build', last_event=trace[-1]['event'], durable_events=len(trace),
            stage=stage, progress=progress, failure=failure, build_report_present=(root / 'build-report.json').is_file(),
            recovery_action='inspect only; start any replacement build in a new output directory')
    pending, measured, estimated = {}, _zero_usage(), _zero_usage()
    for event in trace:
        detail = event['details']
        if event['event'] == 'dispatch':
            pending[detail['attempt_id']] = detail
        elif event['event'] == 'attempt_accounted':
            pending.pop(detail['attempt_id'], None)
            if detail['basis'] == 'adapter_reported':
                measured = _sum_usage(measured, detail['usage'])
            else:
                estimated = _sum_usage(estimated, detail['usage'])
    for attempt in pending.values():
        estimated = _sum_usage(estimated, attempt['reserved'])
    return dict(schema_version=2, last_event=trace[-1]['event'], durable_events=len(trace),
        unresolved_attempts=list(pending), measured_usage=measured, estimated_upper_usage=estimated,
        receipt_present=(root / 'receipt.json').is_file(),
        recovery_action='inspect only; never automatically repeat unresolved calls')


def prepare_core(root, descriptor, *, catalog_override=None, snapshot_override=None):
    paths, options = descriptor['paths'], descriptor.get('options') or {}
    object_fields(paths, ('case', 'snapshot'), 'EP-WIRE-01', 'Preparation paths')
    case = decode('Case', read_json(child(root, paths['case'])))
    snapshot_path = child(root, paths['snapshot'])
    snapshot = snapshot_override or decode('Snapshot', read_json(snapshot_path))
    catalog = catalog_override
    if catalog is None and paths.get('catalog'):
        catalog = read_json(child(root, paths['catalog']))
    source = admit(case, snapshot, snapshot_path.parent, catalog)
    scorer = decode('Scorer', read_json(child(root, paths['scorer']))) if paths.get('scorer') else None
    preflight = scorer_preflight(case, snapshot['profile'], scorer)
    validate_budget(options.get('budget') or {})
    validate_process_limits(options.get('process_limits'))
    require(type(options.get('review_enabled', True)) is bool, 'EP-EXEC-01', 'Review flag must be boolean')
    disabled = options.get('disabled') or []
    require(type(disabled) is list and all(item in CATEGORIES for item in disabled), 'EP-EXEC-01', 'Invalid disabled specialist')
    require(not (paths.get('replay') and paths.get('local_model')), 'EP-EXEC-02', 'Competing backend configurations')
    if paths.get('replay'):
        replay = decode('ReplayDocument', read_json(child(root, paths['replay'])))
        require(replay['schema_version'] == 2, 'EP-EXEC-02', 'Replay version mismatch')
    if paths.get('local_model'):
        from .independent_local import validate_local_config
        validate_local_config(read_json(child(root, paths['local_model'])))
    return dict(admitted_observation_ids=sorted(source['records']),
        eligible_observation_ids=sorted(key for key, record in source['records'].items()
            if permitted(case, record) and record['observation']['status'] == 'observed'),
        exclusions=source['exclusions'], scorer_preflight=preflight)


def validate_bundle(root, descriptor, *, scratch_dir=None):
    """Validate existing files. Unsupported parity is explicit, never accepted."""
    stage = 'descriptor'
    checked = []
    identity = dict(schema_version=1, control_id=descriptor.get('control_id') if type(descriptor) is dict else None)
    try:
        descriptor = descriptor_contract(descriptor)
        variant = descriptor.get('variant')
        operation = descriptor.get('operation')
        require(variant in ('core_v2_catalog1', 'artifact_policy_v2')
            and operation in ('prepare_run', 'verify_run', 'inspect_run'), 'EP-WIRE-01', 'Unknown variant/operation')
        checked.append('descriptor')
        stage = operation
        run_dir = child(root, descriptor['paths']['run_dir']) if operation != 'prepare_run' else None
        outer = run_dir is not None and any((run_dir / name).exists() for name in (
            'tether-manifest.json', 'tether-receipt.json', 'tether-failure.json', 'attempt'))
        if variant == 'artifact_policy_v2' or outer:
            from .independent_policy import validate_policy_bundle
            observed = validate_policy_bundle(Path(root), descriptor, scratch_dir=scratch_dir)
        elif operation == 'prepare_run':
            observed = prepare_core(Path(root), descriptor)
        elif operation == 'verify_run':
            trusted = read_json(child(root, descriptor['paths']['trusted_runtime'])) if descriptor['paths'].get('trusted_runtime') else None
            observed = verify_core(run_dir, (descriptor.get('anchors') or {}).get('receipt_sha256'),
                                   trusted_runtime=trusted)
        else:
            observed = dict(recovery=inspect_core(run_dir))
        checked.append(operation)
        return dict(**identity, decision='inspect_only' if operation == 'inspect_run' else 'accept', stage=stage,
                    violated_obligations=[], checked_scope=checked, observables=observed)
    except PolicyError as error:
        return dict(**identity, decision='reject', stage=stage, violated_obligations=[error.obligation],
                    checked_scope=checked, observables={}, error=str(error))
    except (ModuleNotFoundError, UnsupportedPolicy) as error:
        return dict(**identity, decision='unsupported', stage=stage, violated_obligations=[], checked_scope=checked,
                    observables={}, error=str(error))
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError) as error:
        return dict(**identity, decision='reject', stage=stage, violated_obligations=['EP-IO-01'],
                    checked_scope=checked, observables={}, error=type(error).__name__ + ': ' + str(error))
    except (OSError, KeyError, TypeError, ValueError, RecursionError) as error:
        return dict(**identity, decision='error', stage=stage, violated_obligations=[],
                    checked_scope=checked, observables={}, error=type(error).__name__ + ': ' + str(error))
