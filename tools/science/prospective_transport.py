"""One-shot, bounded public registry readiness capture (never clinical activation).

The non-dispatch proposal stays immutable. A separately reserved execution manifest
enables only its exact candidate query. The first live study call is qualification;
neither successful HTTP nor matching version receipts establishes an atomic snapshot.
"""
from __future__ import annotations

from datetime import datetime, timezone
import multiprocessing
import os
from pathlib import Path
import queue
import re
import shutil
import time
import urllib.error
import urllib.request

from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import fingerprint, parse_json, read_json, write_json
from tools.science import prospective_frame as frame

VERSION_URL = 'https://clinicaltrials.gov/api/v2/version'
BOUND_REQUEST = 'planning/review-assets/prospective-endpoint-readiness-20261023/exposure-bound-request.json'
VERSION_REQUEST = {'method': 'GET', 'url': VERSION_URL, 'authentication': False,
                   'automatic_retry': False, 'request_timeout_seconds': 40,
                   'max_elapsed_seconds': 120, 'max_response_bytes': 2 * 1024 * 1024}
POLICY = {'scope': 'bounded_public_registry_readiness_only', 'source_dispatch_allowed': True,
          'clinical_activation': False, 'model_dispatch_allowed': False,
          'membership_acquisition_allowed': False, 'selected_members': 0,
          'source_rule_pdf_queries': 0, 'provider_spend_usd': 0,
          'version_requests_max': 2, 'caps': frame.CAPS,
          'recovery': 'inspect retained evidence only; never redispatch this proposal, including failed calls',
          'source_coverage': 'Only query-returned dated records; no atomic snapshot or missing-date completeness claim.'}


def _now():
    return datetime.now(timezone.utc)


def _journal(output):
    """Reopen only after the exclusive execution claim has been acquired."""
    result = object.__new__(RunJournal)
    result.kind, result.output = 'run', output
    result.path = output / 'journal.jsonl'
    result._events = list(read_chain(result.path))
    result._durable_size = result.path.stat().st_size
    result._stream = result.path.open('r+b', buffering=0)
    return result


def _exclusive_json(path, payload):
    from tether_engine.serde import canonical
    with path.open('xb') as stream:
        stream.write(canonical(payload) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())


def _bound(root, bound_path):
    bound = read_json(bound_path)
    frame.require(bound['status'] == 'named_origin_inventory_bound_before_source_dispatch'
                  and bound['source_dispatch_allowed'] is False
                  and bound['clinical_activation'] is False, 'Wrong exposure-bound proposal')
    pins = [bound[k] for k in ('contract', 'request', 'journal', 'inventory_receipt', 'inventory')]
    for pin in pins:
        frame._check_pin(pin)
        frame.require(Path(pin['path']).resolve().is_relative_to(root), 'Source pin outside repository')
    contract = frame.verify_build(Path(bound['contract']['path']).parent)
    frame.require(contract['repo_root'] == str(root), 'Proposal belongs to another repository')
    frame.require(read_json(Path(bound['request']['path'])) == frame.page_request(contract), 'Bound request differs')
    inventory_receipt = read_json(Path(bound['inventory_receipt']['path']))
    frame.require(inventory_receipt['inventory'] == bound['inventory'], 'Inventory binding differs')
    for key in ('report', 'journal'):
        pin = inventory_receipt[key]
        frame._check_pin(pin)
        frame.require(Path(pin['path']).resolve().is_relative_to(root), 'Inventory source escaped')
        pins.append(pin)
    read_chain(Path(inventory_receipt['journal']['path']))
    inventory = read_json(Path(bound['inventory']['path']))
    ids = inventory['nct_ids']
    frame.require(isinstance(ids, list) and ids == sorted(set(ids))
                  and ids == contract['exposed_ids']
                  and len(ids) == bound['named_source_inventory_ids']
                  == inventory_receipt['distinct_exposed_nct_ids'], 'Exposure inventory is not exact')
    for key in ('readiness_date_R', 'interval_start', 'interval_end'):
        frame.require(bound[key] == contract[key], 'Bound dates differ')
    frame.require(contract['readiness_date_R'] == _now().date().isoformat(),
                  'Expired R; dates cannot move silently')
    return contract, pins


