"""Exact five-boundary final peer retention. Metadata/AST only; no replay."""
import ast
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXACT = {
    "SHARED-OWNER-INTEGRATION-ACTUAL-EVIDENCE-FREEZE-v2.json": "071cb83afb207185715fe7df3d1403dbad765041c64ae33d8e96c9df56a2a4af",
    "shared_owner_v1.py": "76384e02282b1ce2437b9ff342913297f58ea0858752308724bef912b9e2643b",
    "shared_file_ports_v1.py": "d80f980c771e11ba0116aa3a1a8e526015ce43cafeacc6cf8bc2890f86b4c900",
    "continue_verification_v1.py": "7f52397a8293ae133f019ede1da78881814eb547b026768f072a34e4a4cf8eb2",
    "shared_owner_v2.py": "0ecb8c02e3a8016f2de3a69650b34776de312ffca6f37ded85a31eba9c50c24b",
    "shared_file_ports_v2.py": "a224bfb9e9f33bf2f6b9329f0b337d0076bdab418083d05deb3f59b52722a059",
    "continue_verification_v2.py": "1d05a7398fe215cae987a76ab3960e0dc3730b89fad79caca64c466bac1f4b2f",
    "SHARED-OWNER-INTEGRATION-ACTUAL-PROOF-v2.json": "14d78f96fbdb20e2c40e1884c278704f9da93b02c46cd502df87cf1f756698e3",
    "SHARED-OWNER-FIVE-REGRESSIONS-BEFORE-v2.json": "44eddebb07ef0a1e9a9c463881c67b585ca086febe173e914da1a5e790c63e4e",
    "SHARED-OWNER-AUTHOR-CONTROLS-PURE-PROOF-v2.json": "59240694c2153b4691ad113e69ebd16431511ebed92869e19fc2e793078e301f",
    "SHARED-OWNER-AUTHOR-SUPPLEMENT-PURE-PROOF-v2.json": "6532cf40eb19359c9dfdbcba4257413d9a77a512e84ddd87ac0e010907f5e1cf",
    "SHARED-OWNER-AUTHOR-DELTA-BINDING-v2.json": "266c67860a008181c2b89b33303d0131cba491615f033d47976c52ce0e99f765",
    "SHARED-OWNER-AUTHOR-DELTA-FIRST-ASSERTION-FAILURE-v2.json": "59033886a30955a87c01facffae00dda65cc8008c3ea83b0aa303f88f1ed4fff",
    "SHARED-OWNER-SOURCE-INDEPENDENT-HOLD-v1.json": "66b588bf4f077d7d876be73a6a7db6ded99c1bd7b688f03da1091e8472c72845",
    "SHARED-OWNER-ADJACENT-IDENTITY-RETURN-BEFORE-v1.json": "cdd0c42dc330c4a81feffcca5ab548c244c47f7b88b45e309c2dabd57ae23147",
    "SHARED-OWNER-ADJACENT-IDENTITY-RETURN-AFTER-v2.json": "fa5981c865a4ac3fb5925e8927e637306c53e8d21e35cbda77a444d708257e93",
    "probe_shared_owner_adjacent_identity_return_peer_v2.py": "5b1193f54b75e5d6026edfe4779569e82efdc92323bb1e0a857c3fb44314e8c9",
}
CHANGED = {"Continuation.__init__", "CapturedLoader.load", "SharedOwner.__init__", "SharedOwner._finish", "FilePortView._call"}
ADDED = {"Continuation.__setattr__", "Continuation.owner", "SharedOwner.origin"}


def methods(tree):
    found = {}
    def walk(node, prefix=""):
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found[prefix + item.name] = ast.dump(item, include_attributes=False)
            elif isinstance(item, ast.ClassDef):
                walk(item, prefix + item.name + ".")
    walk(tree)
    return found


def normalize(tree):
    tree = copy.deepcopy(tree)
    def walk(node, prefix=""):
        retained = []
        for item in node.body:
            if isinstance(item, ast.ImportFrom) and item.module == "shared_owner_v2":
                item.module = "shared_owner_v1"
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = prefix + item.name
                if name in ADDED:
                    continue
                if name in CHANGED:
                    item.body = [ast.Pass()]
            elif isinstance(item, ast.ClassDef):
                walk(item, prefix + item.name + ".")
            elif prefix == "Continuation." and isinstance(item, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id == "__slots__" for target in item.targets):
                continue
            retained.append(item)
        node.body = retained
    walk(tree)
    return ast.dump(tree, include_attributes=False)


