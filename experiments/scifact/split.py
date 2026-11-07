"""Source-connected SciFact splits, built before fitting or candidate evaluation."""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import unicodedata

from tether_engine.serde import ContractError, canonical, freeze


def normalized_claim(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def pair_rows(claims):
    """Annotation-relative pairs; arbitrary unannotated corpus docs are excluded."""
    rows = []
    for claim in sorted(claims, key=lambda row: row["id"]):
        evidence = claim["evidence"]
        for document in sorted(set(claim["cited_doc_ids"]) | {int(k) for k in evidence}):
            rationales = evidence.get(str(document), ())
            sets = [list(r["sentences"]) for r in rationales]
            rows.append({"claim_id": claim["id"], "doc_id": document,
                         "label": rationales[0]["label"] if rationales else "NEI",
                         "rationale_sentences": sorted({s for rationale in sets for s in rationale}),
                         "rationale_sets": sets,
                         "negative_basis": None if rationales else "annotated_cited_document_without_evidence"})
    return rows


def build_split(train, dev, *, seed: int = 20261105):
    """Connect by cited/evidence document or normalized exact claim; quarantine dev overlaps."""
    if type(seed) is not int:
        raise ContractError("Split seed must be an integer")
    claims, origins, parent = {}, {}, {}
    for name, rows in (("train", train), ("dev", dev)):
        for claim in rows:
            key = claim["id"]
            if type(key) is not int or key in claims:
                raise ContractError("Duplicate or invalid train/dev claim ID")
            claims[key], origins[key], parent[key] = claim, name, key

    def find(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def union(left, right):
        left, right = find(left), find(right)
        if left != right:
            parent[max(left, right)] = min(left, right)

    by_document, by_text = defaultdict(list), defaultdict(list)
    for key, claim in sorted(claims.items()):
        for doc in sorted(set(claim["cited_doc_ids"]) | {int(k) for k in claim["evidence"]}):
            by_document[doc].append(key)
        by_text[sha256(normalized_claim(claim["claim"]).encode("utf-8")).hexdigest()].append(key)
    for edges in (by_document, by_text):
        for ids in edges.values():
            for key in ids[1:]:
                union(ids[0], key)
    components = defaultdict(list)
    for key in sorted(claims):
        components[find(key)].append(key)
    groups, eligible = [], []
    for ids in components.values():
        group_id = sha256(canonical(ids)).hexdigest()
        group = {"group_id": group_id, "claim_ids": ids,
                 "train_ids": [key for key in ids if origins[key] == "train"],
                 "dev_ids": [key for key in ids if origins[key] == "dev"]}
        if group["dev_ids"]:
            group["partition"] = "dev_connected"
        else:
            eligible.append(group)
        groups.append(group)
    eligible.sort(key=lambda group: (sha256(f"{seed}:{group['group_id']}".encode()).hexdigest(), group["group_id"]))
    fit_end, tune_end = int(len(eligible) * .70), int(len(eligible) * .85)
    for index, group in enumerate(eligible):
        group["partition"] = "fit" if index < fit_end else "tune" if index < tune_end else "calibration"
    partitions = {name: [] for name in ("fit", "tune", "calibration", "dev", "quarantined_train")}
    group_by_claim = {}
    for group in sorted(groups, key=lambda item: item["group_id"]):
        for key in group["claim_ids"]:
            group_by_claim[str(key)] = group["group_id"]
            partition = group["partition"]
            if partition == "dev_connected":
                partition = "dev" if origins[key] == "dev" else "quarantined_train"
            partitions[partition].append(key)
    for ids in partitions.values():
        ids.sort()
    labels = {name: dict(sorted(Counter(row["label"] for row in pair_rows([claims[k] for k in ids])).items()))
              for name, ids in partitions.items()}
    issues = []
    for name in ("fit", "tune", "calibration"):
        missing = sorted({"SUPPORT", "CONTRADICT", "NEI"} - set(labels[name]))
        if missing:
            issues.append({"partition": name, "missing_pair_labels": missing})
    return freeze({"schema_version": 1, "seed": seed,
                   "algorithm": "source_or_nfkc_casefold_whitespace_exact_claim_components_v1",
                   "assignment": "sorted_seeded_group_hash_floor_70_85_percent_group_boundaries",
                   "partitions": partitions, "group_by_claim": group_by_claim,
                   "groups": sorted(groups, key=lambda row: row["group_id"]),
                   "source_edges": {str(k): v for k, v in sorted(by_document.items()) if len(v) > 1},
                   "exact_text_edges": {k: v for k, v in sorted(by_text.items()) if len(v) > 1},
                   "counts": {name: len(ids) for name, ids in partitions.items()},
                   "eligible_group_count": len(eligible), "group_count": len(groups),
                   "pair_label_counts": labels, "feasibility_issues": issues})
