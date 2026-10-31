"""Retain only root-authorized interface guard/report-copy correction proof."""
import ast
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
import unittest

HERE = Path(__file__).parent


def pin(name):
    path = HERE / name
    raw = path.read_bytes()
    return dict(path=str(path.absolute()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    old = ast.parse((HERE / "verifier_bootstrap_interfaces_v1.py").read_text(encoding="utf-8"))
    new = ast.parse((HERE / "verifier_bootstrap_interfaces_v2.py").read_text(encoding="utf-8"))
    old_owner = next(n for n in old.body if isinstance(n, ast.ClassDef) and n.name == "BootstrapOwner")
    new_owner = next(n for n in new.body if isinstance(n, ast.ClassDef) and n.name == "BootstrapOwner")
    methods = {n.name: n for n in old_owner.body if isinstance(n, ast.FunctionDef)}
    changed = [n.name for n in new_owner.body if isinstance(n, ast.FunctionDef)
               and ast.dump(n, include_attributes=False) != ast.dump(methods[n.name], include_attributes=False)]
    assert changed == ["capture", "snapshot"]
    new.body = [n for n in new.body if not (isinstance(n, ast.FunctionDef) and n.name == "_copy_diagnostics")]
    new_owner.body = [methods[n.name] if isinstance(n, ast.FunctionDef) and n.name in changed else n for n in new_owner.body]
    assert ast.dump(new, include_attributes=False) == ast.dump(old, include_attributes=False)
    spec = importlib.util.spec_from_file_location("bootstrap_interface_v2_checks", HERE / "check_verifier_bootstrap_interfaces_v2.py")
    checker = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = checker
    spec.loader.exec_module(checker)
    output = io.StringIO(); started = time.monotonic()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(checker.Checks))
    elapsed = time.monotonic() - started
    assert result.wasSuccessful() and result.testsRun == 22
    artifacts = {name: pin(name) for name in (
        "verifier_bootstrap_interfaces_v1.py", "VERIFIER-BOOTSTRAP-INTERFACES-PURE-PROOF-v1.json",
        "VERIFIER-INTERFACE-SOURCE-IMPLEMENTATION-DECISION-v1.json",
        "VERIFIER-BOOTSTRAP-PEER-FAULTS-BEFORE-v1.json",
        "VERIFIER-BOOTSTRAP-INTERFACES-PEER-REVIEW-v1.json",
        "VERIFIER-BOOTSTRAP-CORRECTION-REGRESSION-BEFORE-v2.json")}
    assert artifacts["verifier_bootstrap_interfaces_v1.py"]["sha256"] == "4c5c0ee62c5663e7666094fdccfcd110ab1ed77b420dfc6c6499a12d7a899966"
    record = dict(schema_version=1, recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status="V2_PURE_INTERFACE_CORRECTION_PASS_INDEPENDENT_REVIEW_PENDING",
        source=pin("verifier_bootstrap_interfaces_v2.py"), checker=pin("check_verifier_bootstrap_interfaces_v2.py"),
        recorder=pin(Path(__file__).name), preserved_artifacts=artifacts,
        root_authorization="Root explicitly authorized separate source/pure v2 after Grammar full review, batching only original read-port identity before hash state/dispatch and detached nested snapshot diagnostics.",
        methods=result.testsRun, failures=len(result.failures), errors=len(result.errors), elapsed_seconds=elapsed,
        output=output.getvalue(),
        before_fix="Two new regression methods failed against the byte-identical preserved4c5c source before this correction; independent before030ade and full HOLDc54a are retained unchanged.",
        source_delta=dict(changed_owner_methods=changed, new_helper="_copy_diagnostics",
                          all_other_module_AST_unchanged=True,
                          capture_guard="port is self._port required before hash_attempted, event reservation, read or digest factory",
                          snapshot="Copy all nested ordinary primary/error/compile diagnostic containers; returned mutation cannot alter owner records"),
        scope="Pure injected origin/owner/slots/compiler interfaces only; no real first-clock entry, production engine integration, platform adapter, evidence checker or eligibility.",
        observed_qualification_flags="Every snapshot remains verification_completeFalse and real_profile_qualifiedFalse.",
        old_original_payload_or_native_operations=0, runtime_protocols_created=0,
        previous_negative_and_timeout_unchanged=True, author_self_clearance=False)
    raw = (json.dumps(record, indent=2, allow_nan=False) + "\n").encode("utf-8")
    out = HERE / "VERIFIER-BOOTSTRAP-INTERFACES-PURE-PROOF-v2.json"
    with out.open("xb") as stream: stream.write(raw)
    print(json.dumps(pin(out.name)))


if __name__ == "__main__":
    main()