def prepare_execution(repo_root, output, *, expected_bound_sha256, bound_request=BOUND_REQUEST):
    """Reserve and pin a separate, explicit source execution authorization. No HTTP."""
    root = Path(repo_root).resolve()
    destination = Path(output)
    frame.require('..' not in destination.parts, 'Output traversal forbidden')
    destination = destination.resolve()
    allowed = (root / frame.OUTPUT_ROOT).resolve()
    frame.require(destination.is_relative_to(allowed) and destination != allowed
                  and allowed.is_relative_to(root), 'Execution output escaped')
    journal = RunJournal(destination)
    try:
        bound_path = frame._inside(root, bound_request)
        frame.require(frame._pin(bound_path)['sha256'] == expected_bound_sha256, 'Bound proposal digest mismatch')
        contract, sources = _bound(root, bound_path)
        sources += [frame._pin(bound_path), contract['protocol'], *contract['parents'],
                    *contract['code_pins'], frame._pin(Path(__file__))]
        if contract['acceptance_pin']:
            sources.append(contract['acceptance_pin'])
        unique = {pin['path']: pin for pin in sources}
        archive = destination / 'archive'
        archive.mkdir()
        archived = []
        for index, pin in enumerate(unique.values()):
            target = archive / f'{index:03d}-{Path(pin["path"]).name}'
            shutil.copyfile(pin['path'], target)
            frame.require(frame._pin(target)['sha256'] == pin['sha256'], 'Source changed during archive')
            archived.append({'source': pin, 'archive': frame._pin(target)})
        write_json(destination / 'effective-policy.json', POLICY)
        manifest = {'kind': 'prospective_bounded_source_execution', 'schema_version': 1,
                    'repo_root': str(root), 'output': str(destination),
                    'prepared_at_utc': _now().isoformat(), 'readiness_date_R': contract['readiness_date_R'],
                    'bound_request': frame._pin(bound_path), 'contract': read_json(bound_path)['contract'],
                    'policy': frame._pin(destination / 'effective-policy.json'),
                    'archives': archived, 'source_dispatch_allowed': True,
                    'clinical_activation': False, 'query_semantics': 'unqualified_until_actual_evidence'}
        manifest['manifest_sha256'] = fingerprint(manifest)
        write_json(destination / 'execution.json', manifest)
        journal.append('execution_prepared', manifest=frame._pin(destination / 'execution.json'), network_requests=0)
        return manifest
    except BaseException as exc:
        journal.fail(exc, 'prepare_execution')
        raise
    finally:
        journal.close()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http_worker(request, events):
    """Child process: no proxy, credentials, cookie jar, redirect or retry handler."""
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        req = urllib.request.Request(request['url'], method='GET', headers={
            'Accept': 'application/json', 'Accept-Encoding': 'identity',
            'User-Agent': 'prospective-readiness/0.1'})
        try:
            response = opener.open(req, timeout=40)
        except urllib.error.HTTPError as exc:
            response = exc  # Preserve error/redirect bytes without following them.
        with response:
            events.put(('headers', {'status': response.status, 'final_url': response.geturl(),
                                    'headers': dict(response.headers.items())}))
            while True:
                chunk = response.read1(65536)
                if not chunk:
                    break
                events.put(('body', chunk))
        events.put(('done', None))
    except BaseException as exc:
        events.put(('error', type(exc).__name__))


class StdlibClient:
    """Authenticated default TLS retrieval, forcibly stopped at the parent deadline."""
    evidence_kind = 'live_authenticated_tls'

    def stream(self, request, *, deadline):
        if time.monotonic() >= deadline:
            raise TimeoutError('HTTP deadline expired before dispatch')
        ctx = multiprocessing.get_context('spawn')
        events = ctx.Queue(maxsize=4)
        process = ctx.Process(target=_http_worker, args=(request, events), daemon=True)
        process.start()
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('Hard HTTP elapsed deadline')
                try:
                    kind, value = events.get(timeout=min(remaining, 0.1))
                except queue.Empty:
                    if not process.is_alive():
                        raise RuntimeError('HTTP worker ended without terminal receipt')
                    continue
                if kind == 'error':
                    raise OSError('HTTP worker failure: ' + value)
                if kind == 'done':
                    break
                yield kind, value
        finally:
            if process.is_alive():
                process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
            events.close()


def _headers(values):
    allowed = {'content-type', 'content-length', 'content-encoding', 'date', 'etag', 'last-modified'}
    return {str(k).lower(): re.sub(r'[\x00-\x1f\x7f]', '', str(v))[:4096]
            for k, v in values.items() if str(k).lower() in allowed}


