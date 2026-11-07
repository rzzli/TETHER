"""Gate evaluator-only technical restoration behind a sealed origin universe.

This restores a database and performs structural audits with an empty cohort query.
It cannot open labels, establish ascertainment or activate clinical evaluation.
"""
from pathlib import Path

from tether_engine.journal import RunJournal
from tether_engine.serde import ContractError, safe_child, sha256_file, write_json
from tools.science.reference_panel import read_bound_json


def validate_gate(origin, decision):
    if (origin.get('status') != 'sealed_mapping_qualified_reconstructed_exploratory' or
            origin.get('origin_at') != '2025-01-01T00:00:00Z' or
            origin.get('horizon_at') != '2026-01-01T00:00:00Z' or
            origin.get('selection_sealed') is not True or origin.get('mapping_qualified') is not True or
            origin.get('reconstructed_origin_information_eligible') is not True or
            origin.get('endpoint_rows_queried') != 0):
        raise ContractError('Endpoint restore needs the sealed historical-mapping origin revision')
    if any(origin.get(k) is not False for k in ('clinical_ready','clinical_locked',
            'strict_dataset_availability_qualified','registry_completeness_qualified','origin_date_qualified')):
        raise ContractError('Exploratory reconstruction cannot claim a strict or locked clinical cohort')
    if (decision.get('mode') != 'reconstructed_exploratory' or
            decision.get('technical_restore_only') is not True or
            decision.get('endpoint_cohort_queries_allowed') is not False or
            decision.get('clinical_activation_allowed') is not False):
        raise ContractError('Restore decision must explicitly withhold labels and clinical activation')


def verify_origin_closure(origin_path, expected_sha256):
    """Validate every declared ancestor, including historical raw inputs/receipts."""
    from tools.science.historical_inputs import verify_manifest
    pins,active={},set()
    def pin(proof):
        path=Path(proof['path']).resolve();expected=proof['sha256']
        if path in pins and pins[path]!=expected:raise ContractError('Conflicting origin ancestor identity')
        if (sha256_file(path)!=expected or
                ('bytes' in proof and path.stat().st_size!=proof['bytes'])):
            raise ContractError('Changed transitive origin ancestor')
        pins[path]=expected
        return path
    def visit(path,expected):
        path=Path(path).resolve()
        if path in active:raise ContractError('Origin ancestry cycle')
        value,digest=read_bound_json(path,expected);pins[path]=digest;active.add(path)
        if (value.get('origin_at')!='2025-01-01T00:00:00Z' or
                value.get('selection_sealed') is not True or value.get('endpoint_rows_queried')!=0):
            raise ContractError('Unsealed or post-endpoint origin ancestor')
        for proof in value.get('files',[])+value.get('source_receipts',[]):
            receipt=pin(proof)
            if receipt.name=='archive-inspection.json':
                archive,_=read_bound_json(receipt,proof['sha256'])
                # Earlier validated restoration receipts used sha256/bytes.
                archive_hash=archive.get('archive_sha256',archive.get('sha256'))
                archive_bytes=archive.get('archive_bytes',archive.get('bytes'))
                if not archive_hash or archive_bytes is None:
                    raise ContractError('Origin archive receipt lacks a complete byte commitment')
                pin({'path':archive['archive'],'sha256':archive_hash,'bytes':archive_bytes})
                for member in archive['members']:
                    extracted=safe_child(receipt.parent/'extracted',member['name'])
                    pin({'path':str(extracted),'sha256':member['sha256'],'bytes':member['bytes']})
        if value.get('parent_origin_seal'):
            proof=value['parent_origin_seal'];visit(proof['path'],proof['sha256'])
        if value.get('historical_mapping_manifest'):
            proof=value['historical_mapping_manifest']
            verified=verify_manifest(Path(proof['path']),expected_manifest_sha256=proof['sha256'])
            for ancestor in verified['ancestor_pins']:pin(ancestor)
        if value.get('reconstruction_rules_proof'):pin(value['reconstruction_rules_proof'])
        active.remove(path)
        return value
    origin=visit(origin_path,expected_sha256)
    return origin,pins


