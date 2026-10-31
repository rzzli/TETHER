"""Retain one finite PRE-FIX batch; metadata only, no subject execution."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    "shared_owner_v1.py": "76384e02282b1ce2437b9ff342913297f58ea0858752308724bef912b9e2643b",
    "shared_file_ports_v1.py": "d80f980c771e11ba0116aa3a1a8e526015ce43cafeacc6cf8bc2890f86b4c900",
    "continue_verification_v1.py": "7f52397a8293ae133f019ede1da78881814eb547b026768f072a34e4a4cf8eb2",
    "SHARED-OWNER-FIRST-SOURCE-PAUSE-v1.json": "13f1c7224d2da092ea74ed27815074fd6108c1d43afb5af4fe8ebb23d2e17c97",
    "SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json": "50ee2d7a9285370e6a3f0d18801c43e441b327f7ceac9eb46ebdf0463eff28d6",
    "SHARED-OWNER-INTEGRATION-FIXTURES-v3.json": "e12d6485d0bc38b38c5b4bf33edcab22c1471da15858718185f18f1b5179eee2",
    "SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v3.json": "34c3df0519df387e31439096b8c76e39fc3ce74437e1281346da58ab3a33952e",
    "SHARED-OWNER-ROOT-SOURCE-SCOPE-v1.json": "4db8622f185edb1488a0066205b6248f0eb37b539e0806d04d748f277ea8e6ee",
    "SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json": "eb5147d200bcc0108b71968d69f6b251c29b56dd52d926a8606504682134d9b8",
    "SHARED-OWNER-CONTINUATION-PROPOSAL-v2.json": "90fc021a044bba34953a8f8f8e42b05f5d61f49da945044e1e108f92bb1fc3cd",
    "SHARED-OWNER-WRAPPER-RETURN-BEFORE-v1.json": "8f602d769a2a68a79628b57f689e9e051667764be84f442f506e0e30e56dc8e7",
    "SHARED-OWNER-CONTINUATION-OWNER-BEFORE-v1.json": "8c27fdb9e1748399d577e3c4095d7dd1586309a0ff667eb74b471a50c22b0733",
    "SHARED-OWNER-LATE-SEAL-FIRST-FINDING-v1.json": "5cdc13ecec8f376aa23d101f7abf45747f60f6a8ec1e737cb482149db6848f0e",
    "SHARED-OWNER-INTEGRATION-ACTUAL-FIRST-PROOF-v1.json": "5a104017dfd925f46b11aa15b4a53355a407a8fa0afce6b83c01ec5ae9ccd577",
    "SHARED-OWNER-AUTHOR-CONTROLS-PURE-PROOF-v1.json": "e3b024d10f27f65fede8fb99098b9549ac52d6e7ca5705c1579a5080f383bc52",
    "SHARED-OWNER-AUTHOR-SUPPLEMENT-PURE-PROOF-v1.json": "bda354cd4f25ca85d42538a4d9f3042a32239d7c267446dca35ccbc163eeca6b",
    "probe_shared_owner_adjacent_identity_return_peer_v1.py": "5a11af308d2369effa8897fdf698823d3bf15d8f9a52fe8b4021102d00098e31",
    "SHARED-OWNER-ADJACENT-IDENTITY-RETURN-BEFORE-v1.json": "cdd0c42dc330c4a81feffcca5ab548c244c47f7b88b45e309c2dabd57ae23147",
}


def main():
    pins, data = {}, {}
    for name, expected in EXPECTED.items():
        raw = (ROOT / name).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == expected, name
        pins[name] = dict(path=str(ROOT / name), bytes=len(raw), sha256=digest)
        if name.endswith(".json"):
            data[name] = json.loads(raw)
    own = data["SHARED-OWNER-ADJACENT-IDENTITY-RETURN-BEFORE-v1.json"]
    assert own["status"] == "REPRODUCED_SOURCE_COUNTEREXAMPLES"
    assert own["denied_operation_attempts"] == []
    assert len(own["observations"]) == 2 and all(x["reproduced"] for x in own["observations"])
    full = data["SHARED-OWNER-INTEGRATION-ACTUAL-FIRST-PROOF-v1.json"]
    assert full["histories_executed"] == 48 and full["histories_matched"] == 47
    findings = [
        dict(id="F1", priority="material", source="shared_file_ports_v1.py", line=59,
             issue="Observed wrapper return remains reported as raised after a hook-latched original error",
             observed="Binding invokes hooks.raise_exception and then returns normally. wrapper_return_observed is True but wrapper_state remains raised.",
             required="Retain the observed returned wrapper state and separately stopped/error axes; never erase the original error.",
             evidence=pins["SHARED-OWNER-WRAPPER-RETURN-BEFORE-v1.json"], provenance="OS author before-probe and 12-control first run; not independently replayed here"),
        dict(id="F2", priority="material", source="shared_owner_v1.py", line=169,
             issue="A genuine Continuation exposes a writable owner field",
             observed="Root ordinary assignment rebinds ownerA's genuine Continuation to legitimate ownerB and executes B with A's view.",
             required="The source-issued continuation's canonical owner identity must be immutable under ordinary assignment.",
             evidence=pins["SHARED-OWNER-CONTINUATION-OWNER-BEFORE-v1.json"], provenance="Root retained counterexample; not duplicated here"),
        dict(id="F3", priority="material", source="shared_owner_v1.py", line=372,
             issue="Terminal acknowledgment projection erases a known late sink ACK",
             observed="The complete seal_ack_late history records seal attempted/returned/acknowledged True, then HARD_DEADLINE; terminal.seal_acknowledged is False because it receives try_action's overall success boolean.",
             required="Candidate/cleanup/receipt/seal terminal fields project known callback acknowledgment facts independently from acceptance/deadline success. Late ACK must still veto completion.",
             evidence=pins["SHARED-OWNER-LATE-SEAL-FIRST-FINDING-v1.json"], provenance="Grammar exact first48 source-localized finding; candidate/cleanup/receipt are the adjacent same source pattern, not additional exercised late histories"),
        dict(id="F4", priority="material", source="shared_owner_v1.py", line=190,
             issue="Ordinary SharedOwner.origin assignment restarts a genuine session on another owner's later clock",
             observed=own["observations"][0],
             required="Retain the same canonical Origin object from source creation; ordinary public assignment cannot replace it. Do not create a new window or substitute another owner.",
             evidence=pins["SHARED-OWNER-ADJACENT-IDENTITY-RETURN-BEFORE-v1.json"], provenance="Independent exact synthetic source counterprobe; only owner.origin ordinary assignment, no private field mutation"),
        dict(id="F5", priority="material", source="shared_owner_v1.py", line=184,
             issue="loader.returned drops an observed late compiler return",
             observed=own["observations"][1],
             required="DATA defines loader.returned as ordered known-return names. Retain the name when the compiler returns, before throwable post-return acceptance checks, while keeping accepted False/not cached and the original deadline failure.",
             evidence=pins["SHARED-OWNER-ADJACENT-IDENTITY-RETURN-BEFORE-v1.json"], provenance="Independent exact injected compiler counterprobe; toy helper source is not executed"),
    ]
    record = dict(
        schema_version=1, status="HOLD_FIRST_SOURCE_CANDIDATE_FINITE_BATCH",
        recorded_at_utc="2026-10-29 16:41:25 UTC", reviewer="native_039_acceptance_audit",
        source_pause=pins["SHARED-OWNER-FIRST-SOURCE-PAUSE-v1.json"],
        source_pins=[pins[n] for n in ("shared_owner_v1.py", "shared_file_ports_v1.py", "continue_verification_v1.py")],
        inputs=pins, material_blockers=findings, finite_batch_complete=True,
        method=dict(
            static_review="Read all three exact paused sources against DATA50ee/proposal90fc, finite14groups and literal preparation e12/34c",
            known_evidence="Bound existing author12 controls (11 pass/1 known wrapper failure), supplemental4 pass, root continuation before, Grammar first48 (47 match/1 seal mismatch). No broad replay by reviewer.",
            independent_execution="Two independently authored injected source probes: public Origin replacement and late compiler return projection. Loaded only captured exact new3 source bytes through a closed import map; trusted stdlib preloaded.",
            independent_expected_fixture_cases_read=0,
            independent_toy_helper_execs=0,
            independent_IO_denials=0),
        other_review_observations=[
            "FileRecordRef/CallRef/BufferRef public properties are read-only and canonical registry/call checks exist; the two ordinary assignment witnesses expose adjacent issuer/Origin identity gaps.",
            "Read raw scalar/count/error facts and known bytes are retained independently from hashing/capture; cleanup uses the central once-close path. The finite review introduces no additional raw-count or close finding.",
            "Single provisional plan precedes early input work, current captured contexts and loader use the same registry, and no ordinary module/path fallback exists in the subject sources. This is static/source-only evidence, not real source qualification.",
            "Output sink callbacks remain fictional acknowledgments. Candidate/cleanup/journal/receipt/seal order is explicit; the known ACK vs accepted projection defect is retained rather than changing fixture expectations.",
        ],
        minimal_correction_scope="One named successor resolving the finite five observations in existing identity, returned-fact and terminal projections. No new APIs, Snapshot fields, fixtures, corpus, features or runtime authority requested.",
        deferred_not_classified_as_v1_bugs=[
            "N4 prototype scaling and performance", "full raw-memory fit qualification",
            "real pre-import first entry", "native/ctypes first-return conversion and immediate storage",
            "real file ports, original inputs, source closure or checker qualification",
            "production engine activation or profile/scientific qualification",
        ],
        unchanged_frozen_sources=True, reviewer_source_or_fixture_edits=0,
        actual_API_calls=0, original_or_payload_operations=0,
        FFI_registration_proven=False, production_owner_bound=False,
        real_checkers_bound=False, runtime_authorized=False,
        profile_qualified=False, verification_complete=False,
    )
    destination = ROOT / "SHARED-OWNER-SOURCE-INDEPENDENT-HOLD-v1.json"
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    md = """# Shared-owner first-source peer

