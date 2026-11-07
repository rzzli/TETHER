import copy
import unittest
import tempfile
from pathlib import Path

from tether_engine.serde import ContractError
from tools.science.t6_reference import validate_review, seal_references
from tools.science.run_comparison import pin
from tether_engine.serde import write_json


class T6ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.tasks = {'tasks': [{'task_id': 't', 'offered_candidate_ids': ['a', 'b']}]}
        self.review = {'schema_version': 1, 'reviewer_id': 'A', 'tasks': [{
            'task_id': 't', 'candidates': [{'observation_id': identity,
            'relevance': 'indirect', 'applicability': 'uncertain', 'uncertainty': 'high',
            'reason': 'Source gives an association without intervention context.'} for identity in ('a', 'b')],
            'admissible_best_ids': ['a', 'b'], 'none_sufficient': False,
            'reference_uncertainty': 'high', 'reason': 'The source does not distinguish the two.'}]}

    def test_tied_and_none_answers_are_allowed(self):
        validate_review(self.review, self.tasks)
        self.review['tasks'][0].update(admissible_best_ids=[], none_sufficient=True)
        validate_review(self.review, self.tasks)

    def test_missing_duplicate_foreign_and_reordered_candidates_fail(self):
        for ids in (['a'], ['a', 'a'], ['a', 'foreign'], ['b', 'a']):
            with self.subTest(ids=ids):
                value = copy.deepcopy(self.review)
                value['tasks'][0]['candidates'] = [dict(value['tasks'][0]['candidates'][0], observation_id=i) for i in ids]
                with self.assertRaises(ContractError):
                    validate_review(value, self.tasks)

    def test_contradictory_none_foreign_best_and_empty_reasons_fail(self):
        for update in ({'none_sufficient': True}, {'admissible_best_ids': ['foreign']}, {'reason': ''}):
            value = copy.deepcopy(self.review)
            value['tasks'][0].update(update)
            with self.assertRaises(ContractError):
                validate_review(value, self.tasks)

    def test_missing_task_and_invalid_rating_fail(self):
        value = copy.deepcopy(self.review)
        value['tasks'] = []
        with self.assertRaises(ContractError):
            validate_review(value, self.tasks)
        self.review['tasks'][0]['candidates'][0]['applicability'] = 'proven therapeutic benefit'
        with self.assertRaises(ContractError):
            validate_review(self.review, self.tasks)

    def test_seal_binds_tasks_reviews_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_json(root/'tasks.json', self.tasks)
            task_pin = pin(root/'tasks.json')
            reviews = []
            for name in ('A', 'B'):
                review = copy.deepcopy(self.review)
                review.update(reviewer_id=name, task_manifest=task_pin)
                write_json(root/(name+'.json'), review)
                reviews.append(pin(root/(name+'.json')))
            adjudication = copy.deepcopy(self.review)
            adjudication.update(reviewer_id='C', task_manifest=task_pin, reviews=reviews)
            write_json(root/'C.json', adjudication)
            target = root/'freeze.json'
            original = seal_references(task_pin, reviews, pin(root/'C.json'), target)
            with self.assertRaises(FileExistsError):
                seal_references(task_pin, reviews, pin(root/'C.json'), target)
            self.assertEqual(pin(target), original)
            adjudication['reviews'] = list(reversed(reviews))
            write_json(root/'C.json', adjudication)
            with self.assertRaises(ContractError):
                seal_references(task_pin, reviews, pin(root/'C.json'), root/'bad.json')
