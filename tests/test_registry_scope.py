import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from asof.serde import sha256_file
from tests import test_registry_sizing as fixtures
from tools.feasibility.registry_scope import ontology_index,relation,context,compare_context,run,verify_prior_row
trial=fixtures.trial


def diseases():
    return [{'id':'D1','name':'Condition X','ancestors':['D0'],
        'synonyms':{'hasExactSynonym':['Synonym X'],'hasNarrowSynonym':['Stage X'],'hasRelatedSynonym':['Related X'],'hasBroadSynonym':['Broad X']}},
        {'id':'D2','name':'Other disease','ancestors':['D0'],'synonyms':{'hasExactSynonym':['Collision']}},
        {'id':'D3','name':'Collision','ancestors':[],'synonyms':{}},
        {'id':'D0','name':'Disease family','ancestors':[],'synonyms':{}}]


class RegistryScopeTests(unittest.TestCase):
    def test_unique_exact_aliases_and_collision_without_precedence(self):
        aliases,proofs,ancestors=ontology_index(diseases())
        self.assertEqual(aliases['synonym x'],{'D1'})
        self.assertEqual(aliases['collision'],{'D2','D3'})
        for term in ['stage x','related x','broad x']:self.assertNotIn(term,aliases)
        self.assertEqual(relation('Condition X','Synonym X',aliases,ancestors),'same_unique_ontology_id')
        self.assertIsNone(relation('Condition X','Stage X',aliases,ancestors))
        self.assertEqual(relation('Condition X','Disease family',aliases,ancestors),'hierarchy_alert_only')
        self.assertIsNone(relation('Condition X','Other disease',aliases,ancestors))
        self.assertEqual(relation('Collision','Collision',aliases,ancestors),'same_verbatim_unresolved_ontology')
        with self.assertRaises(ValueError):ontology_index(diseases()+[diseases()[0]])

    def test_context_uses_matched_arms_and_keeps_study_title_separate(self):
        row=trial();row['study']['brief_title']='Intranasal pediatric extension'
        row['interventions'][0]['description']='Administered intravenously'
        row['design_groups'][0]['description']='Adults with metastatic cancer'
        row['design_groups'].append({'id':8,'title':'Oral comparator','description':'Given orally','group_type':'Active comparator'})
        c=context(row,[2]);signals=c['arm_signals']
        self.assertIn('intravenous',{s['value'] for s in signals})
        self.assertNotIn('oral',{s['value'] for s in signals})
        self.assertNotIn('pediatric',{s['value'] for s in signals})
        self.assertTrue(c['study_wide_signals']);self.assertTrue(c['missing_eligibility'])

    def test_negated_context_and_neoadjuvant_not_adjuvant(self):
        row=trial();row['design_groups'][0]['description']='Not metastatic. Neoadjuvant treatment without oral medication.'
        c=context(row,[2]);signals=c['arm_signals']
        self.assertTrue(any(s['value']=='metastatic' and s['negated_or_qualified'] for s in signals))
        self.assertIn('neoadjuvant',{s['value'] for s in signals});self.assertNotIn('adjuvant',{s['value'] for s in signals})
        self.assertEqual(compare_context(c,c)['clinical_scope_equivalence'],'not_established')

    def test_context_difference_is_not_scientific_exclusion(self):
        a=trial();b=copy.deepcopy(a)
        a['interventions'][0]['description']='Intravenous treatment'
        b['interventions'][0]['description']='Oral treatment'
        result=compare_context(context(a,[2]),context(b,[2]))
        self.assertIn('route_text_differs',result['alerts']);self.assertIsNone(result['training_label'])

    def test_study_wide_context_never_fills_missing_arm_eligibility(self):
        a=trial();b=copy.deepcopy(a)
        a['study']['brief_title']='Adults with metastatic cancer'
        b['study']['brief_title']='Pediatric adjuvant cancer trial'
        result=compare_context(context(a,[2]),context(b,[2]))
        self.assertIn('study_wide_age_words_text_differs',result['alerts'])
        self.assertIn('age_words',result['unreported_facets'])
        self.assertEqual(result['clinical_scope_equivalence'],'not_established')

    def test_original_prior_projection_mismatch_rejected(self):
        row=trial();alert={'source_proof':{'nct':'NCT00000001'},'phase':'PHASE2','start':'2022-02-01','date_type':'ACTUAL','condition':'condition x','source_arm_id':2}
        verify_prior_row(alert,row)
        for key,value in [('phase','Phase 4'),('condition','other disease'),('source_arm_id',8),('start','2020-01-01')]:
            changed={**alert,key:value}
            with self.assertRaises(ValueError):verify_prior_row(changed,row)

    def fixture(self,root,extra_origin=None):
        cohort=fixtures.RegistryCohortTests().build_fixture(root,extra_origin=extra_origin)
        parent=root/'parent.json';frame=root/'frames.json';frames=json.loads(frame.read_text())
        files=[frame]+list(cohort.iterdir())
        seal=root/'evidence.json';seal.write_text(json.dumps({'files':[{'path':p.relative_to(root).as_posix(),'sha256':sha256_file(p)} for p in files]}))
        parent.write_text(json.dumps({'canonical_manifest':{'path':str(seal),'sha256':sha256_file(seal)},'cohort':'output'}))
        raw=root/'ontology.bin';raw.write_bytes(b'fixture')
        receipt=root/'receipt.json';receipt.write_text(json.dumps({'status':'completed','dataset_id':'ot_disease','release_id':'25.09','sha256':sha256_file(raw),'bytes':raw.stat().st_size}))
        policy={'protocol_id':'registry-scope-development-v0.5','role':'evaluation_only',
            'parent_anchor':{'path':str(parent),'sha256':sha256_file(parent)},
            'disease_input':{'path':str(raw),'sha256':sha256_file(raw),'receipt_path':str(receipt),'receipt_sha256':sha256_file(receipt)},
            'clinical_scope':{'non_disease_exact_terms':['healthy volunteers'],'broad_condition_exact_terms':['disease']}}
        pp=root/'scope.json';pp.write_text(json.dumps(policy));freeze=root/'freeze.json';freeze.write_text(json.dumps({'protocol':{'sha256':sha256_file(pp)}}))
        return pp,freeze,raw

    def test_full_fixed_population_audit_and_changed_input_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);pp,freeze,raw=self.fixture(root)
            with patch('tools.feasibility.registry_scope.read_disease_rows',return_value=diseases()):
                run(pp,freeze,root/'audit')
                summary=json.loads((root/'audit/summary.json').read_text())
                self.assertEqual(summary['programs'],2);self.assertEqual(summary['event_links'],1)
                self.assertEqual(summary['training_labels'],0)
                self.assertEqual(summary['mapping_status'],{'unique_exact':2})
                raw.write_bytes(b'changed')
                with self.assertRaises(ValueError):run(pp,freeze,root/'bad')
                self.assertTrue((root/'bad/failure.json').exists())
                with self.assertRaises(FileExistsError):run(pp,freeze,root/'audit')

    def test_higher_phase_under_exact_synonym_is_flagged_without_relabeling(self):
        higher=trial('NCT00000007',phase='Phase 3',start='2021-01-01',posted='2020-01-01')
        higher['conditions'][0]['name']='Synonym X'
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);pp,freeze,raw=self.fixture(root,[higher])
            with patch('tools.feasibility.registry_scope.read_disease_rows',return_value=diseases()):run(pp,freeze,root/'audit')
            programs=json.loads((root/'audit/program-scope.json').read_text())
            p=next(p for p in programs if p['drug_name']=='ExampleA')
            self.assertEqual(p['prior_risk_alerts'][0]['relation'],'same_unique_ontology_id')
            self.assertTrue(p['prior_risk_alerts'][0]['actual_before_origin'])
            self.assertEqual(p['original_label_state'],'recorded_next_phase_start')
            self.assertIsNone(p['training_label'])


if __name__=='__main__':unittest.main()
