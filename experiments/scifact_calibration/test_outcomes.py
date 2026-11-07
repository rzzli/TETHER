"""Invented source, native artifact and strict-outcome boundary controls."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical, parse_json
from . import outcomes as o
from .test_inputs import fixture as preparation_fixture, proof, write
from .test_calibration import row
from . import calibration as c
from experiments.scifact_comparison.worker import Writer, process_requests


class InventedSolver:
    def __init__(self,calibration,dev_evidence=False):self.calibration=calibration;self.dev_evidence=dev_evidence
    def predict(self,claims,corpus,*,pair_deadline_seconds,event):
        cid=claims[0]['id'];doc=corpus[0];did=doc['doc_id']
        if self.calibration:event(event='pair_attempt_reserved',claim_id=cid,abstract_id=did,seconds=pair_deadline_seconds)
        event(event='pair_started',claim_id=cid,abstract_id=did)
        label=('SUPPORT' if cid%2 else 'CONTRADICT') if self.calibration and cid==did else 'NEI'
        if not self.calibration and self.dev_evidence:label='SUPPORT'
        index=('CONTRADICT','NEI','SUPPORT').index(label);ps=[.1,.1,.1];ps[index]=.8
        selected=[0] if label!='NEI' else []
        prediction=dict(claim_id=cid,abstract_id=did,predicted_label=label,predicted_rationale=selected,
            label_probs=ps,rationale_probs=[.8 if i in selected else .1 for i in range(len(doc['abstract']))])
        observations=dict(token_count=10)
        event(event='pair_completed',claim_id=cid,abstract_id=did,prediction=prediction,**observations)
        return dict(status='completed',pair_predictions=[prediction],observations=[observations])


def inventory(root):
    return {p.relative_to(root).as_posix():proof(p) for p in root.rglob('*') if p.is_file()}


def reseal_calibration(root):
    """Adversarial fixture resealing; scientific records are never touched."""
    events=[parse_json(line) for line in (root/'journal.jsonl').read_bytes().splitlines()]
    previous='0'*64
    for event in events:
        details=event['details']
        if event['event'] in ('pair_committed','claim_committed'):
            details['sha256']=proof(root/details['path'])['sha256']
        if event['event']=='pair_completed':
            pair=parse_json((root/f'pairs/{details["claim_id"]}-{details["abstract_id"]}.json').read_bytes())
            details['prediction']=pair['prediction']
        event.pop('sha256');event['previous_sha256']=previous;previous=o.digest(canonical(event));event['sha256']=previous
    (root/'journal.jsonl').write_bytes(b''.join(canonical(event)+b'\n' for event in events))
    status=parse_json((root/'STATUS.json').read_bytes());status['files']={k:v for k,v in inventory(root).items() if k not in ('STATUS.json','RECEIPT.json')}
    write(root/'STATUS.json',status);receipt=parse_json((root/'RECEIPT.json').read_bytes())
    receipt['files']={k:v for k,v in inventory(root).items() if k!='RECEIPT.json'};return write(root/'RECEIPT.json',receipt)


def producer_fixture(root,requests,request_proof,partition,*,dev_evidence=False):
    calibration=partition=='calibration';condition='calibration' if calibration else 'primary'
    recipe=dict(schema_version=1,kind='sc05_calibration_worker_v1' if calibration else 'sc03_condition_worker',
        purpose='calibrate',mode='qualification',condition=condition,schedule=[r['id'] for r in requests],
        requests=request_proof,pair_seconds=120,output_bytes=2*1024**3)
    recipe_path=root.parent/(root.name+'-recipe.json');write(recipe_path,recipe)
    root.mkdir();writer=Writer(root,2*1024**3);writer.publish('recipe.json',recipe)
    if calibration:writer.event('calibration_reserved',recipe_sha256=proof(recipe_path)['sha256'],purpose='calibrate',mode='qualification')
    writer.event('inputs_admitted',requests_sha256=request_proof['sha256'],references_read=False,condition=condition)
    if calibration:
        policy=dict(ipv6_import_probe='disabled_without_socket_call',
            project_distribution_discovery='exact_project_import_roots_excluded',
            windows_version_probe='native_fallback_without_shell' if os.name=='nt' else 'not_applicable',
            network_and_child_audit='unconditionally_denied',sys_path_modified=False)
        writer.publish('DEPENDENCY-POLICY.json',policy)
        writer.event('dependency_discovery_isolated',policy=policy)
        writer.event('model_load_started')
    writer.publish('MODEL.json',dict(metadata=dict(hparams=dict(label_threshold=None,rationale_threshold=.5,num_labels=3))))
    if calibration:writer.event('model_load_completed')
    counts=process_requests(requests,InventedSolver(calibration,dev_evidence),writer,condition)
    if calibration:
        writer.publish('RESOURCES.json',dict(counts=counts));writer.event('calibration_completed',counts=counts);writer.close()
        (root/'io-audit.jsonl').write_bytes(canonical(dict(event='open',allowed=True,basis='declared_file_or_runtime'))+b'\n')
        states=[dict(claim_id=r['id'],abstract_id=d['doc_id'],state='completed',native_started=True,native_returned=True,attempt_reserved=True) for r in requests for d in r['documents']]
        write(root/'STATUS.json',dict(schema_version=1,kind='sc05_calibration_worker_status_v1',status='completed',
            counts=counts,pair_states=states,recipe_sha256=proof(recipe_path)['sha256'],files=inventory(root),error=None,
            references_read=False,scientific_scoring_performed=False,automatic_retry=False,hard_deadline=False,io_denials=0))
        write(root/'RECEIPT.json',dict(schema_version=1,kind='sc05_calibration_worker_receipt_v1',status='completed',
            recipe_sha256=proof(recipe_path)['sha256'],files=inventory(root)))
    else:
        writer.publish('REPORT.json',dict(status='schedule_accounted',counts=counts));writer.event('condition_completed',counts=counts)
        writer.publish('RECEIPT.json',dict(status='complete',files=dict(writer.files),journal_records=writer.sequence,
            journal_last_sha256=writer.previous,recipe_sha256=proof(recipe_path)['sha256'],requests_sha256=request_proof['sha256']))
        writer.close()
    return dict(root=str(root),receipt=proof(root/'RECEIPT.json'),recipe=proof(recipe_path),requests=request_proof)


def fixture(root,partition='calibration',*,dev_evidence=False):
    transition,source,prepared=preparation_fixture(root)
    manifest=parse_json((prepared/'manifest.json').read_bytes())
    queries=[parse_json(x) for x in (prepared/f'views/queries_{partition}.jsonl').read_bytes().splitlines()]
    corpus=[parse_json(x) for x in (prepared/'views/corpus.jsonl').read_bytes().splitlines()]
    byid={d['doc_id']:d for d in corpus};requests=[];retrieval=[]
    for query in queries:
        docs=([query['id']] if query['id'] in byid else [])+[d for d in byid if d!=query['id']]
        docs=docs[:5]
        if partition=='dev' and dev_evidence:docs.reverse()
        requests.append(dict(id=query['id'],claim=query['claim'],documents=[byid[d] for d in docs]))
        retrieval.append(dict(id=query['id'],retrieved=[dict(doc_id=d,rank=i+1,score=1.-.1*i,
            document_sha256=o.digest(canonical(byid[d]))) for i,d in enumerate(docs)]))
    requests_path=root/'requests.jsonl';requests_path.write_bytes(b''.join(canonical(r)+b'\n' for r in requests))
    producer=producer_fixture(root/'producer',requests,proof(requests_path),partition,dev_evidence=dev_evidence)
    retrieved_path=root/'retrieval.jsonl'
    if partition=='calibration':
        write(retrieved_path,dict(kind='sc05_calibration_retrieval_v1',purpose='calibrate',schedule=[q['id'] for q in queries],
            requests=requests,retrieval=retrieval,transition=proof(transition),classifier_called=False,
            fit_performed=False,reference_products_read=False));format='sc05_bundle'
    else:
        retrieved_path.write_bytes(b''.join(canonical(r)+b'\n' for r in retrieval));format='jsonl'
    producer.update(retrieval=proof(retrieved_path),retrieval_format=format,admission=None)
    mapping=None
    if partition=='dev':
        train=tuple(source['expected_calibration_ids']);original=tuple(row(cid,.4+.1*(i%4),int(i%4>=2)) for i,cid in enumerate(train))
        fitted=c.fit_calibration(original,train,{cid:str(i%3) for i,cid in enumerate(train)},purpose='fictional_qualification')
        mapping=write(root/'sealed-map.json',fitted.main.payload())
        admission=root/'admission';admission.mkdir();dispositions=[];checks=[]
        configuration=dict(method='multivers_fever_sci_zero_shot',precision='float32',force_rationale=False,max_tokens=4096,
            retrieval='retained_baseline_top5',label_threshold=None,rationale_threshold=.5,label_order=['CONTRADICT','NEI','SUPPORT'])
        model=write(root/'original-model.json',dict(kind='sc03_external_pretrained_model',configuration=configuration,
            local_fitting_performed=False,producer_code=dict(sha256='a'*64),acquisition_receipt=dict(sha256='b'*64)))
        old_frame=write(root/'original-analysis-frame.json',dict(model=model,references=proof(prepared/'restricted/references_dev.jsonl')))
        for query,request,retrieved in zip(queries,requests,retrieval):
            cid=query['id'];claim=parse_json((root/f'producer/claims/{cid}.json').read_bytes());pred=claim['prediction']
            if claim['status']!='produced':
                dispositions.append(dict(id=cid,producer_status='input_unavailable',check_status='not_run',prediction=None,reason='Invented overlength.'))
                continue
            dispositions.append(dict(id=cid,producer_status='produced',check_status='accepted',prediction=pred,reason=None))
            native_request=dict(schema_version=1,benchmark_id='scifact',release_sha256=manifest['archive']['sha256'],claim_id=cid,
                claim_sha256=o.digest(canonical(query)),corpus_sha256=manifest['products']['corpus']['sha256'],
                model_sha256=model['sha256'],configuration_sha256=o.digest(canonical(configuration)))
            resources=dict(wall_seconds=claim['wall_seconds'],cpu_seconds=claim['cpu_seconds'],input_bytes=len(canonical(request)),
                output_bytes=len(canonical(claim)),examples=1,provider_cost_usd=0,token_usage_reason='not_applicable_non_llm',
                model_input_tokens=None,model_output_tokens=None,tokenizer_identity=None,provider_usage=None)
            bindings=[dict(doc_id=int(did),sentence_id=i,text_sha256=o.digest(byid[int(did)]['abstract'][i].encode()))
                      for did,evidence in pred['evidence'].items() for i in evidence['sentences']]
            envelope=dict(prediction_sha256=o.digest(canonical(pred)),request_sha256=o.digest(canonical(native_request)),
                retrieved=retrieved['retrieved'],source_bindings=bindings,producer_code_sha256='a'*64,resources=resources)
            measured=dict(input_tokens=50,generated_output_tokens=0,tokenizer_assets_receipt_sha256='b'*64,
                mode='non_autoregressive_sequence_and_sentence_classification',pair_observations=[dict(token_count=10)]*5)
            checks.append(dict(candidate=dict(kind='accepted_candidate',scientific_validation='not_performed',prediction=pred,
                request=native_request,envelope=envelope),input_sha256=o.digest(canonical(request)),measured_transformer_resources=measured))
        disp=write(admission/'DISPOSITIONS.json',dispositions);check=write(admission/'CHECKS.json',checks)
        received=write(admission/'RECEIPT.json',dict(status='complete',frame_sha256=old_frame['sha256'],files=inventory(admission)))
        producer['admission']=dict(receipt=received,dispositions=disp,checks=check,frame=old_frame)
    paths=[Path(o.__file__),o.ROOT/'experiments/scifact_calibration/calibration.py',o.ROOT/'experiments/scifact_calibration/inputs.py',
           o.ROOT/'experiments/scifact/evaluate.py',o.ROOT/'experiments/scifact/native_contract.py']
    frame=dict(schema_version=1,kind=o.KIND,purpose='evaluate',mode='fictional_qualification',partition=partition,policy=o.POLICY,
        preparation_transition=proof(transition),expected_ids=[q['id'] for q in queries],producer=producer,
        code_files=[proof(p) for p in paths],sealed_mapping=mapping)
    path=root/'outcomes-frame.json';write(path,frame)
    return path,frame,prepared


class StrictTests(unittest.TestCase):
    def setUp(self):self.corpus={1:dict(abstract=[str(i) for i in range(9)]),2:dict(abstract=['other'])}
    def evaluate(self,evidence,predicted,**kwargs):
        return o.strict_outcome(dict(id=1,evidence=evidence),dict(id=1,evidence=predicted),
            produced=True,admitted=kwargs.get('admitted',True),corpus=self.corpus)
    def test_exact_documents_labels_and_prefix_not_uncapped_overlap(self):
        gold={'1':[dict(label='SUPPORT',sentences=[3])]}
        self.assertEqual(self.evaluate(gold,{'1':dict(label='SUPPORT',sentences=[0,1,2,3])}),0)
        self.assertEqual(self.evaluate(gold,{'1':dict(label='SUPPORT',sentences=[1,3])}),1)
        self.assertEqual(self.evaluate(gold,{'1':dict(label='CONTRADICT',sentences=[3])}),0)
        self.assertEqual(self.evaluate(gold,{}),0)
        self.assertEqual(self.evaluate(gold,{'1':dict(label='SUPPORT',sentences=[3]),'2':dict(label='SUPPORT',sentences=[0])}),0)
    def test_alternative_sets_long_minimum_and_empty_gold(self):
        gold={'1':[dict(label='SUPPORT',sentences=[0,1,2,3]),dict(label='SUPPORT',sentences=[4,5,6,7])]}
        self.assertEqual(self.evaluate(gold,{'1':dict(label='SUPPORT',sentences=[4,5,6,7,8])}),1)
        self.assertEqual(self.evaluate({},{}),1);self.assertEqual(self.evaluate({}, {},admitted=False),0)
        self.assertEqual(o.strict_outcome(dict(id=1,evidence={}),None,produced=False,admitted=False,corpus=self.corpus),0)
    def test_invalid_or_conflicting_indices_and_boolean_identity_rejected(self):
        gold={'1':[dict(label='SUPPORT',sentences=[0])]}
        for indices in ([True],[9],[0,0],[1,0]):
            with self.subTest(indices=indices),self.assertRaises(ValueError):self.evaluate(gold,{'1':dict(label='SUPPORT',sentences=indices)})
        with self.assertRaises(ValueError):self.evaluate({'1':[dict(label='SUPPORT',sentences=[0]),dict(label='CONTRADICT',sentences=[1])]}, {})


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.path,self.frame,self.prepared=fixture(self.root)
    def read(self):return o.reconstruct_partition(self.path,proof(self.path)['sha256'])
    def reframe(self):write(self.path,self.frame)
    def test_retained_binding_order_follows_canonical_claim_not_retrieval(self):
        root=self.root/'source-order';root.mkdir()
        path,frame,_=fixture(root,'dev',dev_evidence=True)
        checks=parse_json(Path(frame['producer']['admission']['checks']['path']).read_bytes())
        bound=[r['doc_id'] for r in checks[0]['candidate']['envelope']['source_bindings']]
        requests=[parse_json(x) for x in Path(frame['producer']['requests']['path']).read_bytes().splitlines()]
        self.assertEqual(bound,sorted(bound))
        self.assertNotEqual(bound,[d['doc_id'] for d in requests[0]['documents']])
        result=o.reconstruct_partition(path,proof(path)['sha256'])
        self.assertEqual(result.coverage['admitted'],1)
        self.assertTrue(result.cases[0]['native_assembly_agreement'])
    def test_binding_order_compatibility_rejects_duplicate_missing_extra_and_wrong_hash(self):
        root=self.root/'source-guards';root.mkdir()
        path,frame,_=fixture(root,'dev',dev_evidence=True)
        admission=frame['producer']['admission'];check_path=Path(admission['checks']['path'])
        original=parse_json(check_path.read_bytes());receipt_path=Path(admission['receipt']['path'])
        receipt=parse_json(receipt_path.read_bytes())
        for change in ('duplicate','missing','extra','hash','boolean','field'):
            changed=copy.deepcopy(original);bindings=changed[0]['candidate']['envelope']['source_bindings']
            if change=='duplicate':bindings.append(dict(bindings[0]))
            if change=='missing':bindings.pop()
            if change=='extra':bindings.append(dict(bindings[0],sentence_id=1))
            if change=='hash':bindings[0]['text_sha256']='0'*64
            if change=='boolean':bindings[0]['sentence_id']=False
            if change=='field':bindings[0]['additional']='not authorized'
            admission['checks']=write(check_path,changed);receipt['files']['CHECKS.json']=admission['checks']
            admission['receipt']=write(receipt_path,receipt);write(path,frame)
            with self.subTest(change=change),self.assertRaises(ValueError):o.reconstruct_partition(path,proof(path)['sha256'])
    def test_full_fictional_partition_native_agreement_and_immutable_rows(self):
        result=self.read();self.assertEqual(result.ids,tuple(self.frame['expected_ids']))
        self.assertEqual(result.coverage['scheduled'],len(result.ids));self.assertTrue(all(r.strict_success==1 for r in result.rows))
        self.assertTrue(all(r.confidence.score==.8 for r in result.rows));self.assertEqual(result.coverage['strict_scorer_agreement'],len(result.ids))
        with self.assertRaises(TypeError):result.cases[0]['strict_success']=0
    def test_current_dependency_policy_and_exact_launch_order_are_reconstructed(self):
        result=self.read()
        self.assertEqual(result.coverage['scheduled'],len(self.frame['expected_ids']))
        events=[parse_json(x) for x in (self.root/'producer/journal.jsonl').read_bytes().splitlines()]
        self.assertEqual([r['event'] for r in events[:5]],['calibration_reserved','inputs_admitted','dependency_discovery_isolated','model_load_started','model_load_completed'])
    def test_resealed_dependency_policy_and_event_drift_are_rejected(self):
        for problem in ('missing_file','file_and_event_policy','event_only_policy','duplicate_event','missing_event','late_event','extra_policy_field'):
            with self.subTest(problem=problem),tempfile.TemporaryDirectory(dir=self.root) as temporary:
                folder=Path(temporary);path,frame,_=fixture(folder);producer=folder/'producer'
                policy_path=producer/'DEPENDENCY-POLICY.json';policy=parse_json(policy_path.read_bytes())
                events=[parse_json(x) for x in (producer/'journal.jsonl').read_bytes().splitlines()]
                entry=next(e for e in events if e['event']=='dependency_discovery_isolated')
                if problem=='missing_file':policy_path.unlink()
                elif problem=='file_and_event_policy':
                    policy['network_and_child_audit']='allowed';write(policy_path,policy);entry['details']['policy']=policy
                elif problem=='event_only_policy':entry['details']['policy']['sys_path_modified']=True
                elif problem=='duplicate_event':events.insert(3,copy.deepcopy(entry))
                elif problem=='missing_event':events.remove(entry)
                elif problem=='late_event':events.remove(entry);events.insert(4,entry)
                else:
                    policy['additional_grant']=True;write(policy_path,policy);entry['details']['policy']=policy
                for index,event in enumerate(events):event['sequence']=index;event['monotonic_seconds']=float(index)
                (producer/'journal.jsonl').write_bytes(b''.join(canonical(e)+b'\n' for e in events))
                frame['producer']['receipt']=reseal_calibration(producer);write(path,frame)
                with self.assertRaises(ValueError):o.reconstruct_partition(path,proof(path)['sha256'])
    def test_detached_current_retrieval_uses_separately_bound_requests(self):
        path=Path(self.frame['producer']['retrieval']['path']);value=parse_json(path.read_bytes())
        value.pop('requests');value['scheduled_pairs']=len(self.frame['expected_ids'])*5
        self.frame['producer']['retrieval']=write(path,value);self.reframe()
        self.assertEqual(self.read().coverage['scheduled'],len(self.frame['expected_ids']))
        value['scheduled_pairs']-=1;self.frame['producer']['retrieval']=write(path,value);self.reframe()
        with self.assertRaises(ValueError):self.read()
    def test_calibration_never_decodes_original_development_annotation_member(self):
        original=o._json_lines;decoded=[]
        def observe(raw):
            result=original(raw)
            if any(isinstance(r,dict) and r.get('id')==100 and 'evidence' in r for r in result):
                raise AssertionError('Development annotations decoded before sealed mapping')
            decoded.append(len(result));return result
        with patch.object(o,'_json_lines',side_effect=observe):self.read()
        self.assertTrue(decoded)
    def test_wrong_role_and_incomplete_production_fail_before_source_reads(self):
        for key,value in (('purpose','predict'),('mode','production')):
            previous=self.frame[key];self.frame[key]=value;self.reframe()
            with patch.object(o,'_preparation',side_effect=AssertionError('reference access')):
                with self.assertRaises(ValueError):self.read()
            self.frame[key]=previous
    def test_external_anchor_mutated_bytes_and_extra_files_fail(self):
        with self.assertRaises(ValueError):o.reconstruct_partition(self.path,'0'*64)
        (self.root/'producer/orphan.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'inventory'):self.read()
    def test_missing_or_reordered_schedule_cannot_drop_cases(self):
        self.frame['expected_ids']=self.frame['expected_ids'][:-1];self.reframe()
        with self.assertRaisesRegex(ValueError,'membership'):self.read()
    def test_scorer_disagreement_is_terminal(self):
        with patch('experiments.scifact.evaluate.strict_correct',return_value=False):
            with self.assertRaisesRegex(ValueError,'disagrees'):self.read()
    def test_current_code_pin_change_is_rejected(self):
        self.frame['code_files'][0]['sha256']='0'*64;self.reframe()
        with self.assertRaisesRegex(ValueError,'bytes changed'):self.read()
    def test_resealed_native_identity_label_rationale_and_source_corruption_fail(self):
        cid=self.frame['expected_ids'][0];pair_path=next((self.root/'producer/pairs').glob(str(cid)+'-*.json'))
        original=pair_path.read_bytes()
        for problem in ('float_identity','label_decode','rationale_span','source_hash'):
            pair=parse_json(original)
            if problem=='float_identity':pair['prediction']['claim_id']=float(cid)
            elif problem=='label_decode':pair['prediction']['predicted_label']='wrong'
            elif problem=='rationale_span':pair['prediction']['rationale_probs'].append(.8)
            else:pair['input_document_sha256']='0'*64
            write(pair_path,pair);self.frame['producer']['receipt']=reseal_calibration(self.root/'producer');self.reframe()
            with self.subTest(problem=problem),self.assertRaises(ValueError):self.read()
        pair_path.write_bytes(original)
    def test_well_formed_wrong_biology_is_admitted_but_scored_zero(self):
        cid=self.frame['expected_ids'][0];pair_path=self.root/f'producer/pairs/{cid}-{cid}.json';pair=parse_json(pair_path.read_bytes())
        label='CONTRADICT' if pair['prediction']['predicted_label']=='SUPPORT' else 'SUPPORT'
        pair['prediction']['predicted_label']=label;pair['prediction']['label_probs']=[.8,.1,.1] if label=='CONTRADICT' else [.1,.1,.8]
        write(pair_path,pair);claim_path=self.root/f'producer/claims/{cid}.json';claim=parse_json(claim_path.read_bytes())
        claim['prediction']['evidence'][str(cid)]['label']=label;write(claim_path,claim)
        self.frame['producer']['receipt']=reseal_calibration(self.root/'producer');self.reframe()
        result=self.read();record=next(row for row in result.rows if row.id==cid)
        self.assertTrue(record.produced);self.assertTrue(record.admitted);self.assertEqual(record.strict_success,0)
        self.assertEqual(record.confidence.status,'available')
    def test_resealed_unexplained_completion_and_accounting_fail(self):
        path=self.root/'producer/journal.jsonl';original=path.read_bytes();events=[parse_json(x) for x in original.splitlines()]
        copied=copy.deepcopy(next(r for r in events if r['event']=='pair_completed'))
        copied['details']['claim_id']=999;events.insert(-1,copied)
        for i,event in enumerate(events):event['sequence']=i;event['monotonic_seconds']=float(i)
        path.write_bytes(b''.join(canonical(r)+b'\n' for r in events))
        # Reseal the chain without replacing the deliberately orphaned event.
        previous='0'*64
        for event in events:
            event.pop('sha256');event['previous_sha256']=previous;previous=o.digest(canonical(event));event['sha256']=previous
        path.write_bytes(b''.join(canonical(r)+b'\n' for r in events))
        status=parse_json((self.root/'producer/STATUS.json').read_bytes())
        status['files']={k:v for k,v in inventory(self.root/'producer').items() if k not in ('STATUS.json','RECEIPT.json')}
        write(self.root/'producer/STATUS.json',status)
        receipt=parse_json((self.root/'producer/RECEIPT.json').read_bytes());receipt['files']={k:v for k,v in inventory(self.root/'producer').items() if k!='RECEIPT.json'}
        self.frame['producer']['receipt']=write(self.root/'producer/RECEIPT.json',receipt);self.reframe()
        with self.assertRaisesRegex(ValueError,'Orphaned'):self.read()
    def test_source_changes_after_first_capture_fail_final_recheck(self):
        original=o._Capture.finish
        def tampered(reader):
            (self.prepared/'views/corpus.jsonl').write_bytes(b'{}\n')
            return original(reader)
        with patch.object(o._Capture,'finish',tampered):
            with self.assertRaisesRegex(ValueError,'bytes changed'):self.read()
    def test_unsafe_receipt_paths_are_rejected_before_external_open(self):
        path=self.root/'producer/RECEIPT.json';receipt=parse_json(path.read_bytes())
        receipt['files']['../outside.json']=next(iter(receipt['files'].values()))
        self.frame['producer']['receipt']=write(path,receipt);self.reframe()
        with self.assertRaisesRegex(ValueError,'Unsafe receipt'):self.read()
    def test_resealed_source_permission_laundering_fails(self):
        path=self.prepared/'manifest.json';manifest=parse_json(path.read_bytes())
        manifest['products']['references_calibration']['purposes'].append('predict')
        transition_path=Path(self.frame['preparation_transition']['path']);transition=parse_json(transition_path.read_bytes())
        transition['manifest']=write(path,manifest);self.frame['preparation_transition']=write(transition_path,transition)
        retrieved=Path(self.frame['producer']['retrieval']['path']);value=parse_json(retrieved.read_bytes())
        value['transition']=self.frame['preparation_transition'];self.frame['producer']['retrieval']=write(retrieved,value);self.reframe()
        with self.assertRaisesRegex(ValueError,'permissions changed'):self.read()
    def test_development_requires_sealed_map_and_matches_retained_admission(self):
        folder=self.root/'development';folder.mkdir();path,frame,prepared=fixture(folder,'dev')
        result=o.reconstruct_partition(path,proof(path)['sha256']);self.assertEqual(result.ids,(100,))
        self.assertEqual(result.rows[0].strict_success,1);self.assertIsNotNone(result.mapping_fingerprint)
        frame['sealed_mapping']['sha256']='0'*64;write(path,frame)
        with patch.object(o,'_preparation',side_effect=AssertionError('dev reference before map')):
            with self.assertRaises(ValueError):o.reconstruct_partition(path,proof(path)['sha256'])
    def test_retained_overlength_is_missing_score_and_zero_success_not_empty_gold_success(self):
        from experiments.scifact_multivers.contracts import ContractError
        original=InventedSolver.predict
        def overlength(solver,claims,corpus,*,pair_deadline_seconds,event):
            if corpus[0]['doc_id']==1:
                cid=claims[0]['id'];did=corpus[0]['doc_id'];reason='Input exceeds 4096 tokens; no truncation is permitted'
                event(event='pair_started',claim_id=cid,abstract_id=did)
                event(event='pair_failed',claim_id=cid,abstract_id=did,error=reason)
                raise ContractError(reason)
            return original(solver,claims,corpus,pair_deadline_seconds=pair_deadline_seconds,event=event)
        folder=self.root/'incomplete-dev';folder.mkdir()
        with patch.object(InventedSolver,'predict',overlength):path,frame,_=fixture(folder,'dev')
        result=o.reconstruct_partition(path,proof(path)['sha256']);record=result.rows[0]
        self.assertFalse(record.produced);self.assertFalse(record.admitted);self.assertEqual(record.strict_success,0)
        self.assertEqual(record.confidence.status,'unavailable');self.assertIsNone(record.confidence.score)
        self.assertEqual(result.coverage['worker_counts']['overlength_pairs'],1)


if __name__=='__main__':unittest.main()
