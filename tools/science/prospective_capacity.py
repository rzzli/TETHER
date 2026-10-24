"""Explicit capacity profiles over the immutable v0.1 scientific contract.

Preparation and offline audit never contact a source. Only execute can consume a
fresh amendment claim. Selection remains an offline, unsealed candidate list.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import shutil
import time
from urllib.parse import urlencode

from asof.journal import RunJournal, read_chain
from asof.serde import fingerprint, parse_json, read_json, write_json
from tools.science import prospective_frame as frame
from tools.science import prospective_transport as transport

AMENDMENT = 'planning/protocols/prospective-endpoint-capacity-v0.2.json'
SEED = '54da82a9dcac5c295d9f68aab818657ec131957a4166ce9d5585019051b43c0a'
PATCH = {'frame_max_records': 5000, 'page_size': 500}
CAPS = dict(frame.CAPS, **PATCH)
SCOPE = {'clinical_activation': False, 'model_dispatch_allowed': False,
         'source_rule_pdf_queries': 0, 'selected_members': 0, 'provider_spend_usd': 0}
POLICY = dict(transport.POLICY, caps=CAPS,
              recovery='inspect retained evidence only; never redispatch this amendment, including failed calls')
require = frame.require


def page_request(contract, token=None):
    request = frame._request(contract['interval_start'], contract['interval_end'], token)
    request['parameters']['pageSize'] = str(CAPS['page_size'])
    request['url'] = frame.ENDPOINT + '?' + urlencode(request['parameters'])
    return request


def _relative_pin(root, value):
    require(isinstance(value, dict) and set(value) == {'path', 'sha256', 'bytes'}, 'Invalid amendment pin')
    path = frame._inside(root, value['path'])
    pin = frame._pin(path)
    require(pin['sha256'] == value['sha256'] and pin['bytes'] == value['bytes'], 'Amendment source changed')
    return pin


def _offline_bound(root, path):
    """Replay bound ancestry without interpreting today's date as dispatch consent."""
    bound = read_json(path)
    require(bound['status'] == 'named_origin_inventory_bound_before_source_dispatch'
            and bound['source_dispatch_allowed'] is False and bound['clinical_activation'] is False,
            'Wrong exposure-bound proposal')
    sources = [bound[k] for k in ('contract', 'request', 'journal', 'inventory_receipt', 'inventory')]
    for pin in sources:
        frame._check_pin(pin)
        require(Path(pin['path']).resolve().is_relative_to(root), 'Bound source escaped')
    contract = frame.verify_build(Path(bound['contract']['path']).parent)
    require(contract['repo_root'] == str(root)
            and read_json(Path(bound['request']['path'])) == frame.page_request(contract), 'Bound request differs')
    inventory_receipt = read_json(Path(bound['inventory_receipt']['path']))
    require(inventory_receipt['inventory'] == bound['inventory'], 'Inventory binding differs')
    for key in ('report', 'journal'):
        pin = inventory_receipt[key]
        frame._check_pin(pin)
        require(Path(pin['path']).resolve().is_relative_to(root), 'Inventory source escaped')
        sources.append(pin)
    read_chain(Path(inventory_receipt['journal']['path']))
    ids = read_json(Path(bound['inventory']['path']))['nct_ids']
    require(isinstance(ids, list) and ids == sorted(set(ids)) == contract['exposed_ids']
            and len(ids) == bound['named_source_inventory_ids'] == inventory_receipt['distinct_exposed_nct_ids'],
            'Exposure inventory differs')
    require(all(bound[k] == contract[k] for k in ('readiness_date_R', 'interval_start', 'interval_end')),
            'Bound dates differ')
    return contract, sources


