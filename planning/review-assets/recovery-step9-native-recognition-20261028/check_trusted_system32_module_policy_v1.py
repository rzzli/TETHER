"""Source/pure shared policy checks; no SDK, image file, compiler or native execution."""
import builtins
import copy
import hashlib
from importlib import util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
SOURCE=HERE/"trusted_system32_module_policy_v1.py"
CONTRACT=HERE/"TRUSTED-SYSTEM32-MODULE-POLICY-v1.json"
VECTORS=HERE/"TRUSTED-SYSTEM32-MODULE-VECTORS-v1.json"
REPORT=HERE/"TRUSTED-SYSTEM32-PARENT-MATCHER-PURE-PROOF-v1.json"
DENIED=[]
def guard(event,args):
    if event in ("subprocess.Popen","os.system","ctypes.dlopen") or event.startswith("socket."):
        DENIED.append(event);raise RuntimeError("Pure platform matcher only")
sys.addaudithook(guard)
spec=util.spec_from_file_location("own_platform_rule_for_checks",SOURCE)
m=util.module_from_spec(spec);spec.loader.exec_module(m)
contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
vectors=json.loads(VECTORS.read_text(encoding="utf-8"))


def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


class Checks(unittest.TestCase):
    def test_semantic_fingerprint_and_contract_are_exact(self):
        self.assertEqual(pin(CONTRACT)["sha256"],"fdd15d4f551efbd3c1ecb515b2724b4ee68cf08d3ea1ed2f5c2a576774da2ca4")
        self.assertEqual(m.SEMANTICS,contract["semantic_policy"])
        canonical=json.dumps(m.SEMANTICS,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
        self.assertEqual(hashlib.sha256(canonical).hexdigest(),m.POLICY_SHA256)
        self.assertEqual(m.POLICY_SHA256,"807995f6061d7a2c85144c58668fc2e4ecb79a4fb51d462e43d0a8dfc586d589")

    def test_all73_shared_admission_category_and_isolated_reason_vectors(self):
        self.assertEqual(len(vectors["cases"]),73)
        for case in vectors["cases"]:
            with self.subTest(case=case["id"]):
                if case["accepted"]:
                    result=m.match_modules(case["modules"],**case["context"])
                    self.assertEqual([r["policy_class"] for r in result["reports"]],case["expected_classes"])
                    self.assertEqual(result["module_policy_sha256"],m.POLICY_SHA256)
                else:
                    with self.assertRaises(m.ModulePolicyError) as caught:m.match_modules(case["modules"],**case["context"])
                    if "reason_if_isolated" in case:self.assertEqual(caught.exception.reason,case["reason_if_isolated"])

    def test_reported_images_never_become_filesystem_inputs(self):
        case=next(c for c in vectors["cases"] if c["id"]=="platform_apphelp.dll")
        def deny(*args,**kwargs):raise AssertionError("No filesystem operation is part of matching")
        with patch.object(builtins,"open",side_effect=deny),patch.object(Path,"open",side_effect=deny),patch.object(Path,"stat",side_effect=deny),patch.object(Path,"resolve",side_effect=deny):
            result=m.match_modules(case["modules"],**case["context"])
        self.assertEqual(result["reports"][-1]["policy_class"],"trusted_platform_context")
        self.assertEqual(result["platform_image_authentication"],"not_established")
        self.assertFalse(result["CPU_or_model_eligibility"])

    def test_serialized_verified_flags_or_child_categories_are_not_admission(self):
        case=copy.deepcopy(next(c for c in vectors["cases"] if c["id"]=="exact_self_core4"))
        for key,value in (("verified",True),("policy_class","trusted_platform_context"),("sha256","0"*64)):
            changed=copy.deepcopy(case["modules"]);changed[0][key]=value
            with self.assertRaises(m.ModulePolicyError):m.match_modules(changed,**case["context"])

    def test_rule_fingerprint_has_no_future_binary_or_parent_hash_dependency(self):
        self.assertNotIn("executable_sha256",m.SEMANTICS)
        self.assertNotIn("parent_sha256",m.SEMANTICS)
        ordinary=next(c for c in vectors["cases"] if c["id"]=="exact_self_core4")
        unicode=next(c for c in vectors["cases"] if c["id"]=="exact_scalar_native_context")
        self.assertEqual(m.match_modules(ordinary["modules"],**ordinary["context"])["module_policy_sha256"],
                         m.match_modules(unicode["modules"],**unicode["context"])["module_policy_sha256"])

    def test_observed17_is_only_a_data_policy_check(self):
        case=next(c for c in vectors["cases"] if c["id"]=="verified_current_census17_metadata_only")
        result=m.match_modules(case["modules"],**case["context"])
        classes=[row["policy_class"] for row in result["reports"]]
        self.assertEqual((classes.count("self_executable"),classes.count("pinned_runtime"),classes.count("trusted_platform_context")),(1,4,12))
        self.assertEqual(result["platform_image_authentication"],"not_established")


if __name__=="__main__":
    if REPORT.exists():raise RuntimeError("Preserve existing proof")
    original=pin(SOURCE)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    assert pin(SOURCE)==original
    value=dict(schema_version=1,status="passed" if result.wasSuccessful() else "failed",tests=result.testsRun,
        failures=[str(c) for c,_ in result.failures],errors=[str(c) for c,_ in result.errors],shared_vectors=73,
        matcher=original,contract=pin(CONTRACT),vectors=pin(VECTORS),checker=pin(Path(__file__)),
        module_policy_id=m.POLICY_ID,module_policy_sha256=m.POLICY_SHA256,denied_real_operations=DENIED,
        activity=dict(SDK_constructors=0,children=0,compiler_calls=0,reported_image_operations=0,new_census_or_tracing=0),
        scope="Pure rule/category checks and intended source semantics only; not native guard execution, image authenticity or ABI qualification")
    with REPORT.open("x",encoding="utf-8") as stream:json.dump(value,stream,sort_keys=True,indent=2);stream.write("\n")
    print(json.dumps(dict(proof=str(REPORT),sha256=pin(REPORT)["sha256"])))
    raise SystemExit(0 if result.wasSuccessful() else 1)
