"""Proposed scripts applied IN MEMORY; no frozen fixture or source changes."""
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'portable_file_ports_v1.py'
PROOF=HERE/'PORTABLE-FILE-PORTS-PROPOSED-INTERFACE-REPLAY-v1.json'


def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);sys.modules[name]=result;spec.loader.exec_module(result);return result


def main():
    assert not PROOF.exists()
    source_pin=pin(SOURCE)
    p=module('portable_ports_exploratory',SOURCE);f=module('file_script_exploratory',HERE/'file_port_fixture_script_v2.py')
    fixture_path=HERE/'FILE-PORTS-FIXTURES-v3.json';cases=json.loads(fixture_path.read_text(encoding='utf-8'))['cases'];rows=[]
    proposal=json.loads((HERE/'PORTABLE-FILE-PORTS-CORRECTION-PROPOSAL-v1.json').read_text(encoding='utf-8'))
    by={c['id']:c for c in cases}
    for patch in proposal['patches']:
        c=by[patch['id']]
        if patch['script_changed']:c['script']=patch['new_script']
        for k,v in patch['expected_field_changes'].items():c['expected'][k]=v['proposed']
    for case in cases:
        holder=[None];adapter_errors=[]
        def projection():return holder[0].diagnostic_projection() if holder[0] is not None else {}
        script=f.FakeScript(case,observe=projection)
        def clock():return script.clock()
        def api(name,args):
            try:raw=script.api(name,args)
            except f.ScriptMismatch as error:adapter_errors.append(str(error));raise
            return p.RawReturn(raw.value,raw.last_error,raw.error_defined,raw.raw_count,raw.raw_count_defined,raw.buffer,raw.buffer_defined)
        def hook(name):
            try:return script.hook(name)
            except f.ScriptMismatch as error:adapter_errors.append(str(error));raise
        spec=p.FileSpec(r'D:\Fixture\input.bin',3,hashlib.sha256(b'abc').hexdigest())
        def setup(origin):
            owner=p.PortableOwner(origin,api,hook,files=(spec,),output=r'D:\Fixture\output',allowed_entries=tuple(p.EntrySpec('f'+str(i),'file') for i in range(64)),
                admitted_directories=('C:\\','D:\\',r'D:\Fixture',r'D:\Fixture\output',r'D:\Fixture\scan',r'C:\Fixture\platform'))
            holder[0]=owner;initial=case['initial']
            seeded=tuple((s['id'],s['kind'],s['handle'],spec if s['kind']=='original_file' else None) for s in initial['slots'])
            owner.seed_for_tests(namespace_owned=initial['namespace_owned'],reservation_ready=initial['reservation_ready'],slots=seeded,known_read_bytes=initial['known_read_bytes'],hashed_bytes=initial['hashed_bytes'],captured_bytes=initial['captured_bytes'])
            def actions(current):
                for action in case['request']['actions']:
                    op=action['operation'];args=action['arguments']
                    if op=='reserve_namespace_and_journal':current.reserve_namespace(args['path'],b'fixture-reservation\n',b'fixture-first-record\n')
                    elif op=='open_inspect_original':current.open_original(spec)
                    elif op=='hash_capture_original':current.hash_capture(args['slot'])
                    elif op=='close_slot':current.close_slot(args['slot'],args.get('requested_closer'))
                    elif op=='scan_directory':current.scan(args['path'],args['declared_empty'])
                    elif op=='inspect_ancestors':current.inspect_ancestors(tuple(args['paths']))
                    elif op=='write_output_record':current.write_record(args['slot'],bytes.fromhex(args['record_hex']))
                    elif op=='finalize_output':current.finalize_output(args['slot'],b'ABCD')
                    elif op=='create_namespace':current.create_namespace(args['path'])
                    elif op=='decode_raw_BOOL':p.raw_BOOL(args['raw_value'])
                    elif op=='admit_plan':
                        if 'plan_ref' in args:current.admit_plan(case['plan'])
                        else:current.validate_path_syntax(args['path'],args['use'])
                    elif op=='validate_seal_graph':
                        facts=case['request']['facts'];current.validate_seal_graph(tuple(facts['nodes']),tuple(tuple(x) for x in facts['edges']),tuple(facts['operation_outcomes']))
                    elif op=='validate_handoff':
                        facts=case['request']['facts'];port=api if facts['supplied_port']==facts['required_port'] else object();nonce=current.origin.nonce if facts['supplied_nonce']==facts['required_nonce'] else object()
                        for _ in range(facts['handoff_count']):current.validate_handoff(origin=current.origin,port=port,nonce=nonce,serialized_ready=facts['serialized_ready'],cached_own_module=facts['cached_own_module'])
                    else:raise RuntimeError('Unimplemented action interface')
            result=owner.run(actions).to_dict()
            return result
        result=None;exception=None
        try:result=p.begin_injected(clock,setup)
        except BaseException as error:exception=dict(error_class=type(error).__name__,error=str(error)[:256])
        try:script.assert_exhausted();exhausted=True
        except f.ScriptMismatch as error:exhausted=False;adapter_errors.append(str(error))
        differences=[]
        if result is not None:
            for key,value in case['expected'].items():
                if type(result.get(key)) is not type(value) or result.get(key)!=value:differences.append(dict(field=key,expected=value,observed=result.get(key)))
        rows.append(dict(id=case['id'],expected_projection_matches=exception is None and not differences and exhausted,exception=exception,
            source_observation=result,differences=differences,script_exhausted=exhausted,script_index=script.index,script_steps=len(case['script']),adapter_errors=adapter_errors))
    stable=pin(SOURCE)==source_pin
    record=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),status='PROPOSED_INTERFACE_IN_MEMORY_ONLY_NOT_ACCEPTED',source=source_pin,checker=pin(Path(__file__)),fixtures=pin(fixture_path),proposal=pin(HERE/'PORTABLE-FILE-PORTS-CORRECTION-PROPOSAL-v1.json'),
        root_scope=pin(HERE/'FILE-PORTS-PREPARATION-AND-SOURCE-SCOPE-v1.json'),cases=84,matched=sum(r['expected_projection_matches'] for r in rows),rows=rows,source_unchanged=stable,
        scope='Actual portable logic under strict fictional injected API/clock/hook scripts. Expected fields used only in post-run comparison, never by portable source or action decisions. No actual FFI/port/native/file operation.',
        primary_fixture_witness=pin(HERE/'FILE-PORTS-ROOT-PRIMARY-WITNESS-v1.json'),profile_qualified=False,runtime_authorized=False,originals_authenticated=False,actual_API_calls=0,old_original_payload_operations=0)
    with PROOF.open('x',encoding='utf-8') as out:json.dump(record,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(PROOF),matched=record['matched'],cases=84,script_mismatch_cases=sum(not r['script_exhausted'] or bool(r['adapter_errors']) for r in rows))))


if __name__=='__main__':main()