def _profile(root, path, *, replay=False):
    amendment = read_json(path)
    require(set(amendment) <= {'schema_version', 'protocol_id', 'status', 'created_at_utc',
            'base_protocol', 'capacity_patch', 'sampling_seed_sha256', 'preserved_readiness_date_R',
            'preserved_interval_start', 'preserved_interval_end', 'base_bound_request',
            'stopped_attempt', 'technical_scope', 'rationale', 'invariants', 'exposure_disclosure',
            'no_automatic_retry', 'required_validation'}, 'Unrecognized amendment override')
    require(amendment.get('no_automatic_retry', True) is True, 'Retry scope changed')
    require(amendment['schema_version'] == 1
            and amendment['protocol_id'] == 'prospective-endpoint-capacity-v0.2'
            and amendment['status'] == 'capacity_only_amendment'
            and amendment['capacity_patch'] == PATCH
            and amendment['sampling_seed_sha256'] == SEED
            and amendment['technical_scope'] == SCOPE, 'Capacity-only profile changed')
    base = _relative_pin(root, amendment['base_protocol'])
    bound_pin = _relative_pin(root, amendment['base_bound_request'])
    stop_pin = _relative_pin(root, amendment['stopped_attempt'])
    require(base['sha256'] == SEED and Path(base['path']) == root / frame.PROTOCOL,
            'Original protocol sampling ancestry changed')
    require(Path(bound_pin['path']) == root / transport.BOUND_REQUEST, 'Bound request ancestry changed')
    contract, sources = (_offline_bound if replay else transport._bound)(root, Path(bound_pin['path']))
    require(contract['protocol'] == base, 'Base protocol differs from bound contract')
    for key, expected in (('readiness_date_R', '2026-10-24'),
                          ('interval_start', '2026-09-24'), ('interval_end', '2026-10-23')):
        require(amendment['preserved_' + key] == contract[key] == expected, 'Scientific dates changed')
    # All scientific fields are taken exclusively from the validated old bound
    # request. No amendment field can override projection, exclusions or screen.
    stop = read_json(Path(stop_pin['path']))
    require(stop['status'] == 'cold_source_attempt_audited_stopped_at_frozen_capacity_gate'
            and stop['declared_query_count'] == 4277 and stop['completed_frame'] is False
            and stop['clinical_activation'] is False and stop['selected_members'] == 0
            and stop['automatic_retries'] == 0 and stop['unresolved_attempts'] == [], 'Invalid retained capacity stop')
    stop_sources = [stop[k] for k in ('execution_manifest', 'journal')] + stop['raw_bodies']
    for pin in stop_sources:
        frame._check_pin(pin)
        require(Path(pin['path']).resolve().is_relative_to(root), 'Stop proof escaped')
    old_manifest = read_json(Path(stop['execution_manifest']['path']))
    old_unsigned = dict(old_manifest)
    old_digest = old_unsigned.pop('manifest_sha256')
    require(fingerprint(old_unsigned) == old_digest
            and old_manifest['kind'] == 'prospective_bounded_source_execution'
            and old_manifest['repo_root'] == str(root)
            and Path(stop['execution_manifest']['path']).parent == Path(old_manifest['output']),
            'Stopped manifest commitment differs')
    require(old_manifest['bound_request'] == bound_pin and old_manifest['contract'] == read_json(Path(bound_pin['path']))['contract'],
            'Stopped execution lineage differs')
    old_events = read_chain(Path(stop['journal']['path']))
    require(old_events[-1]['event'] in ('run_failed', 'run_interrupted')
            and not any(e['event'] == 'execution_completed' for e in old_events), 'Old attempt must remain failed')
    starts = [e for e in old_events if e['event'] == 'attempt_started']
    terminals = [e for e in old_events if e['event'] == 'attempt_terminal']
    require(len(starts) == len(terminals) == 2
            and [e['details']['attempt'] for e in starts] == [0, 1]
            and [e['details']['attempt'] for e in terminals] == [0, 1], 'Old stop attempt accounting differs')
    require(len(stop['raw_bodies']) == 2 and all(
        terminal['details']['retained_body'] == pin
        and terminal['details']['outcome'] == 'received'
        and terminal['details']['streamed_bytes'] == pin['bytes']
        for terminal, pin in zip(terminals, stop['raw_bodies'])), 'Old raw receipt lineage differs')
    require(starts[0]['details']['request'] == transport.VERSION_REQUEST
            and starts[1]['details']['request'] == contract['request'], 'Old stopped request differs')
    old_claim_key = fingerprint({'request': contract['request'], 'protocol': contract['protocol']['sha256'],
        'readiness_date_R': contract['readiness_date_R'],
        'inventory': read_json(Path(bound_pin['path']))['inventory']['sha256']})
    old_claim_path = root / frame.OUTPUT_ROOT / ('source-claim-' + old_claim_key) / 'execution.json'
    old_claim = read_json(old_claim_path)
    require(old_claim['output'] == old_manifest['output']
            and old_claim['manifest'] == stop['execution_manifest'], 'Old no-redispatch claim missing/changed')
    stop_sources.append(frame._pin(old_claim_path))
    require(parse_json(Path(stop['raw_bodies'][1]['path']).read_bytes())['totalCount'] == 4277,
            'Retained capacity count differs')
    for pair in old_manifest['archives']:
        stop_sources += [pair['source'], pair['archive']]
    stop_sources += [old_manifest['policy']]
    sources += [base, bound_pin, stop_pin, *stop_sources, *contract['parents'], *contract['code_pins'],
                frame._pin(path), frame._pin(Path(__file__)), frame._pin(Path(transport.__file__))]
    if contract['acceptance_pin']:
        sources.append(contract['acceptance_pin'])
    for pin in sources:
        frame._check_pin(pin)
    return contract, {p['path']: p for p in sources}


