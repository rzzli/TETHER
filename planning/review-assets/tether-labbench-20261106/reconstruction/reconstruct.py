"""Independent, stdlib-only native score reconstruction; never executes a model.

No project implementation is imported. Actual originals may be opened only after
an externally anchored candidate seal has passed byte verification.
"""
import argparse
import base64
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import random
import string
import time

REFUSAL = "Insufficient information to answer the question"
SEED = 20261106
PRODUCER = {"produced", "input_unavailable", "parse_failure", "timeout", "interrupted", "error", "unexecuted"}
CHECKER = {"accepted", "rejected", "error", "not_run"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def parse(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "Duplicate JSON key")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))


def child(root, relative):
    require(isinstance(relative, str) and "\\" not in relative, "Noncanonical artifact path")
    parts = PurePosixPath(relative)
    require(not parts.is_absolute() and all(p not in (".", "..", "") for p in parts.parts)
            and ":" not in relative, "Unsafe artifact path")
    path = Path(root).joinpath(*parts.parts)
    require(path.resolve().is_relative_to(Path(root).resolve()) and not path.is_symlink(), "Aliased artifact")
    return path


def read(path, expected=None, maximum=64*1024**2):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "Missing or aliased input")
    with path.open("rb") as stream:
        raw = stream.read(maximum+1)
    require(len(raw) <= maximum and (expected is None or sha(raw) == expected), "Input hash/size differs")
    return raw


def proof_json(root, proof):
    raw = read(child(root, proof["path"]), proof["sha256"])
    require(len(raw) == proof["bytes"], "Input byte count differs")
    return parse(raw)


def verify_seal(root, expected):
    """Byte integrity only; generic runtime/policy verification is separate."""
    root = Path(root)
    seal = parse(read(root/"SEALED.json", expected))
    require(isinstance(seal.get("outputs"), dict), "Missing sealed inventory")
    actual = {str(p.relative_to(root)).replace("\\", "/") for p in root.rglob("*")
              if p.is_file() and p != root/"SEALED.json"}
    require(actual == set(seal["outputs"]), "Output inventory differs")
    for name, proof in seal["outputs"].items():
        path = child(root, name)
        digest = hashlib.sha256()
        count = 0
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024**2), b""):
                count += len(block)
                digest.update(block)
        require(count == proof["bytes"] and digest.hexdigest() == proof["sha256"], "Sealed output changed")
    return seal


def reconstruct_keys(originals, queries, seed=SEED):
    """Recreate native all-option shuffle; do not reinterpret the string 'null'."""
    require(len(originals) == len(queries) and len(queries) > 0, "Reference schedule differs")
    rng = random.Random(seed)
    keys, seen = [], set()
    for original, query in zip(originals, queries):
        require(set(query) == {"id", "question", "choices"}, "Unexpected task fields")
        require(original["id"] == query["id"] and query["id"] not in seen
                and original["question"] == query["question"], "Native identity/order differs")
        seen.add(query["id"])
        options = [original["ideal"], REFUSAL] + original["distractors"]
        require(2 <= len(options) <= 26 and all(isinstance(v, str) for v in options), "Native choices invalid")
        require(options[0] != REFUSAL and options[0] not in options[2:] and REFUSAL not in options[2:],
                "Correct/refusal option collision")
        order = list(range(len(options)))
        rng.shuffle(order)
        displayed = ["("+string.ascii_uppercase[i]+") "+options[j] for i, j in enumerate(order)]
        require(displayed == query["choices"], "Frozen choice permutation differs")
        keys.append({"id": query["id"], "answer_index": order.index(0), "unsure_index": order.index(1)})
    return keys


def validate_answer(candidate, choice_count, offered=None):
    require(isinstance(candidate, dict) and set(candidate) == {"answer_index", "evidence_ids"}, "Malformed candidate fields")
    index, evidence = candidate["answer_index"], candidate["evidence_ids"]
    require(type(index) is int and 0 <= index < choice_count, "Invalid answer index")
    require(isinstance(evidence, list) and all(isinstance(i, str) for i in evidence)
            and len(set(evidence)) == len(evidence), "Invalid evidence identities")
    require(offered is None or set(evidence) <= set(offered), "Unoffered evidence identity")
    return index


def native_response(wrapper):
    require(wrapper["http_status"] == 200 and wrapper["complete"] is True
            and wrapper["error_class"] is None, "Incomplete native response")
    body = base64.b64decode(wrapper["body_base64"], validate=True)
    require(sha(body) == wrapper["body_sha256"], "Native body hash differs")
    response = parse(body)
    require(isinstance(response.get("content"), str), "Native text absent")
    return parse(response["content"])


