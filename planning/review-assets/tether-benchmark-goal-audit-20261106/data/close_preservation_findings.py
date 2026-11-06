"""Resolve the first reader's two schema assumptions without rerunning a study."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).parent


def capture(path, expected=None):
    path=Path(path);raw=path.read_bytes();pin={"path":str(path),"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)}
    if expected is not None:
        expected={"sha256":expected} if isinstance(expected,str) else {k:expected[k] for k in ('sha256','bytes') if k in expected}
        assert all(pin[k]==v for k,v in expected.items()),str(path)
    return raw,pin


def load(path, expected=None):
    raw,pin=capture(path,expected);return json.loads(raw),pin


def main():
    original,original_pin=load(HERE/'PRESERVATION-MANIFEST-01.json','6574d819ab6ccc02c4d0423f5be4735b164a1ae75dd15ade2c2337560a9c7e13')
    expected_bad={str(ROOT/name) for name in ('collect.py','data_views.py','retrieval.py','runtime.py')}
    assert {x['path'] for x in original['mismatches']}==expected_bad
    assert all(x['status']=='missing_or_unreadable' and x['scope']=='BG04 collection source equality' for x in original['mismatches'])
    bad_inventory=[x for x in original['inventories'] if x['status']!='pass']
    assert len(bad_inventory)==2 and all(x['added']==['journal.jsonl'] and not x['missing'] for x in bad_inventory)
    collection=ROOT/'data/benchmark/labbench/collection-20261106T011303Z-attempt01'
    manifest,manifest_pin=load(collection/'manifest.json','b75558de8fca5382729e42d7bd6adc9efabdb072791b0d75201aaff2280c47de')
    checks=[]
    for name,expected in manifest['code_pins'].items():
        _,pin=capture(ROOT/'experiments/labbench'/name,expected);checks.append(pin)
    genfreeze,_=load(ROOT/'planning/review-assets/tether-labbench-20261106/stage/generation-freeze-attempt02/GENERATION-FREEZE.json',
                    '4359d589205caec39085872cc72cd5799323e2285e0993b58405e7e70ccd2fe5')
    cseal,cseal_pin=load(collection/'SEALED.json',genfreeze['collection']['seal_sha256'])
    assert cseal['manifest_sha256']==manifest_pin['sha256']
    _,pin=capture(collection/'journal.jsonl',cseal['journal_sha256']);checks.append(pin)
    evaluation=ROOT/'data/benchmark/labbench/evaluation-20261106T011303Z-attempt01'
    eseal,eseal_pin=load(evaluation/'SEALED.json','118711b7e7552750e441380b7abf8f60b68096ae98ef3163cf96754e7423fa6f')
    _,pin=capture(evaluation/'journal.jsonl',eseal['journal_sha256']);checks.append(pin)
    assert {p.relative_to(evaluation).as_posix() for p in evaluation.rglob('*') if p.is_file()} == set(eseal['outputs'])|{'SEALED.json','journal.jsonl'}
    assert {p.relative_to(collection).as_posix() for p in collection.rglob('*') if p.is_file()} == set(manifest['outputs'])|{'manifest.json','SEALED.json','COMPLETE.json','journal.jsonl'}
    acceptance,acceptance_pin=load(ROOT/'planning/review-assets/tether-inspect-20261106/stage/STAGE-ACCEPTANCE-02.json')
    assert acceptance['status']=='pass' and acceptance['count']==60 and acceptance['local_links']==34
    current_acceptance_pins=[]
    for expected in acceptance['pins']:
        _,pin=capture(expected['path'],expected);current_acceptance_pins.append(pin)
    # These are explicitly mutable documentation corrections, not frozen-run repairs.
    mutable=['README.md','memory/MEMORY.md','memory/project-goals.md','planning/TETHER Inspect Comparison Results 2026-11-06.md']
    text=[]
    for name in mutable:
        raw,pin=capture(ROOT/name);decoded=raw.decode('utf-8')
        assert not any(token in decoded for token in ('\u00e2\u20ac\u201c','\u00e2\u20ac\u201d','\u00e2\u20ac\u2122','\u00ef\u00bb\u00bf'))
        diff=subprocess.check_output(['git','diff','--numstat','e8e40af','--',name],cwd=ROOT).decode('utf-8').strip()
        text.append({**pin,'strict_utf8':True,'known_mojibake_markers_absent':True,'git_diff_numstat_from_e8e40af':diff,
                     'scope':'Current corrected documentation, not asserted unchanged from earlier checkpoints'})
    report={'schema_version':1,'status':'pass_scoped_preservation','first_pass':original_pin,
       'resolved_reader_findings':{'source_root_assumption':4,'separate_journal_inventory_assumption':2},
       'corrected_source_and_journal_proofs':checks,'collection_seal':cseal_pin,'evaluation_seal':eseal_pin,
       'actual_byte_hash_mismatches':0,'unresolved_preservation_findings':0,
       'current_document_acceptance':acceptance_pin,'current_acceptance_pins':current_acceptance_pins,
       'utf8_document_correction_review':text,'checked_source_files_and_outputs_unchanged':True,
       'original_artifacts_modified':False,'production_reexecution':False,
       'qualifier':'Only the explicit first-pass six reader flags are discharged; original report/log are preserved. Model weights, broad biological raw stores, live process state and semantic interpretation remain outside this preservation check.'}
    raw=json.dumps(report,sort_keys=True,separators=(',',':')).encode()
    with (HERE/'PRESERVATION-CLOSURE-01.json').open('xb') as f:f.write(raw)
    print(json.dumps({'status':report['status'],'sha256':hashlib.sha256(raw).hexdigest(),'unresolved_findings':0}))


if __name__=='__main__':main()