def _output(root, output):
    destination = Path(output)
    require('..' not in destination.parts, 'Output traversal forbidden')
    destination = destination.resolve()
    allowed = (root / frame.OUTPUT_ROOT).resolve()
    require(allowed.is_relative_to(root) and destination.is_relative_to(allowed)
            and destination != allowed, 'Execution output escaped')
    return destination


def prepare_execution(repo_root, output, *, expected_amendment_sha256, amendment_path=AMENDMENT):
    root = Path(repo_root).resolve()
    output = _output(root, output)
    journal = RunJournal(output)
    try:
        path = frame._inside(root, amendment_path)
        require(frame._pin(path)['sha256'] == expected_amendment_sha256, 'Amendment digest mismatch')
        contract, sources = _profile(root, path)
        archive = output / 'archive'
        archive.mkdir()
        archived = []
        for index, pin in enumerate(sources.values()):
            target = archive / f'{index:03d}-{Path(pin["path"]).name}'
            shutil.copyfile(pin['path'], target)
            require(frame._pin(target)['sha256'] == pin['sha256'], 'Source changed during archive')
            archived.append({'source': pin, 'archive': frame._pin(target)})
        write_json(output / 'effective-policy.json', POLICY)
        manifest = {'kind': 'prospective_capacity_source_execution', 'schema_version': 1,
                    'repo_root': str(root), 'output': str(output),
                    'prepared_at_utc': transport._now().isoformat(),
                    'readiness_date_R': contract['readiness_date_R'], 'amendment': frame._pin(path),
                    'request': page_request(contract), 'sampling_seed_sha256': SEED,
                    'policy': frame._pin(output / 'effective-policy.json'), 'archives': archived,
                    'clinical_activation': False, 'source_dispatch_allowed': True}
        manifest['manifest_sha256'] = fingerprint(manifest)
        write_json(output / 'execution.json', manifest)
        journal.append('execution_prepared', manifest=frame._pin(output / 'execution.json'), network_requests=0)
        return manifest
    except BaseException as exc:
        journal.fail(exc, 'prepare_capacity_execution')
        raise
    finally:
        journal.close()


def _preflight(output, expected, *, replay=False):
    output = Path(output)
    require('..' not in output.parts, 'Execution traversal forbidden')
    output = output.resolve()
    path = output / 'execution.json'
    require(frame._pin(path)['sha256'] == expected, 'Execution manifest digest mismatch')
    manifest = read_json(path)
    unsigned = dict(manifest)
    digest = unsigned.pop('manifest_sha256')
    root = Path(manifest['repo_root']).resolve()
    require(_output(root, output) == output and manifest['output'] == str(output)
            and fingerprint(unsigned) == digest
            and manifest['kind'] == 'prospective_capacity_source_execution'
            and manifest['schema_version'] == 1 and manifest['clinical_activation'] is False
            and manifest['source_dispatch_allowed'] is True and manifest['sampling_seed_sha256'] == SEED,
            'Invalid capacity execution manifest')
    frame._check_pin(manifest['amendment'])
    require(Path(manifest['amendment']['path']).resolve().is_relative_to(root), 'Amendment escaped')
    contract, sources = _profile(root, Path(manifest['amendment']['path']), replay=replay)
    require(manifest['request'] == page_request(contract), 'Amended exact request changed')
    require(manifest['policy'] == frame._pin(output / 'effective-policy.json')
            and read_json(output / 'effective-policy.json') == POLICY, 'Capacity policy changed')
    require(len(manifest['archives']) == len(sources)
            and {p['source']['path']: p['source'] for p in manifest['archives']} == sources,
            'Required archive inventory incomplete')
    archive_paths = set()
    for pair in manifest['archives']:
        frame._check_pin(pair['source'])
        frame._check_pin(pair['archive'])
        archived = Path(pair['archive']['path']).resolve()
        require(archived.is_relative_to(output / 'archive') and archived not in archive_paths
                and pair['archive']['sha256'] == pair['source']['sha256'], 'Archive mismatch')
        archive_paths.add(archived)
    events = read_chain(output / 'journal.jsonl')
    require(len(events) >= 2 and events[1]['event'] == 'execution_prepared'
            and events[1]['details']['manifest'] == frame._pin(path), 'Unsealed preparation')
    return output, manifest, contract, events


