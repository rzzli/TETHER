"""Bounded native-worker controls using invented model interfaces only."""
from contextlib import nullcontext
import base64
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import time
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock,patch

from experiments.alce import native_worker as w
from tether_engine.serde import ContractError, canonical
from tests.test_alce_native_runtime import Model,Tensor,proof,put
from tests.test_alce_offline import SOURCE


def invented_modules(path,fail=False):
    tokenizer=Mock(is_fast=False,legacy=True,eos_token_id=50256)
    tokenizer.return_value=NS(input_ids=Tensor());tokenizer.decode.return_value='1'
    model=Model('bf16')
    if fail:model.generate.side_effect=RuntimeError('invented native failure')
    hf=NS(__file__=str(path),AutoTokenizer=NS(from_pretrained=Mock(return_value=tokenizer)),
          AutoModelForSeq2SeqLM=NS(from_pretrained=Mock(return_value=(model,dict(missing_keys=[],unexpected_keys=[],mismatched_keys=[],error_msgs=[])))))
    torch=NS(__file__=str(path),bfloat16='bf16',inference_mode=nullcontext,set_num_threads=Mock(),
        cuda=NS(is_available=lambda:True,reset_peak_memory_stats=Mock(),max_memory_allocated=lambda _:42,
                max_memory_reserved=lambda _:84,get_device_properties=lambda _:NS(total_memory=10000),set_per_process_memory_fraction=Mock()))
    return dict(torch=torch,transformers=hf)


def sample():return dict(process_bytes=20,process_peak_bytes=20,available_host_bytes=500,cpu_seconds=.01,offload_bytes=0,offload_files=0)


