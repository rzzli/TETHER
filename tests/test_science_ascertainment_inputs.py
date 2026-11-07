from pathlib import Path
import os
import stat
import tempfile
import unittest
import zipfile

from tether_engine.journal import read_chain
from tether_engine.serde import ContractError, read_json, sha256_file
from tools.science.ascertainment_inputs import DEFAULT_LIMITS, actual_date, qualify, safe_members


class AscertainmentInputTests(unittest.TestCase):
    def fixture(self, directory):
        root = Path(directory); archive = root / "supplied.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as z:
            z.writestr("postgres.dmp", b"fictional fixture dump")
            z.writestr("schema.png", b"")
        executable = root / "pg_restore.fixture"; executable.write_bytes(b"fixture executable")
        return root, archive, executable

    def runner(self, executable, dump, timeout, maximum):
        self.assertEqual(dump.name, "postgres.dmp")
        return {"returncode": 0, "output": b"; Archive created at 2026-04-01 04:46:38\n; TOC Entries: 0\n"}

    def test_qualification_retains_hashes_code_and_chained_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            root, archive, executable = self.fixture(directory); before = sha256_file(archive)
            result = qualify(archive, root / "out", executable, runner=self.runner,
                expected_archive_bytes=archive.stat().st_size, expected_archive_sha256=before)
            self.assertEqual(result["status"], "archive_qualification_passed")
            self.assertEqual(result["actual_dump_date"], "2026-04-01")
            self.assertEqual(result["archive_identity_before"], result["archive_identity_after"])
            self.assertEqual(before, sha256_file(archive))
            self.assertIsNone(result["dump_creation_timezone"])
            self.assertIsNone(result["exact_first_public_availability"])
            self.assertFalse(result["database_restored"]); self.assertEqual(result["clinical_rows_queried"], 0)
            for proof in result["members"] + [result["toc"], result["executed_code"], result["pg_restore"]]:
                self.assertEqual(sha256_file(Path(proof["path"])), proof["sha256"])
            self.assertEqual(read_chain(root / "out/journal.jsonl")[-1]["event"], "build_completed")

    def test_existing_output_is_never_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            root, archive, executable = self.fixture(directory); (root / "out").mkdir()
            with self.assertRaises(FileExistsError):
                qualify(archive, root / "out", executable, runner=lambda *a: self.fail("unexpected dispatch"))

    def test_wrong_date_fails_with_preserved_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root, archive, executable = self.fixture(directory)
            with self.assertRaises(ContractError):
                qualify(archive, root / "out", executable,
                    runner=lambda *a: {"returncode": 0, "output": b"; Archive created at 2026-04-02 00:00:00\n"})
            self.assertEqual(read_json(root / "out/failure.json")["stage"], "dump_toc")
            self.assertTrue((root / "out/extracted/postgres.dmp").exists())
            self.assertFalse((root / "out/qualification.json").exists())

    def test_date_requires_exact_single_valid_creation_record(self):
        for toc in ("", "; Archive created at 2026-04-02 00:00:00\n",
                    "; Archive created at 2026-04-01 00:00:00\n; Archive created at 2026-04-01 00:00:00\n"):
            with self.assertRaises(ContractError): actual_date(toc, "2026-04-01")

    def test_zip_paths_collisions_links_and_missing_dump_rejected(self):
        dump = zipfile.ZipInfo("postgres.dmp")
        link = zipfile.ZipInfo("link"); link.external_attr = (stat.S_IFLNK | 0o777) << 16
        for entries in ([dump, zipfile.ZipInfo("../escape")], [dump, zipfile.ZipInfo("C:escape")],
                        [dump, zipfile.ZipInfo("sub/file")], [dump, zipfile.ZipInfo("POSTGRES.DMP")],
                        [dump, link], [zipfile.ZipInfo("other")]):
            with self.assertRaises(ContractError): safe_members(entries, DEFAULT_LIMITS)

    def test_encryption_compression_and_expansion_limits_rejected(self):
        for kind in ("encryption", "compression", "ratio", "member", "total", "count"):
            with self.subTest(kind=kind):
                info = zipfile.ZipInfo("postgres.dmp"); limits = dict(DEFAULT_LIMITS)
                if kind == "encryption": info.flag_bits = 1
                if kind == "compression": info.compress_type = zipfile.ZIP_BZIP2
                if kind == "ratio": info.file_size = 201
                if kind == "member": info.file_size = limits["member_bytes"] + 1
                if kind == "total": info.file_size = 10; info.compress_size = 10; limits["expanded_bytes"] = 9
                entries = [info] if kind != "count" else [info] * (limits["members"] + 1)
                with self.assertRaises(ContractError): safe_members(entries, limits)

    def test_crc_failure_never_dispatches_toc(self):
        with tempfile.TemporaryDirectory() as directory:
            root, archive, executable = self.fixture(directory)
            raw = archive.read_bytes(); raw = raw.replace(b"fictional fixture dump", b"corrupted fixture dump")
            archive.write_bytes(raw)
            with self.assertRaises(zipfile.BadZipFile):
                qualify(archive, root / "out", executable, runner=lambda *a: self.fail("unexpected dispatch"))
            self.assertTrue((root / "out/failure.json").exists())

    def test_archive_mutation_even_with_preserved_size_mtime_fails_final_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            root, archive, executable = self.fixture(directory)
            def mutate(*args):
                initial = archive.stat(); content = bytearray(archive.read_bytes()); content[-1] ^= 1
                archive.write_bytes(content); os.utime(archive, ns=(initial.st_atime_ns, initial.st_mtime_ns))
                return self.runner(*args)
            with self.assertRaisesRegex(ContractError, "Archive changed"):
                qualify(archive, root / "out", executable, runner=mutate)

    def test_extracted_member_mutation_during_toc_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root, archive, executable = self.fixture(directory)
            def mutate(*args):
                args[1].write_bytes(b"tampered original dump")
                return self.runner(*args)
            with self.assertRaisesRegex(ContractError, "ancestor changed"):
                qualify(archive, root / "out", executable, runner=mutate)

    def test_oversize_archive_or_toc_and_failed_toc_retained(self):
        for kind in ("archive", "toc", "returncode", "hash"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root, archive, executable = self.fixture(directory)
                limits = {"archive_bytes": 1} if kind == "archive" else {"toc_bytes": 1} if kind == "toc" else None
                runner = (lambda *a: {"returncode": 1, "output": b"failed"}) if kind == "returncode" else self.runner
                with self.assertRaises(ContractError):
                    qualify(archive, root / "out", executable, runner=runner, limits=limits,
                            expected_archive_sha256="0" * 64 if kind == "hash" else None)
                self.assertTrue((root / "out/failure.json").exists())
                self.assertFalse((root / "out/qualification.json").exists())


if __name__ == "__main__":
    unittest.main()
