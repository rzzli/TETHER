import unittest

from asof.serde import encode
from experiments.labbench.data_views import project_rows
from experiments.litqa_analysis.inputs import projection, graph_groups
from experiments.litqa_analysis.native_records import canonical


class InputTests(unittest.TestCase):
    def rows(self):
        return [dict(id=f'00000000-0000-0000-0000-{i:012d}',question='Invented?',ideal='Right',
            distractors=['Wrong','Wrong'],sources=['https://doi.org/10.1234/a'],canary='invented',tag='fixture',version='v1') for i in range(3)]

    def test_native_projection_agreement_preserves_duplicate_distractors(self):
        raw=b'\n'.join(canonical(r) for r in self.rows())+b'\n'
        got=projection(raw);native=encode(project_rows(raw,expected_count=3))
        self.assertEqual(got['queries'],native['queries']);self.assertEqual(got['references'],native['references'])
        self.assertEqual(got['doi_schedule'],['10.1234/a'])

    def test_bad_source_and_duplicate_id_fail(self):
        for kind in ('source','id','key'):
            rows=self.rows()
            if kind=='source':rows[0]['sources']=['https://example.invalid/10.1234/a']
            if kind=='id':rows[1]['id']=rows[0]['id']
            if kind=='key':rows[0]['distractors'].append(rows[0]['ideal'])
            with self.assertRaises(ValueError):projection(b'\n'.join(canonical(r) for r in rows))

    def test_graph_transitive_shared_source_components(self):
        hints=[dict(id='a',dois=['d1']),dict(id='b',dois=['d1','d2']),dict(id='c',dois=['d2']),dict(id='d',dois=['d3'])]
        self.assertEqual(graph_groups(['a','b','c','d'],hints),[['a','b','c'],['d']])


if __name__=='__main__':unittest.main()
