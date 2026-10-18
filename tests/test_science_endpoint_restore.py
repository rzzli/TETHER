import tempfile
from pathlib import Path
import unittest

from asof.serde import ContractError,read_json,sha256_file,write_json
from tools.science.endpoint_restore import restore,validate_gate,verify_origin_closure
from tests import test_science_historical_inputs as history_fixtures


class EndpointRestoreGateTests(unittest.TestCase):
    def setUp(self):
        self.origin={'status':'sealed_mapping_qualified_reconstructed_exploratory',
            'origin_at':'2025-01-01T00:00:00Z','horizon_at':'2026-01-01T00:00:00Z',
            'selection_sealed':True,'mapping_qualified':True,'reconstructed_origin_information_eligible':True,
            'endpoint_rows_queried':0,'clinical_ready':False,'clinical_locked':False,
            'strict_dataset_availability_qualified':False,'registry_completeness_qualified':False,'origin_date_qualified':False}
        self.decision={'mode':'reconstructed_exploratory','technical_restore_only':True,
            'endpoint_cohort_queries_allowed':False,'clinical_activation_allowed':False}

    def ancestors(self,p):
        history=p/'history';history.mkdir()
        manifest,self.manifest_data=history_fixtures.HistoricalInputTests().fixture_manifest(history)
        write_json(p/'ancestor.json',{'invented_fixture':True})
        proof={'path':str(p/'ancestor.json'),'sha256':sha256_file(p/'ancestor.json')}
        parent=p/'parent.json';write_json(parent,{'origin_at':self.origin['origin_at'],
            'selection_sealed':True,'endpoint_rows_queried':0,'files':[proof]})
        self.origin.update(files=[proof],parent_origin_seal={'path':str(parent),'sha256':sha256_file(parent)},
            historical_mapping_manifest={'path':str(manifest),'sha256':sha256_file(manifest)},reconstruction_rules_proof=proof)

    def test_candidate_only_seal_cannot_open_restore_gate(self):
        self.origin['mapping_qualified']=False
        with self.assertRaises(ContractError):validate_gate(self.origin,self.decision)

    def test_exploratory_route_cannot_activate_clinical_truth(self):
        self.origin['clinical_locked']=True
        with self.assertRaises(ContractError):validate_gate(self.origin,self.decision)

    def test_labels_require_separate_later_authorization(self):
        self.decision['endpoint_cohort_queries_allowed']=True
        with self.assertRaises(ContractError):validate_gate(self.origin,self.decision)

    def test_bad_origin_fails_before_any_executor_call_and_keeps_record(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);self.origin['selection_sealed']=False
            write_json(p/'origin.json',self.origin);write_json(p/'decision.json',self.decision)
            calls=[]
            with self.assertRaises(ContractError):restore(p/'origin.json',sha256_file(p/'origin.json'),
                p/'decision.json',sha256_file(p/'decision.json'),p/'out',{},executor=lambda *a:calls.append(a))
            self.assertEqual(calls,[]);self.assertTrue((p/'out/failure.json').exists())

    def test_valid_gate_dispatches_once_with_literal_empty_query(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);self.ancestors(p)
            write_json(p/'origin.json',self.origin)
            self.decision['origin_seal_sha256']=sha256_file(p/'origin.json');write_json(p/'decision.json',self.decision)
            calls=[]
            def execute(plan,destination):
                calls.append(1)
                self.assertEqual(Path(plan['frozen_cohort_query']).read_text(),"SELECT '[]'::text;\n")
            archive=p/'archive.zip';archive.write_bytes(b'invented archive fixture')
            plan={'snapshots':[{'requested_date':'2026-01-01','archive':str(archive)}],
                  'frozen_nct_ids':[],'source_archive_sha256':sha256_file(archive)}
            result=restore(p/'origin.json',sha256_file(p/'origin.json'),p/'decision.json',sha256_file(p/'decision.json'),p/'out',plan,executor=execute)
            self.assertEqual(calls,[1]);self.assertFalse(result['clinical_activation'])
            with self.assertRaises(FileExistsError):restore(p/'origin.json',sha256_file(p/'origin.json'),
                p/'decision.json',sha256_file(p/'decision.json'),p/'out',plan,executor=execute)
            self.assertEqual(calls,[1])

    def test_changed_archive_never_reaches_restore_executor(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);self.ancestors(p)
            write_json(p/'origin.json',self.origin)
            self.decision['origin_seal_sha256']=sha256_file(p/'origin.json');write_json(p/'decision.json',self.decision)
            archive=p/'archive.zip';archive.write_bytes(b'changed after qualification');calls=[]
            plan={'snapshots':[{'requested_date':'2026-01-01','archive':str(archive)}],'frozen_nct_ids':[],
                  'source_archive_sha256':'0'*64}
            with self.assertRaises(ContractError):restore(p/'origin.json',sha256_file(p/'origin.json'),
                p/'decision.json',sha256_file(p/'decision.json'),p/'out',plan,executor=lambda *a:calls.append(a))
            self.assertEqual(calls,[])

    def test_changed_transitive_raw_parent_never_reaches_executor(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);self.ancestors(p)
            write_json(p/'origin.json',self.origin)
            self.decision['origin_seal_sha256']=sha256_file(p/'origin.json');write_json(p/'decision.json',self.decision)
            Path(self.manifest_data['files'][0]['path']).write_bytes(b'changed raw parent')
            archive=p/'archive.zip';archive.write_bytes(b'invented archive fixture');calls=[]
            plan={'snapshots':[{'requested_date':'2026-01-01','archive':str(archive)}],
                  'frozen_nct_ids':[],'source_archive_sha256':sha256_file(archive)}
            with self.assertRaises(ContractError):restore(p/'origin.json',sha256_file(p/'origin.json'),
                p/'decision.json',sha256_file(p/'decision.json'),p/'out',plan,executor=lambda *a:calls.append(a))
            self.assertEqual(calls,[])

    def test_legacy_and_current_origin_archive_receipts_bind_raw_members(self):
        for legacy in (True,False):
            with self.subTest(legacy=legacy),tempfile.TemporaryDirectory() as temp:
                p=Path(temp);self.ancestors(p)
                archive=p/'source-archive.zip';archive.write_bytes(b'invented source archive')
                extracted=p/'extracted';extracted.mkdir();member=extracted/'postgres.dmp';member.write_bytes(b'invented dump')
                receipt={'archive':str(archive),'members':[{'name':'postgres.dmp','bytes':member.stat().st_size,'sha256':sha256_file(member)}]}
                receipt.update({'sha256':sha256_file(archive),'bytes':archive.stat().st_size} if legacy else
                    {'archive_sha256':sha256_file(archive),'archive_bytes':archive.stat().st_size})
                write_json(p/'archive-inspection.json',receipt)
                parent=read_json(p/'parent.json');parent['source_receipts']=[{'path':str(p/'archive-inspection.json'),'sha256':sha256_file(p/'archive-inspection.json')}]
                write_json(p/'parent.json',parent);self.origin['parent_origin_seal']['sha256']=sha256_file(p/'parent.json')
                write_json(p/'origin.json',self.origin)
                _,pins=verify_origin_closure(p/'origin.json',sha256_file(p/'origin.json'))
                self.assertIn(member.resolve(),pins)
                member.write_bytes(b'changed original dump')
                with self.assertRaises(ContractError):verify_origin_closure(p/'origin.json',sha256_file(p/'origin.json'))

    def test_transitive_input_change_during_restore_prevents_success(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp);self.ancestors(p);write_json(p/'origin.json',self.origin)
            self.decision['origin_seal_sha256']=sha256_file(p/'origin.json');write_json(p/'decision.json',self.decision)
            archive=p/'archive.zip';archive.write_bytes(b'invented endpoint archive')
            plan={'snapshots':[{'requested_date':'2026-01-01','archive':str(archive)}],
                  'frozen_nct_ids':[],'source_archive_sha256':sha256_file(archive)}
            def changed(*args):Path(self.manifest_data['files'][0]['path']).write_bytes(b'changed during execution')
            with self.assertRaises(ContractError):restore(p/'origin.json',sha256_file(p/'origin.json'),
                p/'decision.json',sha256_file(p/'decision.json'),p/'out',plan,executor=changed)
            self.assertFalse((p/'out/report.json').exists());self.assertTrue((p/'out/failure.json').exists())