**HOLD_FIRST_SOURCE_CANDIDATE_FINITE_BATCH.** The exact three paused sources remain unchanged. This finite pre-fix batch contains five concrete observations in existing identity and returned-fact semantics:

1. A normally returning injected wrapper can retain `wrapper_state=raised` after an original hook error. Its known return and stopped/error state must coexist.
2. A genuine `Continuation.owner` is ordinarily writable; root's retained witness rebinds it to another legitimate owner.
3. The late-seal history retains a known callback ACK in `outputs` but overwrites the terminal acknowledgment with an overall deadline-failure boolean. The same candidate/cleanup/receipt/seal projection must preserve known ACKs while keeping completion false.
4. `SharedOwner.origin` is also ordinarily writable. The [independent witness](SHARED-OWNER-ADJACENT-IDENTITY-RETURN-BEFORE-v1.json) replaces A's original100/395/400 window with genuine B's200/495/500 window after A reaches its work cutoff; A's genuine continuation and unchanged registry then report complete. No private field was altered.
5. An injected compiler returns a value at the work deadline. Its compile record says return observed and not accepted, but `loader.returned` remains empty despite DATA's ordered-known-return definition. Preserve the observed name without accepting or caching the value.

The author controls retain11/12 passing plus4 supplemental passes. Grammar's first full run retains47/48 matching histories, with the late-seal mismatch; root's continuation counterexample is separate. This reviewer did not replay those suites. Two independent synthetic source probes reproduced items4–5 with no I/O attempts under denial hooks; no frozen expected cases or toy helper code was executed by those probes.

The one successor should correct this fixed batch without changing APIs, schema, fixtures or authority. Prototype scaling/performance, full raw-memory fit, real first entry, native-return capture, real file ports/checkers, original-source closure and production/profile qualification remain explicitly deferred; they are not new v1 findings here.

No real API, SDK, native, model/CPU/pack or old-original operation occurred. Exact pins, source locations, observed facts and provenance are in the [HOLD JSON](SHARED-OWNER-SOURCE-INDEPENDENT-HOLD-v1.json). Separate final source peer remains required after corrections and complete passing proofs.
"""
    note = ROOT / "SHARED-OWNER-SOURCE-INDEPENDENT-HOLD-v1.md"
    with note.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(md)
    for path in (destination, note):
        encoded = path.read_bytes()
        print(json.dumps(dict(path=str(path), bytes=len(encoded), sha256=hashlib.sha256(encoded).hexdigest())))


if __name__ == "__main__":
    main()
