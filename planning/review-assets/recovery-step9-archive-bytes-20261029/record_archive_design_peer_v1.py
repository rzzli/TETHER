"""Format/design review only. Hashes new design metadata, never old originals."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent


def pin(name):
    path = HERE / name
    raw = path.read_bytes()
    return dict(path=str(path.absolute()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    contract_pin = pin("CAPTURED-NATIVE-ARCHIVE-CONTRACT-v2.json")
    assert contract_pin["sha256"] == "e77f8510d7aa41ea2fdbb7abdc8e9b1337f3abb846705df69414af2a018161cb"
    proposal = json.loads((HERE / "CAPTURED-NATIVE-ARCHIVE-CONTRACT-v2.json").read_text(encoding="utf-8"))
    roots = proposal["relative_locator_policy"]["root_files"]
    children = proposal["relative_locator_policy"]["child_files"]
    assert "journal.jsonl" in roots and "parent-reservation.json" not in roots
    assert "execution/journal.jsonl" not in roots + children
    assert proposal["authorization_now"]["fixture_or_checker_code"] is False
    finding = pin("CAPTURED-NATIVE-ARCHIVE-DESIGN-FINDING-v1.json")
    assert finding["sha256"].startswith("310eecb6")
    record = dict(schema_version=1, recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status="REVISION_REQUIRED_SOURCE_LOCATORS_BEFORE_FIXTURE_OR_CHECKER_STAGE",
        contract=contract_pin, predecessor=pin("CAPTURED-NATIVE-ARCHIVE-CONTRACT-v1.json"),
        format_map=pin("CAPTURED-NATIVE-ARCHIVE-FORMAT-MAP-v1.md"), prior_late_failure_finding=finding,
        recorder=pin(Path(__file__).name),
        material_findings=[dict(id="source_locator_roster", component="relative_locator_policy and early receipt required membership",
            problem="Root journal.jsonl is allowed while execution/journal.jsonl and root parent-reservation.json are missing. A normal captured source archive would therefore be rejected or fixtures would encode the wrong emitter format.",
            source_basis=["reserve_parent_journal writes output/parent-reservation.json before journal construction",
                          "reserve_parent_journal constructs RunJournal(output/execution,kind=build)",
                          "execute scans supplied source files into receipt/terminal maps without moving those paths"],
            required="Use execution/journal.jsonl, remove unsupported root journal.jsonl, admit parent-reservation.json and declare its exact owner_pid/created_at_utc/status schema. Positive complete captured membership requires the reservation; early failure/malformed reservation remains incomplete or negative as appropriate.")],
        prior_correction_assessment="The explicit exception-variant late supplement can be absent from an older terminal map and must remain negative/incomplete. It cannot prove successful terminal return or chronology. Normal late markers must remain pinned/mapped; arbitrary other omissions are not excused.",
        source_phase_checks=[
            "Terminal-publication-error and journal-close-error branches precede the sealer, so a retained normal terminal map includes their supplied bytes; they may be absent from an older receipt.",
            "An after-seal marker pins the supplied terminal bytes, remains outside the earlier map and vetoes its on-disk positive literal.",
            "A source-negative archive can have consistent captured byte edges; positive outcome is independently vetoed by filename presence, malformed marker, primary/secondary failure, partial child result or missing terminal evidence.",
            "Direct expected protocol/authority pins plus exact effective-protocol bytes are stronger than equality of two untrusted copies, but remain unproven original context here.",
            "Static/dynamic/payload descriptor comparisons and bounded direct DAG reject declared inconsistencies without opening or recursively expanding named leaves."],
        mandatory_literal_fixture_closure=[
            "Exact corrected locator roster and reservation schema, canonical parent JSON and intentionally ordered child markers",
            "Normal late marker versus post-terminal exception supplement; positive early receipt followed by later root failure; after-seal failure; missing seal; map self/future/dangling/cross-root edges",
            "Malformed root and child failure filenames veto before parsing can disable them; authoritativeFalse/ready flags are malformed and never clear a veto",
            "Final/partial child conflict; child failure alongside final result; missing attempt; no result-body interpretation by this archive component",
            "Strict bool-versus-integer including byte/schema/elapsed fields, duplicate/nonfinite/nonscalar JSON, finite file/byte/node/depth/edge caps and deadline propagation",
            "Explicit output status/error behavior for malformed versus incomplete capture; no normal complete-terminal claim for exception-supplement branch",
            "Global direct-pin identity consistency, exact static/dynamic/payload/current-protocol/output collisions, and explicit derivation/delegation of all nine argv references"],
        result_scope_confirmed=["profile_qualifiedFalse", "originals_authenticatedFalse", "actual_directory_completeFalse", "source_qualifiedFalse",
                                "Captured-universe equality never proves actual directory absence; opaque result/journal/capture meanings remain separate gates"],
        no_other_confirmed_material_blocker=True,
        source_read_scope=dict(retained_source_text_only=[
            dict(path="../recovery-step9-native-recognition-20261028/detached_parent_launch_draft_v1.py", symbol="reserve_parent_journal"),
            dict(path="../recovery-step9-native-recognition-20261028/run_recognition_observation_v7.py", symbols=["configuration/argv role format", "execute publication tail"])],
            original_source_hashes=0, fresh_source_identity_or_closure_qualification=False,
            explanation="Narrow source text establishes format references only; no retained identity was freshly authenticated."),
        activity=dict(old_actual_archive_replays=0, payload_CPU_GGUF_pack_operations=0, source_import_or_helper_execution=0,
                      SDK_OS_target_compiler_calls=0, fixture_or_checker_implementation=False),
        execution_authorized=False, implementation_authorized=False,
        current_or_future_profile_qualified=False, previous_negative_and_external_timeout_unchanged=True)
    raw = (json.dumps(record, indent=2, allow_nan=False)+"\n").encode("utf-8")
    path = HERE / "CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-DESIGN-REVIEW-v1.json"
    with path.open("xb") as stream: stream.write(raw)
    print(json.dumps(pin(path.name)))


if __name__ == "__main__":
    main()
