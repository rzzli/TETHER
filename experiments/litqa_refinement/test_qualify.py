"""Prospectively fixed invented control coverage and actor projections."""
import unittest
from contextlib import ExitStack, nullcontext
from pathlib import Path
from types import SimpleNamespace
import tempfile
from unittest.mock import patch
from tether_engine.serde import canonical,fingerprint
from . import qualify,model,pipeline


class NativeControlTests(unittest.TestCase):
    def test_completed_control_lifecycle_retains_terminal_after_all_calls(self):
        folder=qualify.ROOT/'data/cache/sc05-refinement-controller-controls';folder.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder) as temporary, ExitStack() as stack:
            root=Path(temporary);output=root/'attempt';license=root/'LICENSE';license.write_text('invented')
            provenance=dict(weights_sha256={'invented.gguf':'a'*64},runtime_sha256='b'*64)
            frame=dict(kind='sc05_refinement_native_controls_v1',purpose='fictional_qualification',output=str(output),
                code_files=[],qualifier=qualify.run.proof(qualify.__file__),interpreter=qualify.run.proof(qualify.sys.executable),
                model_receipt=dict(path=str(root/'receipt.json'),sha256=qualify.run.MODEL_RECEIPT),seconds=1200,
                model_license=qualify.run.proof(license),model_provenance=provenance,model_spec={},port=55631,alias='invented')
            path=root/'FRAME.json';path.write_bytes(canonical(frame))
            expected={item['descriptor']['execution_id']:item['expected'] for item in qualify.controls(provenance)}
            audit=SimpleNamespace(denials=0,activate=lambda:None,flush=lambda:None)
            owner=SimpleNamespace(terminal_record=dict(pid=1,server_stopped=True))
            for target,name,value in ((qualify.run,'code_files',[]),
                    (qualify.native_model,'make_server_spec',({}, {}, provenance)),
                    (qualify.native_model,'owned_server',nullcontext(owner)),
                    (qualify,'RoleAudit',audit),(qualify,'contain_process_tree',None),
                    (qualify,'DeadlineWatchdog',nullcontext()),
                    (qualify,'ProcessSamples',nullcontext(SimpleNamespace(values=[]))),
                    (qualify,'process_sample',{})):
                stack.enter_context(patch.object(target,name,return_value=value))
            caller=stack.enter_context(patch.object(qualify.pipeline,'NativeCaller')).return_value
            def checked(result,descriptor,cell,deadline):
                return dict(summary=dict(status='completed',decoded=expected[descriptor['execution_id']]),
                    summary_proof=None),{},None
            stack.enter_context(patch.object(qualify.pipeline,'_model_result',side_effect=checked))
            result=qualify.execute(path,qualify.run.proof(path)['sha256'],output)
            self.assertEqual(result['status'],'controls_passed');self.assertEqual(caller.call_count,8)
            self.assertTrue((output/'RESULT.json').exists());self.assertFalse((output/'FAILURE.json').exists())
            self.assertFalse((output/'RECEIPT.json').exists())

    def test_dotdot_output_alias_is_rejected_before_reservation(self):
        folder=qualify.ROOT/'data/cache/sc05-refinement-controller-controls';folder.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=folder) as temporary:
            path=Path(temporary)/'frame.json';path.write_bytes(b'{}')
            output=qualify.ROOT/'data/cache/..'/'qualification-escaped'
            frame=dict(kind='sc05_refinement_native_controls_v1',purpose='fictional_qualification',output=str(output),
                code_files=[],qualifier=qualify.run.proof(qualify.__file__),interpreter=qualify.run.proof(qualify.sys.executable),
                model_receipt=dict(sha256=qualify.run.MODEL_RECEIPT),seconds=1200)
            with patch.object(qualify.run,'capture',return_value=frame),patch.object(qualify.run,'code_files',return_value=[]), \
                    patch.object(qualify,'RunJournal',side_effect=AssertionError('Reserved before path authority')) as reserve:
                with self.assertRaises(ValueError):qualify.execute(path,qualify.run.proof(path)['sha256'],output)
                reserve.assert_not_called()

    def test_all_eight_controls_are_bounded_and_reference_free(self):
        provenance=dict(weights_sha256={'invented.gguf':'a'*64},runtime_sha256='b'*64)
        cases=qualify.controls(provenance)
        self.assertEqual(len(cases),8);self.assertEqual(len({r['id'] for r in cases}),8)
        self.assertEqual({r['descriptor']['task'] for r in cases},{'critic','repair','removal'})
        for item in cases:
            descriptor=item['descriptor'];task=descriptor['task']
            self.assertNotIn('expected',pipeline._cell_inputs(descriptor))
            if task=='critic':
                request,payload=model.make_critic_request(descriptor['query'],descriptor['prior'],descriptor['sources'],provenance)
            else:
                request,payload=descriptor['prepared_member']['request'],descriptor['prepared_member']['payload']
                self.assertEqual(descriptor['control_sha256'],fingerprint(dict(query=descriptor['query'],candidate=descriptor['prior'],critique=descriptor['critic'])))
            model.validate_binding(request,payload)
            self.assertLessEqual(len(payload['prompt'].encode()),14000)
            self.assertNotIn('expected',request)
            if task=='removal':self.assertFalse(request['sources'])

    def test_contradiction_absence_and_retained_prior_are_distinct(self):
        cases={r['id']:r for r in qualify.controls(dict(weights_sha256={'invented.gguf':'a'*64},runtime_sha256='b'*64))}
        self.assertEqual(cases['critic-contradicted']['expected']['support'],'contradicted')
        self.assertEqual(cases['critic-contradicted']['descriptor']['prior']['prediction']['answer_index'],1)
        self.assertIsNone(cases['critic-absent-candidate']['descriptor']['prior']['prediction'])
        self.assertFalse(cases['critic-absent-source']['descriptor']['sources'])
        removal=cases['removal']['descriptor']
        self.assertFalse(removal['sources']);self.assertIsNotNone(removal['prior']['prediction'])
        with self.assertRaises(TypeError):removal['prior']['prediction']['answer_index']=1


if __name__=='__main__':unittest.main()
