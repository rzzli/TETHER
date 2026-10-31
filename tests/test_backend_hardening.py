"""Adapter boundary regressions: entirely fake transport, no model execution."""
from dataclasses import replace
import io
import json
from pathlib import Path
import tempfile
import unittest
import urllib.error
from unittest.mock import Mock

from asof.agents import EvidenceView, SpecialistRequest
from asof.contracts import Category
from asof.local_model import LocalSelectionBackend, parse_selection, selection_payload
from asof.retrieval import RetrievalPolicy, bounded_request
from asof.wire import request_bytes
from asof.serde import ContractError, canonical, fingerprint, write_json


class BackendHardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.config = dict(schema_version=1,endpoint='http://127.0.0.1:55580',model_id='fixture',
            model_provenance=dict(weights_sha256={'fixture':'a'*64},runtime_sha256='b'*64),
            retrieval=dict(max_records=12,max_request_bytes=64000),max_output_tokens=256,
            timeout_seconds=2,seed=20261017)
        self.path=Path(self.temp.name)/'config.json';write_json(self.path,self.config)
        self.backend=LocalSelectionBackend(self.path)
        self.backend.opener=Mock()
        self.request=SpecialistRequest('{"action":"inhibit"}',Category.GENETICS,
            (EvidenceView('0','inhibit evidence','source','{}'),),'select IDs',())

    def test_url_and_http_errors_normalized_without_retry(self):
        errors=[urllib.error.URLError('connection refused'),
                urllib.error.HTTPError('http://127.0.0.1:55580/completion',503,'unavailable',{},None)]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                self.backend.opener.open.side_effect=error
                with self.assertRaises(ConnectionError):self.backend.select(self.request)
                self.assertEqual(self.backend.records[-1]['status'],'failed')
                self.assertEqual(self.backend.records[-1]['error_class'],type(error).__name__)
        self.assertEqual(self.backend.opener.open.call_count,2)

    def test_malformed_content_and_usage_raise_contract_error(self):
        valid=dict(content='{"observation_ids":[]}',truncated=False,tokens_evaluated=2,tokens_predicted=1)
        malformed=[None,[],{k:v for k,v in valid.items() if k!='content'},
                   *[{**valid,'content':v} for v in [None,1,{},[],b'{}']],
                   *[{**valid,'content':v} for v in ['null','1','[]','"text"']],
                   *[{k:v for k,v in valid.items() if k!=missing} for missing in ['tokens_evaluated','tokens_predicted']]]
        for response in malformed:
            with self.subTest(response=response),self.assertRaises(ContractError):parse_selection(response,['0'])

    def test_prepare_preflights_escaped_prompt_before_quote_or_dispatch(self):
        empty=replace(self.request,evidence=(replace(self.request.evidence[0],statement=''),))
        framing_only='x'*(16383-len(request_bytes(empty)))
        self.assertEqual(len(request_bytes(replace(empty,evidence=(replace(empty.evidence[0],statement=framing_only),)))),16383)
        for text in ['x'*17000,'<|'*2600,framing_only]:
            with self.subTest(escaped=text.startswith('<')):
                request=replace(self.request,evidence=(replace(self.request.evidence[0],statement=text),))
                bounded,_=bounded_request(request,RetrievalPolicy(12,64000))
                self.assertEqual(bounded.evidence,request.evidence)
                with self.assertRaisesRegex(ContractError,'prompt exceeds'):
                    self.backend.prepare_request(request)
        self.backend.opener.open.assert_not_called()
        self.assertEqual(self.backend.records,[])

    def test_small_request_large_policy_preserves_exact_payload_and_audit(self):
        RetrievalPolicy(12,64000).validate()
        expected,audit=bounded_request(self.request,self.backend.policy)
        payload=selection_payload(expected,256,20261017)
        prepared,actual=self.backend.prepare_request(self.request)
        self.assertEqual(prepared,expected);self.assertEqual(fingerprint(actual),fingerprint(audit))
        self.assertEqual(canonical(self.backend.payload_for(prepared)),canonical(payload))
        self.assertGreater(self.backend.quote(prepared).input_tokens,0)

    def test_malformed_response_is_retained_and_interruption_not_normalized(self):
        response=dict(truncated=False,tokens_evaluated=2,tokens_predicted=1)
        self.backend.opener.open.return_value=io.BytesIO(canonical(response))
        with self.assertRaises(ContractError):self.backend.select(self.request)
        self.assertEqual(self.backend.records[-1]['response'],response)
        self.assertEqual(self.backend.records[-1]['response_sha256'],fingerprint(response))
        self.assertNotIn('measured_usage',self.backend.records[-1])
        self.backend.opener.open.side_effect=KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):self.backend.select(self.request)
        self.assertEqual(self.backend.records[-1]['error_class'],'KeyboardInterrupt')

    def test_timeout_remains_timeout_and_reservation_is_not_measured(self):
        self.backend.opener.open.side_effect=TimeoutError('fixture')
        with self.assertRaises(TimeoutError):self.backend.select(self.request)
        self.assertEqual(self.backend.records[-1]['status'],'timeout')
        self.assertNotIn('measured_usage',self.backend.records[-1])
        self.backend.opener.open.assert_called_once()


if __name__=='__main__':unittest.main()