def _attempt(journal, output, request, client, index, frame_deadline, budget):
    started, monotonic = _now(), time.monotonic()
    frame.require(monotonic < frame_deadline and budget[0] > 0, 'Frame elapsed/byte cap before dispatch')
    frame.require(started.date().isoformat() == read_json(output / 'execution.json')['readiness_date_R'],
                  'Expired capture date before dispatch')
    deadline = min(monotonic + 120, frame_deadline)
    name = f'{index:02d}-response.bin'
    path = output / name
    journal.append('attempt_started', attempt=index, request=request, started_at_utc=started.isoformat())
    response = None
    failure = None
    cleanup_error = None
    seen = 0
    iterator = None
    try:
        with path.open('xb') as raw:
            iterator = iter(client.stream(request, deadline=deadline))
            for kind, value in iterator:
                frame.require(time.monotonic() <= deadline, 'Hard HTTP/frame elapsed cap')
                frame.require(_now().date() == started.date(), 'Capture crossed UTC date R')
                if kind == 'headers':
                    frame.require(response is None and seen == 0 and isinstance(value, dict), 'Invalid HTTP headers event')
                    response = {'status': value['status'], 'final_url': value['final_url'],
                                'headers': _headers(value['headers'])}
                    journal.append('attempt_response_headers', attempt=index, **response)
                else:
                    frame.require(kind == 'body' and response is not None and isinstance(value, bytes), 'Invalid HTTP stream event')
                    seen += len(value)
                    room = max(0, min(2 * 1024 * 1024 - raw.tell(), budget[0]))
                    retained = value[:room]
                    raw.write(retained)
                    raw.flush()
                    os.fsync(raw.fileno())
                    budget[0] -= len(retained)
                    frame.require(len(retained) == len(value), 'HTTP streamed byte cap exceeded')
            frame.require(time.monotonic() <= deadline, 'Hard HTTP/frame elapsed cap')
            frame.require(response is not None and response['status'] == 200
                          and response['final_url'] == request['url'], 'HTTP error or redirect (never followed/retried)')
            frame.require(response['headers'].get('content-encoding', 'identity').lower() == 'identity',
                          'Encoded response forbidden')
            length = response['headers'].get('content-length')
            frame.require(length is None or length.isdigit() and int(length) == seen, 'Partial response length')
    except BaseException as exc:
        failure = type(exc).__name__
        raise
    finally:
        if iterator is not None and hasattr(iterator, 'close'):
            try:
                iterator.close()
            except BaseException as exc:
                # Closing cannot suppress the durable terminal accounting.
                cleanup_error = exc
                failure = failure or 'StreamCloseFailure'
        ended = _now()
        journal.append('attempt_terminal', attempt=index, outcome='failed' if failure else 'received',
                       error_class=failure, response=response, streamed_bytes=seen,
                       retained_body=frame._pin(path) if path.exists() else None,
                       started_at_utc=started.isoformat(), ended_at_utc=ended.isoformat(),
                       elapsed_seconds=time.monotonic() - monotonic, automatic_retry=False)
    if cleanup_error is not None:
        raise cleanup_error
    return {'request': request, 'body': {'path': name, 'bytes': path.stat().st_size,
                                      'sha256': frame._pin(path)['sha256']},
            'http_status': response['status'], 'final_url': response['final_url'], 'attempt': 1,
            'started_at_utc': started.isoformat(), 'ended_at_utc': ended.isoformat()}


