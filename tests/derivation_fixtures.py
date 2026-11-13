"""Fictional, complete-input projection fixtures for strict derivation tests."""

from dataclasses import replace
from datetime import datetime, timezone

from tether_engine.contracts import Derivation, EvidencePacket, Snapshot
from tether_engine.derivations import registry_entry
from tether_engine.serde import decode, fingerprint, read_json, sha256_file, write_json


def qualify_projection(fixture, *, mode="contemporary_method_retrospective"):
    """Qualify one observation; preserve the checked-in v2 fixtures unchanged."""
    packet = decode(EvidencePacket, read_json(fixture / "evidence.json"))
    snapshot = decode(Snapshot, read_json(fixture / "snapshot.json"))
    original = packet.observations[0]
    source = snapshot.sources[0]
    # This test-only original includes the complete typed information being
    # projected, including scope and locator. No field is invented by the method.
    write_json(fixture / source.path, {"observations": [original]})
    source = replace(source, sha256=sha256_file(fixture / source.path))
    parameters = {"input": source.source_id, "pointer": "/observations/0"}
    registered = registry_entry()
    recipe = Derivation(
        schema_version=1,
        method_id="tether.json_projection",
        method_version="1",
        implementation_sha256=registered["implementation_sha256"],
        parameters_sha256=fingerprint(parameters),
        parameters=parameters,
        inputs={source.source_id: source.sha256},
        assets={},
        output_schema="observation.v2",
        method_available_at=registered["method_available_at"],
        mode=mode,
    )
    computed = replace(original, source_kind="computed",
                       computed_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
                       derivation=recipe)
    packet = replace(packet, observations=(computed,) + packet.observations[1:])
    write_json(fixture / "evidence.json", packet)
    snapshot = replace(snapshot, sources=(source,) + snapshot.sources[1:],
                       artifacts=(replace(snapshot.artifacts[0],
                                  sha256=sha256_file(fixture / "evidence.json")),)
                                 + snapshot.artifacts[1:])
    write_json(fixture / "snapshot.json", snapshot)
    return computed


def reseal_observation(fixture, observation):
    packet = decode(EvidencePacket, read_json(fixture / "evidence.json"))
    write_json(fixture / "evidence.json",
               replace(packet, observations=(observation,) + packet.observations[1:]))
    snapshot = decode(Snapshot, read_json(fixture / "snapshot.json"))
    write_json(fixture / "snapshot.json", replace(snapshot, artifacts=(
        replace(snapshot.artifacts[0], sha256=sha256_file(fixture / "evidence.json")),
    ) + snapshot.artifacts[1:]))
