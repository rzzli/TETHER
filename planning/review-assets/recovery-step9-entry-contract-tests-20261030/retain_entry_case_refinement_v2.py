"""Retain authoring-race chronology and restore exact frozen v1, no tests."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def pin(path):
    path=Path(path).resolve();raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def main():
    source=HERE/'entry_contract_cases_v1.py'
    current=source.read_bytes()
    assert hashlib.sha256(current).hexdigest()=='d084ef7563b92730f3220a8af5550cbdc35a619784d9e1282bf9e34d70b18d3a'
    freeze_path=HERE/'ENTRY-CONTRACT-SUITE-FREEZE-v1.json'
    frozen=json.loads(freeze_path.read_bytes().decode('utf-8'))
    wanted=frozen['harness']['cases']
    text=current.decode('utf-8')
    first="    require(w.state.primary is fault,'cleanup retains the original interrupt')\n"
    second="    w.cleanup()\n    require(w.state.primary is fault and w.held_states[0]._known_read_bytes==cached,\n            'cleanup preserves the same primary without healing the failed read cache')\n    require(sum(r.api=='ReadFile' for r in w.originals.refs)==1,'cleanup never retries the failed read')\n"
    assert text.count(first)==text.count(second)==1
    before=text.replace(first,'').replace(second,'').encode('utf-8')
    assert len(before)==wanted['bytes'] and hashlib.sha256(before).hexdigest()==wanted['sha256']
    def functions(raw):
        return {n.name:ast.dump(n,include_attributes=False)for n in ast.parse(raw.decode('utf-8')).body if isinstance(n,ast.FunctionDef)}
    a=functions(before);b=functions(current)
    assert a.keys()==b.keys()
    changed=sorted(name for name in a if a[name]!=b[name]);assert changed==['E17','E21']
    successor=HERE/'entry_contract_cases_v2.py'
    with successor.open('xb')as f:f.write(current)
    source.write_bytes(before)
    assert pin(source)==wanted
    out=HERE/'ENTRY-CONTRACT-ASSERTION-REFINEMENT-CHRONOLOGY-v2.json'
    data=dict(schema_version=1,status='EXACT_FROZEN_V1_RESTORED_REFINED_V2_RETAINED_BEFORE_EXECUTION',
              frozen_v1=pin(freeze_path),restored_v1=pin(source),refined_v2=pin(successor),helper=pin(__file__),
              changed_case_ASTs=changed,other_function_ASTs_equal=True,
              cause='The scaffolding author froze v1 while the assertion author saved two final cleanup checks. No subject imported or ran. V1 bytes were reconstructed by removing only those additions and hash-checked against the retained freeze before restoration; refined bytes are separately named v2.',
              corrections=['E17 asserts original interrupt remains primary after the already-declared cleanup.',
                           'E21 explicitly performs the already-declared cleanup and checks unchanged failed-read cache, same primary and no read retry afterward.'],
              unchanged_named_controls=32,unchanged_literal_branches=53,subject_imports=0,subject_runs=0,
              prior_preparation_and_outputs_preserved=True,source3_files_edited=False)
    with out.open('xb')as f:f.write((json.dumps(data,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    print(json.dumps(dict(chronology=pin(out),v1=pin(source),v2=pin(successor))))


if __name__=='__main__':main()
