"""Evaluator runner safety checks; no real server, credentials or paid calls."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from asof.journal import read_chain
from asof.serde import ContractError, sha256_file, write_json
from tools.science.outcome_extract import check_pins, extract, source_lease, validate_plan


class ExtractionSafetyTests(unittest.TestCase):
    def test_changed_ancestor_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source';path.write_bytes(b'first')
            pin={'path':str(path),'sha256':sha256_file(path),'bytes':5}
            check_pins([pin]);path.write_bytes(b'other')
            with self.assertRaises(ContractError):check_pins([pin])

    def test_conflicting_identity_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source';path.write_bytes(b'same')
            with self.assertRaises(ContractError):
                check_pins([{'path':str(path),'sha256':sha256_file(path)},
                            {'path':str(path),'sha256':'0'*64}])

    def test_concurrent_source_lease_rejected_and_released(self):
        with tempfile.TemporaryDirectory() as tmp:
            with source_lease(Path(tmp)):
                with self.assertRaises(FileExistsError):
                    with source_lease(Path(tmp)):pass
            with source_lease(Path(tmp)):pass

    def test_bad_plan_journaled_before_any_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);plan=root/'plan.json';out=root/'out'
            write_json(plan,{'schema_version':99})
            with patch('tools.science.outcome_extract.subprocess.run') as dispatch:
                with self.assertRaises(ContractError):extract(plan,sha256_file(plan),out)
                dispatch.assert_not_called()
            self.assertEqual(read_chain(out/'journal.jsonl')[-1]['event'],'build_failed')
            self.assertTrue((out/'failure.json').is_file())

    def test_changed_plan_fails_without_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);plan=root/'plan.json';write_json(plan,{})
            with patch('tools.science.outcome_extract.subprocess.run') as dispatch:
                with self.assertRaises(ContractError):extract(plan,'0'*64,root/'out')
                dispatch.assert_not_called()

    def test_output_reuse_cannot_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('tools.science.outcome_extract.subprocess.run') as dispatch:
                with self.assertRaises(FileExistsError):extract(Path('missing'),'0'*64,Path(tmp))
                dispatch.assert_not_called()

    def test_shifted_window_and_incomplete_membership_rejected(self):
        plan={'schema_version':1,'protocol_id':'science4-outcome-inputs-v1','role':'evaluation_only',
            'provider_spend_usd':0,'clinical_activation':False,'origin_at':'2025-01-01T00:00:00Z',
            'horizon_at':'2026-01-01T00:00:00Z','ascertainment_at':'2026-04-02T00:00:00Z'}
        with self.assertRaisesRegex(ContractError,'chronology'):validate_plan(plan)
        plan['ascertainment_at']='2026-04-01T00:00:00Z';plan['nct_ids']=['NCT00000001']
        with self.assertRaisesRegex(ContractError,'twelve'):validate_plan(plan)


if __name__=='__main__':unittest.main()
