"""Collected-source composition requirements; fixtures never represent human judgments."""

from dataclasses import FrozenInstanceError
from pathlib import Path
import tempfile
import hashlib
import io
import time
from dataclasses import replace
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor

from tether_engine.contracts import Category
from tether_engine.serde import ContractError, canonical, fingerprint, freeze, parse_json
from tether_engine.study.collected_source import CollectedSourceInput, literal_document, TRACK
from tether_engine.study import authority_four_arm as composition
from tether_engine.study import source_preparation as source_module
from tether_engine.study import tokenization as tok
from tests import test_study_source_preparation as sources
from tests import test_study_tokenization as tokens


class CollectedInputTests(unittest.TestCase):
    def test_roots_are_copied_and_deeply_immutable(self):
        roots = {"project": str(Path.cwd())}
        source = CollectedSourceInput(
            Path.cwd() / "authority.json", "a" * 64, roots, Category.LITERATURE
        )
        roots["project"] = "changed"
        self.assertEqual(source.roots["project"], str(Path.cwd()))
        with self.assertRaises(TypeError):
            source.roots["project"] = "changed"
        with self.assertRaises(FrozenInstanceError):
            source.authority_sha256 = "0" * 64

    def test_clinical_reserved_roots_and_unanchored_input_are_rejected(self):
        for anchor, roots, category in (
            ("x", {"project": str(Path.cwd())}, Category.LITERATURE),
            ("a" * 64, {"case_run": str(Path.cwd())}, Category.LITERATURE),
            ("a" * 64, {"project": str(Path.cwd())}, Category.CLINICAL),
        ):
            with (
                self.subTest(anchor=anchor, category=category),
                self.assertRaises(ContractError),
            ):
                CollectedSourceInput(
                    Path.cwd() / "authority.json", anchor, roots, category
                )

    def test_lease_required_and_protected_authority_fails_before_open(self):
        root = Path(__file__).resolve().parents[1] / "data/cache"
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            path = Path(tmp) / "benchmark" / "authority.json"
            source = CollectedSourceInput(
                path, "a" * 64, {"project": tmp}, Category.LITERATURE
            )
            with self.assertRaises(ContractError):
                source.assert_active()
            import time

            with self.assertRaises(ContractError):
                with source.locked(time.monotonic() + 20):
                    self.fail("Protected path cannot establish a lease")

    def test_wrong_roots_or_anchor_fail_before_input_path_lookup(self):
        with tempfile.TemporaryDirectory(dir=tokens.TEMP_ROOT) as tmp:
            source, _ = fixture_source(Path(tmp))
            wrong = (
                replace(source, roots={"other": str(Path(tmp))}),
                replace(source, authority_sha256="0" * 64),
            )
            for candidate in wrong:
                with (
                    self.subTest(roots=candidate.roots),
                    patch(
                        "tether_engine.study.collected_source.checked_path",
                        side_effect=AssertionError(
                            "No data lookup before authority admission"
                        ),
                    ),
                ):
                    with self.assertRaises(ContractError):
                        with candidate.locked(time.monotonic() + 20):
                            self.fail("Invalid authority cannot be active")


class LiteralFixtureTests(unittest.TestCase):
    def test_literal_text_is_unchanged_and_not_an_inference(self):
        with tempfile.TemporaryDirectory(dir=tokens.TEMP_ROOT) as tmp:
            _, built = fixture_source(Path(tmp))
            stage = {"original_request": built["request"]}
            doc = literal_document(stage, {"prompt": "fixture"})
            response = parse_json(doc["content_utf8"].encode())
            rows = built["request"]["source_request"]["evidence"]
            self.assertEqual(
                [r["text"] for r in response["claims"]],
                [r["scientific_record"]["statement"] for r in rows[:2]],
            )
            self.assertTrue(
                all(r["kind"] == "source_report" for r in response["claims"])
            )
            self.assertEqual(doc["role"], "evaluation_only_fixture")

    def test_whole_oversized_statement_abstains_instead_of_clipping(self):
        template = sources.CompilerTests()
        template.setUp()
        record = replace(
            template.record,
            observation=replace(template.record.observation, statement="x" * 1801),
        )
        selection = dict(
            template.selection, observation_ids=[record.observation.observation_id]
        )
        request, _ = source_module.compile_request(
            template.case, template.store(record), selection
        )
        response = parse_json(
            literal_document({"original_request": request}, {"prompt": "fixture"})[
                "content_utf8"
            ].encode()
        )
        self.assertEqual(response["answer_status"], "abstained")
        self.assertEqual(response["claims"], [])
        self.assertEqual(
            len(
                request["source_request"]["evidence"][0]["scientific_record"][
                    "statement"
                ]
            ),
            1801,
        )


