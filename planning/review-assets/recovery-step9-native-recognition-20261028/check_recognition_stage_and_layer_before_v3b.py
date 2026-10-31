"""Regression-first pure stage/layer contradictions; original fixtures remain unchanged."""
import copy
import hashlib
from importlib import util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
CHECKER=HERE/'check_recognition_validation_v2.py'
REPORT=HERE/'RECOGNITION-STAGE-LAYER-REGRESSION-BEFORE-v3b.json'
spec=util.spec_from_file_location('modeled_rows_before_stage_layer_fix',CHECKER)
m=util.module_from_spec(spec);spec.loader.exec_module(m)
OBSERVED=[]
def early_call(rows,api,event):
    start=m.first('typed_version_and_defaults_observed');end=m.first(event)
    for row in rows[start:end]:
        row['native_call_counters'][api]['attempted']+=1;row['native_call_counters'][api]['returned']+=1
        state=row['native_state'];state['total_attempted']+=1;state['total_returned']+=1
        flags={'ggml_backend_load':('cpu_load_return_observed','cpu_registry_nonnull'),
            'llama_backend_init':('backend_init_return_observed','backend_owned'),
            'llama_model_load_from_splits':('model_load_return_observed','model_return_nonnull','model_owned')}
        for key in flags[api]:state[key]=True
class Checks(unittest.TestCase):
    def layer(self,group,key):
        rows=copy.deepcopy(m.BASE);row=next(r for r in rows if r['event']=='case_result' and ((group==1 and r['expected_kind']<2) or (group==0 and r['expected_kind']==3)))
        row['id']='wrong-id-with-valid-accounting'
        try:m.validate(rows)
        except m.h.RecognitionValidationError as error:
            OBSERVED.append(dict(case='wrong-id-'+key,coverage=error.coverage,error=str(error)))
            self.assertEqual(error.coverage[key],0)
        else:self.fail('Wrong identity accepted')
    def test_rejected_native_row_cannot_count_as_validated_native_result(self):self.layer(1,'native_case_results_validated')
    def test_rejected_harness_row_cannot_count_as_validated_harness_result(self):self.layer(0,'harness_dispositions_validated')
    def stage(self,api,event):
        rows=copy.deepcopy(m.BASE);early_call(rows,api,event)
        try:value=m.validate(rows)
        except m.h.RecognitionValidationError:OBSERVED.append(dict(case=api,accepted=False));return
        OBSERVED.append(dict(case=api,accepted_complete=value['complete'],native_counts=value['native_call_counters'][api]))
        self.fail('Consistent early native counter/state contradicts source stage ordering but was accepted')
    def test_early_backend_call_is_not_a_valid_no_backend_yet_row(self):self.stage('llama_backend_init','backend_init_returned_exact_CPU_identity_rechecked')
    def test_early_CPU_load_is_not_a_valid_pre_CPU_state(self):self.stage('ggml_backend_load','cpu_registry_verified_before_llama_backend_init')
    def test_early_model_load_is_not_a_valid_no_model_yet_row(self):self.stage('llama_model_load_from_splits','all_vocabulary_ids_EOG_enumerated')
def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
if __name__=='__main__':
    assert not REPORT.exists();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    value=dict(schema_version=1,status='failed_expected_before_stage_layer_fix' if not result.wasSuccessful() else 'unexpected_pass',
        tests=result.testsRun,failures=[str(c) for c,_ in result.failures],errors=[str(c) for c,_ in result.errors],source=pin(m.SOURCE),
        checker=pin(Path(__file__)),modeled_fixture=pin(CHECKER),observed=OBSERVED,
        activity=dict(CPU_binary_reads=0,GGUF_reads=0,SDK_constructors=0,native_calls=0,children=0),
        scope='Data-only semantic contradictions, not evidence of actual native calls or a qualified runtime bypass')
    with REPORT.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(REPORT))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
