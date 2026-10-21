"""Fixed-member evaluator follow-up, with explicit source and publication gates."""
from __future__ import annotations

from pathlib import Path

from asof.serde import ContractError, read_json, sha256_file
from asof.journal import read_chain
from tools.science.reference_panel import read_bound_json
from tools.science.outcome_inputs import study_query, schema_from_audit, validate_study_rows, parse_jsonl
from tools.science.outcome_results import results_query, validate_result_rows
from tools.science.ascertainment_policy import version_eligibility

ROOT=Path(__file__).resolve().parents[2]
POLICY=ROOT/'planning/protocols/endpoint-followup-feasibility-v0.1.json'
PACK_SHA='005db13e5d51f595fa5849d72b3d495e12cad797c20a632db511be85ba514ac6'
PARENT_POLICY_SHA='8a34bb1c596f737f3f8242c8c9975a6d3ffae14d834f79cdc1ca1b789bb27808'
READINESS_SHA='1b9932918621b8e88c53956fb57ece05d6ff5bea89757b695c717f71a0709e17'
DATES=['2026-01-01','2026-04-01']


def require(condition,message):
    if not condition:raise ContractError(message)


def validate_endpoint_binding(plan):
    from tools.science.outcome_extract import check_pins,APPROVED_BASE,APPROVED_RESTORES
    policy_pin=plan['followup_policy']
    require(Path(policy_pin['path']).resolve()==POLICY.resolve(),'Wrong endpoint follow-up policy path')
    policy,_=read_bound_json(POLICY,policy_pin['sha256'])
    required={'protocol_id':'endpoint-followup-feasibility-v0.1','role':'evaluation_only',
        'origin_pack_sha256':PACK_SHA,'parent_protocol_sha256':PARENT_POLICY_SHA,
        'origin_readiness_sha256':READINESS_SHA,'source_snapshots':DATES,
        'query_names':['studies','results'],'max_rows_per_trial':100000,
        'max_output_bytes_per_query':128*1024*1024,'automatic_labels':False,'clinical_activation':False,
        'provider_spend_usd':0}
    require(all(policy.get(k)==v and type(policy.get(k)) is type(v) for k,v in required.items()),
        'Follow-up policy differs from bounded source-only scope')
    require(all(plan[k]==policy[k] for k in ('origin_at','horizon_at','ascertainment_at')),'Wrong follow-up chronology')
    selection=plan['selection'];readiness=plan['origin_readiness']
    require(selection['sha256']==PACK_SHA and readiness['sha256']==READINESS_SHA,'Wrong frozen origin sample/readiness')
    pack,_=read_bound_json(Path(selection['path']),PACK_SHA)
    review,_=read_bound_json(Path(readiness['path']),READINESS_SHA)
    require(pack['selected_distinct_trials']==12 and pack['clinical_labels_assigned']==0 and
        pack['followup_sources_read'] is False and pack['clinical_ready'] is False,'Origin sample qualification differs')
    check_pins(pack['files']+pack['direct_parents']+pack['ancestor_pins'])
    packets=[]
    for pin in pack['files']:
        if Path(pin['path']).parent.name=='packets':
            packet,_=read_bound_json(Path(pin['path']),pin['sha256']);packets.append(packet)
    members=[p['origin_scope']['nct_id'] for p in packets]
    require(len(members)==len(set(members))==12 and plan['nct_ids']==sorted(members),
        'Follow-up membership differs from sealed twelve')
    require(review['pack_freeze']['sha256']==PACK_SHA and review['followup_sources_read'] is False and
        [m['nct_id'] for m in review['members']]==members and review['membership_modified'] is False,
        'Origin readiness membership or exposure differs')
    # All prior executing code is verified through immutable archived pack files.
    # Do not re-apply nested old plans' live-code pins to the new runtime.
    required_parents=[policy_pin,selection,readiness]+pack['files']+pack['direct_parents']+pack['ancestor_pins']
    parent_keys={(Path(p['path']).resolve(),p['sha256']) for p in plan['parents']}
    require(all((Path(p['path']).resolve(),p['sha256']) in parent_keys for p in required_parents),
        'Incomplete origin sample/readiness parent closure')
    require([j['snapshot_date'] for j in plan['jobs']]==DATES,'Wrong follow-up sources/order')
    for job in plan['jobs']:
        date=job['snapshot_date'];root=Path(job['restore_root']).resolve()
        require(root==(APPROVED_BASE/APPROVED_RESTORES[date]).resolve(),'Unapproved follow-up restored path')
        check_pins(job['pins']);pins={Path(p['path']).resolve():p for p in job['pins']}
        for name in ('extracted/postgres.dmp','archive-inspection.json','dump-toc-pg17.txt','technical-audit.json','setup.py'):
            require(root/name in pins,'Missing original follow-up restored-source proof')
        inspection,_=read_bound_json(root/'archive-inspection.json',pins[root/'archive-inspection.json']['sha256'])
        require(next(m for m in inspection['members'] if m['name']=='postgres.dmp')['sha256']==pins[root/'extracted/postgres.dmp']['sha256'],
            'Follow-up dump differs from original archive inspection')
        audit,_=read_bound_json(root/'technical-audit.json',pins[root/'technical-audit.json']['sha256'])
        require(audit['status']=='completed' and audit['study_id_check']['rows']==job['expected_studies'],
            'Wrong follow-up source inventory')
        require([q['name'] for q in job['queries']]==['studies','results'],'Wrong or reordered follow-up query scope')
        schema=schema_from_audit(audit)
        expected=[study_query(members,date,schema,max_ids=12),results_query(members,date,schema,max_rows_per_trial=100000)]
        for query,request in zip(job['queries'],expected):
            require(query['request']==request and Path(query['path']).read_text(encoding='utf-8')==request['sql'],
                'Follow-up query differs from exact frozen membership/schema/recipe')
    return policy


