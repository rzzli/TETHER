"""Explicit collected-source capabilities for the existing recorded composition.

No model adapter or controller. Original inputs are admitted/replayed by the
existing source/retrieval modules; archived root strings are locator metadata.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from collections.abc import Mapping
from pathlib import Path
import re
import time

from tether_engine.contracts import Category
from tether_engine.serde import canonical, fingerprint, freeze
from .baseline_smoke import _read, _write
from .diagnostic_codec import need, quote_choices
from .retrieval_preparation import _records
from .source_preparation import _authority, _source_path_guard, prepare_source_request
from .stable_read import checked_path, deadline_check, stable_files

TRACK = "authority_bound_collected_source_four_arm_recorded"
SOURCE_FILES = {
    "authority.json",
    "package-proof.json",
    "request.json",
    "source-audit.json",
    "source-proofs.json",
    "summary.json",
    "journal.jsonl",
    "receipt.json",
}
MODE_FILES = {"collected-source.json", "collected-source-locations.json"}


def _guard(path):
    _source_path_guard(path)
    need(
        not any(
            p.casefold() in ("benchmark", "completed-responses")
            for p in Path(path).parts
        ),
        "Benchmark and reviewer-output paths cannot authorize collected evidence",
    )


@dataclass(frozen=True)
class CollectedSourceInput:
    authority_path: Path
    authority_sha256: str
    roots: Mapping
    category: Category
    _active: int = field(default=0, init=False, repr=False, compare=False)

    def __post_init__(self):
        need(
            isinstance(self.authority_sha256, str)
            and re.fullmatch("[0-9a-f]{64}", self.authority_sha256),
            "An external collected-source authority anchor is required",
        )
        need(
            type(self.category) is Category and self.category != Category.CLINICAL,
            "Collected interpretation requires an explicit nonclinical category",
        )
        need(
            isinstance(self.roots, Mapping)
            and bool(self.roots)
            and "case_run" not in self.roots,
            "Explicit source roots are required; case_run is reserved",
        )
        roots = {}
        for name, value in self.roots.items():
            path = Path(value)
            need(
                isinstance(name, str)
                and bool(name)
                and path.is_absolute()
                and not path.drive.startswith("\\\\"),
                "Source roots must be explicit absolute local paths",
            )
            roots[name] = str(path)
        object.__setattr__(self, "authority_path", Path(self.authority_path).absolute())
        object.__setattr__(self, "roots", freeze(roots))

    def descriptor(self):
        return freeze(
            dict(
                schema_version=1,
                kind="collected_source_input",
                authority_sha256=self.authority_sha256,
                category=self.category.value,
                input_root_ids=sorted(self.roots),
            )
        )

    def physical_roots(self, root=None):
        roots = {key: Path(value) for key, value in self.roots.items()}
        if root is not None:
            roots["case_run"] = Path(root).absolute()
        return roots

    def assert_active(self):
        need(
            self._active > 0,
            "Collected-source verification requires an active stable-input lease",
        )

    @contextmanager
    def locked(self, deadline):
        _guard(self.authority_path)
        authority, _ = _authority(self.authority_path, self.authority_sha256, deadline)
        required = {p["root_id"] for p in authority["files"].values()}
        need(
            set(self.roots) == required,
            "Collected source root capabilities differ from its input inventory",
        )
        paths = [self.authority_path]
        for pin in authority["files"].values():
            candidate = Path(self.roots[pin["root_id"]]).joinpath(
                *pin["relative_path"].split("/")
            )
            _guard(candidate)  # Before filesystem access, including lstat.
            paths.append(
                checked_path(Path(self.roots[pin["root_id"]]), pin["relative_path"])
            )
        with stable_files(paths, deadline=deadline):
            checked, _ = _authority(
                self.authority_path, self.authority_sha256, deadline
            )
            need(
                canonical(checked) == canonical(authority),
                "Source authority changed before stable admission",
            )
            object.__setattr__(self, "_active", self._active + 1)
            try:
                yield self
            finally:
                object.__setattr__(self, "_active", self._active - 1)

    def prepare_parent(self, root, journal, deadline):
        self.assert_active()
        _write(root, "collected-source.json", self.descriptor())
        _write(
            root,
            "collected-source-locations.json",
            dict(role="locator_metadata_not_access_authority", roots=self.roots),
        )
        journal.append(
            "source_preparing",
            authority_sha256=self.authority_sha256,
            category=self.category.value,
        )
        parent = prepare_source_request(
            self.authority_path,
            self.authority_sha256,
            self.physical_roots(),
            root / "source",
            deadline=deadline,
        )
        deadline_check(deadline)
        journal.append(
            "source_ready",
            receipt_sha256=parent["receipt_sha256"],
            request_sha256=parent["request_sha256"],
            authority_sha256=self.authority_sha256,
            category=self.category.value,
            elapsed_seconds=300 - (deadline - time.monotonic()),
        )

    def retrieval_authority(self, root, events, deadline):
        self.assert_active()
        deadline_check(deadline)
        descriptor, _ = _read(root, "collected-source.json")
        locations, _ = _read(root, "collected-source-locations.json")
        need(
            canonical(descriptor) == canonical(self.descriptor()),
            "Collected source descriptor differs",
        )
        need(
            set(locations) == {"role", "roots"}
            and locations["role"] == "locator_metadata_not_access_authority"
            and set(locations["roots"]) == set(self.roots)
            and all(
                isinstance(v, str) and Path(v).is_absolute()
                for v in locations["roots"].values()
            ),
            "Invalid archived source-locator metadata",
        )
        started = [e["details"] for e in events if e["event"] == "source_preparing"]
        ready = [e["details"] for e in events if e["event"] == "source_ready"]
        need(
            len(started) == len(ready) == 1,
            "Missing or duplicate collected source parent",
        )
        need(
            canonical(started[0])
            == canonical(
                dict(
                    authority_sha256=self.authority_sha256, category=self.category.value
                )
            ),
            "Collected source preparation identity differs",
        )
        parent = root / "source"
        receipt, pin = _read(parent, "receipt.json")
        request, request_pin = _read(parent, "request.json")
        need(
            pin["sha256"] == ready[0]["receipt_sha256"]
            and receipt["authority_sha256"] == self.authority_sha256
            and canonical(request_pin) == canonical(receipt["files"]["request.json"])
            and ready[0]["request_sha256"] == fingerprint(request)
            and ready[0]["authority_sha256"] == self.authority_sha256
            and ready[0]["category"] == self.category.value,
            "Collected source parent binding differs",
        )
        _, records = _records(request)
        need(
            bool(records)
            and all(r.observation.category == self.category for r in records),
            "Collected source category differs",
        )
        return freeze(
            dict(
                schema_version=1,
                kind="real_source_preparation",
                parent=dict(root_id="case_run", relative_path="source"),
                parent_receipt_sha256=pin["sha256"],
                source_authority_sha256=self.authority_sha256,
                candidate_ids=sorted(r.observation.observation_id for r in records),
                grounded_fingerprints={
                    r.observation.observation_id: fingerprint(r) for r in records
                },
                category=self.category.value,
                request_sha256=fingerprint(request),
            )
        )

    @classmethod
    def from_run(cls, root, roots):
        need(
            isinstance(roots, Mapping),
            "Collected replay needs explicit approved input roots",
        )
        descriptor, _ = _read(root, "collected-source.json")
        need(
            set(descriptor)
            == {
                "schema_version",
                "kind",
                "authority_sha256",
                "category",
                "input_root_ids",
            }
            and type(descriptor["schema_version"]) is int
            and descriptor["schema_version"] == 1
            and descriptor["kind"] == "collected_source_input",
            "Invalid collected source descriptor",
        )
        try:
            category = Category(descriptor["category"])
        except (ValueError, TypeError) as error:
            from tether_engine.serde import ContractError

            raise ContractError("Invalid collected category") from error
        result = cls(
            root / "source/authority.json",
            descriptor["authority_sha256"],
            roots,
            category,
        )
        need(
            canonical(result.descriptor()) == canonical(descriptor),
            "Explicit replay source roots differ",
        )
        return result


def literal_document(stage, payload):
    """Deterministic evaluator stimulus; exact strings, never an inference or reference."""
    request = stage["original_request"]
    limit = min(3, request["source_request"]["bounds"]["max_claims"])
    claims = []
    seen = set()
    for alias, choices in quote_choices(request).items():
        text = choices.get("/statement")
        if (
            isinstance(text, str)
            and text.strip()
            and len(text) <= 1800
            and text not in seen
            and len(claims) < limit
        ):
            claims.append(
                dict(
                    kind="source_report",
                    text=text,
                    source_ids=[alias],
                    quote_pointers=["/statement"],
                    limitations=[
                        "Deterministic literal-source fixture; independent scientific assessment was not performed."
                    ],
                )
            )
            seen.add(text)
    response = dict(
        answer_status="partial" if claims else "abstained",
        claims=claims,
        unresolved=[
            "Scientific interpretation is not attempted by this recorded fixture."
        ],
        abstention_reason="Recorded literal-source fixture only; no model or scientific reference answer.",
    )
    return freeze(
        dict(
            schema_version=1,
            role="evaluation_only_fixture",
            request_sha256=fingerprint(stage),
            payload_sha256=fingerprint(payload),
            content_utf8=canonical(response).decode("utf-8"),
            usage=dict(input_tokens=64, output_tokens=64, cost_usd=0.0),
            outcome="return",
        )
    )
