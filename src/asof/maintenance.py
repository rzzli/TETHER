"""Offline manifest publication and the single validated catalog update entry point."""
from __future__ import annotations

import argparse
import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .atomic import publish_bytes
from .serde import ContractError, encode, read_json, safe_child, sha256_file, write_json


def write_new_json(path: Path, value) -> None:
    """Publish complete bytes atomically without replacing an existing report."""
    payload = (json.dumps(encode(value), indent=2, ensure_ascii=False, allow_nan=False)+'\n').encode('utf-8')
    publish_bytes(path, payload)


def validate_catalog(catalog):
    if catalog.get('schema_version') != 1:
        raise ContractError('Unsupported catalog schema')
    providers = [row['provider_id'] for row in catalog['providers']]
    datasets = [row['dataset_id'] for row in catalog['datasets']]
    if len(set(providers)) != len(providers) or len(set(datasets)) != len(datasets):
        raise ContractError('Duplicate catalog identity')
    graph = {}
    for row in catalog['datasets']:
        if row['provider_id'] not in providers:
            raise ContractError('Unknown provider')
        refs = row.get('dependencies', [])
        if not set(refs + row.get('overlap', {}).get('dataset_ids', [])).issubset(datasets):
            raise ContractError('Unknown dependency/overlap')
        for group in row.get('conditional_input_groups', []):
            if not set(group.get('dataset_ids', [])).issubset(datasets):
                raise ContractError('Unknown conditional dependency')
        if not set(row['roles']).issubset({'agent_evidence', 'reference', 'evaluation_only', 'comparison_only'}):
            raise ContractError('Invalid catalog role')
        for field in ('collection_status', 'parse_status', 'validation_status'):
            if row[field] not in catalog['status_definitions'][field]:
                raise ContractError('Invalid catalog status')
        graph[row['dataset_id']] = refs
    def visit(key, visiting, done):
        if key in visiting:
            raise ContractError('Catalog dependency cycle')
        if key in done:
            return
        for parent in graph[key]:
            visit(parent, visiting | {key}, done)
        done.add(key)
    done = set()
    for key in graph:
        visit(key, set(), done)


def acquisition_report(project: Path, raw_root: Path, queues: list[Path], catalog: Path):
    """Read receipts and originals; no catalog, transport or monitor mutation."""
    policy = read_json(catalog)
    validate_catalog(policy)
    ids = {row['dataset_id'] for row in policy['datasets']}
    grouped, seen = {}, set()
    for queue_path in queues:
        queue = read_json(queue_path)
        for row in queue['files']:
            key = (row['dataset_id'], row['relative_path'].replace('\\', '/'))
            if key in seen:
                raise ContractError('Duplicate dataset/path across acquisition queues')
            seen.add(key)
            if row['dataset_id'] not in ids:
                raise ContractError('Unknown acquisition dataset')
            item = grouped.setdefault(row['dataset_id'], {'expected_files': 0, 'completed_files': 0,
                'in_progress_files': 0, 'completed_bytes': 0, 'release_ids': set(), 'batch_ids': set()})
            item['expected_files'] += 1
            item['release_ids'].add(row['release_id'])
            item['batch_ids'].add(queue['batch_id'])
            source = safe_child(raw_root, row['relative_path'])
            receipt_path = safe_child(raw_root, 'manifests/receipts/'+row['receipt_id']+'.json')
            if receipt_path.is_file():
                receipt = read_json(receipt_path)
                if receipt.get('status') == 'completed':
                    if (not source.is_file() or receipt.get('dataset_id') != row['dataset_id'] or
                        receipt.get('release_id') != row['release_id'] or
                        safe_child(raw_root, receipt.get('relative_path', '')) != source or
                        receipt.get('bytes') != source.stat().st_size or receipt.get('sha256') != sha256_file(source)):
                        raise ContractError('Completed acquisition receipt does not match original')
                    item['completed_files'] += 1
                    item['completed_bytes'] += source.stat().st_size
            if source.with_name(source.name+'.partial').exists():
                item['in_progress_files'] += 1
    return {'schema_version': 1, 'kind': 'acquisition', 'created_at_utc': datetime.now(timezone.utc),
        'timezone': 'America/Los_Angeles', 'scope': 'Selected queues; original bytes and receipt identity checked; no parsing/scientific claim',
        'datasets': [{'dataset_id': key, **{k: sorted(v) if isinstance(v, set) else v for k,v in item.items()}}
                     for key,item in sorted(grouped.items())]}


