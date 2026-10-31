"""Fixed approved local launch capability; no archive-selected code or callbacks."""

from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import math
from importlib import resources
from pathlib import Path
import re
import subprocess
import sys
import time
from threading import Lock

from asof.serde import canonical, encode, fingerprint, freeze, parse_json
from .baseline_smoke import _read, _write
from .collected_source import _guard
from .diagnostic_codec import need
from .interpretation_interface import INTERFACE
from . import native, tokenization
from .process import OwnedServer, ServerSpec, _port_free
from .stable_read import checked_path, deadline_check, hash_file, stable_files

RESOURCE = "resources/native-server-v2.json"
RESOURCE_SHA256 = "141dcda167de67078d28bb39a0b2f380278ec0647e5f3e218e05a4ea38bc131d"
ALIAS = "asof-interpretation-v2"
_DEFAULT_PROCESS_FACTORY = subprocess.Popen
FILES = {
    "native-mode.json",
    "native-locations.json",
    "native/server-command.json",
    "native/server.stdout.log",
    "native/server.stderr.log",
    "native/server-terminal.json",
}
TRACKS = (
    "authority_bound_invented_four_arm_native_v2",
    "authority_bound_collected_source_four_arm_native_v2",
)


def _resource():
    raw = resources.files("asof.study").joinpath(RESOURCE).read_bytes()
    need(
        hashlib.sha256(raw).hexdigest() == RESOURCE_SHA256,
        "Approved native server resource differs",
    )
    value = parse_json(raw)
    need(
        value["schema_version"] == 1
        and value["kind"] == "approved_owned_native_server_v2"
        and value["tokenizer_resource_sha256"] == tokenization.RESOURCE_SHA256,
        "Native/tokenizer authority differs",
    )
    return freeze(value)


def _assets(spec):
    spec = tokenization._validate_spec(spec)
    server = _resource()["server"]
    need(
        server["relative_path"] not in {a["relative_path"] for a in spec["assets"]},
        "Duplicate server identity",
    )
    return [*spec["assets"], server]


def description(spec, port):
    spec = tokenization._validate_spec(spec)
    assets = _assets(spec)
    return freeze(
        dict(
            schema_version=1,
            kind="approved_local_native_execution_v2",
            interface=INTERFACE,
            resource_sha256=RESOURCE_SHA256,
            port=port,
            model_alias=ALIAS,
            context_tokens=16384,
            slots=1,
            tokenizer_spec_sha256=fingerprint(spec),
            asset_count=len(assets),
            asset_manifest_sha256=fingerprint(assets),
            model_provenance=dict(
                weights_sha256={
                    Path(a["relative_path"]).name: a["sha256"]
                    for a in assets
                    if a["relative_path"].endswith(".gguf")
                },
                runtime_sha256=_resource()["server"]["sha256"],
                asset_manifest_sha256=spec["authority"]["inventory_sha256"],
            ),
            provider_spend_usd=0,
            automatic_retries=False,
        )
    )


def _argv(root, spec, port):
    assets = _assets(spec)
    first = [a for a in assets if "00001-of-00003.gguf" in a["relative_path"]]
    need(len(first) == 1, "Approved first model shard differs")
    return (
        str(checked_path(root, _resource()["server"]["relative_path"])),
        "--model",
        str(checked_path(root, first[0]["relative_path"])),
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--ctx-size",
        "16384",
        "--parallel",
        "1",
        "--n-gpu-layers",
        "99",
        "--threads",
        "8",
        "--alias",
        ALIAS,
        "--no-webui",
        "--offline",
        "-lv",
        "4",
    )


