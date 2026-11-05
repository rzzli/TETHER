"""Reference-only process qualification using invented claims and abstracts."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

from asof.serde import canonical
from tether._process import ProcessLimits, supervise_command
from experiments.scifact.run import file_proof, read, write, session_cells

ROOT=Path(__file__).resolve().parents[3]


class ScoringWorkerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        corpus=[{"doc_id":1,"title":"Invented article","abstract":["An invented sentence."]}]
        gold=[{"id":1,"claim":"An invented claim.","cited_doc_ids":[1],"evidence":{"1":[{"label":"SUPPORT","sentences":[0]}]}}]
        self.predictions=[{"id":1,"evidence":{"1":{"label":"SUPPORT","sentences":[0]}}}]
        for name,values in (("corpus",corpus),("references",gold)):
            (self.root/(name+".jsonl")).write_bytes(b"".join(canonical(row)+b"\n" for row in values))
        write(self.root/"candidates.json",self.predictions)
        self.recipe={"schema_version":1,"mode":"tune","inputs":{name:file_proof(self.root/filename) for name,filename in
                      (("corpus","corpus.jsonl"),("references","references.jsonl"),("candidates","candidates.json"))},
                     "schedule":[1],"evaluator":file_proof(ROOT/"data/reference/scifact-evaluator-66feffc5/evaluator/eval.py"),
                     "limits":{"phase_seconds":60,"memory_bytes":1024**3}}

    def launch(self,recipe_name="recipe.json",output_name="job"):
        write(self.root/recipe_name,self.recipe)
        return supervise_command([sys.executable,"-I","-B",str(ROOT/"experiments/scifact/score_worker.py"),
                                  "--recipe",str(self.root/recipe_name),"--output",str(self.root/output_name)],
                                 limits=ProcessLimits(timeout_seconds=60,max_output_bytes=1024**2))

    def test_exact_native_metrics_and_managed_input_scope(self):
        process=self.launch();self.assertEqual(process.returncode,0,process.stderr.decode())
        result=read(self.root/"job/RESULT.json");self.assertEqual(len(result),12)
        self.assertTrue(all(value==1 for value in result.values()))
        records=session_cells(self.root/"job",["score"])
        self.assertEqual(records["score"]["resources"]["examples"],1)
        audit=[json.loads(line) for line in (self.root/"job/io-audit.jsonl").read_bytes().splitlines()]
        self.assertTrue(all(row["allowed"] for row in audit))
        inputs={str(Path(proof["path"]).resolve()) for proof in self.recipe["inputs"].values()}
        self.assertTrue(inputs<={row["path"] for row in audit})
        self.assertFalse(any("model.json" in (row["path"] or "") for row in audit))

    def test_changed_reference_bytes_fail_and_retain_attempt(self):
        self.recipe["inputs"]["references"]["sha256"]="0"*64
        process=self.launch();self.assertNotEqual(process.returncode,0)
        self.assertTrue((self.root/"job/FAILED.json").is_file())
        self.assertFalse((self.root/"job/COMPLETE.json").exists())
        records=session_cells(self.root/"job",["score"],require_complete=False)
        self.assertEqual(records["score"]["status"],"failed")
        again=self.launch("retry-recipe.json")
        self.assertNotEqual(again.returncode,0)
        self.assertEqual(records,session_cells(self.root/"job",["score"],require_complete=False))

    def test_operational_failure_never_becomes_successful_nei(self):
        self.recipe["mode"]="evaluate"
        write(self.root/"dispositions.json",[{"id":1,"producer_status":"timeout","check_status":"not_run","prediction":None,"reason":"fictional deadline"}])
        self.recipe["inputs"]["candidates"]=file_proof(self.root/"dispositions.json")
        process=self.launch();self.assertEqual(process.returncode,0,process.stderr.decode())
        result=read(self.root/"job/RESULT.json")
        self.assertEqual(result["scheduled_count"],1);self.assertEqual(result["counts"]["produced"],0)
        self.assertEqual(result["counts"]["successful_native_nei"],0)
        self.assertEqual(result["counts"]["raw_failure_placeholders"],1)

    def test_extra_model_input_rejected_before_scoring(self):
        self.recipe["inputs"]["model"]=self.recipe["inputs"]["corpus"]
        process=self.launch();self.assertNotEqual(process.returncode,0)
        self.assertFalse((self.root/"job").exists())


if __name__=="__main__":unittest.main()