def _incremental(contract, payload, ids, tokens, count):
    frame.require(isinstance(payload, dict) and set(payload) <= {'studies', 'totalCount', 'nextPageToken'}
                  and isinstance(payload.get('studies'), list) and len(payload['studies']) <= 100,
                  'Page projection/shape cap')
    declared = payload.get('totalCount', count)
    frame.require(type(declared) is int and declared >= 0, 'Missing or malformed totalCount')
    frame.require(count is None or declared == count, 'Count drift')
    tree = frame._tree(contract['projection'])
    for record in payload['studies']:
        frame._guard(record, tree)
        nct = frame._get(record, 'protocolSection', 'identificationModule', 'nctId')
        frame.require(isinstance(nct, str) and re.fullmatch(r'NCT[0-9]{8}', nct) and nct not in ids,
                      'Noncanonical or duplicate NCT identity')
        status = frame._get(record, 'protocolSection', 'statusModule') or {}
        posted = frame._get(status, 'studyFirstPostDateStruct', 'date')
        frame.require(frame._day(contract['interval_start']) <= frame._day(posted)
                      <= frame._day(contract['interval_end']), 'First posting date outside frozen interval')
        updated = frame._get(status, 'lastUpdatePostDateStruct', 'date')
        if updated is not None:
            frame.require(frame._day(posted) <= frame._day(updated) <= frame._day(contract['readiness_date_R']),
                          'Future/conflicting update date')
        phases = frame._get(record, 'protocolSection', 'designModule', 'phases')
        interventions = frame._get(record, 'protocolSection', 'armsInterventionsModule', 'interventions')
        frame.require((phases is None or isinstance(phases, list))
                      and (interventions is None or isinstance(interventions, list)
                           and all(isinstance(x, dict) for x in interventions)), 'Malformed projected arrays')
        ids.add(nct)
    frame.require(declared <= 500,
                  'Explicit capacity gate: source declares over frozen 500; query completeness/capacity unresolved; not scientific absence')
    frame.require(len(ids) <= declared, 'Records exceed declared count')
    token = payload.get('nextPageToken')
    if token is not None:
        frame.page_request(contract, token)
        frame.require(token not in tokens, 'Token loop')
        tokens.add(token)
    else:
        frame.require(len(ids) == declared, 'Partial terminal frame')
    return declared, token