def checked_product_reports(project, report):
    docs = {}
    for key in ('build_report', 'pilot_report', 'source_review'):
        ref = report[key]
        if set(ref) != {'path', 'sha256'}:
            raise ContractError('Invalid normalization report reference')
        path = safe_child(project, ref['path'])
        if sha256_file(path) != ref['sha256']:
            raise ContractError('Normalization report hash mismatch')
        docs[key] = read_json(path)
    build, pilot, audit = (docs[key] for key in ('build_report','pilot_report','source_review'))
    if (build['status'] != 'built' or build['blocked_cases'] or pilot['status'] != 'completed' or
        pilot['build_report_sha256'] != report['build_report']['sha256'] or
        pilot['source_review_sha256'] != report['source_review']['sha256'] or
        len(build['cases']) != 10 or len(pilot['cases']) != 10 or audit['distinct_original_rows'] < 20):
        raise ContractError('Incomplete normalization evidence')
    if {x['case_id'] for x in build['cases']} != {x['case_id'] for x in pilot['cases']}:
        raise ContractError('Pilot/build case mismatch')
    case_ids = {x['case_id'] for x in pilot['cases']}
    audit_ids = {(x['source_id'], x['row_group'], x['row']) for x in audit['rows']}
    if (len(case_ids) != 10 or {x['case_id'] for x in audit['cases']} != case_ids or
        len(audit_ids) != len(audit['rows']) or len(audit_ids) != audit['distinct_original_rows']):
        raise ContractError('Incomplete or duplicated source audit')
    for item in pilot['cases']:
        if item['status'] != 'verified' or item['verification']['semantic_consistency'] != 'verified':
            raise ContractError('Unverified pilot case')
        # Use the report's own project-relative directory, never its private run_dir.
        run = safe_child(project, str(Path(report['pilot_report']['path']).parent / item['case_id']))
        if sha256_file(run/'receipt.json') != item['receipt_sha256']:
            raise ContractError('Pilot receipt anchor mismatch')
        receipt = read_json(run/'receipt.json')
        for name,digest in {**receipt['outputs'], **receipt.get('auxiliary_outputs',{})}.items():
            if sha256_file(safe_child(run,name)) != digest:
                raise ContractError('Pilot output integrity mismatch')
    return build, pilot, audit


