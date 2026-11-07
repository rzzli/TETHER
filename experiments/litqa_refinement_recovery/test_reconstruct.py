"""Invented continuation accounting and independently bound envelope controls."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from tether_engine.serde import encode
from unittest.mock import patch

from experiments.litqa_refinement_recovery import reconstruct as r


def invented_accounting():
    ids=['00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002']
    original={p:dict.fromkeys(r.old.FIELDS,0) for p in r.old.PHASES};new=deepcopy(original)
    original['critic'].update(generation_calls=2,measured_input_tokens=20,measured_output_tokens=10,reserved_input_tokens=40,reserved_output_tokens=512)
    original['refinement_collect'].update(source_http_requests=4,measured_response_bytes=356,safety_accounted_bytes=356)
    for phase,count in (('repair',1),('removal',2)):
        new[phase].update(generation_calls=count,measured_input_tokens=10*count,measured_output_tokens=5*count,reserved_input_tokens=20*count,reserved_output_tokens=256*count)
    raw=dict(input_tokens=10,output_tokens=256,cost_usd=0);bound=dict(input_tokens=20,output_tokens=256,cost_usd=0)
    descriptor=dict(kind='sc05_authenticated_native_limit_failure_v1',status='authenticated_limit_failure',execution_id='fictional-original-repair-0000',task='repair',
        producer_status='error',check_status='not_run',prediction=None,original_usage_verified=False,qualified_usage=None,raw_usage_checked=True,
        raw_reported_usage=raw,conservative_reservation=bound)
    attempts=[dict(phase='repair',ordinal=0,origin='original',execution_id=descriptor['execution_id'],descriptor=descriptor,raw_reported_usage=raw,conservative_reservation=bound)]
    envelope=dict(frame=dict(schedule=ids),resources=dict(baseline_resources=[dict(id=key,
        logical_model_usage=dict(generation_calls=1,measured_input_tokens=10,measured_output_tokens=5,reserved_input_tokens=20,reserved_output_tokens=256,provider_cost_usd=0),
        logical_http_usage=dict(requests=2,measured_response_bytes=20,safety_accounted_bytes=20,unknown_transfer_upper_bytes=0)) for key in ids]))
    return original,new,attempts,envelope


def author_retained_recovery(output):
    """Retain a genuine invented recovery and capability for evaluator controls.

    All original/source/native process captures are fictional, as declared by
    the underlying fixture. The real independent gates run. No actual benchmark
    keys, model generations or HTTP calls are made. The returned fixture owns
    only test-context patches; its cleanup keeps these retained files intact.
    """
    from experiments.litqa_refinement import test_envelopes as ef
    from . import test_original as pf
    from .test_run_integration import author_complete_recovery
    root=Path(output).resolve()
    r.need(root.is_relative_to(r.old.REPO/'data/cache') and root!=r.old.REPO/'data/cache' and not root.exists() and root.parent.is_dir(),
           'Fresh ignored retained-fixture root required')
    root.mkdir();folders=[]
    class RetainedTemporaryDirectory:
        def __init__(self,*args,**kwargs):
            target=root/f'scratch-{len(folders):04d}';target.mkdir();folders.append(target);self.name=str(target)
        def cleanup(self):pass
        def __enter__(self):return self.name
        def __exit__(self,*args):pass
    fixture_type=type('RetainedIndependentRecoveryFixture',(pf.FailedFixture,ef.EnvelopeTests),{'repair_stage_seconds':500})
    fixture=fixture_type('runTest')
    with patch.object(tempfile,'TemporaryDirectory',RetainedTemporaryDirectory):fixture.setUp()
    descriptor=author_complete_recovery(fixture,fixture.base/'retained-complete-recovery')
    value=r.reconstruct(descriptor,baseline_acceptance=fixture.acceptance)
    scope=dict(kind='sc05_retained_fictional_recovery_v1',purpose='fictional_qualification',original_sources='invented',original_native_responses='invented',
        native_process_and_supervision='invented',independent_gates_mocked=False,model_calls=0,http_calls=0,reference_keys_read=False,
        producer=descriptor,baseline_acceptance=fixture.acceptance,original_inspection=fixture.inspection,original_source_archive=fixture.archive,
        fictional_model_receipt=fixture.frame['model_receipt'],
        replay_context='For separate-process invented replay, bind old.envelopes.MODEL_RECEIPT to this exact fictional_model_receipt.sha256; never apply this test context to production.')
    ef.write(root/'FIXTURE-SCOPE.json',scope)
    return dict(fixture=fixture,value=value,producer=descriptor,baseline_acceptance=fixture.acceptance,scope=ef.proof(root/'FIXTURE-SCOPE.json'))


class ResourceTests(unittest.TestCase):
    def test_failed_usage_is_separate_from_verified_and_logical_totals(self):
        resources,logical=r.resource_tables(*invented_accounting())
        self.assertEqual(resources['verified']['physical_totals']['generation_calls'],5)
        self.assertEqual(resources['observed_dispatch_totals']['generation_calls'],6)
        self.assertEqual(resources['verified']['physical_totals']['measured_output_tokens'],25)
        self.assertEqual(resources['unverified_native']['reported_totals']['output_tokens'],256)
        self.assertEqual(logical['conditions']['repair']['model_usage']['generation_calls'],5)
        self.assertEqual(len(logical['unverified_native_condition_attribution']['repair']),1)
        self.assertEqual(logical['unverified_native_condition_attribution']['removal'],[])

    def test_rejected_call_cannot_be_qualified_or_repeated(self):
        for change in ('qualified','duplicated','relabelled'):
            args=list(invented_accounting())
            if change=='qualified':args[2][0]['descriptor']['qualified_usage']=dict(input_tokens=10,output_tokens=256,cost_usd=0)
            elif change=='duplicated':args[2].append(deepcopy(args[2][0]))
            else:args[2][0]['origin']='continuation'
            with self.subTest(change=change),self.assertRaises(ValueError):r.resource_tables(*args)

    def test_new_source_or_critic_work_is_rejected(self):
        for phase,field in (('critic','generation_calls'),('refinement_collect','source_http_requests'),('repair','source_http_requests')):
            args=list(invented_accounting());args[1][phase][field]=1
            with self.subTest(phase=phase),self.assertRaises(ValueError):r.resource_tables(*args)

    def test_wrong_bound_and_changed_integer_types_rejected(self):
        for kind in ('negative','bool','output','input'):
            args=list(invented_accounting())
            if kind=='negative':args[0]['critic']['measured_input_tokens']=-1
            elif kind=='bool':args[0]['critic']['generation_calls']=True
            elif kind=='output':args[2][0]['raw_reported_usage']['output_tokens']=255
            else:args[2][0]['conservative_reservation']['input_tokens']=9
            with self.subTest(kind=kind),self.assertRaises(ValueError):r.resource_tables(*args)

    def test_float_zero_cost_retained_but_boolean_or_nonfinite_cost_rejected(self):
        args=list(invented_accounting())
        args[2][0]['raw_reported_usage']['cost_usd']=0.0
        args[2][0]['conservative_reservation']['cost_usd']=0.0
        resources,_=r.resource_tables(*args)
        self.assertEqual(resources['unverified_native']['reported_totals']['cost_usd'],0.0)
        for field in ('raw_reported_usage','conservative_reservation'):
            for value in (False,True,1,float('nan'),float('inf')):
                args=list(invented_accounting());args[2][0][field]['cost_usd']=value
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):r.resource_tables(*args)

    def test_unissued_capability_is_rejected_before_any_revalidation(self):
        forged=r.VerifiedRecovery('unused','a'*64,{}, {},r.fingerprint(dict(root='unused',receipt_sha256='a'*64,report={},envelope={})),r._TOKEN)
        with self.assertRaisesRegex(ValueError,'Issued'):r.revalidate(forged)


class StageClosureTests(unittest.TestCase):
    def test_resealed_orphan_native_product_is_rejected(self):
        from . import run as producer
        temp=tempfile.TemporaryDirectory(dir=r.old.REPO/'data/cache');self.addCleanup(temp.cleanup)
        root=Path(temp.name).resolve()/'stage';ids=invented_accounting()[3]['frame']['schedule']
        stage=producer.RecoveryStage(ids,'repair',(1,),root,purpose='fictional_qualification',seconds=120,original_slots=['old-0','old-1'])
        producer.write(root/'INPUTS.json',dict(baseline={},parent_pair={},original_cutoff='2026-01-01T00:00:00Z',reference_keys_available=False,scoring_performed=False))
        producer.write(root/'products/0001/fixture.json',dict(scope='invented stage structural control; no native success claimed'))
        stage.call(lambda *_:dict(status='capacity',reason='capacity',product={},accounting=producer.schedule.zero_accounting()));stage.finish()
        producer.write(root/'products/0999/extra-call.json',dict(scope='unlisted invented attempt'))
        receipt=r.old.decode((root/'STAGE-RECEIPT.json').read_bytes());receipt['files']=producer.inventory(root,omit=('STAGE-RECEIPT.json',))
        (root/'STAGE-RECEIPT.json').write_bytes(r.old.canonical(encode(receipt)))
        proof=encode(producer.proof(root/'STAGE-RECEIPT.json'))
        with self.assertRaises(ValueError):
            r._stage(root,proof,'repair',dict(purpose='fictional_qualification'),dict(dispatch_ordinals=[1],original_slots=['old-0','old-1'],stage_seconds=120,baseline={},parent_pair={}),
                dict(schedule=ids,pair_prepare=dict(cutoff='2026-01-01T00:00:00Z')),r.accepted_primary._Inputs(),10,11)


class PreflightBoundaryTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(dir=r.old.REPO/'data/cache');self.addCleanup(temp.cleanup)
        self.base=Path(temp.name).resolve();self.root=self.base/'output';self.root.mkdir()
        raw=r.old.canonical(dict(scope='invented preflight metadata; no semantic admission claimed'))
        self.external=self.base/'external-frame.json';self.external.write_bytes(raw)
        (self.root/'FRAME.json').write_bytes(raw)
        self.fp=self.proof(self.root/'FRAME.json')
        self.frame=dict(plan=dict(path='invented-plan'),authority=dict(path='invented-authority'))
        self.plan=dict(parent_identity='invented-parent',original_frame=dict(path='invented-original'),
            budgets=dict(phase_remaining_seconds=dict(repair=580),outer_remaining_seconds=1200))
        self.request=dict(kind='sc05_recovery_preflight_request_v2',frame=self.proof(self.external),output=str(self.root),
            preflight_bounds=dict(repair_seconds=580,outer_seconds=1200),metadata_only_before_admission=True,automatic_retry=False)

    def proof(self,path):
        raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=r.old.digest(raw))

    def call(self):
        path=self.root/'REQUEST.json';path.write_bytes(r.old.canonical(self.request))
        return r._preflight(self.root,self.fp,self.frame,self.plan,r.accepted_primary._Inputs(),self.proof(path))

    def test_exact_external_frame_and_inherited_bounds_define_two_events(self):
        events=self.call()
        self.assertEqual([name for name,_ in events],['recovery_preflight_started','recovery_preflight_admitted'])
        self.assertEqual(events[0][1]['frame'],self.proof(self.external))
        self.assertEqual(events[0][1]['limits'],self.request['preflight_bounds'])
        self.assertEqual(events[1][1]['original_frame'],self.plan['original_frame'])

    def test_changed_external_bytes_and_output_local_frame_rejected(self):
        raw=self.external.read_bytes();self.external.write_bytes(raw+b' ')
        with self.assertRaises(ValueError):self.call()
        self.external.write_bytes(raw);self.request['frame']=self.fp
        with self.assertRaisesRegex(ValueError,'overlaps'):self.call()

    def test_clock_resets_unknown_fields_and_false_metadata_scope_rejected(self):
        original=deepcopy(self.request)
        for change in ('repair','outer','extra','scope','retry'):
            self.request=deepcopy(original)
            if change=='repair':self.request['preflight_bounds']['repair_seconds']=7200
            elif change=='outer':self.request['preflight_bounds']['outer_seconds']=43200
            elif change=='extra':self.request['extra']='unbound'
            elif change=='scope':self.request['metadata_only_before_admission']=False
            else:self.request['automatic_retry']=True
            with self.subTest(change=change),self.assertRaises(ValueError):self.call()

    def test_admission_reserves_setup_cleanup_and_one_bounded_cell(self):
        self.assertEqual(r._admission_limit('production',7200),3600)
        self.assertEqual(r._admission_limit('production',500),110)
        self.assertEqual(r._admission_limit('fictional_qualification',1200),600)
        self.assertEqual(r._admission_limit('fictional_qualification',600),210)
        for purpose,seconds in (('other',7200),('production',390),('production',True),('production',float('inf')),('production',float('nan'))):
            with self.subTest(purpose=purpose,seconds=seconds),self.assertRaises(ValueError):r._admission_limit(purpose,seconds)


class ReconstructionIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from experiments.litqa_refinement import test_envelopes as envelope_fixtures
        from . import test_original as parent_fixtures
        from .test_run_integration import author_complete_recovery
        fixture_type=type('IndependentRecoveryFixture',(parent_fixtures.FailedFixture,envelope_fixtures.EnvelopeTests),{'repair_stage_seconds':500})
        cls.f=fixture_type('runTest');cls.addClassCleanup(cls.f.doCleanups)
        with patch.object(tempfile,'tempdir',str(r.old.REPO/'data/cache')):cls.f.setUp()
        cls.descriptor=author_complete_recovery(cls.f,cls.f.base/'independent-complete-recovery')
        cls.value=r.reconstruct(cls.descriptor,baseline_acceptance=cls.f.acceptance)

    def test_complete_source_native_recovery_is_distinct_and_immutable(self):
        value=self.value;report=value.report
        self.assertEqual(report['status'],'independently_reconstructed_recovery')
        self.assertEqual([q['id'] for q in report['queries']],list(self.f.frame['schedule']))
        self.assertTrue(report['source_lineage_checked'] and report['native_calls_checked'] and report['cross_stage_products_checked'])
        self.assertEqual(report['records']['repair'][0]['producer_status'],'error');self.assertIsNone(report['records']['repair'][0]['prediction'])
        self.assertEqual(report['incremental_resources']['observed_dispatch_totals']['generation_calls'],6)
        self.assertEqual(report['incremental_resources']['verified']['physical_totals']['generation_calls'],5)
        self.assertEqual(report['incremental_resources']['unverified_native']['original_count'],1)
        self.assertEqual(report['incremental_resources']['continuation']['verified_by_phase']['refinement_collect']['source_http_requests'],0)
        self.assertTrue(value.envelope['original_preserved_as_failed'])
        self.assertFalse((self.f.root/'ROOT-RECEIPT.json').exists())
        with self.assertRaises(TypeError):report['records']['repair'][0]['prediction']={}
        self.assertIs(r.revalidate(value),value)

    def test_stale_new_native_bytes_rejected_by_immutable_closure(self):
        target=Path(self.value.root)/'removal/worker/phase/products/0000/native/native-response.bin';raw=target.read_bytes()
        try:
            target.write_bytes(raw+b' ')
            with self.assertRaises(ValueError):r.revalidate(self.value)
        finally:target.write_bytes(raw)

    def test_replaced_closure_and_copied_capability_cannot_skip_revalidation(self):
        value=self.value;closure=value._closure
        with self.assertRaises(TypeError):closure['proofs']=()
        try:
            object.__setattr__(value,'_closure',{'proofs':[],'inventories':[]})
            with self.assertRaisesRegex(ValueError,'closure'):r.revalidate(value)
        finally:object.__setattr__(value,'_closure',closure)
        forged=r.VerifiedRecovery(value.root,value.receipt_sha256,value.report,value.envelope,value._fingerprint,value._token,value._parent,value._closure)
        with self.assertRaisesRegex(ValueError,'Issued'):r.revalidate(forged)

    def test_wrong_external_root_or_baseline_acceptance_stops_before_parent(self):
        bad=dict(self.descriptor,receipt_sha256='0'*64)
        with patch.object(r.original,'reconstruct',side_effect=AssertionError('Must reject before original admission')):
            with self.assertRaises(ValueError):r.reconstruct(bad,baseline_acceptance=self.f.acceptance)
            with self.assertRaises(ValueError):r.reconstruct(self.descriptor,baseline_acceptance={})


if __name__=='__main__':unittest.main()
