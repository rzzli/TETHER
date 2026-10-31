"""Named metadata correction; preserve v1 and every source/harness byte."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def pin(path):
    path=Path(path).resolve();raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def exact(name,digest):
    path=HERE/name;value=pin(path)
    if value['sha256']!=digest:raise RuntimeError('frozen metadata changed: '+name)
    return value,json.loads(path.read_bytes())


def save_new(name,data):
    path=HERE/name
    with path.open('xb')as stream:
        stream.write((json.dumps(data,indent=2,sort_keys=True,ensure_ascii=True,allow_nan=False)+'\n').encode())
    return pin(path)


def main():
    old_inputs,inputs=exact('ENTRY-E08-SUITE-INPUTS-v1.json','1718d4aa895409ef18137559c90583bea73d280f3b65accdd64e25c4c019b707')
    old_preparation,preparation=exact('ENTRY-E08-SUITE-PREPARATION-v1.json','c9e8e976420095f84b3d80768b0818f50f952d1f76a912f1c66ac17af11ece86')
    old_outline,outline=exact('ENTRY-E08-SUITE-BINDING-OUTLINE-v1.json','9cbdbd741d6b2f1b5f27b47a9ae0a18226bbb67cfe6ba8558d2345934a5abd36')
    old_freeze,frozen=exact('ENTRY-E08-SUITE-FREEZE-v1.json','e9138b4304455bcf316148bec4758075e1058bf352874c44afe467394a827270')
    for value in [inputs['source_pause'],*inputs['source_map'].values(),*preparation['harness'].values()]:
        if pin(value['path'])!=value:raise RuntimeError('paused source/harness changed')
    for path in outline['consumed_paths']:
        if Path(path).exists():raise RuntimeError('subject already consumed; correction forbidden')
    inherited=inputs['kernel_tcb']
    if inherited['pin']['sha256']!='60d266f2a6488fac96fa9e31663052a41b191d56b905a102f96cd7187f732fad':
        raise RuntimeError('unexpected inherited provenance')
    active=inputs['source_map'][inputs['module_names']['kernel']]
    if active['sha256']!='e389db4ec1e667f1b81694575ba1ba0d1d7ceed3e642cf43504766f331c759f8':
        raise RuntimeError('actual Source4 kernel anchor required')
    correction=dict(reason='Inherited unused kernel_tcb field named Source3 while active Source4 map/size were correct. No source or test execution occurred.',
                    preserved_inputs=old_inputs,preserved_preparation=old_preparation,
                    preserved_outline=old_outline,preserved_freeze=old_freeze,
                    active_source_harness_unchanged=True,subject_runs=0)
    inputs['schema_version']=2
    inputs['inherited_source3_tcb_reference']=inherited
    inputs['kernel_tcb']=dict(captured_as_helper=False,pin=active)
    inputs['metadata_provenance_correction']=correction
    ip=save_new('ENTRY-E08-SUITE-INPUTS-v2.json',inputs)
    preparation['schema_version']=2;preparation['inputs']=ip
    preparation['preserved_original_preparer']=preparation['preparer']
    preparation['preparer']=pin(__file__)
    preparation['metadata_provenance_correction']=correction
    pp=save_new('ENTRY-E08-SUITE-PREPARATION-v2.json',preparation)
    outline['schema_version']=2;outline['inputs']=ip;outline['preparation']=pp
    outline['freeze']=dict(path=str(HERE/'ENTRY-E08-SUITE-FREEZE-v2.json'),bytes=None,sha256=None,
                           reason='Root fills acyclic corrected metadata freeze pin')
    op=save_new('ENTRY-E08-SUITE-BINDING-OUTLINE-v2.json',outline)
    frozen.update(schema_version=2,inputs=ip,preparation=pp,outline=op,
                  preserved_original_preparer=frozen['preparer'],preparer=pin(__file__),
                  metadata_provenance_correction=correction)
    fp=save_new('ENTRY-E08-SUITE-FREEZE-v2.json',frozen)
    print(json.dumps(dict(inputs=ip,preparation=pp,outline=op,freeze=fp)))


if __name__=='__main__':main()
