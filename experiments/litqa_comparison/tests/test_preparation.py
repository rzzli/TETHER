import unittest
import tempfile
from pathlib import Path
from tether_engine.serde import canonical,freeze,encode
from experiments.litqa_comparison.preparation import project,load_product
from experiments.litqa_comparison.codecs import digest


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.q=dict(id='00000000-0000-0000-0000-000000000001',question='Which fictional color?',
                    choices=['(A) Blue','(B) Insufficient information to answer the question','(C) Red'])

    def test_choices_absent_from_expansion_product(self):
        result=project([self.q],expected_count=1)
        self.assertEqual(set(result['source_queries'][0]),{'id','question'})
        self.assertEqual(result['answer_queries'][0]['choices'],tuple(self.q['choices']))
        self.q['choices'][0]='modified'
        self.assertEqual(result['answer_queries'][0]['choices'][0],'(A) Blue')

    def test_hidden_fields_are_rejected_not_silently_forwarded(self):
        for key in ('answer','ideal','source','doi','key_passage'):
            with self.subTest(key=key),self.assertRaises(ValueError):
                project([dict(self.q,**{key:'CANARY'})],expected_count=1)

    def test_incomplete_or_duplicate_schedule_is_not_full_cohort(self):
        with self.assertRaises(ValueError):project([self.q])
        with self.assertRaises(ValueError):project([self.q,self.q],expected_count=2)

    def test_loader_accepts_frozen_and_json_schedule_without_weakening_roles(self):
        rows=[dict(self.q,id=f'00000000-0000-0000-0000-{i:012d}') for i in range(1,200)]
        projected=project(rows)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source.json';raw=canonical(projected['source_queries']);p.write_bytes(raw)
            manifest=freeze(dict(kind='sc04_task_products_v1',scheduled=199,schedule=projected['schedule'],
                                products=dict(source_queries=dict(path=str(p),bytes=len(raw),sha256=digest(raw),role='question_only_input'))))
            self.assertEqual(len(load_product(manifest,'source_queries')),199)
            self.assertEqual(load_product(manifest,'source_queries'),load_product(encode(manifest),'source_queries'))
            changed=encode(manifest);changed['products']['source_queries']['role']='evaluation_only'
            with self.assertRaises(ValueError):load_product(changed,'source_queries')


if __name__=='__main__':unittest.main()
