"""Invented-source tests for evaluator reference assembly, never biomedical truth."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

from asof.serde import ContractError,read_json,sha256_file,write_json
from tests import test_v02_ingest as fixtures
from tests import test_science_reference_packets as reference_fixtures
from tools.science.finalize_reference import assemble
from tools.science.reference_panel import RUBRIC,validate_q1


@unittest.skipUnless(importlib.util.find_spec('pyarrow'),'install the ingest extra for source-audit tests')
class FinalizeReferenceTests(unittest.TestCase):
    setUp = fixtures.IngestTests.setUp
    tearDown = fixtures.IngestTests.tearDown
    save_manifest = fixtures.IngestTests.save_manifest
    receipt = fixtures.IngestTests.receipt
    evidence = fixtures.IngestTests.evidence
    make_build = reference_fixtures.ReferencePacketBuildTests.make_build
    prepare = reference_fixtures.ReferencePacketBuildTests.prepare

    def setup_reference(self):
        self.make_build()
        self.prepare()
        self.source = self.root/'reference'
        self.source_hash = sha256_file(self.source/'reference-report.json')
        audits = read_json(self.source/self.case_id/'raw-row-audit.json')
        observations = [{'observation_id':a['observation_id'],'source_row_sha256':a['source_row_sha256'],
            'answer':'supported','rationale':'Invented annotation matches invented source',
            'rubric':{k:'Fixture context; no therapeutic inference' for k in RUBRIC},
            'context_qualifiers':['Invented test data']} for a in audits]
        cases = [{'case_id':self.case_id,'question_id':'Q1','finding':'Resource annotation',
                  'rationale':'Fixture source match','uncertainty':'Biology not assessed','observations':observations}]
        self.reviews=[]
        for name in ('a','b'):
            p=self.root/(name+'.json')
            write_json(p,{'reviewer_id':name,'model_provenance':{'execution_id':name,'model_id':None,'reason':'test'},
                'blind_to_arm_outputs':True,'other_reviewer_answers_visible':False,
                'source_report_sha256':self.source_hash,'cases':cases})
            self.reviews.append(p)
        self.adjudication=self.root/'adjudication.json'
        write_json(self.adjudication,{'source_report_sha256':self.source_hash,'external_independence':False,
            'model_provenance':{'execution_id':'third','model_id':None,'reason':'test'},
            'review_sha256s':[sha256_file(p) for p in self.reviews],'cases':cases})

    def run_assembly(self):
        return assemble(self.source,self.reviews,self.adjudication,self.root/'assembled',
                        source_report_sha256=self.source_hash)

    def test_full_source_fidelity_reference_remains_evaluator_only(self):
        self.setup_reference()
        report=self.run_assembly()
        self.assertEqual(report['references'],1)
        self.assertFalse(report['independent_scientific_truth'])
        ref=read_json(self.root/'assembled/references.json')['references'][0]
        self.assertEqual(ref['role'],'evaluation_only')
        self.assertEqual(ref['reference_level'],'ai_source_adjudicated')

    def test_adjudication_bound_to_exact_review_bytes(self):
        self.setup_reference()
        review=read_json(self.reviews[0]);review['cases'][0]['rationale']='Changed after adjudication'
        write_json(self.reviews[0],review)
        with self.assertRaises(ContractError):self.run_assembly()
        self.assertTrue((self.root/'assembled/failure.json').exists())

    def test_missing_adjudicated_row_cannot_be_silently_skipped(self):
        self.setup_reference()
        a=read_json(self.adjudication);a['cases'][0]['observations']=[];write_json(self.adjudication,a)
        with self.assertRaises(ContractError):self.run_assembly()

    def test_source_changed_after_review_validation_is_rejected(self):
        self.setup_reference()
        calls=[]
        def checked(*args):
            report=validate_q1(*args);calls.append(1)
            if len(calls)==2:
                path=self.source/self.case_id/'source-packet.json'
                packet=read_json(path);packet['observations'][0]['statement']='Unreviewed replacement'
                write_json(path,packet)
            return report
        with patch('tools.science.finalize_reference.validate_q1',side_effect=checked):
            with self.assertRaises(ContractError):self.run_assembly()
        self.assertFalse((self.root/'assembled/report.json').exists())

    def test_adjudicator_cannot_reuse_an_initial_context(self):
        self.setup_reference()
        a=read_json(self.adjudication);a['model_provenance']['execution_id']='a';write_json(self.adjudication,a)
        with self.assertRaises(ContractError):self.run_assembly()

    def test_review_mutation_cannot_rebind_already_parsed_judgments(self):
        self.setup_reference()
        calls=[]
        def checked(*args):
            result=validate_q1(*args);calls.append(1)
            if len(calls)==2:
                review=read_json(self.reviews[0])
                review['cases'][0]['observations'][0]['rationale']='Unreviewed replacement'
                write_json(self.reviews[0],review)
                a=read_json(self.adjudication)
                a['review_sha256s']=[sha256_file(p) for p in self.reviews]
                write_json(self.adjudication,a)
            return result
        with patch('tools.science.finalize_reference.validate_q1',side_effect=checked):
            with self.assertRaises(ContractError):self.run_assembly()
        self.assertFalse((self.root/'assembled/report.json').exists())
