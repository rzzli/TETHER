"""Independent SOURCE/METADATA arithmetic, never original roster inspection.

The aggregate is supplied retained metadata. Only accepted NEW source text and
its acceptance/peer metadata are read. No reviewed module is imported/executed.
"""
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASIS = ROOT.parent / "recovery-step9-shared-owner-20261029"
SOURCE_PINS = {
    "shared_owner_v2.py": "0ecb8c02e3a8016f2de3a69650b34776de312ffca6f37ded85a31eba9c50c24b",
    "shared_file_ports_v2.py": "a224bfb9e9f33bf2f6b9329f0b337d0076bdab418083d05deb3f59b52722a059",
    "continue_verification_v2.py": "1d05a7398fe215cae987a76ab3960e0dc3730b89fad79caca64c466bac1f4b2f",
    "SHARED-OWNER-SCOPED-ACCEPTANCE-v2.json": "7e0d94849d5ba9da358167a9d103b44fa6ae25acc8e5bed646d2839162220344",
    "SHARED-OWNER-SOURCE-INDEPENDENT-PEER-v2.json": "13b1e793e5275efa74ee0e0b98a8fd944d9ca5675657c1ccc1d888c0bc79453d",
}


def source_locations(raw):
    tree = ast.parse(raw)
    output = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    output[node.name + "." + item.name] = item.lineno
        elif isinstance(node, ast.FunctionDef):
            output[node.name] = node.lineno
    return output


