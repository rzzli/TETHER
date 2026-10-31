"""Author two narrow FICTIONAL source branches; no observation validator.

V1 is immutable. This writes a separately frozen successor container, retaining
all prior literal histories/scenarios unchanged and adding two full negatives.
Only new review metadata/pure modules are consumed. New pack bytes stay in RAM.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import time
import types

HERE=Path(__file__).resolve().parent
REVIEW=HERE.parent
CONTROL=REVIEW/"recovery-step9-unicode-control-20261029"
WIRE=REVIEW/"recovery-step9-unicode-wire-20261029"
CODEC=REVIEW/"recovery-step9-unicode-codec-20261029"
ORACLE=REVIEW/"recovery-step9-utf8-oracle-20261029"
TARGET=HERE/"UNICODE-OBSERVATIONS-TRACE-FIXTURES-v2.json"
FREEZE=HERE/"UNICODE-OBSERVATIONS-TRACE-FREEZE-v2.json"
STARTED=time.monotonic()


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")


def sha(raw): return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw=path.read_bytes(); return dict(path=str(path),bytes=len(raw),sha256=sha(raw))


def budget():
    if time.monotonic()-STARTED>20: raise TimeoutError("Fictional supplement author20s")


def load(path,expected,name):
    raw=path.read_bytes(); assert sha(raw)==expected
    module=types.ModuleType(name); module.__file__=str(path); sys.modules[name]=module
    exec(compile(raw,str(path),"exec"),module.__dict__)
    return module


def all_cases_nonpopulation_unknown(author):
    """Same authored V1 bookkeeping; ONLY ordinal68 has known tokenize0/QCunknown."""
    for index,(case,source,pieces,geometry,ledger) in enumerate(zip(author.profile.cases,author.source,author.pieces,author.geometries,author.ledgers)):
        author.book.state["current_case_index"]=index
        reference=author.case_reference(index)
        author.emit("unicode_before_case",dict(reference,declared_native_byte_eligible=case.native_byte_eligible))
        expected=source["expected"]
        authored=dict(native_member=expected["native_membership"],generation_member=expected["generation_grammar_membership"],
            semantic_eligible=expected["complete_v3_semantic_validation"],coverage_population=source["coverage_population"])
        if not case.native_byte_eligible:
            status="harness_raw_nul_rejection" if case.harness_kind==2 else "harness_utf8_rejection"
            qc=dict(status="harness_ineligible",reason=status); observation=author.empty_observation(status)
            compact=dict(counts=None,matrix=None,zero_piece_count=None); matches=None
        elif index==68:
            assert not source["coverage_population"]
            author.book.call("llama_tokenize",2,0)
            qc=dict(status="unknown",reason="tokenize_size_invalid")
            observation=author.empty_observation("not_attempted_QC_unknown")
            compact=dict(counts=None,matrix=None,zero_piece_count=None); matches=None
        else:
            author.book.tokenize_and_pieces(pieces)
            member=expected["native_membership"]
            rejected=author.book.grammar(len(pieces),member)
            if rejected is not None:
                start=sum(len(p) for p in pieces[:rejected]); end=start+len(pieces[rejected])
                observation=dict(status="native_token_rejection",native_member=False,all_input_tokens_admitted=False,
                    first_rejected_token_index=rejected,first_rejected_byte_start=start,first_rejected_byte_end=end,completion_EOG=None)
            else:
                observation=dict(status="native_member" if member else "native_eog_rejection",native_member=bool(member),
                    all_input_tokens_admitted=True,first_rejected_token_index=None,first_rejected_byte_start=None,
                    first_rejected_byte_end=None,completion_EOG=[dict(id=t,admitted=bool(member)) for t in author.context["EOG_ids"]])
            qc=dict(status="ok",reason=None)
            compact={key:copy.deepcopy(geometry[key]) for key in ("counts","matrix","zero_piece_count")}
            matches=observation["native_member"] is member
        state=author.book.state; stratum=author.strata.index(source["stratum"])
        state["cases_computed"]+=1; state["stratum_computed"][stratum]+=1
        author.emit("unicode_case_result",dict(reference,authored_expected=authored,QC=qc,observation=observation,
            ledger=ledger,compact_analysis=compact,matches_authored_native_expectation=matches))
        state["case_results_written"]+=1; state["stratum_results_written"][stratum]+=1


def reframe(base,rows):
    answer=copy.deepcopy(base); lines=[canonical(row)+b"\n" for row in rows]; raw=b"".join(lines)
    answer.update(raw_hex=raw.hex(),bytes=len(raw),sha256=sha(raw),row_count=len(lines),
        row_offsets=[sum(map(len,lines[:i])) for i in range(len(lines))])
    return answer


def main():
    assert not TARGET.exists() and not FREEZE.exists()
    paths={"v1_fixtures":HERE/"UNICODE-OBSERVATIONS-TRACE-FIXTURES-v1.json",
        "v1_freeze":HERE/"UNICODE-OBSERVATIONS-TRACE-FREEZE-v1.json",
        "v1_encoding_proof":HERE/"UNICODE-OBSERVATIONS-TRACE-ENCODING-PROOF-v1.json",
        "v1_peer":HERE/"UNICODE-OBSERVATIONS-TRACE-INDEPENDENT-PEER-v1.json",
        "scope":HERE/"UNICODE-OBSERVATIONS-ROOT-SUPPLEMENTAL-TRACE-SCOPE-v1.json"}
    expected={"v1_fixtures":"113bdf35742cf0be7eeae760dba966220ed0941d61de6254c89d3c7371b86ef1",
        "v1_freeze":"64e07cf33268334b13d742fac9860211fdb2faf7a7e996e5d176b1cbf7708a41",
        "v1_encoding_proof":"64c1b9139faa55edbdb79ec4f628dba8969a66fc29d989360af594c0fde753d9",
        "v1_peer":"a22e3d7010978f25d16a9c549134a6866336617b5d99c83721cca19bac164804",
        "scope":"013fb851f2da521e04659d32688fd46b88a8649d4c156efdcf4f6f2fa7796a51"}
    for key,path in paths.items(): assert pin(path)["sha256"]==expected[key]
    prior=json.loads(paths["v1_fixtures"].read_bytes()); fixture=copy.deepcopy(prior)
    old=load(HERE/"author_unicode_observation_traces_v1.py","103e016b226e27afc627d8f1c5da2c443173fafc00381e06f35e83b65b18567d","frozen_v1_fictional_author")
    context=json.loads(old.CONTEXT.read_bytes())
    corpus_path=CONTROL/"UNICODE-CONTROL-CORPUS-v1.json"; corpus=json.loads(corpus_path.read_bytes())["cases"]
    semantics=json.loads((WIRE/"UNICODE-WIRE-DESIGN-CONTRACT-v2.json").read_bytes())["semantic_contract"]
    positive=prior["base_traces"][0]; conflict=prior["base_traces"][2]
    # Exact mixed EOG closure: first true, last false. Last-call shape/counters are
    # identical to the existing allfalse conflict; no following state changes.
    mixed_rows=[json.loads(line) for line in bytes.fromhex(conflict["raw_hex"]).split(b"\n")[:-1]]
    mixed_body=mixed_rows[24]["body"]
    assert mixed_body["case_ordinal"]==4 and mixed_body["observation"]["status"]=="native_eog_rejection"
    mixed_body["observation"].update(status="native_EOG_disagreement",native_member=None,
        completion_EOG=[dict(id=1022,admitted=True),dict(id=1023,admitted=False)])
    mixed_body["matches_authored_native_expectation"]=None
    mixed=reframe(conflict,mixed_rows); mixed["id"]="complete_mixed_EOG_unknown_membership"
    mixed["expected_projection"].update(known_membership_outcomes=77,all_expected_membership_outcomes_match=None)
    mixed["branch_scope"]="Root-confirmed missing coherent EOG union; QCok,all78 full geometries,known population. No native experiment."
    # Nonpopulation QCunknown is a supplemental branch, not a new peer defect.
    old.load(ORACLE/"strict_utf8_oracle_v1.py","4e5d36afa001339735a349a8ebab88a312cde1cb57fa43336e38ee4195134c21","strict_utf8_oracle_v1")
    analyzer=old.load(CONTROL/"unicode_piece_analyzer_v1.py","537a780a3d2d3b95d5fe4976cd8a073cf528db908badf3edf3e861e729ff8f9d","supplement_analyzer")
    codec=old.load(CODEC/"unicode_pack_codec_v2.py","8ff0d6228fbec2900d52125f2e94e311cc22762d2d0b8b52c3eaadf0e59be91a","supplement_codec")
    source_paths=dict(base_design=WIRE/"UNICODE-WIRE-DESIGN-CONTRACT-v2.json",framing_contract=WIRE/"UNICODE-WIRE-FRAMING-CONTRACT-v1.json",
        corpus=corpus_path,stages=CONTROL/"UNICODE-CONTROL-STAGES-v1.json",profile_contract=CONTROL/"UNICODE-CONTROL-CONTRACT-v2.json",
        analyzer_contract=CONTROL/"UNICODE-PIECE-ANALYZER-CONTRACT-v1.json")
    profile=codec.make_profile(codec.SourceBytes(**{key:path.read_bytes() for key,path in source_paths.items()}),check=budget)
    encoded=codec.encode(profile,check=budget)
    assert len(encoded)==37766 and sha(encoded)==context["expected_newpack_sha256"]
    author=old.TraceAuthor(semantics,context,corpus,profile,sha(encoded))
    assert corpus[68]["id"]=="negative/unknown_quote" and not corpus[68]["coverage_population"]
    author.geometries[68]=None; author.ledgers[68]=None
    author.summary=old.authored_summary(corpus,author.geometries); author.strata=old.STRATA
    analyzer_cases=tuple(dict(id=case.id,ordinal=case.ordinal,raw_bytes=case.raw,native_byte_eligible=case.native_byte_eligible,
        generation_member=src["expected"]["generation_grammar_membership"] is True,
        semantic_eligible=src["expected"]["complete_v3_semantic_validation"] is True) for case,src in zip(profile.cases,corpus))
    ledgers=tuple(None if ledger is None else {key:tuple(value) for key,value in ledger.items()} for ledger in author.ledgers)
    corroboration=analyzer.analyze(analyzer_cases,ledgers,1024,(1022,1023)).to_dict()
    for key,value in author.summary.items(): assert corroboration[key]==value,(key,value,corroboration[key])
    assert author.summary["coverage_complete"] is True and author.summary["all_case_QC_complete"] is False
    for key in ("counts","matrix","selectors","selected_prefixes","required_available"):
        assert author.summary[key]==positive["authored_geometry_summary"][key]
    author.setup(); all_cases_nonpopulation_unknown(author); author.coverage(); author.fail("document_QC_unknown")
    nonpop=author.capture("complete_nonpopulation_QC_unknown","complete_negative_consistent")
    nonpop["expected_projection"].update(validated_native_geometry_rows=77,known_membership_outcomes=77,
        unique_selected_prefix_results=0,all_expected_membership_outcomes_match=None)
    nonpop["branch_scope"]="Explicit supplemental nonpopulation QCunknown; fixed population68/counts/selectors/availability known; whole all_case_QCfalse."
    fixture["base_traces"].extend([mixed,nonpop])
    # Existing coherent rejection is referenced, not duplicated. Literal formula
    # expectations are authored independently of any observation validator.
    positive_rows=[json.loads(line) for line in bytes.fromhex(positive["raw_hex"]).split(b"\n")[:-1]]
    before,result=positive_rows[151:153]; body=result["body"]
    assert body["case_ordinal"]==68 and body["case_id"]=="negative/unknown_quote"
    n=227; r=226; start=225; end=226
    assert len(body["ledger"]["token_ids"])==n
    assert body["observation"]==dict(status="native_token_rejection",native_member=False,all_input_tokens_admitted=False,
        first_rejected_token_index=r,first_rejected_byte_start=start,first_rejected_byte_end=end,completion_EOG=None)
    delta={name:0 for name in semantics["API_accounting"]["names"]}
    delta.update(llama_tokenize=2,llama_token_to_piece=227,llama_sampler_init_grammar=1,llama_sampler_free=1,
        llama_sampler_apply=r+1,llama_sampler_accept=r)
    for name,value in delta.items():
        for outcome in ("attempted","returned"):
            assert result["native_call_counters"][name][outcome]-before["native_call_counters"][name][outcome]==value
    assert result["native_state"]["token_work_reserved"]-before["native_state"]["token_work_reserved"]==n
    assert sum(body["ledger"]["piece_byte_lengths"][:r])==start
    assert start+body["ledger"]["piece_byte_lengths"][r]==end
    fixture["supplemental_branch_references"]=[dict(id="existing_coherent_native_token_rejection",kind="reference_existing_literal_not_duplicate",
        base_trace=positive["id"],base_sha256=positive["sha256"],before_row=151,result_row=152,case_ordinal=68,case_id=body["case_id"],
        expected=dict(N=n,rejected_token_index=r,first_rejected_interval=[start,end],full_ledger_retained=True,
            QC="ok",native_member=False,matches_authored_native_expectation=True,geometry_retained=True,
            native_call_delta_each_attempted_returned=delta,token_work_delta=n),
        also_covered_ordinals=[69,70,72,73,74,75,76,77])]
    fixture["status"]="FROZEN_FICTIONAL_FULL_SOURCE_TRACES_V2_BEFORE_OBSERVATION_VALIDATOR"
    fixture["v2_delta"]=dict(prior_inputs={key:pin(path) for key,path in paths.items()},
        prior_v1_bases_unchanged=True,prior36scenarios_unchanged=True,prior11callback_vectors_unchanged=True,
        added_base_ids=[mixed["id"],nonpop["id"]],expected_classifications="Independently authored before observation validator implementation",
        source_case_population_body_changes=False,observation_validator_implemented=False)
    for base in (mixed,nonpop):
        assert base["row_count"]==185
        for name,c in base["authored_final_counters"].items(): assert c["attempted"]==c["returned"]<=semantics["API_accounting"]["hard_caps"][name]
    budget()
    TARGET.write_bytes(canonical(fixture)+b"\n")
    freeze=dict(schema_version=2,status="narrow_fictional_branch_successor_frozen_before_validator_code",fixture=pin(TARGET),
        author=pin(Path(__file__).resolve()),prior_v1_inputs={key:pin(path) for key,path in paths.items()},
        prior_author=pin(HERE/"author_unicode_observation_traces_v1.py"),base_traces=6,scenarios=36,callback_families=11,
        existing_token_rejection_reference=True,added_coherent_branches=2,pack_file_created=False,observation_validator_implemented=False,
        native_payload_SDK_operations=0,profile_qualified=False,elapsed_seconds=time.monotonic()-STARTED)
    FREEZE.write_bytes(canonical(freeze)+b"\n")
    print(json.dumps(dict(fixtures=pin(TARGET),freeze=pin(FREEZE),base_traces=6,scenarios=36)))


if __name__=="__main__": main()
