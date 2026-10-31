"""Design arithmetic and source-contract review only; no pack or runtime work."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).parent
PROFILE = HERE.parent / "recovery-step9-unicode-control-20261029"


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path.absolute()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")


def main():
    contract_path = HERE / "UNICODE-WIRE-DESIGN-CONTRACT-v1.json"
    proposal_pin = pin(contract_path)
    assert proposal_pin["sha256"] == "e7219e813562423ab9b71f39073be486c62ebf8357551f7b79c8956a2ef13302"
    proposal = json.loads(contract_path.read_text(encoding="utf-8"))
    semantic = proposal["semantic_contract"]
    semantic_sha = hashlib.sha256(canonical(semantic)).hexdigest()
    assert semantic_sha == proposal["semantic_sha256"] == "778d21d3fd70e72574750a8f4f63dc3184ce62a62e13728d57ec980afb16269c"
    freeze_path = HERE / "UNICODE-WIRE-DESIGN-FREEZE-v1.json"
    freeze_pin = pin(freeze_path)
    assert freeze_pin["sha256"].startswith("0a5464de")
    names = ("UNICODE-CONTROL-CONTRACT-v2.json", "UNICODE-CONTROL-CORPUS-v1.json", "UNICODE-CONTROL-STAGES-v1.json",
             "UNICODE-CONTROL-FIXTURE-FREEZE-v1.json", "UNICODE-PIECE-ANALYZER-CONTRACT-v1.json",
             "UNICODE-PIECE-ANALYZER-SCOPED-ACCEPTANCE-v2.json", "unicode_piece_analyzer_v1.py")
    basis = {name: pin(PROFILE / name) for name in names}
    assert all(basis[name]["sha256"] == proposal["basis"][name]["sha256"] for name in names)
    profile = json.loads((PROFILE / names[0]).read_text(encoding="utf-8"))
    cases = json.loads((PROFILE / names[1]).read_text(encoding="utf-8"))["cases"]
    eligible = [row for row in cases if row["expected"]["native_byte_eligible"]]
    population = [row for row in cases if row["coverage_population"]]
    counts = dict(cases=len(cases), eligible=len(eligible), harness=len(cases)-len(eligible), population=len(population),
                  stage_instances=len({row["stage_id"] for row in cases}), unique_grammars=len({row["grammar_sha256"] for row in cases}),
                  authored_members=sum(row["expected"]["native_membership"] is True for row in eligible),
                  authored_nonmembers=sum(row["expected"]["native_membership"] is False for row in eligible))
    assert list(counts.values()) == [84, 78, 6, 68, 4, 2, 69, 9]
    eligible_bytes = sum(row["bytes"] for row in eligible)
    largest = max(row["bytes"] for row in eligible)
    document_tokens = sum(4*row["bytes"]+32 for row in eligible)
    prefix_tokens = 4*(4*largest+32)
    token_work = document_tokens+prefix_tokens
    assert (eligible_bytes, largest, document_tokens, token_work) == (14941, 420, 62260, 69108)
    caps = semantic["API_accounting"]["hard_caps"]
    upper = semantic["API_accounting"]["positive_fixed_profile_upper_bounds"]
    assert len(caps) == len(upper) == 25 and set(caps) == set(upper)
    assert all(type(upper[k]) is int and 0 <= upper[k] <= caps[k] for k in caps)
    assert sum(caps.values()) == 4276181 and sum(upper.values()) == 530477
    assert upper["llama_sampler_apply"] == token_work + 82*64 == 74356
    assert upper["llama_sampler_accept"] == token_work
    assert upper["llama_token_to_piece"] == 2*document_tokens == 124520
    assert upper["llama_tokenize"] == 2*78 == 156
    assert upper["llama_sampler_init_grammar"] == upper["llama_sampler_free"] == 82
    envelope = semantic["wire_size"]["fixed_case_sizing_envelope"]
    arrays = envelope["body"]["ledger"]
    measured = len(canonical(envelope)+b"\n")-sum(len(canonical(v)) for v in arrays.values())
    assert measured == 6407
    envelope["body"]["observation"]["native_member"] = False
    false_measured = len(canonical(envelope)+b"\n")-sum(len(canonical(v)) for v in arrays.values())
    assert false_measured == 6408 < 8192
    reserved = 96*65536+96*8192+64*8192+4*65536+16*8192
    fixed84 = 84*65536+84*8192+64*8192+4*65536+16*8192
    assert reserved == 7995392 and fixed84 == 7110656
    assert reserved+4096+65536 == 8065024 < 8388608
    assert profile["JSONL_reservation"]["global_footer_rows"] == dict(count=16, bytes_each=8192)
    record = dict(schema_version=1, recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status="DESIGN_REVISION_REQUIRED_BEFORE_LITERAL_FRAMING_FIXTURE_FREEZE",
        scope="Independent design/data arithmetic review only; no bridge, pack builder, row implementation or runtime authority.",
        proposal=proposal_pin, freeze=freeze_pin, semantic_sha256=semantic_sha, basis=basis,
        recorder=pin(Path(__file__).name),
        material_findings=[
            dict(id="footer_per_row_budget", location="semantic_contract.wire_size.footer_pool / JSONL_buckets.footer",
                 problem="Proposal permits one65536-byte failureJSONL row by pooling8units, but frozen profile reserves16actualfooterROWS each<=8192. Aggregate fit does not satisfy the per-row constraint.",
                 required="FailureJSONL<=8192 includingLF; keep separate failureFILE<=65536 and16actualfooter rows each<=8192. Do not relabel rows as byteunits."),
            dict(id="closed_stage_schemas_and_deltas", location="semantic_contract.event_order.setup_bodies / API_accounting.stage_schedule",
                 problem="Existing typed payloads and exact source-derived setup counter deltas are deferred to a future implementation, so the proposed closed wire cannot yet determine setup row bodies/accounting at literal framing freeze.",
                 required="Embed exact closed per-stage body schemas, finite observation enums and cumulative25API/state transition vectors before fixtures. Monotonic/global ceilings alone are insufficient."),
            dict(id="geometry_QC_vs_native_observation", location="semantic_contract.case_row.observation / ledger / compact_analysis",
                 problem="Mixed observed EOG results force QCunknown and nullledger/counts even when token-piece geometry is fully valid. This couples geometry/population completeness to measured grammar behavior, unlike accepted analyzer537a.",
                 required="Retain valid ledger/geometry QC/counts. Report native_EOG_disagreement/native_memberNull/matchesNull separately, making profile negative while preserving known geometry. Unknown native ownership/nonreturn still stops unsafe work.")],
        clarifications=[
            dict(id="sizing_field_maximum", measured_template_excluding_arrays=measured, false_member_variant=false_measured,
                 effect="Nonblocking within8192, but6407is exacttemplate size rather than strictfieldmax; use longest valid type/finite enum and label mathematical envelope, not trace."),
            dict(id="null_API_name_sentinel", location="semantic_contract.framing.native_state_fields.last_attempt / last_return",
                 requirement="Represent actualJSONnull, not literalstringnull, in the finite API-name/null grammar before fixtures.")],
        checked_arithmetic=dict(profile_counts=counts, eligible_bytes=eligible_bytes, largest_document=largest,
            document_token_cap_sum=document_tokens, unique_prefix_token_upper=prefix_tokens, total_token_work_upper=token_work,
            sampler_upper=82, tokenize_upper=156, piece_upper=124520, apply_upper=74356,
            hard_API_caps_sum=4276181, positive_upper_sum=530477, case_row_maximum=60864,
            actual_largest_case_bound=30060, reserved_JSONL_bytes=reserved, fixed84_JSONL_bytes=fixed84,
            all_artifact_bytes=8065024, pack_fixed_header_bytes=188),
        otherwise_consistent=["84full cases/78native/6harness/68fixedpopulation, fourstages/twogrammars and independent expectation dimensions",
            "Full tokenID/length/hex arrays, preservedzero ordinals, wholecorpus first-case/token selection and de-dup<=4",
            "Unknown versus knownzero, selected originaltoken prefix with no re-tokenization and failed mismatch retention",
            "Existing25API/45state and117/120/300s/256MiB/token/pack/row ceilings; no time/memory fit established",
            "Acyclic source authority and immutable captured-context intent; new Unicode journal/resource/core gates remain future work"],
        activity=dict(new_design_and_metadata_only=True, old_original_source_qualification_or_hashes=0,
                      CPU_GGUF_oldpack_reads=0, native_model_SDK_compiler_OS_calls=0,
                      actual_new_profile_pack_or_bridge_or_parent_implementation=False),
        execution_authorized=False, current_or_future_profile_qualified=False,
        old_negative_and_external_timeout_unchanged=True)
    raw = (json.dumps(record, indent=2, allow_nan=False)+"\n").encode("utf-8")
    path = HERE / "UNICODE-WIRE-INDEPENDENT-DESIGN-REVIEW-v1.json"
    with path.open("xb") as stream: stream.write(raw)
    print(json.dumps(pin(path)))


if __name__ == "__main__":
    main()