def main():
    captured, pins = {}, {}
    for name, expected in SOURCE_PINS.items():
        path = BASIS / name
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        assert digest == expected, name
        captured[name] = raw
        pins[name] = dict(path=str(path), bytes=len(raw), sha256=digest)
    # These integers are parent-supplied RETAINED aggregate metadata, not a fresh
    # manifest, original-file read/stat/hash, or measured execution input.
    N, total, chunk = 213, 9017363392, 65536
    quotient, remainder = divmod(total, chunk)
    ceil_total = (total + chunk - 1) // chunk
    all_positive_ceils_max = (total - N) // chunk + N
    Rmin, Rmax = ceil_total + 16 * N, all_positive_ceils_max + 16 * N
    Cmin, Cmax = 6 * N + Rmin, 6 * N + Rmax
    assert (quotient, remainder, ceil_total) == (137594, 3008, 137595)
    assert (Rmin, Rmax, Cmin, Cmax) == (141003, 141215, 142281, 142493)
    query_frame_per_file = 8 + 8202 + 8
    query_frames = N * query_frame_per_file
    work_buffers = 65536 + 8202
    assert query_frames == 1750434 and query_frames + work_buffers == 1824172
    quota_scan_visits_min = ceil_total * (ceil_total - 1) // 2
    assert quota_scan_visits_min == 9466123215
    # Small invented JSON values instantiate only the frozen serializer's exact
    # fields/ordinal lengths. This does not execute _packet or model a subject run.
    minimum_closures = [{"file_id": i, "invoked": True, "return_observed": True,
                         "success": True} for i in range(N)]
    minimum_closure_bytes = len(json.dumps(minimum_closures, sort_keys=True,
                                          separators=(",", ":"), ensure_ascii=True,
                                          allow_nan=False).encode("ascii"))
    assert minimum_closure_bytes == 14588 and minimum_closure_bytes > 8192
    owner_lines = source_locations(captured["shared_owner_v2.py"])
    port_lines = source_locations(captured["shared_file_ports_v2.py"])
    findings = [
        dict(id="S1", kind="declared_admission_barrier_not_new_N4_bug",
             location=dict(source="shared_owner_v2.py", line=owner_lines["SharedOwner.admit_plan"]),
             fact="The current exact plan admits <=4 files, <=4096 bytes per file, <=16384 aggregate, capture=True for every file, B/M<=2, R<=68/C<=92/E<=224.",
             implication="The retained213/9GB aggregate is not an admissible current plan. Merely lifting N/R/C is not a production migration."),
        dict(id="S2", kind="retention_representation_barrier_not_empirical_memory_claim",
             location=dict(source="shared_owner_v2.py", line=owner_lines["FileState.__init__"]),
             fact="FileState allocates a full-size bytearray assembly for every admitted file; completed bytes(file.assembly) blobs are additionally retained. Three immutable identity query frames per complete file remain on CallState.",
             conditional_full_roster=dict(query_frames_bytes=query_frames,
                                          query_frames_plus_work_buffers_bytes=query_frames + work_buffers,
                                          current_raw_pool_bytes=131072,
                                          all_capture_assembly_bytes=total,
                                          assemblies_plus_final_blobs_if_policy_carried_over=2 * total),
             implication="Current guards prevent these full-scale allocations. A future design must separate hash-only originals from finite captured sources/metadata and account retained/query/capture/log state before any cap change; the payload numbers do not measure physical RSS."),
        dict(id="S3", kind="source_algorithmic_cost_lower_bound_not_walltime",
             location=dict(source="shared_file_ports_v2.py", line=port_lines["FilePortView._call"]),
             fact="Each ReadFile quota check builds previous by scanning the entire global call list. read_known, handle and canonical CallState membership also scan that list; snapshot/packet repeatedly rescan it per file.",
             conditional_lower_bound=dict(minimum_successful_max64KiB_reads=ceil_total,
                                          one_quota_pass_element_visits_at_least=quota_scan_visits_min,
                                          formula="Q(Q-1)/2, since the ith read sees at least i-1 prior read records"),
             implication="A complete 64KiB policy at this size incurs quadratic list traversal even before extra scans/short reads. Indexed canonical records and incremental per-file/API/byte totals need source-only design and parity tests. This is no measured time or300s fit estimate."),
        dict(id="S4", kind="fixed_packet_representation_barrier",
             location=dict(source="shared_owner_v2.py", line=owner_lines["SharedOwner._packet"]),
             fact="Every compact packet serializes original_closures for every file. Even the shortest boolean/null value lengths with actual IDs0..212 yield a14588-byte array alone.",
             minimal_array_bytes=minimum_closure_bytes, packet_cap_bytes=8192,
             implication="The fixed8192 packet fails for213 files before any other keys, digests, links or LF. A prospectively closed aggregate/partitioned publication contract is needed; never silently trim original states or simply relax bytes."),
        dict(id="S5", kind="finite_generation_and_snapshot_domain",
             location=dict(source="shared_file_ports_v2.py", line=port_lines["AdoptionHooks.buffer_write"]),
             fact="The raw hook validates generation<=68 for both read and query buffers; three successful query frame calls per file advance the reused query generation. Full213 completion would require639 query generations. Public Snapshot helper/literals are also finite N4/C92/E224 domains.",
             implication="A future larger admission requires an exact generation/record/schema/cap derivation, not only larger loop capacities. Existing accepted N4 behavior is consistent with its declared bounds."),
        dict(id="S6", kind="trust_and_origin_scope_limit",
             location=dict(source="shared_owner_v2.py", line=owner_lines["start_injected"]),
             fact="start_injected samples the supplied synthetic clock before setup, after its module was loaded. File binding uses injected Python hooks; sink and factory/checker brands are fictional. Real C-return conversion/storage and production first-entry/checker binding remain absent.",
             implication="Neither index arithmetic nor passing toy histories qualifies actual Win32 APIs, original bytes/identity, imports before t0, physical durability, native source closure, or a production profile."),
    ]
    report = dict(
        schema_version=1, status="SOURCE_METADATA_FULL_ROSTER_FEASIBILITY_ONLY",
        recorded_at_utc="2026-10-29 17:05:38 UTC", reviewer="native_039_acceptance_audit",
        inputs=pins,
        aggregate_basis=dict(origin="Root-supplied retained aggregate only; no manifest/original requalification",
                             files=N, bytes=total, per_file_size_vector_available=False,
                             roles_and_capture_classes_available=False,
                             all_files_positive_established=False),
        arithmetic=dict(
            chunk_bytes=chunk, quotient=quotient, remainder=remainder,
            ceil_aggregate_chunks=ceil_total,
            definitions=dict(P="number of positive-byte files, unknown1..213",
                             A="sum ceil(si/65536) over positive files",
                             R="A+16P reservation capacity, not measured calls",
                             C="6N+R if every file uses the same open/four-query/once-close policy"),
            general_positive_file_bounds=dict(
                P_range=[1, N], A_min=ceil_total,
                A_max_formula="floor((total-P)/65536)+P",
                R_min_formula="137595+16P", R_max_formula="137594+17P",
                proof="ceil(si/q)=1+floor((si-1)/q); sum floors<=floor((total-P)/q). Also total<=q*A. Remainder3008>=P for every P<=213, so the displayed simplified upper bound holds."),
            conditional_all_213_positive=dict(A=[ceil_total, all_positive_ceils_max],
                                               R=[Rmin, Rmax], C=[Cmin, Cmax],
                                               qualification="Conditional reservation arithmetic only; actual reads/returns/short counts unknown"),
            query_policy=dict(frame_bytes_per_file=query_frame_per_file,
                              complete213_retained_frames_bytes=query_frames,
                              work_buffers_bytes=work_buffers,
                              current_raw_cap_bytes=131072,
                              qualification="Only if all213 complete the same four identity queries and existing retention is carried over; no physical memory measurement")),
        findings=findings,
        current_N4_acceptance_reopened=False,
        cap_lift_supported=False,
        empirical_time_or_memory_fit_established=False,
        cheapest_safe_next_stage=[
            "Freeze a finite source-only admission/index/storage/serialization proposal before implementing a larger roster or real entry. Preserve the current N4 acceptance and its exact oracle.",
            "Specify canonical per-file/API/byte counters and indexed call identity so a successful read does not repeatedly scan all prior records; prove same facts/unknowns/once cleanup in the existing bounded synthetic domain before any cap growth.",
            "Prospectively declare hash-only versus captured roles, exact metadata descriptors, per-role size/capture limits, buffer lifetime/retention and bounded observation storage. No current original/CPU/GGUF/pack access follows from that design.",
            "Close a scalable packet/Snapshot/journal schema and all row/count/byte budgets without silent truncation, then give a finite literal/fake preparation set. Do not reuse old189 runtime checker policy by swapping bindings.",
            "Only after independent design/source review should root separately authorize an actual same-Origin bootstrap/typed file binding qualification. No human/tool roundtrips or new timer windows can be excluded from its original300s owner clock."],
        stop_criteria=[
            "No exact role/size/capture vector and complete joint admission/storage/output bounds: no production cap lift or original opens.",
            "Any required retained fact cannot fit the declared representation/cap: reject prospectively, never trim or relabel unknown as zero.",
            "No reviewed real first-entry/raw capture/once-close/checker binding: no production verification claim.",
            "Any proposed300s fit rests only on this aggregate, synthetic elapsed time or unmeasured throughput: gate remains unpassed."],
        preserved_negative_evidence="The original recognition profile remains failed and its whole external verification timed out. This analysis does not rerun it, repair its two unavailable slots, merge post-hoc passes, or infer new token/model behavior.",
        observed_run_cost_or_throughput=None,
        reviewed_subject_modules_executed=0, implementation_changes=0,
        source_test_repeats=0, actual_API_calls=0,
        old_original_or_payload_operations=0, retained_aggregate_requalified=False,
        FFI_registration_proven=False, originals_authenticated=False,
        production_owner_bound=False, real_checkers_bound=False,
        runtime_authorized=False, profile_qualified=False, verification_complete=False,
    )
    destination = ROOT / "SHARED-OWNER-FULL-ROSTER-FEASIBILITY-INDEPENDENT-v1.json"
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    note = """# Independent full-roster feasibility preflight

The accepted N4 prototype remains valid in its bounded injected-source scope. **A production cap lift is unsupported.** This review uses only the supplied retained aggregate213 files/9,017,363,392 bytes and accepted NEW source text; no original file, CPU/GGUF/pack or prior source closure was inspected.

At64KiB, the aggregate quotient is137594 with remainder3008, hence ceil137595. If all213 files have positive integer byte sizes, the exact conditional reservation bounds are R141003–141215 and C142281–142493. Without the per-file vector, positivity, exact R, roles and capture eligibility remain unknown. These are capacities, not observed calls, durations or throughput.

The current four-query retention would keep213×8218=1,750,434 raw frame bytes, exceeding the131072 pool before the73738-byte work buffers. Full-file assemblies plus immutable captures would also preserve the full data twice if the current all-capture policy were carried over; current N4/4KiB/16KiB guards prevent that plan today. These are logical payload counts, not physical RSS measurements.

There are two additional source-derived obstacles. A single global quota-list scan per required64KiB read has at least9,466,123,215 element visits; other read and snapshot paths rescan the same history. Also the shortest possible213-entry `original_closures` JSON array is14588 bytes, already beyond the8192 packet cap before other fields. The hook's generation68 and Snapshot N4/C92/E224 domains likewise are not scalable merely by lifting N.

The cheapest safe next step is a finite source-only admission/index/storage/serialization design: incremental canonical counters, hash-only versus finite captured roles, explicit retained-byte budgets and a prospectively scalable closed output format. Keep current N4/caps/oracles while proving indexed behavior in synthetic tests; do not authorize originals or a larger actual run from aggregate arithmetic. Real first-entry/typed binding/checker qualification is a later separate gate.

No empirical300s or256MiB fit is established. The original failed recognition profile and timed-out external gate remain unchanged; no rerun or repair is implied. Exact derivations, source locations, limits and stop criteria are in the [machine report](SHARED-OWNER-FULL-ROSTER-FEASIBILITY-INDEPENDENT-v1.json). All real qualification flags remain false.
"""
    markdown = ROOT / "SHARED-OWNER-FULL-ROSTER-FEASIBILITY-INDEPENDENT-v1.md"
    with markdown.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(note)
    for path in (destination, markdown):
        raw = path.read_bytes()
        print(json.dumps(dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())))


if __name__ == "__main__":
    main()
