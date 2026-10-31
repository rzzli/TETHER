"""Own one non-daemonizing server; never discover a process to kill by port."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.error

from asof.atomic import publish_bytes
from asof.serde import ContractError, Frozen, canonical, freeze
from .proofs import verify_file


@dataclass(frozen=True)
class ServerSpec(Frozen):
    argv: tuple[str, ...]
    executable: Mapping
    required_inputs: tuple[Mapping, ...]
    host: str
    port: int
    startup_seconds: float = 180
    terminate_seconds: float = 30
    kill_seconds: float = 10


def _port_free(host, port):
    with socket.socket() as probe:
        probe.bind((host, port))


class OwnedServer:
    """Trusted callbacks establish ownership and bounded readiness, never generation.

    listener_owner(pid, host, port) must return exactly True only for the owned
    listener; health_probe(host, port, timeout) returns exactly True when healthy.
    All other results remain unready. Only the retained Popen handle is cleaned.
    Test injection is trusted Python configuration, not archive-selected code.
    """

    def __init__(
        self,
        spec: ServerSpec,
        *,
        bindings: Mapping[str, Path],
        output: Path,
        journal,
        listener_owner,
        health_probe,
        process_factory=subprocess.Popen,
        availability_probe=_port_free,
        monotonic=time.monotonic,
        sleep=time.sleep,
        parent_deadline=None,
    ):
        if not isinstance(spec, ServerSpec):
            raise ContractError("Invalid server specification")
        if (
            spec.host != "127.0.0.1"
            or type(spec.port) is not int
            or not 1 <= spec.port <= 65535
            or not spec.argv
            or any(
                not isinstance(arg, str) or not arg or "\0" in arg for arg in spec.argv
            )
            or any(
                type(value) not in (int, float)
                or not math.isfinite(value)
                or value <= 0
                for value in (
                    spec.startup_seconds,
                    spec.terminate_seconds,
                    spec.kill_seconds,
                )
            )
        ):
            raise ContractError("Invalid bounded loopback server specification")
        if not all(
            callable(fn)
            for fn in (
                listener_owner,
                health_probe,
                process_factory,
                availability_probe,
                monotonic,
                sleep,
            )
        ):
            raise ContractError("Explicit trusted server callbacks required")
        self.spec, self.bindings = (
            spec,
            {name: Path(path).absolute() for name, path in bindings.items()},
        )
        self.output, self.journal = Path(output).absolute(), journal
        self.listener_owner, self.health_probe = listener_owner, health_probe
        self.factory, self.availability_probe = process_factory, availability_probe
        self.monotonic, self.sleep = monotonic, sleep
        if parent_deadline is not None and (
            type(parent_deadline) not in (int, float)
            or not math.isfinite(parent_deadline)
        ):
            raise ContractError("Invalid owned-server parent deadline")
        self.parent_deadline = parent_deadline
        self._process, self._logs = None, []
        self._used = self._ready = self._closed = False
        self._record = dict(
            started=False,
            server_stopped=None,
            exit_code=None,
            secondary_failures=[],
            peak_native_memory_bytes=None,
            peak_native_memory_reason="Not instrumented",
        )

    @property
    def terminal_record(self):
        return freeze(self._record)

    def _secondary(self, primary, error, stage):
        self._record["secondary_failures"].append(
            dict(stage=stage, error_class=type(error).__name__)
        )
        if primary is None:
            return error
        primary.add_note(stage + ": " + type(error).__name__)
        return primary

    def _close_logs(self, primary):
        while self._logs:
            stream = self._logs.pop()
            try:
                stream.close()
            except BaseException as error:
                primary = self._secondary(primary, error, "server_log_close")
        return primary

    def __enter__(self):
        if self._used:
            raise ContractError("Owned server cannot be reused")
        self._used = True
        self._started_at = None
        try:
            self._started_at = self.monotonic()
            proofs = (self.spec.executable, *self.spec.required_inputs)
            if (
                any(not isinstance(p, Mapping) or "logical_id" not in p for p in proofs)
                or len({p["logical_id"] for p in proofs}) != len(proofs)
                or set(self.bindings) != {p["logical_id"] for p in proofs}
            ):
                raise ContractError("Server input bindings differ from proofs")
            for proof in proofs:
                verify_file(self.bindings[proof["logical_id"]], proof)
            executable = self.bindings[self.spec.executable["logical_id"]]
            if (
                not Path(self.spec.argv[0]).is_absolute()
                or Path(self.spec.argv[0]).resolve() != executable.resolve()
            ):
                raise ContractError(
                    "Command executable differs from verified executable"
                )
            if not self.output.is_dir():
                raise ContractError(
                    "Server output must be an already reserved directory"
                )
            self.availability_probe(self.spec.host, self.spec.port)
            publish_bytes(self.output / "server-command.json", canonical(self.spec))
            for name in ("server.stdout.log", "server.stderr.log"):
                self._logs.append((self.output / name).open("xb"))
            if (
                self.parent_deadline is not None
                and self.monotonic() >= self.parent_deadline
            ):
                raise TimeoutError("Owned-server parent expired before spawn")
            self._process = self.factory(
                list(self.spec.argv),
                stdout=self._logs[0],
                stderr=self._logs[1],
                shell=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                if os.name == "nt"
                else 0,
            )
            # Preserve ownership before any operation that can fail after spawn.
            self._record.update(started=True, pid=self._process.pid)
            deadline = self.monotonic() + self.spec.startup_seconds
            if self.parent_deadline is not None:
                deadline = min(deadline, self.parent_deadline)
            close_error = self._close_logs(None)
            if close_error is not None:
                raise close_error
            self.journal.append("server_started", pid=self._process.pid)
            while self.monotonic() < deadline:
                if self._process.poll() is not None:
                    raise ContractError("Owned server exited during startup")
                if (
                    self.listener_owner(
                        self._process.pid, self.spec.host, self.spec.port
                    )
                    is True
                ):
                    remaining = deadline - self.monotonic()
                    if remaining <= 0:
                        break
                    try:
                        healthy = self.health_probe(
                            self.spec.host, self.spec.port, min(1.0, remaining)
                        )
                    except (ConnectionError, TimeoutError, urllib.error.URLError):
                        healthy = False
                    if healthy is True:
                        self._ready = True
                        self.assert_ready()
                        if self.monotonic() >= deadline:
                            raise TimeoutError(
                                "Owned server readiness exceeded startup deadline"
                            )
                        self.journal.append("server_ready", pid=self._process.pid)
                        return self
                remaining = deadline - self.monotonic()
                if remaining > 0:
                    self.sleep(min(0.1, remaining))
            raise TimeoutError("Owned server startup timed out; no automatic relaunch")
        except BaseException as primary:
            self._finish(primary)
            raise

    def assert_ready(self):
        """Call immediately before each dispatch; an endpoint alone is not ownership."""
        if (
            not self._ready
            or self._closed
            or self._process is None
            or self._process.poll() is not None
            or self.listener_owner(self._process.pid, self.spec.host, self.spec.port)
            is not True
        ):
            raise ContractError("Owned listener is not ready")

    def _finish(self, primary):
        if self._closed:
            return primary
        self._closed, self._ready = True, False
        primary = self._close_logs(primary)
        process = self._process
        if process is not None:
            try:
                if process.poll() is None:
                    try:
                        process.terminate()
                        process.wait(
                            timeout=self._cleanup_timeout(self.spec.terminate_seconds)
                        )
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(
                            timeout=self._cleanup_timeout(self.spec.kill_seconds)
                        )
                    except BaseException as error:
                        # A failed soft stop does not abandon the process we own.
                        # Preserve that failure even if the hard stop succeeds.
                        primary = self._secondary(primary, error, "server_terminate")
                        process.kill()
                        process.wait(
                            timeout=self._cleanup_timeout(self.spec.kill_seconds)
                        )
                self._record.update(
                    server_stopped=process.poll() is not None, exit_code=process.poll()
                )
                if not self._record["server_stopped"]:
                    raise ContractError("Owned process did not stop")
            except BaseException as error:
                self._record["server_stopped"] = False
                primary = self._secondary(primary, error, "server_cleanup")
        try:
            self._record["elapsed_seconds"] = (
                self.monotonic() - self._started_at
                if self._started_at is not None
                else None
            )
        except BaseException as error:
            self._record["elapsed_seconds"] = None
            self._record["elapsed_reason"] = "Terminal clock measurement failed"
            primary = self._secondary(primary, error, "server_terminal_clock")
        if primary is not None:
            self._record["error_class"] = type(primary).__name__
        try:
            self.journal.append("server_terminal", **self.terminal_record)
        except BaseException as error:
            primary = self._secondary(primary, error, "server_terminal_journal")
            self._record["error_class"] = type(primary).__name__
        return primary

    def _cleanup_timeout(self, desired):
        if self.parent_deadline is None:
            return desired
        # A small positive bounded wait still permits stopping the retained process
        # after expiry. The caller cannot publish success after its parent deadline.
        return min(desired, max(0.001, self.parent_deadline - self.monotonic()))

    def __exit__(self, error_type, error, traceback):
        failure = self._finish(error)
        if error is None and failure is not None:
            raise failure
        return False
