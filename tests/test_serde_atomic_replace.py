"""Bounded Windows replacement resilience; only private fictional files."""
import ctypes
from ctypes import wintypes
import errno
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine import serde
from tether_engine.maintenance import write_new_json


def native_error(code, source="fictional-stage", destination="fictional-destination"):
    error = PermissionError(errno.EACCES, "injected native denial", str(source))
    error.winerror = code
    error.filename2 = str(destination)
    return error


class AtomicReplaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "mutable.json"
        self.before = b'{"before":true}\n'
        self.path.write_bytes(self.before)

    def test_success_needs_one_replace_and_no_backoff(self):
        # This is the no-error control-flow case. Actual Windows replacement
        # can transiently fail even without a deliberately held test handle.
        staged = self.root / 'invented-staged.json'
        with patch.object(serde.os, "replace", return_value=None) as replace, patch("time.sleep") as sleep:
            serde._replace_staged(staged, self.path)
        replace.assert_called_once_with(staged, self.path)
        sleep.assert_not_called()

    def test_actual_write_publishes_complete_content_and_cleans_staging(self):
        serde.write_json(self.path, {"after": True})
        self.assertEqual(json.loads(self.path.read_bytes()), {"after": True})
        self.assertEqual(list(self.root.glob('.writing-*')), [])

    def test_native_retry_reuses_exact_staged_bytes_and_preserves_old_until_success(self):
        real_replace = os.replace
        for code in (5, 32, 33):
            self.path.write_bytes(self.before)
            attempts = []
            def fail_twice(source, destination):
                attempts.append((str(source), str(destination), hashlib.sha256(Path(source).read_bytes()).hexdigest()))
                self.assertEqual(self.path.read_bytes(), self.before)
                if len(attempts) < 3:
                    raise native_error(code, source, destination)
                real_replace(source, destination)
            with self.subTest(code=code), patch.object(serde, "_WINDOWS_REPLACE_RETRY", True, create=True), \
                    patch.object(serde.os, "replace", side_effect=fail_twice) as replace, patch("time.sleep") as sleep, \
                    patch.object(serde.os, "fsync", wraps=os.fsync) as fsync:
                serde.write_json(self.path, {"after": code})
                self.assertEqual(replace.call_count, 3)
                self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.05, 0.1])
                self.assertEqual(fsync.call_count, 1)
                self.assertEqual(len(set(attempts)), 1)
                self.assertEqual(json.loads(self.path.read_bytes()), {"after": code})
                self.assertEqual(list(self.root.glob(".writing-*")), [])

    def test_persistent_native_denial_is_bounded_and_preserves_final_exception(self):
        for code in (5, 32, 33):
            errors = []
            def denied(source, destination):
                error = native_error(code, source, destination)
                errors.append(error)
                raise error
            with self.subTest(code=code), patch.object(serde, "_WINDOWS_REPLACE_RETRY", True, create=True), \
                    patch.object(serde.os, "replace", side_effect=denied) as replace, patch("time.sleep") as sleep:
                with self.assertRaises(PermissionError) as caught:
                    serde.write_json(self.path, {"after": True})
                self.assertIs(caught.exception, errors[-1])
                self.assertEqual(caught.exception.winerror, code)
                self.assertEqual(caught.exception.filename2, str(self.path))
                self.assertEqual(replace.call_count, 3)
                self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.05, 0.1])
                self.assertEqual(self.path.read_bytes(), self.before)
                self.assertEqual(list(self.root.glob(".writing-*")), [])

    def test_noneligible_errors_and_nonwindows_fail_without_retry(self):
        cases = [(True, PermissionError("no native code")), (True, OSError("disk failure")),
                 *((True, native_error(code)) for code in (2, 3, 19, 80, 112)), (False, native_error(5))]
        for windows, error in cases:
            with self.subTest(windows=windows, error=str(error)), \
                    patch.object(serde, "_WINDOWS_REPLACE_RETRY", windows, create=True), \
                    patch.object(serde.os, "replace", side_effect=error) as replace, patch("time.sleep") as sleep:
                with self.assertRaises(OSError) as caught:
                    serde.write_json(self.path, {"after": True})
                self.assertIs(caught.exception, error)
                self.assertEqual(replace.call_count, 1)
                sleep.assert_not_called()
                self.assertEqual(self.path.read_bytes(), self.before)

    def test_fsync_failure_is_not_retried(self):
        error = native_error(5)
        with patch.object(serde.os, "fsync", side_effect=error), patch.object(serde.os, "replace") as replace, \
                patch("time.sleep") as sleep:
            with self.assertRaises(PermissionError) as caught:
                serde.write_json(self.path, {"after": True})
            self.assertIs(caught.exception, error)
            replace.assert_not_called()
            sleep.assert_not_called()
            self.assertEqual(self.path.read_bytes(), self.before)

    def test_replace_and_cleanup_failures_preserve_the_primary(self):
        for primary in (OSError("primary replacement failure"), KeyboardInterrupt("primary interrupt")):
            staged = []
            def cleanup(path, *args, **kwargs):
                staged.append(path)
                raise PermissionError("secondary staged cleanup failure")
            with self.subTest(primary=type(primary).__name__), patch.object(serde.os, "replace", side_effect=primary), \
                    patch.object(Path, "unlink", side_effect=cleanup, autospec=True):
                with self.assertRaises(type(primary)) as caught:
                    serde.write_json(self.path, {"after": True})
                self.assertIs(caught.exception, primary)
                self.assertTrue(any("cleanup" in note.lower() for note in getattr(primary, "__notes__", ())))
            for path in staged:
                path.unlink(missing_ok=True)
            self.assertEqual(self.path.read_bytes(), self.before)

    def test_interruption_during_backoff_is_not_swallowed_or_retried(self):
        interruption = KeyboardInterrupt("stop during bounded backoff")
        with patch.object(serde, "_WINDOWS_REPLACE_RETRY", True, create=True), \
                patch.object(serde.os, "replace", side_effect=native_error(5)) as replace, \
                patch("time.sleep", side_effect=interruption) as sleep:
            with self.assertRaises(KeyboardInterrupt) as caught:
                serde.write_json(self.path, {"after": True})
            self.assertIs(caught.exception, interruption)
            self.assertEqual(replace.call_count, 1)
            self.assertEqual(sleep.call_count, 1)
            self.assertEqual(self.path.read_bytes(), self.before)

    def test_no_clobber_publication_does_not_use_replacement(self):
        with patch.object(serde.os, "replace", side_effect=AssertionError("no-clobber must not replace")):
            with self.assertRaises(FileExistsError):
                write_new_json(self.path, {"after": True})
            fresh = self.root / "new.json"
            write_new_json(fresh, {"new": True})
            self.assertEqual(json.loads(fresh.read_bytes()), {"new": True})
        self.assertEqual(self.path.read_bytes(), self.before)

    @unittest.skipUnless(os.name == "nt", "native held-handle test requires Windows")
    def test_real_windows_held_handle_can_release_before_retry(self):
        self._held_handle(release=True)

    @unittest.skipUnless(os.name == "nt", "native held-handle test requires Windows")
    def test_real_windows_persistent_held_handle_fails_bounded(self):
        self._held_handle(release=False)

    def _held_handle(self, release):
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                                      wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        handle = kernel.CreateFileW(str(self.path), 0x80000000, 0x00000003, None, 3, 0x80, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        errors = []
        real_replace = os.replace
        def attempt(source, destination):
            try:
                return real_replace(source, destination)
            except OSError as error:
                errors.append(error.winerror)
                raise
        def sleep(_delay):
            nonlocal handle
            if release and handle is not None:
                self.assertTrue(kernel.CloseHandle(handle))
                handle = None
        try:
            with patch.object(serde.os, "replace", side_effect=attempt) as replace, patch("time.sleep", side_effect=sleep) as backoff:
                if release:
                    serde.write_json(self.path, {"after": True})
                    self.assertEqual(replace.call_count, 2)
                    self.assertEqual(backoff.call_count, 1)
                    self.assertEqual(json.loads(self.path.read_bytes()), {"after": True})
                else:
                    with self.assertRaises(PermissionError):
                        serde.write_json(self.path, {"after": True})
                    self.assertEqual(replace.call_count, 3)
                    self.assertEqual(backoff.call_count, 2)
                    self.assertEqual(self.path.read_bytes(), self.before)
                self.assertTrue(errors and all(code in (5, 32, 33) for code in errors))
        finally:
            if handle is not None:
                kernel.CloseHandle(handle)


if __name__ == "__main__":
    unittest.main()
