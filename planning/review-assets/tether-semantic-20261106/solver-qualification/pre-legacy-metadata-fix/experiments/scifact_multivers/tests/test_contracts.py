"""Fictional contracts; no SciFact annotations or model dependencies."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from experiments.scifact_multivers.contracts import (
    ContractError, capture_asset_bytes, native_predictions, prepare_entries, require_complete_pairs,
)
from experiments.scifact_multivers.data import tensorize_pair
from experiments.scifact_multivers.runtime import receipt_assets
from experiments.scifact_multivers.inference import record_pair_failure


class Tokenized(dict):
    @property
    def input_ids(self):
        return self['input_ids']


class FictionalTokenizer:
    eos_token = '</s>'
    eos_token_id = 2
    bos_token_id = 0
    pad_token_id = 1
    model_max_length = 4096

    def __call__(self, text):
        # Every whitespace-delimited fictional word is one token; preserve EOS.
        pieces = text.replace('</s>', ' </s> ').split()
        ids = [0] + [2 if p == '</s>' else 7 for p in pieces] + [2]
        return Tokenized(input_ids=ids, attention_mask=[1] * len(ids))


class ContractTests(unittest.TestCase):
    def test_claim_title_sentences_global_mask_and_offsets(self):
        row = tensorize_pair(FictionalTokenizer(), 'Alpha signal rises.',
                             ['Control is stable.', 'Signal fell.'], title='Fictional study')
        self.assertEqual(row['abstract_sent_idx'], [11, 14])
        ids = row['tokenized']['input_ids']
        self.assertEqual(len(ids), 15)
        self.assertEqual(row['tokenized']['global_attention_mask'],
                         [1, 1, 1, 1, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1])

    def test_none_title_and_empty_title_are_distinct(self):
        tok = FictionalTokenizer()
        a = tensorize_pair(tok, 'Claim.', ['Sentence.'], title=None)
        b = tensorize_pair(tok, 'Claim.', ['Sentence.'], title='')
        self.assertEqual(a['abstract_sent_idx'], [4])
        self.assertEqual(b['abstract_sent_idx'], [5])

    def test_overflow_rejected_without_truncation(self):
        with self.assertRaisesRegex(ContractError, '4096'):
            tensorize_pair(FictionalTokenizer(), 'claim', [' '.join(['word'] * 4095)], title=None)

    def test_literal_separator_in_sentence_cannot_shift_evidence_offsets(self):
        with self.assertRaises(ContractError):
            tensorize_pair(FictionalTokenizer(), 'claim', ['one </s> two'], title='title')

    def test_entries_preserve_order_and_exact_text(self):
        claims = [{'id': 7, 'claim': ' α study? ', 'doc_ids': [20, 10]}]
        corpus = [{'doc_id': 10, 'title': 'X', 'abstract': ['first']},
                  {'doc_id': 20, 'title': 'Y', 'abstract': ['line one\nline two', 'second']}]
        entries = prepare_entries(claims, corpus)
        self.assertEqual([e['abstract_id'] for e in entries], [20, 10])
        self.assertEqual(entries[0]['claim'], ' α study? ')
        self.assertEqual(entries[0]['sentences'][0], 'line one\nline two')

    def test_annotation_bearing_claims_are_rejected(self):
        with self.assertRaises(ContractError):
            prepare_entries([{'id': 7, 'claim': 'fictional', 'doc_ids': [], 'evidence': {}}], [])

    def test_duplicate_claim_doc_and_missing_document_are_rejected(self):
        doc = {'doc_id': 10, 'title': 'X', 'abstract': ['sentence']}
        for claims, corpus in [
            ([{'id': 1, 'claim': 'x', 'doc_ids': [10, 10]}], [doc]),
            ([{'id': 1, 'claim': 'x', 'doc_ids': [20]}], [doc]),
            ([{'id': 1, 'claim': 'x', 'doc_ids': []}] * 2, [doc]),
            ([{'id': 1, 'claim': 'x', 'doc_ids': []}], [doc, doc]),
        ]:
            with self.subTest(claims=claims, corpus=corpus), self.assertRaises(ContractError):
                prepare_entries(claims, corpus)

    def test_native_nei_omission_preserves_all_claims_and_empty_rationale(self):
        rows = [{'claim_id': 1, 'abstract_id': 3, 'predicted_label': 'NEI', 'predicted_rationale': [0]},
                {'claim_id': 2, 'abstract_id': 4, 'predicted_label': 'SUPPORT', 'predicted_rationale': []}]
        self.assertEqual(native_predictions([1, 2, 3], rows),
                         [{'id': 1, 'evidence': {}}, {'id': 2, 'evidence': {'4': {'label': 'SUPPORT', 'sentences': []}}},
                          {'id': 3, 'evidence': {}}])

    def test_duplicate_pair_or_unknown_claim_cannot_overwrite_predictions(self):
        row = {'claim_id': 1, 'abstract_id': 3, 'predicted_label': 'SUPPORT', 'predicted_rationale': [0]}
        for ids, rows in [([1], [row, row]), ([2], [row])]:
            with self.assertRaises(ContractError):
                native_predictions(ids, rows)

    def test_missing_pair_cannot_be_converted_into_nei(self):
        entries=[{'claim_id':1,'abstract_id':10,'sentences':['fictional']}]
        with self.assertRaisesRegex(ContractError,'lost'):
            require_complete_pairs(entries,[])
        with self.assertRaisesRegex(ContractError,'escapes'):
            require_complete_pairs(entries,[{'claim_id':1,'abstract_id':10,'predicted_rationale':[1]}])

    def test_failed_pair_is_journaled_and_exception_propagates(self):
        events=[]
        with self.assertRaisesRegex(ContractError,'fictional failed computation'):
            with record_pair_failure(lambda **row: events.append(row), {'claim_id':1,'abstract_id':10}):
                raise ContractError('fictional failed computation')
        self.assertEqual(events[0]['event'],'pair_failed')
        self.assertEqual(events[0]['status'],'failed')
        self.assertEqual(events[0]['claim_id'],1)

    def test_capture_verifies_consumed_bytes_and_declared_files_only(self):
        scratch = Path(__file__).resolve().parents[3] / 'planning/review-assets/tether-semantic-20261106/solver-feasibility/test-temp'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as name:
            root = Path(name); raw = b'fictional config'
            (root/'config.json').write_bytes(raw)
            expected = {'config.json': {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}}
            captured = capture_asset_bytes(root, expected)
            (root/'config.json').write_bytes(b'tampered')
            self.assertEqual(captured['config.json'], raw)
            with self.assertRaises(ContractError):
                capture_asset_bytes(root, expected)
            with self.assertRaises(ContractError):
                capture_asset_bytes(root, {'../escape': {'bytes': 0, 'sha256': '0'*64}})

    def test_actual_transport_pass_schema_and_incomplete_row_rejection(self):
        scratch = Path(__file__).resolve().parents[3] / 'planning/review-assets/tether-semantic-20261106/solver-feasibility/test-temp'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as name:
            root=Path(name).resolve(); (root/'tokenizer').mkdir()
            rows=[]
            for logical in ('config.json','vocab.json','merges.txt','tokenizer.json'):
                raw=b'fictional'; path=root/'tokenizer'/logical; path.write_bytes(raw)
                rows.append(dict(kind='tokenizer_config',logical_id=logical,relative_path='tokenizer/'+logical,
                                 path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),status='completed',
                                 http_repo_commit='b190dd42e462d2dee634d1162c839710079f97ab'))
            rows.append(dict(kind='checkpoint',logical_id='fever_sci.ckpt',relative_path='checkpoint/fever_sci.ckpt',
                             path=str(root/'checkpoint/fever_sci.ckpt'),bytes=5253768950,sha256='a'*64,status='completed',
                             http_version_id='GYe58tFsyvvn1n7rib5H4wrsiq32ZY5Y'))
            receipt={'status':'PASS','files':rows}
            def write():
                raw=json.dumps(receipt).encode(); (root/'RECEIPT.json').write_bytes(raw)
                return hashlib.sha256(raw).hexdigest()
            captured,checkpoint,_=receipt_assets(root,write())
            self.assertEqual(len(captured),4)
            self.assertEqual(checkpoint['sha256'],'a'*64)
            receipt['files'][0]['status']='started'
            with self.assertRaisesRegex(ContractError,'incomplete'):
                receipt_assets(root,write())


if __name__ == '__main__':
    unittest.main()
