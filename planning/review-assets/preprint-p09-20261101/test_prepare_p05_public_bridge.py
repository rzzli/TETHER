"""The public bridge must remove only the declared identity and no source fact."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("p09_bridge_exporter", ROOT / "tools/science/prepare_p05_public_bridge.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class BridgeBoundaryTests(unittest.TestCase):
    def test_compiled_disposition_is_a_bound_record_not_a_status_string(self):
        reference = dict(method=dict(catalog_sha256="a" * 64), facts=[])
        case = dict(reference=reference, disposition=dict(status="compiled", case_id="p05-01",
            blocked_reason=None, role="evaluation_only", agent_visible=False, adjudicated_gold=False,
            reference_sha256=m.fingerprint(reference)))
        self.assertEqual(m.historical_reference(case, "p05-01"), reference)
        for replacement in ("compiled", dict(case["disposition"], status="blocked"),
                            dict(case["disposition"], reference_sha256="f" * 64)):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                m.historical_reference(dict(case, disposition=replacement), "p05-01")

    def test_catalog_projection_is_exact_and_nonmutating(self):
        original = dict(method=dict(catalog_sha256="a" * 64, source_snapshot_sha256="b" * 64),
                        facts=[dict(value=1.25, unknown_reason=None, source=dict(field="beta"))])
        before = deepcopy(original)
        projected = m.projection(original)
        self.assertEqual(original, before)
        self.assertEqual(projected, dict(method=dict(source_snapshot_sha256="b" * 64), facts=before["facts"]))
        changed = deepcopy(original)
        changed["facts"][0]["value"] = -1.25
        self.assertNotEqual(m.fingerprint(projected), m.fingerprint(m.projection(changed)))
        changed = deepcopy(original)
        changed["method"]["source_snapshot_sha256"] = "c" * 64
        self.assertNotEqual(m.fingerprint(projected), m.fingerprint(m.projection(changed)))

    def test_missing_catalog_is_not_silently_projected(self):
        with self.assertRaises(ValueError):
            m.projection(dict(method={}, facts=[]))

    def test_machine_paths_and_credentials_are_rejected(self):
        for value in ("C:\\Users\\someone\\private", "E:/raw/source", "/home/user/raw", "/Users/name/raw",
                      "https://example.org/a?token=secret", "Bearer abcDEF123"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.safe_public(dict(nested=[dict(value=value)]))
        with self.assertRaises(ValueError):
            m.safe_public(dict(access_token="anything"))

    def test_neutral_queries_and_provider_urls_are_allowed(self):
        m.safe_public(dict(targetId="ENSG_FAKE", diseaseId="EFO_FAKE", studyLocusId="locus:fictional",
                           source_url="https://example.org/25.09/part.parquet", relative_path="raw/a.parquet"))

    def test_export_pins_are_full_independent_byte_hashes(self):
        for name, (_, digest) in m.PINS.items():
            with self.subTest(name=name):
                self.assertRegex(digest, r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
