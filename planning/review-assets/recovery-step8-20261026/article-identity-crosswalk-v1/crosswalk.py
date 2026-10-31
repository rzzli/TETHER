"""Identity-only JSON projection; never decode unselected string values."""
from pathlib import Path
import collections
import hashlib
import json
import re
import time

ROOT = Path(__file__).resolve().parents[4]
BASE = Path(__file__).resolve().parent
METHOD = json.loads((BASE / "method.json").read_text())
IDS = set(METHOD["article_ids"])
TOKEN = re.compile(rb'"(?:[^"\\]|\\.)*"|[{}\[\]]|[^\s,{}\[\]:]+')
STRING = re.compile(rb'"(?:[^"\\]|\\.)*"')
IDENTITY = {
    "observation_id", "target_id", "indication_id", "study_id",
    "dependency_group", "source_kind", "input_refs",
}
METRICS = {
    "literature", "pmid", "pubmedId", "pubmed_id", "articleId", "article_id",
    "studyId", "study_id", "cohortId", "cohort_id", "accession", "accessions",
    "studyAccession", "geoAccession", "geo_accession", "pmcid", "doi",
}
LOCATOR = {"evidence_id", "datasource_id", "row_group", "row_index", "row_in_group", "row", "path", "file", "source_id", "list_index"}
TRIE = {"schema_version": True, "observations": {"*": {
    **dict.fromkeys(IDENTITY, True), "context": {"cohort_ids": True},
    "source_metrics": dict.fromkeys(METRICS, True),
    "source_locator": dict.fromkeys(LOCATOR, True),
}}}


class Projection:
    def __init__(self, raw):
        self.raw = raw
        self.pos = 0
        self.metric_keys = collections.Counter()

    def ws(self):
        while self.pos < len(self.raw) and self.raw[self.pos] in b" \r\n\t":
            self.pos += 1

    def skip(self):
        self.ws()
        token = TOKEN.match(self.raw, self.pos)
        if token is None:
            raise ValueError("Invalid value")
        self.pos = token.end()
        if token.group() not in (b"{", b"["):
            return
        depth = 1
        for part in TOKEN.finditer(self.raw, self.pos):
            t = part.group()
            if t in (b"{", b"["):
                depth += 1
            elif t in (b"}", b"]"):
                depth -= 1
                if depth == 0:
                    self.pos = part.end()
                    return
        raise ValueError("Unterminated container")

    def read(self, rule, location=""):
        self.ws()
        if rule is True:
            start = self.pos
            self.skip()
            return json.loads(self.raw[start:self.pos])
        ch = self.raw[self.pos:self.pos + 1]
        self.pos += 1
        if ch == b"[":
            out = []
            self.ws()
            while self.raw[self.pos:self.pos + 1] != b"]":
                out.append(self.read(rule["*"], location + "/*"))
                self.ws()
                if self.raw[self.pos:self.pos + 1] != b",":
                    break
                self.pos += 1
            assert self.raw[self.pos:self.pos + 1] == b"]"
            self.pos += 1
            return out
        if ch != b"{":
            raise ValueError("Expected projected object")
        out = {}
        self.ws()
        while self.raw[self.pos:self.pos + 1] != b"}":
            self.ws()
            token = STRING.match(self.raw, self.pos)
            if token is None:
                raise ValueError("Invalid object key")
            key = json.loads(token.group())
            self.pos = token.end()
            self.ws()
            assert self.raw[self.pos:self.pos + 1] == b":"
            self.pos += 1
            if location.endswith("/source_metrics"):
                self.metric_keys[key] += 1
            if key in rule:
                out[key] = self.read(rule[key], location + "/" + key)
            else:
                self.skip()
            self.ws()
            if self.raw[self.pos:self.pos + 1] != b",":
                break
            self.pos += 1
        assert self.raw[self.pos:self.pos + 1] == b"}"
        self.pos += 1
        return out


def proof(path):
    b = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)}


def values(value):
    if isinstance(value, dict):
        for v in value.values():
            yield from values(v)
    elif isinstance(value, list):
        for v in value:
            yield from values(v)
    elif isinstance(value, (str, int)):
        yield str(value)