def _incremental(contract, payload, records, tokens, count):
    require(isinstance(payload, dict) and set(payload) <= {'studies', 'totalCount', 'nextPageToken'}
            and isinstance(payload.get('studies'), list) and len(payload['studies']) <= CAPS['page_size'],
            'Page projection/shape cap')
    declared = payload.get('totalCount', count)
    require(type(declared) is int and 0 <= declared <= CAPS['frame_max_records'], 'Complete frame count cap')
    require(count is None or count == declared, 'Count drift')
    tree = frame._tree(contract['projection'])
    for record in payload['studies']:
        frame._guard(record, tree)
        nct = frame._get(record, 'protocolSection', 'identificationModule', 'nctId')
        require(isinstance(nct, str) and re.fullmatch(r'NCT[0-9]{8}', nct) and nct not in records,
                'Noncanonical or duplicate NCT identity')
        status = frame._get(record, 'protocolSection', 'statusModule') or {}
        posted = frame._get(status, 'studyFirstPostDateStruct', 'date')
        require(frame._day(contract['interval_start']) <= frame._day(posted)
                <= frame._day(contract['interval_end']), 'Posting date outside interval')
        updated = frame._get(status, 'lastUpdatePostDateStruct', 'date')
        if updated is not None:
            require(frame._day(posted) <= frame._day(updated) <= frame._day(contract['readiness_date_R']),
                    'Update date conflict')
        phases = frame._get(record, 'protocolSection', 'designModule', 'phases')
        interventions = frame._get(record, 'protocolSection', 'armsInterventionsModule', 'interventions')
        require((phases is None or isinstance(phases, list))
                and (interventions is None or isinstance(interventions, list)), 'Malformed arrays')
        records[nct] = dict(frame._screen(record), nct_id=nct, exposure_excluded=nct in contract['exposed_ids'])
    require(len(records) <= declared, 'Records exceed declared count')
    token = payload.get('nextPageToken')
    if token is not None:
        page_request(contract, token)
        require(token not in tokens, 'Token loop')
        tokens.add(token)
    else:
        require(len(records) == declared, 'Partial terminal frame')
    return declared, token


def _version(output, receipt):
    version = parse_json(frame._inside(output, receipt['body']['path']).read_bytes())
    require(isinstance(version, dict) and set(version) == {'apiVersion', 'dataTimestamp'}
            and all(isinstance(v, str) and v for v in version.values()), 'Unknown version schema')
    return version


def _claim_key(manifest, contract):
    # Informational prose or creation timestamps cannot grant another attempt.
    return fingerprint({'amendment_profile': 'prospective-endpoint-capacity-v0.2',
                        'base_protocol': SEED, 'capacity_patch': PATCH, 'request': page_request(contract),
                        'inventory': contract['exposed_ids'], 'readiness_date_R': contract['readiness_date_R']})