def join_snapshot(study_rows,result_rows,study_request,result_request):
    """Revalidate both original projections; held rows remain quarantined observations."""
    require(study_request['snapshot_date']==result_request['snapshot_date'] and
        study_request['nct_ids']==result_request['nct_ids'],'Metadata/results request identities differ')
    studies=validate_study_rows(study_rows,study_request)
    results=validate_result_rows(result_rows,result_request)
    by_study={r['study']['nct_id']:r for r in study_rows};by_result={r['study']['nct_id']:r for r in result_rows}
    require(set(by_study)==set(by_result),'Metadata/results source membership differs')
    sd={d['nct_id']:d for d in studies['version_dispositions']}
    rd={d['nct_id']:d for d in results['version_dispositions']}
    joined=[]
    for nct in study_request['nct_ids']:
        if nct not in by_study:
            joined.append({'nct_id':nct,'status':'missing_both_source_envelopes','clinical_label':None,'absence_claim':False});continue
        sr=by_study[nct];rr=by_result[nct]
        common=set(sr['study'])&set(rr['study'])
        require(all(sr['study'][k]==rr['study'][k] for k in common),'Metadata/results shared source version differs')
        reasons=[]
        for kind,disposition in (('metadata',sd[nct]),('results',rd[nct])):
            if disposition['version_eligibility']['status']!='eligible_reconstructed_date_bound':
                reasons.append(kind+':'+disposition['version_eligibility']['status'])
        populated=any(rr[t] for t in rr if t!='study')
        if populated:
            posted=rr['study'].get('results_first_posted_date')
            if str(rr['study'].get('results_first_posted_date_type','')).strip().upper()!='ACTUAL':
                reasons.append('results:held_unqualified_first_results_posting_type')
            available=version_eligibility(last_update_posted_date=posted,
                first_posted_date=rr['study'].get('study_first_posted_date'),cutoff_at=result_request['cutoff_at'])
            if available['status']!='eligible_reconstructed_date_bound':
                reasons.append('results:first_posting:'+available['status'])
        joined.append({'nct_id':nct,'status':'eligible_context_only' if not reasons else 'held_source_context',
            'holds':reasons,'metadata_version':sd[nct]['version_eligibility'],'results_version':rd[nct]['version_eligibility'],
            'reported_results_observed':bool(rr['outcomes']),'result_rows':rd[nct]['result_rows'],
            'table_counts':rd[nct]['table_counts'],'clinical_label':None,'absence_claim':False,
            'decision_date_inferred':False,'scope_qualified':False})
    return {'schema_version':1,'status':'joined_source_context_pending_adjudication','role':'evaluation_only',
        'snapshot_date':study_request['snapshot_date'],'members':joined,'missing_nct_ids':studies['missing_nct_ids'],
        'studies_validation':studies,'results_validation':results,'clinical_labels_assigned':0,'clinical_activation':False}


