"""Preserve candidate v1; author the bounded prefreeze review corrections only."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=(HERE/'UTF8-ORACLE-SPEC-v1.md').read_text(encoding='utf-8')
spec=spec.replace('# Strict UTF-8 byte/chunk oracle specification','# Strict UTF-8 byte/chunk oracle specification, revision 2')
spec=spec.replace('UTF8-ORACLE-CORPUS-v1.json','UTF8-ORACLE-CORPUS-v2.json')
addition='''## Request types and terminal API behavior

The prospective adapter interface is `feed(chunk, *, final=False)`. Require `type(chunk) is bytes` and `type(final) is bool`; do not implicitly copy or coerce strings, bytearrays, memoryviews, subclasses or other objects. Check chunk type first, then final type, before examining bytes or changing state. Invalid chunk type raises `TypeError("chunk_must_be_bytes")`; invalid final type raises `TypeError("final_must_be_bool")`. Both leave all state and counters unchanged.

After successful finalization, any otherwise well-typed feed raises `RuntimeError("decoder_already_finalized")` and leaves state unchanged, including an empty feed. Argument-type errors retain the precedence above. These request/state exceptions are API errors, separate from the byte-stream error object; they never create or replace that object. After an encoding error, well-typed feeds instead follow the absorbing-error behavior already specified. Immutable snapshot records and tuple-valued scalar evidence are intended; any dictionary serialization must be a fresh copy that cannot mutate decoder state. These are prospective interface requirements, not an implemented adapter.

'''
spec=spec.replace('## Exact error precedence',addition+'## Exact error precedence')
spec=spec.replace('An initial `EF BB BF` emits U+FEFF; this is UTF-8, not UTF-8-SIG.',
    'Both initial and middle `EF BB BF` emit U+FEFF; this is UTF-8, not UTF-8-SIG.')
with (HERE/'UTF8-ORACLE-SPEC-v2.md').open('x',encoding='utf-8',newline='\n') as out:out.write(spec)
source=(HERE/'author_utf8_oracle_corpus_v1.py').read_text(encoding='utf-8')
source=source.replace('UTF8-ORACLE-SPEC-v1.md','UTF8-ORACLE-SPEC-v2.md').replace('UTF8-ORACLE-CORPUS-v1.json','UTF8-ORACLE-CORPUS-v2.json')
source=source.replace('UTF8-ORACLE-GENERATION-PROVENANCE-v1.json','UTF8-ORACLE-GENERATION-PROVENANCE-v2.json')
source=source.replace("('four_byte_min',0x10000,'f0908080'),('grinning_face',0x1F600,'f09f9880'),('scalar_max',0x10FFFF,'f48fbfbf'),",
    "('four_byte_min',0x10000,'f0908080'),('grinning_face',0x1F600,'f09f9880'),('scalar_max',0x10FFFF,'f48fbfbf'),\n    ('two_byte_min',0x0080,'c280'),('four_middle_lead',0x40000,'f1808080'),")
addition=r'''
    case('mixed/middle_bom_is_not_removed','BOM preservation','A middle BOM is emitted without stripping or resetting','Literal A,BOM,B scalar sequence',[
        step('41',False,'boundary',emitted=[0x41]),step('efbbbf',False,'boundary',emitted=[0xFEFF],total=4,total_examined=4),
        step('42',True,'finished',emitted=[0x42],total=5,total_examined=5)])
    for name,lead,tail,code,width in [
        ('overlong_three','e0','80af','overlong_sequence',3),('overlong_four','f0','8080af','overlong_sequence',4),
        ('surrogate','ed','a080','surrogate_scalar',3),('out_of_range','f4','908080','out_of_range_scalar',4),
    ]:
        data=bytes.fromhex(tail)
        case('split_restricted/'+name,'Restricted second-byte state across chunks',
            'Keep the leading-byte range restriction when the second byte arrives later','Literal lead-specific invalid second byte',[
                step(lead,False,'pending',pending=lead,width=width),
                step(tail,True,'error',pending=lead,width=width,consumed=0,examined=1,total=1,total_examined=2,
                    failure=error(code,1,0,data[0]),unconsumed=tail)])
'''
source=source.replace('    return dict(schema_version=1,profile=',addition+'\n    return dict(schema_version=1,profile=')
with (HERE/'author_utf8_oracle_corpus_v2.py').open('x',encoding='utf-8',newline='\n') as out:out.write(source)
checker=(HERE/'check_utf8_oracle_structure_v1.py').read_text(encoding='utf-8')
for old,new in [('CORPUS-v1','CORPUS-v2'),('SPEC-v1','SPEC-v2'),('corpus_v1.py','corpus_v2.py'),('PROVENANCE-v1','PROVENANCE-v2'),('CHECKS-v1','CHECKS-v2')]:
    checker=checker.replace(old,new)
checker=checker.replace('fixtures=96,steps=146,supplied_bytes=315','fixtures=107,steps=167,supplied_bytes=354')
checker=checker.replace("len(DATA['expected_scalar_encoding_pairs']),12","len(DATA['expected_scalar_encoding_pairs']),14")
checker=checker.replace("'mixed/complete_two_then_partial_four','mixed/nul_does_not_terminate'", 
    "'mixed/complete_two_then_partial_four','mixed/middle_bom_is_not_removed','scalar/two_byte_min','scalar/four_middle_lead','split_restricted/overlong_three','split_restricted/overlong_four','split_restricted/surrogate','split_restricted/out_of_range','mixed/nul_does_not_terminate'")
with (HERE/'check_utf8_oracle_structure_v2.py').open('x',encoding='utf-8',newline='\n') as out:out.write(checker)
print('Authored v2spec/generator/structural checker; v1files unchanged. No corpus generated, decoder or adapter run.')
