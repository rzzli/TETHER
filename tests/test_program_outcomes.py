import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.feasibility.program_outcomes import (date_bounds, report_window, phase_screen,
    incident_supported, validate_bundle, verify_manifest, sha)
from tools.feasibility.build_program_feasibility import run, proof, ROOT


class ProgramOutcomeTests(unittest.TestCase):
    def event(self):
        return {'event_id':'e','candidate_id':'P01','candidate_program_ids':['p'],
                'report_ids':['r'],'event_interval':{'lower':'2024-01-01','upper':'2024-08-01'},
                'scope_match':'qualified','content_status':'primary_report_or_manuscript_reviewed',
                'report_window':'within_window','incident_supported':True}

    def bundle(self):
        return {'dispositions':[{'candidate_id':'P01','program_ids':['p']}],
                'programs':[{'program_id':'p','candidate_id':'P01','arm_ids':['a'],
                             'role':'evaluation_only','historically_certified':False}],
                'trial-arm-links':[{'arm_id':'a','candidate_id':'P01'}],
                'reports':[{'report_id':'r','candidate_id':'P01','source_id':'s'}],
                'events':[self.event()],
                'followup-assessments':[{'candidate_id':'P01','clinical_label':None,'censoring_date':None}]}

    def test_partial_dates_and_boundary_are_not_invented_days(self):
        self.assertEqual(date_bounds('2024-02'),('2024-02-01','2024-02-29'))
        self.assertEqual(report_window('2025','2023-01-01','2025-01-01'),'straddles_boundary')
        self.assertEqual(report_window('2026-01-01','2023-01-01','2025-01-01'),'postendpoint')
        with self.assertRaises(ValueError): date_bounds('2024-13')

    def test_phase_formats_roles_and_unknown(self):
        for phase in ['Phase 2','PHASE2','PHASE_2']:
            self.assertEqual(phase_screen(phase,'ACTIVE_NOT_RECRUITING'),'provisional_origin_screen_pass')
        self.assertEqual(phase_screen('Phase 1/Phase 2','Recruiting'),'unresolved_arm_stage')
        self.assertEqual(phase_screen('Phase 2','UNKNOWN'),'unresolved_activity')
        self.assertEqual(phase_screen('Phase 2','Recruiting','closed_arm'),'excluded_anchor_role')
        self.assertEqual(phase_screen('Phase 3','Not yet recruiting'),'excluded_not_active_at_origin')

    def test_report_date_upper_bound_alone_cannot_certify_incident(self):
        event=self.event();self.assertTrue(incident_supported(event,'2023-01-01','2025-01-01'))
        for field,value in [('scope_match','unresolved'),('report_window','postendpoint'),
                            ('content_status','unavailable_full_content')]:
            changed={**event,field:value}
            self.assertFalse(incident_supported(changed,'2023-01-01','2025-01-01'))
        event['event_interval']['lower']=None
        self.assertFalse(incident_supported(event,'2023-01-01','2025-01-01'))

    def test_reversed_and_preorigin_event_intervals(self):
        event=self.event();event['event_interval']['lower']='2025-02-01'
        with self.assertRaises(ValueError):incident_supported(event,'2023-01-01','2025-01-01')
        event['event_interval']['lower']='2022-12-31'
        self.assertFalse(incident_supported(event,'2023-01-01','2025-01-01'))

    def test_duplicate_reports_and_platform_leakage_rejected(self):
        b=self.bundle();selected=[{'candidate_id':'P01'}]
        validate_bundle(b,selected)
        bad=copy.deepcopy(b);bad['reports'].append({**bad['reports'][0],'report_id':'duplicate'})
        with self.assertRaises(ValueError):validate_bundle(bad,selected)
        bad=copy.deepcopy(b);bad['trial-arm-links'][0]['candidate_id']='P02'
        with self.assertRaises(ValueError):validate_bundle(bad,selected)

    def test_missing_cases_later_mapping_and_censoring_rejected(self):
        b=self.bundle();selected=[{'candidate_id':'P01'}]
        with self.assertRaises(ValueError):validate_bundle(b,selected+[{'candidate_id':'P02'}])
        bad=copy.deepcopy(b);bad['programs'][0]['historically_certified']=True
        with self.assertRaises(ValueError):validate_bundle(bad,selected)
        bad=copy.deepcopy(b);bad['followup-assessments'][0]['censoring_date']='2025-01-01'
        with self.assertRaises(ValueError):validate_bundle(bad,selected)

    def test_manifest_tampering_and_path_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.write_text('original')
            manifest=root/'manifest.json';manifest.write_text(json.dumps({'files':[{'path':'source','sha256':sha(source)}]}))
            anchor=sha(manifest);self.assertEqual(verify_manifest(manifest,anchor),1)
            source.write_text('changed')
            with self.assertRaises(ValueError):verify_manifest(manifest,anchor)
            manifest.write_text(json.dumps({'files':[{'path':'../escape','sha256':'bad'}]}))
            with self.assertRaises(ValueError):verify_manifest(manifest,sha(manifest))

    def test_reserved_output_is_never_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'protocol.json').write_text(json.dumps({'protocol_id':'program-outcome-development-v0.2'}))
            reservation=root/'build-reservation.json';reservation.write_text('existing reservation')
            with self.assertRaises(FileExistsError):run(root)
            self.assertEqual(reservation.read_text(),'existing reservation')
            self.assertFalse((root/'build-journal.jsonl').exists())

    def test_relative_source_paths_produce_the_same_proof(self):
        path=Path('tools/feasibility/program_outcomes.py')
        self.assertEqual(proof(path),proof(ROOT/path))


if __name__=='__main__':unittest.main()
