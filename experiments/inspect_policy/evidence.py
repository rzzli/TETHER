"""Minimal source-grounded claim authority for the live Inspect witnesses.

This ports a bounded selection/claim commit, not the eight-specialist scheduler.
The same independent native admission/feature rules used in archive conformance
remain explicit reused code. There is no biological correctness oracle here.
"""
from __future__ import annotations

from pathlib import Path

from .records import checked_json, digest, freeze, parse, read_bytes, thaw
from .archive import checked_rows

from equal_policy.independent import (admit, build_features, child, decode,
    descriptor_contract, observation_reason, permitted, prediction, scorer_preflight)


class EvidenceContext:
    def __init__(self, row):
        row = checked_rows([row])[0]
        root = Path(row["bundle_root"])
        pin = row["descriptor"]
        descriptor = descriptor_contract(thaw(checked_json(root / pin["path"],
                                          {key: pin[key] for key in ("sha256", "bytes")})))
        if descriptor["operation"] != "prepare_run" or descriptor["variant"] != "core_v2_catalog1":
            raise ValueError("Runtime witness accepts core-v2 preparation only")
        paths = descriptor["paths"]
        case = decode("Case", parse(read_bytes(child(root, paths["case"]))))
        snapshot_path = child(root, paths["snapshot"])
        snapshot = decode("Snapshot", parse(read_bytes(snapshot_path)))
        catalog = parse(read_bytes(child(root, paths["catalog"]))) if paths.get("catalog") else None
        source = admit(case, snapshot, snapshot_path.parent, catalog)
        scorer = decode("Scorer", parse(read_bytes(child(root, paths["scorer"])))) if paths.get("scorer") else None
        applicability = scorer_preflight(case, snapshot["profile"], scorer)
        self.case = freeze(case)
        self.snapshot = freeze(snapshot)
        self.records = freeze(source["records"])
        self.fingerprints = freeze(source["admitted_fingerprints"])
        self.proofs = freeze(source["proofs"])
        self.exclusions = freeze(source["exclusions"])
        self._graph = source["graph"]
        self._eligible = freeze(source["eligible"])
        self._scorer = freeze(scorer)
        self._ledgers = {}
        self.report = freeze({"case": case, "snapshot": snapshot,
            "source_proofs": source["proofs"], "admitted_fingerprints": source["admitted_fingerprints"],
            "exclusions": source["exclusions"], "scorer_preflight": applicability,
            "scorer_sha256": digest(scorer), "descriptor_sha256": pin["sha256"]})

    def offered(self, category):
        case = thaw(self.case)
        return tuple(key for key, item in self.records.items()
                     if permitted(case, thaw(item), category) and item["observation"]["status"] == "observed")

    def review(self, selected, category):
        if type(selected) is not list or any(type(key) is not str for key in selected) or len(selected) != len(set(selected)):
            raise ValueError("Unique observation-ID list required")
        offered = set(self.offered(category))
        if not set(selected) <= offered:
            raise ValueError("Selected observation is outside the offered request")
        return tuple(selected)

    def commit(self, selected, category, record, *, clock, deadline):
        selected = self.review(selected, category)
        claims = self._ledgers.setdefault(str(record.path), [])
        prior_ids = {claim["evidence"]["observation"]["observation_id"] for claim in claims}
        if set(selected) & prior_ids:
            raise ValueError("Previously committed observation cannot be committed again")
        initial_count = len(claims)
        case = thaw(self.case)
        stopped = False
        for key in selected:
            if clock() >= deadline:
                record.append("claim_commit_budget_stop", {"committed": len(claims) - initial_count, "reviewed": len(selected)})
                stopped = True
                break
            grounded = thaw(self.records[key])
            if digest(grounded) != self.fingerprints[key] or not permitted(case, grounded, category):
                raise ValueError("Claim source fingerprint or capability differs")
            observation, citation = grounded["observation"], grounded["citation"]
            artifact = thaw(self._eligible[citation["artifact_id"]])
            if observation["status"] != "observed" or observation_reason(observation, artifact, self._graph, case) is not None:
                raise ValueError("Claim fails write-time eligibility")
            claim = freeze({"claim_id": "claim-" + digest({"case": case["case_id"], "evidence": grounded})[:20],
                            "specialist": category, "evidence": grounded,
                            "admitted_fingerprint": self.fingerprints[key],
                            "extraction_mode": "verbatim_source_selection"})
            record.append("claim_committed", claim)
            claims.append(claim)
        features = build_features(case, thaw(claims))
        predicted = prediction(case, self.snapshot["profile"], features, thaw(self._scorer),
                               run_status="budget_exhausted" if stopped else "completed")
        return freeze({"reviewed_ids": selected, "claims": claims,
                       "features": features, "prediction": predicted,
                       "status": "budget_exhausted" if stopped else "completed"})
