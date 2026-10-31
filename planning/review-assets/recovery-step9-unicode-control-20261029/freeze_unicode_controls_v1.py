"""Freeze reviewed source-only controls before any bridge/pack/runtime code."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
RECORD=HERE/'UNICODE-CONTROL-FIXTURE-FREEZE-v1.json'
EXPECTED={
    'UNICODE-CONTROL-PROFILE-v2.md':'f6512f48ffd58756e96ea1655df05824e4ccb2588cbe19264cd21e8b1bd27dbf',
    'UNICODE-CONTROL-CONTRACT-v2.json':'65a34539dd1bdecb20ed85724c58f80e362113cb4db969f5edf60b48af9a111d',
    'UNICODE-CONTROL-CORPUS-v1.json':'13e2c2f2900802729c0d39fa9b7851c56ab3db6afdc45c4b15c2f7f80bd6523c',
    'UNICODE-CONTROL-STAGES-v1.json':'ad688168a366d5e95413ec69731d030c54431663e6574fb93445ced2b580413a',
    'UNICODE-CONTROL-GENERATION-CHECKS-v1.json':'9f1c4636d15706cc9fa628f55d0c668ce622d96d1ca5f02e7fcb2b7f9a252a4c',
    'UNICODE-CONTROL-PROVENANCE-v1.json':'e6adbfe5e754a02ebe223e548b418b7a7fc8008926aadda8b17cddf1e6fe80f8',
    'UNICODE-CONTROL-STRUCTURAL-CHECKS-v1.json':'6e62f04b8f701e9a358c9bc8ab2c3872723a59d2218cc4bedfd23a0c06c0b3da',
    'UNICODE-CONTROL-PROFILE-PRECHECK-v2.json':'7fbce38480668e8eb99d7761c0c2c2bccef83ad7b969840af28d1c5aaebfd8b4',
    'UNICODE-CONTROL-CORPUS-MANUAL-PRECHECK-v1.json':'77b7f3f9ec2d069ae6b4357ff16ea2f4ced9e520ee3b2230995c7aa9038dc04a',
    'UNICODE-CONTROL-PROFILE-v1.md':'88c55e0f64099053711caac53c67216a169343567fee55c30b1084c76654b945',
    'UNICODE-CONTROL-PROFILE-DRAFT-REVIEW-v1.json':'42400ed622240bff8a4243bd1ab48aab274f56a29f2664b49ddd2d58f3c86d11',
}
def pin(path):
    path=Path(path);assert path.parent==HERE
    raw=path.read_bytes();raw.decode('utf-8','strict')
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def load(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
def main():
    assert not RECORD.exists(),'Preserve frozen fixture record'
    artifacts={}
    for name,expected in EXPECTED.items():
        row=pin(HERE/name);assert row['sha256']==expected;artifacts[name]=row
    corpus=load('UNICODE-CONTROL-CORPUS-v1.json');stages=load('UNICODE-CONTROL-STAGES-v1.json')
    structural=load('UNICODE-CONTROL-STRUCTURAL-CHECKS-v1.json');generation=load('UNICODE-CONTROL-GENERATION-CHECKS-v1.json')
    assert structural['status']=='passed' and structural['methods']==7 and structural['failures']==structural['errors']==[]
    assert generation['status']=='passed' and generation['errors']==[] and len(generation['exact_rawbyte_semantic_checks'])==84
    assert len(corpus['cases'])==84 and len(corpus['scalar_pairs'])==14 and len(stages['stages'])==4 and len(stages['unique_grammar_hashes'])==2
    assert all(c['measured_piece_ledger'] is None for c in corpus['cases'])
    assert sum(c['coverage_population'] for c in corpus['cases'])==68
    assert sum(c['expected']['native_membership'] is True for c in corpus['cases'])==69
    assert sum(c['expected']['native_membership'] is False for c in corpus['cases'])==9
    assert sum(c['expected']['native_membership'] is None for c in corpus['cases'])==6
    for name in ('author_unicode_controls_v1.py','author_unicode_controls_v2.py','check_unicode_control_structure_v1.py',
        'UNICODE-CONTROL-AUTHORING-FAILURE-v1.json'):
        artifacts[name]=pin(HERE/name)
    sources=list(HERE.glob('*.py'))
    for path in sources:ast.parse(path.read_text(encoding='utf-8'))
    assert not list(HERE.glob('*.cpp')) and not list(HERE.glob('*.pack')) and not list(HERE.glob('*EXECUTION-PROTOCOL*'))
    links=[]
    for name in ('UNICODE-CONTROL-PROFILE-v1.md','UNICODE-CONTROL-PROFILE-v2.md'):
        for target in re.findall(r'\]\(([^)]+)\)',(HERE/name).read_text(encoding='utf-8')):
            if not target.startswith(('http:','https:','#')):assert (HERE/target).is_file();links.append(target)
    value=dict(schema_version=1,status='FROZEN_DISTINCT_SOURCE_ONLY_UNICODE_CORPUS_BEFORE_RUNTIME_CODE',
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),profile_id=corpus['profile_id'],artifacts=artifacts,
        corpus=dict(cases=84,scalar_pairs=14,stage_payload_instances=4,unique_actual_GBNF_hashes=2,
            native_byte_eligible_cases=78,coverage_population=68,authored_native_membership_expectations=dict(member=69,nonmember=9,ineligible_null=6),
            measured_native_or_token_results=0,maximum_document_bytes=max(c['bytes'] for c in corpus['cases'])),
        review_and_checks=dict(rawbyte_actual_v3_semantic_author_checks=84,structural_methods=7,
            manual_profile_and_corpus_precheck_clear=True,independent_postfreeze_semantic_run='pending'),
        preserved_drafts_and_failure=dict(original_profile_v1_restored_to_reviewed_bytes=True,original_HOLD_preserved=True,
            initial_authoring_failure='Frozen mapping passed to a dict-only pointer; stopped before corpus/stage output. Separatev2helper encodes the pointer input. No expectations/profile cases changed.'),
        fixed_coverage_policy=['Entire fixed corpus, all outcomes/piece data and boundary counts; no favorable subset or observed-success filter',
            'Width2/3/4 and same-piece wholly-contained complete scalar plus pending tail; matrix distinct-width unit and witness intervals explicit',
            'Deterministic first(case,token) selector after fullscan; overlapping classes de-duplicate; original token prefix is never retokenized',
            'Unavailable/unknown requiredclass or any expected outcome/QC/record failure stays negative/incomplete; no automatic extra corpus or native rerun'],
        limits_not_increased=dict(case_ceiling=96,grammar_instances=4,token_work=1000000,vocabulary=262144,EOG=64,
            JSONL_bytes=8388608,row_bytes=65536,pack_bytes=20971520,cooperative_ms=117000,child_seconds=120,owner_seconds=300,commit_bytes=268435456),
        scope='Exact accepted v3 fullresponse/string-branch fixtures and source-only contracts, not an extracted language or native pack.',
        activity_scope='Zero counts refer targetDLL/SDK/process/compiler/tokenizer/network profile actions; ordinary Python/stdlib/loader/OS activity is not universally attested.',
        activity=dict(target_native_SDK_tokenizer_compiler_calls=0,CPU_GGUF_oldpack_operations=0,downloads=0,
            bridge_pack_runtime_implementations=0,old_profile_edits_or_retries=0),
        remaining='Independent frozen rawbyte/JSON/v3 semantic reference review, then separate source/bridge/row-wire/pack/parent/verifier/resource gates and root decisions. No runtime authority follows.',
        QA=dict(all_expected_pins_current=True,text_UTF8_valid=True,python_sources_syntax_valid=len(sources),local_links_checked=links),
        execution_authorized=False,native_conformance='unverified',scientific_validation='not_established',freezer=pin(Path(__file__)))
    with RECORD.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(freeze=pin(RECORD),corpus=value['corpus'],runtime_authorized=False)))
if __name__=='__main__':main()
