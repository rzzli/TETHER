"""Fresh mock-only smoke; permit Windows stdlib self-pipe, deny external traffic."""
from datetime import datetime, timezone
import hashlib
import importlib.metadata as metadata
import inspect
import ipaddress
import json
import os
from pathlib import Path
import socket
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
TARGET = ROOT/"data/cache/tether-inspect-env-attempt02"
EVIDENCE = Path(__file__).parent/"attempt02"


def write(path, value):
    with Path(path).open("xb") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2).encode()+b"\n")


def main():
    started = time.monotonic()
    assert Path(sys.prefix).resolve() == (TARGET/"environment").resolve()
    assert metadata.version("inspect-ai") == "0.3.287"
    work = TARGET/"mock-eval-attempt02"
    work.mkdir(exist_ok=False)
    os.chdir(work)
    os.environ.update(INSPECT_CACHE_DIR=str(work/"cache"), INSPECT_LOG_DIR=str(work/"logs"),
                      TIKTOKEN_CACHE_DIR=str(work/"tiktoken-cache"), PYTHON_DOTENV_DISABLED="1")
    allowed, blocked = [], []
    stdlib_socket = str(Path(socket.__file__).resolve())
    def audit(event, args):
        if event not in ("socket.connect", "socket.getaddrinfo", "socket.sendto"):
            return
        frame = sys._getframe(1)
        self_pipe = False
        while frame is not None:
            if frame.f_code.co_name == "_fallback_socketpair" and str(Path(frame.f_code.co_filename).resolve()) == stdlib_socket:
                self_pipe = True
                break
            frame = frame.f_back
        if event == "socket.connect" and self_pipe and ipaddress.ip_address(args[1][0]).is_loopback:
            allowed.append({"event": event, "purpose": "Windows stdlib asyncio socketpair", "loopback": True})
            return
        blocked.append({"event": event})
        raise PermissionError("External/non-self-pipe network denied during mock qualification")
    sys.addaudithook(audit)
    from inspect_ai import Task, eval
    from inspect_ai.dataset import Sample
    from inspect_ai.model import ModelAPI, ModelOutput, ModelUsage, GenerateConfig
    from inspect_ai.solver import TaskState, generate
    from inspect_ai.scorer import match
    outputs = []
    for value in ("fictional-blue", "fictional-wrong"):
        output = ModelOutput.from_content(model="mockllm", content=value)
        output.usage = ModelUsage(input_tokens=7, output_tokens=2, total_tokens=9)
        outputs.append(output)
    task = Task(name="inspect_environment_mock", dataset=[
        Sample(id="fictional-1", input="Invented color?", target="fictional-blue"),
        Sample(id="fictional-2", input="Another invented color?", target="fictional-green")],
        solver=generate(), scorer=match(location="exact"))
    logs = eval(task, model="mockllm/model", model_args={"custom_outputs": outputs}, display="none",
        log_dir=str(work/"logs"), log_format="json", fail_on_error=True, retry_on_error=0, score_on_error=False,
        max_retries=0, max_samples=1, max_tasks=1, time_limit=30, log_shared=False, notification=False,
        log_samples=True, log_model_api=True)
    assert len(logs) == 1 and logs[0].status == "success", "Mock evaluation did not complete"
    log = logs[0]
    assert log.samples is not None and len(log.samples) == 2
    values = [sample.scores["match"].value for sample in log.samples]
    assert values == ["C", "I"] and not blocked, "Mock score or external isolation differs"
    write(EVIDENCE/"MOCK-EVAL-02.json", {"status": "pass", "sample_count": 2, "scores": values,
        "model": "mockllm/model", "mock_generation_count": 2, "real_model_calls": 0, "external_provider_calls": 0,
        "blocked_network_attempts": blocked, "allowed_stdlib_loopback_events": allowed, "provider_cost_usd": 0,
        "usage_basis": "Explicit synthetic fixture usage; not measured model tokens", "retry_on_error": 0,
        "max_retries": 0, "log_location": str(log.location), "results": log.results.model_dump(mode="json"),
        "stats": log.stats.model_dump(mode="json"), "elapsed_seconds": time.monotonic()-started})
    api = {"ModelAPI.__init__": str(inspect.signature(ModelAPI.__init__)),
           "ModelAPI.generate": str(inspect.signature(ModelAPI.generate)), "TaskState": str(inspect.signature(TaskState)),
           "GenerateConfig": str(inspect.signature(GenerateConfig)), "eval": str(inspect.signature(eval))}
    write(EVIDENCE/"OBSERVED-API.json", {"inspect_ai_version": "0.3.287", "signatures": api})
    print(json.dumps({"status": "pass", "mock_samples": 2, "external_calls": 0, "self_pipe_events": len(allowed)}))


if __name__ == "__main__":
    try:
        main()
    except BaseException as exc:
        write(EVIDENCE/"MOCK-FAILED-02.json", {"error_class": type(exc).__name__, "message": str(exc),
              "at": datetime.now(timezone.utc).isoformat(), "automatic_retry": False})
        raise
