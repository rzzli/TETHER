"""Validate the exposed A04 development inputs against independent references."""

from collections import Counter
import hashlib
from pathlib import Path
import unittest

from tether_engine.serde import parse_json


FIXTURES = Path(__file__).resolve().parent / 'fixtures' / 'retrieval-development'
UNRESOLVED = 'Unresolved in the supplied records'


def digest(payload):
    return hashlib.sha256(payload).hexdigest()


class RetrievalDevelopmentFixtureTests(unittest.TestCase):
    def rows(self, name, purpose, field, keys, identity):
        document = parse_json((FIXTURES / name).read_bytes())
        self.assertEqual(set(document), {'schema_version', 'purpose', field})
        self.assertEqual(document['schema_version'], 1)
        self.assertEqual(document['purpose'], purpose)
        rows = {}
        for row in document[field]:
            self.assertEqual(set(row), keys)
            self.assertNotIn(row[identity], rows)
            rows[row[identity]] = row
        return rows

    def setUp(self):
        self.corpus = self.rows('corpus.json', 'retrieval_input', 'documents',
                                {'document_id', 'body', 'body_sha256'}, 'document_id')
        self.questions = self.rows('queries.json', 'retrieval_input', 'questions',
                                   {'case_id', 'question', 'candidate_ids'}, 'case_id')
        self.options = self.rows('options.json', 'answer_input', 'items',
                                 {'case_id', 'options'}, 'case_id')
        self.reference = self.rows('reference.json', 'evaluation_only', 'items',
                                   {'case_id', 'family', 'answer_option_id', 'relevant_spans'}, 'case_id')

    def test_question_and_document_universes_are_complete_and_bounded(self):
        self.assertEqual(len(self.corpus), 48)
        self.assertEqual(set(self.questions), {f'dev-{i:02}' for i in range(1, 31)})
        self.assertEqual(self.questions.keys(), self.reference.keys())
        self.assertEqual(self.questions.keys(), self.options.keys())
        candidates = set()
        for question in self.questions.values():
            candidate_ids = question['candidate_ids']
            self.assertEqual(len(candidate_ids), len(set(candidate_ids)))
            self.assertLessEqual(len(candidate_ids), 12)
            self.assertTrue(question['question'].strip())
            candidates.update(candidate_ids)
        self.assertEqual(candidates, set(self.corpus))
        for key, row in self.corpus.items():
            self.assertRegex(key, r'^doc-[a-f0-9]{16}$')
            body = row['body'].encode('utf-8')
            self.assertTrue(body.strip())
            self.assertEqual(digest(body), row['body_sha256'])

    def test_query_and_answer_inputs_do_not_carry_reference_fields(self):
        for case_id, row in self.options.items():
            with self.subTest(case_id=case_id):
                self.assertEqual([option['option_id'] for option in row['options']], list('ABCD'))
                texts = set()
                for option in row['options']:
                    self.assertEqual(set(option), {'option_id', 'text'})
                    self.assertTrue(option['text'].strip())
                    texts.add(option['text'])
                self.assertEqual(len(texts), 4)
                self.assertIn(UNRESOLVED, texts)
                self.assertTrue(all(text.casefold() not in self.questions[case_id]['question'].casefold()
                                    for text in texts))

    def test_reference_spans_are_literal_utf8_slices_in_the_candidate_universe(self):
        multibyte = 0
        for case_id, row in self.reference.items():
            for span in row['relevant_spans']:
                self.assertEqual(set(span), {'document_id', 'body_sha256', 'start_byte', 'end_byte', 'quote'})
                key = span['document_id']
                self.assertIn(key, self.questions[case_id]['candidate_ids'])
                doc = self.corpus[key]
                self.assertEqual(doc['body_sha256'], span['body_sha256'])
                body = doc['body'].encode('utf-8')
                start, end = span['start_byte'], span['end_byte']
                self.assertEqual((type(start), type(end)), (int, int))
                self.assertTrue(0 <= start < end <= len(body))
                self.assertEqual(body[start:end].decode('utf-8'), span['quote'])
                multibyte += int(len(body[:start].decode('utf-8')) < start)
        self.assertEqual(multibyte, 6)

    def test_reference_preserves_all_five_conditions(self):
        expected = {'numeric_identifier': 1, 'unicode_identifier': 1, 'full_body': 1,
                    'two_documents': 2, 'no_relevant_passage': 0}
        counts = Counter()
        empty_slices = 0
        answers = set()
        for case_id, row in self.reference.items():
            with self.subTest(case_id=case_id):
                family = row['family']
                counts[family] += 1
                spans = row['relevant_spans']
                self.assertEqual(len(spans), expected[family])
                self.assertEqual(len({span['document_id'] for span in spans}), len(spans))
                options = {choice['option_id']: choice['text'] for choice in self.options[case_id]['options']}
                answer = options[row['answer_option_id']]
                answers.add(row['answer_option_id'])
                self.assertEqual(answer == UNRESOLVED, not spans)
                if family == 'two_documents':
                    values = [span['quote'].rsplit(' ', 1)[-1].rstrip('.') for span in spans]
                    self.assertEqual(answer, ' then '.join(values))
                elif spans:
                    self.assertIn(answer, spans[0]['quote'])
                empty_slices += int(not self.questions[case_id]['candidate_ids'])
        self.assertEqual(counts, dict.fromkeys(expected, 6))
        self.assertEqual(answers, set('ABCD'))
        self.assertEqual(empty_slices, 1)
