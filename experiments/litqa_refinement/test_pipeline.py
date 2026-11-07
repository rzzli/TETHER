"""Invented full two-case phase graph; never native inference or public HTTP."""
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal
from tether_engine.serde import canonical,encode,fingerprint,freeze
from experiments.litqa_refinement import pipeline as p,model,projection,schedule,collection
from experiments.litqa_refinement import test_projection as original_fixtures,test_collection as source_fixtures
from experiments.litqa_refinement.test_model import MODEL


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.fixture=original_fixtures.ProjectionTests('runTest');self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.baseline=self.fixture.prepare();self.base=self.fixture.base/'sc05';self.base.mkdir()
        self.calls=[];self.codec_fail=set();self.raise_on=None;self.parents={}

    def fake_model(self,descriptor,output,deadline):
        value=encode(descriptor);self.calls.append(value)
        if self.raise_on==(value['task'],value['query']['id']):raise TimeoutError('fictional uncertain native attempt')
        root=Path(output);journal=RunJournal(root,kind='build')
        inputs=p._cell_inputs(descriptor);publish_bytes(root/'INPUT.json',canonical(inputs))
        if value['task']=='critic':
            request,payload=model.make_critic_request(value['query'],value['prior'],value['sources'],value['model_provenance'])
            decoded=dict(support='insufficient',evidence_ids=[],criticism='More direct evidence is needed.',queries=[['Lumarin'],['color']])
        else:
            request,payload=value['prepared_member']['request'],value['prepared_member']['payload']
            decoded=dict(answer_index=0 if value['sources'] or value['task']=='removal' else 2,
                         evidence_ids=[value['sources'][0]['source_id']] if value['sources'] else [])
        status='codec_failure' if (value['task'],value['query']['id']) in self.codec_fail else 'completed'
        if status=='codec_failure':decoded=None
        usage=dict(input_tokens=10,output_tokens=20,cost_usd=0)
        terminal=dict(execution_id=value['execution_id'],generation_entered=True,status=status,measured_usage=usage)
        name='result.json' if status=='completed' else 'failure.json'
        publish_bytes(root/'native'/name,canonical(terminal))
        publish_bytes(root/'native/native-response.bin',canonical(dict(fictional_only=True,decoded=decoded)))
        summary=dict(status=status,decoded=decoded,generation_entered=True,usage=usage,reservation_input_tokens=50,
            reservation_output_tokens=256,native_result=p.proof(root/'native'/name),task=value['task'],
            execution_id=value['execution_id'],input_sha256=fingerprint(inputs),request_sha256=fingerprint(request),
            provider_cost_usd=0,automatic_retry=False,scientific_correctness='unevaluated')
        publish_bytes(root/'SUMMARY.json',canonical(summary));journal.append('fictional_model_terminal',status=status);journal.close()
        return freeze(dict(summary=summary,summary_proof=p.proof(root/'SUMMARY.json'),root=str(root)))

    def execute(self,phase,**kwargs):
        path=self.base/phase
        parents={key:self.parents[key] for key in schedule.PARENTS[phase]}
        with patch.object(collection.acquisition.legacy,'fetch_http',side_effect=source_fixtures.fetcher(('PMC8',))):
            result=p.execute(phase,self.baseline,path,purpose='fictional_qualification',seconds=120,parents=parents,
                cutoff='2099-01-01T00:00:00+00:00' if phase=='pair_prepare' else None,
                model_provenance=MODEL,call_model=self.fake_model,**kwargs)
        receipt=p.proof(path/'STAGE-RECEIPT.json')
        self.parents[phase]=dict(root=str(path),receipt_sha256=receipt['sha256'])
        checked=schedule.verify(path,receipt['sha256'],expected_ids=self.baseline.manifest['schedule'],expected_phase=phase,purpose='fictional_qualification')
        self.assertEqual(result,checked['report'])
        return result

    def prepare_pair(self):
        self.execute('critic');self.execute('refinement_collect');return self.execute('pair_prepare')

    def test_all_stages_reuse_one_critic_and_collection_and_freeze_both_final_members(self):
        pair=self.prepare_pair();self.assertEqual(len(self.calls),2)
        self.assertEqual(pair['accounting']['known_totals']['generation_calls'],0)
        for row in pair['rows']:
            product=row['product'];factual=p.read(product['repair']);removal=p.read(product['removal'])
            self.assertEqual(factual['request']['candidate_context'],removal['request']['candidate_context'])
            self.assertEqual(factual['request']['critique_context'],removal['request']['critique_context'])
            self.assertTrue(factual['request']['sources']);self.assertEqual(removal['request']['sources'],())
        repair=self.execute('repair');removal=self.execute('removal')
        self.assertEqual([c['task'] for c in self.calls],['critic','critic','repair','repair','removal','removal'])
        self.assertTrue(all(r['product']['disposition']['check_status']=='accepted' for r in repair['rows']))
        self.assertTrue(all(r['product']['disposition']['check_status']=='rejected' for r in removal['rows']))
        self.assertTrue(all(p.read(r['product']['decision'])['raw_removal_mechanical_rejection'] for r in removal['rows']))
        for call in self.calls[-2:]:
            self.assertEqual(call['sources'],[]);self.assertNotIn('prepared_pair',call)
            self.assertNotIn('Fictional Lumarin is cobalt.',canonical(call).decode())
        self.assertEqual(removal['accounting']['known_totals']['source_http_requests'],0)

    def test_unavailable_critic_preserves_case_and_runs_original_source_repair(self):
        ident=self.baseline.queries[0]['id'];self.codec_fail.add(('critic',ident))
        critic=self.execute('critic');collection_result=self.execute('refinement_collect')
        self.assertEqual(critic['rows'][0]['status'],'codec_failure')
        first=collection_result['rows'][0];self.assertEqual(first['status'],'unavailable');self.assertIsNone(first['product']['collection'])
        self.assertEqual(first['accounting']['source_http_requests'],0)
        self.execute('pair_prepare');repair=self.execute('repair')
        self.assertEqual(repair['scheduled'],2);self.assertEqual(repair['rows'][0]['product']['disposition']['prediction']['answer_index'],2)
        self.assertEqual(critic['rows'][0]['product']['semantic_selection']['reason'],'original_not_admitted')

    def test_incomplete_or_changed_pair_parent_stops_before_any_final_dispatch(self):
        pair=self.prepare_pair();before=len(self.calls)
        path=Path(pair['rows'][1]['product']['removal']['path']);path.write_bytes(b'{}')
        with self.assertRaises(ValueError):self.execute('repair')
        self.assertEqual(len(self.calls),before)
        report=p.parse_json((self.base/'repair/REPORT.json').read_bytes())
        self.assertEqual(report['unexecuted'],2);self.assertEqual(report['status'],'incomplete')

    def test_uncertain_call_stops_remaining_schedule_and_cannot_retry_directory(self):
        self.raise_on=('critic',self.baseline.queries[0]['id'])
        with self.assertRaises(TimeoutError):self.execute('critic')
        report=p.parse_json((self.base/'critic/REPORT.json').read_bytes())
        self.assertEqual([r['status'] for r in report['rows']],['failed','unexecuted'])
        self.assertIsNone(report['rows'][0]['accounting']);self.assertEqual(len(self.calls),1)
        with self.assertRaises(FileExistsError):self.execute('critic')
        self.assertEqual(len(self.calls),1)

    def test_final_phase_cannot_accept_factual_answers_as_parent(self):
        self.prepare_pair();self.execute('repair');before=len(self.calls)
        bad={'pair_prepare':self.parents['pair_prepare'],'repair':self.parents['repair']}
        with self.assertRaisesRegex(ValueError,'Exact required parent'):
            p.execute('removal',self.baseline,self.base/'bad-removal',purpose='fictional_qualification',seconds=120,
                parents=bad,model_provenance=MODEL,call_model=self.fake_model)
        self.assertEqual(len(self.calls),before)

    def test_collection_failure_does_not_become_empty_source_or_drop_case(self):
        self.execute('critic')
        def uncertain(plan,root,*,deadline):raise TimeoutError('fictional acquisition failure')
        with self.assertRaises(TimeoutError):self.execute('refinement_collect',acquire_sources=uncertain)
        report=p.parse_json((self.base/'refinement_collect/REPORT.json').read_bytes())
        self.assertEqual(report['scheduled'],2);self.assertEqual(report['rows'][0]['status'],'failed')
        self.assertEqual(report['unexecuted'],1)


if __name__=='__main__':unittest.main()
