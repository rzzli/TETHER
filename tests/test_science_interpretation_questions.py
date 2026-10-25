"""Synthetic question/codec/state checks, not scientific quality or generation."""
from dataclasses import replace
from pathlib import Path
import copy
import shutil
import tempfile
import unittest
from unittest.mock import patch

from asof.contracts import Case
from asof.serde import ContractError, canonical, decode, encode, fingerprint, read_json, write_json
from tools.science import interpretation_questions as q
from tools.science.bounded_interpretation import validate_response as validate_v1

ROOT = Path(__file__).resolve().parents[1]
MECHANISM = 'mechanism-report.v1'
GENETICS = 'genetic-study-report.v1'


class QuestionInterpretationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.inputs = Path(self.temp.name)/'inputs'
        shutil.copytree(ROOT/'src/asof/demo/v2', self.inputs)
        case = replace(decode(Case, read_json(self.inputs/'case.json')), task='T6', endpoint=None)
        write_json(self.inputs/'case.json', encode(case))
        self.prepared = self.prepare()

    def prepare(self, family=MECHANISM, **kwargs):
        return q.prepare_question(self.inputs/'case.json', self.inputs/'snapshot.json', family, **kwargs)

    def source(self):
        return encode(self.prepared.request['source_request'])

    def response(self, request=None, kind='scientific_inference'):
        request = request or self.prepared.request
        row = request['source_request']['evidence'][0]
        quote = dict(observation_id=row['observation_id'], pointer='/statement',
            span=dict(start=0, end=len(row['statement'].encode('utf-8'))), text=row['statement'])
        prop = dict(subject='Synthetic source', predicate='reports', object='fixture association',
            negation=False, modal='possible', population=None, tissue=None, intervention=None,
            comparator=None, outcome=None, timing=None, orientation=None)
        claim = dict(claim_id='Q1', kind=kind, text=row['statement'] if kind == 'source_report' else
            'Synthetic context is limited to the offered fixture.', proposition=prop,
            premise_ids=[row['observation_id']], quotes=[quote],
            limitations=['Invented contract fixture, not biological evidence.'], applicability='uncertain')
        return dict(schema_version=2, kind='question_interpretation', request_sha256=fingerprint(request),
            hypothesis_key=request['hypothesis_key'], question_key=request['question_key'],
            answer_status='answered', claims=[claim], abstention_reason=None,
            features={}, clinical_probability=None)

    def test_closed_templates_are_immutable(self):
        self.assertEqual(set(q.QUESTIONS), {MECHANISM, GENETICS})
        with self.assertRaises(TypeError): q.question_template(MECHANISM)['text'] = 'answer'

    def test_unknown_template_fails_before_admission(self):
        with patch.object(q, 'prepare_sources') as load:
            with self.assertRaises(ContractError): self.prepare('case-specific-answer')
        load.assert_not_called()

    def test_same_source_different_question_cannot_reuse_response(self):
        other = self.prepare(GENETICS).request
        self.assertEqual(fingerprint(other['source_request']), fingerprint(self.prepared.request['source_request']))
        self.assertNotEqual(fingerprint(other), fingerprint(self.prepared.request))
        with self.assertRaises(ContractError): q.validate_response(other, self.response())

    def test_template_and_question_key_tampering_rejected(self):
        for field in ['text', 'family', 'schema_version']:
            request = encode(self.prepared.request); request['question'][field] = 'changed'
            request['question_key'] = fingerprint(request['question'])
            with self.assertRaises(ContractError): q.validate_request(request)

    def test_action_modality_and_tissue_bind_response(self):
        original = read_json(self.inputs/'case.json')
        for field, value in [('intended_action','activate'), ('modality','antibody'), ('tissue','another tissue')]:
            case = copy.deepcopy(original); case['hypothesis'][field] = value
            write_json(self.inputs/'case.json', case)
            with self.assertRaises(ContractError): q.validate_response(self.prepare().request, self.response())

    def test_request_and_archive_are_deeply_immutable(self):
        with self.assertRaises(TypeError): self.prepared.request['source_request']['coverage']['absence_claim'] = True
        with self.assertRaises(TypeError): self.prepared.archive['source_archive']['inputs'][0]['sha256'] = 'changed'
        self.assertTrue(all(not r['scientific_record']['features'] for r in self.prepared.request['source_request']['evidence']))

    def test_binding_copies_caller_owned_sources(self):
        source = self.source(); request = q.bind_question(source, MECHANISM); before = fingerprint(request)
        source['coverage']['missing_input_count'] = 99
        source['evidence'][0]['scientific_record']['features']['invented'] = 1
        self.assertEqual(fingerprint(request), before)

    def test_scope_hash_order_and_snapshot_are_bound(self):
        for update in [lambda r: r['source_scope'].update(snapshot_id='foreign'),
                       lambda r: r['source_scope']['observations'][0].update(scientific_record_sha256='0'*64),
                       lambda r: r['source_scope']['observations'].reverse()]:
            request = encode(self.prepared.request); update(request)
            with self.assertRaises(ContractError): q.validate_request(request)

    def test_incomplete_scope_rejected_as_contract_error(self):
        for source in [{}, {'evidence':[]}, dict(self.source(), evidence=[{}])]:
            with self.assertRaises(ContractError): q.bind_question(source, MECHANISM)

    def test_duplicate_sources_rejected(self):
        source = self.source(); source['evidence'].append(copy.deepcopy(source['evidence'][0]))
        source['coverage']['observations_visible'] += 1
        with self.assertRaises(ContractError): q.bind_question(source, MECHANISM)

    def test_evaluator_only_source_fails_existing_admission(self):
        snapshot = read_json(self.inputs/'snapshot.json'); snapshot['sources'][0]['role'] = 'evaluation_only'
        write_json(self.inputs/'snapshot.json', snapshot)
        with self.assertRaises(ContractError): self.prepare()

    def test_future_program_fails_existing_admission(self):
        case = read_json(self.inputs/'case.json'); case['program']['availability']['annotation_public_at'] = '2024-01-01'
        write_json(self.inputs/'case.json', case)
        with self.assertRaises(ContractError): self.prepare()

    def test_t1_is_outside_question_interpretation(self):
        case = read_json(self.inputs/'case.json'); case['task'] = 'T1'
        write_json(self.inputs/'case.json', case)
        with self.assertRaises(ContractError): self.prepare()

    def test_selected_subset_preserves_missingness(self):
        source = self.source(); source['coverage']['missing_input_count'] = 65
        source['coverage']['missing_count_basis'] = 'snapshot_declaration'
        request = q.bind_question(source, GENETICS)
        rebuilt = q.expand_view(q.scientific_view(request))
        self.assertEqual(rebuilt['source_request']['coverage']['missing_input_count'], 65)
        self.assertIs(rebuilt['source_request']['coverage']['absence_claim'], False)

    def test_unknown_coverage_is_not_zero(self):
        source = self.source(); source['coverage'].update(missing_input_count=None, missing_count_basis='not_measured')
        rebuilt = q.expand_view(q.scientific_view(q.bind_question(source, MECHANISM)))
        self.assertIsNone(rebuilt['source_request']['coverage']['missing_input_count'])

    def test_scientific_first_view_round_trips_all_nested_values(self):
        source = self.source(); source['evidence'][0]['scientific_record']['source_metrics'] = {
            'score':0.2, 'unknown':[None,True,0,0.0,{'extra':'Δ – naïve'}],
            'textMiningSentences':[{'text':'α source <| text', 'unknown':{'all':[1,False,None]}},
                                   {'text':'second', 'unselected':True}]}
        request = q.bind_question(source, MECHANISM); view = q.scientific_view(request)
        self.assertEqual(fingerprint(q.expand_view(view)), fingerprint(request))
        self.assertEqual(len(view['records'][0]['reported_passages']), 2)
        self.assertNotIn('textMiningSentences', view['records'][0]['provider_metadata'])

    def test_opaque_null_absent_empty_metrics_are_distinct(self):
        requests = []
        for absent, value in [(True,None),(False,None),(False,{}),(False,[]),(False,'opaque')]:
            source = self.source(); science = source['evidence'][0]['scientific_record']
            if absent: science.pop('source_metrics',None)
            else: science['source_metrics'] = value
            request = q.bind_question(source, MECHANISM)
            self.assertEqual(fingerprint(q.expand_view(q.scientific_view(request))), fingerprint(request))
            requests.append(fingerprint(request))
        self.assertEqual(len(set(requests)), len(requests))

    def test_passages_null_absent_empty_nonlist_are_distinct(self):
        values = []
        for metrics in [{}, {'textMiningSentences':None}, {'textMiningSentences':[]},
                        {'textMiningSentences':'opaque'}, {'textMiningSentences':{'not':'an array'}}]:
            source = self.source(); source['evidence'][0]['scientific_record']['source_metrics'] = metrics
            request = q.bind_question(source, GENETICS); values.append(fingerprint(request))
            self.assertEqual(fingerprint(q.expand_view(q.scientific_view(request))), fingerprint(request))
        self.assertEqual(len(set(values)), len(values))

    def test_codec_retains_scalar_types(self):
        values = []
        for value in [False,0,0.0]:
            source = self.source(); source['evidence'][0]['scientific_record']['source_metrics'] = {'typed':value}
            request = q.bind_question(source, MECHANISM); values.append(fingerprint(request))
            self.assertEqual(fingerprint(q.expand_view(q.scientific_view(request))), fingerprint(request))
        self.assertEqual(len(set(values)),3)

    def test_view_is_immutable_and_input_unmodified(self):
        before = fingerprint(self.prepared.request); view = q.scientific_view(self.prepared.request)
        with self.assertRaises(TypeError): view['records'][0]['annotation']['statement'] = 'replacement'
        self.assertEqual(fingerprint(self.prepared.request), before)

    def test_view_flags_and_field_collisions_rejected(self):
        for update in [lambda v:v['records'][0].update(passages_present=0),
                       lambda v:v['records'][0]['annotation'].update(scientific_record={}),
                       lambda v:v['records'][0]['scientific_context'].update(source_metrics={}),
                       lambda v:v['source_request_context'].update(evidence=[])]:
            view = encode(q.scientific_view(self.prepared.request)); update(view)
            with self.assertRaises(ContractError): q.expand_view(view)

    def test_view_changed_values_and_order_rejected(self):
        for update in [lambda v:v['records'][0]['annotation'].update(statement='fabricated'),
                       lambda v:v['records'].reverse()]:
            view = encode(q.scientific_view(self.prepared.request)); update(view)
            with self.assertRaises(ContractError): q.expand_view(view)

    def test_view_size_excess_fails_without_truncation(self):
        request = self.prepared.request; size = len(canonical(request))
        self.assertGreater(len(canonical(q.scientific_view(request))),size)
        with patch.object(q,'MAX_BYTES',size+1):
            with self.assertRaises(ContractError): q.scientific_view(request)

    def test_answered_partial_abstained_states(self):
        response = self.response(); q.validate_response(self.prepared.request,response)
        response.update(answer_status='partial',abstention_reason='Additional context is not provided.')
        q.validate_response(self.prepared.request,response)
        response.update(answer_status='abstained',claims=[])
        q.validate_response(self.prepared.request,response)

    def test_abstention_cannot_carry_positive_structured_claim(self):
        for state in ['abstained','partial','answered']:
            response = self.response(); response.update(answer_status=state)
            if state != 'answered':response['abstention_reason']='Unknown.'
            response['claims'][0]['kind']='abstention'
            with self.assertRaises(ContractError):q.validate_response(self.prepared.request,response)

    def test_state_prechecks_happen_before_legacy_validation(self):
        for state, claims, reason in [('answered',[],None),('answered',[{}],'reason'),
                                       ('partial',[{}],None),('abstained',[{}],'reason'),('abstained',[],None)]:
            response=self.response();response.update(answer_status=state,claims=claims,abstention_reason=reason)
            with patch.object(q,'validate_legacy_claims') as legacy:
                with self.assertRaises(ContractError):q.validate_response(self.prepared.request,response)
            legacy.assert_not_called()

    def test_valid_source_report_does_not_receive_scientific_success_flag(self):
        accepted=q.validate_response(self.prepared.request,self.response(kind='source_report'))
        self.assertNotIn('scientific_validation',accepted)
        self.assertIsNone(accepted['clinical_probability'])

    def test_valid_caution_can_supply_partial_answer(self):
        response=self.response(kind='caution');response.update(answer_status='partial',abstention_reason='Fixture scope unresolved.')
        accepted=q.validate_response(self.prepared.request,response)
        self.assertEqual(accepted['claims'][0]['kind'],'caution')

    def test_response_is_copied_and_deeply_immutable(self):
        response=self.response();accepted=q.validate_response(self.prepared.request,response);before=fingerprint(accepted)
        response['claims'][0]['proposition']['predicate']='changed'
        self.assertEqual(fingerprint(accepted),before)
        with self.assertRaises(TypeError):accepted['claims'][0]['proposition']['predicate']='changed'

    def test_foreign_premise_fabricated_quote_and_duplicate_claim_rejected(self):
        for update in [lambda r:r['claims'][0].update(premise_ids=['foreign']),
                       lambda r:r['claims'][0]['quotes'][0].update(text='fabricated'),
                       lambda r:r['claims'].append(copy.deepcopy(r['claims'][0]))]:
            response=self.response();update(response)
            with self.assertRaises(ContractError):q.validate_response(self.prepared.request,response)

    def test_exact_utf8_original_quote_and_split_rejection(self):
        source=self.source();source['evidence'][0]['statement']='naïve Δ – source'
        source['evidence'][0]['scientific_record']['statement']=source['evidence'][0]['statement']
        request=q.bind_question(source,MECHANISM);response=self.response(request)
        q.validate_response(request,response)
        response['claims'][0]['quotes'][0].update(span=dict(start=2,end=3),text='x')
        with self.assertRaises(ContractError):q.validate_response(request,response)

    def test_empty_sources_require_real_abstention(self):
        request=self.prepare(observation_ids=[]).request;response=self.response()
        response.update(request_sha256=fingerprint(request),hypothesis_key=request['hypothesis_key'])
        with self.assertRaises(ContractError):q.validate_response(request,response)
        response.update(answer_status='abstained',claims=[],abstention_reason='No source is selected.')
        q.validate_response(request,response)

    def test_v1_and_v2_responses_are_not_relabelled(self):
        response=self.response()
        with self.assertRaises(ContractError):validate_v1(self.prepared.request['source_request'],response)
        response.update(schema_version=1,kind='generated_interpretation')
        with self.assertRaises(ContractError):q.validate_response(self.prepared.request,response)

    def test_predictive_features_and_probability_are_rejected(self):
        for field,value in [('features',{'effect':1}),('clinical_probability',0.0)]:
            response=self.response();response[field]=value
            with self.assertRaises(ContractError):q.validate_response(self.prepared.request,response)

    def test_unbounded_abstention_reason_is_rejected(self):
        response=self.response();response.update(answer_status='partial',abstention_reason='Δ'*5000)
        with self.assertRaises(ContractError):q.validate_response(self.prepared.request,response)

    def test_malformed_proposition_enum_has_contract_error(self):
        for value in [[],{}]:
            response=self.response();response['claims'][0]['proposition']['modal']=value
            with self.assertRaises(ContractError):q.validate_response(self.prepared.request,response)

    def test_malformed_applicability_enum_has_contract_error(self):
        for value in [[],{}]:
            response=self.response();response['claims'][0]['applicability']=value
            with self.assertRaises(ContractError):q.validate_response(self.prepared.request,response)

    def test_typed_versions_and_unknown_fields_rejected(self):
        for field,value in [('schema_version',2.0),('answer_status',False),('question_key','foreign')]:
            response=self.response();response[field]=value
            with self.assertRaises(ContractError):q.validate_response(self.prepared.request,response)
        response=self.response();response['extra']='unreviewed'
        with self.assertRaises(ContractError):q.validate_response(self.prepared.request,response)


if __name__=='__main__':unittest.main()