def restore(origin_path, origin_sha256, decision_path, decision_sha256, output, plan, *, executor=None):
    """Reserve a new output, verify exact artifacts, dispatch once, retain failures."""
    output = Path(output)
    journal = RunJournal(output,kind='build')
    stage='origin_gate'
    try:
        origin,origin_hash=read_bound_json(origin_path,origin_sha256)
        decision,decision_hash=read_bound_json(decision_path,decision_sha256)
        validate_gate(origin,decision)
        if decision.get('origin_seal_sha256') != origin_hash:
            raise ContractError('Restore route decision does not bind the exact origin seal')
        _,pins=verify_origin_closure(origin_path,origin_hash)
        pins[Path(decision_path)]=decision_hash
        if len(plan.get('snapshots',[]))!=1 or plan.get('frozen_nct_ids')!=[]:
            raise ContractError('Technical restoration requires one snapshot and an empty cohort')
        requested_date=plan['snapshots'][0].get('requested_date')
        if requested_date not in ('2026-01-01','2026-04-01'):
            raise ContractError('Unapproved technical snapshot date')
        archive=Path(plan['snapshots'][0]['archive'])
        archive_hash=plan.get('source_archive_sha256')
        if requested_date=='2026-04-01':
            if (decision.get('technical_snapshot_date')!=requested_date or
                    decision.get('snapshot_purpose')!='ascertainment' or
                    decision.get('ascertainment_at')!='2026-04-01T00:00:00Z'):
                raise ContractError('April restoration needs an exact ascertainment decision without cutoff extension')
            proof=plan.get('archive_qualification')
            if not isinstance(proof,dict) or not proof.get('path') or not proof.get('sha256'):
                raise ContractError('April archive requires a pinned qualification report')
            qualification_path=Path(proof['path'])
            qualification,qualification_hash=read_bound_json(qualification_path,proof['sha256'])
            source=qualification.get('archive',{})
            if (qualification.get('schema_version')!=1 or qualification.get('status')!='archive_qualification_passed' or
                    qualification.get('requested_date')!=requested_date or qualification.get('actual_dump_date')!=requested_date or
                    Path(source.get('path','')).resolve()!=archive.resolve() or source.get('sha256')!=archive_hash or
                    source.get('bytes')!=archive.stat().st_size):
                raise ContractError('April archive qualification does not match the requested original and date')
            pins[qualification_path]=qualification_hash
            for ancestor in qualification.get('proofs',[]):
                path=Path(ancestor['path'])
                if (sha256_file(path)!=ancestor['sha256'] or
                        ('bytes' in ancestor and path.stat().st_size!=ancestor['bytes'])):
                    raise ContractError('Changed archive qualification ancestor')
                pins[path]=ancestor['sha256']
        if not archive_hash or sha256_file(archive)!=archive_hash:
            raise ContractError('Endpoint archive differs from its prior qualification receipt')
        pins[archive]=archive_hash
        query=output/'empty-cohort.sql'
        query.write_text("SELECT '[]'::text;\n",encoding='utf-8')
        plan=dict(plan,frozen_cohort_query=str(query.resolve()),frozen_cohort_query_sha256=sha256_file(query))
        write_json(output/'gate.json',{'origin_seal_sha256':origin_hash,'decision_sha256':decision_hash,
            'mode':'reconstructed_exploratory','endpoint_cohort_rows_requested':0,'clinical_activation':False})
        write_json(output/'plan.json',plan)
        journal.append('build_stage',stage='technical_endpoint_restore',origin_sha256=origin_hash,
                       decision_sha256=decision_hash,endpoint_cohort_rows_requested=0)
        stage='technical_endpoint_restore'
        if executor is None:
            from tools.feasibility.restore_intermediate_aact import execute
            executor=execute
        executor(plan,output/'restore')
        for p,h in pins.items():
            if sha256_file(p)!=h:raise ContractError('Origin inputs changed during endpoint restoration')
        result={'schema_version':1,'role':'evaluation_only','status':'technical_restore_completed',
            'snapshot_date':requested_date,'snapshot_purpose':'ascertainment' if requested_date=='2026-04-01' else 'endpoint',
            'origin_seal_sha256':origin_hash,'decision_sha256':decision_hash,'endpoint_cohort_rows_queried':0,
            'clinical_activation':False,'ascertainment_qualified':False,'provider_spend_usd':0}
        write_json(output/'report.json',result)
        journal.append('build_completed',report_sha256=sha256_file(output/'report.json'))
        return result
    except BaseException as error:
        journal.fail(error,stage)
        write_json(output/'failure.json',{'status':'failed','stage':stage,'error_type':type(error).__name__,
            'error':str(error),'recovery':'Inspect only; no automatic retry or overwrite'})
        raise
    finally:
        journal.close()
