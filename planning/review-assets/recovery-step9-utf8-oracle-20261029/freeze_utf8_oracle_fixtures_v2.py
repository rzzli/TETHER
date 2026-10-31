"""Seal reviewed literal fixtures before any semantic adapter/reference test."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
RECORD=HERE/'UTF8-ORACLE-FIXTURE-FREEZE-v2.json'
PINS={
    'UTF8-ORACLE-SPEC-v2.md':'f4f3835481f1961c01830bf6ba37107cf270ebaad7a9321d6f1b4ee0fcdec44a',
    'UTF8-ORACLE-CORPUS-v2.json':'65428d32cc06c58836d1d541bde0e893db13cef9e5ae756e26d6e353908b302d',
    'author_utf8_oracle_corpus_v2.py':'a844f88aefa2cb1fad3be52f8de7d11884e6485edfc046259a9c20c654dd2a79',
    'UTF8-ORACLE-GENERATION-PROVENANCE-v2.json':'22aa695081ed6338ad68ac2c2ac3c9a6f7c6d8bd85b134fa0e5ae6704c8c23fa',
    'check_utf8_oracle_structure_v2.py':'cb3eac67c530f01679268b9f9d278966bac7ecfd9db4dc98ba2eda4b243f436a',
    'UTF8-ORACLE-STRUCTURAL-CHECKS-v2.json':'2f28621a9ac28e2c9aaf2f3054bb255f6f6a1127d3d51151059d4d5c858d0eaf',
    'UTF8-ORACLE-MANUAL-PRECHECK-v2.json':'a1a8a9dd407ce3ada77a55de0cdad00d95ac8afdc9108132542e9db861a7bfc8',
}
def pin(path):
    raw=path.read_bytes();raw.decode('utf-8','strict')
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def main():
    assert not RECORD.exists(),'Freeze record already exists'
    records={}
    for name,expected in PINS.items():
        item=pin(HERE/name);assert item['sha256']==expected;records[name]=item
    proof=json.loads((HERE/'UTF8-ORACLE-STRUCTURAL-CHECKS-v2.json').read_text(encoding='utf-8'))
    assert proof['status']=='passed' and proof['tests']==5 and proof['semantic_decoder_comparisons']==0 and proof['test_adapters_implemented']==0
    assert proof['counts']==dict(fixtures=107,steps=167,supplied_bytes=354)
    peer=json.loads((HERE/'UTF8-ORACLE-MANUAL-PRECHECK-v2.json').read_text(encoding='utf-8'))
    # The full peer report is independently hash-bound, without guessing its prose/status schema.
    assert peer['schema_version']==1
    old={p.name:pin(p) for p in HERE.glob('*v1.*') if p.is_file()}
    assert {'UTF8-ORACLE-SPEC-v1.md','UTF8-ORACLE-CORPUS-v1.json','author_utf8_oracle_corpus_v1.py',
        'UTF8-ORACLE-GENERATION-PROVENANCE-v1.json','UTF8-ORACLE-STRUCTURAL-CHECKS-v1.json'}<=set(old)
    # This is a source-generation directory, not a runtime adapter location.
    sources=list(HERE.glob('*.py'))
    for path in sources:ast.parse(path.read_text(encoding='utf-8'))
    assert not any(p.name.startswith(('utf8_oracle_adapter','strict_utf8_decoder')) for p in sources)
    spec=(HERE/'UTF8-ORACLE-SPEC-v2.md').read_text(encoding='utf-8')
    local_links=[]
    for target in re.findall(r'\]\(([^)]+)\)',spec):
        if not target.startswith(('https://','http://','#')):
            assert (HERE/target).is_file();local_links.append(target)
    value=dict(schema_version=1,status='frozen_model_independent_strict_UTF8_fixtures_before_adapter',
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),artifacts=records,counts=proof['counts'],
        prior_candidate_artifacts_preserved=old,
        correction_scope='Initial v1coverage HOLD preserved. Revision2adds valid2byte minimum and F1lead with allinteriors,4crosschunk restricted-second-byte failures and middleBOM; specifies request type/afterfinal API policies. No original expected case was adaptively removed or made favorable.',
        semantic_contract=dict(bytes_only=True,strict_bool_final=True,valid_scalars_committed_before_later_same_chunk_error=True,
            offending_byte_examined_not_consumed=True,pending_bytes_retained_on_error=True,error_absorbing_no_recovery=True,
            empty_final_pending_is_premature_EOF=True,NUL_and_ASCII_controls_are_UTF8_scalars=True,BOM_preserved=True,
            JSON_escape_interpretation='none',vendor_decoder_equivalence='not_assumed'),
        prefreeze_validation=dict(structural_methods=5,semantic_manual_peer='UTF8-ORACLE-MANUAL-PRECHECK-v2.json',
            codec_reference_runs=0,adapters_implemented=0),
        next_gate='Separately retained independent bytewise strictCPython reference check. Root owns any later adapter implementation and its scientific/native boundaries.',
        QA=dict(all_pins_current=True,UTF8_text_valid=True,python_syntax_valid=len(sources),local_markdown_links_checked=local_links),
        activity=dict(CPU_GGUF_oldpack_path_operations=0,target_DLL_API_calls=0,compiler_calls=0,downloads=0,original_native_artifact_edits=0),
        actual_native_vocabulary_EOG_grammar_qualification=False,scientific_validation='not_established',execution_authorized=False,
        freezer=pin(Path(__file__)))
    with RECORD.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(freeze=pin(RECORD),counts=value['counts'],adapters_implemented=0,reference_runs_before_freeze=0)))
if __name__=='__main__':main()