def invented_execute(p,fail=False):
    value=json.loads(Path(p['path']).read_bytes());module_path=Path(value['runtime_sources']['torch']['path'])
    modules=invented_modules(module_path,fail)
    assets=NS(product='true_nli',root=Path(value['acquisition_receipt']['path']).parent,revalidate=Mock(),
              provenance=lambda:dict(product='true_nli',invented=True))
    return w.execute(p,module_loader=lambda **kw:modules,asset_loader=lambda *a,**kw:assets,resource_sampler=sample)


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.module=self.root/'invented.py';self.module.write_text('# invented native dependency\n')
        source=self.root/'urllib3/util/connection.py';source.parent.mkdir(parents=True);source.write_text(SOURCE)
        record=self.root/'urllib3-9.9.dist-info/RECORD';record.parent.mkdir()
        h=base64.urlsafe_b64encode(hashlib.sha256(source.read_bytes()).digest()).rstrip(b'=').decode()
        record.write_text(f'urllib3/util/connection.py,sha256={h},{source.stat().st_size}\n')
        acq=self.root/'acquisition';acq.mkdir();ap=put(acq/'RECEIPT.json',dict(invented=True))
        request=dict(logical_model=w.runtime.MODELS['true_nli'][0],max_new_tokens=10,premise='Invented evidence',hypothesis='Invented claim',
            input_text='premise: Invented evidence hypothesis: Invented claim')
        self.rows=[dict(id=f'invented-{i}',request=dict(request)) for i in range(2)]
        self.job=dict(schema_version=1,kind='alce_native_job_v1',operation='true',purpose='qualification',
            acquisition_receipt=ap,inputs=put(self.root/'INPUT.json',self.rows),output=str(self.root/'worker'),
            interpreter=proof(Path(sys.executable).resolve()),offline=dict(record=proof(record),connection=proof(source)),
            limits=dict(seconds=15,process_bytes=100,minimum_available_host_bytes=100,gpu_bytes=8000,offload_bytes=10000,
                        max_calls=2,input_bytes=100000,output_bytes=1000000,cpu_threads=1),
            placement=dict(gpu_bytes=6000,cpu_bytes=10000),native_sources={},code_pins=w.source_pins(),
            runtime_sources=dict(torch=proof(self.module),transformers=proof(self.module)))
        self.jp=put(self.root/'JOB.json',self.job)

    def test_invented_whole_worker_has_exact_results_journal_and_offline_scope(self):
        p=invented_execute(self.jp);self.assertTrue(Path(p['path']).is_file())
        got=w.verify_worker(Path(self.job['output']),self.jp,self.job,self.rows,time.monotonic()+10)
        self.assertEqual(got,p)
        c=json.loads((Path(self.job['output'])/'COMPLETE.json').read_bytes())
        self.assertEqual(len(c['result_files']),2)
        self.assertEqual(c['offline']['denied_network_attempts'],0)
        self.assertEqual(len(c['native']['calls']),2)

    def test_worker_native_failure_keeps_one_failed_call_and_no_success(self):
        with self.assertRaises(RuntimeError):invented_execute(self.jp,True)
        root=Path(self.job['output']);failure=json.loads((root/'FAILURE.json').read_bytes())
        self.assertEqual(len(failure['native']['calls']),1)
        self.assertEqual(failure['native']['calls'][0]['status'],'failed')
        self.assertFalse((root/'WORKER-RECEIPT.json').exists())

    def test_invalid_source_or_overlapping_output_never_writes_or_imports(self):
        for defect in ('source','output'):
            changed=dict(self.job)
            if defect=='source':changed['code_pins']={}
            else:changed['output']=str(self.root/'acquisition'/'bad')
            p=put(self.root/'BAD.json',changed)
            loader=Mock()
            with self.assertRaises(ContractError):w.execute(p,module_loader=loader)
            loader.assert_not_called();self.assertFalse(Path(changed['output']).exists())

    def test_duplicate_missing_and_excess_schedule_rejected(self):
        for rows in ([self.rows[0],self.rows[0]],[],self.rows+[dict(self.rows[0],id='extra')]):
            self.job['inputs']=put(self.root/'INPUT.json',rows);p=put(self.root/'JOB.json',self.job)
            with self.assertRaises(ContractError):w.load_job(p)
        self.assertFalse(Path(self.job['output']).exists())

    def test_unknown_and_exhausted_resource_observations_fail(self):
        limits=self.job['limits']
        for changed in (dict(process_bytes=None),dict(process_bytes=101),dict(available_host_bytes=99),dict(offload_bytes=10001)):
            with self.subTest(change=changed),self.assertRaises(ContractError):w.check_resources(dict(sample(),**changed),limits)
        w.check_resources(sample(),limits)

    def test_resource_watchdog_retains_abort_without_real_process_exit(self):
        out=self.root/'watch';out.mkdir();stop=Mock()
        watcher=w.ResourceWatchdog(out,self.job['limits'],sample=lambda:dict(sample(),process_bytes=101),terminate=stop)
        watcher.stop.wait=lambda _:False
        watcher.poll()
        stop.assert_called_once_with(125);self.assertTrue((out/'RESOURCE-LIMIT.json').is_file())

    def test_sampler_thread_must_stop_before_success(self):
        watcher=w.ResourceWatchdog(self.root,self.job['limits'],sample=sample,terminate=Mock())
        watcher.thread=Mock();watcher.thread.is_alive.return_value=True
        with self.assertRaises(ContractError):watcher.__exit__(None,None,None)

    def test_resealed_resource_gpu_and_call_clock_claims_rejected(self):
        invented_execute(self.jp);root=Path(self.job['output'])
        receipt=json.loads((root/'WORKER-RECEIPT.json').read_bytes())
        baseline=json.loads((root/'COMPLETE.json').read_bytes())
        from experiments.scifact_multivers_transport.download import verify_journal
        journal_events=verify_journal(root/'journal.jsonl')
        changes=(lambda c:c['resource_samples'][0].update(process_bytes=101),
                 lambda c:c['resource_samples'][0].update(available_host_bytes=None),
                 lambda c:c['native']['gpu'].update(peak_allocated_bytes=8001),
                 lambda c:c['native']['calls'][0].update(elapsed_seconds=-1))
        for i,change in enumerate(changes):
            value=json.loads(json.dumps(baseline));change(value)
            (root/'journal.jsonl').unlink();journal=w.Journal(root/'journal.jsonl')
            for event in journal_events:
                details=dict(event['details'])
                if i==3 and event['event']=='call_completed' and details['ordinal']==0:details['elapsed_seconds']=-1
                journal.append(event['event'],**details)
            receipt['files']['journal.jsonl']=proof(root/'journal.jsonl')
            receipt['files']['COMPLETE.json']=put(root/'COMPLETE.json',value);put(root/'WORKER-RECEIPT.json',receipt)
            with self.subTest(case=i),self.assertRaises(ContractError):w.verify_worker(root,self.jp,self.job,self.rows,time.monotonic()+10)

    def test_resealed_omission_failure_status_or_unknown_directory_rejected(self):
        invented_execute(self.jp);root=Path(self.job['output'])
        receipt=json.loads((root/'WORKER-RECEIPT.json').read_bytes())
        baseline=(root/'COMPLETE.json').read_bytes()
        for defect in ('denial','omission','failure','directory'):
            (root/'COMPLETE.json').write_bytes(baseline)
            value=json.loads(baseline)
            if defect=='denial':value['offline']['denied_network_attempts']=1
            if defect=='omission':value['native']['calls'].pop()
            if defect=='failure':(root/'FAILURE.json').write_bytes(b'{}')
            if defect=='directory':(root/'unlisted').mkdir()
            receipt['files']['COMPLETE.json']=put(root/'COMPLETE.json',value);put(root/'WORKER-RECEIPT.json',receipt)
            with self.subTest(defect=defect),self.assertRaises(ContractError):w.verify_worker(root,self.jp,self.job,self.rows,time.monotonic()+10)
            if defect=='failure':(root/'FAILURE.json').unlink()
            if defect=='directory':(root/'unlisted').rmdir()

    def test_output_write_failure_is_retained_and_never_retried(self):
        original=w.write_new
        def write(path,value):
            if path.name=='000000.json':raise OSError('invented storage failure')
            return original(path,value)
        with patch.object(w,'write_new',side_effect=write),self.assertRaises(OSError):invented_execute(self.jp)
        failure=json.loads((Path(self.job['output'])/'FAILURE.json').read_bytes())
        self.assertEqual(len(failure['native']['calls']),1)
        self.assertFalse((Path(self.job['output'])/'WORKER-RECEIPT.json').exists())

    def test_metadata_and_journal_share_aggregate_output_ceiling(self):
        self.job['limits']['output_bytes']=1000;self.jp=put(self.root/'JOB.json',self.job)
        with self.assertRaises(ContractError):invented_execute(self.jp)
        root=Path(self.job['output'])
        self.assertFalse((root/'WORKER-RECEIPT.json').exists())
        regular=[p for p in root.rglob('*') if p.is_file() and p.name!='FAILURE.json' and not p.is_relative_to(root/'offload')]
        self.assertLessEqual(sum(p.stat().st_size for p in regular),1000)

    def test_journal_larger_than_legacy_transport_cap_verifies_streaming(self):
        self.job['limits']['output_bytes']=12*1024**2;self.jp=put(self.root/'JOB.json',self.job)
        original=w.runtime.TrueRuntime
        class ObservedRuntime(original):
            def __call__(instance,request):
                for _ in range(5):instance.emit('cache_instrumentation',dict(invented_observation='x'*(512*1024)))
                return super().__call__(request)
        with patch.object(w.runtime,'TrueRuntime',ObservedRuntime):invented_execute(self.jp)
        root=Path(self.job['output']);self.assertGreater((root/'journal.jsonl').stat().st_size,4*1024**2)
        w.verify_worker(root,self.jp,self.job,self.rows,time.monotonic()+15)

    def test_resealed_native_result_cannot_differ_from_captured_observation(self):
        invented_execute(self.jp);root=Path(self.job['output'])
        baseline=json.loads((root/'COMPLETE.json').read_bytes())
        receipt=json.loads((root/'WORKER-RECEIPT.json').read_bytes())
        for changed in (2,0,True):
            result=put(root/'results/000000.json',dict(id=self.rows[0]['id'],result=changed))
            complete=json.loads(json.dumps(baseline));complete['result_files'][0]=result
            receipt['files']['results/000000.json']=result
            receipt['files']['COMPLETE.json']=put(root/'COMPLETE.json',complete)
            put(root/'WORKER-RECEIPT.json',receipt)
            with self.subTest(value=changed),self.assertRaises(ContractError):w.verify_worker(root,self.jp,self.job,self.rows,time.monotonic()+10)

    def test_real_harmless_child_supervisor_and_root_receipt(self):
        script=self.root/'child.py'
        code='import sys,json\nfrom pathlib import Path\n'
        code+='sys.path[:0]='+repr([str(w.ROOT),str(w.ROOT/'src'),str(w.ROOT/'packages/tether/src')])+'\n'
        code+='from tests.test_alce_native_worker import invented_execute,proof\n'
        code+='p=proof(Path(sys.argv[1]));invented_execute(p)\n'
        script.write_text(code)
        original=w.processes.supervise_command
        def launch(command,*,limits):return original([sys.executable,'-I','-B',str(script),self.jp['path']],limits=limits)
        with patch.object(w,'contain_process_tree',return_value=object()),patch.object(w.processes,'supervise_command',side_effect=launch):
            p=w.supervise(self.jp,self.root/'supervisor')
        self.assertEqual(json.loads(Path(p['path']).read_bytes())['status'],'verified')

    def test_real_harmless_child_timeout_retains_closed_process(self):
        self.job['limits']['seconds']=1;self.jp=put(self.root/'JOB.json',self.job)
        original=w.processes.supervise_command
        def launch(command,*,limits):
            return original([sys.executable,'-I','-B','-c','import time;time.sleep(60)'],
                            limits=w.processes.ProcessLimits(.2,limits.max_output_bytes))
        with patch.object(w,'contain_process_tree',return_value=object()),patch.object(w.processes,'supervise_command',side_effect=launch):
            with self.assertRaises(Exception):w.supervise(self.jp,self.root/'supervisor')
        proc=json.loads((self.root/'supervisor/PROCESS.json').read_bytes())
        self.assertTrue(proc['supervision']['process_reaped']);self.assertEqual(proc['supervision']['termination_reason'],'deadline_exceeded')
        self.assertFalse((self.root/'supervisor/RECEIPT.json').exists())


if __name__=='__main__':unittest.main()
