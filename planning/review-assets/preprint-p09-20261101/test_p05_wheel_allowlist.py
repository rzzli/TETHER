"""Invented wheel fixtures; no provider data, installs or network access."""
from __future__ import annotations

import base64
import csv
import hashlib
import io
from pathlib import Path
import stat
import sys
import tempfile
import unittest
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/science"))
from p05_wheel_allowlist import SPECS, verify_wheel

LICENSE = b"Invented license for fictional package fixtures.\n"


def record(members, record_name):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    for name, raw in members.items():
        if name != record_name:
            digest = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode()
            writer.writerow((name, "sha256=" + digest, str(len(raw))))
    writer.writerow((record_name, "", ""))
    return stream.getvalue().encode()


def fixture(prefix):
    spec = SPECS[prefix]
    dist = spec["distribution"].replace("-", "_") + "-" + spec["version"]
    info = dist + ".dist-info/"
    package = {"__init__.py": b"# invented package\n", "cli.py": b"def main(): pass\n"}
    headers = [("Metadata-Version", "2.4"), ("Name", spec["distribution"]), ("Version", spec["version"]),
        ("Summary", spec["summary"]), ("License", LICENSE.decode().strip()), ("Requires-Python", spec["python"]),
        ("License-File", "LICENSE")]
    headers += [("Provides-Extra", value) for value in spec["extras"]]
    headers += [("Requires-Dist", value) for value in spec["dependencies"]]
    headers += [("Dynamic", "license-file")]
    members = {prefix + "/" + name: raw for name, raw in package.items()}
    members.update({
        info + "licenses/LICENSE": LICENSE,
        info + "METADATA": ("\n".join(key + ": " + value for key, value in headers) + "\n\n").encode(),
        info + "WHEEL": b"Wheel-Version: 1.0\nGenerator: setuptools (84.0.0)\nRoot-Is-Purelib: true\nTag: py3-none-any\n\n",
        info + "entry_points.txt": ("[console_scripts]\n" + spec["entrypoint"] + "\n").encode(),
        info + "top_level.txt": (prefix + "\n").encode(),
    })
    members[info + "RECORD"] = record(members, info + "RECORD")
    return dist + "-py3-none-any.whl", info, members, {name: hashlib.sha256(raw).hexdigest() for name, raw in package.items()}


class WheelAllowlistTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def write(self, name, members, *, duplicate=None, special=None, comment=b""):
        path = self.root / name
        with warnings.catch_warnings(), zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            warnings.simplefilter("ignore", UserWarning)
            archive.comment = comment
            for key, raw in members.items():
                if special and key == special[0]:
                    info = zipfile.ZipInfo(key); info.external_attr = special[1] << 16
                    archive.writestr(info, raw)
                else:
                    archive.writestr(key, raw)
            if duplicate:
                archive.writestr(duplicate, members[duplicate])
        return path

    def check(self, name, members, expected, **options):
        return verify_wheel(self.write(name, members, **options), "asof_p05_replay", expected, LICENSE)

    def test_both_exact_known_distributions_pass(self):
        for prefix in SPECS:
            name, _, members, expected = fixture(prefix)
            self.assertEqual(verify_wheel(self.write(name, members), prefix, expected, LICENSE), expected)

    def test_legacy_subset_proof_accepts_extra_payload_but_new_verifier_rejects(self):
        name, info, members, expected = fixture("asof_p05_replay")
        for extra in ("unapproved.pth", "unapproved/data.parquet", "asof_p05_replay/font.ttf", "other_package/__init__.py"):
            with self.subTest(extra=extra):
                changed = dict(members, **{extra: b"Invented excluded bytes only"})
                changed[info + "RECORD"] = record(changed, info + "RECORD")
                path = self.write(name, changed)
                # Exact behavior of the former subset-only wheel_payloads helper.
                with zipfile.ZipFile(path) as archive:
                    before = {key[len("asof_p05_replay/"):]: hashlib.sha256(archive.read(key)).hexdigest()
                        for key in archive.namelist() if key.startswith("asof_p05_replay/") and key.endswith((".py", ".json"))}
                self.assertEqual(before, expected)
                with self.assertRaises(ValueError): verify_wheel(path, "asof_p05_replay", expected, LICENSE)

    def test_missing_or_changed_package_bytes_fail(self):
        name, info, members, expected = fixture("asof_p05_replay")
        for missing in (True, False):
            changed = dict(members)
            if missing: del changed["asof_p05_replay/cli.py"]
            else: changed["asof_p05_replay/cli.py"] += b"# changed\n"
            changed[info + "RECORD"] = record(changed, info + "RECORD")
            with self.assertRaises(ValueError): self.check(name, changed, expected)

    def test_wrong_distribution_version_python_dependencies_and_metadata_fail(self):
        name, info, members, expected = fixture("asof_p05_replay")
        for old, new in ((b"Name: asof-p05-replay", b"Name: other"), (b"Version: 0.1.0", b"Version: 9.9"),
                (b"Requires-Python: <3.12,>=3.11", b"Requires-Python: >=3.10"), (b"pyarrow==21.0.0", b"pyarrow==22.0.0"),
                (b"Metadata-Version: 2.4", b"Metadata-Version: 2.3"), (b"\n\n", b"\nAuthor: unreviewed metadata\n\n")):
            with self.subTest(new=new):
                changed = dict(members); changed[info + "METADATA"] = changed[info + "METADATA"].replace(old, new)
                changed[info + "RECORD"] = record(changed, info + "RECORD")
                with self.assertRaises(ValueError): self.check(name, changed, expected)

    def test_missing_extra_or_wrong_entrypoint_fails_even_with_valid_record(self):
        name, info, members, expected = fixture("asof_p05_replay")
        for payload in (None, b"[console_scripts]\nother = other:main\n", members[info + "entry_points.txt"] + b"extra = other:main\n"):
            changed = dict(members)
            if payload is None: del changed[info + "entry_points.txt"]
            else: changed[info + "entry_points.txt"] = payload
            changed[info + "RECORD"] = record(changed, info + "RECORD")
            with self.assertRaises(ValueError): self.check(name, changed, expected)

    def test_wheel_backend_tag_purelib_license_and_toplevel_fail(self):
        name, info, members, expected = fixture("asof_p05_replay")
        mutations = [("WHEEL", b"84.0.0", b"85.0.0"), ("WHEEL", b"py3-none-any", b"cp311-win_amd64"),
            ("WHEEL", b"true", b"false"), ("licenses/LICENSE", LICENSE, b"Other license"),
            ("top_level.txt", b"asof_p05_replay", b"other"), ("METADATA", b"License: Invented", b"License: Other")]
        for leaf, old, new in mutations:
            changed = dict(members); changed[info + leaf] = changed[info + leaf].replace(old, new)
            changed[info + "RECORD"] = record(changed, info + "RECORD")
            with self.assertRaises(ValueError): self.check(name, changed, expected)

    def test_record_requires_every_unique_member_correct_hash_size_and_empty_self(self):
        name, info, members, expected = fixture("asof_p05_replay")
        rows = list(csv.reader(io.StringIO(members[info + "RECORD"].decode())))
        variants = [rows[1:], rows + [rows[0]], [rows[0][:1] + ["sha256=wrong", rows[0][2]]] + rows[1:],
            [rows[0][:2] + ["0"]] + rows[1:], rows[:-1] + [[info + "RECORD", "sha256=wrong", "0"]]]
        for changed_rows in variants:
            stream = io.StringIO(newline=""); csv.writer(stream, lineterminator="\n").writerows(changed_rows)
            changed = dict(members); changed[info + "RECORD"] = stream.getvalue().encode()
            with self.assertRaises(ValueError): self.check(name, changed, expected)

    def test_duplicates_unsafe_names_symlink_and_comments_fail(self):
        name, info, members, expected = fixture("asof_p05_replay")
        with self.assertRaises(ValueError): self.check(name, members, expected, duplicate="asof_p05_replay/cli.py")
        for extra in ("../outside", "C:/outside", "asof_p05_replay\\outside.py", "/absolute", "asof_p05_replay/../outside"):
            changed = dict(members, **{extra: b"Invented only"})
            with self.assertRaises(ValueError): self.check(name, changed, expected)
        with self.assertRaises(ValueError): self.check(name, members, expected, special=("asof_p05_replay/cli.py", stat.S_IFLNK | 0o777))
        with self.assertRaises(ValueError): self.check(name, members, expected, comment=b"Unreviewed bytes")

    def test_filename_unknown_prefix_and_expected_inventory_are_strict(self):
        name, _, members, expected = fixture("asof_p05_replay")
        with self.assertRaises(ValueError): self.check("other.whl", members, expected)
        with self.assertRaises(ValueError): verify_wheel(self.write(name, members), "unknown", expected, LICENSE)
        with self.assertRaises(ValueError): verify_wheel(self.write(name, members), "asof_p05_replay", {"../unsafe.py": "a" * 64}, LICENSE)


if __name__ == "__main__":
    unittest.main()
