"""Invented offline-guard controls; no DNS or outbound request is dispatched."""
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from experiments.alce.offline import OfflineNetworkGuard, OfflineViolation


SOURCE = '''import socket
def _has_ipv6(host):
    sock=socket.socket(socket.AF_INET6)
    try:
        sock.bind((host, 0))
        return True
    finally:
        sock.close()
'''


def proof(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.source = self.root / "urllib3/util/connection.py"
        self.source.parent.mkdir(parents=True)
        self.source.write_text(SOURCE, encoding="utf-8")
        self.record = self.root / "urllib3-9.9.9.dist-info/RECORD"
        self.record.parent.mkdir()
        encoded = base64.urlsafe_b64encode(hashlib.sha256(self.source.read_bytes()).digest()).rstrip(b"=").decode()
        self.record.write_text(f"urllib3/util/connection.py,sha256={encoded},{self.source.stat().st_size}\n", encoding="utf-8")
        self.rp, self.sp = proof(self.record), proof(self.source)

    def guard(self, **kwargs):
        value = OfflineNetworkGuard(self.rp, self.sp, **kwargs)
        self.addCleanup(value.close)
        return value

    def function(self, raw=None, filename=None):
        values = {"__file__": filename or str(self.source)}
        exec(compile(raw or self.source.read_bytes(), filename or str(self.source), "exec", dont_inherit=True), values)
        return values["_has_ipv6"]

    @unittest.skipUnless(socket.has_ipv6, "Python has no IPv6 socket capability")
    def test_exact_pinned_function_can_probe_only_once(self):
        f = self.function(); guard = self.guard().install()
        try: f("::1")
        except OSError as error:
            if isinstance(error, OfflineViolation): raise
            # The policy admits an OS capability test, not a promise IPv6 exists.
        self.assertEqual(guard.snapshot()["allowed_local_capability_probes"], 1)
        with self.assertRaises(OfflineViolation): f("::1")
        self.assertEqual(guard.snapshot()["denied_network_attempts"], 1)

    def test_same_function_name_and_filename_do_not_authorize_altered_code(self):
        f = self.function(SOURCE.replace("return True", "return False"))
        guard = self.guard().install()
        with self.assertRaises(OfflineViolation): f("::1")
        self.assertEqual(guard.snapshot()["allowed_local_capability_probes"], 0)

    def test_identical_copied_function_or_changed_module_locator_is_denied(self):
        copied = self.root / "copied.py"
        copied.write_bytes(self.source.read_bytes())
        for changed_global in (False, True):
            f = self.function(filename=str(copied) if not changed_global else None)
            if changed_global: f.__globals__["__file__"] = str(copied)
            guard = self.guard().install()
            try:
                with self.subTest(changed_global=changed_global), self.assertRaises(OfflineViolation): f("::1")
                self.assertEqual(guard.snapshot()["allowed_local_capability_probes"], 0)
            finally: guard.close()

    def test_arbitrary_local_remote_and_wildcard_binds_are_denied(self):
        guard = self.guard().install()
        for family, address in ((socket.AF_INET, ("127.0.0.1", 0)),
                                (socket.AF_INET, ("0.0.0.0", 0)),
                                (socket.AF_INET6, ("::1", 0)),
                                (socket.AF_INET6, ("::", 0))):
            with self.subTest(address=address), socket.socket(family) as sock:
                with self.assertRaises(OfflineViolation): sock.bind(address)
        self.assertEqual(guard.snapshot()["denied_network_attempts"], 4)

    def test_pinned_function_wrong_address_still_denied(self):
        f = self.function(); self.guard().install()
        with self.assertRaises(OfflineViolation): f("::")

    def test_dns_connect_and_connect_ex_are_denied_before_dispatch(self):
        guard = self.guard().install()
        for action in (lambda: socket.getaddrinfo("invented.invalid", 443),
                       lambda: socket.gethostbyname("invented.invalid"),
                       lambda: socket.gethostbyaddr("192.0.2.1"),
                       lambda: socket.getnameinfo(("192.0.2.1", 0), 0)):
            with self.assertRaises(OfflineViolation): action()
        for name in ("connect", "connect_ex"):
            with socket.socket() as sock, self.assertRaises(OfflineViolation):
                getattr(sock, name)(("192.0.2.1", 443))
        self.assertEqual(guard.snapshot()["denied_network_attempts"], 6)

    def test_unaudited_listen_accept_and_sends_are_wrapped(self):
        guard = self.guard().install()
        with socket.socket() as sock:
            for name, args in (("listen", (1,)), ("accept", ()), ("send", (b"secret",)),
                               ("sendall", (b"secret",)), ("sendto", (b"secret", ("192.0.2.1", 1)))):
                with self.subTest(name=name), self.assertRaises(OfflineViolation): getattr(sock, name)(*args)
        serialized = json.dumps(guard.snapshot())
        self.assertNotIn("secret", serialized); self.assertNotIn("192.0.2.1", serialized)
        self.assertEqual(guard.snapshot()["denied_network_attempts"], 5)

    def test_direct_invalid_bind_shapes_are_denied(self):
        guard = self.guard()
        with socket.socket(socket.AF_INET6) as sock:
            for address in (("::1", False), ["::1", 0], ("::1", 0, 0, 0), ("::1", 1)):
                with self.subTest(address=address), self.assertRaises(OfflineViolation):
                    guard("socket.bind", (sock, address))

    def test_record_hash_size_membership_and_duplicate_rows_reject(self):
        original = self.record.read_text()
        for changed in (original + original, original.replace("sha256=", "sha1="),
                        original.replace("connection.py", "unrelated.py")):
            self.record.write_text(changed)
            with self.assertRaises(ValueError): OfflineNetworkGuard(proof(self.record), self.sp)
        self.record.write_text(original)
        with self.assertRaises(ValueError): OfflineNetworkGuard(dict(self.rp, sha256="0"*64), self.sp)
        with self.assertRaises(ValueError): OfflineNetworkGuard(self.rp, dict(self.sp, bytes=self.sp["bytes"]+1))

    def test_changed_source_after_constructor_rejects_probe(self):
        f = self.function(); guard = self.guard().install()
        self.source.write_bytes(self.source.read_bytes().replace(b"True", b"None"))
        with self.assertRaises(OfflineViolation): f("::1")
        self.assertEqual(guard.snapshot()["allowed_local_capability_probes"], 0)

    def test_event_storage_is_bounded_without_losing_denial_counts(self):
        guard = self.guard(max_events=2)
        for _ in range(5):
            with self.assertRaises(OfflineViolation): guard("socket.connect", ("credentials",))
        value = guard.snapshot()
        self.assertEqual(value["denied_network_attempts"], 5)
        self.assertEqual(len(value["events"]), 2); self.assertEqual(value["dropped_event_records"], 3)
        self.assertNotIn("credentials", json.dumps(value))

    def test_snapshot_is_copy_and_close_restores_methods(self):
        before = socket.socket.listen
        guard = self.guard().install(); guard.close()
        self.assertIs(socket.socket.listen, before)
        view = guard.snapshot(); view["record"]["sha256"] = "wrong"
        self.assertEqual(guard.snapshot()["record"], self.rp)
        with self.assertRaises(ValueError): guard.install()

    def test_constructor_and_module_import_install_nothing(self):
        with mock.patch.object(sys, "addaudithook") as hook:
            guard = self.guard()
        hook.assert_not_called(); self.assertFalse(guard.snapshot()["installed"])

    def test_cpython_listen_lacks_audit_event_in_isolated_child(self):
        script = """import json,sys,socket
events=[]
sys.addaudithook(lambda event,args: events.append(event) if event.startswith('socket.') else None)
with socket.socket() as s:
    try:s.listen(-999999999999999999999999999999)
    except (OSError,OverflowError):pass
print(json.dumps(events))
"""
        # Invalid C argument prevents an actual listening socket even without a guard.
        child = subprocess.run([sys.executable, "-I", "-B", "-c", script], capture_output=True, timeout=10, check=True)
        self.assertNotIn("socket.listen", json.loads(child.stdout))


if __name__ == "__main__": unittest.main()