def main():
    captured, pins = {}, {}
    def pin(name, expected=None):
        if name in pins:
            if expected is not None:
                assert pins[name]["sha256"] == expected
            return pins[name]
        path = ROOT / name
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if expected is not None:
            assert digest == expected, name
        captured[name] = raw
        pins[name] = dict(path=str(path), bytes=len(raw), sha256=digest)
        return pins[name]
    for name, expected in EXACT.items():
        pin(name, expected)
    freeze = json.loads(captured["SHARED-OWNER-INTEGRATION-ACTUAL-EVIDENCE-FREEZE-v2.json"])
    frozen_pins = dict(freeze["pins"])
    frozen_pins["freezer"] = freeze["freezer"]
    for label, expected in frozen_pins.items():
        path = Path(expected["path"])
        assert path.parent == ROOT, label  # only the new phase, no original-source closure expansion
        actual = pin(path.name, expected["sha256"])
        assert actual["bytes"] == expected["bytes"], label
    for name in ("check_shared_owner_author_controls_v1.py", "check_shared_owner_author_controls_v2.py",
                 "check_shared_owner_author_supplement_v1.py", "check_shared_owner_author_supplement_v2.py"):
        pin(name)

    summaries, unchanged, changed, added = [], [], [], []
    for stem in ("shared_owner", "shared_file_ports", "continue_verification"):
        old_name, new_name = stem + "_v1.py", stem + "_v2.py"
        old_tree, new_tree = ast.parse(captured[old_name]), ast.parse(captured[new_name])
        old, new = methods(old_tree), methods(new_tree)
        equal = [name for name in old if name in new and old[name] == new[name]]
        different = [name for name in old if name in new and old[name] != new[name]]
        extra = [name for name in new if name not in old]
        removed = [name for name in old if name not in new]
        assert not removed
        assert normalize(old_tree) == normalize(new_tree), stem
        unchanged.extend(equal); changed.extend(different); added.extend(extra)
        summaries.append(dict(old=old_name, new=new_name, unchanged_methods=len(equal),
                              changed_methods=different, added_methods=extra, removed_methods=removed,
                              all_other_normalized_AST_equal=True))
    assert len(unchanged) == 107 and set(changed) == CHANGED and len(changed) == 5
    assert set(added) == ADDED and len(added) == 3
    old_controls = methods(ast.parse(captured["check_shared_owner_author_controls_v1.py"]))
    new_controls = methods(ast.parse(captured["check_shared_owner_author_controls_v2.py"]))
    controls = [name for name in old_controls if name.startswith("t") and name[1:3].isdigit()]
    assert len(controls) == 12 and all(old_controls[name] == new_controls[name] for name in controls)
    supplement = ("diagnostic_capture", "unreturned_read_unknown", "returned_count_before_late_clock", "returned_checker_before_late_clock")
    old_extra = methods(ast.parse(captured["check_shared_owner_author_supplement_v1.py"]))
    new_extra = methods(ast.parse(captured["check_shared_owner_author_supplement_v2.py"]))
    assert all(old_extra[name] == new_extra[name] for name in supplement)

    complete = json.loads(captured["SHARED-OWNER-INTEGRATION-ACTUAL-PROOF-v2.json"])
    before = json.loads(captured["SHARED-OWNER-FIVE-REGRESSIONS-BEFORE-v2.json"])
    own_after = json.loads(captured["SHARED-OWNER-ADJACENT-IDENTITY-RETURN-AFTER-v2.json"])
    assert complete["status"] == "passed" and complete["methods"] == 9
    assert complete["histories_executed"] == complete["histories_matched"] == 48
    assert complete["snapshot_count"] == 372 and complete["errors"] == complete["failures"] == []
    assert complete["audit_denials"] == [] and all(complete["source_unchanged"].values())
    assert len(complete["focused_observations"]) == 9
    assert before["methods"] == 8 and len(before["failures"]) == 8 and before["errors"] == []
    assert before["histories_executed"] == 0
    assert complete["regressions"] == before["regressions"]
    assert own_after["status"] == "PASSED_SAME_COUNTEREXAMPLES_AFTER"
    assert len(own_after["observations"]) == 2 and all(item["passed"] for item in own_after["observations"])
    assert own_after["denied_operation_attempts"] == []
    for name, count in (("SHARED-OWNER-AUTHOR-CONTROLS-PURE-PROOF-v2.json", 12),
                        ("SHARED-OWNER-AUTHOR-SUPPLEMENT-PURE-PROOF-v2.json", 4)):
        proof = json.loads(captured[name])
        assert proof["status"] == "PASS" and proof["methods"] == count
        assert all(item["passed"] for item in proof["results"])
        assert proof["actual_API_calls"] == 0

    resolved = [
        dict(id="F1", correction="Normal invoke return now stores wrapper_return=True and wrapper_state=returned unconditionally; stopped/original error remains separate.", evidence="Same focused wrapper assertion and unchanged old author control pass."),
        dict(id="F2", correction="Continuation has one private issuer slot, read-only owner property and assignment refusal.", evidence="Distinct genuine-owner assignment regression rejects without mutation or foreign dispatch."),
        dict(id="F3", correction="Four terminal ACK fields project their callback record's acknowledged fact after try_action; no late fact can mint a positive gate.", evidence="Separate candidate/cleanup/receipt/seal hard400 controls retain known ACK, fail completion and record no later sink call."),
        dict(id="F4", correction="SharedOwner stores its original Origin privately and exposes only a getter.", evidence="Independent same counterexample now raises AttributeError, retains100/395/400 and ends REFUSED/pureFalse; other owner has0dispatch/output."),
        dict(id="F5", correction="Compiler name enters known-return order immediately after observed compiler return; postclock/live checks still precede acceptance/cache.", evidence="Independent same counterexample retains returned name with acceptedFalse/notcached/originaldeadline; shared focused test also passes."),
    ]
    report = dict(
        schema_version=1, status="CLEAR_SOURCE_PURE_INJECTED_SHARED_OWNER_V2",
        material_blockers=[], recorded_at_utc="2026-10-29 16:56:25 UTC",
        reviewer="native_039_acceptance_audit",
        source_pins=[pins[name] for name in ("shared_owner_v2.py", "shared_file_ports_v2.py", "continue_verification_v2.py")],
        evidence_freeze=pins["SHARED-OWNER-INTEGRATION-ACTUAL-EVIDENCE-FREEZE-v2.json"],
        prior_hold=pins["SHARED-OWNER-SOURCE-INDEPENDENT-HOLD-v1.json"],
        root_correction_scope=pins["SHARED-OWNER-ROOT-CORRECTION-SCOPE-v2.json"],
        inputs=pins, frozen_phase_pins_rehashed=len(frozen_pins),
        resolved_findings=resolved,
        independent_AST_review=dict(sources=summaries, unchanged_methods=107, changed_methods=5,
                                    added_readonly_methods=3, removed_methods=0,
                                    all_other_module_AST_equal_after_only_version_import_and_authorized_body_slot_normalization=True,
                                    controller_methods_unchanged=4, unchanged_author_test_methods=12,
                                    unchanged_supplement_test_methods=4),
        retained_test_evidence=dict(
            independent_full_suite=dict(proof=pins["SHARED-OWNER-INTEGRATION-ACTUAL-PROOF-v2.json"],
                                        methods=9, frozen_histories=48, histories_matched=48,
                                        strictly_validated_history_snapshots=372,
                                        focused_assertion_methods=8, focused_observation_records=9,
                                        full48_fake_dispatches=complete["actual_full48_fake_dispatches"],
                                        full48_inmemory_marker_execs=complete["actual_full48_marker_execs"],
                                        failures=0, errors=0, audit_denials=0),
            retrospective_same_assertions=dict(proof=pins["SHARED-OWNER-FIVE-REGRESSIONS-BEFORE-v2.json"],
                                               methods=8, failures=8, errors=0,
                                               chronology=before["chronology"]),
            author_unchanged_controls=16,
            reviewer_same_two_after=pins["SHARED-OWNER-ADJACENT-IDENTITY-RETURN-AFTER-v2.json"]),
        provenance_and_limits=[
            "The consolidated shared8 module was authored AFTER v2 source existed and retrospectively run on unchanged v1, then v2. It is not claimed preregistered/pre-fix authored; original functional witnesses and first48 failure preceded fixes.",
            "This reviewer read source/AST and retained proofs, independently reran only the same two previously demonstrated Origin/compiler counterexamples, and did not replay the complete48 or author16 suites.",
            "Fresh captured v2 module maps are explicit, with no old-name module/source-cache fallback. Driver's only logic delta adds a stricter stopped monitor after raise_exception plus normal binding return; frozen e12 expected cases are unchanged.",
            "The proof's372 snapshots are strictly validated full-history captures; its9 focused observation records are separate. Counts are not claimed disjoint tests or real system measurements.",
            "The 141B marker modules really execute only inside the synthetic suite's closed in-memory compiler. Fixture-only branded factories/checkers remain separate from those toy helper modules. The late compiler returns an opaque value and earns no source acceptance.",
            "Source public read-only property tests concern ordinary assignment, not hostile private/object.__setattr__ manipulation.",
            "Eight-record output ceiling is slack around five named fictional kinds. Serialized seven-key rows/tip prove retained synthetic ACK-prefix bytes, not persisted hash-chain/native journal format or physical durability.",
            "Publication8193/repeated-kind refusal is not isolated exercised coverage; all-produced-packet cap/once-kind checks remain structural/SinkSpy only. Compound admission controls do not establish isolated per-cap guards.",
            "N4 scaling/performance, full raw-memory fit, a full original roster and real first-clock/bootstrap/FFI/checker qualification remain deferred, not silently upgraded by this bounded prototype clearance.",
        ],
        schema_or_fixture_changes_by_reviewer=0, subject_source_changes_by_reviewer=0,
        whole_project_accepted=False, actual_API_calls=0, old_original_or_payload_operations=0,
        FFI_registration_proven=False, originals_authenticated=False,
        production_owner_bound=False, real_checkers_bound=False,
        runtime_authorized=False, profile_qualified=False, verification_complete=False,
    )
    destination = ROOT / "SHARED-OWNER-SOURCE-INDEPENDENT-PEER-v2.json"
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    note = """# Shared-owner corrected source peer

**CLEAR_SOURCE_PURE_INJECTED_SHARED_OWNER_V2.** No material blocker remains in the exact five-boundary correction of owner `0ecb8c02…`, ports `a224bfb9…` and controller `1d05a739…`, bound by final evidence freeze `071cb83a…`. The historical first-source HOLD remains preserved.

The changes preserve a normally returned wrapper independently from its later stop, make the continuation issuer and original Origin read-only under ordinary assignment, retain all four known terminal callback ACK facts despite late failure, and record known compiler returns before acceptance checks. Late facts never grant a positive gate or cache acceptance.

Independent AST comparison finds exactly five changed existing methods, three added read-only methods and107 unchanged methods. All other module ASTs match after only the authorized bodies/slot and version-import normalization; all four controller methods are unchanged. The original12 author controls and4 supplemental tests have identical assertion ASTs and pass.

The retained full proof `14d78f96…` passes all48 frozen histories plus the same8 focused assertions, with372 strictly validated full-history snapshots and no failures/errors/audit denials. Separate focused records cover each late publication kind without post-hard-cutoff sink calls. The same8 assertions fail on preserved v1 (`44eddebb…`,8failures/0errors); their consolidated module was authored after v2 and replayed retrospectively, not claimed preregistered. Original functional witnesses preceded the fixes. The unchanged frozen oracle remains `e12d6485…`.

This reviewer independently reran only its same two Origin/compiler counterexamples. [AFTER evidence](SHARED-OWNER-ADJACENT-IDENTITY-RETURN-AFTER-v2.json) retains the original100/395/400 clock and refuses completion; it also preserves a known late compiler name without accepting/caching it. No I/O attempt occurred under denial hooks. The complete suites were reviewed through their exact retained proof/dependency bindings, not repeated.

Clearance is limited to the injected Python prototype. The fictional sink is not physical output durability; the retained seven-key ACK-prefix journal is not a native persisted hash chain. Fixture-only factory/checker brands do not establish real source binding. Publication8193/repeated-kind refusal remains unexercised in isolation, and compound cap controls do not establish isolated cap guards. N4 performance, full raw-memory fit, real first entry/FFI/originals/production checkers and full-profile qualification remain deferred. All real qualification flags stay false.

Exact source/proof/fixture pins, five resolved findings and limits are in the [peer JSON](SHARED-OWNER-SOURCE-INDEPENDENT-PEER-v2.json). Root acceptance and any later execution authority are separate.
"""
    markdown = ROOT / "SHARED-OWNER-SOURCE-INDEPENDENT-PEER-v2.md"
    with markdown.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(note)
    for path in (destination, markdown):
        raw = path.read_bytes()
        print(json.dumps(dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())))


if __name__ == "__main__":
    main()
