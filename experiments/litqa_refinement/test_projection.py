"""Entirely invented original execution tree; no benchmark answers or keys."""
import base64
import shutil
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from tether_engine.journal import RunJournal
from tether_engine.serde import canonical,encode,fingerprint
from experiments.litqa_comparison import acquisition,admission,transport
from experiments.litqa_refinement import projection as p
from experiments.litqa_refinement import test_contracts as f
from experiments.litqa_refinement.test_model import MODEL


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(canonical(value))


def proof(path):
    raw=path.read_bytes();return dict(path=str(path),sha256=p.codecs.digest(raw),bytes=len(raw))


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name);self.root=self.base/'original';self.root.mkdir()
        self.queries=[f.query(),dict(f.query(),id='00000000-0000-0000-0000-000000000002')]
        write(self.base/'visible.json',self.queries)
        self.frame=dict(kind='sc04_primary_execution_v1',purpose='fictional_qualification',count=2,
            schedule=[q['id'] for q in self.queries],query_products=dict(answer_queries=proof(self.base/'visible.json'),
            source_queries=proof(self.base/'visible.json')))
        self.cutoff='2099-01-01T00:00:00+00:00'
        for phase in ('collect','answer'):
            write(self.root/phase/'worker/phase/CONFIG.json',dict(stage=phase,ids=self.frame['schedule']))
        for i,q in enumerate(self.queries):self.cell(i,q)
        self.reseal()
        self.activation=self.base/'acceptance.json';write(self.activation,dict(status='accepted',coordinator_only=True))

    def cell(self,i,q):
        collect=self.root/'collect/worker/phase';source_root=collect/'products'/f'{2*i:04d}'
        plan=acquisition.plan(dict(id=q['id'],question=q['question']),'lexical')
        def fetch(url,**kwargs):
            return dict(body=canonical(dict(resultList=dict(result=[]))),status=200,final_url=url,headers={})
        with patch.object(acquisition.legacy,'fetch_http',side_effect=fetch):
            acquisition.acquire(plan,source_root,deadline=time.monotonic()+20)
        source_receipt=proof(source_root/'RECEIPT.json')
        source=dict(root=str(source_root),receipt=source_receipt,manifest=proof(source_root/'MANIFEST.json'),plan=plan)
        write(collect/'slots'/f'{2*i:04d}.json',dict(ordinal=2*i,id=q['id'],branch='L',status='completed',product=source))
        answer=self.root/'answer/worker/phase';cell=answer/'products'/f'{4*i:04d}'
        journal=RunJournal(cell,kind='build')
        context=admission.capture(q,source_root,source_receipt['sha256'],plan,self.cutoff,MODEL)
        request,payload=transport.make_answer_request(q,context.sources,MODEL)
        # Case 1 is a valid but unsupported candidate. Case 2 is native unsure.
        prediction=dict(answer_index=0 if i==0 else 2,evidence_ids=[])
        decision=admission.check(context,prediction,request)
        write(cell/'INPUT.json',dict(task='answer',query=q,items=[]))
        write(cell/'CONTEXT.json',context.report)
        write(cell/'native/request.json',request);write(cell/'native/payload.json',payload)
        body=canonical(dict(content=canonical(prediction).decode()))
        wrapper=dict(body_base64=base64.b64encode(body).decode(),body_sha256=p.codecs.digest(body),complete=True,
                     request_sha256=fingerprint(request),payload_sha256=fingerprint(payload))
        write(cell/'native/native-response.bin',wrapper)
        summary=dict(task='answer',status='completed',decoded=prediction,generation_entered=True,
            query_sha256=fingerprint(q),items_sha256=fingerprint([]),request_sha256=fingerprint(request))
        write(cell/'SUMMARY.json',summary)
        journal.append('model_cell_completed',summary_sha256=fingerprint(summary),status='completed');journal.close()
        row=dict(ordinal=4*i,id=q['id'],branch='L/O',status='completed',product=dict(
            disposition=dict(id=q['id'],producer_status='produced',check_status='accepted' if decision['accepted'] else 'rejected',
                             prediction=prediction,reason=decision['reason']),decision=decision,
            call=dict(summary=summary,summary_proof=proof(cell/'SUMMARY.json'),root=str(cell)),
            context=proof(cell/'CONTEXT.json'),collection_receipt_sha256=source_receipt['sha256'],order=[]))
        write(answer/'slots'/f'{4*i:04d}.json',row)

    def reseal(self):
        write(self.root/'FRAME.json',self.frame)
        phases={}
        for phase in ('collect','answer'):
            phase_root=self.root/phase;stage=phase_root/'worker/phase'
            inventory={x.relative_to(stage).as_posix():{k:proof(x)[k] for k in ('sha256','bytes')}
                for x in stage.rglob('*') if x.is_file() and x.name!='STAGE-RECEIPT.json'}
            write(stage/'STAGE-RECEIPT.json',dict(status='complete',files=inventory))
            inventory={x.relative_to(phase_root).as_posix():proof(x) for x in phase_root.rglob('*')
                       if x.is_file() and x.name!='PACKAGE-RECEIPT.json'}
            write(phase_root/'PACKAGE-RECEIPT.json',dict(status='complete',phase=phase,
                frame_sha256=proof(self.root/'FRAME.json')['sha256'],files=inventory))
            phases[phase]=dict(root=str(phase_root),package_sha256=proof(phase_root/'PACKAGE-RECEIPT.json')['sha256'],
                               stage_receipt_sha256=proof(stage/'STAGE-RECEIPT.json')['sha256'])
        phases.update(expand={},rank={})
        for phase,value in phases.items():write(self.root/(phase+'-ANCHOR.json'),value)
        write(self.root/'COMPLETE.json',dict(status='primary_execution_complete',purpose=self.frame['purpose'],phases=phases,
            scientific_scoring_performed=False,provider_cost_usd=0,source_cutoff=self.cutoff))
        write(self.root/'journal.jsonl',{})
        files={x.name:proof(x) for x in self.root.iterdir() if x.is_file() and x.name!='ROOT-RECEIPT.json'}
        write(self.root/'ROOT-RECEIPT.json',dict(status='primary_execution_complete',frame_sha256=proof(self.root/'FRAME.json')['sha256'],files=files))
        self.descriptor=dict(kind=p.KIND,role='original_sc04_execution',root=str(self.root),root_receipt_sha256=proof(self.root/'ROOT-RECEIPT.json')['sha256'])

    def prepare(self):return p.prepare_baseline(self.descriptor,proof(self.activation),self.base/'projection')

    def test_original_roles_reconstructed_and_worker_projection_minimal(self):
        prepared=self.prepare()
        self.assertEqual(len(prepared.cases),2)
        self.assertEqual(prepared.cases[0]['candidate']['original_admission_status'],'rejected')
        self.assertEqual(prepared.cases[1]['candidate']['prediction']['answer_index'],2)
        self.assertIsNone(prepared.cases[0]['candidate']['generated_at_utc'])
        inputs=p.worker_files(prepared,self.queries[0]['id'])
        self.assertEqual(set(inputs),{'query','candidate','sources'})
        self.assertNotIn(str(self.activation),canonical(prepared.manifest).decode())
        receipt=p.parse_json((Path(prepared.root)/'RECEIPT.json').read_bytes())
        self.assertNotIn('COORDINATOR.json',receipt['files'])
        verified=p.verify_baseline_projection(dict(root=prepared.root,receipt_sha256=prepared.receipt_sha256),self.frame['schedule'])
        self.assertEqual(verified.manifest,prepared.manifest)
        with self.assertRaises(TypeError):prepared.cases[0]['candidate']['prediction']['answer_index']=1

    def test_evaluator_role_rejected_before_any_source_open(self):
        bad=dict(self.descriptor,role='evaluation_only')
        with patch.object(p._Reader,'read',side_effect=AssertionError('must not open')),self.assertRaises(ValueError):
            p.prepare_baseline(bad,proof(self.activation),self.base/'bad')
        for extra in ('reference_keys','doi_annotations','coordinator_acceptance'):
            bad=dict(self.descriptor,**{extra:{}})
            with self.assertRaises(ValueError):p._reconstruct(bad)

    def test_renamed_evaluator_package_and_cross_arm_rejected(self):
        path=self.root/'answer/worker/phase/slots/0000.json';row=p.parse_json(path.read_bytes())
        row['branch']='E/R';write(path,row);self.reseal()
        with self.assertRaisesRegex(ValueError,'Fixed original'):self.prepare()
        self.frame['kind']='sc04_evaluator_analysis_v1';self.reseal()
        with self.assertRaisesRegex(ValueError,'Evaluator'):p._reconstruct(self.descriptor)

    def test_option_annotation_and_tampered_original_rejected(self):
        path=self.base/'visible.json';queries=encode(self.queries);queries[0]['correct_index']=0
        write(path,queries);self.frame['query_products']['answer_queries']=proof(path);self.reseal()
        with self.assertRaises(ValueError):self.prepare()
        write(path,self.queries);self.frame['query_products']['answer_queries']=proof(path);self.reseal()
        source=self.root/'collect/worker/phase/products/0000/responses/000.body';source.write_bytes(b'changed')
        with self.assertRaises(ValueError):p._reconstruct(self.descriptor)

    def test_resealed_candidate_disagrees_with_original_native(self):
        path=self.root/'answer/worker/phase/slots/0000.json';row=p.parse_json(path.read_bytes())
        row['product']['disposition']['prediction']['answer_index']=1;write(path,row);self.reseal()
        with self.assertRaisesRegex(ValueError,'producer disposition'):self.prepare()

    def test_role_label_cannot_promote_copied_or_evaluator_annotated_originals(self):
        # A renamed/copy-root retains original absolute proofs and cannot become
        # a new execution authority just by assigning the right role string.
        copied=self.base/'renamed-evaluator-package';shutil.copytree(self.root,copied)
        disguised=dict(self.descriptor,root=str(copied))
        with self.assertRaisesRegex(ValueError,'root proof location'):p._reconstruct(disguised)
        context_path=self.root/'answer/worker/phase/products/0000/CONTEXT.json'
        annotated=p.parse_json(context_path.read_bytes());annotated['reference_keys']={'fictional':0}
        write(context_path,annotated)
        slot=self.root/'answer/worker/phase/slots/0000.json';row=p.parse_json(slot.read_bytes())
        row['product']['context']=proof(context_path);write(slot,row);self.reseal()
        with self.assertRaisesRegex(ValueError,'evaluator annotations'):p._reconstruct(self.descriptor)

    def test_projection_file_mutation_wrong_schedule_and_reuse_rejected(self):
        prepared=self.prepare();descriptor=dict(root=prepared.root,receipt_sha256=prepared.receipt_sha256)
        with self.assertRaises(ValueError):p.verify_baseline_projection(descriptor,list(reversed(self.frame['schedule'])))
        Path(p.worker_files(prepared,self.queries[0]['id'])['candidate']).write_bytes(b'{}')
        with self.assertRaises(ValueError):p.verify_baseline_projection(descriptor,self.frame['schedule'])
        with self.assertRaises(FileExistsError):self.prepare()


if __name__=='__main__':unittest.main()
