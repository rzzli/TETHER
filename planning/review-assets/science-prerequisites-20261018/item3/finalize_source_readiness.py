"""Retain the bounded Science3 input disposition after independent acceptance.

No database connection, endpoint search, model call or raw-data mutation occurs.
Scientific gate activation is explicitly separate from this task's completion.
"""
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from asof.serde import read_json, sha256_file, write_json
from tools.science.ascertainment_policy import version_eligibility
from tools.science.reference_panel import read_bound_json


def main():
    base=Path.cwd().resolve()
    item=base/'planning/review-assets/science-prerequisites-20261018/item3'
    now=datetime.now(timezone.utc).isoformat()
    terminal=read_json(item/'april-terminal-validation.json')
    verification_path=Path(terminal['full_verification_report']['path'])
    full,_=read_bound_json(verification_path,terminal['full_verification_report']['sha256'])
    assert full['status']=='independent_terminal_acceptance_passed'
    assert full['snapshot_date']=='2026-04-01' and full['endpoint_cohort_rows_queried']==0
    assert full['server_stopped'] and not full['owned_port_listening']
    assert full['technical_checks']['identifier_exceptions']==[]
    restore=Path(full['restore_root'])
    audit_path=restore/'restore/2026-04-01/technical-audit.json'
    audit_proof=next(p for p in full['proofs'] if Path(p['path']).resolve()==audit_path.resolve())
    audit,_=read_bound_json(audit_path,audit_proof['sha256'])
    assert sum(t['rows'] for t in audit['tables'])==full['technical_checks']['total_rows']
    origin=base/'data/benchmark/cohorts/science-origin-20250101-20261018T173340Z/mapping-r1/origin-freeze.json'
    origin_data,_=read_bound_json(origin,'8622c4896796489e0d34c9359ccdbc3a1ad0eb1778541e173e0ab34ff7cd26e8')
    assert origin_data['selection_sealed'] and not origin_data['clinical_ready']
    assert origin_data['endpoint_rows_queried']==0
    peer_path=item/'origin-review-adjudication-validation.json'
    peer=read_json(peer_path)
    assert peer['status']=='passed_bounded_origin_source_adjudication_validation'
    assert peer['issues']=={} and peer['final_small_artifact_rehash']['status']=='passed'
    assert peer['case_memberships_checked']==12 and peer['original_prior_comparisons_checked']==20
    for key in ('full_evaluator_report','evaluator_notes','initial_review_seal','pack_freeze'):
        ref=peer[key]
        read_bound_json(Path(ref['path']),ref['sha256']) if key!='evaluator_notes' else None
        assert sha256_file(Path(ref['path']))==ref['sha256']
    pack=base/'data/benchmark/cohorts/science-origin-review-20261018T210300Z'
    adjud_path=pack/'adjudication/assessments.json'
    adjud,_=read_bound_json(adjud_path,'ab02cd61911d903e155438efa20c18452d8025b3d3097417277a0e56a7a0ffab')
    assert len(adjud['assessments'])==12 and adjud['counts']['prior_comparison_count']==20
    assert adjud['counts']['clinical_labels_assigned']==0
    assert not adjud['clinical_ready'] and not adjud['followup_sources_read']
    assert all(not c['clinical_ready'] and c['clinical_labels']==[] and c['origin_member_retained']
               and c['label_linkage_status']=='unresolved_pending_complete_scope_temporal_and_prior_risk_qualification'
               for c in adjud['assessments'])
    jan=read_json(item/'endpoint-terminal-validation.json')
    assert jan['status']=='independent_terminal_acceptance_passed'
    assert jan['technical_checks']['snapshot_date']=='2026-01-01'
    assert jan['server_stopped'] and jan['endpoint_cohort_rows_queried']==0
    for name in ('april-final-code-validation.json','april-core-code-validation.json'):
        result=read_json(item/name)
        assert result['status']=='passed' and result['tests']['run']==402
    ci=read_json(base/'data/derived/science-prerequisites-20261018/hosted-195d7d6.json')
    assert ci['conclusion']=='success' and len(ci['jobs'])==4
    assert all(j['conclusion']=='success' for j in ci['jobs'])

    def proof(path):
        path=Path(path)
        return {'path':str(path.relative_to(base)) if path.is_relative_to(base) else str(path),
                'sha256':sha256_file(path)}

    dates=[]
    for row in audit['study_date_ranges']:
        if row['column'] not in ('study_first_posted_date','last_update_posted_date','results_first_posted_date'):
            continue
        dates.append({**row,'latest_date_disposition':version_eligibility(
            last_update_posted_date=row['max'],cutoff_at='2026-04-01T00:00:00Z')})
    report={'schema_version':1,'created_at_utc':now,'role':'evaluation_only',
        'status':'bounded_input_readiness_qualified','science_stage':'science_3','task_complete':True,
        'completion_scope':'Four historical mapping projections, sealed reconstructed origin universe, two evaluator snapshots and explicit temporal/coverage disposition; not clinical predictor, label or scoring qualification',
        'historical_mapping_scope':{'release':'24.09','products':['targets','diseases','molecule','mechanismOfAction'],
            'original_files':805,'projected_rows':115821,'complete_scoring_evidence_bundle':False,
            'biological_prediction_features_admitted':0,'current_annotation_fallback':False},
        'origin_scope':{'sealed_candidate_scopes':origin_data['programs'],
            'membership_unchanged':True,'route':'reconstructed_exploratory','strict_historical_qualification':False,
            'qualified_clinical_programs':0,'reviewed_distinct_trials':12,'prior_rows_reviewed':20,
            'discovery_ready':9,'discovery_unresolved':3,'exact_clinical_linkage_unresolved':12,
            'global_prior_risk_unknown':12,'clinical_labels_assigned':0},
        'source_snapshots':[
            {'snapshot_date':'2026-01-01','technical_checks':jan['technical_checks'],
             'source_archive_sha256':jan['source_archive_sha256'],'source_archive_bytes':jan['source_archive_bytes']},
            {'snapshot_date':'2026-04-01','technical_checks':full['technical_checks'],
             'source_archive_sha256':full['source_archive_sha256'],'source_archive_bytes':full['source_archive_bytes']}],
        'temporal_coverage':{'origin_at':'2025-01-01T00:00:00Z','event_horizon_at':'2026-01-01T00:00:00Z',
            'ascertainment_at':'2026-04-01T00:00:00Z','reporting_allowance_days':90,
            'reporting_allowance_completeness_qualified':False,'strict_utc_publication_times_qualified':False,
            'source_date_audit':dates,'per_record_eligible_count':None,
            'per_record_count_reason':'Aggregate date audit is not a per-record eligibility census; March31 versions are held under the frozen offset-envelope rule',
            'whole_world_registry_completeness_qualified':False,'no_record_negative_admission':False,
            'separate_annotations':'Record posting dates do not date independent AACT enrichments or unverified result revisions'},
        'remaining_scientific_gates':{'G03_historical_predictors':False,'G04_outcomes':False,
            'G05_power_precision':False,'G07_training_calibration':False,'clinical_locked':False},
        'resources':{k:full[k] for k in ('restore_elapsed_seconds','import_elapsed_seconds',
            'acceptance_elapsed_seconds','retained_bytes','peak_memory_bytes','peak_memory_reason')},
        'free_disk_bytes_at_report':{drive:shutil.disk_usage(drive+':/').free for drive in ('D','E')},
        'capacity_scope':'Measured pilot/input work only; not a capacity claim for the full requirements inventory',
        'validation':{'full_tests':402,'core_expected_skips':52,'hosted_jobs_passed':4,
            'source_evidence_files':full['evidence_files_verified'],'origin_ancestor_pins':full['ancestor_pins_reverified']},
        'next_stage_preconditions':['Freeze an evaluator-only extraction/review/search protocol before endpoint cohort queries',
            'Keep all origin members and source holds; resolve endpoint-specific scope/risk or retain null labels',
            'Separate start/enrollment,dosing and clinical-success facts; source/public/event dates remain distinct',
            'Only admitted origin-valid features and pre-test-available labels could support later fitting'],
        'endpoint_cohort_rows_queried':0,'clinical_activation':False,'probabilities':'remain null',
        'provider_spend_usd':0,'executed_builder':proof(Path(__file__).resolve()),
        'proofs':[proof(p) for p in (item/'april-terminal-validation.json',item/'endpoint-terminal-validation.json',
            item/'april-input-scope-amendment.json',item/'input-stage-qualification-boundary.json',peer_path,
            item/'april-final-code-validation.json',item/'april-core-code-validation.json',adjud_path,
            pack/'initial-review-seal.json',pack/'pack-audit-final.json',origin)]}
    # The review validator itself is a scoped source-integrity assessment, not a truth label.
    assert peer.get('clinical_activation',False) is False
    write_json(item/'source-readiness-report.json',report)
    public={'schema_version':1,'created_at_utc':now,'dataset_id':'aact_snapshots','role':'evaluation_only',
        'snapshot_requested_date':'2026-04-01','dump_creation_date':'2026-04-01',
        'status':'technical_restore_and_independent_acceptance_passed','public_availability_at':None,
        'public_availability_reason':'Dump timezone/exact public release time unknown; conditional per-version date bounds only',
        'source_archive_sha256':full['source_archive_sha256'],'source_archive_bytes':full['source_archive_bytes'],
        'technical_checks':full['technical_checks'],'retained_workspace_bytes_excluding_original_archive':full['retained_bytes'],
        'elapsed_seconds':full['restore_elapsed_seconds'],'peak_memory_bytes':None,
        'peak_memory_reason':full['peak_memory_reason'],'empty_cohort_records':0,'server_stopped':True,
        'ascertainment_qualified':False,'clinical_activation':False,'scientific_validation':'not_established',
        'proof':proof(item/'april-terminal-validation.json'),'provider_spend_usd':0}
    write_json(base/'data/manifests/public/2026-10-18-aact-ascertainment-technical.json',public)
    print('Science3 bounded source-readiness report and scoped technical manifest retained')


if __name__=='__main__':
    main()
