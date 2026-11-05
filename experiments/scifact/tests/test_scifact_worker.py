import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

from asof.serde import canonical
from tether._process import ProcessLimits, supervise_command
from experiments.scifact.baseline import LEARNER_SETTINGS, VECTORIZER_SETTINGS, SEED
from experiments.scifact.tether_adapter import verify_session
from test_scifact_baseline import fictional

ROOT = Path(__file__).resolve().parents[3]
WORKER = ROOT/'experiments/scifact/worker.py'


def proof(path):
    raw=path.read_bytes()
    return {'path':str(path.resolve()),'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}


class WorkerTests(unittest.TestCase):
    def launch(self, recipe, root, name):
        path=root/(name+'.recipe.json');path.write_bytes(canonical(recipe)+b'\n')
        output=root/name
        result=supervise_command([sys.executable,'-I','-B',str(WORKER),'--recipe',str(path),'--output',str(output)],
                                 limits=ProcessLimits(timeout_seconds=40,max_output_bytes=1024*1024))
        return output,result

    def test_actual_fictional_fit_predict_and_audited_no_reference_access(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);corpus,queries,pairs=fictional()
            inputs={}
            for name,rows in [('corpus',list(corpus.values())),('queries_fit',queries),('fit_pairs',pairs)]:
                p=root/(name+'.jsonl');p.write_bytes(b''.join(canonical(x)+b'\n' for x in rows));inputs[name]=proof(p)
            limits={'phase_seconds':35,'query_seconds':10,'memory_bytes':8*1024**3}
            recipe={'schema_version':1,'mode':'fit','inputs':inputs,'configuration':{
                'method_id':'scifact_sparse_linear_v1','seed':SEED,
                'learner_settings':LEARNER_SETTINGS,'vectorizer_settings':VECTORIZER_SETTINGS},'schedule':[], 'limits':limits}
            fit,result=self.launch(recipe,root,'fit-job')
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
            complete=json.loads((fit/'COMPLETE.json').read_text())
            verification=verify_session(fit/'session',expected_receipt_sha256=complete['session_receipt_sha256'])
            self.assertEqual(verification['terminal_cells'],1)
            selected=[queries[0],queries[12],queries[24]]
            q=root/'queries.jsonl';q.write_bytes(b''.join(canonical(x)+b'\n' for x in selected))
            recipe={'schema_version':1,'mode':'predict','inputs':{
                'model_json':proof(fit/'model/model.json'), 'model_arrays':proof(fit/'model/arrays.npz'),'queries':proof(q)},
                'configuration':{'k':2,'rationale_threshold':0.5},'schedule':[x['id'] for x in selected],'limits':limits}
            prediction,result=self.launch(recipe,root,'predict-job')
            self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
            complete=json.loads((prediction/'COMPLETE.json').read_text())
            verification=verify_session(prediction/'session',expected_receipt_sha256=complete['session_receipt_sha256'])
            self.assertEqual(verification['terminal_cells'],4)
            events=[json.loads(x) for x in (prediction/'io-audit.jsonl').read_text().splitlines()]
            self.assertTrue(all(x['allowed'] for x in events))
            forbidden={inputs['fit_pairs']['path'],inputs['queries_fit']['path']}
            self.assertFalse(forbidden.intersection(x['path'] for x in events))
            records=[json.loads(p.read_text()) for p in (prediction/'session/cells').glob('*.json')]
            candidates=[r['result']['prediction'] for r in records if r['cell_id']!='setup']
            self.assertEqual(len(candidates),3)
            self.assertEqual(sum(not x['evidence'] for x in candidates),1)

    def test_extra_reference_input_is_denied_before_fitting(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            recipe={'schema_version':1,'mode':'fit','inputs':{'references_dev':{}},
                    'configuration':{},'schedule':[],'limits':{}}
            output,result=self.launch(recipe,root,'bad-job')
            self.assertNotEqual(result.returncode,0)
            self.assertIn(b'input names differ',result.stderr)
            self.assertTrue((output/'recipe.json').exists())
            self.assertFalse((output/'model').exists())


if __name__=='__main__':unittest.main()
