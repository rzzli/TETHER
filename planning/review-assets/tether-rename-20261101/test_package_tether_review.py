"""Invented packet/wheel controls; no actual paper/result/provider payload reads."""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.presentation import package_tether_review as packet


PROJECT_TOML = '''[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
[project]
name = "tether-target-agents"
version = "0.4.0"
description = "TETHER: auditable evidence-agent execution with a frozen compatibility engine"
requires-python = ">=3.11"
dependencies = ["asof-target-agents==0.3.11"]
license = {file = "LICENSE"}
[project.optional-dependencies]
ingest = ["pyarrow==21.0.0"]
[project.scripts]
tether = "tether._cli:main"
[tool.setuptools.packages.find]
where = ["src"]
include = ["tether", "tether.*"]
[tool.uv.sources]
asof-target-agents = {path = "../.."}
'''


def wheel_bytes(sources, license_bytes, *, extra=None, metadata_change=None, record_bad=False):
    info = "tether_target_agents-0.4.0.dist-info/"
    files = {"tether/" + name: raw for name, raw in sources.items()}
    fields = ["Metadata-Version: 2.4", "Name: tether-target-agents", "Version: 0.4.0",
              "Summary: TETHER: auditable evidence-agent execution with a frozen compatibility engine",
              "License: " + license_bytes.decode().strip(), "Requires-Python: >=3.11", "License-File: LICENSE", "Dynamic: license-file",
              "Requires-Dist: asof-target-agents==0.3.11", 'Requires-Dist: pyarrow==21.0.0; extra == "ingest"', "Provides-Extra: ingest"]
    metadata = ("\n".join(fields) + "\n\n").encode()
    if metadata_change:
        metadata = metadata_change(metadata)
    files.update({info + "METADATA": metadata,
                  info + "WHEEL": b"Wheel-Version: 1.0\nGenerator: setuptools (84.0.0)\nRoot-Is-Purelib: true\nTag: py3-none-any\n\n",
                  info + "entry_points.txt": b"[console_scripts]\ntether = tether._cli:main\n",
                  info + "top_level.txt": b"tether\n", info + "licenses/LICENSE": license_bytes})
    files.update(extra or {})
    record = io.StringIO(newline="")
    writer = csv.writer(record, lineterminator="\n")
    for name, raw in sorted(files.items()):
        hashed = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode()
        writer.writerow([name, "sha256=bad" if record_bad else hashed, str(len(raw))])
    writer.writerow([info + "RECORD", "", ""])
    files[info + "RECORD"] = record.getvalue().encode()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, raw in sorted(files.items()):
            archive.writestr(name, raw)
    return stream.getvalue()


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tether-packet-invented-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for n in ["data/cache", "data/derived", "paper/release/tether", "packages/tether/src/tether/study"]:
            (self.root / n).mkdir(parents=True, exist_ok=True)
        self.results = self.root / "data/cache/results"
        self.results.mkdir()
        self.license = b"Invented test license\n"
        (self.root / "LICENSE").write_bytes(self.license)
        self.write("paper/release/tether/README.md", b"# Invented TETHER packet\n[Paper](paper/manuscript.md)\n[PDF](paper/tether-source-reporting-preprint.pdf)\n[Qualification](TETHER-QUALIFICATION.json)\n")
        for n in packet.PAPER_FILES:
            raw = b"{}\n" if n.endswith(".json") else b"Invented working-draft text; owner facts deferred.\n"
            self.write("paper/" + n, raw)
        self.write(packet.PDF_NAME, b"Invented PDF-shaped test bytes; not a rendered result.\n")
        outputs, comparisons = {}, []
        names = [f"tables/invented-{i:02d}.csv" for i in range(34)] + [f"figures/figure{i}.pdf" for i in range(1, 4)]
        for name in names + ["README.md"]:
            raw = b"Invented aggregate only.\n"
            p = self.results / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(raw)
            outputs[name] = dict(path=name, sha256=packet.safe.sha(raw), bytes=len(raw))
            if name != "README.md":
                comparisons.append(dict(outputs[name], matches_historical=True))
        result_manifest = packet.safe._wire(dict(status="PASS_PORTABLE_HISTORICAL_PAYLOAD_REPRODUCTION",
            manifest_self_excluded=True, tables_and_outputs=outputs, historical_payload_comparisons=comparisons))
        (self.results / "ARTIFACTS.json").write_bytes(result_manifest)
        legacy = {}
        for name, (relative, _, role) in packet.LEGACY_FILES.items():
            raw = b"{}\n" if name.endswith(".json") else b"Invented compatibility instructions.\n"
            self.write(relative, raw)
            legacy[name] = (relative, packet.safe.sha(raw), role)
        self.legacy_zip = self.root / "data/derived/legacy/asof-research-artifact-0.1.0.zip"
        self.legacy_zip.parent.mkdir()
        self.legacy_zip.write_bytes(b"Invented opaque legacy container; never parsed.\n")
        self.write("packages/tether/pyproject.toml", PROJECT_TOML.encode())
        self.write("packages/tether/uv.lock", b"version = 1\n")
        self.write("packages/tether/README.md", b"# Invented source guide\n")
        self.write("packages/tether/LICENSE", self.license)
        self.sources = {name: b"VALUE = 'invented'\n" for name in
                        ["__init__.py", "__main__.py", "_cli.py", "_presentation.py", "study/__init__.py", "study/__main__.py"]}
        for name, raw in self.sources.items():
            self.write("packages/tether/src/tether/" + name, raw)
        self.wheel = self.root / ("data/cache/wheels/" + packet.WHEEL_NAME)
        self.wheel.parent.mkdir()
        self.wheel.write_bytes(wheel_bytes(self.sources, self.license))
        for patcher in [patch.object(packet, "RESULTS_MANIFEST_SHA256", packet.safe.sha(result_manifest)),
                        patch.object(packet, "P09_ARCHIVE_SHA256", packet.safe.sha(self.legacy_zip.read_bytes())),
                        patch.object(packet, "LEGACY_FILES", legacy)]:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.qualification = self.root / "paper/release/tether/qualification.json"
        self.output = self.root / "data/derived/review.zip"
        self.refresh()

    def write(self, relative, raw):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def refresh(self, change=None):
        inventory = packet.source_inventory(self.root, self.results, self.wheel, self.legacy_zip)
        self.qualified = {**packet.QUALIFICATION, "qualified_at_utc": "2026-11-02T01:02:03.123456+00:00",
                          "scope_notes": ["Invented helper fixture, no actual qualification."],
                          "payloads": {n: dict(sha256=packet.safe.sha(p.read_bytes()), bytes=p.stat().st_size, role=role)
                                       for n, (p, role) in inventory.items()}}
        if change:
            change(self.qualified)
        self.qualification.write_bytes(packet.safe._wire(self.qualified))
        self.qualification_sha = packet.safe.sha(self.qualification.read_bytes())

    def build(self, output=None):
        return packet.package(self.root, self.results, self.wheel, self.legacy_zip,
                              self.qualification, self.qualification_sha, output or self.output)

    def test_exact_closure_repeat_source_layout_and_no_actual_values(self):
        first = self.build()
        second = self.build(self.output.with_name("repeat.zip"))
        self.assertEqual(first["archive_sha256"], second["archive_sha256"])
        self.assertEqual(first["members"], 58 + len(self.sources))
        with zipfile.ZipFile(self.output) as archive:
            names = archive.namelist()
            self.assertEqual(set(names), set(self.qualified["payloads"]) | {packet.QUAL_NAME, packet.MANIFEST_NAME})
            self.assertIn(packet.SOURCE_PREFIX + "src/tether/study/__main__.py", names)
            self.assertNotIn("paper/asof-source-reporting-preprint-v2.pdf", names)
            self.assertEqual(archive.read("reproduction/asof-research-artifact-0.1.0.zip"), self.legacy_zip.read_bytes())
            self.assertEqual({m.date_time for m in archive.infolist()}, {(2026, 11, 2, 1, 2, 2)})
            manifest = json.loads(archive.read(packet.MANIFEST_NAME))
            self.assertFalse(manifest["publication_authorized"])
            self.assertFalse(manifest["agent_visible"])
            self.assertNotIn(packet.MANIFEST_NAME, manifest["files"])

    def test_existing_output_and_partial_are_never_replaced(self):
        self.output.write_bytes(b"prior owner")
        with self.assertRaises(FileExistsError): self.build()
        self.assertEqual(self.output.read_bytes(), b"prior owner")
        self.output.unlink()
        partial = self.output.with_name(self.output.name + ".partial")
        partial.write_bytes(b"failed prior attempt")
        with self.assertRaises(FileExistsError): self.build()
        self.assertEqual(partial.read_bytes(), b"failed prior attempt")

    def test_tampered_qualification_source_size_and_role_reject(self):
        original = self.qualification_sha
        self.qualification.write_bytes(self.qualification.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "Pinned input"): self.build()
        self.qualification_sha = original
        self.refresh(lambda q: q["payloads"]["paper/manuscript.md"].update(bytes=True))
        with self.assertRaises(ValueError): self.build()
        self.refresh(lambda q: q["payloads"]["paper/manuscript.md"].update(role="agent_evidence"))
        with self.assertRaisesRegex(ValueError, "role"): self.build()
        self.refresh()
        self.write("paper/manuscript.md", b"changed source")
        with self.assertRaisesRegex(ValueError, "Pinned input"): self.build()
        self.assertFalse(self.output.exists())

    def test_unsafe_aliased_unlisted_and_missing_payload_names_reject(self):
        cases = [lambda q: q["payloads"].update({"../outside": dict(sha256="a" * 64, bytes=0, role="x")}),
                 lambda q: q["payloads"].update({"README.MD": q["payloads"]["README.md"]}),
                 lambda q: q["payloads"].update({"extra.txt": dict(sha256="a" * 64, bytes=0, role="x")}),
                 lambda q: q["payloads"].pop("README.md")]
        for change in cases:
            with self.subTest(change=change):
                self.refresh(change)
                with self.assertRaises(ValueError): self.build()

    def test_science_publication_owner_and_boolean_status_guards(self):
        for key, value in [("schema_version", True), ("agent_visible", True), ("publication_authorized", True),
                           ("owner_declarations", "confirmed"), ("scientific_validation", "established"),
                           ("author_acceptance", "accepted"), ("submission_ready", True)]:
            with self.subTest(key=key):
                self.refresh(lambda q: q.update({key: value}))
                with self.assertRaisesRegex(ValueError, "qualification contract"): self.build()

    def test_public_metadata_and_guide_private_paths_credentials_and_answers_reject(self):
        for value in ["D:/private/machine", "api_key=fictional-secret-value"]:
            self.refresh(lambda q: q.update(scope_notes=[value]))
            with self.assertRaises(ValueError): self.build()
        self.refresh(lambda q: q.update(checks={"reference_facts": ["invented"]}))
        with self.assertRaises(ValueError): self.build()
        self.write("paper/release/tether/README.md", b"A private path D:/invented/private.\n")
        self.refresh()
        with self.assertRaises(ValueError): self.build()

    def test_source_code_is_not_subject_to_generic_privacy_regex_and_cache_is_excluded(self):
        self.sources["_cli.py"] = b"api_key = 'invented explanatory test literal'\n"
        self.write("packages/tether/src/tether/_cli.py", self.sources["_cli.py"])
        self.write("packages/tether/src/tether/__pycache__/ignored.py", b"must not ship")
        self.write("packages/tether/tests/private_fixture.py", b"must not ship")
        self.wheel.write_bytes(wheel_bytes(self.sources, self.license))
        self.refresh()
        self.build()
        with zipfile.ZipFile(self.output) as archive:
            self.assertFalse(any("__pycache__" in n or "/tests/" in n for n in archive.namelist()))

    def test_whole_wheel_rejects_asof_pth_metadata_record_and_padding(self):
        bad = [wheel_bytes(self.sources, self.license, extra={"asof/__init__.py": b"injected"}),
               wheel_bytes(self.sources, self.license, extra={"injected.pth": b"injected"}),
               wheel_bytes(self.sources, self.license, metadata_change=lambda raw: raw.replace(b"asof-target-agents==0.3.11", b"asof-target-agents>=0.3")),
               wheel_bytes(self.sources, self.license, record_bad=True),
               wheel_bytes(self.sources, self.license) + b"unlisted trailer"]
        for raw in bad:
            with self.subTest(case=packet.safe.sha(raw)), self.assertRaises(ValueError):
                packet.verify_tether_wheel(raw, self.sources, self.license)

    def test_wheel_and_source_substitution_reject_even_with_new_qualification(self):
        altered = dict(self.sources, _cli=b"changed")
        altered["_cli.py"] = b"different implementation\n"
        self.wheel.write_bytes(wheel_bytes(altered, self.license))
        self.refresh()
        with self.assertRaises(ValueError): self.build()
        self.wheel.write_bytes(wheel_bytes(self.sources, self.license))
        path = self.root / "packages/tether/pyproject.toml"
        path.write_text(PROJECT_TOML.replace('path = "../.."', 'path = "elsewhere"'))
        self.refresh()
        with self.assertRaisesRegex(ValueError, "layout"): self.build()

    def test_immutable_legacy_and_result_bytes_cannot_be_requalified(self):
        self.legacy_zip.write_bytes(b"changed legacy")
        self.refresh()
        with self.assertRaisesRegex(ValueError, "legacy P09 archive"): self.build()
        self.legacy_zip.write_bytes(b"Invented opaque legacy container; never parsed.\n")
        path = self.results / "tables/invented-00.csv"
        path.write_bytes(b"changed historical numbers")
        self.refresh()
        with self.assertRaisesRegex(ValueError, "result bytes"): self.build()

    def test_missing_relative_link_and_protected_output_tree_reject(self):
        self.write("paper/release/tether/README.md", b"[Missing](not-in-packet.md)\n")
        self.refresh()
        with self.assertRaisesRegex(ValueError, "link is missing"): self.build()
        self.write("paper/release/tether/README.md", b"Invented guide\n")
        self.refresh()
        with self.assertRaisesRegex(ValueError, "immutable input tree"):
            self.build(self.results / "bad.zip")

    def test_readback_failure_and_publication_race_keep_partial_and_no_false_success(self):
        with patch.object(packet.safe, "_verify_zip", side_effect=ValueError("invented readback failure")), self.assertRaises(ValueError):
            self.build()
        partial = self.output.with_name(self.output.name + ".partial")
        self.assertTrue(zipfile.is_zipfile(partial))
        self.assertFalse(self.output.exists())
        partial.unlink()
        original = packet.safe._verify_zip
        def race(path, entries, timestamp):
            raw = original(path, entries, timestamp)
            self.output.write_bytes(b"concurrent owner")
            return raw
        with patch.object(packet.safe, "_verify_zip", side_effect=race), self.assertRaises(FileExistsError): self.build()
        self.assertEqual(self.output.read_bytes(), b"concurrent owner")
        self.assertTrue(partial.exists())


if __name__ == "__main__":
    unittest.main()
