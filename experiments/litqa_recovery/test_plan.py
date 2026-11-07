"""Fictional interruption and concurrency controls, with no network or models."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from experiments.litqa_recovery import plan as p
from experiments.litqa_analysis.test_collection import reseal
from experiments.litqa_supplied import resolver as producer


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(p.canonical(value))


def journal(path, pairs):
    path.parent.mkdir(parents=True, exist_ok=True)
    previous, lines = None, []
    for index, (kind, details) in enumerate(pairs):
        event = dict(sequence=index, previous_sha256=previous, event=kind, details=details)
        event["sha256"] = p.digest(p.canonical(event))
        previous = event["sha256"]
        lines.append(p.canonical(event))
    path.write_bytes(b"\n".join(lines) + b"\n")


def reserved():
    return ("build_reserved", dict(created_at_utc="2026-11-06T23:40:00+00:00", owner_pid=42,
                                   run_id="00000000-0000-0000-0000-000000000042"))


class RecoveryPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.top = Path(self.temp.name).resolve()
        self.root = self.top / "interrupted"
        self.root.mkdir()
        self.registry = self.top / "stable-authorities"
        self.registry.mkdir()
        self.audit_path = self.top / "AUDIT.json"
        self.frame_path = self.top / "frozen/FRAME.json"
        self.phase = self.root / p.PHASE
        self.dois = ["10.1234/one", "10.1234/two", "10.1234/three"]
        self.queries = [dict(id=f"00000000-0000-0000-0000-{i:012d}", question=f"Invented question {i}?",
                             choices=["(A) Yes", "(B) Insufficient information to answer the question"])
                        for i in range(1, 4)]
        self.hints = [dict(id=q["id"], question=q["question"], dois=[d]) for q, d in zip(self.queries, self.dois)]
        products = {}
        for name, value in (("doi_schedule", self.dois), ("answer_queries", self.queries), ("hints", self.hints)):
            path = self.top / "inputs" / (name + ".json")
            write(path, value)
            products[name] = p._proof(path)
        self.policy = json.loads(producer.canonical(producer.legacy.DEFAULT_POLICY))
        self.frame = dict(kind="sc04_supplied_execution_v1", purpose="fictional_qualification", automatic_retry=False,
                          ordinary_retrieval=False, provider_cost_usd=0, products=products, questions=3,
                          unique_dois=3, question_doi_pairs=3, policy=self.policy,
                          phase_seconds={"collect": 7200}, python=dict(path=sys.executable))
        write(self.frame_path, self.frame)
        self.frame_sha = p._proof(self.frame_path)["sha256"]
        write(self.root / "FRAME.json", self.frame)
        journal(self.root / "journal.jsonl", [reserved(), ("diagnostic_phase_started", {"phase": "collect"})])
        journal(self.root / "collect/journal.jsonl", [reserved(), ("diagnostic_worker_dispatch", {"phase": "collect"})])
        journal(self.root / "collect/worker/journal.jsonl", [reserved()])
        repo = self.top / "original-repository"
        cache = repo / "data/cache" / ("sc04-diagnostic-" + self.root.name + "-collect-imports")
        job = dict(phase="collect", frame_sha256=self.frame_sha, common_root=str(self.root),
                   collection=None, cutoff=None, import_cache=str(cache))
        job_path = self.root / "collect/JOB.json"
        write(job_path, job)
        command = [sys.executable, "-I", "-B", "-X", "pycache_prefix=" + str(cache),
                   str(repo / "experiments/litqa_supplied/run.py"), "worker", "--frame", str(self.frame_path),
                   "--frame-sha256", self.frame_sha, "--job", str(job_path), "--job-sha256", p._proof(job_path)["sha256"],
                   "--output", str(self.root / "collect/worker")]
        write(self.root / "collect/COMMAND.json", dict(command=command, limits=dict(max_output_bytes=4*1024**2, timeout_seconds=7200)))
        write(self.root / "collect/worker/CONFIG.json", dict(frame_sha256=self.frame_sha, job=job, purpose="fictional_qualification"))
        (self.root / "collect/worker/io-audit.jsonl").write_bytes(p.canonical(dict(fictional=True)) + b"\n")
        schedule = [dict(ordinal=i, id=d, branch="shared") for i, d in enumerate(self.dois)]
        config = dict(kind="sc04_stage_v1", stage="supplied", ids=self.dois, schedule=schedule, seconds=7100)
        write(self.phase / "CONFIG.json", config)
        complete_root = self.phase / "products/0000"
        doi_plan = json.loads(producer.canonical(producer.plan(self.dois[0], self.policy)))
        def response(url, **limits):
            return dict(body=b'{"hitCount":0,"resultList":{"result":[]}}', status=200,
                        final_url=url, headers={})
        with patch.object(producer.legacy, "fetch_http", side_effect=response):
            producer.acquire(doi_plan, complete_root, deadline=time.monotonic()+60)
        product = dict(root=str(complete_root), receipt=p._proof(complete_root / "RECEIPT.json"),
                       manifest=p._proof(complete_root / "MANIFEST.json"), plan=doi_plan)
        slot = dict(**schedule[0], status="completed", reason=None, product=product)
        slot_path = self.phase / "slots/0000.json"
        write(slot_path, slot)
        self.stage_pairs = [reserved(), ("stage_configured", dict(config_sha256=p._proof(self.phase / "CONFIG.json")["sha256"])),
                            ("slot_reserved", schedule[0]),
                            ("slot_terminal", dict(ordinal=0, slot_sha256=p._proof(slot_path)["sha256"], path="slots/0000.json", status="completed")),
                            ("slot_reserved", schedule[1])]
        journal(self.phase / "journal.jsonl", self.stage_pairs)
        uncertain = self.phase / "products/0001"
        uncertain_plan = p._doi_plan(self.dois[1], self.policy)
        write(uncertain / "PLAN.json", uncertain_plan)
        (uncertain / "responses").mkdir()
        self.uncertain_pairs = [reserved(), ("plan_bound", dict(plan_sha256=p._proof(uncertain / "PLAN.json")["sha256"])),
            ("http_attempt", dict(request_id="000", kind="metadata", url=uncertain_plan["metadata_url"],
                                  byte_reservation=self.policy["metadata_bytes"], transport_status="started"))]
        journal(uncertain / "journal.jsonl", self.uncertain_pairs)
        self.anchor()
        contract = self.top / "RECOVERY-CONTRACT.md"
        contract.write_bytes(b"Fictional prospective contract; no production dispatch.\n")
        self.registry_policy_path = self.top / "REGISTRY-POLICY.json"
        identity = p.digest(p.canonical(dict(original_frame_sha256=self.frame_sha,
                      original_root_reservation_sha256=p._journal(self.root / "journal.jsonl")[0]["sha256"])))
        write(self.registry_policy_path, dict(schema_version=1, kind="sc04_recovery_registry_binding_v1",
              parent_identity=identity, registry=str(self.registry), contract=p._proof(contract)))
        self.registry_policy_sha = p._proof(self.registry_policy_path)["sha256"]

    def anchor(self):
        self.audit = dict(schema_version=1, kind="sc04_read_only_interrupted_attempt_audit",
                          original_root=str(self.root), frame_proof=p._proof(self.frame_path),
                          externally_retained_anchors=dict(supplied_frame_sha256=self.frame_sha),
                          original_inventory=p._inventory(self.root)[0],
                          summary=dict(completed=999, uncertain=0, unexecuted=999))
        write(self.audit_path, self.audit)
        self.audit_sha = p._proof(self.audit_path)["sha256"]

    def inspect(self):
        return p.inspect_parent(self.audit_path, self.audit_sha, self.frame_path, self.frame_sha)

    def reserve(self, name="child"):
        return p.reserve_parent(self.audit_path, self.audit_sha, self.frame_path, self.frame_sha,
                                registry_policy_path=self.registry_policy_path, registry_policy_sha=self.registry_policy_sha,
                                registry=self.registry, output=self.top / name)

    def test_completed_reuse_uncertainty_and_untouched_dispatch_derive_from_bytes(self):
        before = p._inventory(self.root)
        result = self.inspect()
        self.assertEqual([s["disposition"] for s in result["slots"]],
                         ["adopt_completed", "inherited_uncertain_metadata", "untouched"])
        self.assertEqual(result["allowed_dispatch_ordinals"], [2])
        self.assertEqual(result["answer_queries"], self.queries)
        self.assertEqual(result["hints"], self.hints)
        self.assertEqual(result["prior_answers"], 0)
        self.assertIsNone(result["slots"][1]["response_proof"])
        self.assertIsNone(result["slots"][1]["accounting"]["measured_response_bytes"])
        self.assertFalse(result["slots"][0]["coverage"]["article_retained"])
        self.assertEqual(result["historical_accounting"]["http_attempts"], 2)
        self.assertEqual(result["historical_accounting"]["unknown_transfer_upper_bytes"], 1048576)
        self.assertEqual(before, p._inventory(self.root))

    def test_exclusive_authority_binds_plan_and_preserves_originals(self):
        before = p._inventory(self.root)
        result = self.reserve()
        frame = p._bound(result["frame"])
        authority = p._bound(result["authority"])
        self.assertEqual(authority["frame"], result["frame"])
        self.assertEqual(authority["allowed_dispatch_ordinals"], [2])
        self.assertFalse(frame["production_dispatch_qualified"])
        self.assertEqual(before, p._inventory(self.root))
        with self.assertRaises(FileExistsError): self.reserve("different-output")
        self.assertTrue((self.top / "different-output/FAILURE.json").is_file())
        with self.assertRaises(FileExistsError): self.reserve()

    def test_two_concurrent_outputs_cannot_reserve_same_parent(self):
        def reserve(name):
            try: return self.reserve(name)
            except FileExistsError: return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reserve, ("first", "second")))
        self.assertEqual(sum(r is not None for r in results), 1)
        self.assertEqual(len(list(self.registry.iterdir())), 1)

    def test_new_audit_anchor_does_not_create_a_new_parent_authority(self):
        first = self.inspect()["parent_identity"]
        self.reserve()
        self.audit["summary"]["completed"] = 1000
        write(self.audit_path, self.audit)
        self.audit_sha = p._proof(self.audit_path)["sha256"]
        self.assertEqual(self.inspect()["parent_identity"], first)
        with self.assertRaises(FileExistsError): self.reserve("second")

    def test_changed_inputs_or_original_files_rejected(self):
        source = Path(self.frame["products"]["answer_queries"]["path"])
        original = source.read_bytes()
        source.write_bytes(original + b" ")
        with self.assertRaises(ValueError): self.inspect()
        source.write_bytes(original)
        (self.phase / "slots/0000.json").write_bytes(b"{}")
        with self.assertRaises(ValueError): self.inspect()

    def test_orphan_product_directory_blocks_untouched_dispatch(self):
        (self.phase / "products/0002").mkdir()
        self.anchor()
        with self.assertRaisesRegex(ValueError, "Unexplained"): self.inspect()

    def test_extra_response_or_prior_answer_cannot_be_reanchored_as_safe(self):
        for relative in ("collect/worker/phase/products/0001/responses/000.body", "answer/RESERVED.json", "unexpected.txt"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"unexpected")
            self.anchor()
            with self.subTest(path=relative), self.assertRaises(ValueError): self.inspect()
            path.unlink()
            if relative.startswith("answer/"): path.parent.rmdir()

    def test_torn_or_invalid_journal_prefix_never_becomes_dispatchable(self):
        path = self.phase / "journal.jsonl"
        original = path.read_bytes()
        for payload in (original[:-1], original.replace(b'"sequence":0', b'"sequence":9', 1)):
            path.write_bytes(payload)
            self.anchor()
            with self.assertRaises(ValueError): self.inspect()
        path.write_bytes(original)
        events = deepcopy(self.stage_pairs)
        events[-1] = ("slot_reserved", dict(ordinal=2, id=self.dois[2], branch="shared"))
        journal(path, events)
        self.anchor()
        with self.assertRaisesRegex(ValueError, "Nonsequential"): self.inspect()

    def test_uncertain_request_substitution_and_manufactured_terminal_rejected(self):
        path = self.phase / "products/0001/journal.jsonl"
        pairs = deepcopy(self.uncertain_pairs)
        pairs[-1][1]["byte_reservation"] = 0
        journal(path, pairs)
        self.anchor()
        with self.assertRaisesRegex(ValueError, "uncertain request"): self.inspect()
        journal(path, self.uncertain_pairs + [("http_terminal", dict(transport_status="failed"))])
        self.anchor()
        with self.assertRaisesRegex(ValueError, "uncertain request"): self.inspect()

    def test_completed_source_semantics_reconstructed_not_only_hashed(self):
        path = self.phase / "products/0000/MANIFEST.json"
        content = json.loads(path.read_bytes())
        content["coverage"]["article_retained"] = True
        write(path, content)
        reseal(path.parent)
        slot_path = self.phase / "slots/0000.json"
        slot = json.loads(slot_path.read_bytes())
        slot["product"]["receipt"] = p._proof(path.parent / "RECEIPT.json")
        slot["product"]["manifest"] = p._proof(path)
        write(slot_path, slot)
        self.stage_pairs[3][1]["slot_sha256"] = p._proof(slot_path)["sha256"]
        journal(self.phase / "journal.jsonl", self.stage_pairs)
        self.anchor()
        with self.assertRaisesRegex(ValueError, "coverage reconstruction"): self.inspect()

    def test_altered_original_directory_and_journal_anchors_are_rejected(self):
        self.audit["original_inventory"]["FRAME.json"]["path"] = str(self.top / "FRAME.json")
        write(self.audit_path, self.audit)
        self.audit_sha = p._proof(self.audit_path)["sha256"]
        with self.assertRaisesRegex(ValueError, "locator differs"): self.inspect()

    def test_registry_policy_and_contract_changes_fail_before_reservation(self):
        contract = self.top / "RECOVERY-CONTRACT.md"
        contract.write_bytes(b"Changed contract")
        with self.assertRaisesRegex(ValueError, "contract changed"): self.reserve()
        self.assertEqual(list(self.registry.iterdir()), [])
        self.assertFalse((self.top / "child").exists())

    def test_answer_query_and_hint_order_is_bound(self):
        hint_path = Path(self.frame["products"]["hints"]["path"])
        write(hint_path, list(reversed(self.hints)))
        self.frame["products"]["hints"] = p._proof(hint_path)
        write(self.frame_path, self.frame)
        self.frame_sha = p._proof(self.frame_path)["sha256"]
        write(self.root / "FRAME.json", self.frame)
        self.anchor()
        with self.assertRaisesRegex(ValueError, "Question/hint"): self.inspect()

    def test_write_failure_keeps_authority_and_prevents_another_output(self):
        original = p._write
        def fail_authority(path, value):
            if Path(path).name == "AUTHORITY.json": raise OSError("Invented authority write failure")
            return original(path, value)
        with patch.object(p, "_write", side_effect=fail_authority), self.assertRaises(OSError): self.reserve()
        self.assertEqual(len(list(self.registry.iterdir())), 1)
        self.assertTrue((self.top / "child/FAILURE.json").is_file())
        with self.assertRaises(FileExistsError): self.reserve("later")

    def test_explicit_external_anchors_and_bounds(self):
        with self.assertRaises(ValueError):
            p.inspect_parent(self.audit_path, "0"*64, self.frame_path, self.frame_sha)
        for key, limit in (("MAX_FILES", 1), ("MAX_FILE_BYTES", 10), ("MAX_TOTAL_BYTES", 10)):
            with self.subTest(key=key), patch.object(p, key, limit), self.assertRaises(ValueError): self.inspect()

    def test_registry_and_output_cannot_be_inside_original(self):
        with self.assertRaises(ValueError):
            p.reserve_parent(self.audit_path, self.audit_sha, self.frame_path, self.frame_sha,
                             registry_policy_path=self.registry_policy_path, registry_policy_sha=self.registry_policy_sha,
                             registry=self.registry, output=self.root / "recovery")
        with self.assertRaises(ValueError):
            p.reserve_parent(self.audit_path, self.audit_sha, self.frame_path, self.frame_sha,
                             registry_policy_path=self.registry_policy_path, registry_policy_sha=self.registry_policy_sha,
                             registry=self.root, output=self.top / "child")

    def test_a_different_registry_cannot_bypass_parent_authority(self):
        self.reserve()
        alternate = self.top / "different-registry"
        alternate.mkdir()
        with self.assertRaisesRegex(ValueError, "externally pinned"):
            p.reserve_parent(self.audit_path, self.audit_sha, self.frame_path, self.frame_sha,
                             registry_policy_path=self.registry_policy_path, registry_policy_sha=self.registry_policy_sha,
                             registry=alternate, output=self.top / "another-child")
        self.assertEqual(list(alternate.iterdir()), [])

    def test_transient_policy_parse_cannot_create_second_registry_authority(self):
        self.reserve("first-child")
        alternate = self.top / "alternate-registry"
        alternate.mkdir()
        substituted = json.loads(self.registry_policy_path.read_bytes())
        substituted["registry"] = str(alternate)
        substituted_bytes = p.canonical(substituted)
        actual_read = p.read
        policy_reads = 0

        def transient_read(path, *args, **kwargs):
            nonlocal policy_reads
            raw = actual_read(path, *args, **kwargs)
            if Path(path) == self.registry_policy_path:
                policy_reads += 1
                if policy_reads == 2:
                    return substituted_bytes
            return raw

        with patch.object(p, "read", side_effect=transient_read), self.assertRaises(ValueError):
            p.reserve_parent(self.audit_path, self.audit_sha, self.frame_path, self.frame_sha,
                             registry_policy_path=self.registry_policy_path,
                             registry_policy_sha=self.registry_policy_sha,
                             registry=alternate, output=self.top / "second-child")
        self.assertEqual(list(alternate.iterdir()), [])
        self.assertEqual(len(list(self.registry.iterdir())), 1)

    def test_bound_input_decodes_only_hash_checked_bytes(self):
        expected = self.frame["products"]["answer_queries"]
        replacement = deepcopy(self.queries)
        replacement[0]["question"] = "Unanchored transient replacement question?"
        actual_read = p.read
        input_reads = 0

        def transient_read(path, *args, **kwargs):
            nonlocal input_reads
            raw = actual_read(path, *args, **kwargs)
            if Path(path) == Path(expected["path"]):
                input_reads += 1
                if input_reads == 2:
                    return p.canonical(replacement)
            return raw

        with patch.object(p, "read", side_effect=transient_read):
            self.assertEqual(p._bound(expected), self.queries)

    def test_audit_and_frame_are_not_parsed_from_unhashed_second_read(self):
        actual_read, actual_decode = p.read, p.decode
        for target in (self.audit_path, self.frame_path):
            replacement = json.loads(target.read_bytes())
            replacement["unanchored_probe_marker"] = "different captured bytes"
            substituted_bytes = p.canonical(replacement)
            target_reads = 0
            decoded_unanchored = []

            def transient_read(path, *args, **kwargs):
                nonlocal target_reads
                raw = actual_read(path, *args, **kwargs)
                if Path(path) == target:
                    target_reads += 1
                    if target_reads == 2:
                        return substituted_bytes
                return raw

            def observed_decode(raw):
                if raw == substituted_bytes:
                    decoded_unanchored.append(True)
                return actual_decode(raw)

            with self.subTest(target=target), patch.object(p, "read", side_effect=transient_read), \
                    patch.object(p, "decode", side_effect=observed_decode):
                try:
                    self.inspect()
                except ValueError:
                    # Rejecting a later stability observation is also safe.
                    pass
                self.assertEqual(decoded_unanchored, [])


if __name__ == "__main__":
    unittest.main()
