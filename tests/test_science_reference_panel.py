import copy
import unittest

from tether_engine.serde import ContractError
from tools.science.reference_panel import RUBRIC, validate_panel, validate_q1_rows


class ReferencePanelTests(unittest.TestCase):
    def setUp(self):
        self.case = dict(case_id='case-a', symbol='A', disease_id='D', intended_action='inhibit', modality='antibody')
        self.pack = {'cases': [self.case]}
        self.panel = dict(schema_version=1, reviewer_type='ai_agent', blind_to_arm_outputs=True,
            other_reviewer_answers_visible=False, model_provenance={'execution_id':'panel-a','model_id':None,'reason':'not exposed'},
            cases=[self.case | dict(case_key='case-a', reference_level='ai_source_adjudicated',
                context_constraints=['not generalizable'], uncertainties=['limited scope'],
                primary_sources=[dict(source_id=s, url='https://example.org/'+s, title='Original study',
                    publication_date='2024',access_depth='abstract',source_type='original_trial',findings_supported=['Q2','Q3','Q4'])
                    for s in ('a','b')],
                questions=[dict(question_id=q,finding='uncertain',rationale='Study is scoped',source_refs=['a','b'],uncertainty='No extrapolation')
                    for q in ('Q2','Q3','Q4')])])

    def test_valid_does_not_certify_science(self):
        result = validate_panel(self.panel, self.pack)
        self.assertFalse(result['external_scientific_validation'])
        self.assertEqual(result['answered_questions'], 3)

    def test_exact_scope(self):
        self.panel['cases'][0]['modality'] = 'small_molecule'
        with self.assertRaises(ContractError): validate_panel(self.panel, self.pack)

    def test_explicit_tissue_cannot_override_unspecified_scope(self):
        self.panel['cases'][0]['tissue']='brain'
        with self.assertRaises(ContractError):validate_panel(self.panel,self.pack)

    def test_citation_must_resolve(self):
        self.panel['cases'][0]['questions'][0]['source_refs'] = ['missing']
        with self.assertRaises(ContractError): validate_panel(self.panel, self.pack)

    def test_future_sources_rejected(self):
        self.panel['cases'][0]['primary_sources'][0]['publication_date'] = '2027-01-01'
        with self.assertRaises(ContractError): validate_panel(self.panel, self.pack)

    def test_unknown_publication_requires_reason(self):
        ref = self.panel['cases'][0]['primary_sources'][0]
        ref['publication_date'] = None
        with self.assertRaises(ContractError): validate_panel(self.panel, self.pack)
        ref['publication_date_reason'] = 'Official label has no exposed version date'
        validate_panel(self.panel, self.pack)

    def test_blinding_is_explicit(self):
        self.panel['other_reviewer_answers_visible'] = True
        with self.assertRaises(ContractError): validate_panel(self.panel, self.pack)

    def test_duplicate_case_not_coverage(self):
        self.panel['cases'].append(copy.deepcopy(self.panel['cases'][0]))
        with self.assertRaises(ContractError): validate_panel(self.panel, self.pack)

    def test_ai_cannot_certify_external_independence(self):
        self.panel['cases'][0]['reference_level'] = 'independently_adjudicated'
        with self.assertRaises(ContractError): validate_panel(self.panel, self.pack)

    def test_duplicate_source_not_two_references(self):
        self.panel['cases'][0]['primary_sources'][1]['url'] = 'https://example.org/a'
        with self.assertRaises(ContractError): validate_panel(self.panel, self.pack)

    def test_model_unknown_is_candid(self):
        del self.panel['model_provenance']['reason']
        with self.assertRaises(ContractError): validate_panel(self.panel, self.pack)


class Q1ContractTests(unittest.TestCase):
    def setUp(self):
        self.expected = {'a':{'row-1':'1'*64,'row-2':'2'*64}}
        self.review = {'reviewer_id':'panel-a','model_provenance':{'execution_id':'a','model_id':None,'reason':'not exposed'},
            'blind_to_arm_outputs':True,'other_reviewer_answers_visible':False,'source_report_sha256':'3'*64,
            'cases':[{'case_id':'a','question_id':'Q1','finding':'Source annotation only','rationale':'Matches original',
                'uncertainty':'No therapeutic inference','observations':[
                    {'observation_id':key,'source_row_sha256':value,'answer':'supported','rationale':'Faithful annotation',
                     'rubric':{k:'Resource context only' for k in RUBRIC},'context_qualifiers':['No drug direction inferred']}
                    for key,value in self.expected['a'].items()]}]}

    def test_every_selected_row_reviewed(self):
        self.assertEqual(validate_q1_rows(self.review,self.expected,'3'*64)['reviewed_rows'],2)

    def test_missing_original_row_fails(self):
        self.review['cases'][0]['observations'].pop()
        with self.assertRaises(ContractError): validate_q1_rows(self.review,self.expected,'3'*64)

    def test_changed_source_fails(self):
        self.review['cases'][0]['observations'][0]['source_row_sha256'] = '4'*64
        with self.assertRaises(ContractError): validate_q1_rows(self.review,self.expected,'3'*64)

    def test_rubric_numeric_score_is_not_explanation(self):
        self.review['cases'][0]['observations'][0]['rubric']['source_fidelity'] = 1
        with self.assertRaises(ContractError): validate_q1_rows(self.review,self.expected,'3'*64)

    def test_changed_source_report_fails(self):
        with self.assertRaises(ContractError): validate_q1_rows(self.review,self.expected,'0'*64)

    def test_uncertain_not_forced_to_support(self):
        self.review['cases'][0]['observations'][0]['answer'] = 'uncertain'
        result = validate_q1_rows(self.review,self.expected,'3'*64)
        self.assertEqual(result['answers'],{'uncertain':1,'supported':1})
