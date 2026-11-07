"""Non-dispatch registry frame contracts and offline original-response validation.

No HTTP client lives here. Schema-derived requests remain transport-unqualified;
offline fixtures cannot establish live query acceptance or scientific readiness.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timedelta, timezone
import hashlib
from pathlib import Path
import re
from urllib.parse import urlencode

from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import ContractError, fingerprint, parse_json, read_json, sha256_file, write_json


ENDPOINT = 'https://clinicaltrials.gov/api/v2/studies'
PROTOCOL = 'planning/protocols/prospective-endpoint-readiness-v0.1.json'
METADATA = 'data/benchmark/labels/prospective-endpoint-readiness-20261023/metadata-v1/'
OUTPUT_ROOT = 'data/benchmark/labels/prospective-endpoint-readiness-20261023'
FIELDS = ('NCTId', 'StudyFirstPostDate', 'StudyFirstPostDateType',
          'LastUpdatePostDate', 'LastUpdatePostDateType', 'StudyType', 'Phase',
          'DesignPrimaryPurpose', 'InterventionType')
CAPS = {'frame_max_records': 500, 'page_size': 100, 'max_page_attempts': 10,
        'max_bytes_per_page': 2 * 1024 * 1024, 'max_frame_bytes': 20 * 1024 * 1024,
        'max_frame_elapsed_seconds': 600, 'attempts_per_exact_request': 1,
        'automatic_retries': 0, 'request_timeout_seconds': 40,
        'max_elapsed_seconds_per_request': 120}
CODE = (Path(__file__).resolve(), Path(RunJournal.__init__.__code__.co_filename).resolve(),
        Path(parse_json.__code__.co_filename).resolve())


def require(condition, message):
    if not condition:
        raise ContractError(message)


def _utc_now():
    return datetime.now(timezone.utc)


def _day(value):
    require(isinstance(value, str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}', value),
            'Exact ISO calendar date required')
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ContractError('Invalid calendar date') from exc


def _time(value):
    require(isinstance(value, str), 'UTC timestamp required')
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ContractError('Invalid UTC timestamp') from exc
    require(result.utcoffset() == timedelta(0), 'Timestamp must be UTC')
    return result


def _inside(root, relative, *, file=True):
    require(isinstance(relative, str) and relative and not Path(relative).is_absolute()
            and '..' not in Path(relative).parts and '\\' not in relative,
            'Only contained relative paths permitted')
    result = (root / relative).resolve()
    require(result.is_relative_to(root.resolve()) and (not file or result.is_file()),
            'Missing or escaped source path')
    return result


def _pin(path):
    return {'path': str(path.resolve()), 'sha256': sha256_file(path),
            'bytes': path.stat().st_size}


def _check_pin(pin):
    require(isinstance(pin, Mapping) and set(pin) == {'path', 'sha256', 'bytes'}, 'Invalid source pin')
    p = Path(pin['path'])
    require(p.is_file() and p.stat().st_size == pin['bytes'] and sha256_file(p) == pin['sha256'],
            'Pinned source or code changed')


def _projection(metadata):
    found = {}

    def walk(value, path=()):
        if isinstance(value, dict):
            current = path + ((value['name'],) if 'name' in value else ())
            if value.get('piece') in FIELDS:
                require(value['piece'] not in found, 'Duplicate metadata piece')
                require(not value.get('children'), 'Frame projection must use leaf fields')
                found[value['piece']] = {'json_path': '.'.join(current),
                                         'type': value.get('type'), 'has_children': False}
            for child in value.values():
                if isinstance(child, (dict, list)):
                    walk(child, current)
        elif isinstance(value, list):
            for child in value:
                walk(child, path)
    walk(metadata)
    require(set(found) == set(FIELDS), 'Archived schema lacks exact nine frame fields')
    return {key: found[key] for key in FIELDS}


def _request(start, end, token=None):
    require(token is None or isinstance(token, str) and 0 < len(token) <= 2048
            and not any(ord(c) < 32 or ord(c) == 127 for c in token), 'Invalid opaque page token')
    parameters = [('format', 'json'),
                  ('filter.advanced', f'AREA[StudyFirstPostDate]RANGE[{start},{end}]'),
                  ('fields', ','.join(FIELDS)), ('sort', 'StudyFirstPostDate:asc'),
                  ('countTotal', 'true'), ('pageSize', '100')]
    if token is not None:
        parameters.append(('pageToken', token))
    return {'method': 'GET', 'endpoint': ENDPOINT, 'parameters': dict(parameters),
            'url': ENDPOINT + '?' + urlencode(parameters), 'automatic_retry': False,
            'authentication': False, 'transport_qualified': False,
            'request_timeout_seconds': CAPS['request_timeout_seconds'],
            'max_elapsed_seconds': CAPS['max_elapsed_seconds_per_request'],
            'max_response_bytes': CAPS['max_bytes_per_page']}


def build_frame(repo_root, output, *, expected_protocol_sha256, readiness_date,
                interval_start, interval_end, extra_exposed_ids=(), acceptance_pin=None):
    """Reserve a fresh non-dispatch proposal using the actual UTC build day as R.

    The caller freezes exact dates, never an inferred clinical origin. Extra known
    exposures may be sealed now, but no completeness claim is made for inventory.
    """
    root = Path(repo_root).resolve()
    destination = Path(output)
    require('..' not in destination.parts, 'Output traversal forbidden')
    destination = destination.resolve()
    allowed = (root / OUTPUT_ROOT).resolve()
    require(allowed.is_relative_to(root) and destination.is_relative_to(allowed) and destination != allowed,
            'Output must be a fresh child of readiness evidence root')
    journal = RunJournal(destination, kind='build')
    try:
        protocol_path = _inside(root, PROTOCOL)
        require(sha256_file(protocol_path) == expected_protocol_sha256, 'Protocol digest mismatch')
        p = read_json(protocol_path)
        require(p['protocol_id'] == 'prospective-endpoint-readiness-v0.1'
                and p['status'] == 'proposed_non_dispatch_design', 'Wrong non-dispatch protocol')
        require(all(p['permissions'].get(k) is False for k in
                    ('source_dispatch_allowed', 'membership_acquisition_allowed',
                     'clinical_activation', 'model_dispatch_allowed', 'followup_allowed')),
                'Protocol permissions changed')
        require(all(p['caps'].get(k) == v for k, v in CAPS.items()), 'Protocol caps changed')
        require(p['frame']['sample_max_records'] == 12, 'Sample cap changed')
        now = _utc_now()
        r, start, end = map(_day, (readiness_date, interval_start, interval_end))
        require(r == now.date() and end < r and (end - start).days == 29,
                'Freeze thirty dates ending before actual builder UTC day R')
        parents = []
        parent_names = set()
        for parent in p['parents']:
            source = _inside(root, parent['path'])
            require(parent['path'] not in parent_names, 'Duplicate protocol parent')
            parent_names.add(parent['path'])
            require(sha256_file(source) == parent['sha256'], 'Protocol parent changed')
            parents.append(_pin(source))
        required = {METADATA + n for n in ('01-openapi.yaml', '02-metadata.json',
                                          '03-search-areas.json', '04-version.json')}
        require(required <= parent_names, 'Archived metadata parents missing')
        projection = _projection(read_json(_inside(root, METADATA + '02-metadata.json')))
        require(list(p['request_contract']['exact_projection']) == list(FIELDS)
                and projection == p['request_contract']['frozen_schema_verified_frame_projection'],
                'Protocol and archived projection differ')
        oas = _inside(root, METADATA + '01-openapi.yaml').read_text(encoding='utf-8')
        require(all(f'      - name: "{key}"' in oas for key in
                    ('fields', 'filter.advanced', 'sort', 'pageSize', 'countTotal', 'pageToken'))
                and 'only date and numeric fields' in oas, 'Archived query documentation changed')
        exposed = list(p['frame']['exposure_policy']['exclude_known_ids']) + list(extra_exposed_ids)
        require(all(isinstance(n, str) and re.fullmatch(r'NCT[0-9]{8}', n) for n in exposed),
                'Invalid exposure identity')
        if acceptance_pin is not None:
            _check_pin(acceptance_pin)
            require(Path(acceptance_pin['path']).resolve().is_relative_to(root), 'Acceptance outside root')
        contract = {'schema_version': 1, 'kind': 'prospective_frame_non_dispatch',
                    'repo_root': str(root), 'build_output': str(destination),
                    'protocol': _pin(protocol_path), 'parents': parents,
                    'code_pins': [_pin(path) for path in CODE], 'acceptance_pin': acceptance_pin,
                    'built_at_utc': now.isoformat(), 'readiness_date_R': readiness_date,
                    'interval_start': interval_start, 'interval_end': interval_end,
                    'clinical_origin_F': None, 'capture_started_at_utc': None,
                    'capture_ended_at_utc': None, 'projection': projection, 'caps': dict(CAPS),
                    'sample_max_records': 12, 'exposed_ids': sorted(set(exposed)),
                    'exposure_inventory_complete': False, 'transport_qualified': False,
                    'source_dispatch_allowed': False, 'clinical_activation': False,
                    'query_grammar_status': 'schema_candidate_not_live_qualified',
                    'query_uncertainty': 'Archived OpenAPI documents Essie filters and date RANGE examples; '
                    'this exact StudyFirstPostDate expression, closed boundaries, leaf projection and '
                    'pagination consistency have not been accepted by a live study endpoint.',
                    'source_coverage_limit': 'Only query-returned dated records; no atomic snapshot '
                    'or missing-date population completeness claim.', 'request': _request(interval_start, interval_end)}
        contract['contract_sha256'] = fingerprint(contract)
        write_json(destination / 'request.json', contract['request'])
        write_json(destination / 'contract.json', contract)
        journal.append('build_completed', contract=_pin(destination / 'contract.json'),
                       request=_pin(destination / 'request.json'), network_requests=0)
        return contract
    except BaseException as exc:
        journal.fail(exc, 'non_dispatch_request_build')
        raise
    finally:
        journal.close()


def validate_contract(contract):
    require(isinstance(contract, dict), 'Contract mapping required')
    unsigned = dict(contract)
    digest = unsigned.pop('contract_sha256', None)
    require(fingerprint(unsigned) == digest, 'Contract commitment changed')
    build_output = Path(contract['build_output']).resolve()
    require(build_output.is_relative_to(Path(contract['repo_root']).resolve() / OUTPUT_ROOT),
            'Build output escaped')
    events = read_chain(build_output / 'journal.jsonl')
    require(events[0]['event'] == 'build_reserved' and events[-1]['event'] == 'build_completed',
            'Unsealed build contract')
    require(events[-1]['details']['contract'] == _pin(build_output / 'contract.json')
            and read_json(build_output / 'contract.json') == contract,
            'Contract differs from reserved build')
    require(contract['kind'] == 'prospective_frame_non_dispatch'
            and contract['transport_qualified'] is False
            and contract['source_dispatch_allowed'] is False
            and contract['clinical_activation'] is False
            and contract['clinical_origin_F'] is None
            and contract['capture_started_at_utc'] is None
            and contract['capture_ended_at_utc'] is None, 'Non-dispatch boundary changed')
    root = Path(contract['repo_root']).resolve()
    require(Path(contract['protocol']['path']).resolve() == _inside(root, PROTOCOL), 'Protocol path changed')
    _check_pin(contract['protocol'])
    protocol = read_json(root / PROTOCOL)
    expected_parents = [_pin(_inside(root, p['path'])) for p in protocol['parents']]
    require(contract['parents'] == expected_parents
            and all(p['sha256'] == v['sha256'] for p, v in zip(protocol['parents'], expected_parents)),
            'Parent ancestry changed')
    require(contract['code_pins'] == [_pin(path) for path in CODE], 'Code ancestry changed')
    if contract['acceptance_pin'] is not None:
        _check_pin(contract['acceptance_pin'])
        require(Path(contract['acceptance_pin']['path']).resolve().is_relative_to(root), 'Acceptance path changed')
    projection = _projection(read_json(root / (METADATA + '02-metadata.json')))
    require(contract['projection'] == projection
            == protocol['request_contract']['frozen_schema_verified_frame_projection'], 'Schema changed')
    require(contract['caps'] == CAPS and contract['sample_max_records'] == 12, 'Budget changed')
    r, start, end = map(_day, (contract['readiness_date_R'], contract['interval_start'], contract['interval_end']))
    require(_time(contract['built_at_utc']).date() == r and end < r and (end - start).days == 29,
            'Frozen dates changed')
    require(contract['request'] == _request(contract['interval_start'], contract['interval_end']),
            'Exact request changed')
    require(set(protocol['frame']['exposure_policy']['exclude_known_ids']) <= set(contract['exposed_ids'])
            and contract['exposed_ids'] == sorted(set(contract['exposed_ids']))
            and all(isinstance(n, str) and re.fullmatch(r'NCT[0-9]{8}', n) for n in contract['exposed_ids'])
            and contract['exposure_inventory_complete'] is False, 'Exposure boundary changed')
    return contract


def page_request(contract, token=None):
    """Build bytes-identical parameters except an encoded opaque next-page token."""
    validate_contract(contract)
    return _request(contract['interval_start'], contract['interval_end'], token)


def verify_build(output):
    """Check reserved artifact bytes and hash-chain without asserting dispatch readiness."""
    output = Path(output).resolve()
    events = read_chain(output / 'journal.jsonl')
    require(events[0]['event'] == 'build_reserved' and events[-1]['event'] == 'build_completed',
            'Build not sealed complete')
    for name in ('contract', 'request'):
        pin = events[-1]['details'][name]
        require(Path(pin['path']).resolve() == output / (name + '.json'), 'Build artifact escaped')
        _check_pin(pin)
    contract = validate_contract(read_json(output / 'contract.json'))
    require(read_json(output / 'request.json') == contract['request'], 'Request artifact changed')
    return contract


def _tree(projection):
    result = {}
    for field in projection.values():
        node = result
        for key in field['json_path'].split('.'):
            node = node.setdefault(key, {})
    return result


def _guard(value, tree, path='study'):
    """Reject every unprojected key; missing allowed leaves remain explicit unknowns."""
    if isinstance(value, list):
        require(len(value) <= 100 and path in {
            'study.protocolSection.designModule.phases',
            'study.protocolSection.armsInterventionsModule.interventions'},
            'Quarantine: array outside archived array path')
        if path.endswith('.phases'):
            require(all(item is None or isinstance(item, str) and len(item) <= 128 for item in value),
                    'Quarantine: phase array scalar shape')
        else:
            for item in value:
                require(isinstance(item, dict), 'Quarantine: intervention array object shape')
                _guard(item, tree, path + '[]')
    elif tree:
        require(isinstance(value, dict) and set(value) <= set(tree),
                'Quarantine: prohibited or malformed response branch ' + path)
        for key, child in value.items():
            if child is not None:
                _guard(child, tree[key], path + '.' + key)
    else:
        require(value is None or isinstance(value, str) and len(value) <= 128,
                'Quarantine: invalid projected scalar ' + path)


def _get(record, *keys):
    value = record
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _screen(record):
    design = record.get('protocolSection', {}).get('designModule') or {}
    missing, failures = [], []
    for key, actual, expected, valid in (
        ('study_type', design.get('studyType'), 'INTERVENTIONAL',
         {'INTERVENTIONAL', 'OBSERVATIONAL', 'EXPANDED_ACCESS'}),
        ('primary_purpose', _get(design, 'designInfo', 'primaryPurpose'), 'TREATMENT',
         {'TREATMENT', 'PREVENTION', 'DIAGNOSTIC', 'ECT', 'SUPPORTIVE_CARE', 'SCREENING',
          'HEALTH_SERVICES_RESEARCH', 'BASIC_SCIENCE', 'DEVICE_FEASIBILITY', 'OTHER'})):
        if actual not in valid:
            missing.append(key)
        elif actual != expected:
            failures.append(key)
    phases = design.get('phases')
    if not phases or not isinstance(phases, list) or len(phases) != len(set(phases)) or not set(phases) <= {
            'NA', 'EARLY_PHASE1', 'PHASE1', 'PHASE2', 'PHASE3', 'PHASE4'}:
        missing.append('phase')
    elif set(phases) not in ({'PHASE2'}, {'PHASE2', 'PHASE3'}):
        failures.append('phase')
    interventions = _get(record, 'protocolSection', 'armsInterventionsModule', 'interventions')
    known = {'BEHAVIORAL', 'BIOLOGICAL', 'COMBINATION_PRODUCT', 'DEVICE', 'DIAGNOSTIC_TEST',
             'DIETARY_SUPPLEMENT', 'DRUG', 'GENETIC', 'PROCEDURE', 'RADIATION', 'OTHER'}
    values = [x.get('type') for x in interventions] if isinstance(interventions, list) else None
    if values is None or not values or any(v not in known for v in values):
        missing.append('intervention_type')
    if values and not any(v in {'DRUG', 'BIOLOGICAL'} for v in values) and all(v in known for v in values):
        failures.append('intervention_type')
    status = _get(record, 'protocolSection', 'statusModule') or {}
    if _get(status, 'studyFirstPostDateStruct', 'type') != 'ACTUAL':
        missing.append('first_post_date_type')
    if _get(status, 'lastUpdatePostDateStruct', 'type') != 'ACTUAL' or not _get(status, 'lastUpdatePostDateStruct', 'date'):
        missing.append('last_update_date_or_type')
    return {'screen': 'ineligible' if failures else 'screen_unknown' if missing else 'eligible',
            'known_disqualifications': failures, 'missing_or_conflicting': missing}


def validate_frame(contract, pages, *, capture_root, version_before, version_after):
    """Validate offline retained-page manifests. Never issue HTTP or qualify transport.

    Page manifests bind raw body pins, exact request/final URL, attempt=1,
    HTTP status, and UTC start/end. Every supplied attempt must have succeeded;
    failures stop the batch rather than being retried or silently omitted.
    """
    validate_contract(contract)
    require(isinstance(version_before, dict) and set(version_before) == {'apiVersion', 'dataTimestamp'}
            and all(isinstance(v, str) and v for v in version_before.values())
            and version_before == version_after, 'Version/dataTimestamp drift')
    require(isinstance(pages, list) and 0 < len(pages) <= CAPS['max_page_attempts'], 'Page attempt cap')
    capture_root = Path(capture_root).resolve()
    records, tokens, bodies = {}, set(), set()
    total_bytes, count, next_token, first_start, previous_end = 0, None, None, None, None
    tree = _tree(contract['projection'])
    for index, page in enumerate(pages):
        require(isinstance(page, dict) and set(page) == {'request', 'body', 'http_status',
                'final_url', 'attempt', 'started_at_utc', 'ended_at_utc'}, 'Malformed page manifest')
        expected = _request(contract['interval_start'], contract['interval_end'], next_token)
        require(page['request'] == expected and page['final_url'] == expected['url']
                and page['http_status'] == 200 and type(page['attempt']) is int
                and page['attempt'] == 1, 'Exact request, URL or no-retry boundary failed')
        start, end = _time(page['started_at_utc']), _time(page['ended_at_utc'])
        require(start.date().isoformat() == contract['readiness_date_R']
                and end.date() == start.date() and start <= end
                and (end - start).total_seconds() <= CAPS['max_elapsed_seconds_per_request']
                and start >= _time(contract['built_at_utc'])
                and (previous_end is None or start >= previous_end), 'Expired or invalid capture timing')
        first_start = first_start or start
        previous_end = end
        require((end - first_start).total_seconds() <= CAPS['max_frame_elapsed_seconds'], 'Elapsed frame cap')
        body = page['body']
        require(isinstance(body, dict) and set(body) == {'path', 'bytes', 'sha256'}, 'Invalid body pin')
        path = _inside(capture_root, body['path'])
        require(path not in bodies, 'Duplicate raw-body path')
        bodies.add(path)
        require(type(body['bytes']) is int and 0 < body['bytes'] <= CAPS['max_bytes_per_page']
                and path.stat().st_size == body['bytes'],
                'Page bytes/hash cap or provenance failed')
        with path.open('rb') as stream:
            raw = stream.read(CAPS['max_bytes_per_page'] + 1)
        require(len(raw) == body['bytes'] and hashlib.sha256(raw).hexdigest() == body['sha256'],
                'Page original bytes changed')
        total_bytes += body['bytes']
        require(total_bytes <= CAPS['max_frame_bytes'], 'Aggregate frame byte cap')
        payload = parse_json(raw)
        require(isinstance(payload, dict) and set(payload) <= {'studies', 'totalCount', 'nextPageToken'}
                and isinstance(payload.get('studies'), list)
                and len(payload['studies']) <= CAPS['page_size'], 'Page response allowlist/cap failed')
        if index == 0:
            count = payload.get('totalCount')
            require(type(count) is int and 0 <= count <= CAPS['frame_max_records'], 'Complete frame count cap')
        elif 'totalCount' in payload:
            require(type(payload['totalCount']) is int and payload['totalCount'] == count, 'Count drift')
        for record in payload['studies']:
            _guard(record, tree)
            phase_array = _get(record, 'protocolSection', 'designModule', 'phases')
            interventions_array = _get(record, 'protocolSection', 'armsInterventionsModule', 'interventions')
            require((phase_array is None or isinstance(phase_array, list))
                    and (interventions_array is None or isinstance(interventions_array, list)
                         and all(isinstance(item, dict) for item in interventions_array)),
                    'Quarantine: projected array shape differs from schema')
            nct = _get(record, 'protocolSection', 'identificationModule', 'nctId')
            require(isinstance(nct, str) and re.fullmatch(r'NCT[0-9]{8}', nct)
                    and nct not in records, 'Noncanonical or duplicate NCT identity')
            status = _get(record, 'protocolSection', 'statusModule') or {}
            posted = _get(status, 'studyFirstPostDateStruct', 'date')
            require(posted is not None and _day(contract['interval_start']) <= _day(posted)
                    <= _day(contract['interval_end']), 'Returned first-post date missing or outside interval')
            updated = _get(status, 'lastUpdatePostDateStruct', 'date')
            if updated is not None:
                require(_day(posted) <= _day(updated) <= _day(contract['readiness_date_R']),
                        'Returned update date conflicts with capture')
            result = _screen(record)
            result.update(nct_id=nct, exposure_excluded=nct in contract['exposed_ids'])
            records[nct] = result
        require(len(records) <= count, 'Returned records exceed declared total')
        token = payload.get('nextPageToken')
        if token is not None:
            _request(contract['interval_start'], contract['interval_end'], token)
            require(token not in tokens and index + 1 < len(pages), 'Token loop or truncated frame')
            tokens.add(token)
        else:
            require(index + 1 == len(pages), 'Extra page after terminal response')
        next_token = token
    require(next_token is None and len(records) == count, 'Incomplete terminal frame')
    pool = [nct for nct, row in records.items() if row['screen'] != 'ineligible' and not row['exposure_excluded']]
    pool.sort(key=lambda n: (hashlib.sha256((contract['protocol']['sha256'] + n).encode('utf-8')).hexdigest(), n))
    return {'kind': 'offline_frame_validation', 'complete': True, 'frame_count': count,
            'all_member_ledger': [records[n] for n in sorted(records)],
            'sample_nct_ids': pool[:12], 'source_bytes': total_bytes, 'page_attempts': len(pages),
            'actual_capture_started_at_utc': pages[0]['started_at_utc'],
            'actual_capture_ended_at_utc': pages[-1]['ended_at_utc'],
            'transport_qualified': False, 'clinical_activation': False,
            'interpretation': 'Offline shape/integrity validation only; no live transport or clinical qualification.'}
