"""Public checkout gates must not depend on private project working records."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError
from tools import validate


class PublicTreeValidationTests(unittest.TestCase):
    def test_internal_records_fail_before_catalog_or_file_reads(self):
        for name in (
            "memory/MEMORY.md", "Memory/user-profile.md", "planning/run-registry.json",
            "reports/review.md", "paper/manuscript.md", "research_notes/session.md",
            "tmp/probe.py", "TODO.md", "docs/TETHER-NAMESPACE-VALIDATION.json",
            "packages/tether/MIGRATION-VALIDATION.json", "data/DATA_PLAN.md",
        ):
            with self.subTest(path=name), \
                    patch.object(validate.subprocess, "check_output", return_value=name.encode() + b"\0"), \
                    patch.object(validate, "read_json", side_effect=AssertionError("Read before scope rejection")):
                with self.assertRaises(ContractError):
                    validate.structural_checks()

    def test_code_configuration_protocols_and_fixtures_remain_public(self):
        for name in (
            "src/tether_engine/serde.py", "packages/tether/src/tether/_cli.py",
            "tests/fixtures/metadata.json", "experiments/scifact/PROTOCOL.md",
            "data/catalog/sources.json", "data/catalog/policy-v2.json",
            "docs/FRAMEWORK.md", ".github/workflows/validate.yml",
        ):
            with self.subTest(path=name):
                validate.validate_public_path(name)

    def test_bulk_private_and_runtime_outputs_stay_excluded(self):
        for name in (
            "data/raw/sample.parquet", "data/cache/run.json", "data/derived/snapshot.json",
            "runs/receipt.json", "packages/tether/runs/receipt.json", ".venv/metadata.json",
            "data/manifests/private/receipt.json", "data/raw/.gitkeep",
            "data/catalog/history/old-policy.json", "data/manifests/README.md",
        ):
            with self.subTest(path=name), self.assertRaises(ContractError):
                validate.validate_public_path(name)

    def test_nested_generated_output_directories_are_not_public(self):
        for name in (
            "results/RESULTS.json", "experiments/litqa_analysis/cache/RECEIPT.json",
            "experiments/example/results/summary.json", "tools/tmp/session.json",
            "tests/temp/session.log", "packages/tether/logs/worker.txt",
            "experiments/example/scratch/notes.md",
            "experiments/example/private/session.json",
        ):
            with self.subTest(path=name), self.assertRaises(ContractError):
                validate.validate_public_path(name)

    def test_nested_working_records_are_not_public(self):
        for name in (
            "experiments/memory/session.md", "packages/tether/planning/notes.md",
            "experiments/example/reports/run.json", "experiments/paper/results.json",
            "packages/research_notes/session.md", "experiments/TODO.md",
            "packages/tether/memory.md", "experiments/MEMORY.md",
        ):
            with self.subTest(path=name), \
                    patch.object(validate.subprocess, "check_output", return_value=name.encode()+b"\0"), \
                    patch.object(Path, "read_bytes", side_effect=AssertionError("Working record opened")):
                with self.assertRaises(ContractError):
                    validate.structural_checks()

    def test_force_added_docs_data_and_credentials_fail_before_content_reads(self):
        for name in (
            "docs/session-notes.md", "docs/review/notes.md",
            "data/catalog/acquisition-report.json", "data/collection-state.json",
            "data/STORAGE_AND_DOWNLOAD_REPORT.md", "src/.env", "config/.env.local",
            "config/cloud-credentials.json", "config/SECRETS.yaml", "tools/signed_urls.txt",
        ):
            with self.subTest(path=name), \
                    patch.object(validate.subprocess, "check_output", return_value=name.encode()+b"\0"), \
                    patch.object(Path, "read_bytes", side_effect=AssertionError("Payload opened before boundary rejection")):
                with self.assertRaises(ContractError):
                    validate.structural_checks()

    def test_public_examples_source_and_exact_documentation_allowlists(self):
        for name in (
            ".env.example", "examples/.env.example", "tests/test_credentials.py",
            "tests/fixtures/metadata.json", "src/tether_engine/study/process.py",
            "docs/ARCHIVE.md", "docs/FRAMEWORK.md", "docs/MAINTENANCE.md",
            "docs/TETHER-CATALOG-POLICY.md", "docs/TETHER-VERIFICATION-SCOPE.md",
            "data/.gitignore", "data/README.md", "data/catalog/README.md",
            "data/catalog/sources.json", "data/catalog/policy-v2.json",
        ):
            with self.subTest(path=name):
                validate.validate_public_path(name)

    def test_former_project_identity_is_rejected_in_paths_and_all_content(self):
        token = bytes((97, 115, 111, 102))
        for variant in (token, token.upper(), token.title()):
            name = "src/"+variant.decode()+"/module.py"
            with self.subTest(path=name), self.assertRaises(ContractError):
                validate.validate_public_path(name)
            for name in ("README.md", "tests/fixtures/names.bin", "src/example.py"):
                with self.subTest(path=name, variant=variant), \
                        patch.object(validate.subprocess, "check_output", return_value=name.encode()+b"\0"), \
                        patch.object(Path, "read_bytes", return_value=b"prefix "+variant+b" suffix"), \
                        patch.object(validate, "read_json", side_effect=AssertionError("Catalog checked before branding")):
                    with self.assertRaisesRegex(ContractError, "Legacy project identifier"):
                        validate.structural_checks()

    def catalog_checkout(self, folder):
        root = Path(folder)
        catalog = root / "data/catalog"
        catalog.mkdir(parents=True)
        for name in ("sources.json", "policy-v2.json"):
            (catalog / name).write_bytes((validate.ROOT / "data/catalog" / name).read_bytes())
        return root

    def test_catalog_only_checkout_needs_no_planning_or_working_index(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.catalog_checkout(folder)
            names = b"data/catalog/sources.json\0data/catalog/policy-v2.json\0"
            with patch.object(validate, "ROOT", root), \
                    patch.object(validate.subprocess, "check_output", return_value=names), \
                    patch.object(validate.subprocess, "run", return_value=SimpleNamespace(returncode=0)):
                result = validate.structural_checks()
            catalog = json.loads((root / "data/catalog/sources.json").read_bytes())
            self.assertEqual(result["providers"], len(catalog["providers"]))
            self.assertEqual(result["datasets"], len(catalog["datasets"]))
            self.assertEqual(result["tracked_scope_files"], 2)
            self.assertFalse((root / "planning").exists())
            self.assertFalse((root / "data/DATA_PLAN.md").exists())

    def test_catalog_policy_source_binding_is_still_required(self):
        with tempfile.TemporaryDirectory() as folder:
            root = self.catalog_checkout(folder)
            path = root / "data/catalog/policy-v2.json"
            policy = json.loads(path.read_bytes())
            policy["source_catalog"]["sha256"] = "0" * 64
            path.write_text(json.dumps(policy), encoding="utf-8")
            names = b"data/catalog/sources.json\0data/catalog/policy-v2.json\0"
            with patch.object(validate, "ROOT", root), \
                    patch.object(validate.subprocess, "check_output", return_value=names), \
                    patch.object(validate.subprocess, "run", return_value=SimpleNamespace(returncode=0)):
                with self.assertRaises(ContractError):
                    validate.structural_checks()

    def test_template_refuses_local_collection_and_verification_claims(self):
        original = json.loads((validate.ROOT / "data/catalog/sources.json").read_bytes())
        for changes in (
            {"collection_status": "collected"}, {"parse_status": "parsed"},
            {"validation_status": "validated"},
            {"verification": {"level": "not_checked", "checked_at": "2026-11-07", "evidence": []}},
        ):
            catalog = copy.deepcopy(original)
            catalog["datasets"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                validate.validate_public_catalog_template(catalog)

    def test_template_refuses_nested_machine_state_and_absolute_paths(self):
        original = json.loads((validate.ROOT / "data/catalog/sources.json").read_bytes())
        for private in (
            {"workspace_path": "machine-specific"}, {"state_path": "machine-specific"},
            {"metadata_artifact_path": "machine-specific"},
            {"acquisition_snapshot": {}}, {"last_maintenance_update": "local run"},
            {"note": "Original at E:/private/run.json"}, {"note": "D:\\private\\run.json"},
            {"note": "\\\\workstation\\private\\run.json"},
            {"note": "/home/user/run.json"}, {"note": "Local state at /tmp/cache/run.json"},
        ):
            catalog = copy.deepcopy(original)
            catalog["datasets"][0]["invented_metadata"] = {"nested": private}
            with self.subTest(private=private), self.assertRaises(ContractError):
                validate.validate_public_catalog_template(catalog)

    def test_template_keeps_public_urls_and_requires_its_scope(self):
        catalog = json.loads((validate.ROOT / "data/catalog/sources.json").read_bytes())
        catalog["invented_public_source"] = "https://example.org/source"
        validate.validate_public_catalog_template(catalog)
        for field, value in (("catalog_mode", "local_workspace"), ("status_scope", "")):
            changed = copy.deepcopy(catalog)
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate.validate_public_catalog_template(changed)

    def test_shipped_policy_cannot_authorize_a_local_deployment(self):
        validate.validate_public_policy_template({"artifacts": [], "uses": []})
        for field in ("artifacts", "uses"):
            policy = {"artifacts": [], "uses": []}
            policy[field] = [{"id": "invented-local-grant"}]
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate.validate_public_policy_template(policy)
