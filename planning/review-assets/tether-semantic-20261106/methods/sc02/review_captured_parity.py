"""Independently check saved SC02 tensors/decodes; imports no model or torch.

Requires a parent-supplied qualification report hash. This does not repeat GPU
inference or claim historical tokenizer binary equivalence.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path


CONTROLS_SHA256 = "65a697882396742b46589bfd96f1a18c3862583447f202560dea1d6a3a6ada2e"
FLOAT_FIELDS = ("label_logits", "rationale_logits", "label_probs", "rationale_probs")
DISCRETE_FIELDS = ("predicted_labels", "predicted_rationales")
LABELS = ("CONTRADICT", "NEI", "SUPPORT")


def proof(path):
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def need(ok, message):
    if not ok:
        raise ValueError(message)


def array(record, shape, dtype):
    need(record["shape"] == shape and record["dtype"] == dtype, "Tensor shape/dtype mismatch")
    value = record["values"]
    def check(v, dims):
        if dims:
            need(type(v) is list and len(v) == dims[0], "Tensor nesting mismatch")
            for child in v:
                check(child, dims[1:])
        else:
            need(type(v) in (int, float) and math.isfinite(v), "Nonfinite/nonnumeric saved tensor")
            if dtype == "torch.int64":
                need(type(v) is int, "Noninteger discrete tensor")
    check(value, shape)
    return value


def flat(value):
    if type(value) is list:
        return [x for part in value for x in flat(part)]
    return [value]


def close(actual, reference, atol, rtol):
    a, b = flat(actual), flat(reference)
    need(len(a) == len(b), "Different output lengths")
    errors = [abs(x-y) for x, y in zip(a, b)]
    need(all(error <= atol + rtol*abs(y) for error, y in zip(errors, b)), "Numerical parity tolerance violated")
    return max(errors, default=0.0)


def argmax(values):
    return max(range(len(values)), key=values.__getitem__)


def decoded(values, cid, did, offsets, label_threshold, rationale_threshold):
    logits, probs = values["label_logits"][0], values["label_probs"][0]
    normalizer = sum(math.exp(x-max(logits)) for x in logits)
    recomputed_probs = [math.exp(x-max(logits))/normalizer for x in logits]
    close(probs, recomputed_probs, 1e-5, 1e-4)
    adjusted = probs[:]
    if label_threshold is not None:
        adjusted[1] = label_threshold
    label_id = argmax(logits) if label_threshold is None else argmax(adjusted)
    need(values["predicted_labels"] == [label_id], "Predicted label differs from saved logits/threshold")
    rationale_logits, rationale_probs = values["rationale_logits"][0], values["rationale_probs"][0]
    sigmoid = lambda v: 1/(1+math.exp(-v)) if v >= 0 else math.exp(v)/(1+math.exp(v))
    close(rationale_probs, [sigmoid(x) for x in rationale_logits], 1e-5, 1e-4)
    indicators = [int(p >= rationale_threshold) for p in rationale_probs]
    need(values["predicted_rationales"] == [indicators], "Rationale threshold/indicator disagreement")
    valid = [i for i, offset in enumerate(offsets) if offset > 0]
    return {"claim_id": cid, "abstract_id": did, "predicted_label": LABELS[label_id],
            "predicted_rationale": [j for j, i in enumerate(valid) if indicators[i]],
            "label_probs": probs, "rationale_probs": [rationale_probs[i] for i in valid]}


def self_test():
    need(close([1.0], [1.0], 1e-5, 1e-4) == 0, "Exact numerical control")
    failures = 0
    for call in (lambda: close([1.1], [1.0], 1e-5, 1e-4),
                 lambda: array({"shape": [1], "dtype": "torch.float32", "values": ["NaN"]}, [1], "torch.float32"),
                 lambda: array({"shape": [1], "dtype": "torch.int64", "values": [True]}, [1], "torch.int64")):
        try:
            call()
        except ValueError:
            failures += 1
    need(failures == 3, "Adverse arithmetic controls failed")
    values = {"label_logits": [[0, 0, 1]], "label_probs": [[1/(2+math.e), 1/(2+math.e), math.e/(2+math.e)]],
              "predicted_labels": [2], "rationale_logits": [[0, -1, 2]],
              "rationale_probs": [[.5, 1/(1+math.e), 1/(1+math.exp(-2))]], "predicted_rationales": [[1, 0, 1]]}
    got = decoded(values, 1, 10, [3, 6, 0], None, .5)
    need(got["predicted_rationale"] == [0], "Equality/padding native decode control")
    return {"status": "PASS", "adverse_controls": 3, "positive_decode": got}


def run(args):
    root = args.qualification.resolve()
    inputs = {}
    def read(name):
        path = root / name
        inputs[name] = proof(path)
        return json.loads(path.read_text(encoding="utf-8"))
    report = read("QUALIFICATION.json")
    need(inputs["QUALIFICATION.json"]["sha256"] == args.report_sha256, "External report pin mismatch")
    controls = read("controls.json")
    need(inputs["controls.json"]["sha256"] == CONTROLS_SHA256 == report["controls_sha256"], "Frozen fictional control identity mismatch")
    need(report["status"] == "passed" and report["semantic_diagnostics_are_not_a_pass_gate"] is True, "Qualification status/scope mismatch")
    need(report["dev_or_calibration_data_used"] is False and report["original_tokenizers_binary_parity"] is False, "Exposure/parity scope changed")
    need(report["versions"] == {"torch": "2.7.1+cu128", "transformers": "4.57.1", "tokenizers": "0.22.1"}, "Unqualified runtime version")
    need([r["case_id"] for r in report["cases"]] == [x["id"] for x in controls["cases"]], "Scheduled fictional case mismatch")
    need(len(report["cases"]) == 9 and controls["force_rationale"] is False, "Frozen schedule/default changed")
    hparams = report["checkpoint"]["hparams"]
    label_threshold, rationale_threshold = hparams.get("label_threshold"), hparams.get("rationale_threshold", .5)
    outcomes = []
    for index, (spec, saved) in enumerate(zip(controls["cases"], report["cases"])):
        stem = f'{index:02d}-{spec["id"]}'
        case, row = read(stem + ".input.json"), read(stem + ".result.json")
        need(row == saved and case["id"] == spec["id"], "Per-case report/input mismatch")
        for field in ("claim", "title", "expected_label_diagnostic", "expected_rejection"):
            need(case.get(field) == spec.get(field), "Fictional input changed outside declared expansion")
        if "target_tokens" in spec:
            need(case["sentences"][1:] == spec["sentences"], "Long-context recipe altered original sentences")
            filler = case["sentences"][0]
            recipe = controls["long_context_recipe"]
            need(filler.startswith(recipe["prefix"]) and filler.endswith(recipe["suffix"]), "Filler recipe mismatch")
            middle = filler[len(recipe["prefix"]):-len(recipe["suffix"])]
            count = len(middle) // len(recipe["repeat_word"])
            need(0 <= count <= 6000 and middle == recipe["repeat_word"]*count, "Filler repeat content differs")
            need(spec["target_tokens"]-3 <= case["constructed_token_count"] <= spec["target_tokens"], "Constructed token target mismatch")
        else:
            need(case["sentences"] == spec["sentences"], "Fictional sentences changed")
        if spec.get("expected_rejection"):
            need(row["rejected"] is True and row["token_count"] > 4096 and "4096" in row["reason"], "Overflow failed for wrong reason")
            need(not (root/(stem+".tensors.json")).exists(), "Overflow unexpectedly dispatched a model")
            outcomes.append({"case_id": spec["id"], "result": "expected_overflow", "tokens": row["token_count"]})
            continue
        tensors, decodes = read(stem + ".tensors.json"), read(stem + ".decoded.json")
        n_tokens, n_sentences = row["token_count"], len(case["sentences"])
        ids = array(tensors["tokenized"]["input_ids"], [1, n_tokens], "torch.int64")[0]
        ordinary = array(tensors["tokenized"]["attention_mask"], [1, n_tokens], "torch.int64")[0]
        global_mask = array(tensors["tokenized"]["global_attention_mask"], [1, n_tokens], "torch.int64")[0]
        offsets = array(tensors["abstract_sent_idx"], [1, n_sentences], "torch.int64")[0]
        need(array(tensors["claim_id"], [1], "torch.int64") == [index+1], "Claim ID shift")
        need(array(tensors["abstract_id"], [1], "torch.int64") == [index+101], "Document ID shift")
        need(0 < n_tokens <= 4096 and all(0 <= x < 50275 for x in ids), "Input token bounds")
        need(ids[0] == 0 and ids[-1] == 2 and ordinary == [1]*n_tokens, "Outer tokens/ordinary mask changed")
        eos = [i for i, token in enumerate(ids) if token == 2]
        need(offsets == eos[1 if case["title"] is None else 2:] == row["sentence_offsets"], "Original sentence offset rule differs")
        need(global_mask == [int(token in (0, 2) or i < eos[0]) for i, token in enumerate(ids)], "Global attention rule differs")
        values = {}
        for arm in ("actual", "reference"):
            need(set(tensors[arm]) == set(FLOAT_FIELDS + DISCRETE_FIELDS), "Unexpected saved output fields")
            values[arm] = {}
            for field in FLOAT_FIELDS + DISCRETE_FIELDS:
                shape = [1] if field == "predicted_labels" else [1, 3] if field.startswith("label_") else [1, n_sentences]
                dtype = "torch.float32" if field in FLOAT_FIELDS else "torch.int64"
                values[arm][field] = array(tensors[arm][field], shape, dtype)
        differences = {field: close(values["actual"][field], values["reference"][field], controls["parity_atol"], controls["parity_rtol"]) for field in FLOAT_FIELDS}
        for field in DISCRETE_FIELDS:
            need(values["actual"][field] == values["reference"][field], "Discrete parity differs")
        reconstructed = {arm: decoded(v, index+1, index+101, offsets, label_threshold, rationale_threshold) for arm, v in values.items()}
        for arm in reconstructed:
            need(decodes[arm] == [reconstructed[arm]], "Captured decode differs from independently reconstructed tensors")
        need(row["prediction"] == reconstructed["actual"], "Main result differs from captured decode")
        pred = reconstructed["actual"]
        native = {"id": index+1, "evidence": {} if pred["predicted_label"] == "NEI" else {str(index+101): {"label": pred["predicted_label"], "sentences": pred["predicted_rationale"]}}}
        need(row["native_prediction"] == native, "Native formatting differs")
        need(row["semantic_diagnostic_match"] == (pred["predicted_label"] == spec["expected_label_diagnostic"]), "Diagnostic label tally differs")
        need(row["source_level_parity"] is True, "Missing case parity status")
        for field, difference in differences.items():
            need(abs(row["maximum_absolute_differences"][field]-difference) <= 1e-12, "Reported difference differs from captured values")
        need(0 <= row["forward_seconds"] + row["reference_seconds"] <= controls["maximum_case_seconds"], "Measured inference exceeds case cap")
        outcomes.append({"case_id": spec["id"], "tokens": n_tokens, "maximum_absolute_differences": differences,
                         "native_prediction": native, "semantic_diagnostic_match": row["semantic_diagnostic_match"]})
    need(len(outcomes) == 9, "All-case reconstruction incomplete")
    for name, original in inputs.items():
        need(proof(root/name) == original, "Qualification input changed during reconstruction")
    args.output.mkdir(parents=True, exist_ok=False)
    result = {"status": "PASS_captured_source_parity_reconstruction", "scheduled_cases": 9, "inference_cases": 8, "overflow_controls": 1,
              "cases": outcomes, "input_pins": inputs, "reviewer": proof(Path(__file__)), "self_controls": self_test(),
              "scope": "All retained tensors, native decode, masks, IDs and numerical tolerances reconstructed with stdlib only; no torch/model import or GPU run.",
              "limits": ["Token IDs are checked against captured source-rule masks and offsets; this checker does not independently run the tokenizer backend.", "Captured reference/adapter agreement is source-level parity on the modern runtime, not historical binary reproduction.", "Fictional semantic diagnostic matches do not establish SciFact accuracy or clinical validity."]}
    destination = args.output/"PARITY-REVIEW.json"
    destination.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "record": proof(destination)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualification", type=Path)
    parser.add_argument("--report-sha256")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        result = {"status": "PASS", "controls": self_test(), "reviewer": proof(Path(__file__))}
        if args.output is not None:
            args.output.mkdir(parents=True, exist_ok=False)
            destination = args.output/"QUALIFICATION.json"
            destination.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")
            result["retained"] = proof(destination)
        print(json.dumps(result))
    else:
        need(args.qualification is not None and args.report_sha256 and args.output is not None, "Actual review arguments required")
        run(args)
