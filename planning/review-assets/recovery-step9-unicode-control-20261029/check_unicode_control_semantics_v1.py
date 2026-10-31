"""Independent postfreeze rawbyte/JSON/actual-v3 checks; no tokenizer/runtime.

Generation membership is a reviewed source-rule expectation, not inferred from
the semantic validator or claimed as a native grammar observation.
"""
import hashlib
from importlib import metadata
import json
from pathlib import Path
import re
import sys
import time

HERE = Path(__file__).resolve().parent
FREEZE = HERE / "UNICODE-CONTROL-FIXTURE-FREEZE-v1.json"
FREEZE_SHA = "e6e8419c0ad37db007263de0a57e0ce66a20f7481f35686427076ea36c7106b3"
CORPUS_SHA = "13e2c2f2900802729c0d39fa9b7851c56ab3db6afdc45c4b15c2f7f80bd6523c"
STAGES_SHA = "ad688168a366d5e95413ec69731d030c54431663e6574fb93445ced2b580413a"
REPORT = HERE / "UNICODE-CONTROL-INDEPENDENT-SEMANTIC-PROOF-v1.json"
BUDGET = 20
DENIALS = []


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def exact(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(exact(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(exact(a, b) for a, b in zip(left, right))
    return left == right


def all_scalars(value):
    if isinstance(value, str):
        return all(not 0xD800 <= ord(char) <= 0xDFFF for char in value)
    if isinstance(value, list):
        return all(all_scalars(item) for item in value)
    if isinstance(value, dict):
        return all(all_scalars(key) and all_scalars(item) for key, item in value.items())
    return True


def wire_statistics(raw):
    result = dict(raw_nonASCII_bytes=sum(value > 127 for value in raw), ASCII_only=not any(value > 127 for value in raw),
                  Unicode_escape_spellings=len(re.findall(rb"\\u[0-9a-fA-F]{4}", raw)),
                  short_JSON_escape_spellings=len(re.findall(rb"\\[nrtbf]", raw)))
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeError:
        result.update(UTF8_valid=False, raw_scalar_width_counts=None,
                      raw_scalar_width_counts_null_reason="Invalid UTF8 has no complete strict-scalar segmentation.")
    else:
        widths = {str(width): 0 for width in range(1, 5)}
        for char in text:
            point = ord(char)
            width = 1 if point < 0x80 else 2 if point < 0x800 else 3 if point < 0x10000 else 4
            widths[str(width)] += 1
        require(sum(int(width) * count for width, count in widths.items()) == len(raw), "Strict scalar byte segmentation changed")
        result.update(UTF8_valid=True, raw_scalar_width_counts=widths, raw_scalar_width_counts_null_reason=None)
    return result


def guard(event, args):
    if event.startswith(("socket.", "subprocess.", "ctypes.dlopen", "os.system")):
        DENIALS.append(event)
        raise RuntimeError("No target/native/process/network in semantic review")
    if event == "open" and args and isinstance(args[0], (str, bytes)):
        value = str(args[0]).lower().replace("/", "\\")
        if value.startswith("e:") or value.endswith((".gguf", ".dll", ".pyd", ".pack")) or "\\data\\benchmark\\" in value:
            DENIALS.append("protected_payload_open")
            raise RuntimeError("No model/native/oldpack payload reads")


def main():
    started = time.monotonic()
    deadline = started + BUDGET
    require(sys.flags.isolated and sys.dont_write_bytecode and metadata.version("asof-target-agents") == "0.3.11",
            "Accepted isolated no-bytecode pure environment required")
    require(not REPORT.exists(), "Reference report already consumed; no overwrite/restart")
    # Ordinary standard-library/accepted declaration imports precede the guard.
    # This is no claim of zero Python/OS loader activity or an OS sandbox.
    from asof.serde import ContractError, encode, fingerprint, parse_json
    from asof.study import diagnostic, interpretation_generation as generation
    sys.addaudithook(guard)
    raw = FREEZE.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == FREEZE_SHA, "Exact fixture freeze changed")
    frozen = json.loads(raw)
    pins = {}
    for name, record in frozen["artifacts"].items():
        path = Path(record["path"])
        require(path.parent == HERE and path.name == name, "Frozen leaf outside current phase")
        require(pin(path) == record, "Frozen artifact changed: " + name)
        pins[name] = record
    require(pins["UNICODE-CONTROL-CORPUS-v1.json"]["sha256"] == CORPUS_SHA
            and pins["UNICODE-CONTROL-STAGES-v1.json"]["sha256"] == STAGES_SHA, "Exact source/data corpus domain required")
    corpus = json.loads((HERE / "UNICODE-CONTROL-CORPUS-v1.json").read_bytes())
    stage_data = json.loads((HERE / "UNICODE-CONTROL-STAGES-v1.json").read_bytes())
    contract = json.loads((HERE / "UNICODE-CONTROL-CONTRACT-v2.json").read_bytes())
    provenance = json.loads((HERE / "UNICODE-CONTROL-PROVENANCE-v1.json").read_bytes())
    checks, errors, stage_checks = [], [], []
    rebuilt = {}
    for index, stage in enumerate(stage_data["stages"]):
        require(time.monotonic() < deadline, "Semantic review20s expired")
        declared = contract["language"]["stage_instances"][index]
        request = diagnostic.load_synthetic_request(declared["fixture"])
        prepared = generation.prepare_payload(request, declared["arm"], declared["stage_index"], declared["feedback"])
        require(exact(encode(request), stage["request"]) and exact(encode(prepared), stage["prepared"]), "Actual stage preparation mismatch")
        require(request["question"]["question_id"] == declared["question_id"] and prepared["semantic_data"]["stage"] == declared["stage_name"], "Wrong registered question/stage")
        grammar = prepared["generation_grammar"]
        encoded = grammar["grammar"].encode("utf-8")
        require(len(encoded) == stage["grammar_bytes"] and hashlib.sha256(encoded).hexdigest() == stage["grammar_sha256"], "Full actual grammar bytes differ")
        require(prepared["execution_authorized"] is False and prepared["native_conformance"] == "unverified", "Pure preparation authority changed")
        rebuilt[stage["id"]] = (request, prepared)
        stage_checks.append(dict(id=stage["id"], request_sha256=fingerprint(request), payload_sha256=prepared["payload_sha256"],
                                 grammar_sha256=stage["grammar_sha256"], full_actual_v3_preparation_equal=True))
    for row in provenance["source_modules"]:
        require(pin(row["installed"]["path"]) == row["installed"] and pin(row["workspace"]["path"]) == row["workspace"], "Pinned accepted pure source changed")
        require(Path(row["installed"]["path"]).read_text(encoding="utf-8") == Path(row["workspace"]["path"]).read_text(encoding="utf-8"), "Workspace/accepted source text mismatch")
    by_id = {case["id"]: case for case in corpus["cases"]}
    for ordinal, case in enumerate(corpus["cases"]):
        require(time.monotonic() < deadline, "Semantic review20s expired")
        raw = bytes.fromhex(case["raw_hex"])
        expected = case["expected"]
        mismatches = []
        require(case["ordinal"] == ordinal and 0 < len(raw) <= 1024 and len(raw) == case["bytes"], "Case framing/cap differs")
        require(hashlib.sha256(raw).hexdigest() == case["sha256"], "Case bytes changed")
        stats = wire_statistics(raw)
        if not exact(stats, case["wire_statistics"]): mismatches.append("wire_statistics")
        try:
            json.loads(raw.decode("utf-8", "strict"))
        except UnicodeError:
            syntax = None
        except ValueError:
            syntax = False
        else:
            syntax = True
        try:
            parsed = parse_json(raw)
        except (ContractError, UnicodeError, ValueError):
            parsed, project_parse, scalar = None, False, None
        else:
            project_parse, scalar = True, all_scalars(parsed)
        value = encode(parsed) if project_parse and scalar else None
        request, prepared = rebuilt[case["stage_id"]]
        try:
            result = generation.validate_output(request, prepared["payload"], raw)
        except (ContractError, UnicodeError, ValueError) as error:
            semantic, semantic_error = False, type(error).__name__
        else:
            semantic, semantic_error = True, None
            require(result["features"] == {} and result["clinical_probability"] is None and result["native_conformance"] == "unverified", "Unexpected numerical/native claim")
            require(exact(encode(result["response"]), value), "Validator rewrote response value")
        for key, actual in (("JSON_syntax", syntax), ("project_JSON_parse", project_parse), ("Unicode_scalar_JSON", scalar),
                            ("JSON_value", value), ("JSON_value_sha256", fingerprint(value) if value is not None else None),
                            ("complete_v3_semantic_validation", semantic)):
            if not exact(actual, expected[key]): mismatches.append(key)
        eligible = stats["UTF8_valid"] and b"\0" not in raw
        if eligible is not expected["native_byte_eligible"]: mismatches.append("byte_harness_eligibility")
        # Reviewed source-rule controls, not a newly invented grammar recognizer.
        source_generation = case["stratum"] != "byte_harness_guards" and (not case["id"].startswith("negative/") or case["id"] == "negative/duplicate_claim_text")
        if source_generation is not expected["generation_grammar_membership"]: mismatches.append("source_rule_expectation")
        population = eligible and source_generation and semantic
        if population is not case["coverage_population"]: mismatches.append("declared_population")
        if case["ASCII_counterpart_of"]:
            base = by_id[case["ASCII_counterpart_of"]]
            require(case["stage_id"] == base["stage_id"] and exact(expected["JSON_value"], base["expected"]["JSON_value"]), "ASCII pair changed value/stage")
            require(stats["ASCII_only"] and stats["raw_nonASCII_bytes"] == 0 and base["wire_statistics"]["raw_nonASCII_bytes"] > 0, "ASCII pair is not a representation control")
        checks.append(dict(id=case["id"], matched=not mismatches, mismatches=mismatches, bytes=len(raw),
            UTF8_valid=stats["UTF8_valid"], project_JSON_parse=project_parse, scalar_JSON=scalar, v3_semantic=semantic,
            semantic_error_class=semantic_error, native_byte_eligible=eligible, source_generation_expectation=source_generation,
            coverage_population=population, native_observation=None))
        if mismatches: errors.append(dict(id=case["id"], mismatches=mismatches))
    require(len(checks) == 84 and len(stage_checks) == 4 and len({row["grammar_sha256"] for row in stage_checks}) == 2, "Case/stage/grammar counts differ")
    counts = dict(cases=84, coverage_population=sum(row["coverage_population"] for row in checks),
                  native_byte_eligible=sum(row["native_byte_eligible"] for row in checks),
                  expected_native_members=sum(row["native_byte_eligible"] and row["source_generation_expectation"] for row in checks),
                  expected_native_nonmembers=sum(row["native_byte_eligible"] and not row["source_generation_expectation"] for row in checks),
                  null_native_membership=sum(not row["native_byte_eligible"] for row in checks),
                  v3_semantic_true=sum(row["v3_semantic"] for row in checks), project_JSON_parse_true=sum(row["project_JSON_parse"] for row in checks),
                  scalar_JSON_true=sum(row["scalar_JSON"] is True for row in checks), scalar_JSON_false=sum(row["scalar_JSON"] is False for row in checks),
                  scalar_JSON_null=sum(row["scalar_JSON"] is None for row in checks), ASCII_pairs=sum(bool(case["ASCII_counterpart_of"]) for case in corpus["cases"]),
                  max_document_bytes=max(row["bytes"] for row in checks))
    require(counts == dict(cases=84, coverage_population=68, native_byte_eligible=78, expected_native_members=69, expected_native_nonmembers=9,
        null_native_membership=6, v3_semantic_true=71, project_JSON_parse_true=76, scalar_JSON_true=75, scalar_JSON_false=1, scalar_JSON_null=8,
        ASCII_pairs=14, max_document_bytes=420), "Source-predicted count ledger differs")
    for name, row in pins.items(): require(pin(HERE / name) == row, "Frozen artifact changed during reference")
    require(pin(FREEZE)["sha256"] == FREEZE_SHA, "Freeze changed during reference")
    require(time.monotonic() < deadline, "Semantic reference finalization exceeded20s")
    proof = dict(schema_version=1, status="passed" if not errors and not DENIALS else "failed", freeze_sha256=FREEZE_SHA,
        checker=pin(__file__), counts=counts, stage_checks=stage_checks, case_checks=checks, errors=errors, audit_denials=DENIALS,
        frozen_artifacts=pins, elapsed_seconds=time.monotonic()-started, budget_seconds=BUDGET,
        scope="Independent exact bytes/strictJSON/scalar/actualacceptedv3 raw-byte validator and fullstage reconstruction; source-rule generation expectations remain authored, not native observations",
        activity_scope="No target/SDK/tokenizer/compiler/network calls; ordinary Python/stdlib import/loader activity not universally attested",
        tokenizer_calls=0, target_native_calls=0, SDK_constructions=0, CPU_GGUF_oldpack_operations=0, bridge_pack_runtime_implementations=0,
        old_profile_repaired=False, native_conformance="unverified", scientific_validation="not_established")
    with REPORT.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(proof, stream, indent=2); stream.write("\n")
    print(json.dumps(dict(status=proof["status"], errors=len(errors), counts=counts, elapsed_seconds=proof["elapsed_seconds"])))
    return 0 if proof["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
