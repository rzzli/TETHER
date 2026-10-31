"""Final finite indexed-source peer retention; metadata/AST only, no replay."""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASIS = ROOT.parent / "recovery-step9-shared-owner-20261029"
PRE = ROOT.parent / "recovery-step9-production-preflight-20261029"
EXACT = {
    "shared_owner_v3.py": "d8ee1e135a9e9d4b5c197eacb287f9e0fcb8c145d8baef154aa8faa7a68fca31",
    "shared_file_ports_v3.py": "8ecabef93656867fa443d26ef8826b359029f79d33c220cbc1a41734f80c0f49",
    "continue_verification_v3.py": "16ff0a3463d7d97f068fb38b709addfdfa43944490c015329e4470fad314a47e",
    "INDEXED-ACCOUNTING-SOURCE-PAUSE-v3.json": "8c0103972a4cd33365e0b642e8d9ae44981d6121a31d644cfc2e443c1f20390c",
    "INDEXED-ACCOUNTING-INDEPENDENT-ACTUAL-PROOF-v3.json": "173bfdeba4a25bab32ac676c1af194805cd33dc847b2616e12f4ffa7a905d660",
    "INDEXED-ACCOUNTING-AUTHOR-CONTROLS-PURE-PROOF-v3.json": "80d93cc5a7d5f53229380b79c8d65d02d70130fa563a33acbaee0aaa900c9b91",
    "INDEXED-ACCOUNTING-AUTHOR-SUPPLEMENT-PURE-PROOF-v3.json": "a86d0da9642ef79a0432e50cea7a3f4d203824a29c3f367746daca06549bbe81",
    "INDEXED-ACCOUNTING-ACTUAL-EVIDENCE-FREEZE-v3.json": "2be26673ca6d3ca71c0025d0917538dc17f22d41523bbab37c906f22df4c2d58",
}


def methods(raw):
    found = {}
    def walk(node, prefix=""):
        for value in node.body:
            if isinstance(value, ast.FunctionDef):
                found[prefix + value.name] = value
            elif isinstance(value, ast.ClassDef):
                walk(value, prefix + value.name + ".")
    walk(ast.parse(raw))
    return found