def main():
    started = time.monotonic()
    result = {"schema_version": 1, "role": "evaluation_only", "agent_visible": False,
              "method_proof": proof(BASE / "method.json"), "script_proof": proof(Path(__file__)),
              "article_ids": sorted(IDS), "descriptors": [], "packet_proofs": [],
              "matches": [], "unknown": [], "source_metric_key_counts": {},
              "freshness_established": False, "protected_files_read": False,
              "candidate_outputs_read": False, "source_text_values_decoded": False}
    metric_keys = collections.Counter()
    total = with_literature = 0
    for declared in METHOD["descriptor_proofs"]:
        path = ROOT / declared["path"]
        assert proof(path) == declared
        descriptor = json.loads(path.read_bytes())
        result["descriptors"].append(declared)
        for artifact in descriptor["artifacts"]:
            if artifact["role"] not in METHOD["bounds"]["roles"] or not artifact["access_approved"]:
                result["unknown"].append({"descriptor": declared["path"], "reason": "ineligible_role_or_access"})
                continue
            p = (path.parent / artifact["path"]).resolve()
            rel = p.relative_to(ROOT).as_posix()
            if not rel.startswith("data/derived/") or p.name not in ("evidence.json",) and not re.fullmatch(r"evidence-\d+\.json", p.name):
                result["unknown"].append({"path": rel, "reason": "not_whitelisted_evidence_packet"})
                continue
            if any(x in rel.lower() for x in ("normalized-outcomes", "gold", "labels", "answers", "candidate")):
                result["unknown"].append({"path": rel, "reason": "protected_path"})
                continue
            if p.stat().st_size > METHOD["bounds"]["packet_maximum_bytes"]:
                result["unknown"].append({"path": rel, "reason": "size_limit"})
                continue
            raw = p.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            if digest != artifact["sha256"]:
                result["unknown"].append({"path": rel, "reason": "hash_mismatch"})
                continue
            parser = Projection(raw)
            packet = parser.read(TRIE)
            parser.ws()
            assert parser.pos == len(raw)
            metric_keys.update(parser.metric_keys)
            rows = packet["observations"]
            result["packet_proofs"].append({"path": rel, "sha256": digest, "bytes": len(raw), "descriptor": declared["path"], "observations": len(rows)})
            for index, row in enumerate(rows):
                total += 1
                metrics = row.get("source_metrics", {})
                if metrics.get("literature"):
                    with_literature += 1
                hits = []
                for field in METRICS:
                    for value in values(metrics.get(field)):
                        normalized = re.sub(r"^(?:PMID\s*:\s*|https?://pubmed\.ncbi\.nlm\.nih\.gov/)", "", value, flags=re.I).rstrip("/")
                        if normalized in IDS:
                            hits.append({"article_id": normalized, "field": "source_metrics/" + field, "value": value})
                if hits:
                    result["matches"].append({"packet": rel, "observation_index": index, "identity_metadata": row, "hits": hits})
    result["source_metric_key_counts"] = dict(sorted(metric_keys.items()))
    result["coverage"] = {"descriptors_verified": len(result["descriptors"]), "packets_verified_projected": len(result["packet_proofs"]), "observation_occurrences": total, "observation_occurrences_with_literature": with_literature, "matched_observation_occurrences": len(result["matches"])}
    result["limitations"] = ["Normalized selected packet identity metadata only; raw ancestors not traversed.", "Identity absence, missing literature fields and missing cohort/article aliases remain unknown exposure; not freshness.", "Repeated snapshot occurrences are not independent scientific records.", "Exact published Virtual Biotech analytic roster and complete GEO/article crosswalk remain unresolved."]
    result["elapsed_seconds"] = time.monotonic() - started
    (BASE / "crosswalk-report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"coverage": result["coverage"], "unknown": result["unknown"], "article_matches": dict(collections.Counter(h["article_id"] for m in result["matches"] for h in m["hits"])), "elapsed_seconds": result["elapsed_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
