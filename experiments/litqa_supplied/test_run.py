from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from experiments.litqa_supplied import run as r,qualification_fixtures as f


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def test_primary_gate_verifies_jsonl_bytes_without_parsing_as_json(self):
        root=self.root/'primary';root.mkdir()
        r.write(root/'COMPLETE.json',dict(purpose='production',status='primary_execution_complete',
            phases={name:dict(root=str(root/name),package_sha256=name) for name in r.controller.PHASES}))
        (root/'journal.jsonl').write_bytes(b'{"first":1}\n{"second":2}\n')
        r.write(root/'ROOT-RECEIPT.json',dict(frame_sha256='a'*64,files={p.name:r.primary.proof(p) for p in root.iterdir()}))
        frame=dict(purpose='production',primary_execution=dict(root=str(root),receipt=r.primary.proof(root/'ROOT-RECEIPT.json')))
        def verify(path,sha):return dict(phase=Path(path).name,frame_sha256='a'*64)
        with patch.object(r.controller,'verify_package',side_effect=verify):r.primary_gate(frame)
        (root/'journal.jsonl').write_bytes(b'changed')
        with self.assertRaises(ValueError):
            with patch.object(r.controller,'verify_package',side_effect=verify):r.primary_gate(frame)

    def test_fictional_scope_cannot_claim_primary_parent(self):
        r.primary_gate(dict(purpose='fictional_qualification',primary_execution=None))
        with self.assertRaises(ValueError):r.primary_gate(dict(purpose='fictional_qualification',primary_execution={'claimed':True}))

    def test_collection_loader_only_opens_doi_schedule(self):
        r.write(self.root/'dois.json',[f.DOI])
        frame=dict(unique_dois=1,products=dict(doi_schedule=r.primary.proof(self.root/'dois.json'),answer_queries={'path':'missing'},hints={'path':'missing'}))
        self.assertEqual(r.tasks(frame,'collect'),(f.DOI,))

    def test_complete_question_and_doi_schedule_required(self):
        queries=f.queries();hints=[dict(id=q['id'],question=q['question'],dois=[f.DOI]) for q in queries]
        products={}
        for name,rows in (('answer_queries',queries),('hints',hints),('doi_schedule',[f.DOI])):
            r.write(self.root/(name+'.json'),rows);products[name]=r.primary.proof(self.root/(name+'.json'))
        frame=dict(products=products,questions=2,unique_dois=1,question_doi_pairs=2)
        self.assertEqual(len(r.tasks(frame,'answer')[0]),2)
        frame['question_doi_pairs']=1
        with self.assertRaises(ValueError):r.tasks(frame,'answer')

    def test_invalid_frame_retains_failure_without_dispatch(self):
        args=SimpleNamespace(frame=self.root/'missing',frame_sha256='a'*64,output=self.root/'attempt')
        with patch.object(r,'execute_phase') as dispatch:
            with self.assertRaises(ValueError):r.execute(args)
        dispatch.assert_not_called();self.assertTrue((args.output/'FAILURE.json').exists())


if __name__=='__main__':unittest.main()
