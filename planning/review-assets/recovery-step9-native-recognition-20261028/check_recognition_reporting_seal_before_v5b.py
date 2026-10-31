"""Pure regression-first injection at post-cleanup report derivation; no real SDK."""
import ast
import copy
import hashlib
from importlib import util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
HARNESS=HERE/'check_recognition_parent_integration_v4.py'
REPORT=HERE/'RECOGNITION-REPORT-SEAL-REGRESSION-BEFORE-v5b.json'
spec=util.spec_from_file_location('retained_fake_harness_before_report_boundary',HARNESS)
m=util.module_from_spec(spec);spec.loader.exec_module(m)
OBSERVED=[]
class Inject(ast.NodeTransformer):
    def visit_FunctionDef(self,node):
        if node.name!='harness':return node
        output=[]
        for statement in node.body:
            if isinstance(statement,ast.Expr) and isinstance(statement.value,ast.Call) and isinstance(statement.value.func,ast.Name) and statement.value.func.id=='exec' and len(statement.value.args)==2 and isinstance(statement.value.args[1],ast.Name) and statement.value.args[1].id=='ns':
                output.append(statement)
                output.extend(ast.parse('''def metadata_fault(*args):
    raise (KeyboardInterrupt if fault=="metadata_KI" else RuntimeError)("Synthetic report derivation fault")
ns["parent_payload_observations"]=metadata_fault
''').body)
            elif isinstance(statement,ast.Assign) and isinstance(statement.value,ast.Call) and isinstance(statement.value.func,ast.Subscript) \
                and isinstance(statement.value.func.value,ast.Name) and statement.value.func.value.id=='ns':
                output.append(ast.Try(body=[statement],handlers=[ast.ExceptHandler(type=ast.Name(id='BaseException',ctx=ast.Load()),name='error',body=ast.parse('''OBSERVED.append(dict(case=name,exit_code=exit_code,error_class=type(error).__name__,
    terminal_seal_exists=(output/"terminal-seal.json").exists(),original_lease100_closed=api.counts.get(100,0)>0,
    fake_API_events=list(api.events),output=str(output)))
raise
''').body)],orelse=[],finalbody=[]))
            else:output.append(statement)
        node.body=output;return node
tree=ast.parse(HARNESS.read_text(encoding='utf-8'))
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='harness')
namespace=dict(m.__dict__,OBSERVED=OBSERVED)
exec(compile(ast.fix_missing_locations(ast.Module(body=[Inject().visit(copy.deepcopy(node))],type_ignores=[])),str(HARNESS)+'::<pure metadata-fault harness>','exec'),namespace)
class Checks(unittest.TestCase):
    def test_report_failure_or_interrupt_never_bypasses_original_lease_cleanup_and_seal(self):
        for fault in ('metadata_runtime','metadata_KI'):
            for code in (0,2):
                with self.subTest(fault=fault,code=code):
                    try:namespace['harness'](fault+'-'+str(code),exit_code=code,fault=fault)
                    except BaseException:
                        observation=OBSERVED[-1]
                        self.assertTrue(observation['original_lease100_closed'],'Original read lease must close on metadata fault')
                        self.assertTrue(observation['terminal_seal_exists'],'Metadata fault must retain mandatory failed seal')
                    else:self.fail('Expected v4 metadata derivation fault to be handled and retained')
def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
if __name__=='__main__':
    assert not REPORT.exists();result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    value=dict(schema_version=1,status='failed_expected_before_unconditional_sealer_boundary' if not result.wasSuccessful() else 'unexpected_pass',
        tests=result.testsRun,subcases=4,failures=[str(c) for c,_ in result.failures],errors=[str(c) for c,_ in result.errors],
        source=pin(m.SOURCE),harness=pin(HARNESS),checker=pin(Path(__file__)),observed=OBSERVED,
        activity=dict(actual_children=0,SDK_constructors=0,CPU_binary_reads=0,GGUF_reads=0),
        scope='Injected pure reporting RuntimeError/KeyboardInterrupt with fake process/file leases only; not an actual leaked host handle or runtime run')
    with REPORT.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(REPORT))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
