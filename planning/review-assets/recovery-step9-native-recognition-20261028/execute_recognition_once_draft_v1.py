"""Unbound source-only recognition driver; this file grants no execution authority.

Freeze a separately named successor only after the parent, actual build proof and
protocol are independently reviewed. No current helper/protocol is bound here.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
import types

BOUND = False
HELPER = None
HELPER_SHA = None
PROTOCOL = None
PROTOCOL_SHA = None
DECISION = None
SUCCESS_STATUS = "recognition_observations_retained_independent_qualification_pending"
DECISION_STATUS = "root_authorizes_one_exact_frozen_pack_singleton_recognition_observation"
PARENT_SECONDS = 300
FINALIZATION_SECONDS = 5
TECHNICAL_FILE_BYTES = 2 * 1024 * 1024
CONTRACT_SHA = "30d82a42c5338789644fea00f666e264fb3e4114637c2c37330386a177f17861"
POLICY_SHA = "4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713"
FROZEN_PACK = dict(
    path=r"D:\Projects\drug_target_agents\data\cache\r09-native-recognition-pack-v2-20261028T183647Z\recognition.pack",
    bytes=259867,
    sha256="f75ab9937c57b5f03c2234643a8a9c91cda852ca0cca0de0478369f793e57e5f",
)
ORDERED_SHARDS = [
    r"D:\Projects\drug_target_agents\data\cache\approved-native-mirror-20261028T004531Z\qwen2.5-14b-instruct-q4_k_m-00001-of-00003.gguf",
    r"D:\Projects\drug_target_agents\data\cache\approved-native-mirror-20261028T004531Z\qwen2.5-14b-instruct-q4_k_m-00002-of-00003.gguf",
    r"D:\Projects\drug_target_agents\data\cache\approved-native-mirror-20261028T004531Z\qwen2.5-14b-instruct-q4_k_m-00003-of-00003.gguf",
]
PROFILE = dict(parent_seconds=300, child_seconds=120, child_cleanup_reserved_seconds=2,
               finalization_reserved_seconds=5, process_and_job_commit_bytes=268435456,
               active_processes=1, maximum_children=1, stream_bytes=65536,
               result_bytes=8388608, row_bytes=65536)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def check_clock(deadline, stage):
    if time.monotonic() >= deadline:
        raise TimeoutError("Recognition owner deadline reached: " + stage)


def technical_file(path, deadline):
    """Only main's four fixed technical paths enter here; never config.inputs.

    Parse/import the same bounded bytes that were hashed. Checks before and
    after each read reject overrun; they are cooperative checks, not an OS I/O
    interruption guarantee. There are at most four files and 8 MiB total.
    """
    path = Path(path)
    check_clock(deadline, "before technical read")
    chunks = []
    count = 0
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            check_clock(deadline, "before technical block")
            block = stream.read(min(65536, TECHNICAL_FILE_BYTES + 1 - count))
            check_clock(deadline, "after technical block")
            if not block:
                break
            count += len(block)
            if count > TECHNICAL_FILE_BYTES:
                raise RuntimeError("Technical file exceeds fixed cap")
            digest.update(block)
            chunks.append(block)
    check_clock(deadline, "after technical close")
    return dict(path=str(path), bytes=count, sha256=digest.hexdigest()), b"".join(chunks)


def load_helper(raw, path, deadline):
    check_clock(deadline, "before helper import")
    module = types.ModuleType("exact_root_recognition_parent")
    module.__file__ = str(path)
    exec(compile(raw, str(path), "exec"), module.__dict__)
    check_clock(deadline, "after helper import")
    return module


def main(args):
    started = time.monotonic()  # Before binding checks, hashes, parsing or helper import.
    owner_end = started + PARENT_SECONDS
    work_end = owner_end - FINALIZATION_SECONDS
    if not BOUND or any(value is None for value in (HELPER, HELPER_SHA, PROTOCOL, PROTOCOL_SHA, DECISION)):
        raise RuntimeError("Source-only driver is unbound; no execution permitted")
    if len(args) != 2 or args[0] != "--execute-once":
        raise RuntimeError("Exact separately retained root-decision SHA required")
    expected = args[1]
    if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
        raise RuntimeError("Malformed decision hash")
    decision_pin, decision_raw = technical_file(DECISION, work_end)
    if decision_pin["sha256"] != expected:
        raise RuntimeError("Root decision bytes differ")
    decision = json.loads(decision_raw)
    driver_pin, _ = technical_file(__file__, work_end)
    helper_pin, helper_raw = technical_file(HELPER, work_end)
    protocol_pin, protocol_raw = technical_file(PROTOCOL, work_end)
    if (decision["status"] != DECISION_STATUS
            or decision["driver"] != driver_pin or decision["helper"] != helper_pin
            or decision["protocol"] != protocol_pin
            or helper_pin["sha256"] != HELPER_SHA or protocol_pin["sha256"] != PROTOCOL_SHA
            or type(decision["maximum_attempts"]) is not int or decision["maximum_attempts"] != 1
            or decision["automatic_retry"] is not False or decision["success_status"] != SUCCESS_STATUS
            or canonical(decision["frozen_pack"]) != canonical(FROZEN_PACK)):
        raise RuntimeError("Exact once-only recognition root decision differs")
    config = json.loads(protocol_raw)
    argv = config["argv"]
    if (config["kind"] != "detached_singleton_recognition_observation_v1"
            or config["mode"] != "--recognize" or config["output"] != decision["output"]
            or canonical(config["limits"]) != canonical(decision["limits"])
            or canonical({key: config["limits"][key] for key in PROFILE}) != canonical(PROFILE)
            or canonical(config["argv"]) != canonical(decision["argv"])
            or type(argv) is not list or len(argv) != 9 or any(type(arg) is not str or not arg or "\0" in arg for arg in argv)
            or argv[0] != config["executable"]["path"] or argv[1] != "--recognize"
            or argv[4] != FROZEN_PACK["path"] or argv[5] != "ggml-cpu-x64.dll" or argv[6:] != ORDERED_SHARDS
            or config["expected_pack_sha256"] != FROZEN_PACK["sha256"] or config["contract_sha256"] != CONTRACT_SHA
            or config["module_policy_sha256"] != POLICY_SHA or config["expected_version"] != "0.7.0-dev"
            or type(config["maximum_attempts"]) is not int or config["maximum_attempts"] != 1
            or config["automatic_retry"] is not False or config["full_vocabulary_mask"] is not False
            or config["inference"] is not False or config["original_SDK_general_gate"] is not False
            or canonical([config["parent_seconds"], config["child_seconds"], config["cooperative_work_ms"], config["creation_flags"]])
            != canonical([300, 120, 117000, 0x0008040C])
            or type(config["hash_pass_policy"]["driver_model_passes"]) is not int
            or config["hash_pass_policy"]["driver_model_passes"] != 0):
        raise RuntimeError("Exact full frozen-pack singleton recognition role differs")
    check_clock(work_end, "before output check")
    if Path(config["output"]).exists():
        raise RuntimeError("Recognition output already consumed; no repeat")
    check_clock(work_end, "before helper import")
    # Do not loop over config.inputs or call validate_role: the parent performs
    # runtime leases/hash/role checks inside execute under this original clock.
    helper = load_helper(helper_raw, HELPER, work_end)
    check_clock(work_end, "before single execute")
    result = helper.execute(config, PROTOCOL_SHA, owner_started=started)  # One call; no retry or catch/restart.
    check_clock(owner_end, "after parent sealing")
    print(json.dumps(dict(status=result["status"], output=config["output"],
                          owner_elapsed_seconds=time.monotonic() - started)))
    return 0 if result["status"] == SUCCESS_STATUS else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
