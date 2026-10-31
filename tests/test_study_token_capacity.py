"""Exact token-proof admission preserves default byte semantics; no real children."""
import hashlib
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from asof.agents import Usage
from asof.serde import ContractError, canonical, encode, fingerprint, parse_json
from asof.study import tokenization as tok
from asof.study.__main__ import fixture
from asof.study.diagnostic import REQUIRED_RESOURCES, load_synthetic_request, prepare_payload
from asof.study.recorded import RecordedVerifier
from asof.study.session import StudySession, _capacity, verify_study
from asof.study.token_capacity import (
    TrustedTokenCapacity, TokenQuotedRecordedBackend, verify_recorded_execution,
)
from asof.workflow import Budget
from tests import test_study_tokenization as helpers


class CapacityVerifier(RecordedVerifier):
    def __init__(self, policy, deadline):
        super().__init__()
        self.policy, self.deadline = policy, deadline

    def validate_payload(self, request, payload):
        expected=encode(prepare_payload(request,'simplified'))
        expected['n_predict']=1024
        if canonical(expected) != canonical(payload):
            raise ContractError('Test payload differs')

    def verify_execution(self, request, payload, content, configuration, usage):
        verify_recorded_execution(request, payload, content, configuration, usage,
            capacity_policy=self.policy, case_deadline=self.deadline, interface=self.interface)


class TokenCapacityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        helpers.TokenizationArtifactTests.setUpClass()

    @classmethod
    def tearDownClass(cls):
        helpers.TokenizationArtifactTests.tearDownClass()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=helpers.TEMP_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.request = load_synthetic_request('synthetic-orientation')
        self.payload = encode(prepare_payload(self.request, 'simplified'))
        self.payload['n_predict']=1024
        spec = helpers.TokenizationArtifactTests.spec
        real_run = tok._run_child
        with patch.object(tok, '_run_child', side_effect=lambda *args: real_run(*args, process_factory=helpers.FakeChild)):
            quote = tok.tokenize_prompt(self.payload['prompt'], spec, time.monotonic()+60,
                self.root/'quote', payload_sha256=fingerprint(self.payload))
        self.policy = TrustedTokenCapacity(self.root/'quote', quote['receipt_sha256'],
            hashlib.sha256(self.payload['prompt'].encode()).hexdigest(), fingerprint(spec), fingerprint(self.payload))
        self.deadline = time.monotonic()+60
        doc = fixture(self.request,self.payload)
        doc['usage'] = encode(Usage(7,2,0.0))
        self.backend = TokenQuotedRecordedBackend(doc,capacity_policy=self.policy,
            case_deadline=self.deadline,interface='simplified')
        self.verifier = CapacityVerifier(self.policy,self.deadline)

    def session(self, name='cell', **kw):
        return StudySession(self.root/name, resources={n:'study/'+n for n in REQUIRED_RESOURCES},
            required_resources=REQUIRED_RESOURCES, **kw)

    def test_exact_quote_admitted_only_with_explicit_policy_and_replay_deadline(self):
        quote = self.backend.quote(self.request,self.payload)
        self.assertEqual(quote.input_tokens,35)
        with self.assertRaises(ContractError):
            _capacity(self.payload,self.backend.capabilities,quote,Budget())
        with self.session(capacity_policy=self.policy) as cell:
            cell.call_once(request=self.request,payload=self.payload,backend=self.backend,verifier=self.verifier)
            cell.finish()
        anchor=hashlib.sha256((cell.output/'receipt.json').read_bytes()).hexdigest()
        with patch.object(tok.subprocess,'Popen',side_effect=AssertionError('No replay child')):
            self.assertEqual(verify_study(cell.output,expected_receipt_sha256=anchor,
                verifier=self.verifier,capacity_policy=self.policy,deadline=time.monotonic()+60)['status'],'verified_study_cell')
        for kw in ({},{'capacity_policy':self.policy}):
            with self.subTest(kw=tuple(kw)), self.assertRaises(ContractError):
                verify_study(cell.output,expected_receipt_sha256=anchor,verifier=self.verifier,**kw)

    def test_expired_quote_has_zero_dispatch_and_retains_request(self):
        expired = time.monotonic()-1
        with patch.object(tok,'verify_tokenization',side_effect=TimeoutError('fixture expired')):
            with self.assertRaises(TimeoutError), self.session(capacity_policy=self.policy) as cell:
                cell.call_once(request=self.request,payload=self.payload,backend=self.backend,verifier=self.verifier)
        self.assertFalse(self.backend.used)
        self.assertTrue((cell.output/'request.json').is_file())
        self.assertFalse((cell.output/'receipt.json').exists())
        self.assertFalse((cell.output/'configuration.json').exists())
        with self.assertRaises(TimeoutError):
            tok.verify_tokenization(self.policy.path,self.policy.receipt_sha256,
                self.policy.prompt_sha256,self.policy.spec_sha256,
                expected_payload_sha256=self.policy.payload_sha256,deadline=expired)

    def test_count_and_output_reservations_must_be_exact(self):
        for quote in (Usage(34,1024,0.0),Usage(36,1024,0.0),Usage(35,1025,0.0)):
            with self.subTest(quote=quote),self.assertRaises(ContractError):
                self.policy.verify(self.request,self.payload,self.backend.capabilities,quote,Budget(),deadline=self.deadline)

    def test_limits_remain_enforced_with_a_valid_token_proof(self):
        quote=self.backend.quote(self.request,self.payload)
        for caps,budget in ((replace(self.backend.capabilities,max_prompt_bytes=1),Budget()),
                (replace(self.backend.capabilities,max_payload_bytes=1),Budget()),
                (replace(self.backend.capabilities,context_tokens=1000),Budget()),
                (replace(self.backend.capabilities,max_output_tokens=1),Budget()),
                (self.backend.capabilities,replace(Budget(),max_input_tokens=34)),
                (self.backend.capabilities,replace(Budget(),max_output_tokens=1023))):
            with self.subTest(caps=caps,budget=budget),self.assertRaises(ContractError):
                self.policy.verify(self.request,self.payload,caps,quote,budget,deadline=self.deadline)

    def test_wrong_payload_prompt_or_tokenizer_fails_before_quote_read(self):
        payload=encode(self.payload)
        payload['seed']=43
        for policy,selected,caps in ((self.policy,payload,self.backend.capabilities),
                (replace(self.policy,prompt_sha256='0'*64),self.payload,self.backend.capabilities),
                (self.policy,self.payload,replace(self.backend.capabilities,tokenizer_identity='0'*64))):
            with self.subTest(policy=policy),patch.object(tok,'verify_tokenization',side_effect=AssertionError('No quote read')):
                with self.assertRaises(ContractError):
                    policy.reservation(self.request,selected,caps,deadline=self.deadline)

    def test_external_receipt_and_spec_anchors_are_independent(self):
        for policy in (replace(self.policy,receipt_sha256='0'*64),replace(self.policy,spec_sha256='0'*64)):
            caps=replace(self.backend.capabilities,tokenizer_identity=policy.spec_sha256)
            with self.subTest(policy=policy),self.assertRaises(ContractError):
                policy.reservation(self.request,self.payload,caps,deadline=self.deadline)

    def test_policy_and_descriptor_are_immutable_and_locator_independent(self):
        with self.assertRaises(FrozenInstanceError):
            self.policy.receipt_sha256='0'*64
        with self.assertRaises(TypeError):
            self.policy.describe()['implementation']['file']['sha256']='0'*64
        moved=replace(self.policy,path=self.root/'other-location')
        self.assertEqual(self.policy.describe(),moved.describe())

    def test_recorded_consumption_cannot_repeat(self):
        self.backend.generate(self.request,self.payload,timeout_seconds=10)
        with self.assertRaises(ContractError):
            self.backend.generate(self.request,self.payload,timeout_seconds=10)

    def test_token_adapter_cannot_be_verified_as_a_legacy_configuration(self):
        with self.session(capacity_policy=self.policy) as cell:
            cell.call_once(request=self.request,payload=self.payload,backend=self.backend,verifier=self.verifier)
            cell.finish()
        config=parse_json((cell.output/'configuration.json').read_bytes())
        config['schema_version']=1
        config.pop('capacity_policy')
        config.pop('capacity_binding')
        with self.assertRaises(ContractError):
            self.verifier.verify_execution(self.request,self.payload,
                (cell.output/'raw-response.bin').read_bytes(),config,Usage(7,2,0.0))
