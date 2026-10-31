"""Finite literal-fixture/source-delta inspection; not the archive checker."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE / "CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-DESIGN-REVIEW-v3.json"
NOTE = HERE / "CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-DESIGN-REVIEW-v3.md"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}


def load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def files(case):
    return {r["locator"]: bytes.fromhex(r["raw_hex"]) for r in case["captured"]["run_files"]}


def main():
    assert not REPORT.exists() and not NOTE.exists()
    names = ["CAPTURED-NATIVE-ARCHIVE-CONTRACT-v3.json", "CAPTURED-NATIVE-ARCHIVE-CONTRACT-FREEZE-v3.json",
             "CAPTURED-NATIVE-ARCHIVE-FIXTURES-v1.json", "CAPTURED-NATIVE-ARCHIVE-FIXTURES-v2.json",
             "CAPTURED-NATIVE-ARCHIVE-FIXTURES-v3.json", "CAPTURED-NATIVE-ARCHIVE-FIXTURE-FREEZE-v3.json",
             "CAPTURED-NATIVE-ARCHIVE-FIXTURE-FRAMING-v1.json", "CAPTURED-NATIVE-ARCHIVE-FIXTURE-FRAMING-PROOF-v3.json",
             "CAPTURED-NATIVE-ARCHIVE-FIXTURE-PEER-FINDINGS-v2.json", "author_captured_archive_fixtures_v3.py",
             "retain_archive_fixture_framing_v3.py", "CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-DESIGN-REVIEW-v1.json"]
    before = {n: pin(HERE / n) for n in names}
    contract = load(names[0]); fixture = load(names[4]); freeze = load(names[5]); proof = load(names[7])
    previous = {c["id"]: c for c in load(names[3])["cases"]}
    cases = {c["id"]: c for c in fixture["cases"]}
    assert before[names[0]]["sha256"] == "ce077d5bfd2e12bd5de7a84d17094572a15286e0cb44bdc224513206f305e3d2"
    assert before[names[4]]["sha256"] == "3e75447d4d3a01c56833d089bf23dab52e5e53bc49a9ea33e9de689eef9b5dcd"
    assert before[names[5]]["sha256"] == "7663f2edfff3d0c4365bbe9d4336895b56f2e5b5001bb69717eeeab06bfd96b9"
    assert before[names[7]]["sha256"] == "1f1ba32f2cb13fbffa9056c07431a4e5076b758e6be04bb12c427ae621922b7e"
    for key in ("contract", "contract_freeze", "framing", "author", "fixtures", "predecessor_fixtures", "fixture_finding", "independent_fixture_findings"):
        assert pin(Path(freeze[key]["path"])) == freeze[key]
    assert proof["status"] == "fixture_framing_and_narrow_source_delta_passed" and proof["methods"] == 5
    assert proof["errors"] == proof["failures"] == 0
    assert proof["expected_graph_results_are_authored_not_observed"] is True
    assert proof["actual_archive_graph_checks"] == 0

    checks = []
    def checked(identity, evidence):
        checks.append({"id": identity, "status": "passed", "evidence": evidence})

    locators = contract["relative_locator_policy"]
    assert "parent-reservation.json" in locators["root_files"] and "journal.jsonl" not in locators["root_files"]
    assert locators["execution_files"] == ["execution/journal.jsonl"]
    assert contract["source_documents"]["parent_reservation"]["exact_keys"] == ["owner_pid", "created_at_utc", "status"]
    assert contract["authorization_now"]["literal_fixture_framing_preparation"] is True
    checked("corrected_v3_contract_locators", "Root reservation and nested execution journal are explicitly admitted; root journal is unsupported. First/second header references and early incomplete branches are explicit. No full chain or real owner authentication is claimed.")

    assert len(cases) == len(fixture["cases"]) == 32 and list(cases) == list(previous)
    maximum = 0; instances = 0
    for identity, case in cases.items():
        assert case["bindings"] == previous[identity]["bindings"]
        assert case["expected_projection"] == previous[identity]["expected_projection"]
        capture = case["captured"]; old = previous[identity]["captured"]
        assert capture["protocol_hex"] == old["protocol_hex"] and capture["authority_hex"] == old["authority_hex"]
        raw = files(case); prior = files(previous[identity]); assert raw.keys() == prior.keys()
        assert len(raw) == len(capture["run_files"]) <= 64
        assert all(bytes.fromhex(x["raw_hex"]).hex() == x["raw_hex"] for x in capture["run_files"])
        total = len(bytes.fromhex(capture["protocol_hex"])) + len(bytes.fromhex(capture["authority_hex"])) + sum(map(len, raw.values()))
        maximum = max(maximum, total); instances += len(raw); assert total < 33554432
        allowed = {"post-lease-cleanup.json", "terminal-seal.json", "late-failure.json", "after-seal-failure.json"}
        if identity == "publication_after_receipt": allowed |= {"failure.json", "terminal-publication-error.json"}
        assert {n for n in raw if raw[n] != prior[n]} <= allowed
        for outcome in json.loads(raw["post-lease-cleanup.json"])["outcomes"]: assert outcome["validation"] == "passed"
        assert all(case["expected_projection"][k] is False for k in ("profile_qualified", "originals_authenticated", "actual_directory_complete", "source_qualified"))
    checked("encoding_predecessor_preservation_and_finite_roster", "32 captures retain unchanged bindings/protocol/authority/expected projections and only approved run-file deltas. Every capture remains bounded; raw lower-hex encoding and four negative qualification flags checked. Expected graph statuses were not executed as a checker.")

    early = files(cases["early_initialization"])
    assert cases["early_initialization"] == previous["early_initialization"]
    assert set(early) == {"parent-reservation.json", "failure.json", "parent-report.json", "receipt.json", "post-lease-cleanup.json", "terminal-seal.json"}
    p = json.loads(early["parent-report.json"]); cleanup = json.loads(early["post-lease-cleanup.json"])
    assert "returncode" not in p and "reaped" not in p and p["call_return_observed"] is False
    assert cleanup["outcomes"] == cleanup["close_errors"] == []
    assert set(json.loads(early["receipt.json"])["outputs"]) == {"parent-reservation.json", "failure.json", "parent-report.json"}
    assert set(json.loads(early["terminal-seal.json"])["outputs"]) == set(early)-{"terminal-seal.json"}
    checked("early_initialization_absence_is_unknown", "Byte-identical corrected early branch has six root files, no API/Owner lease outcomes, no journal/protocol/streams/child nodes and no returncode/reaped fields. Its authored disposition is negative and incomplete.")

    publication = files(cases["publication_after_receipt"]); prior = files(previous["publication_after_receipt"])
    assert publication["parent-report.json"] == prior["parent-report.json"] and publication["receipt.json"] == prior["receipt.json"]
    error = json.loads(publication["terminal-publication-error.json"])
    for entry in [json.loads(publication["failure.json"]), error["publication_error"], error["primary_failure"], error["finalization_errors"][0], json.loads(publication["post-lease-cleanup.json"])["primary_failure"]]:
        assert entry["phase"] == "terminal_publication"
    assert "failure.json" not in json.loads(publication["receipt.json"])["outputs"]
    assert "failure.json" in json.loads(publication["terminal-seal.json"])["outputs"]
    checked("publication_primary_phase_and_earlier_bytes", "New publication-stop details carry the source phase in marker, publication/primary/error list and cleanup. Earlier positive report and receipt bytes remain unchanged; the later marker is absent from old receipt and present in terminal map.")

    positive = cases["complete_positive_captured_graph"]; good = files(positive)
    protocol_raw = bytes.fromhex(positive["captured"]["protocol_hex"]); config = json.loads(protocol_raw)
    reservation = json.loads(good["parent-reservation.json"])
    headers = [json.loads(row) for row in good["execution/journal.jsonl"].splitlines()]
    assert set(reservation) == {"owner_pid", "created_at_utc", "status"}
    assert type(reservation["owner_pid"]) is int and reservation["owner_pid"] == headers[0]["details"]["owner_pid"]
    assert headers[0]["event"] == "build_reserved" and headers[0]["sequence"] == 0 and headers[0]["previous_sha256"] is None
    assert headers[1]["event"] == "detached_recognition_attempt_reserved" and headers[1]["sequence"] == 1
    assert headers[1]["previous_sha256"] == headers[0]["sha256"]
    assert headers[1]["details"] == {"protocol_sha256":sha(protocol_raw), "limits": config["limits"]}
    for row in headers: assert sha(canonical({k:v for k,v in row.items() if k != "sha256"})) == row["sha256"]
    assert good["effective-protocol.json"] == protocol_raw
    for name in ("receipt.json", "terminal-seal.json"):
        declared = json.loads(good[name])["outputs"]
        for locator, value in declared.items(): assert value == {"bytes":len(good[locator]), "sha256":sha(good[locator])}
    assert set(json.loads(good["terminal-seal.json"])["outputs"]) == set(good)-{"terminal-seal.json"}
    checked("literal_normal_reservation_headers_and_selected_map_edges", "Normal literal reservation owner, both local canonical header hashes, captured protocol/limit references and supplied receipt/terminal byte references agree. This finite inspection is not a general archive checker, full journal chain or actual directory scan.")

    for index in range(9):
        c = cases[f"argv_{index}"]; mutated = json.loads(bytes.fromhex(c["captured"]["protocol_hex"]))["argv"]
        assert len(mutated) == len(config["argv"]) == 9
        assert [i for i,(a,b) in enumerate(zip(mutated,config["argv"])) if a != b] == [index]
    after = files(cases["after_seal"]); exception = files(cases["exception_after_terminal"])
    assert "after-seal-failure.json" not in json.loads(after["terminal-seal.json"])["outputs"]
    assert "late-failure.json" not in json.loads(exception["terminal-seal.json"])["outputs"]
    assert json.loads(exception["late-failure.json"])["phase"] == "post_lease_cleanup_or_terminal_sealing"
    assert cases["exception_after_terminal"]["expected_projection"]["captured_graph_status"] == "incomplete_captured_graph"
    checked("nine_argument_mutations_and_post_terminal_supplements", "All nine argument fixtures mutate exactly one index. After-seal and exception-late supplements retain their older-map exclusion and negative/incomplete authored meaning; no status rewrite repairs the earlier evidence.")

    assert before == {n:pin(HERE/n) for n in names}
    result = dict(schema_version=1, recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        status="CLEAR_CORRECTED_DESIGN_AND_LITERAL_SOURCE_FIXTURES_ONLY", reviewer="/root/os_accounting_peer",
        inputs=before, review_script=pin(Path(__file__)), checks=checks, material_findings=[],
        resolved_findings=["Prior root reservation/journal locator omission", "Early initialization returncode/reaped and fabricated lease outcome", "Successful lease validation literal", "Terminal publication phase preservation"],
        preservation="Prior contract/fixture v1-v2 and HOLD/finding reports remain unchanged.",
        counts=dict(captures=32, argv_derivations=9, encoded_run_file_instances=instances, maximum_decoded_capture_bytes=maximum),
        scope="Finite literal encoding/source-format/DAG-design review. Expected graph results remain authored, not results from an archive checker.",
        source_read_scope="Targeted retained execute/read_lease/sealer text only, not original-source hashes/imports/closure qualification.",
        actual_archive_checker_executions=0, old_run_replays=0, original_payload_operations=0,
        SDK_OS_native_compiler_operations=0, profile_qualified=False, source_qualified=False,
        originals_authenticated=False, actual_directory_complete=False, checker_implementation_authorized_by_review=False)
    with REPORT.open("x",encoding="utf-8") as out: json.dump(result,out,sort_keys=True,indent=2);out.write("\n")
    with NOTE.open("x",encoding="utf-8") as out:
        out.write("""# Captured archive: corrected design and literal fixture review

CLEAR for contract v3 and literal fixtures v3 only. The root reservation and nested execution journal fix resolves the prior design HOLD. Exact fixture deltas preserve the corrected early branch: no child return/reaping fields, no API/lease outcomes and no fabricated journal, streams or child artifacts.

The two later source-shape findings are corrected: successful lease validation is `passed`, and new terminal-publication failures retain their phase while the earlier positive report/receipt bytes remain unchanged. Six bounded independent inspection groups cover the 32 literal captures, all nine argument mutations, local reservation/header bindings, selected byte-map edges and later negative supplements. No further material issue was found in this scope.

Expected graph classifications remain authored data. No archive checker exists or was executed; this is not actual old-run verification, original-source qualification, a directory census, resource evidence, native execution or profile success. Checker implementation still requires the root's separate decision.
""")
    print(json.dumps({"report":pin(REPORT),"note":pin(NOTE),"check_groups":len(checks)}))


if __name__ == "__main__":
    main()
