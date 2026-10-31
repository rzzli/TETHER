"""Retain only the narrow new-source correction graph; no runtime data reads."""
import ast
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OUT=HERE/'CAPTURED-JOURNAL-CORRECTION-BINDING-v2.json'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(name):
    path=HERE/name;raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=sha(raw))
def tree(name):return ast.parse((HERE/name).read_text(encoding='utf-8'))
def dump(node):return ast.dump(node,include_attributes=False)
def basis(t):return [dump(n) for i,n in enumerate(t.body) if not (i==0 and isinstance(n,ast.Expr) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)) and not (isinstance(n,ast.FunctionDef) and n.name=='check_native_v7')]
def main():
    assert not OUT.exists(),'Preserve correction record'
    files=['captured_journal_v1.py','captured_journal_v2.py','check_captured_journal_v1.py','check_captured_journal_v2.py',
        'CAPTURED-JOURNAL-SOURCE-PURE-PROOF-v1.json','CAPTURED-JOURNAL-SOURCE-PURE-PROOF-v2.json',
        'CAPTURED-JOURNAL-INDEPENDENT-PEER-v1.json','check_captured_journal_peer_v1.py',
        'CAPTURED-JOURNAL-CONTRACT-v1.json','CAPTURED-JOURNAL-FIXTURES-v1.json','CAPTURED-JOURNAL-FIXTURE-FREEZE-v1.json']
    pins={name:pin(name) for name in files}
    assert pins['captured_journal_v1.py']['sha256']=='5b86f70a57dd1b51d7fe74829b032ddd954f656075ec585c062d5c6dc5e3cf37'
    assert pins['CAPTURED-JOURNAL-INDEPENDENT-PEER-v1.json']['sha256']=='d7b6c1d13e96ed6236b0a5acb9e3a37ef35ee9d36e4d87974f0ca26a53d5ae97'
    assert pins['check_captured_journal_peer_v1.py']['sha256']=='5fc7e50d0fcf9bc660d7110e9af7dbdda437715daa9160ce375804cd2f08a30c'
    a,b=tree('captured_journal_v1.py'),tree('captured_journal_v2.py');assert basis(a)==basis(b),'Nonterminal policy drift'
    old={n.name:dump(n) for n in a.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
    new={n.name:dump(n) for n in b.body if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
    unchanged=[name for name in old if old[name]==new.get(name)];assert set(old)-set(unchanged)=={'check_native_v7'}
    proof=json.loads((HERE/'CAPTURED-JOURNAL-SOURCE-PURE-PROOF-v2.json').read_text(encoding='utf-8'))
    assert proof['status']=='passed' and proof['methods']==10 and len(proof['frozen_case_observations'])==30
    assert proof['source']==pins['captured_journal_v2.py'] and proof['checker']==pins['check_captured_journal_v2.py']
    value=dict(schema_version=1,status='CORRECTED_SOURCE_PURE_PENDING_INDEPENDENT_PEER',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        inputs=pins,recorder=pin(Path(__file__).name),unchanged_module_AST_except_docstring_and_native_terminal_policy=True,
        unchanged_classes_functions=unchanged,changed_function='check_native_v7',
        correction=['terminal errors must be present and empty','strict known EOF drain status and reserved poll counts',
                    'ordered successful call/read frames; no missing value or consume error','nonempty drain ends exactly once at returned None availability',
                    'read bytes cannot exceed retained capture; optional aggregate poll count is strict','terminal Job invocation status returned'],
        checks=dict(methods=10,frozen_fixtures=30,added_terminal_regression_vectors=13,unchanged_frozen_fixture_bytes=True),
        chronology='Original v1/proof preserved. Independent before evidence reproduced five false positives; separate v2 source/checker passed ten methods. No actual old run was replayed.',
        synthetic_extension_correction='The v1 optional nonempty-drain test used status observed_EOF and omitted invoke status; v2 uses the actual observed_pipe_EOF/returned labels without modifying any frozen literal fixture.',
        profile_qualified=False,resource_semantics_validated=False,actual_old_run_replay=False,actual_children=0,real_SDK_constructions=0,
        CPU_GGUF_pack_reads=0,live_adapter_or_fresh_original_qualification=False)
    with OUT.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(pin(OUT.name)))
if __name__=='__main__':main()