def calculate(queries, keys, dispositions):
    require(len(queries) == len(keys) == len(dispositions) and queries, "Missing scheduled cases")
    require(len({q["id"] for q in queries}) == len(queries), "Duplicate scheduled identity")
    counts = Counter({k: 0 for k in ("produced", "producer_failures", "accepted", "rejected", "check_errors",
        "check_not_run", "raw_answered", "checked_answered", "raw_correct", "correct_and_admitted",
        "correct_but_rejected", "correct_not_admitted", "native_unsure", "accepted_unsure",
        "incorrect_and_admitted", "incorrect_substantive_and_admitted", "parse_failures", "produced_or_parse_failure")})
    producer, checker = Counter(), Counter()
    for query, key, item in zip(queries, keys, dispositions):
        require(query["id"] == key["id"] == item["id"], "Disposition schedule differs")
        require(set(item) == {"id", "producer_status", "check_status", "prediction", "reason"}, "Disposition fields differ")
        state, checked = item["producer_status"], item["check_status"]
        require(state in PRODUCER and checked in CHECKER, "Unknown disposition")
        producer[state] += 1
        checker[checked] += 1
        made = state == "produced"
        require(made or item["prediction"] is None and checked == "not_run", "Failed producer carries an answer/check")
        require(not made or checked != "not_run", "Produced candidate omitted its checker outcome")
        answer = validate_answer(item["prediction"], len(query["choices"])) if made else None
        unsure = made and answer == key["unsure_index"]
        correct = made and answer == key["answer_index"]
        admitted = made and checked == "accepted"
        answered = made and not unsure
        counts.update(produced=made, producer_failures=not made, accepted=admitted,
            rejected=made and checked == "rejected", check_errors=made and checked == "error",
            check_not_run=checked == "not_run", raw_answered=answered, checked_answered=answered and admitted,
            raw_correct=correct, correct_and_admitted=correct and admitted,
            correct_but_rejected=correct and checked == "rejected", correct_not_admitted=correct and not admitted,
            native_unsure=unsure, accepted_unsure=unsure and admitted,
            incorrect_and_admitted=admitted and not correct,
            incorrect_substantive_and_admitted=admitted and answered and not correct,
            parse_failures=state == "parse_failure", produced_or_parse_failure=made or state == "parse_failure")
    total = len(queries)
    def metrics(correct, answered):
        return {"accuracy": correct/total, "precision": correct/answered if answered else 0.0, "coverage": answered/total}
    return {"scheduled_count": total, "raw_metrics": metrics(counts["raw_correct"], counts["raw_answered"]),
        "checked_metrics": metrics(counts["correct_and_admitted"], counts["checked_answered"]),
        "raw_precision_defined": counts["raw_answered"] != 0, "checked_precision_defined": counts["checked_answered"] != 0,
        "counts": dict(counts), "rates": {"correct_and_admitted_per_scheduled": counts["correct_and_admitted"]/total,
            "admitted_per_scheduled": counts["accepted"]/total, "producer_failure_per_scheduled": counts["producer_failures"]/total},
        "producer_statuses": dict(producer), "check_statuses": dict(checker)}


def dependence(originals):
    """Conservative observed dependence, not an estimate of independence."""
    parents = list(range(len(originals)))
    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    question_owner, source_owner = {}, {}
    for i, row in enumerate(originals):
        groups = ((question_owner, [" ".join(row["question"].split())]),
                  (source_owner, sorted(set(s.strip() for s in row.get("sources", [])))))
        for seen, values in groups:
            for value in values:
                if value in seen:
                    parents[find(i)] = find(seen[value])
                else:
                    seen[value] = i
    sizes = sorted(Counter(find(i) for i in range(len(originals))).values(), reverse=True)
    return {"scheduled_question_count": len(originals), "observed_component_count": len(sizes),
            "observed_component_sizes": sizes,
            "grouping": "Exact shared stripped annotation string or whitespace-normalized identical question; transitive closure",
            "limitations": "Different DOI/PMID/PMCID or publisher aliases are not resolved here. Distinct observed components are not asserted independent. No confidence interval or power claim uses 199 as independent units."}


def analytical_controls(queries):
    counts = [len(q["choices"]) for q in queries]
    total = len(counts)
    expected_correct = sum(1/n for n in counts)
    expected_answered = sum((n-1)/n for n in counts)
    return {"executed": False, "basis": "Analytical option-position expectations, not model or policy runs",
            "always_unsure": {"accuracy": 0.0, "coverage": 0.0, "precision": 0.0, "precision_defined": False},
            "uniform_all_choices": {"expected_accuracy": expected_correct/total,
                "expected_coverage": expected_answered/total,
                "ratio_of_expected_correct_to_expected_answered": expected_correct/expected_answered,
                "precision_note": "Ratio of expectations, not expectation of finite-sample precision"},
            "uniform_substantive_choices": {"expected_accuracy": sum(1/(n-1) for n in counts)/total, "coverage": 1.0},
            "checked_control": "Not simulated"}


