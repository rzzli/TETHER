"""Independent invented decode/mask controls on exact retained MultiVerS functions.

Only named function ASTs execute; imports, constructors, loading and forward model
code never execute. NumPy emulates the tiny tensor operations for mask controls.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / "solver-feasibility/source/multivers"
OUT = HERE / "source-controls-attempt01"


def proof(path):
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def extracted(path, name, namespace, class_name=None):
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    parent = next(x for x in module.body if isinstance(x, ast.ClassDef) and x.name == class_name) if class_name else module
    node = copy.deepcopy(next(x for x in parent.body if isinstance(x, ast.FunctionDef) and x.name == name))
    decorators = [ast.unparse(x) for x in node.decorator_list]
    assert not decorators or decorators == ["staticmethod"], decorators
    node.decorator_list = []
    ast.fix_missing_locations(node)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
    return namespace[name]


class FakeTensor(np.ndarray):
    def to(self, dtype):
        return self.astype(dtype)


class Tokenized(dict):
    __getattr__ = dict.__getitem__


def array(values):
    return np.asarray(values).view(FakeTensor)


def main():
    model, data, util, predict = [SOURCE / name for name in ("model.py", "data.py", "util.py", "predict.py")]
    source_before = [proof(p) for p in (model, data, util, predict)]
    receipt = json.loads((SOURCE.parents[1] / "source-receipt.json").read_text(encoding="utf-8"))
    expected = {str(Path(x["local_path"]).resolve()): x["sha256"] for x in receipt["files"]}
    assert all(expected[x["path"]] == x["sha256"] for x in source_before)
    # ndarray inputs deliberately avoid torch.Tensor conversion in unbatch.
    unbatch = extracted(util, "unbatch", {"torch": SimpleNamespace(Tensor=type("NeverTensor", (), {}))})
    decode = extracted(model, "decode", {"util": SimpleNamespace(unbatch=unbatch)}, "MultiVerSModel")
    batch = {"claim_id": np.array([901, 902, 903]), "abstract_id": np.array([101, 102, 103]),
             "abstract_sent_idx": np.array([[3, 5, 7, 0], [4, 8, 0, 0], [3, 6, 9, 12]]), "tokenized": {}}
    outputs = {"predicted_labels": np.array([0, 1, 2]), "predicted_rationales": np.array([[1, 0, 1, 1], [1, 0, 1, 1], [0, 0, 0, 0]]),
               "label_probs": np.array([[.8, .1, .1], [.1, .8, .1], [.1, .1, .8]]),
               "rationale_probs": np.array([[.55, .1, .95, .99], [.6, .2, .99, .99], [.1, .2, .4, .3]])}
    raw = decode(outputs, batch, False)
    assert [r["predicted_label"] for r in raw] == ["CONTRADICT", "NEI", "SUPPORT"]
    assert [r["predicted_rationale"] for r in raw] == [[0, 2], [0], []]
    assert [r["rationale_probs"].tolist() for r in raw] == [[.55, .1, .95], [.6, .2], [.1, .2, .4, .3]]
    forced = decode(outputs, batch, True)
    assert forced[2]["predicted_rationale"] == [2] and raw[2]["predicted_rationale"] == []
    assert forced[1]["predicted_label"] == "NEI"
    format_predictions = extracted(predict, "format_predictions", {"util": SimpleNamespace(load_jsonl=lambda _: [{"id": x} for x in (901, 902, 903, 904)])})
    native = format_predictions(SimpleNamespace(input_file="invented-only"), raw)
    # JSON round trip is the native on-disk representation: document keys are strings.
    native = json.loads(json.dumps(native))
    assert native == [{"id": 901, "evidence": {"101": {"label": "CONTRADICT", "sentences": [0, 2]}}},
                      {"id": 902, "evidence": {}},
                      {"id": 903, "evidence": {"103": {"label": "SUPPORT", "sentences": []}}},
                      {"id": 904, "evidence": {}}]
    torch_stub = SimpleNamespace(tensor=array, where=np.where, arange=lambda n: array(np.arange(n)), int64=np.int64)
    mask_fn = extracted(data, "_get_global_attention_mask", {"torch": torch_stub}, "MultiVerSDataset")
    sentence_fn = extracted(data, "_get_abstract_sent_tokens", {"torch": torch_stub}, "MultiVerSDataset")
    self = SimpleNamespace(tokenizer=SimpleNamespace(bos_token_id=0, eos_token_id=2))
    mask_cases = [
        ("with_title_and_ordinary_science_marker", [0, 10, 11, 2, 50265, 2, 30, 31, 2, 40, 2], "title", [1, 1, 1, 1, 0, 1, 0, 0, 1, 0, 1], [8, 10]),
        ("without_title", [0, 10, 2, 30, 2, 40, 2], None, [1, 1, 1, 0, 1, 0, 1], [4, 6]),
        ("empty_string_title_is_present", [0, 10, 2, 2, 30, 2], "", [1, 1, 1, 1, 0, 1], [5]),
    ]
    controls = []
    for name, tokens, title, expected_mask, expected_sentences in mask_cases:
        tokenized = Tokenized(input_ids=tokens)
        got_mask, got_sentences = mask_fn(self, tokenized), sentence_fn(self, tokenized, title)
        assert got_mask == expected_mask and got_sentences == expected_sentences
        controls.append({"name": name, "input_ids": tokens, "global_attention_mask": got_mask, "abstract_sent_idx": got_sentences})
    long_tokens = [0, 10, 2, 20, 2] + [30] * 600 + [2, 40, 2]
    long_mask = mask_fn(self, Tokenized(input_ids=long_tokens))
    long_sentences = sentence_fn(self, Tokenized(input_ids=long_tokens), "title")
    assert len(long_tokens) > 512 and long_sentences == [605, 607]
    assert [i for i, x in enumerate(long_mask) if x] == [0, 1, 2, 4, 605, 607]
    controls.append({"name": "over_512_no_implicit_truncation", "tokens": len(long_tokens), "global_positions": [i for i, x in enumerate(long_mask) if x], "abstract_sent_idx": long_sentences})
    assert source_before == [proof(p) for p in (model, data, util, predict)]
    OUT.mkdir(exist_ok=False)
    report = {"status": "PASS_function_controls_only", "source_pins": source_before, "reviewer": proof(Path(__file__)),
              "native_decode_expected": native, "mask_controls": controls,
              "checks": ["three_label_mapping", "ascending_sentence_order_not_probability_order", "padding_excluded", "force_false_preserves_empty_non_nei", "forced_variant_differs_explicitly", "nei_omitted_from_native", "all_scheduled_ids_formatted", "title_none_vs_empty", "science_marker_not_automatically_global", "over_512_sentence_offsets_retained"],
              "limitations": ["No tokenizer backend, checkpoint, transformer forward pass or GPU run.", "NumPy stub checks the selected mask-function operations only, not torch numerical compatibility.", "Formatter preserves IDs with no document records; later runner must separately prevent failure-as-empty from becoming substantive NEI.", "Staticmethod decorators removed for standalone function extraction; computational function bodies unchanged."]}
    (OUT / "CONTROLS.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "record": proof(OUT / "CONTROLS.json")}))


if __name__ == "__main__":
    main()