def verify_extraction(output,plan_sha256,report_sha256):
    """Check retained execution against caller-supplied plan and report commitments."""
    output=Path(output).resolve();report_path=output/'report.json'
    require(sha256_file(report_path)==report_sha256,'Extraction report differs from external commitment')
    plan_path=output/'effective-plan.json';require(sha256_file(plan_path)==plan_sha256,'Effective plan differs')
    from tools.science.outcome_extract import check_pins,validate_plan
    plan=read_json(plan_path);report=read_json(report_path);validate_plan(plan)
    validate_endpoint_binding(plan);check_pins(plan['parents'])
    require(report['phase']=='endpoint_followup' and report['protocol_sha256']==plan_sha256 and
        report['status']=='source_reads_complete_pending_scientific_validation' and report['role']=='evaluation_only' and
        report['provider_spend_usd']==0 and report['clinical_labels_assigned']==0 and
        report['clinical_activation'] is False,'Wrong follow-up execution scope')
    pinned=[]
    def retain(path):
        pinned.append({'path':str(path),'sha256':sha256_file(path),'bytes':path.stat().st_size})
    for path in (plan_path,report_path,output/'journal.jsonl',output/'executed-code-proofs.json',output/'executed-runner.py'):
        retain(path)
    events=read_chain(output/'journal.jsonl')
    require(events[-1]['event']=='build_completed' and events[-1]['details']['report_sha256']==report_sha256,
        'No matching terminal follow-up journal')
    archived=read_json(output/'executed-code-proofs.json')
    require(len(archived)==len(plan['executed_code']) and
        {p['source']['path'] for p in archived}=={p['path'] for p in plan['executed_code']},'Archived runtime closure differs')
    for p in archived:
        source=Path(p['source']['path']).resolve()
        require(source.is_relative_to(ROOT) and Path(p['archive_path']).resolve()==output/'executed-code'/source.relative_to(ROOT),
            'Archived executing source path differs')
        require(p['source'] in plan['executed_code'] and p['sha256']==p['source']['sha256'] and
            sha256_file(Path(p['archive_path']))==p['sha256'],'Archived executing source differs')
        retain(Path(p['archive_path']))
    runner=next(p for p in plan['executed_code'] if Path(p['path']).resolve()==ROOT/'tools/science/outcome_extract.py')
    require(sha256_file(output/'executed-runner.py')==runner['sha256'],'Archived runner copy differs')
    require([s['snapshot_date'] for s in report['snapshots']]==DATES,'Wrong extraction report snapshots')
    joined=[]
    for snapshot,job in zip(report['snapshots'],plan['jobs']):
        folder=output/job['snapshot_date'];life=read_json(folder/'lifecycle.json')
        require(life['ownership_acquired'] is True and life['server_stopped'] is True and
            life['port']==job['port'] and life['automatic_retry'] is False,'Incomplete owned source cleanup')
        metadata=read_json(folder/'metadata.stdout.log')
        require(metadata==snapshot['metadata'] and metadata['database']=='aact_snapshot' and metadata['read_only']=='on' and
            metadata['studies']==job['expected_studies'] and metadata['port']==str(job['port']) and
            Path(metadata['directory']).resolve()==Path(job['restore_root']).resolve()/'pgdata',
            'Recorded source identity/read-only state differs')
        for path in (folder/'lifecycle.json',folder/'metadata.stdout.log'):retain(path)
        require([q['name'] for q in snapshot['queries']]==['studies','results'],'Wrong reported query identities')
        raw=[]
        for committed,query in zip(snapshot['queries'],job['queries']):
            first=folder/(query['name']+'-first.stdout.log');repeat=folder/(query['name']+'-repeat.stdout.log')
            require(Path(committed['path']).resolve()==first and committed['sha256']==sha256_file(first) and
                committed['bytes']==first.stat().st_size and committed['repeat_identical'] is True and
                first.read_bytes()==repeat.read_bytes() and first.stat().st_size<=128*1024*1024,
                'Source read bytes differ from committed repeat output')
            retain(first);retain(repeat)
            raw.append(parse_jsonl(first.read_text(encoding='utf-8')))
        joined_snapshot=join_snapshot(*raw,*[q['request'] for q in job['queries']])
        for name,key in (('studies','studies_validation'),('results','results_validation')):
            path=folder/(name+'-validation.json')
            require(read_json(path)==joined_snapshot[key],'Saved validation differs from source reconstruction')
            retain(path)
        joined.append(joined_snapshot)
    check_pins(pinned+plan['parents'])
    require(sha256_file(report_path)==report_sha256 and sha256_file(plan_path)==plan_sha256,
        'Extraction commitment changed during verification')
    return joined
