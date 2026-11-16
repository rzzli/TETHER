"""Small specification-based checker; no imports from the TETHER runtime.

See docs/FORMAT-CONTRACTS.md. This checks a caller-owned static copy, not a
hostile concurrently changing filesystem. It never opens serialized source paths.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import stat
import sys
import unicodedata

MIB = 1024 * 1024
POLICY = 'tether.derivation.v1'
VERSION = '0.6.0.dev1'
OUTPUTS = frozenset(('run.json', 'inputs.json', 'ledger.json', 'features.json',
                     'prediction.json', 'trace.jsonl', 'journal.jsonl', 'dossier.md'))
BUNDLE_OUTPUTS = OUTPUTS - {'journal.jsonl'}
CATEGORIES = ('genetics', 'perturbation', 'expression', 'modality', 'literature',
              'clinical', 'safety', 'pathway')


class Rejected(ValueError):
    def __init__(self, reason, detail=''):
        self.reason = reason
        super().__init__(reason + (': ' + detail if detail else ''))


class Unavailable(Rejected):
    pass


def demand(condition, reason, detail=''):
    if not condition:
        raise Rejected(reason, detail)


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


def hash_text(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def parse(payload):
    def pairs(items):
        result = {}
        for key, value in items:
            demand(key not in result, 'json_duplicate_key')
            result[key] = value
        return result

    def number(text):
        value = float(text)
        demand(math.isfinite(value), 'json_nonfinite')
        return value

    def bad_constant(_):
        raise Rejected('json_nonfinite')

    try:
        value = json.loads(payload.decode('utf-8-sig'), object_pairs_hook=pairs,
                           parse_float=number, parse_constant=bad_constant)
        stack = [(iter((value,)), 0)]
        while stack:
            iterator, depth = stack[-1]
            try:
                item = next(iterator)
            except StopIteration:
                stack.pop()
                continue
            if isinstance(item, (dict, list)):
                demand(depth < 128, 'json_depth')
                if isinstance(item, dict):
                    for key in item:
                        key.encode('utf-8')
                    item = item.values()
                stack.append((iter(item), depth + 1))
            elif type(item) is str:
                item.encode('utf-8')
        return value
    except Rejected:
        raise
    except (UnicodeError, ValueError, RecursionError) as error:
        raise Rejected('json_invalid') from error


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def fp(value):
    return digest(canonical(value))


def anchor(value):
    if value is None:
        return None
    demand(type(value) is str and re.fullmatch('[0-9a-fA-F]{64}', value) is not None,
           'anchor_invalid')
    return value.lower()


def logical(name):
    demand(type(name) is str and 0 < len(name) <= 512, 'path_invalid')
    demand(unicodedata.normalize('NFC', name) == name, 'path_invalid')
    parts = name.split('/')
    for part in parts:
        demand(0 < len(part) <= 120 and part not in ('.', '..') and
               not part.endswith((' ', '.')) and
               not any(ord(c) < 32 or ord(c) == 127 or unicodedata.category(c) == 'Cs' or
                       c in '\\:<>"|?*' for c in part), 'path_invalid')
        demand(not re.fullmatch(r'(CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|COM[0-9¹²³]|LPT[0-9¹²³])',
                                part.split('.')[0].rstrip(), re.IGNORECASE), 'path_invalid')
    return parts


class StaticCopy:
    """Bounded reads with before/after identity checks; no executable payloads."""
    def __init__(self, root):
        demand(not str(root).startswith(('\\\\', '//')), 'path_invalid')
        self.root = Path(root).resolve(strict=True)
        demand(self.root.is_dir() and not str(self.root).startswith(('\\\\', '//')), 'path_invalid')
        self.consumed = 0

    def read(self, name, limit, *, hardlinks=True):
        path = self.root
        parts = logical(name)
        for index, part in enumerate(parts):
            path = path / part
            info = path.lstat()
            demand(not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0) & 0x400,
                   'linked_member')
            demand(stat.S_ISREG(info.st_mode) if index == len(parts) - 1 else stat.S_ISDIR(info.st_mode),
                   'member_type')
        demand(hardlinks or info.st_nlink == 1, 'linked_member')
        demand(info.st_size <= limit, 'size_limit')
        if self.consumed + info.st_size > 512 * MIB:
            raise Unavailable('aggregate_read_limit')
        signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns, s.st_nlink)
        with path.open('rb') as stream:
            demand(signature(info) == signature(os.fstat(stream.fileno())), 'member_changed')
            payload = stream.read(limit + 1)
            demand(signature(info) == signature(os.fstat(stream.fileno())) == signature(path.lstat()),
                   'member_changed')
        demand(len(payload) == info.st_size and len(payload) <= limit, 'size_limit')
        self.consumed += len(payload)
        return payload


def chain(payload):
    demand(len(payload) <= 64 * MIB, 'size_limit')
    records = []
    for line in payload.splitlines():
        row = parse(line)
        demand(type(row) is dict and type(row.get('sequence')) is int and
               row['sequence'] == len(records), 'journal_sequence')
        demand(type(row.get('event')) is str and row['event'] and type(row.get('details')) is dict,
               'journal_shape')
        demand(row.get('previous_sha256') == (records[-1]['sha256'] if records else None), 'journal_predecessor')
        demand(hash_text(row.get('sha256')) and
               row['sha256'] == fp({k: v for k, v in row.items() if k != 'sha256'}), 'journal_digest')
        records.append(row)
    demand(bool(records), 'journal_empty')
    return records


def usage(value):
    demand(type(value) is dict and set(value) == {'input_tokens', 'output_tokens', 'cost_usd'}, 'usage_shape')
    demand(all(type(value[k]) is int and value[k] >= 0 for k in ('input_tokens', 'output_tokens')), 'usage_shape')
    cost = value['cost_usd']
    demand(type(cost) in (int, float) and math.isfinite(cost) and cost >= 0, 'usage_shape')
    return (value['input_tokens'], value['output_tokens'], Fraction(str(cost)))


def declared_claims(receipt, inputs, claims):
    """Check declared used ancestry only; no source bytes or eligibility inference."""
    snapshot = inputs['snapshot']
    artifacts = {a['artifact_id']: a for a in snapshot['artifacts']}
    sources = {s['source_id']: s for s in snapshot['sources']}
    proofs = {p['artifact_id']: p for p in receipt['sources']}
    demand(len(artifacts) == len(snapshot['artifacts']) and len(sources) == len(snapshot['sources']) and
           not set(artifacts) & set(sources) and len(proofs) == len(receipt['sources']), 'lineage_inventory')

    def declared_path(base, relative):
        demand(type(base) is str and type(relative) is str, 'lineage_path')
        logical(relative.replace('\\', '/'))
        constructor = PureWindowsPath if PureWindowsPath(base).drive else PurePosixPath
        return str(constructor(base).joinpath(*relative.replace('\\', '/').split('/')))

    for key, proof in proofs.items():
        definition = artifacts.get(key, sources.get(key))
        demand(definition is not None, 'lineage_inventory')
        for field in ('dataset_id', 'release_id', 'sha256'):
            demand(proof[field] == definition[field], 'lineage_binding', key)
        base = inputs['snapshot_base']
        if key in sources and not definition.get('computed_at'):
            base = snapshot.get('raw_root') or base
        demand(proof['path'] == declared_path(base, definition['path']), 'lineage_binding', key)
        if key in sources:
            demand(proof['parents'] == definition['parents'] and proof['role'] == definition['role'], 'lineage_binding', key)
            if definition.get('receipt_path'):
                demand(proof.get('receipt_sha256') == definition['receipt_sha256'] and
                       proof.get('receipt_path') == declared_path(snapshot.get('raw_root') or inputs['snapshot_base'],
                                                                  definition['receipt_path']), 'lineage_binding', key)
    done, visiting = set(), set()

    def ancestors(key):
        demand(key in sources and key in proofs, 'lineage_omission', str(key))
        demand(key not in visiting, 'lineage_cycle')
        if key in done:
            return
        visiting.add(key)
        for parent in sources[key]['parents']:
            ancestors(parent)
        visiting.remove(key)
        done.add(key)

    seen = set()
    for claim in claims:
        evidence = claim['evidence']
        observation, citation = evidence['observation'], evidence['citation']
        oid, aid = observation['observation_id'], citation['artifact_id']
        demand(oid not in seen, 'claim_duplicate')
        seen.add(oid)
        demand(fp(evidence) == claim['admitted_fingerprint'] == receipt['admitted_fingerprints'].get(oid), 'claim_fingerprint')
        demand(aid in artifacts and aid in proofs, 'lineage_omission', aid)
        demand(citation['artifact_sha256'] == artifacts[aid]['sha256'], 'lineage_binding', aid)
        demand(all(citation[k] == artifacts[aid][k] for k in ('dataset_id', 'release_id')), 'lineage_binding', aid)
        demand(claim['specialist'] == observation['category'] and
               all(observation[k] == inputs['case']['hypothesis'][k] for k in ('target_id', 'indication_id')), 'claim_scope')
        if observation.get('program_id') is not None:
            program = inputs['case'].get('program')
            demand(program is not None and program['mapping_confidence'] > 0 and
                   program['program_id'] == observation['program_id'], 'claim_scope')
        for ref in (*artifacts[aid]['input_refs'], *observation['input_refs']):
            ancestors(ref)


def completed_consistency(receipt, documents, trace):
    """Parse a narrow successful execution grammar, not the production reducer."""
    run, inputs = documents['run.json'], documents['inputs.json']
    demand(type(run.get('schema_version')) is int and run['schema_version'] == 2, 'run_version')
    if run.get('backend_id') != 'offline-extractive-v1' or run.get('status') != 'completed':
        raise Unavailable('execution_profile_unavailable')
    if any(r['event'] not in {'run_reserved', 'inputs_archived', 'plan', 'dispatch',
                            'attempt_accounted', 'review', 'claim_committed', 'finalize'} for r in trace):
        raise Unavailable('execution_profile_unavailable')
    config, case, snapshot = inputs['configuration'], inputs['case'], inputs['snapshot']
    demand(all(type(item.get('schema_version')) is int and item['schema_version'] == 2
               for item in (case, snapshot)), 'input_version')
    demand(run['software_version'] == VERSION and
           run['admission_policy'] == config['admission_policy'] == POLICY, 'run_version')
    demand(run['case_id'] == case['case_id'] and run['snapshot_id'] == snapshot['snapshot_id'] and
           run['profile'] == snapshot['profile'] and run['backend_id'] == config['backend_id'], 'run_identity')
    demand(run['budget'] == config['budget'], 'budget_binding')
    demand(type(run['calls']) is int, 'accounting')
    demand(type(config['review_enabled']) is bool and set(config['disabled']) <= set(CATEGORIES), 'configuration')
    budget = run['budget']
    demand(all(type(budget[k]) is int and budget[k] >= 0 for k in
               ('max_calls', 'max_input_tokens', 'max_output_tokens', 'max_retries')), 'budget_shape')
    cap = usage(dict(input_tokens=budget['max_input_tokens'], output_tokens=budget['max_output_tokens'],
                     cost_usd=budget['max_cost_usd']))
    demand(type(budget['max_seconds']) in (int, float) and math.isfinite(budget['max_seconds']) and budget['max_seconds'] > 0,
           'budget_shape')
    plan = run['plan']
    demand([s['category'] for s in plan] == list(CATEGORIES) and set(run['coverage']) == set(CATEGORIES), 'plan_inventory')
    cursor, preamble = 0, set()
    while cursor < len(trace) and trace[cursor]['event'] in {'run_reserved', 'inputs_archived'}:
        name = trace[cursor]['event']
        demand(name not in preamble, 'event_order')
        preamble.add(name)
        cursor += 1

    def consume(name):
        nonlocal cursor
        demand(cursor < len(trace) and trace[cursor]['event'] == name, 'event_order', name)
        row = trace[cursor]['details']
        cursor += 1
        return row

    recorded = consume('plan')
    demand(recorded['snapshot_id'] == snapshot['snapshot_id'] and fp(recorded['configuration']) == fp(config) and
           fp(recorded['steps']) == fp(plan), 'plan_binding')
    total, calls, committed = (0, 0, Fraction(0)), 0, []
    for step in plan:
        category = step['category']
        coverage = run['coverage'][category]
        count = step['observed_records']
        demand(type(count) is int and count >= 0 and count == coverage['available_observations'], 'coverage_binding')
        state = 'disabled' if category in config['disabled'] else 'ready' if count else 'no_observed_evidence'
        demand(step['initial_status'] == state, 'plan_binding')
        if state != 'ready':
            demand(coverage['status'] == state, 'terminal_state')
            continue
        dispatch = consume('dispatch')
        demand(dispatch['category'] == category and type(dispatch['attempt']) is int and dispatch['attempt'] == 1 and
               dispatch['attempt_id'] == category + ':1' and hash_text(dispatch['request_sha256']), 'dispatch_binding')
        reserved = usage(dispatch['reserved'])
        demand(calls < budget['max_calls'] and all(total[i] + reserved[i] <= cap[i] for i in range(3)), 'reservation_budget')
        account = consume('attempt_accounted')
        demand(account['attempt_id'] == dispatch['attempt_id'], 'accounting')
        if account['basis'] != 'adapter_reported':
            raise Unavailable('execution_profile_unavailable')
        measured = usage(account['usage'])
        demand(all(measured[i] <= reserved[i] for i in range(3)), 'usage_overrun')
        total = tuple(total[i] + measured[i] for i in range(3))
        calls += 1
        review = consume('review')
        if review['problems']:
            raise Unavailable('execution_profile_unavailable')
        demand(review['problems'] == [] and review['category'] == category and
               fp(review['usage']) == fp(account['usage']), 'review_binding')
        selected = review['selected']
        demand(type(selected) is list and all(type(x) is str for x in selected) and len(selected) == len(set(selected)), 'review_binding')
        for oid in selected:
            claim = consume('claim_committed')['claim']
            demand(claim['specialist'] == category and claim['evidence']['observation']['observation_id'] == oid, 'claim_selection')
            committed.append(claim)
        demand(coverage['status'] == 'completed' and coverage['selected_observations'] == len(selected), 'terminal_state')
    final = consume('finalize')
    demand(cursor == len(trace), 'event_order', 'after finalize')
    demand(final['status'] == run['status'] and final['feature_sha256'] == fp(documents['features.json']) and
           final['prediction_sha256'] == fp(documents['prediction.json']), 'final_binding')
    demand(run['calls'] == calls, 'accounting')
    expected = dict(input_tokens=total[0], output_tokens=total[1], cost_usd=float(total[2]))
    demand(usage(run['usage']) == usage(expected) == usage(run['measured_usage']) and
           usage(run['estimated_usage']) == (0, 0, Fraction(0)), 'accounting')
    ledger = documents['ledger.json']
    demand(type(ledger['schema_version']) is int and ledger['schema_version'] == 2 and
           fp(ledger['claims']) == fp(committed), 'ledger_binding')
    declared_claims(receipt, inputs, ledger['claims'])


def native(copy, expected, bytes_only, allow_legacy):
    payload = copy.read('receipt.json', 64 * MIB)
    demand(expected is None or digest(payload) == expected, 'anchor_mismatch')
    receipt = parse(payload)
    version = receipt['schema_version']
    demand(type(version) is int, 'receipt_version')
    current = version == 2 and receipt.get('software_version') == VERSION and receipt.get('admission_policy') == POLICY
    legacy = (version, receipt.get('software_version')) in ((1, '0.1.0'), (2, '0.4.0')) and 'admission_policy' not in receipt
    demand(current or legacy, 'receipt_version')
    if legacy:
        demand(allow_legacy and bytes_only, 'legacy_opt_in_required')
    names = OUTPUTS - {'journal.jsonl'} if version == 1 else OUTPUTS
    demand(set(receipt['outputs']) == names, 'output_inventory')
    auxiliary = receipt.get('auxiliary_outputs', {})
    demand(type(auxiliary) is dict and set(auxiliary) <= {'request.json', 'backend-execution.json'}, 'output_inventory')
    files = {}
    for name, checksum in {**receipt['outputs'], **auxiliary}.items():
        demand(hash_text(checksum), 'output_digest')
        limit = 256 * MIB if name in ('ledger.json', 'dossier.md') else 64 * MIB
        blob = copy.read(name, limit)
        demand(digest(blob) == checksum, 'output_digest', name)
        if not bytes_only and (name == 'trace.jsonl' or name in OUTPUTS and name.endswith('.json')):
            files[name] = blob
    result = dict(receipt_sha256=digest(payload), byte_integrity='verified',
                  consistency='unavailable_legacy' if legacy else 'not_requested', assurance='byte_integrity')
    if bytes_only:
        return result
    demand(receipt['outputs']['trace.jsonl'] == receipt['outputs']['journal.jsonl'], 'journal_trace_binding')
    documents = {name: parse(files.pop(name)) for name in names if name.endswith('.json')}
    demand(fp(documents['inputs.json']) == receipt['input_fingerprint'] == documents['run.json']['input_fingerprint'], 'input_binding')
    completed_consistency(receipt, documents, chain(files['trace.jsonl']))
    return result | dict(consistency='verified_supported_completed_path', assurance='declared_completed_consistency',
                         source_bytes='not_checked', full_eligible_closure='not_checked',
                         information_eligibility='not_checked', exact_producer_replay='not_checked',
                         derivations_features_predictions_prose='not_recomputed')


def bundle(copy, expected, bytes_only):
    payload = copy.read('bundle.json', MIB, hardlinks=False)
    demand(expected is None or digest(payload) == expected, 'anchor_mismatch')
    manifest = parse(payload)
    demand(set(manifest) == {'format', 'admission_policy', 'source_tier', 'producer', 'objects'} and
           manifest['format'] == 'tether.portable_bundle.v1' and
           manifest['source_tier'] in ('included', 'receipts_only'), 'manifest_shape')
    demand(type(manifest['admission_policy']) is str and 0 < len(manifest['admission_policy']) <= 128, 'manifest_shape')
    producer = manifest['producer']
    demand(set(producer) == {'software_version', 'receipt_sha256', 'input_fingerprint', 'code', 'environment'} and
           type(producer['software_version']) is str and hash_text(producer['receipt_sha256']) and
           hash_text(producer['input_fingerprint']), 'manifest_shape')
    demand(set(producer['environment']) == {'python', 'platform', 'runtime_dependencies'}, 'manifest_shape')
    demand(type(producer['code']) is dict and 0 < len(producer['code']) <= 512, 'manifest_shape')
    for name, checksum in producer['code'].items():
        logical(name)
        demand(name.endswith('.py') and hash_text(checksum), 'manifest_shape')
    inventory = manifest['objects']
    demand(type(inventory) is dict and BUNDLE_OUTPUTS <= set(inventory) and len(inventory) <= 256 and
           len({k.casefold() for k in inventory}) == len(inventory), 'object_inventory')
    sizes, total = {}, 0
    for name, item in inventory.items():
        logical(name)
        demand(name in BUNDLE_OUTPUTS or name.startswith(('packets/', 'lineage/', 'originals/')), 'object_inventory')
        demand(set(item) == {'sha256', 'bytes'} and hash_text(item['sha256']) and type(item['bytes']) is int and
               0 <= item['bytes'] <= 64 * MIB, 'object_shape')
        checksum, size = item['sha256'], item['bytes']
        demand(checksum not in sizes or sizes[checksum] == size, 'object_shape')
        sizes[checksum] = size
        total += size
    demand(total <= 256 * MIB, 'size_limit')
    for checksum, size in sizes.items():
        blob = copy.read('objects/sha256/' + checksum, size, hardlinks=False)
        demand(len(blob) == size and digest(blob) == checksum, 'object_digest')
    if not bytes_only:
        raise Unavailable('bundle_replay_unavailable')
    return dict(manifest_sha256=digest(payload), byte_integrity='verified', assurance='byte_integrity',
                consistency='unavailable_bundle_replay', objects=len(inventory), logical_bytes=total)


def verify(root, *, kind='native', expected_sha256=None, bytes_only=False, allow_legacy=False):
    demand(type(bytes_only) is bool and type(allow_legacy) is bool, 'option_type')
    demand(kind in ('native', 'bundle'), 'kind')
    expected = anchor(expected_sha256)
    try:
        copy = StaticCopy(root)
        result = native(copy, expected, bytes_only, allow_legacy) if kind == 'native' else bundle(copy, expected, bytes_only)
        return result | dict(status='passed', checker='tether-independent-format-v1',
                             external_anchor='matched' if expected is not None else 'not_supplied',
                             authenticity='not_established', scientific_validation='not_established')
    except Rejected:
        raise
    except (KeyError, TypeError, AttributeError, ValueError, OverflowError, RecursionError) as error:
        raise Rejected('malformed_contract') from error
    except OSError as error:
        raise Rejected('file_unavailable', str(error)) from error


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--kind', choices=('native', 'bundle'), default='native')
    parser.add_argument('--anchor')
    parser.add_argument('--bytes-only', action='store_true')
    parser.add_argument('--allow-legacy', action='store_true')
    args = parser.parse_args(argv)
    try:
        result = verify(args.directory, kind=args.kind, expected_sha256=args.anchor,
                        bytes_only=args.bytes_only, allow_legacy=args.allow_legacy)
        code = 0
    except Unavailable as error:
        result, code = dict(status='unavailable', reason=error.reason, assurance='not_established'), 3
    except Rejected as error:
        result, code = dict(status='rejected', reason=error.reason, detail=str(error), assurance='not_established'), 2
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == '__main__':
    sys.exit(main())
