"""Publication/replay of four invented deterministic results, without dispatch."""

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, canonical
from tether_engine.study import baseline_smoke as smoke_module


class BaselineSmokeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "new"

    def reseal(self, filename, change):
        file = self.path / filename
        doc = json.loads(file.read_bytes())
        change(doc)
        file.write_bytes(canonical(doc))
        receipt = json.loads((self.path / "receipt.json").read_bytes())
        if filename in receipt["artifacts"]:
            receipt["artifacts"][filename]["sha256"] = hashlib.sha256(
                file.read_bytes()
            ).hexdigest()
            receipt["artifacts"][filename]["bytes"] = file.stat().st_size
        (self.path / "receipt.json").write_bytes(canonical(receipt))
        return hashlib.sha256((self.path / "receipt.json").read_bytes()).hexdigest()

    def test_smoke_and_external_anchor_verify(self):
        result = smoke_module.smoke(self.path)
        verified = smoke_module.verify(self.path, result["receipt_sha256"])
        self.assertEqual(verified["synthetic_cells"], 4)
        self.assertEqual(verified["model_calls"], 0)
        self.assertEqual(verified["scientific_validation"], "not_attempted")
        with self.assertRaises(ContractError):
            smoke_module.verify(self.path, "0" * 64)
        with self.assertRaises(FileExistsError):
            smoke_module.smoke(self.path)

    def test_resealed_semantic_tampering(self):
        cases = [
            ("cell-01-result.json", lambda d: d.update(model_calls=1)),
            ("cell-01-result.json", lambda d: d["excerpts"][0].update(text="changed")),
            ("cell-01-reviewer.json", lambda d: d.update(label="Candidate Z")),
            ("assignment.json", lambda d: d["cells"][0].update(method="lexical")),
            ("accounting.json", lambda d: d.update(model_calls=1)),
            ("package-proof.json", lambda d: d["resources"].clear()),
        ]
        for index, (filename, change) in enumerate(cases):
            with self.subTest(filename=filename, index=index):
                self.path = Path(self.tmp.name) / str(index)
                smoke_module.smoke(self.path)
                anchor = self.reseal(filename, change)
                with self.assertRaises(ContractError):
                    smoke_module.verify(self.path, anchor)

    def test_extra_and_missing_members(self):
        result = smoke_module.smoke(self.path)
        anchor = result["receipt_sha256"]
        extra = self.path / "extra.json"
        extra.write_text("{}")
        with self.assertRaises(ContractError):
            smoke_module.verify(self.path, anchor)
        extra.unlink()
        (self.path / "cell-02-policy.json").unlink()
        with self.assertRaises(ContractError):
            smoke_module.verify(self.path, anchor)

    def test_one_concurrent_winner(self):
        def attempt():
            try:
                return smoke_module.smoke(self.path)
            except FileExistsError:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: attempt(), range(2)))
        winners = [r for r in results if r is not None]
        self.assertEqual(len(winners), 1)
        smoke_module.verify(self.path, winners[0]["receipt_sha256"])

    def test_publish_failure_retains_primary_and_marker(self):
        real = smoke_module.publish_bytes
        calls = []

        def injected(path, payload):
            calls.append(path.name)
            if len(calls) == 3:
                raise OSError("injected publication")
            return real(path, payload)

        with patch.object(smoke_module, "publish_bytes", side_effect=injected):
            with self.assertRaisesRegex(OSError, "injected publication"):
                smoke_module.smoke(self.path)
        self.assertTrue((self.path / "failure.json").exists())
        self.assertFalse((self.path / "receipt.json").exists())

    def test_interruption_preserved_even_if_failure_write_fails(self):
        real = smoke_module.publish_bytes

        def injected(path, payload):
            if path.name == "failure.json":
                raise OSError("marker unavailable")
            return real(path, payload)

        with (
            patch.object(
                smoke_module, "run_baseline", side_effect=KeyboardInterrupt("stop")
            ),
            patch.object(smoke_module, "publish_bytes", side_effect=injected),
        ):
            with self.assertRaisesRegex(KeyboardInterrupt, "stop"):
                smoke_module.smoke(self.path)
        self.assertTrue(self.path.exists())
        self.assertFalse((self.path / "receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
