"""Exact-token authority for recorded and explicitly owned-native cells.

This policy never generates text or tokenizes.

An installed trusted caller supplies this object and external quote anchors. JSON
names cannot select it. Locations are capabilities and are omitted from portable
descriptors; the anchored quote and current package establish their identities.
"""
from dataclasses import dataclass
from collections.abc import Mapping
import hashlib
import math
from pathlib import Path
import re
import time

from asof.agents import Usage
from asof.serde import canonical, encode, fingerprint, freeze
from . import tokenization
from .recorded import RecordedBackend, _document
from .session import BackendCapabilities, GeneratedBytes, _identity, _usage, need
from .stable_read import deadline_check


@dataclass(frozen=True)
class TrustedTokenCapacity:
    path: Path
    receipt_sha256: str
    prompt_sha256: str
    spec_sha256: str
    payload_sha256: str

    def __post_init__(self):
        object.__setattr__(self, 'path', Path(self.path).absolute())
        for name in ('receipt_sha256','prompt_sha256','spec_sha256','payload_sha256'):
            value = getattr(self,name)
            need(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value),
                 'External token-capacity anchor required')

    def describe(self):
        return freeze(dict(schema_version=1,kind='trusted_offline_token_capacity',
            implementation=_identity(TrustedTokenCapacity),
            receipt_sha256=self.receipt_sha256,prompt_sha256=self.prompt_sha256,
            spec_sha256=self.spec_sha256,payload_sha256=self.payload_sha256,
            margin=32,usage_basis='reservation_not_model_usage'))

    def _authenticated_quote(self, request, payload, caps, *, deadline):
        deadline_check(deadline)
        need(isinstance(caps,BackendCapabilities),'Missing token capacity capabilities')
        caps.validate()
        need(caps.tokenizer_identity == self.spec_sha256,
             'Configured tokenizer identity differs')
        prompt=payload.get('prompt')
        need(isinstance(prompt,str) and hashlib.sha256(prompt.encode('utf-8')).hexdigest() == self.prompt_sha256
             and fingerprint(payload) == self.payload_sha256,'Token prompt/payload anchor differs')
        quote=tokenization.verify_tokenization(self.path,self.receipt_sha256,
            self.prompt_sha256,self.spec_sha256,expected_payload_sha256=self.payload_sha256,
            deadline=deadline)
        deadline_check(deadline)
        need(quote['input_reservation'] == quote['token_count']+32,
             'Exact token reservation differs')
        return quote

    def reservation(self, request, payload, caps, *, deadline):
        """Internal adapter seam: authenticate before an allocated budget is known."""
        quote=self._authenticated_quote(request,payload,caps,deadline=deadline)
        result=Usage(quote['input_reservation'],payload.get('n_predict'),0.0)
        return _usage(result)

    def verify(self, request, payload, caps, quote, budget, *, deadline):
        proof=self._authenticated_quote(request,payload,caps,deadline=deadline)
        budget.validate()
        quote=_usage(quote)
        need(len(payload['prompt'].encode('utf-8')) <= caps.max_prompt_bytes,
             'Prompt exceeds capability')
        need(len(canonical(payload)) <= caps.max_payload_bytes,'Payload exceeds capability')
        output=payload.get('n_predict')
        need(type(output) is int and 0 < output <= caps.max_output_tokens,'Output exceeds capability')
        need(quote.input_tokens == proof['input_reservation'] and quote.output_tokens == output,
             'Quote differs from exact authenticated token reservation')
        need(quote.input_tokens+quote.output_tokens <= caps.context_tokens,'Quote/context mismatch')
        need(quote.cost_usd == budget.max_cost_usd == 0 and budget.max_calls >= 1
             and quote.input_tokens <= budget.max_input_tokens
             and quote.output_tokens <= budget.max_output_tokens,'Cell exceeds budget')
        deadline_check(deadline)
        return freeze(dict(schema_version=1,kind='verified_exact_token_capacity',
            request_sha256=fingerprint(request),payload_sha256=fingerprint(payload),
            descriptor_sha256=fingerprint(self.describe()),quote_sha256=fingerprint(proof),
            token_count=proof['token_count'],margin=32,reservation=encode(quote),
            context_tokens=caps.context_tokens,tokenizer_identity=caps.tokenizer_identity))


