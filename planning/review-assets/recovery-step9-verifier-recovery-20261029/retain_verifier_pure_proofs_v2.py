"""Retain the root-approved synthetic ownership/factory correction only."""
import ast
import datetime
import importlib.util
import json
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def owner_methods(filename):
    tree = ast.parse((HERE / filename).read_text(encoding="utf-8"))
    owner = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "_Owner")
    return {n.name: ast.dump(n, include_attributes=False) for n in owner.body if isinstance(n, ast.FunctionDef)}


def main():
    writer = load("recovery_writer_v1", "retain_verifier_pure_proofs_v1.py")
    checker = load("recovery_checker_v2", "check_deterministic_verifier_v2.py")
    before, after = owner_methods("deterministic_verifier_v1.py"), owner_methods("deterministic_verifier_v2.py")
    changed = sorted(name for name in before if before[name] != after[name])
    assert changed == ["__init__", "finish", "hash_files", "result"]
    unchanged = sorted(name for name in before if before[name] == after[name])
    result = writer.run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(checker.Checks))
    assert result["passed"] and result["methods"] == 23
    document = dict(schema_version=1, recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    status="V2_SOURCE_PURE_CORRECTION_PASS_INDEPENDENT_REVIEW_PENDING",
                    scope="Synthetic orchestration only; no live adapter/bootstrap/checker qualification, old verification eligibility or scientific claim.",
                    source=writer.pin("deterministic_verifier_v2.py"), checker=writer.pin("check_deterministic_verifier_v2.py"),
                    retention_writer=writer.pin(pathlib.Path(__file__).name), result=result,
                    previous_source=writer.pin("deterministic_verifier_v1.py"),
                    previous_proof=writer.pin("VERIFIER-RECOVERY-SOURCE-PURE-PROOF-v1.json"),
                    initial_ownership_witness=writer.pin("VERIFIER-OPEN-RETURN-REGRESSION-BEFORE-v2.json"),
                    independent_hold=writer.pin("VERIFIER-RECOVERY-INDEPENDENT-HOLD-SUPPLEMENT-v1.json"),
                    contract=writer.pin("VERIFIER-RECOVERY-DESIGN-CONTRACT-v2.json"),
                    correction=["Exact OpenReturn with owned is True and nonnull handle alone transfers ownership before deadline/metadata checks.",
                                "Typed OpenFailure transfers no handle; unknown/malformed returned observations never become guessed leases.",
                                "Future source-bound live port must validate and normalize platform-specific invalid handles before minting an ownership acknowledgment.",
                                "Known open failure is INCOMPLETE_ORIGINAL_IO; malformed ownership remains INCOMPLETE_UNKNOWN_IO_OR_CLEANUP.",
                                "Three post-reservation factories use existing durable stage reservation/return machinery; no new gates or caps."],
                    owner_AST_unchanged_methods=unchanged, owner_AST_changed_methods=changed,
                    gate_order=list(checker.v.GATES),
                    event_budget=dict(per_file=6, maximum_files=256, fixed_allowance=64, factory_added_events=6,
                                      failure_allowance=128, joint_worst_case=1728, cap=2048),
                    root_approval="Root explicitly approved this separate v2 typed-open/factory correction after the before-fix witness; no live adapter or old input access.",
                    old_original_or_payload_reads=0, SDK_native_compiler_calls=0,
                    author_self_clearance=False,
                    timing_limit="Measured pure test duration is clock-resolution dependent and does not establish live-file fit or a real bootstrap clock.")
    print(json.dumps(writer.write_new("VERIFIER-RECOVERY-SOURCE-PURE-PROOF-v2.json", document)))


if __name__ == "__main__":
    main()
