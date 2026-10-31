"""Focused metadata assertions only; never import/run an acceptance main."""

import ast
import copy
from email.parser import Parser
import hashlib
import json
from pathlib import Path
import re
import tomllib
import unittest
import zipfile


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HELPER = HERE / "accept_generation_v3.py"
tree = ast.parse(HELPER.read_text(encoding="utf-8"))
selected = [node for node in tree.body if isinstance(node, ast.FunctionDef)
            and node.name in ("require", "check_dependency_metadata")]
assert len(selected) == 2
namespace = {"re": re}
# Compile just the two pure assertion definitions; no top-level code, imports,
# artifact aggregation, protected hashing or acceptance publication is executed.
exec(compile(ast.Module(body=selected, type_ignores=[]),
             str(HELPER) + "::metadata_assertions_only", "exec"), namespace)
check = namespace["check_dependency_metadata"]


class AcceptanceMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        package = json.loads((HERE / "WHEEL-ENVIRONMENTS.json").read_text(encoding="utf-8"))
        cls.wheel = Path(package["wheel"])
        assert hashlib.sha256(cls.wheel.read_bytes()).hexdigest() == (
            "b0d7573be994e3f44e3d942a1944cddb2e43e1306a64cfd6480dd05e3415a276"
        )
        with zipfile.ZipFile(cls.wheel) as archive:
            name = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
            cls.metadata = Parser().parsestr(archive.read(name).decode("utf-8"))
        cls.project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    def test_actual_exact_ingest_name_and_pinned_version_pass(self):
        self.assertEqual(self.metadata.get_all("Provides-Extra"), ["ingest"])
        self.assertEqual(self.project["project"]["optional-dependencies"],
                         {"ingest": ["pyarrow==21.0.0"]})
        check(self.metadata, self.project)

    def test_unconditional_default_dependency_is_rejected(self):
        for dependency in ("pyarrow==21.0.0", "numpy>=1"):
            metadata = copy.deepcopy(self.metadata)
            metadata.replace_header("Requires-Dist", dependency)
            with self.subTest(dependency=dependency), self.assertRaises(RuntimeError):
                check(metadata, self.project)

    def test_wrong_or_unpinned_optional_version_is_rejected(self):
        for dependency in ('pyarrow==20.0.0; extra == "ingest"',
                           'pyarrow>=21.0.0; extra == "ingest"'):
            metadata = copy.deepcopy(self.metadata)
            metadata.replace_header("Requires-Dist", dependency)
            with self.subTest(dependency=dependency), self.assertRaises(RuntimeError):
                check(metadata, self.project)

    def test_provides_extra_and_project_must_agree_on_ingest(self):
        for extra in (None, "ingestion"):
            metadata = copy.deepcopy(self.metadata)
            del metadata["Provides-Extra"]
            if extra is not None:
                metadata["Provides-Extra"] = extra
            with self.subTest(extra=extra), self.assertRaises(RuntimeError):
                check(metadata, self.project)
        for update in (
            {"dependencies": ["jsonschema"]},
            {"optional-dependencies": {"ingestion": ["pyarrow==21.0.0"]}},
        ):
            project = copy.deepcopy(self.project)
            project["project"].update(update)
            with self.subTest(update=update), self.assertRaises(RuntimeError):
                check(self.metadata, project)

    def test_original_observed_failure_and_v2_bytes_remain_preserved(self):
        observed = json.loads((HERE / "ROOT-ACCEPTANCE-ATTEMPT-v2.json").read_text(encoding="utf-8"))
        self.assertEqual(observed["status"], "failed_acceptance_helper_no_acceptance_published")
        self.assertEqual(observed["error"], "Default dependency-free metadata differs")
        self.assertFalse(observed["acceptance_published"])
        self.assertEqual(
            hashlib.sha256((HERE / "accept_generation_v2.py").read_bytes()).hexdigest(),
            observed["helper_sha256"],
        )
        self.assertFalse((HERE / "acceptance.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