@dataclass(frozen=True)
class NativeExecutionConfig:
    model_root: Path
    port: int
    execution_scope: str = "owned_native"
    listener_owner: object = field(
        default=native.windows_listener_owner, repr=False, compare=False
    )
    health_probe: object = field(
        default=native.bounded_health_probe, repr=False, compare=False
    )
    process_factory: object = field(default=subprocess.Popen, repr=False, compare=False)
    availability_probe: object = field(default=_port_free, repr=False, compare=False)
    _active: int = field(default=0, init=False, repr=False, compare=False)
    _used: bool = field(default=False, init=False, repr=False, compare=False)
    _lock: object = field(default_factory=Lock, init=False, repr=False, compare=False)

    def __post_init__(self):
        path = Path(self.model_root)
        need(
            path.is_absolute() and not path.drive.startswith("\\\\"),
            "Explicit local model root required",
        )
        _guard(path)
        need(
            type(self.port) is int and 1 <= self.port <= 65535,
            "Invalid explicit native port",
        )
        need(
            self.execution_scope in ("owned_native", "simulated_native_transport"),
            "Invalid explicit native execution scope",
        )
        need(
            all(
                callable(f)
                for f in (
                    self.listener_owner,
                    self.health_probe,
                    self.process_factory,
                    self.availability_probe,
                )
            ),
            "Trusted native callbacks must be supplied as code",
        )
        object.__setattr__(self, "model_root", path)

    def describe(self, spec):
        return freeze(
            dict(description(spec, self.port), execution_scope=self.execution_scope)
        )

    def assert_active(self):
        need(
            self._active > 0,
            "Native verification requires an active approved-asset lease",
        )

    @contextmanager
    def locked(self, spec, deadline):
        deadline_check(deadline)
        assets = _assets(spec)
        paths = [checked_path(self.model_root, a["relative_path"]) for a in assets]
        relocated = tokenization._spec(tokenization._resource(), self.model_root)
        with stable_files(paths, deadline=deadline):
            tokenization._inventory(relocated)
            for asset, path in zip(assets, paths):
                actual = hash_file(path, deadline)
                need(
                    actual["sha256"] == asset["sha256"]
                    and actual["bytes"] == asset["bytes"],
                    "Approved native asset differs: " + asset["relative_path"],
                )
            object.__setattr__(self, "_active", self._active + 1)
            try:
                yield self
                tokenization._inventory(relocated)
                deadline_check(deadline)
            finally:
                object.__setattr__(self, "_active", self._active - 1)

    def server_spec(self, spec, deadline):
        deadline_check(deadline)
        assets = _assets(spec)
        proofs = [
            dict(logical_id=f"asset-{i:03d}", sha256=a["sha256"], bytes=a["bytes"])
            for i, a in enumerate(assets)
        ]
        remaining = deadline - time.monotonic()
        return ServerSpec(
            _argv(self.model_root, spec, self.port),
            proofs[-1],
            tuple(proofs[:-1]),
            "127.0.0.1",
            self.port,
            min(180, remaining),
            min(30, remaining),
            min(10, remaining),
        )

    def context(self, spec, owner):
        self.assert_active()
        value = self.describe(spec)
        return freeze(
            dict(
                endpoint=f"http://127.0.0.1:{self.port}",
                owner_pid=owner.terminal_record["pid"],
                model_alias=ALIAS,
                model_provenance=value["model_provenance"],
            )
        )

    def check_archive(self, root, spec):
        self.assert_active()
        value, _ = _read(root, "native-mode.json")
        locations, _ = _read(root, "native-locations.json")
        need(
            canonical(value) == canonical(self.describe(spec)),
            "Archived native mode differs",
        )
        need(
            set(locations) == {"role", "model_root"}
            and locations["role"] == "locator_metadata_not_access_authority"
            and isinstance(locations["model_root"], str)
            and Path(locations["model_root"]).is_absolute(),
            "Native locations are not access authority",
        )
        return value

    @contextmanager
    def running(self, root, journal, spec, deadline):
        self.assert_active()
        need(
            self.execution_scope != "simulated_native_transport"
            or self.process_factory is not _DEFAULT_PROCESS_FACTORY,
            "Simulated transport cannot launch the default real process",
        )
        need(self._lock.acquire(blocking=False), "Native configuration already in use")
        try:
            need(not self._used, "Native configuration cannot launch twice")
            object.__setattr__(self, "_used", True)
        finally:
            self._lock.release()
        deadline_check(deadline)
        need(
            Path(spec["model_root"]) == self.model_root,
            "Execution tokenizer/model root differs",
        )
        folder = root / "native"
        folder.mkdir(exist_ok=False)
        value = self.describe(spec)
        _write(root, "native-mode.json", value)
        _write(
            root,
            "native-locations.json",
            dict(
                role="locator_metadata_not_access_authority",
                model_root=str(self.model_root),
            ),
        )
        journal.append(
            "native_preparing",
            descriptor_sha256=fingerprint(value),
            elapsed_seconds=300 - (deadline - time.monotonic()),
        )
        launch = self.server_spec(spec, deadline)
        assets = _assets(spec)
        bindings = {
            f"asset-{i:03d}": checked_path(self.model_root, a["relative_path"])
            for i, a in enumerate(assets)
        }
        owner = OwnedServer(
            launch,
            bindings=bindings,
            output=folder,
            journal=journal,
            listener_owner=self.listener_owner,
            health_probe=self.health_probe,
            process_factory=self.process_factory,
            availability_probe=self.availability_probe,
            monotonic=time.monotonic,
            parent_deadline=deadline,
        )
        try:
            with owner:
                deadline_check(deadline)
                with (folder / "server.stderr.log").open("rb") as stream:
                    startup = stream.read(1024 * 1024 + 1)
                need(
                    len(startup) <= 1024 * 1024
                    and re.search(
                        rb"n_slots\s*=\s*1,\s*n_ctx_slot\s*=\s*16384", startup
                    ),
                    "Actual owned context not qualified",
                )
                journal.append(
                    "native_context_qualified",
                    context=encode(self.context(spec, owner)),
                    context_tokens=16384,
                    slots=1,
                    startup_bytes=len(startup),
                    startup_sha256=hashlib.sha256(startup).hexdigest(),
                    elapsed_seconds=300 - (deadline - time.monotonic()),
                )
                yield owner
        finally:
            primary = sys.exception()
            try:
                _write(folder, "server-terminal.json", owner.terminal_record)
                journal.append(
                    "native_stopped",
                    terminal_sha256=fingerprint(owner.terminal_record),
                    elapsed_seconds=300 - (deadline - time.monotonic()),
                )
            except BaseException as secondary:
                if primary is None:
                    raise
                primary.add_note(
                    "Native terminal retention: " + type(secondary).__name__
                )
        deadline_check(deadline)

    @classmethod
    def from_run(cls, root, roots):
        need(
            isinstance(roots, Mapping) and set(roots) == {"model"},
            "Explicit approved native model root required",
        )
        value, _ = _read(root, "native-mode.json")
        spec, _ = _read(root, "tokenizer-spec.json")
        need(
            isinstance(value, Mapping) and type(value.get("port")) is int,
            "Invalid archived native port",
        )
        result = cls(
            Path(roots["model"]),
            value["port"],
            execution_scope=value.get("execution_scope"),
        )
        need(
            canonical(value) == canonical(result.describe(spec)),
            "Native archive description differs",
        )
        return result

    def verify_archive(self, root, spec, events, *, successful):
        value = self.check_archive(root, spec)

        def one(name):
            rows = [e["details"] for e in events if e["event"] == name]
            need(len(rows) == 1, "Missing or duplicate " + name)
            return rows[0]

        preparing = one("native_preparing")
        need(
            preparing["descriptor_sha256"] == fingerprint(value),
            "Native preparation authority differs",
        )
        ready = one("native_context_qualified")
        times = [preparing["elapsed_seconds"], ready["elapsed_seconds"]]
        if successful:
            times.append(one("native_stopped")["elapsed_seconds"])
        need(
            all(
                type(t) in (int, float) and math.isfinite(t) and 0 <= t < 300
                for t in times
            )
            and times == sorted(times),
            "Native clock is nonfinite, expired or moves backwards",
        )
        context = ready["context"]
        need(
            ready["context_tokens"] == 16384
            and ready["slots"] == 1
            and context["endpoint"] == f"http://127.0.0.1:{self.port}"
            and context["model_alias"] == ALIAS
            and canonical(context["model_provenance"])
            == canonical(value["model_provenance"])
            and type(context["owner_pid"]) is int
            and context["owner_pid"] > 0,
            "Native context identity differs",
        )
        for name in ("server_started", "server_ready"):
            need(
                one(name) == freeze(dict(pid=context["owner_pid"])),
                "Owned server readiness differs",
            )
        count = ready["startup_bytes"]
        need(
            type(count) is int and 0 < count <= 1024 * 1024,
            "Invalid owned startup prefix",
        )
        with (root / "native/server.stderr.log").open("rb") as stream:
            startup = stream.read(count)
        need(
            len(startup) == count
            and hashlib.sha256(startup).hexdigest() == ready["startup_sha256"]
            and re.search(rb"n_slots\s*=\s*1,\s*n_ctx_slot\s*=\s*16384", startup),
            "Owned startup bytes differ",
        )
        command, _ = _read(root / "native", "server-command.json")
        locations, _ = _read(root, "native-locations.json")
        archived_root = Path(locations["model_root"])
        # Original argv strings establish what was launched, never grant read access.
        assets = _assets(spec)
        first = next(a for a in assets if "00001-of-00003.gguf" in a["relative_path"])
        expected_argv = [
            str(archived_root / _resource()["server"]["relative_path"]),
            "--model",
            str(archived_root / first["relative_path"]),
            "--host",
            "127.0.0.1",
            "--port",
            str(self.port),
            "--ctx-size",
            "16384",
            "--parallel",
            "1",
            "--n-gpu-layers",
            "99",
            "--threads",
            "8",
            "--alias",
            ALIAS,
            "--no-webui",
            "--offline",
            "-lv",
            "4",
        ]
        need(
            set(command)
            == {
                "argv",
                "executable",
                "required_inputs",
                "host",
                "port",
                "startup_seconds",
                "terminate_seconds",
                "kill_seconds",
            }
            and command["argv"] == expected_argv
            and command["host"] == "127.0.0.1"
            and command["port"] == self.port,
            "Archived native command differs",
        )
        proofs = [
            dict(logical_id=f"asset-{i:03d}", sha256=a["sha256"], bytes=a["bytes"])
            for i, a in enumerate(assets)
        ]
        need(
            canonical(command["executable"]) == canonical(proofs[-1])
            and canonical(command["required_inputs"]) == canonical(proofs[:-1]),
            "Archived launch input proofs differ",
        )
        for key, maximum in (
            ("startup_seconds", 180),
            ("terminate_seconds", 30),
            ("kill_seconds", 10),
        ):
            v = command[key]
            need(
                type(v) in (int, float)
                and 0 < v <= min(maximum, 300 - preparing["elapsed_seconds"]) + 1e-6,
                "Archived launch bounds exceed parent",
            )
        if successful:
            terminal, _ = _read(root / "native", "server-terminal.json")
            stopped = one("native_stopped")
            need(
                canonical(terminal) == canonical(one("server_terminal"))
                and stopped["terminal_sha256"] == fingerprint(terminal)
                and terminal["started"] is True
                and terminal["server_stopped"] is True
                and terminal["pid"] == context["owner_pid"]
                and not terminal["secondary_failures"]
                and "error_class" not in terminal
                and type(terminal["exit_code"]) is int,
                "Owned server did not close successfully",
            )
            need(
                0
                <= terminal["elapsed_seconds"]
                <= stopped["elapsed_seconds"] - preparing["elapsed_seconds"] + 1e-6,
                "Owned elapsed time differs",
            )
        return freeze(context)
