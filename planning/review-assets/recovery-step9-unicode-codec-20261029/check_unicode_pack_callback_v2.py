"""Regression replay on frozen v1, then exact narrow v2; all packs in memory."""
from datetime import datetime, timezone
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent


def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def main():
    before = sys.argv[1:] == ["--before"]
    assert before or sys.argv[1:] == []
    source=HERE/("unicode_pack_codec_v1.py" if before else "unicode_pack_codec_v2.py")
    output=HERE/("UNICODE-PACK-CODEC-REGRESSION-BEFORE-v2.json" if before else "UNICODE-PACK-CODEC-REGRESSION-AFTER-v2.json")
    assert not output.exists()
    original=pin(source)
    spec=importlib.util.spec_from_file_location("unicode_callback_regression_"+("before" if before else "after"),source)
    codec=importlib.util.module_from_spec(spec);sys.modules[spec.name]=codec;spec.loader.exec_module(codec)
    wire=HERE.parent/"recovery-step9-unicode-wire-20261029";control=HERE.parent/"recovery-step9-unicode-control-20261029"
    captured=[(wire/"UNICODE-WIRE-DESIGN-CONTRACT-v2.json").read_bytes(),(wire/"UNICODE-WIRE-FRAMING-CONTRACT-v1.json").read_bytes(),
              (control/"UNICODE-CONTROL-CORPUS-v1.json").read_bytes(),(control/"UNICODE-CONTROL-STAGES-v1.json").read_bytes(),
              (control/"UNICODE-CONTROL-CONTRACT-v2.json").read_bytes(),(control/"UNICODE-PIECE-ANALYZER-CONTRACT-v1.json").read_bytes()]
    profile=codec.make_profile(codec.SourceBytes(*captured),check=lambda:None)
    packed=codec.encode(profile,check=lambda:None)
    probes=[]
    def errors():
        return [UnicodeError("synthetic callback"),UnicodeDecodeError("utf-8",b"\xff",0,1,"synthetic callback"),
                UnicodeEncodeError("utf-8","\ud800",0,1,"synthetic callback"),UnicodeTranslateError("x",0,1,"synthetic callback")]

    class Checks(unittest.TestCase):
        def test_callback_unicode_exception_identity_before_and_after_ID_copy(self):
            for occurrence in (1,2):
                for marker in errors():
                    with self.subTest(occurrence=occurrence,error_class=type(marker).__name__):
                        found=[0];observed=None
                        def check():
                            frame=sys._getframe(1)
                            if frame.f_code.co_name=="take" and frame.f_locals.get("n")==9:
                                found[0]+=1
                                if found[0]==occurrence:raise marker
                        try:codec.decode(packed,profile,check=check)
                        except BaseException as error:observed=error
                        probes.append(dict(error_class=type(marker).__name__,take_check_occurrence=occurrence,
                                           observed_class=None if observed is None else type(observed).__name__,
                                           same_exception=observed is marker,only_cause=observed is not None and observed.__cause__ is marker))
                        self.assertIs(observed,marker)

        def test_invalid_data_still_gets_ID_ASCII_error(self):
            mutated=packed[:192]+b"\xff"+packed[193:]
            with self.assertRaises(codec.CodecError) as caught:codec.decode(mutated,profile,check=lambda:None)
            self.assertEqual(str(caught.exception),"ID_ASCII")
            self.assertIsInstance(caught.exception.__cause__,UnicodeDecodeError)

        def test_all_data_exception_regions_exclude_check_or_take_dispatch(self):
            tree=ast.parse(source.read_text(encoding="utf-8"));regions=0
            for node in ast.walk(tree):
                if not isinstance(node,ast.Try):continue
                regions+=1
                calls=[call for statement in node.body for call in ast.walk(statement) if isinstance(call,ast.Call)]
                self.assertFalse(any(isinstance(call.func,ast.Name) and call.func.id in ("check","_check","take","_hash") for call in calls))
            self.assertEqual(regions,4)

    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    stable=pin(source)==original
    record=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),source=original,checker=pin(Path(__file__)),
                status=("EXPECTED_BEFORE_COUNTEREXAMPLES_REPRODUCED" if before and len(result.failures)==9 and not result.errors else
                        "passed" if result.wasSuccessful() and stable else "failed"),
                chronology="Preserved-v1 regression replay executed after root counterexample and before writing v2 correction." if before else "Same regression vectors executed against separately named v2 after its one protected-region correction.",
                methods=result.testsRun,failures=[dict(test=str(t),traceback=s) for t,s in result.failures],errors=[dict(test=str(t),traceback=s) for t,s in result.errors],
                callback_probes=probes,source_unchanged=stable,valid_pack_bytes=len(packed),pack_persisted=False,
                scope="Callback identity and data-error separation only. Other four data catches inspected for callback-dispatch overlap; no general API change.",
                profile_qualified=False,originals_authenticated=False,runtime_authorized=False,CPU_GGUF_oldpack_operations=0,SDK_native_compiler_operations=0)
    with output.open("x",encoding="utf-8") as out:json.dump(record,out,sort_keys=True,indent=2);out.write("\n")
    print(json.dumps(dict(proof=pin(output),status=record["status"],methods=result.testsRun,failures=len(result.failures),callback_probes=len(probes))))
    return 0 if record["status"] in ("passed","EXPECTED_BEFORE_COUNTEREXAMPLES_REPRODUCED") else 1


if __name__=="__main__":raise SystemExit(main())
