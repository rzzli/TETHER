"""An append-only run ledger that accepts only admitted, grounded records."""

from __future__ import annotations

from .chrono import EvidenceStore
from .contracts import Case, Category, Claim, EvidenceStatus
from .serde import ContractError, fingerprint


class EvidenceLedger:
    def __init__(self, case: Case, store: EvidenceStore):
        self.case = case
        self.store = store
        self._claims: list[Claim] = []
        self._selected: set[str] = set()

    @property
    def claims(self) -> tuple[Claim, ...]:
        return tuple(self._claims)

    def append(self, category: Category, observation_id: str) -> Claim:
        evidence = self.store.lookup(observation_id)
        observation = evidence.observation
        if (observation.category != category or observation.target_id != self.case.hypothesis.target_id or
                observation.indication_id != self.case.hypothesis.indication_id or
                not self.case.permits_program(observation.program_id)):
            raise ContractError("Claim is outside specialist/case retrieval capability")
        digest = fingerprint(evidence)
        if digest != self.store.admitted_fingerprints.get(observation_id):
            raise ContractError("Claim no longer matches admitted source fingerprint")
        if observation.source_kind != "computed" and observation.availability.exclusion(self.case.cutoff):
            raise ContractError("Claim failed the write-time availability gate")
        if observation.status != EvidenceStatus.OBSERVED:
            raise ContractError("Unavailable evidence must be reported as coverage, not a factual claim")
        if observation_id in self._selected:
            raise ContractError("Duplicate claim selection")
        claim = Claim("claim-" + fingerprint({"case": self.case.case_id, "evidence": evidence})[:20],
                      category, evidence, "verbatim_source_selection", digest)
        self._claims.append(claim)
        self._selected.add(observation_id)
        return claim