def reconstruct(generation_root, generation_sha, original_path, original_sha, *, expected_count=199,
                references_path=None, references_sha=None, evaluation_root=None, evaluation_sha=None):
    root = Path(generation_root)
    seal = verify_seal(root, generation_sha)  # MUST precede reference access.
    require(seal["kind"] == "labbench_generation", "Not a generation seal")
    manifest = parse(read(root/"manifest.json", seal["manifest_sha256"]))
    require(manifest["status"] == seal["status"] and manifest["status"] in ("completed", "partial"), "Contradictory generation status")
    queries = proof_json(root, manifest["queries"])
    records = proof_json(root, manifest["dispositions"])
    index = proof_json(root, manifest["case_index"])
    ids = [q["id"] for q in queries]
    require(len(queries) == expected_count and len(set(ids)) == expected_count and ids == manifest["schedule"]
            and len(index) == len(records) == expected_count, "Generation denominator differs")
    paired = 0
    for ordinal, (query, item, case) in enumerate(zip(queries, records, index)):
        require(case["ordinal"] == ordinal and case["id"] == query["id"] and case["disposition"] == item,
                "Index/disposition join differs")
        artifacts = case["artifacts"]
        if item["producer_status"] == "produced":
            candidate = proof_json(root, artifacts["candidate"])
            sources = proof_json(root, artifacts["sources"])
            validate_answer(candidate, len(query["choices"]), [s["source_id"] for s in sources])
            require(candidate == item["prediction"] == proof_json(root, artifacts["session_response"])
                    == native_response(proof_json(root, artifacts["raw_response"])), "Candidate/native response bytes differ")
            if item["check_status"] in ("accepted", "rejected"):
                decision = proof_json(root, artifacts["decision"])
                require(type(decision["accepted"]) is bool and decision["accepted"] == (item["check_status"] == "accepted"),
                        "Admission decision differs")
            paired += 1
    # Only now open mixed answer-containing originals; no per-question keys are emitted.
    original = read(original_path, original_sha)
    originals = [parse(line) for line in original.splitlines() if line.strip()]
    require(len(originals) == expected_count, "Original population differs")
    keys = reconstruct_keys(originals, queries)
    if references_path is not None:
        require(references_sha is not None and parse(read(references_path, references_sha)) == keys, "Prepared reference map differs")
    result = calculate(queries, keys, records)
    if evaluation_root is not None:
        require(evaluation_sha is not None, "Evaluation external anchor required")
        verify_seal(evaluation_root, evaluation_sha)
        report = parse(read(Path(evaluation_root)/"REPORT.json"))
        for name in ("scheduled_count", "raw_metrics", "checked_metrics", "counts", "rates",
                     "raw_precision_defined", "checked_precision_defined"):
            require(report[name] == result[name], "Primary evaluation differs: "+name)
    result.update(status="pass", generation_status=manifest["status"], paired_original_candidates=paired,
        preparation_reference_comparison=references_path is not None, primary_evaluation_comparison=evaluation_root is not None,
        original_sha256=original_sha, generation_sealed_sha256=generation_sha,
        inputs_opened_after_generation_seal=True, new_model_calls=0, new_network_requests=0,
        observed_dependence=dependence(originals), analytical_controls=analytical_controls(queries),
        scope="Independent native key permutation, candidate/native-byte joins, full-schedule metrics and paired counts; generic runtime/provenance replay remains a separate verification.",
        semantic_support="unevaluated")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("generation-root", "generation-sha", "original-path", "original-sha", "output"):
        parser.add_argument("--"+name, required=True)
    for name in ("references-path", "references-sha", "evaluation-root", "evaluation-sha"):
        parser.add_argument("--"+name)
    parser.add_argument("--generation-sealed-authorized", action="store_true", required=True)
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    try:
        result = reconstruct(args.generation_root, args.generation_sha, args.original_path, args.original_sha,
            references_path=args.references_path, references_sha=args.references_sha,
            evaluation_root=args.evaluation_root, evaluation_sha=args.evaluation_sha)
        result.update(completed_at=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.monotonic()-started,
                      reconstruction_code_sha256=sha(Path(__file__).read_bytes()))
        (out/"RECONSTRUCTION.json").write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "scheduled": result["scheduled_count"]}))
    except BaseException as exc:
        (out/"FAILED.json").write_text(json.dumps({"status": "failed", "error_class": type(exc).__name__,
            "message": str(exc), "elapsed_seconds": time.monotonic()-started})+"\n", encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
