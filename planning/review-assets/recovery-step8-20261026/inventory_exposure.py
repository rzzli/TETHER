"""R08 evaluator-only metadata inventory. Never read source/evaluator payloads.

Reads exact case.json files and explicitly named control manifests only. Ancestor
snapshot.json descriptors are metadata; referenced evidence is never followed.
This draft cannot establish all-repository freshness or independently validated IDs.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'planning/review-assets/recovery-step8-20261026'
CACHE=ROOT/'data/cache/recovery-step8-exposure-20261026'
INITIAL=ROOT/'planning/decisions/2026-10-26-exposure-register.json'
PACK=ROOT/'data/derived/science2-fresh-20261018T170501Z/case-pack.json'
PROPOSAL=ROOT/'planning/review-assets/science-prerequisites-20261018/item2/fresh-case-proposals.json'
VB=ROOT/'data/derived/virtual-biotech-compatibility-20261018-resume01'
SPECIAL={INITIAL,PACK,PROPOSAL,VB/'audit.json',VB/'evidence-manifest.json',VB/'README.md',
 ROOT/'runs/r07-native-diagnostic-20261026T165505Z/run-plan.json',
 ROOT/'runs/question-development-20261026T023832Z/run-plan.json',
 ROOT/'planning/review-assets/recovery-step5-20261026/paired-preflight-v2.json',
 ROOT/'src/asof/study/resources/synthetic-context-v1.json',
 ROOT/'src/asof/study/resources/synthetic-orientation-v1.json',
 OUT/'virtual-biotech-mapping-metadata-v1.json',
 CACHE/'virtual-biotech-identity-keys-v1.json'}
ROOTS=[ROOT/'runs',ROOT/'data/derived',ROOT/'src/asof/demo']
SKIP={'labels','gold_evidence','benchmark','__pycache__','executing-package','source-compiler-data','.git'}
READS={}
SKIPPED=[]

def protected(p):
    parts=[s.lower() for s in p.parts]
    return p.name.lower()=='normalized-outcomes.json' or any(s in SKIP or s.startswith('adjudication') for s in parts)

def relative(p):
    try:return p.relative_to(ROOT).as_posix()
    except ValueError:return str(p)

def proof(p, raw):
    return dict(path=relative(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))

def allowed(p):
    p=p.absolute()
    return (not protected(p) and (p in SPECIAL or p.name in ('case.json','snapshot.json') and any(p.is_relative_to(r) for r in ROOTS)))

def read(p, cap=4*1024*1024):
    p=p.absolute()
    assert allowed(p), 'Non-whitelisted content read: '+str(p)
    assert not p.is_symlink()
    for ancestor in [p,*p.parents]:
        assert not (getattr(ancestor.stat(),'st_file_attributes',0)&0x400), 'Reparse input'
    assert p.stat().st_size<=cap, 'Oversized metadata: '+str(p)
    raw=p.read_bytes()
    item=proof(p,raw)
    if relative(p) in READS: assert READS[relative(p)]==item
    READS[relative(p)]=item
    return json.loads(raw)

def audit(event,args):
    if event in ('socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'):
        raise AssertionError('No network/process work in exposure inventory')
    if event=='open' and isinstance(args[0],str):
        p=Path(args[0]).absolute()
        mode=args[1]
        writing=isinstance(mode,str) and any(c in mode for c in 'wax+')
        if not writing and p.suffix not in ('.pyc','.py'):
            assert allowed(p), 'Audit denied non-whitelisted read: '+str(p)

# All required stdlib imports precede this guard; no runtime/tool imports.
sys.addaudithook(audit)
initial=read(INITIAL)
pack=read(PACK)
proposal=read(PROPOSAL)
original_pin=READS[relative(INITIAL)]
entries=[]

def norm_id(value):
    if value is None:return None
    assert isinstance(value,str)
    value=value.strip().upper()
    return re.sub(r'^(EFO|MONDO|HP):',r'\1_',value)

def token(value):
    if value is None:return None
    assert isinstance(value,str)
    return re.sub(r'[\s-]+','_',value.strip().lower())

SNAPSHOTS={}
def source_metadata(casefile):
    path=casefile.parent/'snapshot.json'
    if not path.exists():return None
    if relative(path) in SNAPSHOTS:return SNAPSHOTS[relative(path)]
    try:
        snap=read(path)
        items=snap.get('artifacts',[])+snap.get('sources',[])
        datasets=sorted({i['dataset_id'] for i in items if isinstance(i,dict) and isinstance(i.get('dataset_id'),str)})
        partitions=set()
        artifact_roles=set()
        for item in items:
            if not isinstance(item,dict):continue
            if isinstance(item.get('role'),str):artifact_roles.add(item['role'])
            for field in ('path','source_url'):
                raw=item.get(field)
                if isinstance(raw,str):
                    match=re.search(r'(?:^|/)evidence/([^/]+)(?:/|$)',raw.replace('\\','/'))
                    if match:partitions.add(match.group(1).removeprefix('sourceId='))
        result=dict(snapshot_id=snap.get('snapshot_id'),profile=snap.get('profile'),dataset_ids=datasets,provider_evidence_partitions=sorted(partitions),artifact_roles=sorted(artifact_roles),proof=READS[relative(path)],interpretation='Declared descriptor families only; no evidence records read or source sufficiency inferred')
        SNAPSHOTS[relative(path)]=result
        return result
    except (AssertionError,ValueError,KeyError,TypeError) as error:
        SKIPPED.append(dict(path=relative(path),reason=type(error).__name__,details=str(error)))
        return None

def add_case(case, origin_path, kind, pointer=None, include_snapshot=False):
    assert isinstance(case,dict) and isinstance(case.get('hypothesis'),dict)
    h=case['hypothesis']
    fields=('target_id','indication_id','intended_action','modality','tissue','target_namespace_version','indication_namespace_version')
    permitted={k:h.get(k) for k in fields}
    for value in permitted.values(): assert value is None or isinstance(value,str)
    normalized=dict(target_id=norm_id(h.get('target_id')),indication_id=norm_id(h.get('indication_id')),intended_action=token(h.get('intended_action')),modality=token(h.get('modality')),tissue=token(h.get('tissue')))
    t=normalized['target_id'] or ''
    classification='synthetic_fixture' if t.startswith(('DEMO:','SYNTHETIC:','FIXTURE:')) else 'real_identifier_metadata' if re.fullmatch(r'ENSG\d+',t) else 'unresolved_identifier_class'
    program=case.get('program')
    program={k:program.get(k) for k in ('program_id','phase_at_origin','status_at_origin')} if isinstance(program,dict) else None
    item=dict(case_id=case.get('case_id'),task=case.get('task'),origin=case.get('origin'),origin_at=case.get('origin_at'),hypothesis=permitted,normalized_hypothesis=normalized,program_origin_metadata=program,classification=classification,exposure=kind,source_file=READS[relative(origin_path)],json_pointer=pointer,source_family_metadata=source_metadata(origin_path) if include_snapshot and classification=='real_identifier_metadata' else None)
    entries.append(item)

casefiles=[]
for root in ROOTS:
    for parent,dirs,files in os.walk(root,followlinks=False):
        dirs[:]=sorted(d for d in dirs if d.lower() not in SKIP and not d.lower().startswith('adjudication') and not Path(parent,d).is_symlink() and not getattr(Path(parent,d).stat(),'st_file_attributes',0)&0x400)
        if 'case.json' in files:
            p=Path(parent)/'case.json'
            if not protected(p):casefiles.append(p)
for path in sorted(casefiles):
    try:
        c=read(path,cap=256*1024)
        add_case(c,path,'prior_run_or_fixture_material' if path.is_relative_to(ROOT/'runs') else 'prior_project_preparation',include_snapshot=True)
    except (AssertionError,ValueError,KeyError,TypeError) as error:
        SKIPPED.append(dict(path=relative(path),reason=type(error).__name__,details=str(error)))
for index,c in enumerate(initial['cases']):add_case(c,INITIAL,'R01_declared_development_exposure',f'/cases/{index}')
for index,c in enumerate(pack['cases']):
    add_case(dict(case_id=c['case_id'],task='T6',hypothesis=dict(target_id=c['target_id'],indication_id=c['disease_id'],intended_action=c['intended_action'],modality=c['modality'],tissue=c.get('tissue'))),PACK,'previously_frozen_development_pack',f'/cases/{index}')
for name in ('synthetic-context','synthetic-orientation'):
    path=ROOT/f'src/asof/study/resources/{name}-v1.json'
    synthetic=read(path)
    add_case(synthetic['source_request']['case'],path,'packaged_explicit_synthetic', '/source_request/case')

# Run plans are control metadata only: follow no request, reference-seal, or outcome path.
r07path=ROOT/'runs/r07-native-diagnostic-20261026T165505Z/run-plan.json'
r07=read(r07path)
questionpath=ROOT/'runs/question-development-20261026T023832Z/run-plan.json'
question=read(questionpath)
r05path=ROOT/'planning/review-assets/recovery-step5-20261026/paired-preflight-v2.json'
r05=read(r05path)
assert len(r07['cells'])==6
exposure_events=[dict(event='R07_existing_native_development',control=READS[relative(r07path)],cells=[dict(case_id=c['case_id'],interface=c['interface'],source_kind=c['source_kind'],request_sha256=c['request']['sha256']) for c in r07['cells']],canonical_real_case_control=question['case'],prior_input_plan=READS[relative(questionpath)],paired_preflight=READS[relative(r05path)],scope='All IL6R derivatives and both synthetic fixtures remain development-exposed; no candidate contents read')]

vb_manifest=read(VB/'evidence-manifest.json')
vb_audit=read(VB/'audit.json')
readme=(VB/'README.md').read_bytes()
README_PROOF=proof(VB/'README.md',readme)
READS[relative(VB/'README.md')]=README_PROOF
assert next(p for p in vb_manifest['files'] if p['path']=='README.md')['sha256']==README_PROOF['sha256']
assert next(p for p in vb_manifest['files'] if p['path']=='audit.json')['sha256']==READS[relative(VB/'audit.json')]['sha256']
competitor=dict(repository=vb_audit['repository'],revision=vb_audit['revision'],status='published_case_keys_incomplete_quarantine',pinned_manifest=READS[relative(VB/'evidence-manifest.json')],pinned_audit=READS[relative(VB/'audit.json')],pinned_readme=README_PROOF,declared_dataset_paths=['datasets/clinical_trials/chembl_clinical_nct_data.parquet','datasets/clinical_trials/clinical_trial_labels_reconciled.csv'],local_mapping_filename='E:/projects_data/drug_target_agents_data/reference/vbt_linkage/71f9da6/chembl_clinical_nct_data.parquet',local_mapping_rows_read=False,clinical_labels_read=False,known_examples_from_R01=['CD276/B7-H3 and non-small cell lung carcinoma','OSMR and ulcerative colitis','published single-cell trial-feature analysis'],known_examples_independently_enumerated_from_pinned_case_table=False,limitation='Pinned compatibility artifact contains code/configuration/README metadata, not a complete published case-key inventory. Labels and linkage rows remain quarantined; filename presence does not qualify cases or reproduce benchmark.')

vb_summary=read(OUT/'virtual-biotech-mapping-metadata-v1.json')
vb_keys=read(CACHE/'virtual-biotech-identity-keys-v1.json',cap=8*1024*1024)
assert READS[relative(CACHE/'virtual-biotech-identity-keys-v1.json')]['sha256']==vb_summary['key_inventory']['sha256']
competitor.update(status='complete_local_mapping_keys_published_evaluated_subset_unresolved',mapping_projection=vb_summary,mapping_summary_proof=READS[relative(OUT/'virtual-biotech-mapping-metadata-v1.json')],limitation='All local mapping identity keys enumerated through three-column projection. Published evaluated-label subset, article vignette universe and single-cell keys remain unresolved; clinical columns and labels unread.',local_mapping_rows_read=True,local_mapping_projection_only=['targetId','diseaseId','nct_id'])
vb_pairs={(row['target_id'],row['indication_id']):row for row in vb_keys['keys']}
groups=defaultdict(list)
for item in entries:
    key=json.dumps(item['normalized_hypothesis'],sort_keys=True,separators=(',',':'))
    groups[key].append(item)
group_rows=[]
for key,items in sorted(groups.items()):
    dataset_ids=sorted({d for item in items for d in (item['source_family_metadata'] or {}).get('dataset_ids',[])})
    partitions=sorted({d for item in items for d in (item['source_family_metadata'] or {}).get('provider_evidence_partitions',[])})
    group_rows.append(dict(group_id=hashlib.sha256(key.encode()).hexdigest(),hypothesis=json.loads(key),classification=items[0]['classification'],occurrence_count=len(items),case_ids=sorted({i['case_id'] for i in items if isinstance(i['case_id'],str)}),tasks=sorted({i['task'] for i in items if isinstance(i['task'],str)}),namespace_versions=sorted({json.dumps({k:i['hypothesis'][k] for k in ('target_namespace_version','indication_namespace_version')},sort_keys=True) for i in items}),source_dataset_ids=dataset_ids,source_provider_partitions=partitions,freshness='not_eligible_as_fresh' if items[0]['classification']=='real_identifier_metadata' else 'synthetic_or_unresolved_not_a_fresh_real_case',occurrence_indexes=[entries.index(i) for i in items]))
for group in group_rows:
    h=group['hypothesis']
    member=vb_pairs.get((h['target_id'],h['indication_id']))
    group['virtual_biotech_mapping_membership']=dict(found=member is not None,mapping_rows=member['mapping_rows'] if member else None,distinct_trial_ids=member['distinct_trial_ids'] if member else None,published_evaluated_subset_membership='unresolved',meaning='Identity overlap only; no clinical values or action/modality/tissue inferred')
pairs=defaultdict(list)
for group in group_rows:pairs[(group['hypothesis']['target_id'],group['hypothesis']['indication_id'])].append(group['group_id'])
pair_rows=[dict(target_id=k[0],indication_id=k[1],hypothesis_group_ids=v,policy='Conservative target-indication family exclusion across action/modality/tissue variants; no biological synonym inference') for k,v in sorted(pairs.items(),key=lambda item:str(item[0]))]
classification=Counter(item['classification'] for item in entries)
summary=dict(discovered_case_files=len(casefiles),parsed_case_files=sum(1 for e in entries if e['json_pointer'] is None),case_metadata_occurrences=len(entries),unique_hypothesis_groups=len(group_rows),unique_real_hypothesis_groups=sum(g['classification']=='real_identifier_metadata' for g in group_rows),unique_target_indication_groups=len(pair_rows),unique_real_target_indication_groups=len({(g['hypothesis']['target_id'],g['hypothesis']['indication_id']) for g in group_rows if g['classification']=='real_identifier_metadata'}),classification_occurrences=dict(classification),snapshot_metadata_files=len(SNAPSHOTS),input_files_read=len(READS),skipped_metadata=len(SKIPPED),fresh_real_cases_qualified=0)
quarantine=[dict(scope='all existing clinical feasibility cohorts and labels',paths=['data/benchmark/cohorts','data/benchmark/labels','E:/projects_data/drug_target_agents_data/benchmark'],enumeration='family-level only; all protected payloads unread',reason='Prior clinical feasibility exposure and outcome access cannot qualify fresh cases here'),dict(scope='all gold/reference/AI adjudication and completed human forms',paths=['data/benchmark/gold_evidence','all adjudication directories','reference_seal targets'],enumeration='family-level only; no answer contents read',reason='Evaluator-only exposure must not be copied into agent-visible inputs'),dict(scope='all IL6R derivatives, orientation/reference preparation and source qualification',paths=['runs/question-development-20261026T023832Z','runs/r07-native-diagnostic-20261026T165505Z','research_notes/IL6R primary evidence qualification','docs/expert-review-20261026'],enumeration='known classes and run controls; not all reference-file contents read',reason='No IL6R variant or derivative treated as fresh'),dict(scope='published Virtual Biotech cases and single-cell analyses',enumeration='incomplete case keys; known R01 examples plus pinned metadata only',reason='Full published-case identity/exposure reconciliation pending'),dict(scope='cache/restore/checkpoint mirrors, tests, inline cases and nonstandard case containers',enumeration='not exhaustively parsed; packaged demos separately explicit synthetic',reason='No all-repository completeness assertion; dedicated metadata reconciliation needed before fresh selection')]
result=dict(schema_version=1,revision='R08-exposure-draft-v3',role='evaluation_only',agent_visible=False,purpose='Conservative exposure exclusion only; not scientific labels, admission or freshness certification',created_at_utc=datetime.now(timezone.utc).isoformat(),supersedes_for_expanded_coverage=original_pin,original_register_modified=False,complete=False,status='draft_partial_inventory',scoped_completeness=dict(whitelisted_case_files=True,local_virtual_biotech_mapping_identity_keys=True,all_project_exposure=False,published_evaluated_case_subset=False),summary=summary,normalization_policy=['Only identifier case/whitespace and EFO/MONDO/HP colon-to-underscore syntax normalized.','No symbol-to-ID, disease synonym, gene version or tissue equivalence inferred.','Action/modality/tissue tokens normalize case and separator spelling; null remains distinct from unspecified.','Hypothesis exposure groups ignore annotation-version differences conservatively while retaining all namespace versions.','Prior material existence establishes preparation/exposure exclusion, not successful dispatch or scientific review.'],inputs=list(READS.values()),case_metadata=entries,hypothesis_groups=group_rows,target_indication_groups=pair_rows,snapshot_metadata=list(SNAPSHOTS.values()),control_exposure_events=exposure_events,virtual_biotech=competitor,quarantined_classes=quarantine,skipped_metadata=SKIPPED,unresolved=['All 72,158 identity pairs in the receipt-matched local Virtual Biotech mapping are inventoried; the published evaluated-label subset and single-cell case keys remain unqualified.','Protected clinical/reference families are quarantined without reading labels or follow-up values.','Nonstandard case containers, source relationships, inline test/demo variants, and cache/restore mirrors are not exhaustively reconciled.','Source metadata is inventory only; no source sufficiency, chronology, reuse permission or alias-equivalence acceptance.','No fresh pool or reviewer domain coverage has been qualified.'],prohibited_access=dict(normalized_outcomes_contents_read=False,benchmark_label_payloads_read=False,gold_answers_read=False,clinical_followup_values_read=False,raw_source_records_read=False,model_outputs_read=False,new_network_or_model_calls=0))
assert read(INITIAL) and READS[relative(INITIAL)]==original_pin
output=OUT/'EXPOSURE-DRAFT-v3.json'
assert not output.exists()
output_bytes=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
output.write_bytes(output_bytes)
# Filenames/sizes are metadata; content of protected trees is never requested.
(CACHE/'discovered-case-files.json').write_text(json.dumps([relative(p) for p in casefiles],indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(output=str(output),sha256=hashlib.sha256(output_bytes).hexdigest(),summary=summary),indent=2))
