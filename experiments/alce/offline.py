"""Trusted-Python offline guard with one source-bound local IPv6 probe.

This is not hostile-code or native-extension isolation. Nothing is installed on
import. Call install() explicitly in a dedicated process before library imports;
close() disables its audit callback and restores its socket method wrappers.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import os
from pathlib import Path
import re
import socket
import stat
import sys
import threading
import types


class OfflineViolation(PermissionError):
    """A network operation was refused before dispatch."""


def _read(proof, maximum):
    if (type(proof) is not dict or set(proof) != {"path", "bytes", "sha256"}
            or type(proof["bytes"]) is not int or not 0 < proof["bytes"] <= maximum
            or type(proof["sha256"]) is not str or not re.fullmatch("[0-9a-f]{64}", proof["sha256"])):
        raise ValueError("Exact bounded file proof required")
    path = Path(proof["path"])
    if not path.is_absolute() or path != path.resolve() or ".." in path.parts:
        raise ValueError("Canonical absolute proof path required")
    for item in (path, *path.parents):
        info = item.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Linked proof paths rejected")
    before = path.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if not stat.S_ISREG(before.st_mode) or before.st_size != proof["bytes"]:
        raise ValueError("Proof file size/type differs")
    with path.open("rb") as stream:
        if identity(os.fstat(stream.fileno())) != identity(before):
            raise ValueError("Proof changed before capture")
        raw = stream.read(before.st_size + 1)
        after = os.fstat(stream.fileno())
    if (identity(before) != identity(after) or identity(before) != identity(path.stat())
            or len(raw) != proof["bytes"] or hashlib.sha256(raw).hexdigest() != proof["sha256"]):
        raise ValueError("Proof bytes changed")
    return path, raw


class OfflineNetworkGuard:
    """One pinned urllib3 capability bind; all other network actions denied.

The RECORD proof must be externally anchored to the qualified installation.
Event records intentionally contain no addresses, names, URLs or payloads.
Only audit callback install/close and these counters are provided: this class
cannot issue an experiment or environment qualification receipt.
"""

    _AUDITED = frozenset({"socket.bind", "socket.connect", "socket.connect_ex",
        "socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr",
        "socket.getnameinfo", "socket.sendto", "socket.sendmsg", "socket.listen"})
    _METHODS = ("listen", "accept", "send", "sendall", "sendto", "sendmsg",
                "sendmsg_afalg", "sendfile")

    def __init__(self, record_proof, connection_proof, *, max_events=128):
        if type(max_events) is not int or not 1 <= max_events <= 4096:
            raise ValueError("Bounded event capacity required")
        record, raw_record = _read(record_proof, 8 * 1024**2)
        source, raw_source = _read(connection_proof, 2 * 1024**2)
        if (record.name != "RECORD" or not re.fullmatch(r"urllib3-[A-Za-z0-9_.+]+\.dist-info", record.parent.name)
                or source != record.parent.parent / "urllib3/util/connection.py"):
            raise ValueError("Installed urllib3 RECORD/source relationship differs")
        matches = [row for row in csv.reader(io.StringIO(raw_record.decode("utf-8")))
                   if row and row[0] == "urllib3/util/connection.py"]
        digest = base64.urlsafe_b64encode(hashlib.sha256(raw_source).digest()).rstrip(b"=").decode()
        if matches != [["urllib3/util/connection.py", "sha256=" + digest, str(len(raw_source))]]:
            raise ValueError("Installation RECORD does not bind source bytes")
        compiled = compile(raw_source, str(source), "exec", dont_inherit=True)
        codes = [x for x in compiled.co_consts if isinstance(x, types.CodeType) and x.co_name == "_has_ipv6"]
        if len(codes) != 1:
            raise ValueError("One pinned IPv6 capability function required")
        self._record_proof, self._source_proof = dict(record_proof), dict(connection_proof)
        self._source_path = source
        self._code, self._max = codes[0], max_events
        self._events, self._allowed, self._denied, self._dropped = [], 0, 0, 0
        self._lock = threading.RLock()
        self._active, self._installed, self._wrappers = True, False, {}

    def _event(self, event, disposition):
        if disposition == "allowed_local_capability_probe": self._allowed += 1
        else: self._denied += 1
        if len(self._events) < self._max:
            self._events.append({"event": event, "disposition": disposition})
        else:
            self._dropped += 1

    def _refuse(self, event):
        with self._lock:
            self._event(event, "denied_network_attempt")
        raise OfflineViolation("Offline network policy denied " + event)

    def __call__(self, event, args):
        if not self._active or event not in self._AUDITED:
            return
        with self._lock:
            caller = sys._getframe(1)
            # CodeType equality alone does not establish the source locator.
            # Require both the executing code and its module to name this file.
            locators = (caller.f_code.co_filename, caller.f_globals.get("__file__"))
            same_source = all(type(p) is str and Path(p).is_absolute()
                              and Path(p) == self._source_path
                              and Path(p).resolve() == self._source_path for p in locators)
            allowed = (event == "socket.bind" and self._allowed == 0 and self._dropped == 0
                       and type(args) is tuple and len(args) == 2
                       and isinstance(args[0], socket.socket) and args[0].family == socket.AF_INET6
                       and args[0].type == socket.SOCK_STREAM
                       and type(args[1]) is tuple and len(args[1]) == 2
                       and type(args[1][0]) is str and args[1][0] == "::1"
                       and type(args[1][1]) is int and args[1][1] == 0
                       and same_source and caller.f_code == self._code)
            if allowed:
                try:
                    _read(self._record_proof, 8 * 1024**2)
                    _read(self._source_proof, 2 * 1024**2)
                except (ValueError, OSError):
                    allowed = False
            if allowed:
                self._event(event, "allowed_local_capability_probe")
                return
        self._refuse(event)

    def install(self):
        """Install once; wrappers cover CPython methods lacking audit events."""
        if self._installed or not self._active:
            raise ValueError("Guard cannot be installed twice or after closing")
        self._installed = True
        sys.addaudithook(self)
        for name in self._METHODS:
            if not hasattr(socket.socket, name): continue
            original = getattr(socket.socket, name)
            def blocked(instance, *args, _name=name, **kwargs):
                return self._refuse("socket." + _name)
            self._wrappers[name] = (original, blocked)
            setattr(socket.socket, name, blocked)
        return self

    def close(self):
        for name, (original, wrapper) in self._wrappers.items():
            if getattr(socket.socket, name) is wrapper:
                setattr(socket.socket, name, original)
        self._active = False

    def snapshot(self):
        with self._lock:
            return {"scope": "trusted_python_offline_guard_v1",
                    "allowed_local_capability_probes": self._allowed,
                    "denied_network_attempts": self._denied,
                    "dropped_event_records": self._dropped,
                    "events": [dict(e) for e in self._events],
                    "record": dict(self._record_proof), "connection": dict(self._source_proof),
                    "installed": self._installed, "active": self._active}

    def __enter__(self): return self.install()
    def __exit__(self, *unused): self.close()
