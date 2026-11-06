"""Independent schema2 authorization and canonical outer evidence validation.

Only standard-library and experiment-owned helpers are used. Native product wire
names are data contracts, not calls into the implementation under comparison.
"""
from __future__ import annotations

import copy
import hashlib
import math
import os
from pathlib import Path
import re
import stat
import time

from .independent import (PolicyError, admit, availability_reason, canonical, child,
                          decode, digest, inspect_core, parse, prepare_core, require,
                          timestamp, validate_case, verify_core)

CONTROL = 16 * 1024 * 1024
NORMAL = 64 * 1024 * 1024
LARGE = 256 * 1024 * 1024
IDENTITY = ('dataset_id', 'release_id', 'root_alias', 'relative_path', 'sha256', 'bytes')
POLICY_FIELDS = {'schema_version', 'policy_id', 'created_at_utc', 'source_catalog', 'catalog_metadata', 'products', 'artifacts', 'uses'}
PRODUCT_FIELDS = {'dataset_id', 'metadata', 'input_dependencies', 'validation_dependencies', 'conditional_input_groups', 'dependency_review_status', 'agent_use_policy'}
ARTIFACT_FIELDS = {'artifact_id', *IDENTITY, 'kind', 'parents', 'availability', 'temporal_classification', 'source_url', 'provenance', 'scope', 'scientific_validation'}
USE_FIELDS = {'use_id', 'kind', 'status', 'profile', 'origin_at', 'frame_sha256', 'case_fingerprint', 'snapshot_fingerprint', 'raw_root_alias', 'snapshot_root_alias', 'grants', 'blockers'}
ROLES = {'agent_evidence', 'reference', 'evaluation_only', 'comparison_only'}
PROFILES = {'historical_benchmark', 'contemporary_assessment', 'synthetic_demo'}
TEMPORAL = {'verified_historical', 'reconstructed', 'contemporary_only', 'unverified'}
USE_KINDS = {'contemporary_evidence', 'normalization_reference', 'origin_context', 'endpoint_evaluation', 'ascertainment_evaluation'}
SHA = re.compile(r'[0-9a-f]{64}\Z')


def need(value, message, obligation='EP-POLICY-01'):
    require(value, obligation, message)


def exact(value, fields, label):
    need(type(value) is dict and set(value) == set(fields), label + ' fields differ')


def text(value, label):
    need(type(value) is str and value and value.strip() == value and all(ord(c) >= 32 for c in value), 'Invalid ' + label)
    return value


def pin(value):
    need(type(value) is str and SHA.fullmatch(value), 'Invalid SHA256')
    return value


def alias(value):
    need(type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}', value), 'Invalid root alias')


def relative(value):
    text(value, 'relative path')
    parts = value.split('/')
    forbidden = {'CON', 'PRN', 'AUX', 'NUL'} | {f'{p}{n}' for p in ('COM', 'LPT') for n in range(1, 10)}
    need(not any(c in value for c in '\\:<>"|?*') and not value.startswith('/') and
         all(p not in ('', '.', '..') and p.rstrip(' .') == p and p.split('.')[0].upper() not in forbidden for p in parts), 'Unsafe portable path')
    return value


def utc(value):
    text(value, 'UTC time')
    result = timestamp(value)
    need('T' in value and result.utcoffset().total_seconds() == 0, 'Exact UTC time required')
    # timestamp normalizes offsets, so inspect the original timezone as well.
    from datetime import datetime
    need(datetime.fromisoformat(value.replace('Z', '+00:00')).utcoffset().total_seconds() == 0, 'Non-UTC policy time')
    return result


def unique(value, label):
    need(type(value) is list and all(type(x) is str and x and x.strip() == x for x in value), 'Invalid ' + label)
    need(len(value) == len(set(value)), 'Duplicate ' + label)
    return set(value)


def finite_json(value):
    if type(value) is dict:
        need(all(type(k) is str for k in value), 'Nonstring JSON key')
        for v in value.values(): finite_json(v)
    elif type(value) is list:
        for v in value: finite_json(v)
    else:
        need(type(value) in (str, int, float, bool, type(None)) and
             not (type(value) is float and not math.isfinite(value)), 'Nonfinite/non-JSON policy value')


