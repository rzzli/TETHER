"""Property test for asof.ingest._packet_groups (bounded packet layout) with a small artificial limit.

Checks, over 300 random observation lists (ASCII and non-ASCII): order and completeness preserved, every packet
within the limit (envelope, commas, trailing newline included), greedy minimality (adjacent packets cannot merge),
the exact-boundary behaviour, explicit failure for an oversized single observation, and explicit failure of the
default single layout. Run from the project root with the .venv Python. Prints a summary.
"""
import random
import sys

sys.path.insert(0, r"D:\Projects\drug_target_agents\src")
import asof.ingest as ingest  # noqa: E402
from asof.contracts import EvidencePacket  # noqa: E402
from asof.serde import ContractError, canonical  # noqa: E402


def packet_size(observations):
    return len(canonical(EvidencePacket(2, tuple(observations)))) + 1


def make(count, low, high, non_ascii):
    return [{"id": i, "text": ("\u00e9" if non_ascii else "x") * random.randint(low, high)} for i in range(count)]


random.seed(7)
limit = 5000
ingest.MAX_NORMALIZED_JSON_BYTES = limit
envelope = len(canonical(EvidencePacket(2, ()))) + 1
violations = failures_ok = 0
for trial in range(300):
    observations = make(random.randint(1, 60), 1, 400, bool(trial % 2))
    try:
        groups = ingest._packet_groups(tuple(observations), "bounded")
    except ContractError:
        assert any(envelope + len(canonical(o)) > limit for o in observations)
        failures_ok += 1
        continue
    assert [o for g in groups for o in g] == observations
    violations += sum(packet_size(g) > limit for g in groups)
    violations += 1000 * sum(packet_size(list(a) + list(b)) <= limit for a, b in zip(groups, groups[1:]))
print("random trials: 300; oversized-observation failures raised correctly:", failures_ok,
      "; violations:", violations)

sample = make(20, 50, 50, False)
one = len(canonical(sample[0]))
for k in (3, 7):
    exact = envelope + k * one + (k - 1)
    ingest.MAX_NORMALIZED_JSON_BYTES = exact
    groups = ingest._packet_groups(tuple(sample), "bounded")
    print(f"exact limit for {k} observations: first packet holds {len(groups[0])}; max size {max(packet_size(g) for g in groups)} <= {exact}")
ingest.MAX_NORMALIZED_JSON_BYTES = limit
try:
    ingest._packet_groups(tuple(make(3, 10, 10, False) + [{"id": 99, "text": "x" * (limit + 1)}]), "bounded")
    print("oversized single observation: NO ERROR (unexpected)")
except ContractError as error:
    print("oversized single observation ->", error)
ingest.MAX_NORMALIZED_JSON_BYTES = 1000
try:
    ingest._packet_groups(tuple(make(50, 100, 100, False)), "single")
    print("single layout: NO ERROR (unexpected)")
except ContractError as error:
    print("single layout over limit ->", error)
