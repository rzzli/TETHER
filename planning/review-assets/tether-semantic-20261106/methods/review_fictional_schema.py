"""Inspect the primary analyzer's two invented transport fixtures independently."""
import json
from pathlib import Path
import runpy


root = Path(__file__).resolve().parent
qualified = root.parent / "decomposition/qualification-attempt01"
inputs = qualified / "fictional-inputs"
read = lambda p: json.loads(p.read_text(encoding="utf-8"))
manifest = read(inputs / "MANIFEST.json")
assert manifest["mode"] == "fictional_qualification"
helpers = runpy.run_path(str(root / "independent_native_check.py"), run_name="independent_fictional_schema_review")
references = [json.loads(x) for x in (inputs / "references.json").read_text(encoding="utf-8").splitlines()]
result = helpers["reconstruct"](references, read(inputs / "dispositions.json"), read(inputs / "candidates.json"), read(inputs / "freeze.json")["dev_schedule"])
primary_path = qualified / "fictional-analysis/DECOMPOSITION.json"
primary = read(primary_path)
assert primary["schedule"] == [x["id"] for x in result["cases"]]
assert primary["summary"]["scheduled_claims"] == result["counts"]["scheduled"] == 2
assert primary["summary"]["raw_strict_correct"] == result["counts"]["raw_strict_correct"] == 2
assert primary["summary"]["document_counts"]["gold"] == result["counts"]["gold_document_pairs"] == 1
for p, q in zip(primary["cases"], result["cases"]):
    assert p["raw_strict_correct"] is q["raw_strict_correct"]
    assert p["checked_strict_correct"] is q["checked_strict_correct"]
    assert p["selection"]["documents"] == q["selected_doc_ids"]
    assert p["selection"]["false_positive_documents"] == q["selected_extra_ids"]
    assert p["selection"]["false_negative_documents"] == q["selected_missing_ids"]
    docs = {d["doc_id"]: d for d in p["gold_document_details"] if d["selected"]}
    for d in q["documents"]:
        assert docs[d["doc_id"]]["native_cap"] == d["native_cap"]
        assert docs[d["doc_id"]]["complete_any_capped"] == d["complete_capped"]
        assert docs[d["doc_id"]]["complete_any_full"] == d["complete_full"]
        assert docs[d["doc_id"]]["missing_sentences_by_rationale_full"] == d["missing_by_alternative_full"]
        assert docs[d["doc_id"]]["extra_sentences_full"] == d["outside_union_full"]
output = root / "fictional-schema-review-attempt01"
output.mkdir(exist_ok=False)
record = {"status": "PASS", "invented_transport_cases": 2, "scope": "Schema/data join only; no real development analysis and no primary analyzer import.",
          "primary": helpers["proof"](primary_path), "reviewer": helpers["proof"](__file__),
          "independent_checker": helpers["proof"](root / "independent_native_check.py"), "independent": result}
helpers["write"](output / "REVIEW.json", record)
print(json.dumps({"status": "PASS", "invented_transport_cases": 2, "output": str(output)}))