def update_catalog(project: Path, catalog_path: Path, report_path: Path, expected_sha256: str):
    project, catalog_path, report_path = project.resolve(), catalog_path.resolve(), report_path.resolve()
    if not report_path.is_relative_to(project/'data/manifests/public'):
        raise ContractError('Catalog proposals must be sanitized public manifests')
    lock = catalog_path.with_name(catalog_path.name+'.lock')
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise ContractError('Catalog is locked; inspect owner before retrying') from error
    try:
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(json.dumps({'pid': os.getpid(), 'created_at_utc': datetime.now(timezone.utc).isoformat()}))
            stream.flush(); os.fsync(stream.fileno())
        if sha256_file(catalog_path) != expected_sha256:
            raise ContractError('Stale catalog proposal; expected prior hash differs')
        catalog = read_json(catalog_path)
        validate_catalog(catalog)
        updated = copy.deepcopy(catalog)
        report = read_json(report_path)
        report_sha = sha256_file(report_path)
        reference = report_path.relative_to(project).as_posix()
        if report.get('schema_version') != 1:
            raise ContractError('Unsupported maintenance report')
        rows = {row['dataset_id']: row for row in updated['datasets']}
        changed = []
        if report.get('kind') == 'acquisition':
            allowed = {'dataset_id','expected_files','completed_files','in_progress_files','completed_bytes','release_ids','batch_ids'}
            for item in report['datasets']:
                if set(item) != allowed or item['dataset_id'] not in rows or item['dataset_id'] in changed:
                    raise ContractError('Invalid acquisition fields or dataset')
                for name in ('expected_files','completed_files','in_progress_files','completed_bytes'):
                    if type(item[name]) is not int or item[name] < 0:
                        raise ContractError('Invalid acquisition count')
                for name in ('release_ids', 'batch_ids'):
                    if (not isinstance(item[name], list) or not item[name] or
                        any(not isinstance(value, str) or not value.strip() for value in item[name]) or
                        len(set(item[name])) != len(item[name])):
                        raise ContractError('Invalid acquisition release/batch identities')
                if item['expected_files'] == 0 or max(item['completed_files'],item['in_progress_files']) > item['expected_files']:
                    raise ContractError('Inconsistent acquisition counts')
                row = rows[item['dataset_id']]
                if row['provider_id'] == 'project':
                    raise ContractError('Transport cannot update generated products')
                status = ('collected' if item['completed_files']==item['expected_files'] else
                          'partial' if item['completed_files'] else 'downloading' if item['in_progress_files'] else 'queued')
                row['collection_status'] = status
                row['acquisition_snapshot'] = {**item, 'status': status, 'report': reference, 'report_sha256': report_sha,
                    'scope': report['scope'], 'created_at_utc': report['created_at_utc']}
                changed.append(item['dataset_id'])
        elif report.get('kind') == 'normalization':
            if set(report) != {'schema_version','kind','created_at_utc','build_report','pilot_report','source_review'}:
                raise ContractError('Invalid normalization proposal fields')
            build,pilot,audit = checked_product_reports(project, report)
            row = rows['asof_normalized_packets']
            missing_count = len(build['inspection']['missing_inputs'])
            row.update(collection_status='collected', parse_status='parsed', validation_status='not_run')
            row['verification'] = {'level': 'sample_inspected','checked_at': str(report['created_at_utc'])[:10],
                'evidence': [{'kind':'scoped_normalization','workspace_path': reference,'sha256':report_sha,
                    'result':'Ten finalized contemporary cases; 20-row technical audit and source-inclusive semantic verification; scientific validation not run'}],
                'next_acquisition_check':('Independent biological review; resolve selected-subset missing inputs before broader claims'
                    if missing_count else 'Independent biological review; selected-manifest completeness does not establish biological coverage')}
            row['blockers'] = ([f"{missing_count} frozen inputs missing; no absence-of-evidence inference"]
                               if missing_count else []) + ['Independent scientific validation not run']
            row['storage']['expanded_bytes'] = sum(x['packet_bytes'] for x in build['cases'])
            row['storage']['estimate_basis'] = 'Measured ten-case normalized JSON packets only; build intermediates, run outputs, originals and backups excluded'
            row['release_policy'] = 'Pinned build '+build['snapshot_id']+'; full input lineage and UTC origin retained; no historical eligibility claim'
            changed.append(row['dataset_id'])
        elif report.get('kind') == 'status_correction':
            allowed_report = {'schema_version','kind','created_at_utc','scope','evidence','datasets'}
            if set(report) != allowed_report or not report['evidence'] or not report['datasets']:
                raise ContractError('Invalid status correction proposal')
            for proof in report['evidence']:
                if set(proof) != {'path','sha256'}:
                    raise ContractError('Invalid correction evidence')
                source = safe_child(project, proof['path'])
                if sha256_file(source) != proof['sha256']:
                    raise ContractError('Correction evidence changed')
            for item in report['datasets']:
                if (set(item) != {'dataset_id','collection_status','verification','blockers'} or
                    item['dataset_id'] not in rows or item['dataset_id'] in changed):
                    raise ContractError('Invalid correction fields or dataset')
                row = rows[item['dataset_id']]
                # Corrections may describe an idle/incomplete collection; they
                # cannot promote acquisition, parsing, science or access policy.
                if (item['collection_status'] != row['collection_status'] and
                    item['collection_status'] not in {'partial','blocked','failed'}):
                    raise ContractError('Status correction cannot promote collection')
                verification = item['verification']
                if (not isinstance(verification, dict) or
                    set(verification) != {'level','checked_at','evidence','next_acquisition_check'} or
                    verification['level'] not in catalog['status_definitions']['verification_level'] or
                    not isinstance(verification['evidence'],list) or not verification['evidence'] or
                    not isinstance(item['blockers'],list) or
                    any(not isinstance(value,str) for value in item['blockers'])):
                    raise ContractError('Invalid status correction verification')
                for key in ('collection_status','verification','blockers'):
                    row[key] = copy.deepcopy(item[key])
                changed.append(item['dataset_id'])
        else:
            raise ContractError('Unsupported maintenance report kind')
        updated['last_updated'] = datetime.now(timezone.utc).date().isoformat()
        updated['last_maintenance_update'] = {'expected_prior_sha256': expected_sha256, 'report':reference,
            'report_sha256': report_sha,'kind':report['kind'],'datasets':changed,
            'created_at_utc':datetime.now(timezone.utc).isoformat()}
        validate_catalog(updated)
        if sha256_file(report_path) != report_sha:
            raise ContractError('Proposal changed during update')
        if sha256_file(catalog_path) != expected_sha256:
            raise ContractError('Catalog changed outside the maintenance lock')
        write_json(catalog_path, updated)
        return {'catalog_sha256':sha256_file(catalog_path),'updated_datasets':changed,'report_sha256':report_sha}
    finally:
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    inspect = commands.add_parser('inspect-transport')
    inspect.add_argument('--raw-root',type=Path,required=True)
    inspect.add_argument('--queue',type=Path,action='append',required=True)
    inspect.add_argument('--output',type=Path,required=True)
    update = commands.add_parser('update-catalog')
    update.add_argument('--report',type=Path,required=True)
    update.add_argument('--expected-sha256',required=True)
    for sub in (inspect,update):
        sub.add_argument('--project-root',type=Path,default=Path.cwd())
        sub.add_argument('--catalog',type=Path,required=True)
    args = parser.parse_args()
    if args.command == 'inspect-transport':
        if args.output.exists():
            raise ContractError('Report already exists; choose a fresh output')
        report = acquisition_report(args.project_root,args.raw_root,args.queue,args.catalog)
        write_new_json(args.output,report)
        print(json.dumps({'report':str(args.output),'sha256':sha256_file(args.output)}))
    else:
        print(json.dumps(update_catalog(args.project_root,args.catalog,args.report,args.expected_sha256)))


if __name__ == '__main__':
    main()
