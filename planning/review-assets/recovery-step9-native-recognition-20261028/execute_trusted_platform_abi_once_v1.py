"""Root-reviewed once-only driver; a pinned root decision is required separately."""
from importlib import util
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
HELPER = HERE / "run_platform_abi_observation_v2.py"
HELPER_SHA = "f2682469f48919698d4ba702920888e8b2175b63161080afc62604668d639ef5"
PROTOCOL = HERE / "TRUSTED-PLATFORM-ABI-EXECUTION-PROTOCOL-v1.json"
PROTOCOL_SHA = "5e1755588ef3788540dd5a5775e1948803af05259bcabf1ff680b7e88de6866e"
DECISION = HERE / "TRUSTED-PLATFORM-ABI-EXECUTION-ROOT-DECISION-v1.json"
SUCCESS_STATUS = "ABI_observations_retained_independent_qualification_pending"


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
    if (decision["status"] != "root_authorizes_one_exact_trusted_platform_ABI_observation"
            or decision["driver"] != pin(__file__) or decision["helper"] != pin(HELPER)
            or decision["protocol"] != pin(PROTOCOL)
            or decision["helper"]["sha256"] != HELPER_SHA
            or decision["protocol"]["sha256"] != PROTOCOL_SHA
            or type(decision["maximum_attempts"]) is not int
            or decision["maximum_attempts"] != 1 or decision["automatic_retry"] is not False
            or decision["success_status"] != SUCCESS_STATUS):
        raise RuntimeError("Exact once-only root decision differs")
    config = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if (config["output"] != decision["output"] or json.dumps(config["limits"], sort_keys=True) != json.dumps(decision["limits"], sort_keys=True)
            or config["mode"] != "--abi" or Path(config["output"]).exists()
            or config["explicit_target_calls"] != ["llama_version", "llama_model_default_params"]
            or config["recognition_enabled"] is not False or config["no_model_or_CPU_paths_supplied"] is not True):
        raise RuntimeError("ABI role/output already consumed or differs")
    for item in config["inputs"]:
        if pin(item["path"]) != item:
            raise RuntimeError("Pinned ABI input changed")
    spec = util.spec_from_file_location("exact_root_platform_ABI_parent", HELPER)
    helper = util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    helper.validate_role(config)
    result = helper.execute(config, PROTOCOL_SHA)  # Exactly one call; never retry.
    print(json.dumps(dict(status=result["status"], output=config["output"])))
    return 0 if result["status"] == SUCCESS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