def execute(output, *, expected_manifest_sha256, client=None):
    output, manifest, contract, events = _preflight(output, expected_manifest_sha256)
    require(events[-1]['event'] == 'execution_prepared', 'Execution already attempted')
    transport._exclusive_json(output / 'execution-claimed.json', {'claimed_at_utc': transport._now().isoformat()})
    journal = transport._journal(output)
    try:
        claim = Path(manifest['repo_root']) / frame.OUTPUT_ROOT / ('capacity-source-claim-' + _claim_key(manifest, contract))
        claim.mkdir(exist_ok=False)
        transport._exclusive_json(claim / 'execution.json', {'output': str(output), 'manifest': frame._pin(output / 'execution.json')})
        if client is None:
            client = transport.StdlibClient()
        else:
            require(getattr(client, 'evidence_kind', None) == 'synthetic', 'Injected client must be synthetic')
        journal.append('execution_started', evidence_kind=client.evidence_kind, global_claim=str(claim), clinical_activation=False)
        deadline, budget = time.monotonic() + CAPS['max_frame_elapsed_seconds'], [CAPS['max_frame_bytes']]
        before = transport._attempt(journal, output, transport.VERSION_REQUEST, client, 0, deadline, budget)
        version = _version(output, before)
        require(version['apiVersion'] == read_json(Path(manifest['repo_root']) / (frame.METADATA + '04-version.json'))['apiVersion'],
                'API version differs from archived schema')
        pages, records, tokens, count, token = [], {}, set(), None, None
        while True:
            require(len(pages) < CAPS['max_page_attempts'], 'Page attempt cap')
            page = transport._attempt(journal, output, page_request(contract, token), client, len(pages) + 1, deadline, budget)
            pages.append(page)
            count, token = _incremental(contract, parse_json((output / page['body']['path']).read_bytes()), records, tokens, count)
            if token is None:
                break
        after = transport._attempt(journal, output, transport.VERSION_REQUEST, client, len(pages) + 1, deadline, budget)
        require(_version(output, after) == version, 'Source version/dataTimestamp drift')
        receipt = {'status': 'complete_capacity_frame_capture', 'evidence_kind': client.evidence_kind,
                   'frame_count': count, 'study_queries': len(pages), 'version_queries': 2,
                   'version_before': before, 'version_after': after, 'pages': pages,
                   'source_version': version, 'collected_bytes': CAPS['max_frame_bytes'] - budget[0],
                   'transport_qualified': client.evidence_kind == 'live_authenticated_tls',
                   'atomic_snapshot': False, 'clinical_activation': False, 'selected_members': 0,
                   'model_calls': 0, 'source_rule_pdf_queries': 0,
                   'source_coverage': POLICY['source_coverage']}
        write_json(output / 'receipt.json', receipt)
        journal.append('execution_completed', receipt=frame._pin(output / 'receipt.json'))
        return receipt
    except BaseException as exc:
        journal.fail(exc, 'execute_capacity_source')
        raise
    finally:
        journal.close()


def inspect_execution(output):
    return dict(transport.inspect_execution(output), recovery=POLICY['recovery'])


