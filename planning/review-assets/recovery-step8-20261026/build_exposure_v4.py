"""Build R08 exposure v4 from pinned evaluator/control metadata only."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'planning/review-assets/recovery-step8-20261026'
V3=OUT/'EXPOSURE-DRAFT-v3.json'
EXPECTED='986e48cbd67e29f99a47f81a5c3416007cccf66b495c46c63a41a9eb23412186'

def safe(path):
    path=Path(path)
    assert path.name.lower()!='normalized-outcomes.json'
    assert not any(x.lower() in ('labels','gold_evidence') or x.lower().startswith('adjudication') for x in path.parts)
    return path

def pin(path):
    path=safe(path)
    raw=path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))

def read(path):return json.loads(safe(path).read_bytes())

assert pin(V3)['sha256']==EXPECTED
value=read(V3)
inputs={p['path']:p for p in value['inputs']}
def retain(path):
    proof=pin(path);inputs[proof['path']]=proof;return proof

source_pins=read(OUT/'source-feasibility-pins.json')
for path,expected in source_pins['artifacts'].items():
    proof=retain(Path(path));assert proof['sha256']==expected['sha256'] and proof['bytes']==expected['bytes']
required=['source-feasibility.md','source-feasibility-pins.json','terms-review.md','terms-review.json','virtual-biotech-public-coverage-discovery-v1.json','virtual-biotech-public-coverage.md','virtual-biotech-pinned-tree-audit-v1.json','date-and-review-addendum.md','date-followup-pins.json']
references={name:retain(OUT/name) for name in required}
public=read(OUT/'virtual-biotech-public-coverage-discovery-v1.json')
for proof in public['evidence']:
    actual=retain(ROOT/proof['path']);assert actual==proof
terms=read(OUT/'terms-review.json')
date_pins=read(OUT/'date-followup-pins.json')
for path,expected in date_pins['artifacts'].items():
    path=Path(path);proof=retain(path if path.is_absolute() else ROOT/path)
    assert proof['sha256']==expected['sha256'] and proof['bytes']==expected['bytes']
frame_path=ROOT/'data/cache/recovery-step8-source-feasibility-20261026/candidate-pair-metadata.json'
frame=read(frame_path)
old_real=[g for g in value['hypothesis_groups'] if g['classification']=='real_identifier_metadata']
old_targets={g['hypothesis']['target_id'] for g in old_real}
old_pairs={(g['hypothesis']['target_id'],g['hypothesis']['indication_id']) for g in old_real}
assert len(old_real)==20 and len(old_targets)==18 and len(old_pairs)==18
mapping=read(ROOT/'data/cache/recovery-step8-exposure-20261026/virtual-biotech-identity-keys-v1.json')
map_keys={(i['target_id'],i['indication_id']):i for i in mapping['keys']}
rows=[]
for item in sorted(frame,key=lambda x:(x['symbol'],x['disease_id'])):
    target,disease=item['target_id'],item['disease_id']
    match=map_keys.get((target,disease))
    rows.append(dict(symbol=item['symbol'],target_id=target,indication_id=disease,intended_action=None,modality=None,tissue=None,case_id=None,prior_historical_target_match=target in old_targets,prior_historical_target_indication_match=(target,disease) in old_pairs,published_vignette_target_match=target in {'ENSG00000103855','ENSG00000145623'},virtual_biotech_mapping_member=match is not None,virtual_biotech_mapping_rows=match['mapping_rows'] if match else None,published_evaluated_subset='unknown',published_GEO_source_overlap='unresolved_identity_crosswalk_not_available',prior_case_article_overlap='unresolved_prior_article_membership_not_joined',stage='selection_metadata_preparation_only',generated_candidate_exposure=False,freshness_qualified=False,disposition='conservative_public_mapping_overlap_quarantine' if match else 'no_direct_known_match_freshness_unqualified',concept_role='alternate_RA_phenotype_audit_only' if disease=='HP_0001370' else 'intended_disease_concept',RA_concept_policy='EFO_0000685 intended; HP_0001370 retained separately for audit, no automatic merging'))
assert len(rows)==70 and len({i['target_id'] for i in rows})==14
assert not any(i['prior_historical_target_match'] or i['published_vignette_target_match'] for i in rows)
assert sum(i['virtual_biotech_mapping_member'] for i in rows)==31

value.update(revision='R08-exposure-draft-v4',created_at_utc=datetime.now(timezone.utc).isoformat(),previous_revision=pin(V3),status='preparation_complete_scientific_and_freshness_qualification_pending',complete=False)
value['summary'].update(unique_real_targets=18,historical_input_files_read=value['summary']['input_files_read'],preliminary_frame_targets=14,preliminary_frame_target_concept_combinations=70,preliminary_frame_exact_historical_target_matches=0,preliminary_frame_VB_mapping_overlap_pairs=31,preliminary_frame_nonoverlap_pairs_not_qualified_fresh=39,preliminary_intended_disease_combinations=56,preliminary_alternate_RA_audit_combinations=14,fresh_real_cases_qualified=0)
value['exposure_evidence_classes']={
 'confirmed_project_material':dict(historical_hypotheses=20,historical_targets=18,real_metadata_occurrences=197,rule='Existing case metadata, frozen case packs and run controls establish prior project material. Do not infer successful model dispatch or independent scientific review from file presence.',scope='Historical action/modality/tissue hypotheses and all IL6R derivatives remain excluded from fresh evaluation.'),
 'confirmed_published_identity_exposure':dict(entries=public['publication_identity_exclusions'],source_accessions=public['related_source_accessions'],source=references['virtual-biotech-public-coverage-discovery-v1.json'],rule='CD276 LUAD/SCLC and OSMR UC are published narrative contexts. Five GEO accessions are published source identities, not per-patient or per-trial outcome labels.'),
 'conservative_quarantine':dict(rules=[dict(scope='Any CD276 lung-cancer hypothesis',basis='Published LUAD/SCLC exposure; existing NSCLC key is insufficiently broad',canonical_target_id='ENSG00000103855',additional_indication_ids=None,requires='Resolve disease identity scope before considering any related variant'),dict(scope='OSMR ulcerative-colitis hypotheses and related referenced source cohorts',canonical_target_id='ENSG00000145623',canonical_indication_id='EFO_0000729'),dict(scope='All IL6R derivatives, protected clinical/reference families, and overlapping published source material',basis='R01 and subsequent control metadata; contents remain protected'),dict(scope='Local Virtual Biotech mapping identity overlaps',basis='Conservative freshness quarantine only; mapping membership is not evidence of actual published evaluation',identity_pair_count=72158)]),
 'unknown_publication_subset':dict(status='unresolved',local_mapping_identity_inventory_complete=True,actual_clinical_analytic_subset='unqualified',single_cell_analytic_subset='unqualified',reason='Pinned tree lacks separately named identity roster; paper/repository counts differ; publisher supplement metadata returned HTTP429. No equality/containment inferred.',required='Release-matched identity-only analytic inclusion roster or documented key-selection export; no clinical label values needed'),
 'selection_stage_metadata_preparation':dict(targets=14,target_concept_pairs=70,meaning='New preliminary frame inspected for identifiers and source metadata. This is not prior generated-answer exposure, and is not permission to call the frame fresh or confirmatory.')}
value['preliminary_candidate_exclusion_review']=dict(source_frame=retain(frame_path),source_summary=references['source-feasibility.md'],source_manifest=references['source-feasibility-pins.json'],pairs=rows,counts=dict(targets=14,pairs=70,direct_historical_target_matches=0,VB_mapping_overlap=31,VB_mapping_nonoverlap=39,RA_concepts_retained=2,intended_disease_pairs=56,alternate_RA_audit_pairs=14,intended_pairs_VB_mapping_overlap=31,intended_nonmatches_not_qualified_fresh=25,freshness_qualified=0),limitations=['No case is selected, ranked, action/modality/tissue assigned or split frozen.','EFO_0000685 is intended per owner case scope;14 HP_0001370 combinations remain audit-only and cannot inflate the56 intended combinations or manufacture freshness.','Shared articles across preliminary pairs are identified by source feasibility, but overlap with earlier case/article inventories and five GEO sources remains unresolved.','Rights and source sufficiency depend on selected original content; high row counts and no exact target match do not qualify evidence or freshness.'])
nonmatches=[dict(symbol=i['symbol'],target_id=i['target_id'],indication_id=i['indication_id']) for i in rows if i['concept_role']=='intended_disease_concept' and not i['virtual_biotech_mapping_member'] and not i['prior_historical_target_match'] and not i['published_vignette_target_match']]
assert len(nonmatches)==25
value['selection_guard']=dict(role='evaluation_only',scope='Prospective development-only source qualification; not fresh-case acceptance',intended_indication_ids=['EFO_0000384','EFO_0000676','EFO_0000685','EFO_0000729'],alternate_indication_ids_audit_only=['HP_0001370'],confirmed_prior_target_exclusions=sorted(old_targets),confirmed_prior_pair_exclusions=[dict(target_id=t,indication_id=d) for t,d in sorted(old_pairs)],published_vignette_target_family_exclusions=public['publication_identity_exclusions'],published_source_accession_flags=public['related_source_accessions'],conservative_mapping_screen='For this small prospective preparation pool, withhold the31 mapping-overlap combinations; nonmembership is not freshness and not a biological criterion.',intended_metadata_combinations=56,conservative_nonmatch_pool_count=25,conservative_nonmatch_pool=nonmatches,order_rule='symbol ascending, then indication_id ascending; distinct target families; no outcome/model-performance ranking',chosen_cases=[],selection_frozen=False,on_zero_source_or_qualification_failure='Retain the planned question outcome with its reason; no automatic substitution or replacement',on_unresolved_source_overlap='Record unresolved; do not certify freshness. Any source-only development use must disclose this status.',candidate_generation_allowed=False)
value['preparation_references']=references
value['terms_note']=dict(proof=references['terms-review.json'],document=references['terms-review.md'],interpretation='Read the pinned provider/product-specific note; no blanket full-text, clinical transfer, scientific or freshness approval is inferred.')
value['virtual_biotech']['public_tree_audit']=references['virtual-biotech-pinned-tree-audit-v1.json']
value['virtual_biotech']['public_coverage_discovery']=references['virtual-biotech-public-coverage-discovery-v1.json']
value['virtual_biotech']['publication_vignettes']=public['publication_identity_exclusions']
value['virtual_biotech']['published_source_accessions']=public['related_source_accessions']
value['development_preparation_boundary']=dict(source_only_preparation_may_continue=True,reviewer_names_required_before_harmless_source_checks=False,known_exposure_policy='Exclude confirmed old case and published vignette/source families for a proposed new development sample; mapping overlap alone is not confirmed evaluation exposure.',unknown_published_roster='Disclose and retain; prevents strong freshness claims but not explicitly development-only source qualification.',scientific_acceptance_pending_HR3=True,no_candidate_generation=True,next_finite_step='Prospectively specify up to two development-only source-question contexts, at most three articles and six intact excerpts/1500 words each; qualify original snippets/locators/context/date/rights without repairing outputs or inventing hypotheses.')
value['inputs']=list(inputs.values())
value['summary']['input_files_read']=len(value['inputs'])
value['unresolved']=['Actual published clinical/single-cell inclusion roster; broader mapping membership does not settle it.','Full project/source relationship exposure beyond the scoped case metadata inventory.','Prior-case and published-source article/accession crosswalk for the new preliminary frame.','Preserve intended RA EFO and audit-only HP distinction; justified action/modality/tissue hypotheses remain unset.','Selected source passage rights, sufficiency, context, dates and replay;440 date-year disagreements remain unresolved in source-feasibility metadata.','HR3 domain-matched independent reviewer coverage and later source-only human references.','No fresh or confirmatory pool, split or generation plan is qualified.']
for expected in value['inputs']:
    actual=pin(ROOT/expected['path']);assert actual==expected
indices=[index for group in value['hypothesis_groups'] for index in group['occurrence_indexes']]
assert sorted(indices)==list(range(493))
assert pin(V3)['sha256']==EXPECTED
output=OUT/'EXPOSURE-DRAFT-v4.json';assert not output.exists()
output.write_bytes((json.dumps(value,indent=2,ensure_ascii=False)+'\n').encode('utf-8'))
validation=dict(schema_version=1,role='evaluation_only',status='passed_preparation_consistency_not_R08_acceptance',output=pin(output),previous_revision=pin(V3),previous_revision_unchanged=True,R01=pin(ROOT/value['supersedes_for_expanded_coverage']['path']),inputs_rehashed=len(value['inputs']),historical_case_files=471,historical_metadata_occurrences=493,historical_occurrence_partition_complete=True,historical_real_hypotheses=20,historical_unique_targets=18,historical_unique_target_indication_pairs=18,candidate_review=dict(targets=14,target_concept_pairs=70,exact_historical_target_overlap=0,VB_mapping_overlap=31,VB_nonoverlap_not_certified_fresh=39,intended_disease_pairs=56,alternate_RA_audit_pairs=14,intended_mapping_nonmatches_not_fresh=25),new_case_files=0,new_agent_visible_manifests=0,new_model_calls=0,protected_contents_read=False,fresh_cases_qualified=0,source_preparation_references=references,generator=pin(Path(__file__)))
(OUT/'exposure-v4-validation.json').write_bytes((json.dumps(validation,indent=2)+'\n').encode())
print(json.dumps(validation,indent=2))