def main():
    inputs, captured = {}, {}
    def pin(path, expected=None, size=None):
        assert path.parent in (ROOT, BASIS, PRE), str(path)
        key = str(path)
        if key not in inputs:
            raw = path.read_bytes()
            inputs[key] = dict(path=key, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            captured[key] = raw
        actual = inputs[key]
        if expected is not None:assert actual["sha256"] == expected, path.name
        if size is not None:assert actual["bytes"] == size, path.name
        return actual
    for name, digest in EXACT.items():pin(ROOT / name, digest)
    freeze = json.loads(captured[str(ROOT / "INDEXED-ACCOUNTING-ACTUAL-EVIDENCE-FREEZE-v3.json")])
    for item in list(freeze["inputs"].values()) + [freeze["freezer"]]:
        pin(Path(item["path"]), item["sha256"], item["bytes"])
    comparisons, unchanged, changed, added = [], [], [], []
    old_source_sha={"shared_owner":"0ecb8c02e3a8016f2de3a69650b34776de312ffca6f37ded85a31eba9c50c24b","shared_file_ports":"a224bfb9e9f33bf2f6b9329f0b337d0076bdab418083d05deb3f59b52722a059","continue_verification":"1d05a7398fe215cae987a76ab3960e0dc3730b89fad79caca64c466bac1f4b2f"}
    for stem in ("shared_owner", "shared_file_ports", "continue_verification"):
        old, new = BASIS / (stem + "_v2.py"), ROOT / (stem + "_v3.py")
        pin(old,old_source_sha[stem])
        a, b = methods(captured[str(old)]), methods(captured[str(new)])
        dump = lambda node: ast.dump(node, include_attributes=False)
        equal = [name for name in a if name in b and dump(a[name]) == dump(b[name])]
        different = [name for name in a if name in b and dump(a[name]) != dump(b[name])]
        extra = [name for name in b if name not in a]
        assert set(a) <= set(b)
        comparisons.append(dict(old=inputs[str(old)], new=inputs[str(new)],
                                changed_methods=different, added_methods=extra,
                                unchanged_methods=len(equal), removed_methods=[]))
        unchanged.extend(equal);changed.extend(different);added.extend(extra)
    assert (len(unchanged), len(changed), len(added)) == (95, 20, 5)
    assert set(added) == {"SharedOwner._require_accounting_work", "SharedOwner._accounting_failed",
                          "SharedOwner._index_reserved_call", "SharedOwner._fold_read_fact",
                          "SharedOwner._canonical_projection"}
    # Locate any loop that directly traverses the authoritative call list.
    traversal = []
    for filename in ("shared_owner_v3.py", "shared_file_ports_v3.py"):
        for name, node in methods(captured[str(ROOT / filename)]).items():
            for item in ast.walk(node):
                expressions = [item.iter] if isinstance(item, (ast.For, ast.AsyncFor, ast.comprehension)) else []
                if any(any(isinstance(child, ast.Attribute) and child.attr == "_calls"
                           for child in ast.walk(expression)) for expression in expressions):
                    traversal.append(filename + ":" + name)
                if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute) and isinstance(item.func.value, ast.Name):
                    assert item.func.value.id != "list", "source base-list instrumentation bypass"
    assert traversal == ["shared_owner_v3.py:SharedOwner._canonical_projection"]
    old_tests_equal = []
    for stem in ("check_shared_owner_author_controls", "check_shared_owner_author_supplement"):
        old, new = BASIS / (stem + "_v2.py"), ROOT / (stem + "_v3.py")
        pin(old);pin(new)
        a,b=methods(captured[str(old)]),methods(captured[str(new)])
        names=[name for name in a if name.startswith("t") and name[1:3].isdigit()] if stem.endswith("controls") else ["diagnostic_capture","unreturned_read_unknown","returned_count_before_late_clock","returned_checker_before_late_clock"]
        assert all(ast.dump(a[name],include_attributes=False)==ast.dump(b[name],include_attributes=False) for name in names)
        old_tests_equal.extend(names)
    assert len(old_tests_equal)==16
    proof=json.loads(captured[str(ROOT / "INDEXED-ACCOUNTING-INDEPENDENT-ACTUAL-PROOF-v3.json")])
    assert proof["status"]=="passed" and proof["methods"]==15
    assert proof["histories_executed"]==proof["histories_matched"]==48 and proof["snapshot_count"]==372
    assert proof["errors"]==proof["failures"]==proof["audit_denials"]==[]
    assert all(proof["source_unchanged"].values()) and all(proof["test_unchanged"].values())
    assert len(freeze["actual_hot_metrics"])==4 and len(freeze["explicit_canonical_report_metrics"])==18 and len(freeze["quarantine_checks"])==5
    for row in freeze["actual_hot_metrics"]:
        for key in ("iterated_items","membership_items","slice_copied_items"):assert row["metrics"][key]==0
    for name, count in (("INDEXED-ACCOUNTING-AUTHOR-CONTROLS-PURE-PROOF-v3.json",12),("INDEXED-ACCOUNTING-AUTHOR-SUPPLEMENT-PURE-PROOF-v3.json",4)):
        p=json.loads(captured[str(ROOT/name)]);assert p["status"]=="PASS" and p["methods"]==count and all(r["passed"] for r in p["results"])
    report=dict(
        schema_version=1,status="CLEAR_SOURCE_PURE_INDEXED_N4_V3",material_blockers=[],
        recorded_at_utc="2026-10-29 18:01:24 UTC",reviewer="native_039_acceptance_audit",
        source=inputs[str(ROOT/"shared_owner_v3.py")],helper_sha256=EXACT["shared_owner_v3.py"],
        source_pins=[inputs[str(ROOT/n)] for n in ("shared_owner_v3.py","shared_file_ports_v3.py","continue_verification_v3.py")],
        evidence_freeze=inputs[str(ROOT/"INDEXED-ACCOUNTING-ACTUAL-EVIDENCE-FREEZE-v3.json")],
        inputs=inputs,method_delta=comparisons,
        independent_static_summary=dict(unchanged_existing_methods=95,changed_existing_methods=20,new_private_helpers=5,removed_methods=0,controller_methods_unchanged=4,old_author_assertion_methods_unchanged=16,global_call_list_traversal_locations=traversal),
        reviewed_invariants=[
            "Raw scalar/count assignment occurs inside the catch envelope before derived folding/hints/aux. Domain and canonical-ref checks remain strict; this is Python-visible injected-port ordering, not native-return atomicity.",
            "Canonical append and all index registration are guarded before invoked=True. Failed before/after registration leaves actual reserved/unentered records and original errors; no undo/retry/guessed entry.",
            "Private per-call watermarks distinguish pendingNone and known0, contribute identical complete facts once, and quarantine all fold interruptions including a wrapper throwing after commit. The first accounting fault is retained before diagnostics.",
            "Noncleanup check/read_known refuse quarantine before clock/dispatch/progress. Legal cleanup uses the same Origin hardclock and direct canonical open/close pointers/raw scalars, not known-byte cache or display hints.",
            "Hot handle/read-known/ref/quota paths use direct ordinal or per-file fields. No canonical call-list iteration/membership/slice, base-list bypass, copied call ledger, global-dictionary traversal or hidden hot rebuild remains.",
            "The named projection makes one authoritative call pass and one file pass, derives raw/API/known/unknown/open/close views, and never repairs caches. Healthy consistency compares derived state with raw truth before its existing gate, with original work checks before/after.",
            "Snapshot/packet keys and N4/4KiB/16KiB/R68/C92/E224/gen68/output budgets remain unchanged. Context reporting uses the same owner-created blob keys for linear per-file membership; no source eligibility or public shape is added.",
        ],
        retained_evidence=dict(
            independent_methods=15,frozen_histories=48,matched_histories=48,same_focused_methods=8,precode_indexed_methods=6,
            strict_full_history_snapshots=372,full48_fake_dispatches=518,full48_inmemory_toy_module_execs=34,
            unchanged_author_methods=12,unchanged_author_supplement_methods=4,
            hot_metrics=freeze["actual_hot_metrics"],named_canonical_reports=18,quarantine_checks=5,
            facts="Four hot windows have0iteration/membership/slice; Read admission index6/len8/oneappend. Named reports retain exactly r visits in measured6/18-record worlds. Five healthy-clock quarantine checks preserve selected source facts and no I/O/progress."),
        chronology="Frozen d76/cccf/52da and acceptedV2 BEFORE24da precede indexed implementation. The first coherent8c010 source was paused before tests. Independent15 and author12+4 are separately retained runs; local zero-run fields do not erase earlier acceptedV2 or author runs. First candidates and all prior failures remain preserved.",
        scope_limits=[
            "Source/pure N4 prototype only; list-access metrics and source loop shape do not measure time, physical memory or full-roster fit.",
            "The report/runtime input set is209 invented bytes. The real14-export/FFI conversion window, first pre-import clock, physical sink, original files and source/checker closure remain unqualified.",
            "Large-role streaming/storage/retained-query/generation/packet limits from production preflight remain open; no cap lift or new full-roster admission follows.",
            "Old failed recognition profile/whole-check timeout, app0.3.11/defaultv2 and scientific/human gates are unchanged. Separate Unicode runtime policies and real resource/native qualification remain pending.",
            "This peer read exact source/delta/retained proofs and checked AST/pins; it did not execute the subject or repeat the full/focused suites. Metric passes do not replace source review; private/hostile Python manipulation is not qualified.",
        ],
        subject_runs_by_reviewer=0,test_repeats_by_reviewer=0,reviewed_source_or_harness_or_oracle_edits=0,
        actual_API_calls=0,old_original_or_payload_operations=0,whole_project_accepted=False,
        FFI_registration_proven=False,production_owner_bound=False,originals_authenticated=False,
        real_checkers_bound=False,runtime_authorized=False,profile_qualified=False,verification_complete=False)
    destination=ROOT/"INDEXED-ACCOUNTING-SOURCE-INDEPENDENT-PEER-v3.json"
    with destination.open("x",encoding="utf-8",newline="\n") as stream:json.dump(report,stream,indent=2,sort_keys=True,allow_nan=False);stream.write("\n")
    note="""# Indexed N4 source peer

**CLEAR_SOURCE_PURE_INDEXED_N4_V3.** No material blocker in owner `d8ee1e13…`, ports `8ecabef9…`, controller `16ff0a34…` and final freeze `2be26673…` under the closed private plan/addendum and root source scope.

Raw cells precede guarded cache work. Append/index registration catches failures before entry. Per-call fold watermarks preserve pending versus known0 and idempotence, with original-error quarantine on partial or postcommit failure. Cleanup reads canonical pointers/raw outcomes under the original hardclock. Reporting uses one canonical pass, derives known lower bounds without cache healing, and healthy consistency compares raw truth before its existing gate.

The source has no hidden hot call-list scan, base-list bypass, alternate call ledger or hot report rebuild. Static comparison finds20 changed existing methods, five private helpers and95 unchanged methods; all four controller methods and original16 author assertions are unchanged. Public DATA/oracle/caps remain fixed.

The exact first independent15-method proof `173bfdeb…` passes all48 histories, same8 and pre-code6 in indexed mode:372 strictly validated history snapshots,518 fake dispatches and34 actual in-memory toy module executions. Author12+4 separately pass. Four measured hot windows have zero iteration/membership/slice; Read admission uses index6/len8/one append. Eighteen named reports visit exactly r in the measured worlds, and five quarantine checks preserve facts without I/O/progress. The peer reviewed proofs and source without rerunning tests.

These are N4/209B injected Python results, not empirical full-roster/time/RSS fit. Real first-entry/14-export/FFI/native/physical sink/source/checker/resource/scientific qualification and larger storage/packet admission remain open. The old failed profile/timeout and application0.3.11/defaultv2 are unchanged. Exact pins and limitations: [peer JSON](INDEXED-ACCOUNTING-SOURCE-INDEPENDENT-PEER-v3.json). Root acceptance or any next authority is separate.
"""
    md=ROOT/"INDEXED-ACCOUNTING-SOURCE-INDEPENDENT-PEER-v3.md"
    with md.open("x",encoding="utf-8",newline="\n") as stream:stream.write(note)
    for path in (destination,md):
        b=path.read_bytes();print(json.dumps(dict(path=str(path),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())))


if __name__=="__main__":main()
