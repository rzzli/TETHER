"""Independent sealed-input, projection and pre-dispatch denial probes."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
from fixture import build, save, ROOT, HERE
from tether import _catalog_binding as b, _presentation as layer
from asof.serde import ContractError, canonical, fingerprint


def request(f):
    root=f["root"]
    return b.PolicyRequest(root/"policy.json",root/"roots.json",root/"case.json",root/"normalized/snapshot.json",
                           root/"catalog.json","fictional-use",f["frame"])


def argv(f,output):
    root=f["root"]
    return ["run","--case",str(root/"case.json"),"--snapshot",str(root/"normalized/snapshot.json"),
            "--catalog",str(root/"catalog.json"),"--output",str(output),
            "--catalog-policy",str(root/"policy.json"),"--policy-roots",str(root/"roots.json"),
            "--policy-use","fictional-use","--policy-frame-sha256",f["frame"]]


def main():
    checks=[];trees=[]
    def check(name,condition):
        checks.append(dict(name=name,passed=bool(condition)))
        if not condition:raise AssertionError(name)
    def denied(name,callback):
        try:callback()
        except ContractError as error:checks.append(dict(name=name,passed=True,error=str(error)))
        else:raise AssertionError(name+": accepted")
    def fixture(name,**options):
        f=build(name,with_mapping=True,**options);trees.append(str(f['root']));return f
    def prepare(f):
        out=f['root']/'prepared';out.mkdir();return out,b.prepare_policy_run(out,request(f))
    def reseal_binding(out,descriptor,mutate):
        path=out/descriptor['path'];doc=json.loads(path.read_text());mutate(doc)
        save(path,doc);return dict(path=descriptor['path'],sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size)
    try:
        f=fixture('peer-toctou');out=f['root']/'outer';req=request(f)
        original=b.prepare_policy_run;calls=[];limits=layer.ProcessLimits(timeout_seconds=30,max_output_bytes=32768)
        def inspect_then_change(output,selected):
            descriptor=original(output,selected)
            for path in [selected.policy_path,selected.roots_path,selected.case_path,selected.snapshot_path,selected.catalog_path,
                         f['root']/'evidence/check.json',f['root']/'normalized/packets/evidence.json',
                         f['root']/'normalized/mappings/nested/mapping.json']:
                path.write_bytes(b'changed original after checked copy\n')
            return descriptor
        def execute(child_argv):
            calls.append(child_argv)
            return layer.invoke_engine(child_argv,limits=limits)
        with patch.object(b,'prepare_policy_run',inspect_then_change):
            summary=layer.create_outer(out,argv(f,out),policy_request=req,engine=execute,limits=limits)
        verified=layer.verify_outer(out,summary['receipt_sha256'])
        check('mutated original controls not reopened',verified['status']=='integrity_verified')
        check('single actual offline child',len(calls)==1)
        check('nested packet copied', (out/'catalog-policy/inputs/packets/evidence.json').is_file())
        check('nested computed mapping copied',(out/'catalog-policy/inputs/mappings/nested/mapping.json').is_file())
        check('child receives sealed case/snapshot/projection',all(str(out/'catalog-policy') in calls[0][calls[0].index(flag)+1] for flag in ('--case','--snapshot','--catalog')))
        check('child receives no policy wrapper flags',not any(x.startswith('--policy-') or x=='--catalog-policy' for x in calls[0]))
        check('qualified policy result separated',verified.get('artifact_policy',{}).get('status')=='artifact_policy_consistency_verified')

        f=fixture('peer-future-records');out=f['root']/'outer'
        packet_path=f['root']/'normalized/packets/evidence.json'
        packet=json.loads(packet_path.read_text())
        for observation in packet['observations']:
            observation['availability']['record_public_at']='2025-01-01'
            observation['availability']['annotation_public_at']='2025-01-01'
        new_hash=save(packet_path,packet)
        f['snapshot']['artifacts'][0]['sha256']=new_hash
        record=f['policy']['artifacts'][-1];old_id=record['artifact_id']
        record.update(sha256=new_hash,bytes=packet_path.stat().st_size)
        from tether._catalog_policy import artifact_id
        record['artifact_id']=artifact_id(record)
        next(g for g in f['policy']['uses'][0]['grants'] if g['artifact_id']==old_id)['artifact_id']=record['artifact_id']
        f['policy']['uses'][0]['snapshot_fingerprint']=fingerprint(f['snapshot'])
        save(f['root']/'normalized/snapshot.json',f['snapshot']);save(f['root']/'policy.json',f['policy'])
        summary=layer.create_outer(out,argv(f,out),policy_request=request(f),limits=limits)
        verified=layer.verify_outer(out,summary['receipt_sha256'])
        engine_run=json.loads((out/'engine/run.json').read_text())
        ledger=json.loads((out/'engine/ledger.json').read_text())
        check('future record publications produce zero backend calls',engine_run['calls']==0)
        check('future record publications never reach ledger',ledger['claims']==[])
        check('policy admission remains distinct from excluded records',verified['artifact_policy']['checked_inputs']==3)

        for kind in ('wrong_frame','missing_evidence','evidence_hash','transport_receipt','synthetic_profile','scorer'):
            f=fixture('peer-deny-'+kind);out=f['root']/'outer';req=request(f);arguments=argv(f,out);calls=[]
            if kind=='wrong_frame':req=replace(req,frame_sha256='a'*64)
            elif kind=='missing_evidence':(f['root']/'evidence/check.json').unlink()
            elif kind=='evidence_hash':(f['root']/'evidence/check.json').write_bytes(b'changed')
            elif kind=='transport_receipt':(f['root']/'raw/receipts/source.json').write_bytes(b'changed')
            elif kind=='synthetic_profile':
                f['snapshot']['profile']='synthetic_demo';f['policy']['uses'][0]['profile']='synthetic_demo'
                f['policy']['uses'][0]['snapshot_fingerprint']=fingerprint(f['snapshot'])
                save(f['root']/'normalized/snapshot.json',f['snapshot']);save(f['root']/'policy.json',f['policy'])
            else:arguments+=['--scorer','unused.json']
            def forbidden(_):calls.append(True);raise AssertionError('engine must not launch')
            try:layer.create_outer(out,arguments,policy_request=req,engine=forbidden)
            except (ContractError,OSError):pass
            else:raise AssertionError(kind+' was accepted')
            check(kind+': zero engine calls',not calls)
            check(kind+': failed outer readable',layer.inspect_outer(out)['failure'] is not None)
            check(kind+': no success receipt',not (out/layer.RECEIPT).exists())

        f=fixture('peer-raw-receipt-change');out,descriptor=prepare(f)
        (f['root']/'raw/receipts/source.json').write_bytes(b'changed mutable transport receipt')
        denied('changed original receipt cannot override archived copy',lambda:b.verify_policy_run(out,descriptor,check_engine=False))

        f=fixture('peer-legacy-separator',legacy_separator=True);out,descriptor=prepare(f)
        check('pinned legacy separator spelling accepted without rewriting receipt',
              b.verify_policy_run(out,descriptor,check_engine=False)['checked_inputs']==3)
        check('original receipt separator bytes preserved',
              json.loads((f['root']/'raw/receipts/source.json').read_text())['relative_path']=='originals\\raw-inputs.json')

        f=fixture('peer-projection-substitution');out,descriptor=prepare(f)
        projection=out/'catalog-policy/projection.json';doc=json.loads(projection.read_text())
        next(row for row in doc['datasets'] if row['dataset_id']=='vbt_linkage')['roles']=['reference']
        save(projection,doc)
        def bind_new_projection(seal):seal['controls']['projection'].update(sha256=hashlib.sha256(projection.read_bytes()).hexdigest(),bytes=projection.stat().st_size)
        descriptor=reseal_binding(out,descriptor,bind_new_projection)
        denied('rehashed generic projection cannot grant optional evaluator product',lambda:b.verify_policy_run(out,descriptor,check_engine=False))

        f=fixture('peer-binding-omission');out,descriptor=prepare(f)
        descriptor=reseal_binding(out,descriptor,lambda seal:seal['controls'].pop('policy'))
        denied('rehashed omitted policy rejected',lambda:b.verify_policy_run(out,descriptor,check_engine=False))

        f=fixture('peer-frame-transplant');out,descriptor=prepare(f)
        descriptor=reseal_binding(out,descriptor,lambda seal:seal.update(frame_sha256='b'*64))
        denied('rehashed cross-frame binding rejected',lambda:b.verify_policy_run(out,descriptor,check_engine=False))
        status='passed'
    except BaseException as error:
        status='failed';checks.append(dict(name='unexpected',passed=False,error_class=type(error).__name__,error=str(error)));raise
    finally:
        files=['_catalog_policy.py','_catalog_binding.py','_presentation.py','_cli.py']
        record=dict(schema_version=1,status=locals().get('status','failed'),checks=checks,fixture_trees=trees,
                    recorded_at_utc=datetime.now(timezone.utc).isoformat(),
                    code_sha256={name:hashlib.sha256((ROOT/'packages/tether/src/tether'/name).read_bytes()).hexdigest() for name in files})
        path=HERE/('BINDING-PROBES-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
        path.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(dict(status=record['status'],checks=len(checks),report=str(path))))


if __name__=='__main__':main()
