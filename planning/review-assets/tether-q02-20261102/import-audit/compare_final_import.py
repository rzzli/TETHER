"""Bounded delta from the independently audited import; no provider reads."""
import collections
import copy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
OLD = ROOT / "data/derived/catalog-policy-v2-20261102T084315Z"
NEW = ROOT / "data/derived/catalog-policy-v2-20261102T084949Z"
OLD_SHA = "8e6709135e25924f576e33315ff2f36f1cc9745892c5018bbc9a0b382a79ed94"
NEW_SHA = "80a8bf5b61b28298081ec16ae1758a4944f0d45ac0e4ea1181e8eb6faa71cd78"
OUT = Path(__file__).parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    path = Path(path)
    assert path.suffix == ".json" and path.stat().st_size <= 16 * 1024 * 1024
    raw = path.read_bytes()
    return json.loads(raw.decode("utf-8-sig")), raw


def main():
    old, old_bytes = read(OLD / "policy.json")
    new, new_bytes = read(NEW / "policy.json")
    assert sha(old_bytes) == OLD_SHA and sha(new_bytes) == NEW_SHA
    before, _ = read(OLD / "report.json")
    after, after_bytes = read(NEW / "report.json")
    roots, roots_bytes = read(NEW / "roots.json")
    old_roots, _ = read(OLD / "roots.json")
    assert roots == old_roots
    expected = copy.deepcopy(old)
    expected["created_at_utc"] = new["created_at_utc"]
    replacements = 0
    old_prefix = OLD.relative_to(ROOT).as_posix() + "/metadata/"
    new_prefix = NEW.relative_to(ROOT).as_posix() + "/metadata/"
    for artifact in expected["artifacts"]:
        for proof in artifact["provenance"]["evidence"]:
            assert proof["path"].startswith(old_prefix)
            proof["path"] = new_prefix + proof["path"][len(old_prefix):]
            replacements += 1
    assert expected == new, "Policy delta exceeds creation time and metadata-copy prefix"
    assert after["policy_sha256"] == NEW_SHA
    for key in ("products", "artifacts", "raw_lineage_artifacts", "source_node_occurrences", "packets",
                "aact_archives", "allowed_uses", "blocked_uses", "pure_policy_selections",
                "source_payload_hashes", "normalized_packet_hashes", "scientific_validation",
                "collection_status_promotions", "provider_spend_usd"):
        assert before[key] == after[key], key
    previous = {(r["root_alias"], r["relative_path"]):r for r in before["metadata"]}
    current = {(r["root_alias"], r["relative_path"]):r for r in after["metadata"]}
    assert len(previous) == len(before["metadata"]) == len(current) == len(after["metadata"]) == 280
    assert set(previous) == set(current)
    original_roots = {"project":ROOT, "external_data":Path(roots["roots"]["external_data"])}
    verified_bytes = 0
    for key, item in current.items():
        prior = previous[key]
        assert item["sha256"] == prior["sha256"] and item["bytes"] == prior["bytes"]
        assert prior["archived_copy"].startswith(old_prefix)
        assert item["archived_copy"] == new_prefix + prior["archived_copy"][len(old_prefix):]
        # The approved source set is exactly the 280 neutral metadata files
        # previously audited, not newly discovered files or source payloads.
        _, original = read(original_roots[key[0]] / key[1])
        _, archived = read(ROOT / item["archived_copy"])
        assert original == archived and len(archived) == item["bytes"] and sha(archived) == item["sha256"]
        verified_bytes += len(archived)
    cache = ROOT / "data/cache/q02-importer-audit-temp"
    cache.mkdir(exist_ok=True, parents=True)
    tempfile.tempdir = str(cache)
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.defaultTestLoader.loadTestsFromName("tests.test_tether_policy_import"))
    assert result.wasSuccessful() and result.testsRun == 7
    log = OUT / "IMPORTER-TESTS-FINAL.txt"
    with log.open("x", encoding="utf-8") as handle:
        handle.write(stream.getvalue())
    preflight, preflight_bytes = read(ROOT / "planning/review-assets/tether-q02-20261102/REAL-SOURCE-PREFLIGHT.json")
    assert preflight["policy_sha256"] == NEW_SHA and preflight["engine_dispatches"] == 0
    assert preflight["raw_source_files_checked"] == 18 and preflight["selected_raw_bytes"] == 442815104
    assert preflight["normalized_files_copied"] == 1 and 248 - preflight["raw_source_files_checked"] == 230
    report = dict(schema_version=1, status="PASS_FINAL_METADATA_DELTA", created_at_utc=datetime.now(timezone.utc).isoformat(),
        prior_independent_audit="planning/review-assets/tether-q02-20261102/import-audit/ACTUAL-IMPORT-AUDIT-v3.json",
        prior_policy_sha256=OLD_SHA, final_policy_sha256=NEW_SHA, final_import=NEW.relative_to(ROOT).as_posix(),
        allowed_policy_deltas=["top-level created_at_utc", "artifact provenance metadata-copy directory prefix"],
        metadata_copy_path_replacements=replacements, roots_unchanged=True,
        all_other_policy_values_equal=True, metadata_originals_and_copies_checked=280,
        metadata_bytes_checked_per_copy_set=verified_bytes, full_frame_audit_repeated=False,
        final_report_sha256=sha(after_bytes), final_roots_sha256=sha(roots_bytes),
        importer=dict(path="tools/data/build_tether_policy.py", sha256=sha((ROOT / "tools/data/build_tether_policy.py").read_bytes())),
        importer_tests=dict(tests_run=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                            log=log.relative_to(ROOT).as_posix(), sha256=sha(log.read_bytes()),
                            test_code_sha256=sha((ROOT / "tests/test_tether_policy_import.py").read_bytes())),
        checker_initial_attempt="Standalone checker lacked the project import path for targeted test discovery. Reproduced import failure retained in DELTA-HARNESS-IMPORT-FAILURE.txt; corrected before this passing run.",
        code_review_delta="Exact receipt_archive_path guard precedes receipt loading; normalized packets pass checked_path and strict relative_path before read_file. No provider-source read added.",
        retained_real_preflight=dict(report_sha256=sha(preflight_bytes), scope="Root's retained preparation report checked; not reexecuted by this audit", raw_files=18,
                                    raw_bytes=442815104, normalized_packets=1, engine_dispatches=0, remaining_raw_not_freshly_hashed=230,
                                    scientific_validation="not_established"),
        source_payload_reads_or_hashes_by_this_audit=0, protected_outcome_or_expert_reads=0,
        checker_sha256=sha(Path(__file__).read_bytes()))
    with (OUT / "FINAL-IMPORT-DELTA.json").open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2); handle.write("\n")
    print(json.dumps({k:report[k] for k in ("status","metadata_originals_and_copies_checked","metadata_copy_path_replacements","final_policy_sha256")}))


if __name__ == "__main__":
    main()
