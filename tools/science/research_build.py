"""Durable, explicitly granted OT24.09/25.09 development-view qualification.

This is an offline research build, not production agent admission or a frozen
scientific evaluation. The caller must independently select both request and use
grant hashes. All old collection roles are retained in the new provenance.
"""
import argparse
from collections import Counter
import hashlib
from pathlib import Path
import platform
import time

from tether_engine.atomic import publish_bytes
from tether_engine.ingest import peak_memory_bytes
from tether_engine.journal import RunJournal, parse_chain
from tether_engine.provenance import catalog_index, check_role
from tether_engine.serde import ContractError, canonical, fingerprint, parse_json
from tether_engine.source_access import SourceAccess, local_path, selected_root
from tether_engine.study.proofs import _no_links
from tether_engine.temporal import utc_instant
from tools.science.qualify_source_bytes import qualify
from tools.science.source_receipts import conservative_utc_bound
from tools.science.research_mapping import build_index
from tools.science.research_parquet import stream_rows
from tools.science.research_views import build_views, FIELDS, SOURCES

MAX_VIEW_BYTES = 64*1024**2


def _need(condition, message):
    if not condition: raise ContractError(message)


def pipeline_code():
    """Exact maintained implementation inventory, separate from source inputs."""
    from tether_engine import atomic, journal, serde, source_access, temporal
    from tools.science import (research_mapping, research_parquet, research_views, source_receipts,
                               qualify_source_bytes, historical_inputs, temporal_dates, temporal_inventory)
    modules = (atomic, journal, serde, source_access, temporal, research_mapping, research_parquet,
               research_views, source_receipts, qualify_source_bytes, historical_inputs, temporal_dates, temporal_inventory)
    result = {module.__name__: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest() for module in modules}
    engine_root = Path(atomic.__file__).parent
    result.update({'engine/'+path.relative_to(engine_root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in engine_root.rglob('*.py')})
    result['tools.science.research_build'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return result


def build(request_path, expected_request_sha256, output, *, expected_grant_sha256, source_roots):
    started = time.monotonic(); deadline = started+600
    request_path, output = local_path(request_path), local_path(output)
    access = SourceAccess(tuple(selected_root(root) for root in source_roots))
    _no_links(output.parent)
    if output.exists() or output.is_symlink(): _no_links(output)
    journal = RunJournal(output, kind='build')
    consumed = 0; maximum = 512*1024**2; stage = 'controls'; failure = None

    def generated(name, limit=64*1024**2):
        path = output/name
        own = SourceAccess((selected_root(output),)).prepare([path], deadline=deadline)
        return own.read(path, limit)

    def check_child(directory, payload_name, hash_field):
        payload = generated(directory+'/'+payload_name)
        seal = parse_json(generated(directory+'/terminal-seal.json'))
        events = parse_chain(generated(directory+'/journal.jsonl'))
        _need(seal[hash_field] == hashlib.sha256(payload).hexdigest() and
              events[-1]['sha256'] == seal['journal_head'], 'Child build seal or journal differs')
        return payload

    def remaining_seconds():
        value = deadline-time.monotonic()
        if value <= 0: raise TimeoutError('Research build deadline exceeded')
        return value

    def load(reference):
        nonlocal consumed
        _need(type(reference) is dict and set(reference) == {'path', 'sha256'}, 'Invalid pinned build reference')
        path = local_path(reference['path'])
        _need(not path.is_relative_to(output), 'Build output overlaps a declared input')
        prepared = access.prepare([path], deadline=deadline)
        size = prepared.identities[path][2]
        _need(size <= min(16*1024**2, maximum-consumed), 'Build control exceeds input-byte budget')
        raw = prepared.read(path, 16*1024**2); consumed += len(raw)
        _need(hashlib.sha256(raw).hexdigest() == reference['sha256'], 'Pinned build input hash differs')
        return parse_json(raw), raw

    try:
        journal.append('build_stage', stage=stage)
        journal.append('research_build_started', request_sha256=expected_request_sha256,
                       independently_selected_grant_sha256=expected_grant_sha256)
        request, request_bytes = load(dict(path=str(request_path), sha256=expected_request_sha256))
        _need(type(request) is dict and set(request) == {'schema_version', 'kind', 'decision_origin', 'grant',
                                                       'catalog', 'source_screen', 'mapping_manifest', 'hypotheses', 'pipeline_sha256'} and
              type(request.get('schema_version')) is int and request['schema_version'] == 1 and
              request.get('kind') == 'tether_development_three_views',
              'Unsupported research build request')
        _need(request['grant']['sha256'] == expected_grant_sha256, 'Grant differs from independent caller anchor')
        grant, grant_bytes = load(request['grant'])
        _need(grant.get('status') == 'approved' and grant.get('permission_applied') is True and
              grant.get('requested_input_role') == 'reference' and
              grant.get('production_admission_changes') is False and grant.get('new_downloads') is False and
              grant.get('provider_spend_usd') == 0 and grant.get('approval', {}).get('answer') == 'Approve this isolated research use',
              'Explicit isolated research-use approval required')
        _need(request['decision_origin'] == grant['decision_origin'] == '2025-01-01T00:00:00Z',
              'Research origin differs from approved scope')
        code = pipeline_code()
        _need(fingerprint(code) == request.get('pipeline_sha256'), 'Research pipeline fingerprint differs')
        catalog, catalog_bytes = load(request['catalog'])
        products = catalog_index(catalog)
        for product in ('ot_evidence', 'ot_target', 'ot_disease', 'ot_release_inputs'):
            check_role(product, 'reference', products)
        screen, _ = load(request['source_screen'])
        _need(request['source_screen']['sha256'] == grant['source_screen_sha256'], 'Source screen differs from grant')
        mapping_manifest, _ = load(request['mapping_manifest'])
        _need(request['mapping_manifest']['sha256'] == grant['mapping_manifest_sha256'], 'Mapping manifest differs from grant')
        requested_originals = grant.get('evidence_originals')
        mapping_originals = grant.get('mapping_originals')
        _need(type(requested_originals) is list and 0 < len(requested_originals) <= 2000 and
              type(mapping_originals) is list and 0 < len(mapping_originals) <= 1000,
              'Bounded complete grant inventory required')
        permitted = {str(local_path(row['path'])): row for row in requested_originals}
        _need(len(permitted) == len(requested_originals), 'Duplicate granted original')
        selected = []
        for row in screen['files']:
            path = str(local_path(row['path']))
            if path not in permitted: continue
            declared = permitted[path]
            for key in ('sha256', 'bytes', 'release', 'source', 'receipt_path', 'receipt_sha256', 'receipt_role', 'url'):
                _need(row.get(key) == declared.get(key), 'Granted evidence identity differs: '+key)
            _need(row['release'] in ('24.09', '25.09') and row['source'] in SOURCES,
                  'Clinical or unsupported research partition denied')
            directory = 'output/etl/parquet/evidence/' if row['release'] == '24.09' else 'output/evidence/'
            prefix = 'https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/'+row['release']+'/'+directory+'sourceId='+row['source']+'/'
            _need(row['url'].startswith(prefix) and row['url'][len(prefix):].startswith('part-') and
                  '/' not in row['url'][len(prefix):] and row['url'].endswith('.parquet'),
                  'Grant is not an original selected publisher partition')
            selected.append(row)
        _need(len(selected) == len(permitted) and len({row['path'] for row in selected}) == len(selected),
              'Grant/source-screen membership differs')
        _need({r['release'] for r in selected} == {'24.09', '25.09'}, 'Both release views are required')
        all_receipt_hashes = {row['receipt_sha256'] for row in screen['files']}
        selected_receipts = {row['receipt_sha256'] for row in selected}
        metadata = [row for row in screen['metadata_pins'] if row['sha256'] not in all_receipt_hashes or row['sha256'] in selected_receipts]
        actual_mapping = {}
        for row in mapping_manifest['files']:
            product = ('ot_target' if '/targets/' in row['source_url'] else
                       'ot_disease' if '/diseases/' in row['source_url'] else None)
            if product:
                actual_mapping[str(local_path(row['path']))] = dict(dataset_id=product, **{key: row[key] for key in
                    ('path', 'sha256', 'bytes', 'receipt_path', 'receipt_sha256', 'source_url')})
        expected_mapping = {str(local_path(row['path'])): row for row in mapping_originals}
        _need(len(expected_mapping) == len(mapping_originals) and actual_mapping == expected_mapping,
              'Granted mapping originals differ')
        for row in selected + mapping_originals:
            _need(not local_path(row['path']).is_relative_to(output), 'Build output overlaps original')
        publish_bytes(output/'request.json', request_bytes)
        publish_bytes(output/'grant.json', grant_bytes)
        publish_bytes(output/'catalog.json', catalog_bytes)
        publish_bytes(output/'code-fingerprints.json', canonical(code)+b'\n')
        plan = canonical(dict(files=selected, metadata_pins=metadata))+b'\n'
        publish_bytes(output/'selected-source-screen.json', plan)
        plan_hash = hashlib.sha256(plan).hexdigest()
        stage = 'source_qualification'
        journal.append('build_stage', stage=stage)
        journal.append('source_qualification_reserved', files=len(selected), bytes=sum(r['bytes'] for r in selected),
                       selected_source_screen_sha256=plan_hash)
        _need(maximum-consumed-len(plan) > 0, 'No remaining source qualification budget')
        inspected = qualify(output/'selected-source-screen.json', plan_hash, output/'source-inspection',
                            source_roots=(*source_roots, output), max_bytes=maximum-consumed-len(plan),
                            seconds=remaining_seconds(), inspect_parquet=True, inspect_receipts=True)
        consumed += inspected['total_bytes_hashed']+len(plan)
        journal.append('build_progress', stage=stage, files_verified=inspected['files_verified'], input_bytes=consumed)
        stage = 'mapping_membership'
        journal.append('build_stage', stage=stage)
        journal.append('mapping_membership_reserved', originals=len(mapping_originals))
        mapping = build_index(local_path(request['mapping_manifest']['path']), request['mapping_manifest']['sha256'],
                              output/'mapping-membership', source_roots=source_roots,
                              max_bytes=maximum-consumed, seconds=remaining_seconds())
        consumed += sum(value for key, value in mapping['resource_counts'].items() if key.endswith('_bytes_hashed'))
        mapping_raw = check_child('mapping-membership', 'index.json', 'index_sha256')
        _need(len(mapping_raw) <= maximum-consumed, 'Mapping output read exceeds remaining input budget')
        consumed += len(mapping_raw)
        mapping_hash = hashlib.sha256(mapping_raw).hexdigest()
        _need(parse_json(mapping_raw) == mapping, 'Mapping child report changed')
        journal.append('build_progress', stage=stage, canonical_rows=mapping['source_rows'], input_bytes=consumed)
        hypotheses = request.get('hypotheses')
        _need(type(hypotheses) is list and 0 < len(hypotheses) <= 10000, 'Bounded hypotheses required')
        for case in hypotheses:
            _need(case['target_id'] in mapping['indices']['targets'] and case['indication_id'] in mapping['indices']['diseases'],
                  'Hypothesis canonical identifier missing from pinned mapping')
            _need(case['target_namespace_version'] == 'OpenTargets:24.09:targets' and
                  case['indication_namespace_version'] == 'OpenTargets:24.09:diseases',
                  'Hypothesis namespace differs from the pinned identifier tables')
        source_nodes, parents = [], []
        def source_id(url, digest): return fingerprint(dict(url=url, sha256=digest))
        for row in mapping['ancestors']:
            identity = source_id(row['source_url'], row['sha256']); parents.append(identity)
            purpose = 'identifier_mapping' if row['source_url'].endswith('.parquet') else 'release_proof'
            source_nodes.append(dict(artifact_id=identity, sha256=row['sha256'], release='24.09', role='reference',
                                     purpose=purpose, available_by=mapping['available_by'], parents=[], datasource=None))
        source_nodes.append(dict(artifact_id='mapping-index', sha256=mapping_hash, release='24.09', role='reference',
                                 purpose='identifier_mapping', available_by=mapping['available_by'], parents=parents, datasource=None))
        receipts = {row['receipt_sha256']: row for row in inspected['receipts']}
        views = {'archived': [], 'current_filtered': [], 'current_unfiltered': []}
        descriptors = []; provenance = []
        for row in selected:
            proof = receipts[row['receipt_sha256']]
            identity = source_id(row['url'], row['sha256'])
            by = mapping['available_by'] if row['release'] == '24.09' else conservative_utc_bound(proof['retrieved_at'])
            source_nodes.append(dict(artifact_id=identity, sha256=row['sha256'], release=row['release'], role='reference',
                                     purpose='nonclinical_evidence', available_by=by, parents=['mapping-index'], datasource=row['source']))
            descriptors.append(dict(artifact_id=identity, path=row['path'], sha256=row['sha256'], bytes=row['bytes']))
            for view in (('archived',) if row['release'] == '24.09' else ('current_filtered', 'current_unfiltered')):
                views[view].append(identity)
            provenance.append(dict(artifact_id=identity, **proof, new_use_role='reference',
                                    new_use_grant_sha256=expected_grant_sha256,
                                    availability_basis='archived_release_upper_bound' if row['release'] == '24.09' else 'public_download_upper_bound'))
        frame = dict(schema_version=1, view_policy_id='p11-development-three-views.v1', decision_origin=request['decision_origin'],
                     hypotheses=hypotheses, method_sha256=request['pipeline_sha256'], sources=source_nodes, views=views,
                     filter_field='publicationDate', max_rows=1000000, max_selected_rows=100000)
        frame_raw = canonical(frame)+b'\n'; publish_bytes(output/'frame.json', frame_raw)
        publish_bytes(output/'source-provenance.json', canonical(provenance)+b'\n')
        stage = 'view_projection'; stats = {}
        journal.append('build_stage', stage=stage)
        journal.append('view_projection_started', frame_sha256=fingerprint(frame),
                       hypotheses=len(hypotheses), original_files=len(selected))
        iterator = stream_rows(descriptors, hypotheses, expected_descriptors_sha256=fingerprint(descriptors),
                               source_roots=source_roots, max_bytes=maximum-consumed,
                               seconds=remaining_seconds(), stats=stats)
        def observed_batches():
            last_progress = time.monotonic()
            for batch in iterator:
                if time.monotonic()-last_progress >= 1:
                    journal.append('build_progress', stage=stage, **dict(stats))
                    last_progress = time.monotonic()
                yield batch
        observed = observed_batches()
        projection_failure = None
        try:
            result = build_views(frame, observed, expected_frame_sha256=fingerprint(frame))
        except BaseException as error:
            projection_failure = error
            raise
        finally:
            observed.close()
            try: iterator.close()
            except BaseException as cleanup:
                if projection_failure is None: raise
                projection_failure.add_note('Source iterator close: '+type(cleanup).__name__)
        consumed += stats['bytes_hashed']
        _need(stats['status'] == 'completed', 'Research source scan incomplete')
        for view in views:
            release = '24.09' if view == 'archived' else '25.09'
            expected_rows = sum(row['footer_rows'] for row in selected if row['release'] == release)
            _need(result['views'][view]['coverage']['physical_rows'] == expected_rows,
                  'View physical rows differ from qualified complete source set')
        _need(pipeline_code() == code, 'Pipeline code changed during research build')
        stage = 'publication'; files = {}
        journal.append('build_stage', stage=stage)
        for view, value in result['views'].items():
            value.update(integrity_verdict='source_receipt_schema_and_mapping_consistency_verified',
                         source_use_grant_sha256=expected_grant_sha256, scientific_validation='not_established',
                         scope='development_qualification_not_frozen_scientific_evaluation')
            raw = canonical(value)+b'\n'
            _need(len(raw) <= MAX_VIEW_BYTES, 'Research view exceeds 64 MiB packet limit')
            filename = view+'.json'; publish_bytes(output/filename, raw)
            files[filename] = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        _need(parse_json(check_child('source-inspection', 'report.json', 'report_sha256')) == inspected,
              'Source inspection child report changed')
        _need(parse_json(check_child('mapping-membership', 'index.json', 'index_sha256')) == mapping,
              'Mapping child report changed')
        for name in ('request.json', 'grant.json', 'catalog.json', 'code-fingerprints.json', 'frame.json', 'source-provenance.json',
                     'selected-source-screen.json', 'source-inspection/report.json', 'source-inspection/terminal-seal.json',
                     'source-inspection/journal.jsonl', 'mapping-membership/index.json',
                     'mapping-membership/terminal-seal.json', 'mapping-membership/journal.jsonl'):
            raw = generated(name); files[name] = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
        report = dict(schema_version=1, status='development_three_view_build_complete',
                      request_sha256=expected_request_sha256, independently_selected_grant_sha256=expected_grant_sha256,
                      frame_sha256=fingerprint(frame), pipeline_sha256=request['pipeline_sha256'], outputs=files,
                      coverage={view: value['coverage'] for view, value in result['views'].items()},
                      temporal_verdicts={view: value['temporal_verdict'] for view, value in result['views'].items()},
                      preserved_collection_roles=dict(Counter(str(row['collection_role']) for row in provenance)),
                      source_scan=stats, measured_input_bytes_hashed_or_read=consumed,
                      elapsed_seconds=time.monotonic()-started, peak_memory_bytes=peak_memory_bytes(),
                      python_version=platform.python_version(), pyarrow_version='21.0.0',
                      original_roles_changed=False, production_admission_changed=False, provider_spend_usd=0,
                      scientific_validation='not_established', independent_replay='required_before_P11_acceptance',
                      limitations=['Archive-version availability relies on retained publisher provenance, not independent proof of unchanged FTP history.',
                                   'Modern download bounds are not first-publication dates.',
                                   'These are development hypotheses; no labels, calibrated predictions or P15 evaluation.'])
        raw = canonical(report)+b'\n'; publish_bytes(output/'report.json', raw)
        journal.append('build_progress', stage=stage, coverage=report['coverage'], input_bytes=consumed)
        digest = hashlib.sha256(raw).hexdigest(); last = journal.append('build_completed', report_sha256=digest)
        journal.seal(canonical(dict(schema_version=1, report_sha256=digest, journal_head=last['sha256'])),
                     name='terminal-seal.json', deadline=deadline)
        return report
    except BaseException as error:
        failure = error
        try: journal.fail(error, stage)
        except BaseException as secondary: error.add_note('Research failure journal: '+type(secondary).__name__)
        raise
    finally:
        try: journal.close()
        except BaseException as secondary:
            if failure is None: raise
            failure.add_note('Research journal close: '+type(secondary).__name__)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--request-sha256', required=True)
    parser.add_argument('--grant-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, action='append', required=True)
    args = parser.parse_args()
    report = build(args.request.absolute(), args.request_sha256, args.output.absolute(),
                   expected_grant_sha256=args.grant_sha256, source_roots=tuple(args.source_root))
    print(canonical({key: report[key] for key in ('status', 'coverage', 'temporal_verdicts', 'elapsed_seconds', 'peak_memory_bytes')}).decode())


if __name__ == '__main__': main()