def execute(output, *, expected_manifest_sha256, client=None):
    """Consume a fresh manifest once; fixtures must identify themselves as synthetic.

    No recovery path dispatches. A global proposal claim also prevents a second
    execution manifest from retrying a failed or interrupted exact proposal.
    """
    destination = Path(output)
    frame.require('..' not in destination.parts, 'Execution traversal forbidden')
    output = destination.resolve()
    # Validate the trusted manifest and containment before creating even a claim
    # marker. In particular, a copied manifest cannot reserve an arbitrary path.
    manifest_path = output / 'execution.json'
    frame.require(frame._pin(manifest_path)['sha256'] == expected_manifest_sha256,
                  'Execution manifest digest mismatch')
    preflight = read_json(manifest_path)
    unsigned = dict(preflight)
    digest = unsigned.pop('manifest_sha256')
    root = Path(preflight['repo_root']).resolve()
    frame.require(fingerprint(unsigned) == digest and preflight['output'] == str(output)
                  and preflight['kind'] == 'prospective_bounded_source_execution'
                  and preflight['source_dispatch_allowed'] is True and preflight['clinical_activation'] is False,
                  'Invalid source execution manifest')
    allowed = (root / frame.OUTPUT_ROOT).resolve()
    frame.require(allowed.is_relative_to(root) and output.is_relative_to(allowed) and output != allowed,
                  'Execution output escaped')
    frame._check_pin(preflight['contract'])
    frame.require(read_json(Path(preflight['contract']['path']))['repo_root'] == str(root),
                  'Execution repository differs from proposal')
    _exclusive_json(output / 'execution-claimed.json', {'claimed_at_utc': _now().isoformat()})
    journal = _journal(output)
    try:
        manifest_path = output / 'execution.json'
        frame.require(frame._pin(manifest_path)['sha256'] == expected_manifest_sha256, 'Execution manifest digest mismatch')
        manifest = read_json(manifest_path)
        unsigned = dict(manifest)
        digest = unsigned.pop('manifest_sha256')
        frame.require(fingerprint(unsigned) == digest and manifest['output'] == str(output)
                      and manifest['kind'] == 'prospective_bounded_source_execution'
                      and manifest['source_dispatch_allowed'] is True and manifest['clinical_activation'] is False,
                      'Invalid source execution manifest')
        events = read_chain(output / 'journal.jsonl')
        frame.require(events[-1]['event'] == 'execution_prepared'
                      and events[-1]['details']['manifest'] == frame._pin(manifest_path), 'Unsealed execution preparation')
        frame._check_pin(manifest['policy'])
        frame.require(read_json(Path(manifest['policy']['path'])) == POLICY, 'Effective policy changed')
        for pair in manifest['archives']:
            frame._check_pin(pair['source'])
            frame._check_pin(pair['archive'])
            frame.require(pair['source']['sha256'] == pair['archive']['sha256']
                          and Path(pair['archive']['path']).resolve().is_relative_to(output / 'archive'), 'Archive mismatch')
        frame._check_pin(manifest['bound_request'])
        root = Path(manifest['repo_root']).resolve()
        frame.require(output.is_relative_to(root / frame.OUTPUT_ROOT), 'Execution output escaped')
        contract, _ = _bound(root, Path(manifest['bound_request']['path']))
        frame.require(manifest['contract'] == read_json(Path(manifest['bound_request']['path']))['contract'], 'Execution proposal changed')
        # mkdir is the cross-process, cross-manifest exclusion point before HTTP.
        claim_key = fingerprint({'request': contract['request'], 'protocol': contract['protocol']['sha256'],
                                 'readiness_date_R': contract['readiness_date_R'],
                                 'inventory': read_json(Path(manifest['bound_request']['path']))['inventory']['sha256']})
        claim = root / frame.OUTPUT_ROOT / ('source-claim-' + claim_key)
        claim.mkdir(exist_ok=False)
        _exclusive_json(claim / 'execution.json', {'output': str(output), 'manifest': frame._pin(manifest_path),
                                                  'recovery': POLICY['recovery']})
        if client is None:
            client = StdlibClient()
        else:
            frame.require(getattr(client, 'evidence_kind', None) == 'synthetic', 'Injected client must be synthetic')
        journal.append('execution_started', evidence_kind=client.evidence_kind, global_claim=str(claim),
                       query_semantics='cold_candidate_qualification', clinical_activation=False)
        deadline, budget = time.monotonic() + 600, [20 * 1024 * 1024]
        before = _attempt(journal, output, VERSION_REQUEST, client, 0, deadline, budget)
        version = parse_json((output / before['body']['path']).read_bytes())
        frame.require(isinstance(version, dict) and set(version) == {'apiVersion', 'dataTimestamp'}
                      and all(isinstance(v, str) and v for v in version.values()), 'Unknown version response schema')
        archived_version = read_json(root / (frame.METADATA + '04-version.json'))
        frame.require(version['apiVersion'] == archived_version['apiVersion'], 'API version differs from archived schema')
        pages, ids, tokens, count, token = [], set(), set(), None, None
        while True:
            frame.require(len(pages) < 10, 'Page attempt cap')
            request = frame.page_request(contract, token)
            page = _attempt(journal, output, request, client, len(pages) + 1, deadline, budget)
            pages.append(page)
            count, token = _incremental(contract, parse_json((output / page['body']['path']).read_bytes()), ids, tokens, count)
            if token is None:
                break
        after = _attempt(journal, output, VERSION_REQUEST, client, len(pages) + 1, deadline, budget)
        version_after = parse_json((output / after['body']['path']).read_bytes())
        frame.require(version == version_after, 'Source version/dataTimestamp drift')
        validated = frame.validate_frame(contract, pages, capture_root=output,
                                         version_before=version, version_after=version_after)
        # The old validator computes sample IDs. They are deliberately not persisted
        # or exposed as selected/sealed members by this source-only milestone.
        validated.pop('sample_nct_ids')
        write_json(output / 'quarantined-frame-validation.json', validated)
        receipt = {'status': 'complete_bounded_frame_capture', 'evidence_kind': client.evidence_kind,
                   'frame_count': count, 'study_queries': len(pages), 'version_queries': 2,
                   'version_before': before, 'version_after': after, 'pages': pages,
                   'source_version': version, 'collected_bytes': 20 * 1024 * 1024 - budget[0],
                   'source_coverage': POLICY['source_coverage'], 'atomic_snapshot': False,
                   'query_semantics': 'observed_response_shape_and_enumeration_only',
                   'transport_qualified': client.evidence_kind == 'live_authenticated_tls',
                   'clinical_activation': False, 'selected_members': 0, 'model_calls': 0,
                   'sample_selection_quarantined': True}
        write_json(output / 'receipt.json', receipt)
        journal.append('execution_completed', receipt=frame._pin(output / 'receipt.json'))
        return receipt
    except BaseException as exc:
        journal.fail(exc, 'execute_source_readiness')
        raise
    finally:
        journal.close()


def inspect_execution(output):
    """Read complete or crashed accounting without issuing or authorizing requests."""
    output = Path(output).resolve()
    events = read_chain(output / 'journal.jsonl', allow_incomplete_tail=True)
    started = [e['details']['attempt'] for e in events if e['event'] == 'attempt_started']
    terminal = [e['details']['attempt'] for e in events if e['event'] == 'attempt_terminal']
    return {'last_event': events[-1]['event'], 'attempts_started': started,
            'unresolved_attempts': sorted(set(started) - set(terminal)),
            'receipt_present': (output / 'receipt.json').is_file(), 'recovery': POLICY['recovery']}