def acyclic(graph):
    closed, active = set(), set()
    def visit(key):
        need(key in graph and key not in active, 'Missing parent or cycle')
        if key in closed: return
        active.add(key)
        for parent in graph[key]: visit(parent)
        active.remove(key); closed.add(key)
    for key in graph: visit(key)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def no_links(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        info = part.lstat()
        need(not stat.S_ISLNK(info.st_mode) and not (getattr(info, 'st_file_attributes', 0) & 0x400),
             'Link/reparse input denied', 'EP-IO-01')
    return path


def secure_path(root, name):
    relative(name)
    path = no_links(Path(root).joinpath(*name.split('/')))
    need(path.resolve().is_relative_to(Path(root).resolve()), 'Path escaped selected root', 'EP-IO-01')
    return path


def stable(path, deadline, maximum=None, *, collect=True):
    path = no_links(path)
    before = path.stat()
    need(stat.S_ISREG(before.st_mode), 'Nonregular input', 'EP-IO-01')
    need(maximum is None or before.st_size <= maximum, 'Input byte cap', 'EP-IO-01')
    payload, count, checksum = [], 0, hashlib.sha256()
    with path.open('rb') as stream:
        need(_identity(os.fstat(stream.fileno())) == _identity(before), 'Input changed on open', 'EP-IO-01')
        while True:
            need(time.monotonic() < deadline, 'Input deadline', 'EP-IO-01')
            block = stream.read(1024 * 1024 if maximum is None else min(1024 * 1024, maximum - count + 1))
            if not block: break
            count += len(block)
            need(maximum is None or count <= maximum, 'Input grew past cap', 'EP-IO-01')
            checksum.update(block)
            if collect: payload.append(block)
        need(_identity(os.fstat(stream.fileno())) == _identity(before), 'Input changed during read', 'EP-IO-01')
    no_links(path)
    need(time.monotonic() < deadline, 'Input deadline after read', 'EP-IO-01')
    need(_identity(path.stat()) == _identity(before) and count == before.st_size, 'Input changed after read', 'EP-IO-01')
    return b''.join(payload) if collect else dict(sha256=checksum.hexdigest(), bytes=count)


def json_file(path, deadline, cap=CONTROL):
    raw = stable(path, deadline, cap)
    value = parse(raw); finite_json(value)
    need(type(value) is dict, 'JSON object required')
    return value, raw


def legacy(policy):
    return {**copy.deepcopy(policy['catalog_metadata']), 'datasets': [copy.deepcopy(p['metadata']) for p in policy['products']]}


def validate_document(policy):
    finite_json(policy); exact(policy, POLICY_FIELDS, 'policy')
    need(type(policy['schema_version']) is int and policy['schema_version'] == 2, 'Policy schema')
    text(policy['policy_id'], 'policy ID'); utc(policy['created_at_utc'])
    source = policy['source_catalog']; exact(source, {'path', 'sha256', 'document_fingerprint'}, 'source catalog')
    relative(source['path']); pin(source['sha256']); pin(source['document_fingerprint'])
    metadata = policy['catalog_metadata']
    need(type(metadata) is dict and type(metadata.get('schema_version')) is int and metadata['schema_version'] == 1 and 'datasets' not in metadata, 'Retained catalog metadata')
    providers = metadata.get('providers')
    need(type(providers) is list and providers and all(type(p) is dict for p in providers), 'Providers required')
    provider_ids = [p.get('provider_id') for p in providers]
    need(all(type(p) is str and p for p in provider_ids) and len(set(provider_ids)) == len(provider_ids), 'Provider identities')
    need(all(type(policy[field]) is list for field in ('products', 'artifacts', 'uses')), 'Policy inventories')
    products = {}
    for row in policy['products']:
        exact(row, PRODUCT_FIELDS, 'product'); key = text(row['dataset_id'], 'dataset ID')
        need(key not in products, 'Duplicate product')
        m = row['metadata']; need(type(m) is dict and m.get('dataset_id') == key and m.get('provider_id') in provider_ids, 'Product identity')
        roles = unique(m.get('roles'), 'product roles'); need(roles and roles <= ROLES, 'Product roles')
        need(row['agent_use_policy'] == ('denied_evaluator_product' if 'evaluation_only' in roles else 'requires_artifact_grant'), 'Evaluator policy changed')
        need(row['dependency_review_status'] in {'legacy_carried_forward', 'reviewed_dependency_classification', 'reviewed_for_selected_frame'}, 'Dependency review state')
        need(not unique(row['input_dependencies'], 'input dependencies') & unique(row['validation_dependencies'], 'validation dependencies'), 'Dependency overlap')
        need(type(row['conditional_input_groups']) is list, 'Conditional groups')
        products[key] = row
    need(products and digest(legacy(policy)) == source['document_fingerprint'], 'Retained catalog fingerprint')
    for row in products.values():
        for kind in ('input_dependencies', 'validation_dependencies'):
            need(set(row[kind]) <= products.keys(), 'Unknown dependency')
        need(set(row['metadata'].get('required_component_dataset_ids', [])) <= products.keys(), 'Unknown component')
        for group in row['conditional_input_groups']:
            exact(group, {'requirement', 'dataset_ids'}, 'conditional group'); text(group['requirement'], 'requirement')
            need(unique(group['dataset_ids'], 'conditional IDs') and set(group['dataset_ids']) <= products.keys(), 'Conditional IDs')
    acyclic({key: row['input_dependencies'] for key, row in products.items()})
    if 'genetics_results' in products:
        row = products['genetics_results']
        need('genetics_qc_cases' not in row['input_dependencies'] and ('genetics_qc_cases' not in products or 'genetics_qc_cases' in row['validation_dependencies']), 'Genetics QC classification')
        need('igsr_ld_reference' not in row['input_dependencies'], 'LD not conditional')
    artifacts = {}
    for row in policy['artifacts']:
        exact(row, ARTIFACT_FIELDS, 'artifact')
        key = row['artifact_id']; need(key == 'artifact-' + digest({k: row[k] for k in IDENTITY}) and key not in artifacts, 'Artifact identity')
        need(row['dataset_id'] in products, 'Artifact product'); text(row['release_id'], 'release'); alias(row['root_alias'])
        relative(row['relative_path']); pin(row['sha256'])
        need(type(row['bytes']) is int and row['bytes'] >= 0, 'Artifact bytes')
        need(row['kind'] in {'raw', 'derived', 'packet'} and row['temporal_classification'] in TEMPORAL, 'Artifact kind/classification')
        parents = unique(row['parents'], 'artifact parents'); need((row['kind'] == 'raw') == (not parents), 'Raw/derived ancestry')
        if row['availability'] is not None: decode('Availability', row['availability'])
        need(row['source_url'] is None or type(row['source_url']) is str, 'Source URL type')
        text(row['scope'], 'scope'); need(row['scientific_validation'] == 'not_established', 'Scientific promotion')
        provenance = row['provenance']; exact(provenance, {'kind', 'evidence', 'receipt'}, 'provenance')
        kind = provenance['kind']; need(kind in {'download_receipt', 'generated', 'manual_archive'}, 'Provenance kind')
        need(row['source_url'] is not None or kind == 'manual_archive', 'Unknown source URL')
        need(type(provenance['evidence']) is list and provenance['evidence'], 'Provenance evidence required')
        for evidence in provenance['evidence']:
            exact(evidence, {'path', 'sha256'}, 'evidence proof'); relative(evidence['path']); pin(evidence['sha256'])
        receipt = provenance['receipt']
        if kind == 'download_receipt':
            need(row['kind'] == 'raw', 'Generated transport provenance')
            exact(receipt, {'root_alias', 'relative_path', 'sha256', 'receipt_id', 'url'}, 'receipt reference')
            alias(receipt['root_alias']); relative(receipt['relative_path']); pin(receipt['sha256'])
            text(receipt['receipt_id'], 'receipt ID'); text(receipt['url'], 'receipt URL')
            need(receipt['url'] == row['source_url'], 'Receipt/source URL')
        else:
            need(receipt is None and (kind == 'manual_archive') == (row['kind'] == 'raw'), 'Provenance/raw kind differs')
        artifacts[key] = row
    acyclic({key: row['parents'] for key, row in artifacts.items()})
    uses = {}
    for row in policy['uses']:
        exact(row, USE_FIELDS, 'use'); key = text(row['use_id'], 'use ID'); need(key not in uses, 'Duplicate use')
        need(row['kind'] in USE_KINDS and row['status'] in {'allowed', 'blocked'} and row['profile'] in PROFILES, 'Use kind/status/profile')
        utc(row['origin_at']); alias(row['raw_root_alias']); alias(row['snapshot_root_alias'])
        need(row['raw_root_alias'] != row['snapshot_root_alias'], 'Root alias overlap')
        blockers = unique(row['blockers'], 'blockers'); allowed = row['status'] == 'allowed'
        need(allowed == (not blockers), 'Blockers/disposition')
        for field in ('frame_sha256', 'case_fingerprint', 'snapshot_fingerprint'):
            if row[field] is not None: pin(row[field])
            else: need(not allowed, 'Allowed use lacks binding')
        need(type(row['grants']) is list, 'Grants array')
        grants = set()
        for grant in row['grants']:
            exact(grant, {'artifact_id', 'role'}, 'grant'); item = grant['artifact_id']
            need(item in artifacts and item not in grants and grant['role'] in ROLES, 'Invalid grant')
            grants.add(item)
            if allowed:
                product = products[artifacts[item]['dataset_id']]
                need(grant['role'] in {'agent_evidence', 'reference'} and grant['role'] in product['metadata']['roles'] and product['agent_use_policy'] != 'denied_evaluator_product', 'Evaluator/unsupported grant')
                need(product['dependency_review_status'] == 'reviewed_for_selected_frame' and artifacts[item]['provenance']['kind'] != 'manual_archive', 'Unqualified selected product/artifact')
        if allowed:
            need(grants and row['kind'] not in {'endpoint_evaluation', 'ascertainment_evaluation'}, 'Empty/evaluation use')
            need(all(set(artifacts[item]['parents']) <= grants for item in grants), 'Grant omits ancestor')
        uses[key] = row
    return products, artifacts, uses


def root_map(document):
    exact(document, {'schema_version', 'roots'}, 'roots')
    need(type(document['schema_version']) is int and document['schema_version'] == 1 and type(document['roots']) is dict, 'Root schema', 'EP-POLICY-02')
    roots = document['roots']; need('metadata' in roots, 'Metadata root required', 'EP-POLICY-02')
    for key, value in roots.items():
        alias(key); text(value, 'root')
        p = Path(value)
        need(p.is_absolute() and '..' not in p.parts and not p.drive.startswith('\\\\'), 'Absolute local roots required', 'EP-POLICY-02')
    need(len({str(Path(p)).replace('\\', '/').casefold() for p in roots.values()}) == len(roots), 'Root alias collision', 'EP-POLICY-02')
    return roots


def bind(policy, case, snapshot, roots, use_id, frame):
    products, artifacts, uses = validate_document(policy)
    check = lambda condition, message: need(condition, message, 'EP-POLICY-02')
    use = uses.get(use_id)
    check(use is not None and use['status'] == 'allowed', 'Missing/blocked selected use')
    pin(frame); check(frame == use['frame_sha256'], 'Independent frame differs')
    check(type(case.get('schema_version')) is int and case['schema_version'] == 2 and
          type(snapshot.get('schema_version')) is int and snapshot['schema_version'] == 2, 'V2 controls required')
    check(snapshot.get('profile') != 'synthetic_demo', 'Policy path does not authorize demo')
    validate_case(decode('Case', case)); decode('Snapshot', snapshot)
    check(digest(case) == use['case_fingerprint'] and digest(snapshot) == use['snapshot_fingerprint'], 'Case/snapshot fingerprint differs')
    check(snapshot.get('profile') == use['profile'] and snapshot.get('origin_at') == case.get('origin_at') == use['origin_at'] and
          snapshot.get('origin') == case.get('origin') == utc(use['origin_at']).date().isoformat(), 'Use origin/profile differs')
    check(use['raw_root_alias'] in roots and use['snapshot_root_alias'] in roots, 'Missing selected root')
    check(type(snapshot.get('raw_root')) is str and str(Path(snapshot['raw_root'])) == str(Path(roots[use['raw_root_alias']])), 'Raw root differs')
    grants = {g['artifact_id']: g['role'] for g in use['grants']}
    identities = {}
    for record in artifacts.values():
        key = tuple(record[k] for k in IDENTITY if k != 'bytes')
        check(key not in identities, 'Ambiguous artifact identity/size'); identities[key] = record
    inventory, supplied = [], {}
    for category, field, id_field in (('source', 'sources', 'source_id'), ('packet', 'artifacts', 'artifact_id')):
        check(type(snapshot.get(field)) is list, 'Snapshot inventory array required')
        for node in snapshot[field]:
            check(type(node) is dict, 'Inventory node must be object')
            key = text(node.get(id_field), 'node ID'); check(key not in supplied, 'Duplicate supplied identity')
            raw = category == 'source' and node.get('computed_at') is None
            root_alias = use['raw_root_alias'] if raw else use['snapshot_root_alias']
            name = relative(node.get('path'))
            identity = (node.get('dataset_id'), node.get('release_id'), root_alias, name, node.get('sha256'))
            record = identities.get(identity); check(record is not None, 'Undeclared input identity')
            global_id, role = record['artifact_id'], node.get('role')
            check(global_id in grants and grants[global_id] == role and role in {'agent_evidence', 'reference'}, 'Input grant/role differs')
            check(products[node['dataset_id']]['agent_use_policy'] != 'denied_evaluator_product' and node['dataset_id'] != 'scorer_artifacts', 'Evaluator/scorer input denied')
            check(record['kind'] == ('raw' if raw else 'derived' if category == 'source' else 'packet'), 'Input kind differs')
            if category == 'packet': check(role == 'agent_evidence' and node.get('access_approved') is True, 'Packet access differs')
            check(all(node.get(k) == record[k] for k in ('availability', 'temporal_classification', 'source_url')), 'Input context differs')
            if raw:
                check(record['availability'] is not None, 'Raw availability missing')
                check(availability_reason(decode('Availability', record['availability']), utc(use['origin_at'])) is None, 'Raw input unavailable')
                temporal = record['temporal_classification']
                check((temporal == 'verified_historical' or temporal == 'reconstructed' and snapshot.get('allow_reconstructed') is True)
                      if use['profile'] == 'historical_benchmark' else temporal != 'unverified', 'Raw historical/temporal gate')
                receipt = record['provenance']['receipt']
                check(receipt is not None and receipt['root_alias'] == use['raw_root_alias'] and
                      node.get('receipt_path') == receipt['relative_path'] and node.get('receipt_sha256') == receipt['sha256'], 'Raw receipt binding')
            parents = node.get('parents', []) if category == 'source' else node.get('input_refs', [])
            unique(parents, 'supplied parents')
            entry = dict(source_id=key, artifact_id=global_id, category=category, role=role, dataset_id=record['dataset_id'],
                release_id=record['release_id'], root_alias=root_alias, relative_path=name,
                physical_path=str(Path(roots[root_alias]).joinpath(*name.split('/'))), sha256=record['sha256'],
                bytes=record['bytes'], parents=list(parents), receipt=copy.deepcopy(record['provenance']['receipt']))
            inventory.append(entry); supplied[key] = entry
    check(inventory and len({r['artifact_id'] for r in inventory}) == len(inventory) and
          {r['artifact_id'] for r in inventory} == set(grants), 'Exact grant/inventory mismatch')
    for entry in inventory:
        check(set(entry['parents']) <= supplied.keys(), 'Missing supplied ancestor')
        check(all(supplied[p]['category'] == 'source' for p in entry['parents']), 'Packet used as parent')
        actual = {supplied[p]['artifact_id'] for p in entry['parents']}
        check(actual == set(artifacts[entry['artifact_id']]['parents']), 'Actual ancestor edges differ')
        entry['parent_artifact_ids'] = sorted(actual)
    acyclic({entry['source_id']: entry['parents'] for entry in inventory})
    check(len({r['physical_path'].replace('\\', '/').casefold() for r in inventory}) == len(inventory), 'Physical path aliases')
    check(all(r['relative_path'].casefold() != 'snapshot.json' for r in inventory if r['root_alias'] == use['snapshot_root_alias']), 'Snapshot copy collision')
    projection = legacy(policy)
    roles = {}
    for entry in inventory: roles.setdefault(entry['dataset_id'], set()).add(entry['role'])
    for product in projection['datasets']: product['roles'] = sorted(roles.get(product['dataset_id'], {'evaluation_only'}))
    decision = dict(schema_version=1, method='tether.catalog_policy_binding.v1', policy_id=policy['policy_id'],
        policy_fingerprint=digest(policy), source_catalog=copy.deepcopy(policy['source_catalog']), use_id=use_id,
        frame_sha256=frame, profile=use['profile'], origin_at=use['origin_at'], case_fingerprint=digest(case),
        snapshot_fingerprint=digest(snapshot), root_aliases=copy.deepcopy(roots), projection_fingerprint=digest(projection),
        inventory=inventory, scientific_validation='not_established')
    return decision, projection, artifacts, use


def receipt_check(entry, node, raw):
    receipt = parse(raw); finite_json(receipt)
    check = lambda value, message: need(value, message, 'EP-POLICY-03')
    check(type(receipt) is dict, 'Receipt object required')
    ref = entry['receipt']
    expected = dict(receipt_id=ref['receipt_id'], dataset_id=entry['dataset_id'], release_id=entry['release_id'], url=ref['url'])
    check(all(receipt.get(k) == v for k, v in expected.items()), 'Receipt transport identity differs')
    path = receipt.get('relative_path'); check(type(path) is str, 'Receipt relative path required')
    check(relative(path.replace('\\', '/')) == entry['relative_path'], 'Receipt payload path differs')
    check(receipt.get('status') == 'completed' and type(receipt.get('bytes')) is int and receipt['bytes'] == entry['bytes'] and
          receipt.get('sha256') == entry['sha256'], 'Receipt status/bytes/hash differs')
    completed = utc(receipt.get('completed_at_utc'))
    availability = decode('Availability', node['availability'])
    if availability['basis'] == 'public_download_receipt':
        check(availability['known_public_by'] is not None and timestamp(availability['known_public_by']) >= completed and
              availability['evidence_ref'] == node['receipt_sha256'] and node['source_url'] == receipt.get('url'), 'Download availability proof differs')


def checked_bytes(path, entry, deadline, cap=None, *, collect=False):
    result = stable(path, deadline, cap, collect=collect)
    observed = dict(sha256=hashlib.sha256(result).hexdigest(), bytes=len(result)) if collect else result
    need(observed['sha256'] == entry['sha256'] and observed['bytes'] == entry['bytes'], 'Input hash/size differs', 'EP-POLICY-03')
    return result


def publish(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True); no_links(path.parent)
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def descriptor(path, raw):
    return dict(path=path, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def validate_process_limits(value):
    defaults = dict(timeout_seconds=3600.0, max_output_bytes=16 * 1024 * 1024)
    need(type(value) is dict and set(value) <= set(defaults), 'Process option fields', 'EP-PROCESS-01')
    limits = {**defaults, **value}
    timeout, maximum = limits['timeout_seconds'], limits['max_output_bytes']
    need(type(timeout) in (int, float) and math.isfinite(timeout) and timeout > 0 and type(maximum) is int and
         1 <= maximum <= NORMAL, 'Process bounds', 'EP-PROCESS-01')
    return limits


def prepare_policy(root, request, scratch_dir):
    paths, options, anchors = request['paths'], request['options'], request['anchors']
    need(all(paths.get(k) for k in ('case', 'snapshot', 'catalog', 'catalog_policy', 'policy_roots')) and
         options.get('policy_use') and anchors.get('frame_sha256'), 'Complete policy inputs required', 'EP-POLICY-02')
    need(not any(paths.get(k) for k in ('scorer', 'replay', 'local_model')), 'Policy path is offline without scorer/replay/local', 'EP-POLICY-02')
    validate_process_limits(options.get('process_limits', {}))
    deadline = time.monotonic() + 300
    mapped = {'policy': 'catalog_policy', 'roots': 'policy_roots', 'case': 'case', 'snapshot': 'snapshot', 'source_catalog': 'catalog'}
    controls, raw, original = {}, {}, {}
    for key, name in mapped.items():
        original[key] = child(root, paths[name]); controls[key], raw[key] = json_file(original[key], deadline)
    policy = controls['policy']; roots = root_map(controls['roots'])
    decision, projection, artifacts, use = bind(policy, controls['case'], controls['snapshot'], roots, options['policy_use'], anchors['frame_sha256'])
    need(hashlib.sha256(raw['source_catalog']).hexdigest() == policy['source_catalog']['sha256'] and
         controls['source_catalog'] == legacy(policy), 'Original catalog anchor differs')
    need(str(secure_path(roots['metadata'], policy['source_catalog']['path'])) == str(original['source_catalog']) and
         str(original['snapshot'].parent) == str(Path(roots[use['snapshot_root_alias']])), 'Control locations differ', 'EP-POLICY-02')
    need(scratch_dir is not None, 'Schema2 preparation needs fresh scratch', 'EP-IO-01')
    scratch = no_links(Path(scratch_dir)); need(scratch.is_dir() and not any(scratch.iterdir()) and
         not scratch.resolve().is_relative_to(Path(root).resolve()), 'Scratch must be empty and outside frozen bundle', 'EP-IO-01')
    leaf = scratch / 'independent-policy'; leaf.mkdir()
    retained, originals = {}, []
    def retain(name, payload):
        destination = leaf / name
        if destination.exists(): need(stable(destination, deadline, max(CONTROL, len(payload))) == payload, 'Conflicting copy', 'EP-POLICY-04')
        else: publish(destination, payload)
        need(stable(destination, deadline, max(CONTROL, len(payload))) == payload, 'Copied bytes differ', 'EP-POLICY-04')
        retained[name] = descriptor(name, payload)
    for name, payload in raw.items(): retain('controls/' + name + '.json', payload)
    retain('projection.json', canonical(projection)); retain('decision.json', canonical(decision))
    nodes = {n['source_id']: n for n in controls['snapshot']['sources']}
    for entry in decision['inventory']:
        source = secure_path(roots[entry['root_alias']], entry['relative_path'])
        if entry['root_alias'] == use['snapshot_root_alias']:
            payload = checked_bytes(source, entry, deadline, NORMAL, collect=True)
            retain('inputs/' + entry['relative_path'], payload)
        else:
            checked_bytes(source, entry, deadline)
        originals.append((source, entry))
        for proof in artifacts[entry['artifact_id']]['provenance']['evidence']:
            payload = stable(secure_path(roots['metadata'], proof['path']), deadline, CONTROL)
            need(hashlib.sha256(payload).hexdigest() == proof['sha256'], 'Metadata proof differs', 'EP-POLICY-04')
            retain('provenance/' + proof['sha256'] + '.bin', payload)
        if entry['receipt'] is not None:
            ref = entry['receipt']; path = secure_path(roots[ref['root_alias']], ref['relative_path'])
            payload = stable(path, deadline, CONTROL)
            need(hashlib.sha256(payload).hexdigest() == ref['sha256'], 'Receipt hash differs', 'EP-POLICY-03')
            receipt_check(entry, nodes[entry['source_id']], payload)
            retain('receipts/' + ref['sha256'] + '.json', payload)
            originals.append((path, dict(sha256=ref['sha256'], bytes=len(payload))))
    retain('inputs/snapshot.json', raw['snapshot'])
    for path, expected in originals: checked_bytes(path, expected, deadline)
    for name, payload in raw.items(): need(stable(original[name], deadline, CONTROL) == payload, 'Original control changed', 'EP-POLICY-04')
    for name, expected in retained.items(): checked_bytes(secure_path(leaf, name), expected, deadline)
    observed = prepare_core(root, request, catalog_override=projection)
    # Re-admit exact copied packets/mappings against the same external raw roots.
    admit(decode('Case', controls['case']), decode('Snapshot', controls['snapshot']), leaf / 'inputs', projection)
    publish(leaf / 'retention.json', canonical(dict(schema_version=1, copies=retained, source_rechecked=len(originals),
        scope='Independent immutable preparation witness; no execution or scientific validation')))
    return observed


def verify_binding(output, binding_descriptor, deadline):
    obligation = 'EP-POLICY-04'
    check = lambda value, message: need(value, message, obligation)
    exact(binding_descriptor, {'path', 'sha256', 'bytes'}, 'binding descriptor')
    check(binding_descriptor['path'] == 'catalog-policy/binding.json', 'Binding location')
    payload = stable(secure_path(output, binding_descriptor['path']), deadline, CONTROL)
    check(canonical(descriptor(binding_descriptor['path'], payload)) == canonical(binding_descriptor), 'Binding descriptor bytes')
    seal = parse(payload)
    exact(seal, {'schema_version', 'method', 'use_id', 'frame_sha256', 'original_control_paths', 'controls', 'copies',
                 'external_sources', 'receipts', 'execution', 'receipt_execution', 'scientific_validation', 'metadata_proofs'}, 'binding')
    check(type(seal['schema_version']) is int and seal['schema_version'] == 1 and seal['method'] == 'tether.sealed_catalog_binding.v1' and
          seal['receipt_execution'] == 'original_pinned_paths_rechecked_against_archived_copies' and
          seal['scientific_validation'] == 'not_established', 'Binding schema/scope')
    exact(seal['controls'], {'policy', 'roots', 'case', 'snapshot', 'projection', 'decision', 'execution_snapshot', 'source_catalog'}, 'sealed controls')
    controls, raw = {}, {}
    for name, proof in seal['controls'].items():
        expected = 'catalog-policy/' + ('inputs/snapshot.json' if name == 'execution_snapshot' else name + '.json')
        check(proof.get('path') == expected, 'Control path')
        payload = stable(secure_path(output, expected), deadline, CONTROL)
        check(canonical(descriptor(expected, payload)) == canonical(proof), 'Control hash/size')
        controls[name] = parse(payload); raw[name] = payload
    check(raw['snapshot'] == raw['execution_snapshot'], 'Executed snapshot bytes differ')
    policy, roots = controls['policy'], root_map(controls['roots'])
    decision, projection, artifacts, use = bind(policy, controls['case'], controls['snapshot'], roots, seal['use_id'], seal['frame_sha256'])
    check(hashlib.sha256(raw['source_catalog']).hexdigest() == policy['source_catalog']['sha256'] and controls['source_catalog'] == legacy(policy), 'Copied original catalog differs')
    check(str(Path(roots['metadata']).joinpath(*policy['source_catalog']['path'].split('/'))) == seal['original_control_paths']['source_catalog'] and
          str(Path(seal['original_control_paths']['snapshot']).parent) == str(Path(roots[use['snapshot_root_alias']])), 'Original control location differs')
    check(canonical(decision) == canonical(controls['decision']) and canonical(projection) == canonical(controls['projection']), 'Decision/projection differs')
    metadata, copies, external, receipts = [], [], [], []
    nodes = {node['source_id']: node for node in controls['snapshot']['sources']}
    for entry in decision['inventory']:
        for proof in artifacts[entry['artifact_id']]['provenance']['evidence']:
            name = 'catalog-policy/provenance/' + proof['sha256'] + '.bin'
            payload = stable(secure_path(output, name), deadline, CONTROL)
            check(hashlib.sha256(payload).hexdigest() == proof['sha256'], 'Metadata bytes differ')
            metadata.append(dict(source_id=entry['source_id'], declared_path=proof['path'], **descriptor(name, payload)))
        if entry['root_alias'] == use['snapshot_root_alias']:
            name = 'catalog-policy/inputs/' + entry['relative_path']
            checked_bytes(secure_path(output, name), entry, deadline)
            copies.append(dict(source_id=entry['source_id'], path=name, sha256=entry['sha256'], bytes=entry['bytes']))
        else:
            path = secure_path(roots[entry['root_alias']], entry['relative_path'])
            checked_bytes(path, entry, deadline)
            external.append(dict(source_id=entry['source_id'], path=str(path), sha256=entry['sha256'], bytes=entry['bytes']))
        if entry['receipt'] is not None:
            ref = entry['receipt']; path = secure_path(roots[ref['root_alias']], ref['relative_path'])
            original = stable(path, deadline, CONTROL)
            name = 'catalog-policy/receipts/' + ref['sha256'] + '.json'
            payload = stable(secure_path(output, name), deadline, CONTROL)
            check(payload == original and hashlib.sha256(payload).hexdigest() == ref['sha256'], 'Archived/original receipt differs')
            receipt_check(entry, nodes[entry['source_id']], payload)
            receipts.append(dict(source_id=entry['source_id'], original_path=str(path), **descriptor(name, payload)))
    for field, expected in (('metadata_proofs', metadata), ('copies', copies), ('external_sources', external), ('receipts', receipts)):
        check(canonical(seal[field]) == canonical(expected), 'Sealed ' + field + ' differs')
    execution = dict(case='catalog-policy/case.json', snapshot='catalog-policy/inputs/snapshot.json', catalog='catalog-policy/projection.json')
    check(seal['execution'] == execution, 'Execution paths differ')
    case, snapshot = decode('Case', controls['case']), decode('Snapshot', controls['snapshot'])
    admit(case, snapshot, Path(output) / 'catalog-policy/inputs', projection)
    inputs, _ = json_file(Path(output) / 'engine/inputs.json', deadline)
    run, _ = json_file(Path(output) / 'engine/run.json', deadline)
    check(canonical(inputs['case']) == canonical(case) and canonical(inputs['snapshot']) == canonical(snapshot) and
          canonical(inputs['catalog_policy']) == canonical(projection) and inputs['scorer'] is None and
          inputs['snapshot_base'] == str((Path(output) / 'catalog-policy/inputs').resolve()) and
          run['backend_id'] == 'offline-extractive-v1', 'Actual engine controls differ')
    return dict(method='tether.sealed_catalog_binding.v1', status='artifact_policy_consistency_verified', policy_id=policy['policy_id'],
        use_id=seal['use_id'], frame_sha256=seal['frame_sha256'], checked_inputs=len(decision['inventory']), scientific_validation='not_established')


def chain(payload, partial=False):
    events, prior = [], None
    lines = payload.splitlines()
    for i, line in enumerate(lines):
        if partial and i == len(lines)-1 and not payload.endswith(b'\n'): break
        value = parse(line)
        need(type(value) is dict and 'sha256' in value, 'Journal envelope', 'EP-EXEC-04')
        checksum = value.pop('sha256')
        need(value.get('sequence') == len(events) and value.get('previous_sha256') == prior and digest(value) == checksum, 'Journal chain differs', 'EP-EXEC-04')
        value['sha256'] = checksum; events.append(value); prior = checksum
    need(events, 'Empty journal', 'EP-EXEC-04')
    return events


def file_inventory(root):
    root = no_links(root); files, directories = set(), set()
    for directory, children, names in os.walk(root, followlinks=False):
        for name in children:
            item = no_links(Path(directory) / name); directories.add(item.relative_to(root).as_posix())
        for name in names:
            item = no_links(Path(directory) / name)
            need(item.is_file(), 'Nonfile outer artifact', 'EP-IO-01')
            files.add(relative(item.relative_to(root).as_posix()))
    return files, directories


def supervision(report, limits, stdout_size, stderr_size):
    check = lambda value, message: need(value, message, 'EP-PROCESS-01')
    fields = {'schema_version', 'method', 'limits', 'termination_reason', 'execution_elapsed_seconds', 'total_elapsed_seconds',
              'retained_stdout_bytes', 'retained_stderr_bytes', 'observed_stdout_bytes', 'observed_stderr_bytes',
              'observed_counts_are_lower_bounds', 'pipe_eof', 'process_started', 'process_reaped', 'cleanup_errors'}
    check(type(report) is dict and set(report) == fields, 'Supervision fields')
    check(type(report['schema_version']) is int and report['schema_version'] == 1 and report['method'] == 'tether.process_envelope.v1' and
          canonical(report['limits']) == canonical(limits) and report['termination_reason'] == 'exited' and
          report['process_started'] is True and report['process_reaped'] is True and report['observed_counts_are_lower_bounds'] is False and
          type(report['pipe_eof']) is dict and set(report['pipe_eof']) == {'stdout', 'stderr'} and
          all(x is True for x in report['pipe_eof'].values()) and report['cleanup_errors'] == [], 'Unsuccessful supervision declaration')
    elapsed, total = report['execution_elapsed_seconds'], report['total_elapsed_seconds']
    check(all(type(x) in (int, float) and math.isfinite(x) and x >= 0 for x in (elapsed, total)) and
          elapsed < limits['timeout_seconds'] and total >= elapsed, 'Supervision timing')
    for name, size in (('stdout', stdout_size), ('stderr', stderr_size)):
        for prefix in ('retained', 'observed'):
            count = report[prefix + '_' + name + '_bytes']
            check(type(count) is int and count == size, 'Supervision stream counts')
    check(stdout_size + stderr_size <= limits['max_output_bytes'], 'Supervision output cap')


def outer_envelope(value, extra):
    common = {'schema_version', 'method', 'brand', 'status', 'role', 'agent_visible', 'scientific_validation'}
    need(type(value) is dict and set(value) == common | set(extra), 'Outer envelope fields', 'EP-VERIFY-03')
    need(type(value['schema_version']) is int and value['schema_version'] == 1 and value['method'] == 'tether.engine_presentation.v1' and
         value['brand'] == 'TETHER' and value['status'] == 'completed' and value['role'] == 'evaluation_only' and
         value['agent_visible'] is False and value['scientific_validation'] == 'not_established', 'Outer envelope scope', 'EP-VERIFY-03')


def verify_outer(output, anchor, trusted_runtime, *, expected_policy=None):
    output = no_links(output); deadline = time.monotonic() + 300
    check = lambda value, message: need(value, message, 'EP-VERIFY-03')
    check(not (output / 'tether-failure.json').exists(), 'Retained failure cannot be success')
    receipt, raw = json_file(output / 'tether-receipt.json', deadline, NORMAL)
    receipt_sha = hashlib.sha256(raw).hexdigest()
    if anchor is not None: check(pin(anchor) == receipt_sha, 'External outer receipt anchor differs')
    outer_envelope(receipt, {'manifest_sha256', 'journal_sha256', 'engine_receipt_sha256'})
    manifest, raw = json_file(output / 'tether-manifest.json', deadline, NORMAL)
    check(hashlib.sha256(raw).hexdigest() == receipt['manifest_sha256'], 'Manifest bytes differ')
    outer_envelope(manifest, {'command', 'invocation_sha256', 'engine', 'projection', 'launcher', 'artifacts', 'process_limits', 'supervision', 'artifact_policy'})
    if expected_policy is not None:
        need((manifest['artifact_policy'] is not None) == expected_policy,
             'Requested policy variant differs from actual sealed surface', 'EP-WIRE-01')
    check(type(manifest['process_limits']) is dict and set(manifest['process_limits']) == {'timeout_seconds', 'max_output_bytes'}, 'Process limits fields')
    limits = validate_process_limits(manifest['process_limits'])
    check(manifest['command'] in ('run', 'demo') and manifest['engine'] == dict(path='engine', receipt_sha256=receipt['engine_receipt_sha256']), 'Engine identity binding')
    check(type(trusted_runtime) is dict and type(trusted_runtime.get('schema_version')) is int and trusted_runtime['schema_version'] == 1 and
          trusted_runtime.get('versions') == {'tether': '0.5.1', 'asof': '0.3.12'}, 'Trusted current runtime required')
    from .independent_runtime import launcher_proof
    check(canonical(manifest['launcher']) == canonical(launcher_proof(trusted_runtime)), 'Launcher identity differs from current installed runtime')
    pin(manifest['invocation_sha256'])
    check(manifest['projection'] == dict(source='engine/dossier.md', target='dossier.md', transform='exact_first_header_v1'), 'Projection declaration')
    check(type(manifest['artifacts']) is dict, 'Outer artifact inventory')
    expected = set(manifest['artifacts']) | {'tether-manifest.json', 'tether-receipt.json', 'attempt/journal.jsonl'}
    files, directories = file_inventory(output)
    expected_dirs = {p.as_posix() for name in expected for p in Path(name).parents if p.as_posix() != '.'}
    check(files == expected and directories == expected_dirs, 'Whole outer inventory differs')
    for name, proof in manifest['artifacts'].items():
        # Inventory hashing is streamed without imposing metadata's size cap on
        # ledgers or arbitrary retained assets; individual parsers apply theirs.
        observed = stable(secure_path(output, name), deadline, collect=False)
        check(canonical(dict(path=name, **observed)) == canonical(proof), 'Outer artifact bytes/size/path differ')
    payload = stable(output / 'attempt/journal.jsonl', deadline, NORMAL)
    check(hashlib.sha256(payload).hexdigest() == receipt['journal_sha256'], 'Outer journal hash differs')
    events = chain(payload); binding = manifest['artifact_policy']
    schedule = ['run_reserved', 'tether_prepared'] + (['artifact_policy_prepared'] if binding is not None else []) + ['engine_dispatch', 'engine_returned', 'tether_completed']
    check([e['event'] for e in events] == schedule and all(type(e['sequence']) is int for e in events), 'Outer journal schedule')
    check(events[-1]['details'] == dict(manifest_sha256=receipt['manifest_sha256'], engine_receipt_sha256=receipt['engine_receipt_sha256']), 'Outer final event')
    prepared = dict(command=manifest['command'], launcher_proof_sha256=digest(manifest['launcher']), process_limits=limits, artifact_policy_requested=binding is not None)
    dispatched = dict(argv_sha256=manifest['invocation_sha256'], output='engine', process_limits=limits)
    returned = dict(returncode=0, supervision=manifest['supervision'])
    check(canonical(events[1]['details']) == canonical(prepared) and canonical(events[-3]['details']) == canonical(dispatched) and
          canonical(events[-2]['details']) == canonical(returned), 'Outer journal proof/dispatch differs')
    stdout = stable(output / 'engine-stdout.txt', deadline, NORMAL)
    stderr = stable(output / 'engine-stderr.txt', deadline, NORMAL)
    supervision(manifest['supervision'], limits, len(stdout), len(stderr))
    source = stable(output / 'engine/dossier.md', deadline, LARGE)
    projected = stable(output / 'dossier.md', deadline, LARGE)
    check(source.startswith(b'# AsOf dossier:') and projected == b'# TETHER dossier:' + source[len(b'# AsOf dossier:'):], 'Dossier presentation differs')
    for name in ('journal.jsonl', 'trace.jsonl'): stable(output / 'engine' / name, deadline, NORMAL)
    engine = verify_core(output / 'engine', receipt['engine_receipt_sha256'], trusted_runtime=trusted_runtime)
    check(engine['semantic_consistency'] == 'verified' and engine.get('code_matches_current') is True and engine['status'] == 'completed', 'Inner source/current-code/completion qualification')
    if binding is None:
        check(not (output / 'catalog-policy').exists(), 'Unbound policy directory')
        policy = dict(status='unavailable_schema1_compatibility', scientific_validation='not_established')
    else:
        check(canonical(events[2]['details']) == canonical(dict(binding=binding)), 'Policy preparation event differs')
        policy = verify_binding(output, binding, deadline)
    return {**engine, 'verification': dict(status='integrity_verified', receipt_sha256=receipt_sha,
        external_anchor_checked=anchor is not None, launcher_code_verified=True, source_binding='current_originals',
        semantic_consistency='verified', artifact_policy=policy, scientific_validation='not_established')}


def inspect_outer(output):
    output = no_links(output); deadline = time.monotonic() + 300
    events, failure = [], None
    journal_error = None
    if (output / 'attempt/journal.jsonl').is_file():
        try: events = chain(stable(output / 'attempt/journal.jsonl', deadline, NORMAL), partial=True)
        except (PolicyError, OSError): journal_error = 'invalid_or_unreadable_journal'
    if (output / 'tether-failure.json').is_file(): failure, _ = json_file(output / 'tether-failure.json', deadline, NORMAL)
    result = dict(brand='TETHER', kind='outer_attempt', durable_events=len(events), last_event=events[-1]['event'] if events else None,
        journal_inspection_error=journal_error, receipt_present=(output / 'tether-receipt.json').is_file(), failure=failure,
        recovery_action='inspect only; never automatically repeat this attempt')
    if (output / 'engine/journal.jsonl').is_file():
        try:
            inner = chain(stable(output / 'engine/journal.jsonl', deadline, NORMAL), partial=True)
            attempts = {}
            measured = dict(input_tokens=0, output_tokens=0, cost_usd=0)
            estimated = dict(measured)
            for event in inner:
                details = event['details']
                if event['event'] == 'dispatch': attempts[details['attempt_id']] = details
                elif event['event'] == 'attempt_accounted':
                    attempts.pop(details['attempt_id'], None)
                    totals = measured if details['basis'] == 'adapter_reported' else estimated
                    for key in totals: totals[key] += details['usage'][key]
            for attempt in attempts.values():
                for key in estimated: estimated[key] += attempt['reserved'][key]
            result['engine'] = dict(schema_version=2, last_event=inner[-1]['event'], durable_events=len(inner),
                unresolved_attempts=list(attempts), measured_usage=measured, estimated_upper_usage=estimated,
                receipt_present=(output / 'engine/receipt.json').is_file(),
                recovery_action='inspect only; never automatically repeat unresolved calls')
        except (PolicyError, OSError, KeyError, ValueError): result['engine'] = dict(inspection_error='invalid_or_unreadable_journal')
    return result


def validate_policy_bundle(root, request, *, scratch_dir=None):
    operation = request['operation']
    if operation == 'prepare_run': return prepare_policy(root, request, scratch_dir)
    output = child(root, request['paths']['run_dir'])
    if operation == 'inspect_run': return dict(recovery=inspect_outer(output))
    trusted_path = request['paths'].get('trusted_runtime')
    need(trusted_path, 'Pinned runtime manifest required for outer verification', 'EP-VERIFY-03')
    trusted, _ = json_file(child(root, trusted_path), time.monotonic() + 300, NORMAL)
    return verify_outer(output, request.get('anchors', {}).get('receipt_sha256'), trusted,
                        expected_policy=request['variant'] == 'artifact_policy_v2')
