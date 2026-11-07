"""Unrelated invented metadata controls; no private bank or model is loaded."""
import copy
import hashlib
import unittest

from tether_engine.serde import canonical, encode, fingerprint, freeze
from experiments.litqa_refinement import contracts
from . import qualification as q


def _proof(name, raw):
    return dict(path='/fictional-bank/'+name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def invented_bundle():
    unsure='Insufficient information to answer the question'
    choices=[['Increased','Decreased','Unchanged',unsure], ['Increased','Decreased',unsure,'Unchanged'],
             [unsure,'Increased','Unchanged','Decreased'], ['Unchanged',unsure,'Decreased','Increased'],
             [unsure,'Increased','Decreased','Unchanged'], ['Increased',unsure,'Decreased','Unchanged']]
    answers=[0,1,2,3,0,1];relations=['increase','decrease','no_change','increase','unresolved_conflict','empty']
    cases=[];parents=[];expectations=[];slots={};documents={}
    def store(name,value):
        raw=canonical(encode(value));documents[name]=raw;return _proof(name,raw)
    for i in range(6):
        query=dict(id=f'570a4612-e098-4450-89bf-00000000{8200+i:04d}',question=f'In the fictional instrument exercise {i}, what happened to the requested reading?',
                   choices=[f'({chr(65+j)}) {text}' for j,text in enumerate(choices[i])])
        texts=[] if i==5 else ['Unit-test report U states the reading increased.','Unit-test report V states the reading decreased; neither is preferred.'] if i==4 else [
            f'Unit-test report {i} explicitly states that the requested reading was {choices[i][answers[i]].lower()}.']
        sources=[dict(source_id=f'fixture-{i}-{j}',text=text,sha256=hashlib.sha256(text.encode()).hexdigest()) for j,text in enumerate(texts)]
        idx=None if i==2 else choices[i].index(unsure) if i==1 else 1 if i==0 else 0
        prediction=None if idx is None else dict(answer_index=idx,evidence_ids=[])
        pc=dict(kind='invented_prior_capture_v1',actual_model_call=False,query=query,prediction=prediction)
        prior=contracts.candidate(query,prediction,producer_status='input_unavailable' if idx is None else 'produced',
            original_admission_status='not_run' if idx is None else 'accepted' if idx==choices[i].index(unsure) else 'rejected',
            native_call_sha256=None if idx is None else fingerprint(pc),generated_at_utc=None if idx is None else '2020-01-01T00:00:00+00:00',offered_ids=[])
        decoded=dict(support='not_assessable' if idx is None else 'insufficient',evidence_ids=[],criticism='Earlier record had no result.',queries=[['test device'],['reading comparison']])
        cc=dict(kind='invented_critic_capture_v1',actual_model_call=False,query=query,prior=prior,sources=[],decoded=decoded)
        critique=contracts.critique(query,prior,[],decoded,native_status='completed',native_call_sha256=fingerprint(cc))
        case=dict(query=query,candidate_context=prior,critique_context=critique,sources=sources);cases.append(case)
        parents.append(dict(id=query['id'],scope='fictional_qualification',invented=True,prior_sources=[],prior_capture=pc,critic_capture=cc,
            prior_capture_is_actual_native=False,critic_capture_is_actual_native=False,cutoff_utc='2020-01-10T00:00:00+00:00',
            critique_created_at_utc='2020-01-02T00:00:00+00:00',current_source_available_at_utc={s['source_id']:'2020-01-03T00:00:00+00:00' for s in sources}))
        for phase in q.PHASES:
            raw=sources if phase=='repair' else [];name=f'actor_cases/{phase}-{i:04d}.json'
            slots[name]=dict(proof=store(name,dict(task=phase,query=query,candidate_context=prior,critique_context=critique,sources=raw)),
                role='single_slot_actor_input',phase=phase,ordinal=i,id=query['id'])
            positive=phase=='repair' and i<4;index=answers[i] if phase=='repair' else choices[i].index(unsure)
            expectations.append(dict(phase=phase,ordinal=i,id=query['id'],answer_index=index,answer_text=choices[i][index],
                semantic_role=relations[i] if phase=='repair' else 'raw_evidence_removed',allowed_citation_ids=[s['source_id'] for s in raw],
                required_any_citation_ids=[raw[0]['source_id']] if positive else [],empty_citations_required=not raw,
                allowed_native_outcome='completed',producer_status='produced',check_status='accepted',
                supporting_quotes=[dict(source_id=raw[0]['source_id'],text=raw[0]['text'])] if positive else []))
    expectations.sort(key=lambda x:(q.PHASES.index(x['phase']),x['ordinal']))
    actor=store('ACTOR.json',dict(kind='synthetic_refinement_contexts_v1',scope='fictional_qualification',cases=cases))
    ancestry=store('ANCESTRY.json',dict(kind='synthetic_refinement_ancestry_v1',scope='fictional_qualification',actual_prior_model_calls=0,cases=parents))
    evaluator=store('EVALUATOR.json',dict(kind='synthetic_refinement_expectations_v1',role='evaluation_only',expectations=expectations))
    decision=_proof('DECISION.md',b'Unrelated invented authorization')
    bank=dict(schema_version=1,kind='tether_evidence_first_qualification_bank_v1',purpose='fictional_qualification',
        created_at_utc='2020-01-11T00:00:00+00:00',decision=decision,phase_order=list(q.PHASES),max_native_calls=12,source_http_requests=0,
        independence=dict(new_prompt_implementation_read=False,benchmark_questions_or_keys_read=False,model_or_network_calls=0,
            expected_answers_shared_with_prompt_author_before_sealing=False,external_human_review=False),
        rules=dict(complete_schedule_required=True,all_controls_must_pass=True,automatic_retry=False,removal_actor_can_read_full_bank=False,
            per_slot_only_actor_grants=True,archived_code_executed=False),schedule=[c['query']['id'] for c in cases],slots=slots,
        role_files={'contexts':dict(proof=actor,role='coordinator_only'),'ancestry':dict(proof=ancestry,role='coordinator_only'),
                    'expectations':dict(proof=evaluator,role='evaluation_only')})
    return encode(bank),documents


class QualificationTests(unittest.TestCase):
    def setUp(self):self.bank,self.documents=invented_bundle()
    def validate(self):
        raw=canonical(self.bank)
        return q.validate_bank_bundle(raw,self.documents,expected_bank_sha256=hashlib.sha256(raw).hexdigest(),expected_decision_sha256=self.bank['decision']['sha256'])
    def edit(self,name,change):
        body=q.parse_json(self.documents[name]);change(body);raw=canonical(body);self.documents[name]=raw
        if name.startswith('actor_cases/'):
            self.bank['slots'][name]['proof']=_proof(name,raw)
        else:
            key={'ACTOR.json':'contexts','ANCESTRY.json':'ancestry','EVALUATOR.json':'expectations'}[name]
            self.bank['role_files'][key]['proof']=_proof(name,raw)
    def responses(self,bank):
        return [dict(phase=x['phase'],ordinal=x['ordinal'],id=x['id'],status='completed',producer_status='produced',check_status='accepted',
            prediction=dict(answer_index=x['answer_index'],evidence_ids=list(x['required_any_citation_ids']))) for x in bank['expectations']]
    def test_complete_metadata_and_internal_comparison_never_issue_capability(self):
        bank=self.validate();result=q._compare_expectations(bank,self.responses(bank))
        self.assertEqual(result['controls'],12);self.assertFalse(bank['execution_capability'])
        for name in ('native_integrity_verified','source_execution_verified','process_integrity_verified','qualification_issued'):self.assertFalse(result[name])
        with self.assertRaises(TypeError):bank['expectations'][0]['answer_index']=3
        q._compare_expectations(bank,freeze(self.responses(bank)))
    def test_all_twelve_wrong_answers_fail_without_remapping(self):
        bank=self.validate();original=self.responses(bank)
        for i in range(12):
            rows=copy.deepcopy(original);rows[i]['prediction']['answer_index']=(rows[i]['prediction']['answer_index']+1)%4
            with self.subTest(slot=i),self.assertRaisesRegex(ValueError,'expected answer'):q._compare_expectations(bank,rows)
    def test_all_case_order_and_no_missing_duplicate_or_extra_calls(self):
        bank=self.validate();rows=self.responses(bank)
        for changed in (rows[:-1],rows+[rows[0]],list(reversed(rows)),[rows[0]]+rows[:-1]):
            with self.assertRaises(ValueError):q._compare_expectations(bank,changed)
    def test_failure_missing_prediction_and_boolean_index_cannot_pass(self):
        bank=self.validate();original=self.responses(bank)
        for key,value in (('status','authenticated_limit_failure'),('producer_status','error'),('check_status','not_run'),('prediction',None)):
            rows=copy.deepcopy(original);rows[0][key]=value
            with self.assertRaises(Exception):q._compare_expectations(bank,rows)
        rows=copy.deepcopy(original);rows[0]['prediction']['answer_index']=False
        with self.assertRaises(Exception):q._compare_expectations(bank,rows)
    def test_required_support_citation_and_optional_conflict_citations(self):
        bank=self.validate();rows=self.responses(bank);rows[0]['prediction']['evidence_ids']=[]
        with self.assertRaisesRegex(ValueError,'supporting citation'):q._compare_expectations(bank,rows)
        for subset in ([],list(bank['expectations'][4]['allowed_citation_ids'][:1]),list(bank['expectations'][4]['allowed_citation_ids'])):
            rows=self.responses(bank);rows[4]['prediction']['evidence_ids']=subset;q._compare_expectations(bank,rows)
    def test_no_unsupported_duplicate_or_removal_citations(self):
        bank=self.validate();original=self.responses(bank)
        for i,ids in ((0,['not-offered']),(0,original[0]['prediction']['evidence_ids']*2),(6,original[0]['prediction']['evidence_ids'])):
            rows=copy.deepcopy(original);rows[i]['prediction']['evidence_ids']=ids
            with self.assertRaises(Exception):q._compare_expectations(bank,rows)
    def test_changed_captured_bytes_external_anchor_or_decision_fails(self):
        raw=canonical(self.bank)
        for banksha,decision in (('0'*64,self.bank['decision']['sha256']),(hashlib.sha256(raw).hexdigest(),'0'*64)):
            with self.assertRaises(ValueError):q.validate_bank_bundle(raw,self.documents,expected_bank_sha256=banksha,expected_decision_sha256=decision)
        self.documents['ACTOR.json']+=b' '
        with self.assertRaisesRegex(ValueError,'bytes differ'):self.validate()
    def test_manifest_roles_and_gold_in_actor_rejected_after_resealing(self):
        self.bank['role_files']['expectations']['role']='single_slot_actor_input'
        with self.assertRaisesRegex(ValueError,'role separation'):self.validate()
        self.bank['role_files']['expectations']['role']='evaluation_only'
        self.edit('ACTOR.json',lambda body:body.update(expected_answers=[1]*6))
        with self.assertRaisesRegex(ValueError,'gold'):self.validate()
    def test_removal_source_leak_and_extra_actor_fields_rejected(self):
        raw=q.parse_json(self.documents['actor_cases/repair-0000.json'])['sources']
        self.edit('actor_cases/removal-0000.json',lambda body:body.update(sources=raw))
        with self.assertRaisesRegex(ValueError,'paired projection'):self.validate()
    def test_resealed_context_and_capture_lineage_changes_rejected(self):
        self.edit('ANCESTRY.json',lambda body:body['cases'][0]['prior_capture'].update(actual_model_call=True))
        with self.assertRaisesRegex(ValueError,'capture context'):self.validate()
    def test_semantic_answer_and_support_quote_tampering_rejected(self):
        self.edit('EVALUATOR.json',lambda body:body['expectations'][0]['supporting_quotes'][0].update(text='Absent invented text'))
        with self.assertRaisesRegex(ValueError,'Supporting quote'):self.validate()
    def test_future_source_or_false_native_authorship_rejected(self):
        self.edit('ANCESTRY.json',lambda body:body['cases'][0]['current_source_available_at_utc'].update({'fixture-0-0':'2090-01-01T00:00:00+00:00'}))
        with self.assertRaisesRegex(ValueError,'chronology'):self.validate()
    def test_exact_document_membership_and_canonical_logical_paths(self):
        self.documents['extra.json']=b'{}'
        with self.assertRaisesRegex(ValueError,'fifteen'):self.validate()
        del self.documents['extra.json']
        self.bank['role_files']['contexts']['proof']['path']='/fictional-bank/../other/ACTOR.json'
        with self.assertRaisesRegex(ValueError,'logical proof path'):self.validate()
    def test_independence_and_complete_gate_cannot_be_weakened(self):
        self.bank['independence']['new_prompt_implementation_read']=True
        with self.assertRaisesRegex(ValueError,'authorship'):self.validate()
        self.bank['independence']['new_prompt_implementation_read']=False;self.bank['rules']['all_controls_must_pass']=False
        with self.assertRaisesRegex(ValueError,'bank and role'):self.validate()
    def test_typed_ordinals_and_completed_requirement_cannot_be_substituted(self):
        self.edit('EVALUATOR.json',lambda body:body['expectations'][0].update(ordinal=False))
        with self.assertRaisesRegex(ValueError,'membership/order'):self.validate()
    def test_boolean_authorship_and_gate_flags_cannot_be_numbers(self):
        original=copy.deepcopy(self.bank)
        for group in ('independence','rules'):
            for key,value in original[group].items():
                if type(value) is not bool:continue
                self.bank=copy.deepcopy(original);self.bank[group][key]=int(value)
                with self.subTest(group=group,key=key),self.assertRaises(ValueError):self.validate()


if __name__=='__main__':unittest.main()
