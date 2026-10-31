"""Root-reviewed once-only driver; a pinned root decision is required separately."""
from importlib import util
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
HELPER = HERE / "run_self_module_census_v3.py"
HELPER_SHA = "018f3c8216b6096e34eff43241c3864a9a15f0decbdde6005f2b905c5e6c247d"
PROTOCOL = HERE / "SELF-MODULE-CENSUS-EXECUTION-PROTOCOL-v2.json"
PROTOCOL_SHA = "8f011fc7bdc3a92033cd3ab5277b7346a512b08c447234ff2aedeefb3a192215"
DECISION = HERE / "SELF-MODULE-CENSUS-EXECUTION-ROOT-DECISION-v1.json"


def pin(path):
    path = Path(path)
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(path=str(path), bytes=path.stat().st_size, sha256=digest)


def main(args):
    if len(args) != 2 or args[0] != "--execute-once":
        raise RuntimeError("Exact separately retained root-decision SHA required")
    expected = args[1]
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise RuntimeError("Malformed decision hash")
    if pin(DECISION)["sha256"] != expected:
        raise RuntimeError("Root decision bytes differ")
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    if (decision["status"] != "root_authorizes_one_exact_self_module_census_observation"
            or decision["driver"] != pin(__file__) or decision["helper"] != pin(HELPER)
            or decision["protocol"] != pin(PROTOCOL)
            or decision["helper"]["sha256"] != HELPER_SHA
            or decision["protocol"]["sha256"] != PROTOCOL_SHA
            or decision["maximum_attempts"] != 1 or decision["automatic_retry"] is not False):
        raise RuntimeError("Exact once-only root decision differs")
    config = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if (config["output"] != decision["output"] or config["limits"] != decision["limits"]
            or config["mode"] != "--module-census" or Path(config["output"]).exists()):
        raise RuntimeError("Census role/output already consumed or differs")
    for item in config["inputs"]:
        if pin(item["path"]) != item:
            raise RuntimeError("Pinned census input changed")
    spec = util.spec_from_file_location("exact_root_census_parent", HELPER)
    helper = util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.validate_role(config)
    result = helper.execute(config, PROTOCOL_SHA)  # Exactly one call; never retry.
    print(json.dumps(dict(status=result["status"], output=config["output"])))
    return 0 if result["status"] == helper.STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
