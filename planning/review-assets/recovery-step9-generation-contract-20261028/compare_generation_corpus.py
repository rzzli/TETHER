"""One pinned schema batch, then strict/pure comparisons of frozen raw bytes."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))
from asof.serde import ContractError, canonical, read_json
from asof.study.interpretation_generation import validate_output
from finite_gbnf_oracle import parse, accepts

CACHE = ROOT / "data/cache/r09-generation-corpus-extension-v1-20261028"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name, data):
    with (CACHE / name).open("xb") as stream:
        stream.write(canonical(data))


manifest_path = CACHE / "FROZEN-INPUTS.json"
manifest = json.loads(manifest_path.read_bytes())
for name, digest in {**manifest["files"], **manifest["source_pins"]}.items():
    assert sha(ROOT / name) == digest, name
old_path = ROOT / manifest["original_corpus"]["path"]
assert sha(old_path) == manifest["original_corpus"]["sha256"]
oracle = manifest["oracle"]
assert sha(oracle["executable"]) == oracle["executable_sha256"]
assert sha(oracle["script"]) == oracle["script_sha256"]
for item in oracle["dependencies"]["assemblies"]:
    assert sha(item["path"]) == item["sha256"]
argv = [oracle["executable"], "-NoProfile", "-NonInteractive", "-File", oracle["script"], str(CACHE / "oracle-cases.json")]
plan = dict(schema_version=1, role="single_local_schema_oracle_then_pure_comparison",
            input_manifest_sha256=sha(manifest_path), runner_sha256=sha(__file__),
            argv=argv, timeout_seconds=120, maximum_schema_children=1,
            no_retry=True, native_grammar_calls=0, vocabulary_loads=0, model_calls=0,
            servers=0, provider_cost_usd=0, protocol_sha256=sha(HERE / "CORPUS-EXTENSION-PROTOCOL.md"))
write("ORACLE-EXECUTION-PLAN.json", plan)
state = dict(attempted_children=0, denied_events=[])


def audit(event, args):
    if event in ("socket.connect", "socket.getaddrinfo", "socket.__new__", "os.system"):
        state["denied_events"].append(event)
        raise RuntimeError("No Python network/system execution permitted")
    if event == "subprocess.Popen":
        expected = subprocess.list2cmdline(argv) if isinstance(args[1], str) else argv
        if state["attempted_children"] != 0 or args[1] != expected:
            state["denied_events"].append("subprocess.Popen")
            raise RuntimeError("Only one exact pinned local schema-oracle child permitted")
        state["attempted_children"] += 1


sys.addaudithook(audit)
started = time.perf_counter()
schema_started = time.perf_counter()
terminal = dict(schema_version=1, status="running", plan_sha256=sha(CACHE / "ORACLE-EXECUTION-PLAN.json"))
try:
    try:
        child = subprocess.run(argv, capture_output=True, stdin=subprocess.DEVNULL, timeout=120)
        stdout, stderr, returncode, timeout = child.stdout, child.stderr, child.returncode, False
    except subprocess.TimeoutExpired as error:
        stdout, stderr, returncode, timeout = error.stdout or b"", error.stderr or b"", None, True
    (CACHE / "schema-oracle-stdout.json").write_bytes(stdout)
    (CACHE / "schema-oracle-stderr.bin").write_bytes(stderr)
    schema_execution = dict(returncode=returncode, timed_out=timeout,
                            seconds=time.perf_counter()-schema_started,
                            stdout_bytes=len(stdout), stdout_sha256=sha(CACHE / "schema-oracle-stdout.json"),
                            stderr_bytes=len(stderr), stderr_sha256=sha(CACHE / "schema-oracle-stderr.bin"), guards=state)
    write("SCHEMA-EXECUTION.json", schema_execution)
    assert returncode == 0 and not timeout and len(stdout) <= 1048576 and len(stderr) <= 1048576
    observed_schema = json.loads(stdout)
    assert observed_schema["powershell_version"] == "7.6.5"
    oracle_inputs = json.loads((CACHE / "oracle-cases.json").read_bytes())
    schema_by_id = {row["id"]: row["accepted"] for row in observed_schema["results"]}
    assert len(schema_by_id) == len(oracle_inputs) == len(observed_schema["results"])
    assert set(schema_by_id) == {row["id"] for row in oracle_inputs}
    assert all(type(value) is bool for value in schema_by_id.values())
    extension = json.loads((CACHE / "extension-cases.json").read_bytes())
    old = json.loads(old_path.read_bytes())
    old_schema = json.loads((ROOT / "data/cache/r09-native-grammar-corpus-20261028/oracle-stdout.json").read_bytes())
    original_schema_by_id = {row["id"]: row["accepted"] for row in old_schema["results"]}
    contexts = {}
    for name, paths in manifest["variants"].items():
        request = read_json(ROOT / paths["request.json"]["path"])
        prepared = read_json(ROOT / paths["prepared.json"]["path"])
        grammar = (ROOT / paths["grammar.gbnf"]["path"]).read_bytes().decode("utf-8")
        contexts[name] = (request, prepared["payload"], parse(grammar))
    cases = []
    for row in old:
        cases.append(dict(id="legacy/" + row["id"], variant="synthetic-context", raw=row["document_json"].encode("utf-8"),
                          source="unchanged_original_109", authored_generation_membership=None,
                          expected_strict=row["python_accepted"], expected_schema=original_schema_by_id[row["id"]],
                          explanation="Original corpus was not authored for the v3 serialization domain; observed pure membership is separately recorded."))
    for row in extension:
        raw = (ROOT / row["document_path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row["document_sha256"]
        authored = row["authored"]
        cases.append(dict(id="extension/" + row["id"], variant=row["variant"], raw=raw,
                          source="generation_domain_extension_v1", document_path=row["document_path"],
                          authored_generation_membership=authored["generation_membership"],
                          expected_strict=authored["strict_accepted"], expected_schema=authored["schema_accepted"],
                          explanation=authored["rationale"]))
    results, future, mismatches = [], [], []
    progress = CACHE / "comparison-progress.jsonl"
    with progress.open("x", encoding="utf-8") as stream:
        for index, row in enumerate(cases):
            stage_started = time.perf_counter()
            stream.write(json.dumps(dict(event="case_started", index=index, id=row["id"])) + "\n")
            stream.flush()
            request, payload, rules = contexts[row["variant"]]
            strict_error = None
            try:
                validate_output(request, payload, row["raw"])
                strict = True
            except ContractError as error:
                strict, strict_error = False, str(error)
            grammar = accepts(rules, "root", row["raw"].decode("utf-8"))
            schema = schema_by_id[row["id"]]
            observations = dict(schema_accepted=schema, strict_accepted=strict, pure_grammar_membership=grammar)
            checks = dict(strict_matches_expected=strict == row["expected_strict"])
            if type(row["expected_schema"]) is bool:
                checks["schema_matches_expected"] = schema == row["expected_schema"]
            if type(row["authored_generation_membership"]) is bool:
                checks["pure_membership_matches_authored"] = grammar == row["authored_generation_membership"]
            if not all(checks.values()):
                mismatches.append(dict(id=row["id"], checks=checks, observations=observations))
            result = dict(id=row["id"], source=row["source"], variant=row["variant"],
                          document_sha256=hashlib.sha256(row["raw"]).hexdigest(), document_bytes=len(row["raw"]),
                          authored_expectations=dict(schema_accepted=row["expected_schema"], strict_accepted=row["expected_strict"],
                                                     generation_membership=row["authored_generation_membership"], rationale=row["explanation"]),
                          observations=observations, checks=checks, strict_error=strict_error,
                          elapsed_seconds=time.perf_counter()-stage_started)
            results.append(result)
            future.append(dict(id=row["id"], source=row["source"], variant=row["variant"],
                               document_path=row.get("document_path"),
                               original_corpus_path=manifest["original_corpus"]["path"] if row["source"] == "unchanged_original_109" else None,
                               original_corpus_case_id=row["id"][7:] if row["source"] == "unchanged_original_109" else None,
                               document_sha256=result["document_sha256"], document_bytes=result["document_bytes"],
                               authored_generation_membership=row["authored_generation_membership"],
                               observed_pure_membership=grammar, observed_schema_accepted=schema,
                               observed_strict_accepted=strict))
            stream.write(json.dumps(dict(event="case_finished", index=index, id=row["id"],
                                         seconds=result["elapsed_seconds"], checks=checks)) + "\n")
            stream.flush()
    assert state["attempted_children"] == 1 and not state["denied_events"]
    for name, digest in {**manifest["files"], **manifest["source_pins"]}.items():
        assert sha(ROOT / name) == digest, name
    assert sha(old_path) == manifest["original_corpus"]["sha256"]
    native = dict(schema_version=1, role="future_native_corpus_reference_only", identity="generation-domain-extension-v1-with-original109",
                  execution_authorized=False, native_conformance="unverified", vocabulary_eog="not tested", science="not attempted",
                  original_corpus=manifest["original_corpus"], frozen_input_manifest_sha256=sha(manifest_path),
                  variants=manifest["variants"], cases=future,
                  limitation="Pure-interpreter observations are comparison evidence, not actual native gold labels or permission to load a runtime/model.")
    write("FUTURE-NATIVE-CORPUS-MANIFEST.json", native)
    write("COMPARISON-RESULTS.json", results)
    report = dict(schema_version=1, status="passed" if not mismatches else "expectation_mismatch_stop",
                  role="schema_strict_and_pure_generation_domain_comparison_not_native_qualification",
                  original_cases=109, extension_cases=len(extension), total_cases=len(results),
                  frozen_input_manifest_sha256=sha(manifest_path), plan_sha256=sha(CACHE / "ORACLE-EXECUTION-PLAN.json"),
                  results_sha256=sha(CACHE / "COMPARISON-RESULTS.json"), future_native_manifest_sha256=sha(CACHE / "FUTURE-NATIVE-CORPUS-MANIFEST.json"),
                  schema_execution=schema_execution, source_pins=manifest["source_pins"], original_corpus_unchanged=True,
                  mismatches=mismatches, seconds=time.perf_counter()-started,
                  accepted_counts={key: sum(row["observations"][key] for row in results) for key in ("schema_accepted", "strict_accepted", "pure_grammar_membership")},
                  strict_valid_outside_generation_domain=[row["id"] for row in results if row["observations"]["strict_accepted"] and not row["observations"]["pure_grammar_membership"]],
                  grammar_valid_strict_rejected=[row["id"] for row in results if row["observations"]["pure_grammar_membership"] and not row["observations"]["strict_accepted"]],
                  parse_edge_observations=[row for row in results if row["authored_expectations"]["schema_accepted"] == "implementation_dependent_parse"],
                  native_grammar_calls=0, vocabulary_loads=0, model_loads=0, inference_calls=0, servers=0, provider_cost_usd=0,
                  limitations=["Independent restricted finite-GBNF interpreter, not actual DLL parsing or tokenizer/EOG evidence.",
                               "Authored v3 membership labels apply to the separate extension; original109 receive observed replay membership without rewritten documents.",
                               "No scientific validation or controller authorization follows from these comparisons."])
    write("CORPUS-COMPARISON.json", report)
    terminal.update(status=report["status"], report_sha256=sha(CACHE / "CORPUS-COMPARISON.json"), seconds=time.perf_counter()-started)
    assert not mismatches, mismatches
    print(json.dumps({key: report[key] for key in ("status", "original_cases", "extension_cases", "total_cases", "accepted_counts", "seconds", "mismatches")}))
except BaseException as error:
    terminal.update(status="failed", error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc(), seconds=time.perf_counter()-started, guards=state)
    raise
finally:
    write("COMPARISON-TERMINAL.json", terminal)