def fixture_source(root):
    """Invented typed records; raw-admission seam is mocked only in this test."""
    template = sources.CompilerTests()
    template.setUp()
    records = [
        replace(
            template.record,
            observation=replace(
                template.record.observation,
                observation_id="invented-collected-" + str(i),
                statement="Invented source statement " + str(i),
            ),
        )
        for i in range(3)
    ]
    store = template.store()
    store.admitted_fingerprints = {
        r.observation.observation_id: fingerprint(r) for r in records
    }
    store.query = lambda case, category: (
        tuple(records) if category == Category.LITERATURE else ()
    )
    selection = dict(
        template.selection,
        observation_ids=[r.observation.observation_id for r in records],
    )
    request, _ = source_module.compile_request(template.case, store, selection)
    inputs = root / "inputs"
    inputs.mkdir()
    a = sources.authority()
    for name, pin in a["files"].items():
        path = inputs / pin["relative_path"]
        path.write_bytes(b"{}")
        pin.update(sha256=hashlib.sha256(b"{}").hexdigest(), bytes=2)
    a["selection"] = selection
    path = root / "authority.json"
    path.write_bytes(canonical(a))
    source = CollectedSourceInput(
        path,
        hashlib.sha256(path.read_bytes()).hexdigest(),
        {"project": str(inputs)},
        Category.LITERATURE,
    )
    built = freeze(
        dict(
            request=request,
            request_sha256=fingerprint(request),
            source_proofs=[],
            source_audit=dict(
                selected_rows=[
                    dict(
                        observation_id=r.observation.observation_id,
                        observation_sha256=fingerprint(r.observation),
                        whole_record_equal=True,
                    )
                    for r in records
                ]
            ),
            scientific_validation="not_attempted",
            model_calls=0,
        )
    )
    return source, built


class HundredTokenChild(tokens.FakeChild):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stdout = io.BytesIO(
            (
                "["
                + ", ".join(str(i) for i in range(100))
                + "]\nTotal number of tokens: 100\n"
            ).encode()
        )


class CollectedLifecycleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tokens.TokenizationArtifactTests.setUpClass()
        cls.temp = tempfile.TemporaryDirectory(dir=tokens.TEMP_ROOT)
        cls.root = Path(cls.temp.name)
        cls.source, cls.built = fixture_source(cls.root)
        cls.raw_patch = patch.object(source_module, "_build", return_value=cls.built)
        cls.raw_patch.start()
        real_run = tok._run_child
        with patch.object(
            tok,
            "_run_child",
            side_effect=lambda *a: real_run(*a, process_factory=HundredTokenChild),
        ):
            cls.result = composition.smoke(
                cls.root / "run",
                tokens.TokenizationArtifactTests.authority,
                tokens.TokenizationArtifactTests.roots,
                collected_source=cls.source,
            )

    @classmethod
    def tearDownClass(cls):
        cls.raw_patch.stop()
        cls.temp.cleanup()
        tokens.TokenizationArtifactTests.tearDownClass()

    def test_collected_case_not_invented_and_source_inclusive_replay(self):
        self.assertEqual(self.result["track"], TRACK)
        self.assertNotIn("fixture", self.result)
        self.assertEqual(self.result["recorded_calls"], 6)
        with patch.object(
            tok.subprocess, "Popen", side_effect=AssertionError("No replay child")
        ):
            checked = composition.verify(
                self.root / "run",
                self.result["receipt_sha256"],
                source_roots=self.source.roots,
            )
        self.assertEqual(checked, self.result)
        for arm in ("extractive", "lexical"):
            result = parse_json((self.root / "run" / f"{arm}-result.json").read_bytes())
            self.assertNotIn("invented", result["scope"])
            self.assertEqual(result["policy"]["max_excerpts"], 2)
            self.assertEqual(result["coverage"]["observations_available"], 3)
            self.assertEqual(result["coverage"]["missing_input_count"], 65)
            self.assertEqual(result["features"], {})
        response = parse_json((self.root / "run/cells/00/response.json").read_bytes())
        self.assertTrue(
            all(c["kind"] == "source_report" for c in response["response"]["claims"])
        )
        self.assertEqual(self.source._active, 0)

    def test_explicit_replay_roots_required_no_archived_root_fallback(self):
        with self.assertRaises(ContractError):
            composition.verify(self.root / "run", self.result["receipt_sha256"])
        with self.assertRaises(ContractError):
            composition.verify(
                self.root / "run",
                self.result["receipt_sha256"],
                source_roots={"other": str(self.root)},
            )

    def test_source_lease_denies_ordinary_mutation_and_releases(self):
        path = Path(self.source.roots["project"]) / "case.json"
        with self.source.locked(time.monotonic() + 20):
            with self.assertRaises(OSError):
                path.write_bytes(b"changed")
        self.assertEqual(path.read_bytes(), b"{}")
        self.assertEqual(self.source._active, 0)

    def test_wrong_category_fails_before_token_or_consumption(self):
        bad = replace(self.source, category=Category.GENETICS)
        with patch.object(
            composition, "tokenize_prompt", side_effect=AssertionError("No quote child")
        ):
            with self.assertRaises(ContractError):
                composition.smoke(
                    self.root / "wrong-category", {}, {}, collected_source=bad
                )
        self.assertEqual(bad._active, 0)
        failure = parse_json((self.root / "wrong-category/failure.json").read_bytes())
        self.assertEqual(failure["accepted_cells"], [])
        self.assertFalse((self.root / "wrong-category/receipt.json").exists())

    def test_existing_output_cannot_repeat_dispatch(self):
        with patch.object(
            composition, "tokenize_prompt", side_effect=AssertionError("No repeat")
        ):
            with self.assertRaises(FileExistsError):
                composition.smoke(
                    self.root / "run", {}, {}, collected_source=self.source
                )

    def test_verifier_without_source_lease_fails_before_cache_use(self):
        events = composition.read_chain(self.root / "run/journal.jsonl")
        verifier = composition.AuthorityRecordedVerifier(
            self.root / "run",
            events[0]["details"]["run_id"],
            deadline=time.monotonic() + 20,
            collected_source=self.source,
        )
        with self.assertRaises(ContractError):
            verifier.original()

    def test_source_setup_exhaustion_cannot_reset_case_clock(self):
        now = [time.monotonic()]
        original = CollectedSourceInput.prepare_parent

        def delayed(source, root, journal, deadline):
            original(source, root, journal, deadline)
            now[0] = deadline + 1

        with (
            patch.object(time, "monotonic", side_effect=lambda: now[0]),
            patch.object(CollectedSourceInput, "prepare_parent", new=delayed),
            patch.object(
                composition,
                "tokenize_prompt",
                side_effect=AssertionError("No tokenizer after source timeout"),
            ),
        ):
            with self.assertRaises(TimeoutError):
                composition.smoke(
                    self.root / "source-timeout", {}, {}, collected_source=self.source
                )
        self.assertEqual(self.source._active, 0)
        self.assertFalse((self.root / "source-timeout/receipt.json").exists())

    def test_concurrent_output_reserves_source_preparation_only_once(self):
        calls = []

        def stop_before_quote(source, root, journal, deadline):
            calls.append(1)
            raise RuntimeError("Invented fixture stops before tokenization")

        def attempt():
            try:
                composition.smoke(
                    self.root / "concurrent", {}, {}, collected_source=self.source
                )
            except (RuntimeError, FileExistsError) as error:
                return type(error).__name__
            self.fail("Fixture must not succeed")

        with (
            patch.object(CollectedSourceInput, "prepare_parent", new=stop_before_quote),
            patch.object(
                composition,
                "tokenize_prompt",
                side_effect=AssertionError("No tokenizer fixture"),
            ),
        ):
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: attempt(), range(2)))
        self.assertCountEqual(results, ["RuntimeError", "FileExistsError"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.source._active, 0)