def require_policy(policy):
    # This is deliberately one concrete optional authority, not a plugin loader.
    need(type(policy) is TrustedTokenCapacity,'Explicit trusted token-capacity object required')
    return policy


def _capabilities(interface, spec_sha256):
    return BackendCapabilities(interface_version=interface,max_prompt_bytes=32768,
        max_output_tokens=1024,tokenizer_identity=spec_sha256)


class TokenQuotedRecordedBackend(RecordedBackend):
    """One evaluator fixture consumption under exact token and absolute time bounds."""
    def __init__(self, document, *, capacity_policy, case_deadline, interface):
        self.capacity_policy=require_policy(capacity_policy)
        deadline_check(case_deadline)
        self.case_deadline=case_deadline
        super().__init__(document,interface=interface,backend_id='token-quoted-recorded-fixture-v1')
        self.capabilities=_capabilities(interface,capacity_policy.spec_sha256)
        self.provenance=freeze(dict(kind='token_quoted_recorded_study_fixture',document=encode(document),
            parent_case_end_monotonic=case_deadline,capacity_policy=encode(capacity_policy.describe())))

    def quote(self, request, payload):
        return self._quote_before(request,payload,self.case_deadline)

    def _quote_before(self, request, payload, deadline):
        need(not self.used,'Fixture already consumed')
        deadline_check(deadline)
        _,usage=_document(self.provenance['document'],request,payload)
        quote=self.capacity_policy.reservation(request,payload,self.capabilities,deadline=deadline)
        need(usage.input_tokens <= quote.input_tokens and usage.output_tokens <= quote.output_tokens,
             'Fixture exceeds exact token quote')
        deadline_check(deadline)
        return quote

    def generate(self, request, payload, *, timeout_seconds):
        need(type(timeout_seconds) in (int,float) and math.isfinite(timeout_seconds) and timeout_seconds > 0,
             'No fixture time remains')
        deadline=min(self.case_deadline,time.monotonic()+timeout_seconds)
        self._quote_before(request,payload,deadline)
        doc,usage=_document(self.provenance['document'],request,payload)
        # Check after all fallible quote/document work, immediately before use.
        deadline_check(deadline)
        self.used=True
        if doc['outcome'] == 'timeout':
            raise TimeoutError('Recorded timeout fixture; no model call')
        return GeneratedBytes(doc['content_utf8'].encode('utf-8'),usage)


def verify_recorded_execution(request,payload,content,configuration,usage,*,
                              capacity_policy,case_deadline,interface):
    """Reusable fixture binding for explicitly supplied source-aware verifiers."""
    policy=require_policy(capacity_policy)
    binding=configuration.get('capacity_binding')
    need(type(configuration.get('schema_version')) is int and configuration['schema_version']==2
         and canonical(configuration.get('capacity_policy')) == canonical(policy.describe())
         and isinstance(binding,Mapping)
         and binding.get('request_sha256') == fingerprint(request)
         and binding.get('payload_sha256') == fingerprint(payload)
         and binding.get('descriptor_sha256') == fingerprint(policy.describe()),
         'Token recorded execution requires its version-two capacity binding')
    need(encode(configuration['adapter_code']) == _identity(TokenQuotedRecordedBackend),
         'Token recorded adapter identity differs')
    provenance=configuration['adapter_provenance']
    need(set(provenance) == {'kind','document','parent_case_end_monotonic','capacity_policy'}
         and provenance['kind'] == 'token_quoted_recorded_study_fixture'
         and provenance['parent_case_end_monotonic'] == case_deadline
         and canonical(provenance['capacity_policy']) == canonical(policy.describe()),
         'Token recorded provenance differs')
    doc,expected_usage=_document(provenance['document'],request,payload)
    need(doc['outcome'] == 'return' and doc['content_utf8'].encode('utf-8') == content
         and usage == expected_usage,'Token recorded response/fixture usage differs')
    need(canonical(configuration['backend_capabilities']) == canonical(_capabilities(interface,policy.spec_sha256)),
         'Token recorded capabilities differ')
