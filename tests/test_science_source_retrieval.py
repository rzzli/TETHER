import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tether_engine.serde import ContractError,read_json
from tether_engine.journal import read_chain
from tools.science.source_retrieval import fetch_control
from tests import test_science_source_retrieval_peer as fixture


class SourceControlDurabilityTests(unittest.TestCase):
    def setUp(self):self.helper=fixture.SourceRetrievalPeerTests()

    def test_mutating_caller_control_during_response_cannot_bless_html(self):
        body=b'<html>not a PDF</html>';control=self.helper.control(body)
        def response(request):
            control['expected_format']='html';control['allowed_hosts'].append('evil.invalid')
            return fixture.FakeResponse(body)
        with tempfile.TemporaryDirectory() as tmp:
            result=fetch_control(control,Path(tmp)/'out',open_response=response)
            self.assertIs(result['pdf_signature_matches'],False)
            self.assertIs(result['transport_control_passed'],False)
            self.assertEqual('pdf',read_json(Path(tmp)/'out/control.json')['expected_format'])

    def test_changed_control_file_fails_without_receipt_or_retry(self):
        body=b'%PDF-1.7 test';control=self.helper.control(body)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out';calls=[]
            def response(request):
                calls.append(request);(out/'control.json').write_bytes(b'{}')
                return fixture.FakeResponse(body)
            with self.assertRaises(ContractError):fetch_control(control,out,open_response=response)
            self.assertEqual(1,len(calls));self.assertFalse((out/'receipt.json').exists())
            self.assertEqual('build_failed',read_chain(out/'journal.jsonl')[-1]['event'])

    def test_timeout_leaves_failure_and_never_retries_or_reuses_output(self):
        control=self.helper.control(b'%PDF-1.7 test');calls=[]
        def response(request):calls.append(request);raise TimeoutError('synthetic timeout')
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out'
            with self.assertRaises(TimeoutError):fetch_control(control,out,open_response=response)
            self.assertIs(read_json(out/'failure.json')['automatic_retry'],False)
            with self.assertRaises(FileExistsError):fetch_control(control,out,open_response=response)
            self.assertEqual(1,len(calls))

    def test_truncated_content_length_leaves_partial_original_and_failure(self):
        body=b'%PDF-1.7 short';control=self.helper.control(body)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out'
            with self.assertRaises(ContractError):fetch_control(control,out,open_response=lambda request:
                fixture.FakeResponse(body,headers={'Content-Length':str(len(body)+1)}))
            self.assertEqual(body,(out/'body.partial').read_bytes())
            self.assertFalse((out/'receipt.json').exists())

    def test_elapsed_budget_fails_durably_before_reading_body(self):
        body=b'%PDF-1.7 test';control=self.helper.control(body)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out'
            with patch('tools.science.source_retrieval.time.monotonic',side_effect=[0,121]):
                with self.assertRaisesRegex(ContractError,'elapsed budget'):
                    fetch_control(control,out,open_response=lambda request:fixture.FakeResponse(body))
            self.assertEqual('build_failed',read_chain(out/'journal.jsonl')[-1]['event'])
            self.assertFalse((out/'receipt.json').exists())


if __name__=='__main__':unittest.main()
