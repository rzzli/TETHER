"""Read-only positive inventory qualification; no cases or validators execute."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from experiments.inspect_policy import controller
from experiments.inspect_policy.records import checked_json, proof, publish

root = ROOT/"data/benchmark/tether-equal-policy-v2-patched-20261105-attempt01"
pin = proof(root/"FROZEN.json")
assert pin["sha256"] == controller.FROZEN_SHA
frozen = checked_json(root/"FROZEN.json", pin)
pins = controller.corpus_pins(root, frozen)
pins[str(root/"FROZEN.json")] = pin
result = controller.global_source_audit({"input_pins": pins, "corpus_root": str(root), "corpus": pin})
publish(Path(__file__).parent/"INVENTORY-QUALIFICATION-01.json", {
    "status": "pass", "read_only": True, "cases_executed": 0, "corpus": pin,
    "source": proof(ROOT/"experiments/inspect_policy/controller.py"),
    "tests": proof(ROOT/"experiments/inspect_policy/tests/test_controller.py"),
    "green_test_log": proof(Path(__file__).parent.parent/"controller-tests08-inventory-green.log"),
    "inventory_audit": result})
print("PASS: original corpus/source inventory, zero cases executed")
