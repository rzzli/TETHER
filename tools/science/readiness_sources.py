"""Fixed-member, evaluator-only registry source packets.

Only execute performs transport. Listing text and PDF bytes remain quarantined
for steward review; neither availability nor document dates qualify clinical rules.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import os
import re
import shutil
import time
from urllib.parse import urlencode

from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import ContractError, fingerprint, parse_json, read_json, write_json
from tools.science import prospective_frame as frame
from tools.science import prospective_transport as transport
from tools.science import prospective_capacity as capacity

PROTOCOL = 'planning/protocols/prospective-readiness-sources-v0.1.json'
MEMBERSHIP_FREEZE = 'planning/review-assets/prospective-endpoint-readiness-20261023/readiness-membership-freeze.json'
SOURCE_DATE_R = '2026-10-24'
CAPS = {'max_members': 12, 'max_listings_per_member': 1, 'max_pdfs_per_member': 2,
        'max_bytes_per_listing': 2 * 1024 * 1024, 'max_bytes_per_pdf': 16 * 1024 * 1024,
        'max_aggregate_source_bytes': 250 * 1024 * 1024,
        'max_aggregate_source_elapsed_seconds': 1800, 'request_timeout_seconds': 40,
        'max_elapsed_seconds_per_request': 120, 'max_total_source_request_attempts': 48,
        'prior_source_request_attempts': 11, 'automatic_retries': 0}
BOUNDARIES = {'role': 'evaluation_only', 'agent_visible': False, 'steward_review': 'pending',
              'clinical_activation': False, 'model_dispatch_allowed': False,
              'outcome_labels': None, 'probabilities': None, 'replacement_allowed': False,
              'source_rule_readiness': 'unknown', 'origin_risk': 'unknown'}
SCOPE = {'source_dispatch_allowed': True, 'clinical_activation': False,
         'model_dispatch_allowed': False, 'outcome_queries': 0,
         'provider_spend_usd': 0, 'replacement_allowed': False}
OBJECT_ARRAYS = {
    'protocolSection.armsInterventionsModule.interventions',
    'protocolSection.armsInterventionsModule.armGroups',
    'protocolSection.outcomesModule.primaryOutcomes',
    'documentSection.largeDocumentModule.largeDocs'}
CODE = (*frame.CODE, Path(transport.__file__).resolve(), Path(capacity.__file__).resolve(), Path(__file__).resolve())
require = frame.require


def _now():
    return datetime.now(timezone.utc)


def _nct(value):
    require(isinstance(value, str) and re.fullmatch(r'NCT[0-9]{8}', value), 'Canonical fixed NCT identity required')
    return value


def listing_request(nct, fields):
    nct = _nct(nct)
    url = f'{frame.ENDPOINT}/{nct}?' + urlencode([('format', 'json'), ('fields', ','.join(fields))])
    return {'method': 'GET', 'url': url, 'kind': 'listing', 'nct_id': nct,
            'authentication': False, 'automatic_retry': False,
            'request_timeout_seconds': 40, 'max_elapsed_seconds': 120,
            'max_response_bytes': CAPS['max_bytes_per_listing']}


def pdf_request(nct, filename):
    nct = _nct(nct)
    require(isinstance(filename, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]*\.pdf', filename),
            'Unsafe registry PDF filename')
    return {'method': 'GET', 'url': f'https://cdn.clinicaltrials.gov/large-docs/{nct[-2:]}/{nct}/{filename}',
            'kind': 'pdf', 'nct_id': nct, 'filename': filename,
            'authentication': False, 'automatic_retry': False,
            'request_timeout_seconds': 40, 'max_elapsed_seconds': 120,
            'max_response_bytes': CAPS['max_bytes_per_pdf']}


def validate_listing(payload, projection):
    """Typed leaf allowlist. Null or omitted leaves remain explicit unknowns."""
    tree = {}
    for specification in projection.values():
        node = tree
        for key in specification['json_path'].split('.'):
            node = node.setdefault(key, {})
        node['$type'] = specification['type']

    def walk(value, schema, path=''):
        if value is None:
            return
        if '$type' in schema:
            kind = schema['$type']
            if kind in ('text[]', 'Phase[]'):
                require(isinstance(value, list) and len(value) <= 1000
                        and all(isinstance(item, str) for item in value), 'Malformed scalar array: ' + path)
                if kind == 'Phase[]':
                    require(set(value) <= {'NA', 'EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4'},
                            'Unknown phase enum: ' + path)
            elif kind == 'boolean':
                require(type(value) is bool, 'Malformed boolean: ' + path)
            elif kind == 'long':
                require(type(value) is int and value > 0, 'Malformed document byte count: ' + path)
            else:
                require(isinstance(value, str), 'Malformed projected text: ' + path)
            return
        if path in OBJECT_ARRAYS:
            require(isinstance(value, list) and len(value) <= 1000, 'Malformed object array: ' + path)
            for item in value:
                require(isinstance(item, dict), 'Malformed object-array item: ' + path)
                walk_object(item, schema, path)
        else:
            walk_object(value, schema, path)

    def walk_object(value, schema, path):
        require(isinstance(value, dict) and set(value) <= set(schema), 'Unrequested or malformed branch: ' + path)
        for key, child in value.items():
            walk(child, schema[key], path + '.' + key if path else key)

    require(isinstance(payload, dict), 'Listing must be an object')
    walk(payload, tree)
    return payload


def _get(payload, path):
    return frame._get(payload, *path.split('.'))


SELECTION = 'all_relevant_unique_originals_up_to_two_no_metadata_authenticity_inference'


def select_documents(payload, nct):
    """Flags and recognized type tokens choose candidates, never scientific truth."""
    docs = _get(payload, 'documentSection.largeDocumentModule.largeDocs')
    if docs is None:
        return {'status': 'not_listed_in_observed_projection', 'selected': [], 'listing': [], 'ambiguities': []}
    refs, seen, ambiguities, candidates = [], {}, [], []
    for index, doc in enumerate(docs):
        filename = doc.get('filename')
        tokens = set(re.split(r'[_+ /-]+', (doc.get('typeAbbrev') or '').casefold()))
        typed_protocol, typed_sap = 'prot' in tokens, 'sap' in tokens
        protocol = doc.get('hasProtocol') is True or typed_protocol
        sap = doc.get('hasSap') is True or typed_sap
        ref = {'index': index, 'filename': filename, 'has_protocol': doc.get('hasProtocol'),
               'has_sap': doc.get('hasSap'), 'has_icf': doc.get('hasIcf'),
               'date': doc.get('date'), 'upload_date': doc.get('uploadDate'),
               'reported_bytes': doc.get('size'), 'label': doc.get('label'),
               'type_abbrev': doc.get('typeAbbrev'), 'classified_protocol': protocol,
               'classified_sap': sap, 'request': None}
        refs.append(ref)
        if filename is not None and filename in seen:
            if seen[filename] != doc:
                ambiguities.append({'index': index, 'reason': 'conflicting_duplicate_filename'})
            continue
        if filename is not None:
            seen[filename] = doc
        if (typed_protocol and doc.get('hasProtocol') is False) or (typed_sap and doc.get('hasSap') is False):
            ambiguities.append({'index': index, 'reason': 'type_flag_conflict'})
        if not (protocol or sap):
            if doc.get('hasProtocol') is None or doc.get('hasSap') is None:
                if not tokens <= {'icf', ''} or 'icf' not in tokens:
                    ambiguities.append({'index': index, 'reason': 'unknown_document_product'})
            continue
        try:
            ref['request'] = pdf_request(nct, filename)
        except ContractError:
            ambiguities.append({'index': index, 'reason': 'missing_or_unsafe_relevant_filename'})
            continue
        candidates.append(ref)
    if len(candidates) > 2:
        ambiguities.append({'reason': 'more_than_two_relevant_unique_originals'})
    selected = [] if ambiguities else sorted(candidates, key=lambda r: (
        0 if r['classified_protocol'] and r['classified_sap'] else 1 if r['classified_protocol'] else 2,
        r['filename']))
    return {'status': 'insufficient_under_cap_or_metadata' if ambiguities else 'candidate_files_selected' if selected
            else 'not_listed_in_observed_projection', 'selected': selected, 'listing': refs,
            'ambiguities': ambiguities, 'authenticity_qualified': False, 'version_applicability_qualified': False}


def _attempt(journal, output, request, client, index, deadline, budget):
    """Bounded durable stream accounting; uses the unchanged TLS worker/client."""
    started, clock = _now(), time.monotonic()
    require(started.date().isoformat() == SOURCE_DATE_R, 'Expired source capture date R')
    require(clock < deadline and budget[0] > 0, 'Global source elapsed/byte cap')
    require(index + CAPS['prior_source_request_attempts'] < CAPS['max_total_source_request_attempts'],
            'Amended package source attempt cap')
    limit = min(deadline, clock + 120)
    path = output / f'{index:02d}-response.bin'
    journal.append('attempt_started', attempt=index, request=request, started_at_utc=started.isoformat())
    response, failure, reason, iterator, seen = None, None, None, None, 0
    fatal = None
    try:
        with path.open('xb') as raw:
            iterator = iter(client.stream(request, deadline=limit))
            for kind, value in iterator:
                require(_now().date() == started.date(), 'Source job crossed UTC date R')
                if time.monotonic() > limit:
                    raise TimeoutError('Hard source request deadline')
                if kind == 'headers':
                    require(response is None and seen == 0 and isinstance(value, dict), 'Invalid headers event')
                    response = {'status': value['status'], 'final_url': value['final_url'],
                                'headers': transport._headers(value['headers'])}
                    journal.append('attempt_response_headers', attempt=index, **response)
                else:
                    require(kind == 'body' and response is not None and isinstance(value, bytes), 'Invalid stream event')
                    seen += len(value)
                    room = max(0, min(request['max_response_bytes'] - raw.tell(), budget[0]))
                    retained = value[:room]
                    raw.write(retained); raw.flush(); os.fsync(raw.fileno())
                    budget[0] -= len(retained)
                    if len(retained) != len(value):
                        reason = 'oversize' if raw.tell() >= request['max_response_bytes'] else 'global_byte_cap'
                        raise OSError('Source byte cap')
            if time.monotonic() > limit:
                raise TimeoutError('Hard source request deadline')
            require(_now().date() == started.date(), 'Source job crossed UTC date R')
            if response is None or response['status'] != 200 or response['final_url'] != request['url']:
                reason = 'http_failure_or_redirect'
                raise OSError('HTTP error or redirect')
            if response['headers'].get('content-encoding', 'identity').lower() != 'identity':
                reason = 'encoded_response'
                raise OSError('Encoded response forbidden')
            length = response['headers'].get('content-length')
            if length is not None and (not length.isdigit() or int(length) != seen):
                reason = 'partial_response'
                raise OSError('Partial response length')
    except BaseException as exc:
        failure = type(exc).__name__
        reason = reason or ('timeout' if isinstance(exc, TimeoutError) else 'access_failed')
        if isinstance(exc, (KeyboardInterrupt, SystemExit, ContractError)) or not isinstance(exc, (OSError, TimeoutError)):
            fatal = exc
    finally:
        if iterator is not None and hasattr(iterator, 'close'):
            try:
                iterator.close()
            except BaseException as exc:
                failure, reason = failure or type(exc).__name__, reason or 'stream_close_failure'
                fatal = exc
        ended = _now()
        receipt = {'attempt': index, 'request': request, 'response': response,
                   'started_at_utc': started.isoformat(), 'ended_at_utc': ended.isoformat(),
                   'elapsed_seconds': time.monotonic() - clock, 'streamed_bytes': seen,
                   'body': frame._pin(path) if path.exists() else None,
                   'outcome': 'failed' if failure else 'received', 'error_class': failure,
                   'hold_reason': reason, 'automatic_retry': False}
        journal.append('attempt_terminal', **receipt)
    if fatal:
        raise fatal
    require(ended.date() == started.date(), 'Source job crossed UTC date R')
    require(time.monotonic() <= deadline, 'Global source elapsed cap')
    if reason == 'global_byte_cap':
        raise ContractError('Global source byte cap')
    return receipt


def _packets(members, origins, projection, fields, attempt, output, packets):
    """Deterministic source plan shared by execution and offline receipt replay."""
    for member, origin in zip(members, origins):
        nct = member['nct_id']
        packet = dict(BOUNDARIES, order=member['order'], nct_id=nct, screen=member['screen'],
                      status='unknown', listing=None, document_selection=None, pdfs=[],
                      source_authenticity='unqualified', version_applicability='unqualified',
                      mandatory_method_fields='unknown', clinical_origin='unknown')
        packets.append(packet)
        listing = attempt(listing_request(nct, fields))
        packet['listing'] = listing
        if listing['outcome'] != 'received':
            packet['status'] = 'access_failed'
            continue
        payload = parse_json(Path(listing['body']['path']).read_bytes())
        validate_listing(payload, projection)
        observed = _get(payload, 'protocolSection.identificationModule.nctId')
        if observed != nct:
            packet['status'] = 'identity_hold'
            packet['identity_observed'] = observed
            continue
        packet['metadata_evaluation_only'] = payload
        previous = _get(origin, 'protocolSection.designModule.phases')
        phases = _get(payload, 'protocolSection.designModule.phases')
        packet['phase_comparison'] = 'unknown' if previous is None or phases is None else (
            'matched' if len(phases) == len(set(phases)) and set(phases) == set(previous) else 'drift_hold')
        if packet['phase_comparison'] == 'drift_hold':
            packet['status'] = 'phase_drift_hold'
            continue
        selection = select_documents(payload, nct)
        packet['document_selection'] = selection
        packet['status'] = selection['status']
        for ref in selection['selected']:
            item = {'listing_reference': ref, 'receipt': None, 'status': 'unknown',
                    'authenticity_qualified': False, 'material_rule_qualification': 'unknown'}
            packet['pdfs'].append(item)
            if ref['reported_bytes'] is not None and ref['reported_bytes'] > CAPS['max_bytes_per_pdf']:
                item['status'] = 'oversize_reported_not_requested'
                continue
            receipt = attempt(ref['request'])
            item['receipt'] = receipt
            if receipt['outcome'] != 'received':
                item['status'] = receipt['hold_reason']
                continue
            raw = Path(receipt['body']['path']).read_bytes()
            signature = raw.startswith(b'%PDF-')
            eof = b'%%EOF' in raw[-1024:]
            size_match = ref['reported_bytes'] is None or len(raw) == ref['reported_bytes']
            item.update(pdf_signature_matches=signature, pdf_eof_marker_present=eof,
                        reported_size_matches=size_match,
                        status='retained_candidate_pending_steward_review' if signature and eof and size_match
                        else 'pdf_qc_hold')
        if selection['selected']:
            packet['status'] = 'partial_source_packet_pending_steward_review'
    return packets


def _checked_pin(root, pin):
    require(isinstance(pin, dict) and set(pin) == {'path', 'sha256', 'bytes'}, 'Invalid proof pin')
    path = Path(pin['path'])
    if not path.is_absolute():
        path = frame._inside(root, pin['path'])
        expected = dict(pin, path=str(path))
    else:
        expected = pin
    require(path.resolve().is_relative_to(root) or path.resolve() in CODE, 'Proof path escaped repository')
    frame._check_pin(expected)
    return frame._pin(path)


def _membership(root, freeze_path):
    freeze = read_json(freeze_path)
    require(freeze['schema_version'] == 1
            and freeze['status'] == 'fixed_twelve_readiness_members_sealed_before_source_rule_queries'
            and freeze['members'] == 12 and freeze['source_rule_queries'] == 0
            and freeze['clinical_activation'] is False and freeze['model_calls'] == 0,
            'Membership freeze boundary differs')
    sources = [_checked_pin(root, freeze[key]) for key in ('membership', 'origin_metadata', 'journal', 'independent_review')]
    membership = read_json(Path(freeze['membership']['path']))
    require(membership['status'] == 'readiness_membership_sealed' and membership['role'] == 'evaluation_only'
            and membership['sampling_seed_sha256'] == capacity.SEED
            and membership['clinical_activation'] is False and membership['model_dispatch_allowed'] is False
            and membership['outcome_labels'] is None and membership['probabilities'] is None
            and membership['tether_cases_created'] == 0 and membership['replacement_allowed'] is False,
            'Fixed membership boundaries differ')
    members = membership['members']
    require(isinstance(members, list) and len(members) == 12
            and [m['order'] for m in members] == list(range(1, 13))
            and len({_nct(m['nct_id']) for m in members}) == 12
            and all(m['screen']['screen'] in ('eligible', 'screen_unknown')
                    and m['screen']['exposure_excluded'] is False for m in members), 'Invalid fixed member order/screen')
    events = read_chain(Path(freeze['journal']['path']))
    require(events[0]['event'] == 'build_reserved' and events[-1]['event'] == 'build_completed'
            and events[-1]['details']['membership'] == freeze['membership']
            and events[-1]['details']['origin_metadata'] == freeze['origin_metadata']
            and events[-1]['details']['source_rule_queries'] == 0, 'Membership sealing journal differs')
    frame_audit_pin = _checked_pin(root, membership['frame_audit'])
    capture_pin = _checked_pin(root, membership['capture_receipt'])
    review_pin = _checked_pin(root, membership['independent_review'])
    require(review_pin == freeze['independent_review'], 'Independent membership review differs')
    audit = read_json(Path(frame_audit_pin['path']))
    prior_manifest = _checked_pin(root, audit['execution_manifest'])
    prior_output = Path(prior_manifest['path']).parent
    require(audit['capture_receipt'] == capture_pin
            and frame._pin(prior_output / 'receipt.json') == capture_pin, 'Prior capture lineage differs')
    replay = capacity.audit_capture(prior_output, expected_manifest_sha256=prior_manifest['sha256'])
    require([m['nct_id'] for m in members] == replay['candidate_nct_ids'], 'Membership differs from original-seed sample')
    receipt = read_json(Path(capture_pin['path']))
    require(receipt['study_queries'] + receipt['version_queries'] == CAPS['prior_source_request_attempts'],
            'Prior source attempt accounting changed')
    origins = read_json(Path(freeze['origin_metadata']['path']))
    require(origins['role'] == 'evaluation_only' and len(origins['records']) == 12, 'Origin metadata scope differs')
    origin_records = []
    for member, origin in zip(members, origins['records']):
        locator = member['source_locator']
        raw_pin = _checked_pin(root, locator['raw_body'])
        match = re.fullmatch(r'/studies/(0|[1-9][0-9]*)', locator['json_pointer'])
        require(match is not None, 'Invalid origin row pointer')
        studies = parse_json(Path(raw_pin['path']).read_bytes())['studies']
        require(int(match[1]) < len(studies), 'Origin row pointer outside original page')
        row = studies[int(match[1])]
        require(fingerprint(row) == locator['row_sha256'] and origin['source_locator'] == locator
                and origin['nct_id'] == member['nct_id'] and origin['record'] == row
                and _get(row, 'protocolSection.identificationModule.nctId') == member['nct_id'], 'Origin row identity/hash differs')
        require(member['screen'] == next(r for r in replay['all_member_ledger'] if r['nct_id'] == member['nct_id']),
                'Fixed screen differs from original frame')
        sources.append(raw_pin)
        origin_records.append(row)
    prior = read_json(Path(prior_manifest['path']))
    sources += [frame_audit_pin, capture_pin, review_pin, prior_manifest,
                _checked_pin(root, audit['capture_journal']), _checked_pin(root, prior['policy']),
                _checked_pin(root, prior['amendment'])]
    for pair in prior['archives']:
        sources += [_checked_pin(root, pair['source']), _checked_pin(root, pair['archive'])]
    for part in [receipt['version_before'], *receipt['pages'], receipt['version_after']]:
        sources.append(frame._pin(frame._inside(prior_output, part['body']['path'])))
    prior_events = read_chain(prior_output / 'journal.jsonl')
    claim = next(e['details']['global_claim'] for e in prior_events if e['event'] == 'execution_started')
    sources.append(_checked_pin(root, frame._pin(Path(claim) / 'execution.json')))
    sources += [frame._pin(freeze_path)]
    return members, origin_records, sources, receipt


def _profile(root, path):
    protocol = read_json(path)
    require(set(protocol) <= {'schema_version', 'protocol_id', 'status', 'created_at_utc',
            'base_protocol', 'membership_freeze', 'caps', 'technical_scope', 'document_selection',
            'rationale', 'disclosures', 'required_validation', 'prior_capture', 'scientific_boundaries'},
            'Unrecognized source protocol override')
    require(protocol['schema_version'] == 1
            and protocol['protocol_id'] == 'prospective-readiness-sources-v0.1'
            and protocol['status'] == 'fixed_member_source_only_authorization'
            and protocol['caps'] == CAPS and protocol['technical_scope'] == SCOPE
            and protocol['document_selection'] == SELECTION, 'Source-only profile changed')
    base = _checked_pin(root, protocol['base_protocol'])
    require(base['sha256'] == capacity.SEED and Path(base['path']) == root / frame.PROTOCOL, 'Original protocol ancestry differs')
    base_protocol = read_json(Path(base['path']))
    fields = base_protocol['request_contract']['exact_post_membership_projection']
    projection = base_protocol['request_contract']['frozen_schema_verified_post_membership_projection']
    require(len(fields) == 23 and list(projection) == fields and all(not v['has_children'] for v in projection.values()),
            'Exact 23-leaf post-membership projection changed')
    # Verify projection against archived provider schema, including scalar types.
    metadata = read_json(root / (frame.METADATA + '02-metadata.json'))
    found = {}
    def walk(value, path=()):
        if isinstance(value, dict):
            current = path + ((value['name'],) if 'name' in value else ())
            if value.get('piece') in fields:
                require(value['piece'] not in found, 'Duplicate post-membership schema piece')
                found[value['piece']] = {'json_path': '.'.join(current), 'type': value.get('type'),
                                         'has_children': bool(value.get('children'))}
            for child in value.values():
                if isinstance(child, (dict, list)): walk(child, current)
        elif isinstance(value, list):
            for child in value: walk(child, path)
    walk(metadata)
    require(found == projection, 'Archived post-membership types/paths differ')
    freeze = _checked_pin(root, protocol['membership_freeze'])
    require(Path(freeze['path']) == root / MEMBERSHIP_FREEZE, 'Membership freeze path changed')
    members, origins, sources, prior = _membership(root, Path(freeze['path']))
    if 'prior_capture' in protocol:
        require(_checked_pin(root, protocol['prior_capture'])['sha256'] ==
                read_json(Path(read_json(Path(freeze['path']))['membership']['path']))['capture_receipt']['sha256'],
                'Prior capture pin differs')
    sources += [base, freeze, frame._pin(path), *[frame._pin(p) for p in frame.CODE],
                frame._pin(Path(transport.__file__)), frame._pin(Path(capacity.__file__)), frame._pin(Path(__file__))]
    for pin in sources:
        frame._check_pin(pin)
    return {'protocol': protocol, 'members': members, 'origins': origins, 'fields': fields,
            'projection': projection, 'sources': {p['path']: p for p in sources}, 'prior': prior}


def _output(root, output):
    path = Path(output)
    require('..' not in path.parts, 'Output traversal forbidden')
    path = path.resolve()
    allowed = (root / frame.OUTPUT_ROOT).resolve()
    require(allowed.is_relative_to(root) and path.is_relative_to(allowed) and path != allowed, 'Source output escaped')
    return path


def _policy():
    return {'caps': CAPS, 'scope': SCOPE, 'boundaries': BOUNDARIES, 'document_selection': SELECTION,
            'recovery': 'inspect retained source packets only; never redispatch this fixed-member source job'}


def prepare_execution(repo_root, output, *, expected_protocol_sha256, protocol_path=PROTOCOL):
    root = Path(repo_root).resolve()
    output = _output(root, output)
    journal = RunJournal(output)
    try:
        path = frame._inside(root, protocol_path)
        require(frame._pin(path)['sha256'] == expected_protocol_sha256, 'Source protocol digest mismatch')
        context = _profile(root, path)
        (output / 'archive').mkdir()
        archives = []
        for index, pin in enumerate(context['sources'].values()):
            target = output / 'archive' / f'{index:03d}-{Path(pin["path"]).name}'
            shutil.copyfile(pin['path'], target)
            require(frame._pin(target)['sha256'] == pin['sha256'], 'Source changed during archive')
            archives.append({'source': pin, 'archive': frame._pin(target)})
        write_json(output / 'effective-policy.json', _policy())
        manifest = {'schema_version': 1, 'kind': 'fixed_member_readiness_source_execution',
                    'repo_root': str(root), 'output': str(output), 'prepared_at_utc': _now().isoformat(),
                    'protocol': frame._pin(path), 'policy': frame._pin(output / 'effective-policy.json'),
                    'archives': archives, 'members': [m['nct_id'] for m in context['members']],
                    'listing_requests': [listing_request(m['nct_id'], context['fields']) for m in context['members']],
                    'boundaries': BOUNDARIES, 'prior_source_attempts': CAPS['prior_source_request_attempts'],
                    'prior_source_bytes': context['prior']['collected_bytes']}
        manifest['manifest_sha256'] = fingerprint(manifest)
        write_json(output / 'execution.json', manifest)
        journal.append('execution_prepared', manifest=frame._pin(output / 'execution.json'), network_requests=0)
        return manifest
    except BaseException as exc:
        journal.fail(exc, 'prepare_readiness_sources')
        raise
    finally:
        journal.close()


def _preflight(output, expected):
    output = Path(output)
    require('..' not in output.parts, 'Execution traversal forbidden')
    output = output.resolve()
    path = output / 'execution.json'
    require(frame._pin(path)['sha256'] == expected, 'Source manifest digest mismatch')
    manifest = read_json(path)
    unsigned = dict(manifest)
    digest = unsigned.pop('manifest_sha256')
    root = Path(manifest['repo_root']).resolve()
    require(_output(root, output) == output and manifest['output'] == str(output)
            and manifest['kind'] == 'fixed_member_readiness_source_execution'
            and manifest['schema_version'] == 1 and fingerprint(unsigned) == digest
            and manifest['boundaries'] == BOUNDARIES, 'Source execution commitment differs')
    protocol_pin = _checked_pin(root, manifest['protocol'])
    context = _profile(root, Path(protocol_pin['path']))
    require(manifest['members'] == [m['nct_id'] for m in context['members']]
            and manifest['listing_requests'] == [listing_request(m['nct_id'], context['fields']) for m in context['members']]
            and manifest['prior_source_attempts'] == CAPS['prior_source_request_attempts']
            and manifest['prior_source_bytes'] == context['prior']['collected_bytes'], 'Fixed source products differ')
    require(manifest['policy'] == frame._pin(output / 'effective-policy.json')
            and read_json(output / 'effective-policy.json') == _policy(), 'Effective source policy changed')
    require(len(manifest['archives']) == len(context['sources'])
            and {pair['source']['path']: pair['source'] for pair in manifest['archives']} == context['sources'],
            'Required source archive inventory incomplete')
    archived = set()
    for pair in manifest['archives']:
        frame._check_pin(pair['source']); frame._check_pin(pair['archive'])
        target = Path(pair['archive']['path']).resolve()
        require(target.is_relative_to(output / 'archive') and target not in archived
                and pair['archive']['sha256'] == pair['source']['sha256'], 'Source archive mismatch')
        archived.add(target)
    events = read_chain(output / 'journal.jsonl')
    require(len(events) >= 2 and events[0]['event'] == 'run_reserved' and events[1]['event'] == 'execution_prepared'
            and events[1]['details']['manifest'] == frame._pin(path), 'Unsealed source preparation')
    return output, manifest, context, events


def _claim(root, manifest, context):
    semantic = {'protocol_id': context['protocol']['protocol_id'], 'base_protocol': capacity.SEED,
                'caps': CAPS, 'selection': SELECTION, 'listing_requests': manifest['listing_requests'],
                'members': [{'order': m['order'], 'nct_id': m['nct_id'], 'source_locator': m['source_locator']}
                            for m in context['members']]}
    return root / frame.OUTPUT_ROOT / ('readiness-sources-claim-' + fingerprint(semantic))


def execute(output, *, expected_manifest_sha256, client=None):
    output, manifest, context, events = _preflight(output, expected_manifest_sha256)
    require(events[-1]['event'] == 'execution_prepared', 'Source job already attempted')
    require(_now().date().isoformat() == SOURCE_DATE_R, 'Expired source capture date R')
    transport._exclusive_json(output / 'execution-claimed.json', {'claimed_at_utc': _now().isoformat()})
    journal = transport._journal(output)
    packets, receipts = [], []
    started = time.monotonic()
    job_started_at_utc = _now().isoformat()
    budget = [CAPS['max_aggregate_source_bytes'] - manifest['prior_source_bytes']]
    try:
        claim = _claim(Path(manifest['repo_root']), manifest, context)
        claim.mkdir(exist_ok=False)
        transport._exclusive_json(claim / 'execution.json', {'output': str(output), 'manifest': frame._pin(output / 'execution.json')})
        if client is None:
            client = transport.StdlibClient()
        else:
            require(getattr(client, 'evidence_kind', None) == 'synthetic', 'Injected source client must be synthetic')
        journal.append('execution_started', global_claim=str(claim), evidence_kind=client.evidence_kind,
                       active_job_started_at_utc=job_started_at_utc, boundaries=BOUNDARIES)
        deadline = started + CAPS['max_aggregate_source_elapsed_seconds']
        def attempt(request):
            receipt = _attempt(journal, output, request, client, len(receipts), deadline, budget)
            receipts.append(receipt)
            return receipt
        _packets(context['members'], context['origins'], context['projection'], context['fields'], attempt, output, packets)
        require(time.monotonic() <= deadline, 'Global source elapsed cap')
        require(_now().date().isoformat() == SOURCE_DATE_R, 'Source job crossed UTC date R')
        result = {'schema_version': 1, 'status': 'fixed_member_source_packets_retained',
                  'boundaries': BOUNDARIES, 'evidence_kind': client.evidence_kind,
                  'transport_qualified': client.evidence_kind == 'live_authenticated_tls',
                  'packets': packets, 'source_attempts': len(receipts),
                  'prior_source_attempts': manifest['prior_source_attempts'],
                  'amended_package_source_attempts': len(receipts) + manifest['prior_source_attempts'],
                  'retained_bytes': CAPS['max_aggregate_source_bytes'] - manifest['prior_source_bytes'] - budget[0],
                  'amended_package_bytes': CAPS['max_aggregate_source_bytes'] - budget[0],
                  'active_job_started_at_utc': job_started_at_utc,
                  'active_job_ended_at_utc': _now().isoformat(),
                  'active_job_elapsed_seconds': time.monotonic() - started,
                  'prior_capture_elapsed_seconds': (frame._time(context['prior']['version_after']['ended_at_utc'])
                      - frame._time(context['prior']['version_before']['started_at_utc'])).total_seconds(),
                  'source_search_queries': 0,
                  'followup_queries': 0, 'version_metadata_queries': 0,
                  'clinical_labels_created': 0, 'model_calls': 0, 'provider_spend_usd': 0}
        write_json(output / 'packets.json', result)
        journal.append('execution_completed', packets=frame._pin(output / 'packets.json'))
        return result
    except BaseException as exc:
        if packets:
            packets[-1]['status'] = 'global_integrity_or_interruption_hold'
        partial = {'status': 'stopped_fixed_member_source_job', 'boundaries': BOUNDARIES,
                   'packets': packets, 'unattempted_members': manifest['members'][len(packets):],
                   'source_rule_readiness': 'unknown'}
        write_json(output / 'partial-packets.json', partial)
        journal.append('packets_stopped', partial=frame._pin(output / 'partial-packets.json'))
        journal.fail(exc, 'execute_readiness_sources')
        raise
    finally:
        journal.close()


def inspect_execution(output):
    output = Path(output).resolve()
    events = read_chain(output / 'journal.jsonl', allow_incomplete_tail=True)
    starts = [e['details']['attempt'] for e in events if e['event'] == 'attempt_started']
    ends = [e['details']['attempt'] for e in events if e['event'] == 'attempt_terminal']
    return {'last_event': events[-1]['event'], 'attempts_started': starts,
            'unresolved_attempts': sorted(set(starts) - set(ends)),
            'complete_packets_present': (output / 'packets.json').is_file(),
            'partial_packets_present': (output / 'partial-packets.json').is_file(),
            'recovery': _policy()['recovery']}


def audit_packets(output, *, expected_manifest_sha256):
    """Offline original-response replay, including failed case-level attempts."""
    output, manifest, context, events = _preflight(output, expected_manifest_sha256)
    require(events[-1]['event'] == 'execution_completed'
            and events[-1]['details']['packets'] == frame._pin(output / 'packets.json'), 'Source job not sealed complete')
    result = read_json(output / 'packets.json')
    require(result['schema_version'] == 1 and result['status'] == 'fixed_member_source_packets_retained'
            and result['boundaries'] == BOUNDARIES and result['evidence_kind'] in ('synthetic', 'live_authenticated_tls')
            and result['transport_qualified'] == (result['evidence_kind'] == 'live_authenticated_tls')
            and all(result[key] == 0 for key in ('source_search_queries', 'followup_queries',
                'version_metadata_queries', 'clinical_labels_created', 'model_calls', 'provider_spend_usd')),
            'Source packet scientific boundary changed')
    require(len(events) >= 4 and events[2]['event'] == 'execution_started'
            and events[2]['details']['boundaries'] == BOUNDARIES
            and events[2]['details']['evidence_kind'] == result['evidence_kind'], 'Source execution start differs')
    require(events[2]['details']['active_job_started_at_utc'] == result['active_job_started_at_utc'],
            'Active job start differs')
    job_start, job_end = frame._time(result['active_job_started_at_utc']), frame._time(result['active_job_ended_at_utc'])
    require(job_start.date().isoformat() == job_end.date().isoformat() == SOURCE_DATE_R
            and frame._time(manifest['prepared_at_utc']) <= job_start <= job_end
            and (job_end - job_start).total_seconds() <= 1800, 'Source job wall timing differs')
    claim = _claim(Path(manifest['repo_root']), manifest, context)
    require(events[2]['details']['global_claim'] == str(claim)
            and read_json(claim / 'execution.json') == {'output': str(output), 'manifest': frame._pin(output / 'execution.json')},
            'Source semantic claim differs')
    # Parse the entire event grammar rather than ignoring unrecognized attempts.
    cursor, attempts = 3, []
    while cursor < len(events) - 1:
        require(events[cursor]['event'] == 'attempt_started', 'Source attempt event ordering differs')
        begin = events[cursor]['details']; cursor += 1
        head = None
        if cursor < len(events) - 1 and events[cursor]['event'] == 'attempt_response_headers':
            head = events[cursor]['details']; cursor += 1
        require(cursor < len(events) - 1 and events[cursor]['event'] == 'attempt_terminal',
                'Unresolved source attempt')
        terminal = events[cursor]['details']; cursor += 1
        attempts.append((begin, head, terminal))
    require(len(attempts) <= 36 and len(attempts) + CAPS['prior_source_request_attempts'] <= 48,
            'Source attempt cap')
    replay_packets, position, total, first, previous, elapsed_sum = [], 0, 0, None, None, 0

    def replay(request):
        nonlocal position, total, first, previous, elapsed_sum
        require(position < len(attempts), 'Missing planned source attempt')
        begin, head, receipt = attempts[position]
        require(begin['attempt'] == receipt['attempt'] == position and begin['request'] == receipt['request'] == request
                and receipt['automatic_retry'] is False, 'Exact source request/attempt differs')
        require(set(receipt) == {'attempt', 'request', 'response', 'started_at_utc', 'ended_at_utc',
                'elapsed_seconds', 'streamed_bytes', 'body', 'outcome', 'error_class', 'hold_reason', 'automatic_retry'},
                'Unknown source terminal fields')
        start, finish = frame._time(receipt['started_at_utc']), frame._time(receipt['ended_at_utc'])
        require(begin['started_at_utc'] == receipt['started_at_utc']
                and start.date().isoformat() == finish.date().isoformat() == SOURCE_DATE_R
                and start >= frame._time(manifest['prepared_at_utc']) and start <= finish
                and job_start <= start <= finish <= job_end
                and (previous is None or start >= previous)
                and type(receipt['elapsed_seconds']) in (int, float) and receipt['elapsed_seconds'] >= 0,
                'Source attempt timing differs')
        elapsed_sum += receipt['elapsed_seconds']
        first, previous = first or start, finish
        require((finish - first).total_seconds() <= 1800, 'Active source job elapsed cap')
        pin = receipt['body']
        require(pin is not None and Path(pin['path']).resolve() == output / f'{position:02d}-response.bin',
                'Source raw body lineage differs')
        frame._check_pin(pin)
        require(type(receipt['streamed_bytes']) is int and receipt['streamed_bytes'] >= pin['bytes']
                and 0 <= pin['bytes'] <= request['max_response_bytes'], 'Source retained byte accounting differs')
        response = receipt['response']
        require((head is None) == (response is None), 'Source headers evidence mismatch')
        if head is not None:
            require(head['attempt'] == position and response == {k: head[k] for k in ('status', 'final_url', 'headers')},
                    'Source response header lineage differs')
        if receipt['outcome'] == 'received':
            require(receipt['error_class'] is None and receipt['hold_reason'] is None
                    and response is not None and response['status'] == 200 and response['final_url'] == request['url']
                    and response['headers'].get('content-encoding', 'identity').lower() == 'identity'
                    and pin['bytes'] == receipt['streamed_bytes']
                    and receipt['elapsed_seconds'] <= 120 and (finish - start).total_seconds() <= 120,
                    'Successful source receipt differs')
            length = response['headers'].get('content-length')
            require(length is None or length.isdigit() and int(length) == pin['bytes'], 'Partial source body')
        else:
            require(receipt['outcome'] == 'failed' and isinstance(receipt['error_class'], str)
                    and receipt['hold_reason'] in ('oversize', 'timeout', 'access_failed', 'http_failure_or_redirect',
                                                  'encoded_response', 'partial_response'), 'Unknown case failure state')
            if receipt['hold_reason'] == 'oversize':
                require(pin['bytes'] == request['max_response_bytes'] and receipt['streamed_bytes'] > pin['bytes'],
                        'Oversize receipt does not exceed request cap')
            elif receipt['hold_reason'] == 'http_failure_or_redirect':
                require(receipt['error_class'] == 'OSError' and (response is None or response['status'] != 200
                        or response['final_url'] != request['url']), 'HTTP failure contradicts observed response')
            elif receipt['hold_reason'] == 'encoded_response':
                require(receipt['error_class'] == 'OSError' and response is not None
                        and response['headers'].get('content-encoding', 'identity').lower() != 'identity',
                        'Encoding hold contradicts observed headers')
            elif receipt['hold_reason'] == 'partial_response':
                length = response['headers'].get('content-length') if response else None
                require(receipt['error_class'] == 'OSError' and length is not None
                        and (not length.isdigit() or int(length) != receipt['streamed_bytes']),
                        'Partial-response hold contradicts observed length')
            elif receipt['hold_reason'] == 'timeout':
                require(receipt['error_class'] == 'TimeoutError', 'Timeout hold lacks timeout event')
            else:
                require(receipt['error_class'] in ('OSError', 'ConnectionError', 'ConnectionAbortedError',
                        'ConnectionRefusedError', 'ConnectionResetError', 'BrokenPipeError', 'URLError',
                        'SSLError', 'SSLCertVerificationError', 'gaierror'), 'Unknown source access failure class')
        total += pin['bytes']
        require(total + manifest['prior_source_bytes'] <= CAPS['max_aggregate_source_bytes'], 'Aggregate source byte cap')
        position += 1
        return dict(receipt)

    _packets(context['members'], context['origins'], context['projection'], context['fields'], replay, output, replay_packets)
    require(position == len(attempts) and result['packets'] == replay_packets, 'Source packets differ from raw deterministic replay')
    require(result['source_attempts'] == position and result['prior_source_attempts'] == CAPS['prior_source_request_attempts']
            and result['amended_package_source_attempts'] == position + CAPS['prior_source_request_attempts']
            and result['retained_bytes'] == total and result['amended_package_bytes'] == total + manifest['prior_source_bytes']
            and 0 <= result['active_job_elapsed_seconds'] <= 1800
            and result['active_job_elapsed_seconds'] + 0.1 >= elapsed_sum
            and result['active_job_elapsed_seconds'] + 1 >= (job_end - job_start).total_seconds()
            and result['prior_capture_elapsed_seconds'] == (frame._time(context['prior']['version_after']['ended_at_utc'])
                - frame._time(context['prior']['version_before']['started_at_utc'])).total_seconds(),
            'Source job aggregate accounting differs')
    return {'status': 'offline_source_packets_replayed', 'members': manifest['members'],
            'source_attempts': position, 'retained_bytes': total, 'packet_states': [p['status'] for p in replay_packets],
            'boundaries': BOUNDARIES, 'evidence_kind': result['evidence_kind'],
            'transport_qualified': result['transport_qualified'], 'scientific_readiness': 'unknown'}