def audit_capture(output, *, expected_manifest_sha256):
    """Replay every terminal attempt and original body; return unsealed candidates."""
    output, manifest, contract, events = _preflight(output, expected_manifest_sha256, replay=True)
    require(events[-1]['event'] == 'execution_completed'
            and events[-1]['details']['receipt'] == frame._pin(output / 'receipt.json'), 'Capture not sealed complete')
    receipt = read_json(output / 'receipt.json')
    require(receipt['status'] == 'complete_capacity_frame_capture' and receipt['selected_members'] == 0
            and receipt['clinical_activation'] is False and receipt['atomic_snapshot'] is False
            and receipt['model_calls'] == receipt['source_rule_pdf_queries'] == 0
            and receipt['evidence_kind'] in ('synthetic', 'live_authenticated_tls')
            and receipt['source_coverage'] == POLICY['source_coverage'], 'Source-only receipt changed')
    execution = [e['details'] for e in events if e['event'] == 'execution_started']
    claim = Path(manifest['repo_root']) / frame.OUTPUT_ROOT / ('capacity-source-claim-' + _claim_key(manifest, contract))
    require(len(execution) == 1 and execution[0]['global_claim'] == str(claim)
            and read_json(claim / 'execution.json') == {'output': str(output), 'manifest': frame._pin(output / 'execution.json')}
            and execution[0]['evidence_kind'] == receipt['evidence_kind']
            and receipt['transport_qualified'] == (receipt['evidence_kind'] == 'live_authenticated_tls'), 'Execution claim/evidence differs')
    pages = receipt['pages']
    require(isinstance(pages, list) and 0 < len(pages) <= CAPS['max_page_attempts'], 'Page attempt cap')
    attempts = [receipt['version_before'], *pages, receipt['version_after']]
    require([e['event'] for e in events] == ['run_reserved', 'execution_prepared', 'execution_started']
            + ['attempt_started', 'attempt_response_headers', 'attempt_terminal'] * len(attempts)
            + ['execution_completed'], 'Attempt event ordering differs')
    started = [e['details'] for e in events if e['event'] == 'attempt_started']
    terminal = [e['details'] for e in events if e['event'] == 'attempt_terminal']
    headers = [e['details'] for e in events if e['event'] == 'attempt_response_headers']
    require(len(attempts) == len(started) == len(terminal) == len(headers), 'Attempt journal mismatch')
    records, tokens, count, token, total, previous, first = {}, set(), None, None, 0, None, None
    for index, (part, begin, end, head) in enumerate(zip(attempts, started, terminal, headers)):
        request = transport.VERSION_REQUEST if index in (0, len(attempts) - 1) else page_request(contract, token)
        require(set(part) == {'request', 'body', 'http_status', 'final_url', 'attempt', 'started_at_utc', 'ended_at_utc'}
                and part['request'] == request and part['http_status'] == 200 and part['final_url'] == request['url']
                and part['attempt'] == 1 and begin['attempt'] == end['attempt'] == head['attempt'] == index
                and begin['request'] == request and end['outcome'] == 'received' and end['error_class'] is None
                and end['automatic_retry'] is False, 'Request/terminal journal differs')
        start, finish = frame._time(part['started_at_utc']), frame._time(part['ended_at_utc'])
        require(begin['started_at_utc'] == end['started_at_utc'] == part['started_at_utc']
                and end['ended_at_utc'] == part['ended_at_utc']
                and start.date().isoformat() == finish.date().isoformat() == contract['readiness_date_R']
                and start >= frame._time(contract['built_at_utc'])
                and start >= frame._time(manifest['prepared_at_utc'])
                and 0 <= (finish - start).total_seconds() <= CAPS['max_elapsed_seconds_per_request']
                and 0 <= end['elapsed_seconds'] <= CAPS['max_elapsed_seconds_per_request']
                and (previous is None or start >= previous), 'Capture timing differs')
        first, previous = first or start, finish
        require((finish - first).total_seconds() <= CAPS['max_frame_elapsed_seconds'], 'Frame elapsed cap')
        body = part['body']
        require(set(body) == {'path', 'bytes', 'sha256'} and body['path'] == f'{index:02d}-response.bin', 'Raw body lineage differs')
        pin = frame._pin(frame._inside(output, body['path']))
        require(body == {k: pin[k] for k in ('bytes', 'sha256')} | {'path': body['path']}
                and end['retained_body'] == pin and end['streamed_bytes'] == body['bytes']
                and 0 < body['bytes'] <= CAPS['max_bytes_per_page'], 'Raw bytes/journal differ')
        response = end['response']
        require(response == {k: head[k] for k in ('status', 'final_url', 'headers')}
                and response['status'] == 200 and response['final_url'] == request['url']
                and response['headers'].get('content-encoding', 'identity').lower() == 'identity', 'HTTP evidence differs')
        length = response['headers'].get('content-length')
        require(length is None or length.isdigit() and int(length) == body['bytes'], 'Partial raw response')
        total += body['bytes']
        if 0 < index < len(attempts) - 1:
            require(index == 1 or token is not None, 'Extra page after terminal')
            count, token = _incremental(contract, parse_json((output / body['path']).read_bytes()), records, tokens, count)
    require(token is None and count == len(records) == receipt['frame_count']
            and total == receipt['collected_bytes'] <= CAPS['max_frame_bytes']
            and receipt['study_queries'] == len(pages) and receipt['version_queries'] == 2, 'Incomplete/count/byte accounting')
    version = _version(output, attempts[0])
    require(version == _version(output, attempts[-1]) == receipt['source_version']
            and version['apiVersion'] == read_json(Path(manifest['repo_root']) / (frame.METADATA + '04-version.json'))['apiVersion'], 'Source metadata/version drift')
    pool = [n for n, row in records.items() if row['screen'] != 'ineligible' and not row['exposure_excluded']]
    pool.sort(key=lambda n: (hashlib.sha256((SEED + n).encode()).hexdigest(), n))
    return {'complete': True, 'frame_count': count, 'candidate_nct_ids': pool[:12],
            'all_member_ledger': [records[n] for n in sorted(records)], 'sampling_seed_sha256': SEED,
            'selected_members': 0, 'clinical_activation': False, 'evidence_kind': receipt['evidence_kind'],
            'transport_qualified': receipt['transport_qualified'], 'atomic_snapshot': False}
