"""Literal synthetic piece geometry/expected results; no analyzer or UTF8 decoder.

Byte lengths, labels, JSON framing and hashes are bookkeeping. Every scalar
interval, class/count/matrix/selector expectation below is supplied literally.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONTRACT = HERE / "UNICODE-PIECE-ANALYZER-CONTRACT-v1.json"
TARGET = HERE / "UNICODE-PIECE-ANALYZER-VECTORS-v1.json"
FREEZE = HERE / "UNICODE-PIECE-ANALYZER-FREEZE-v1.json"
CLASSES = ("pending_width2", "pending_width3", "pending_width4", "same_piece_complete_scalar_then_pending")
P2, P3, P4, MIX = CLASSES


def counts(values=(0, 0, 0, 0)):
    return dict(zip(CLASSES, values))


def matrix(entries=()):
    result = [[0, 0, 0] for _ in range(4)]
    for complete, pending, value in entries:
        result[complete - 1][pending - 2] = value
    return result


def descriptor(identity, ordinal, raw, native=True, generation=True, semantic=True):
    return dict(id=identity, ordinal=ordinal, raw_hex=raw, native_byte_eligible=native,
                generation_member=generation, semantic_eligible=semantic)


def ledger(*pieces, ids=None):
    return dict(token_ids=list(range(1, len(pieces) + 1)) if ids is None else list(ids),
                piece_byte_lengths=[len(bytes.fromhex(piece)) for piece in pieces], piece_hex=list(pieces))


def boundary(token, start, end, pending=None, widths=(), witnesses=(), labels=()):
    return dict(token_ordinal=token, start=start, end=end,
                pending_start=None if pending is None else pending[0], pending_end=None if pending is None else pending[1],
                complete_widths=list(widths), witnesses=[list(item) for item in witnesses], classes=list(labels))


def case_result(identity, ordinal, population=True, qc="ok", reason=None, zero=0, boundaries=(), values=(0, 0, 0, 0), entries=()):
    return dict(id=identity, ordinal=ordinal, population=population, qc_status=qc, qc_reason=reason,
                zero_piece_count=zero if qc == "ok" else None,
                boundaries=list(boundaries) if qc == "ok" else None,
                counts=counts(values) if qc == "ok" else None, matrix=matrix(entries) if qc == "ok" else None)


def selected(case, token, take, cut, labels):
    return dict(case_ordinal=case, token_ordinal=token, take_tokens=take, byte_cut=cut, classes=list(labels))


def result(cases, values=(0, 0, 0, 0), entries=(), refs=(None, None, None, None), selections=(),
           complete=True, all_qc=True, unknown=(), lower=None, lower_entries=None, available=False):
    return dict(cases=cases, coverage_complete=complete, all_case_QC_complete=all_qc,
                counts=counts(values) if complete else None, matrix=matrix(entries) if complete else None,
                known_counts_lower_bound=counts(values if lower is None else lower),
                known_matrix_lower_bound=matrix(entries if lower_entries is None else lower_entries),
                unknown_population_ordinals=list(unknown), selectors=dict(zip(CLASSES, refs)) if complete else None,
                selected_prefixes=list(selections) if complete else None, required_available=available if complete else None)


def main():
    assert not TARGET.exists() and not FREEZE.exists(), "Preserve prior vector/freeze files"
    vectors = []
    def add(identity, purpose, cases, ledgers, expected=None, exception=None, message=None):
        vectors.append(dict(id=identity, purpose=purpose, cases=cases, ledgers=ledgers,
            vocabulary_size=100, eog_ids=[99], expected=expected, expected_exception=exception, exception_message=message))
    def a2(identity="a2", ordinal=0, **flags): return descriptor(identity, ordinal, "41c2a242", **flags)
    def a3(identity="a3", ordinal=0): return descriptor(identity, ordinal, "41e282ac42")
    def r2(identity="a2", ordinal=0, population=True):
        return case_result(identity, ordinal, population=population,
            boundaries=[boundary(0, 0, 2, (1, 3), (1,), ((1, 0, 1),), (P2, MIX)), boundary(1, 2, 4)],
            values=(1, 0, 0, 1), entries=((1, 2, 1),))
    def r3(identity="a3", ordinal=0):
        return case_result(identity, ordinal,
            boundaries=[boundary(0, 0, 2, (1, 4), (1,), ((1, 0, 1),), (P3, MIX)), boundary(1, 2, 5)],
            values=(0, 1, 0, 1), entries=((1, 3, 1),))

    add("all_widths_and_selection_dedup", "Widths2/3/4 and mixed; priority selectors share one boundary without repeated prefix sampling.",
        [a2(), a3(ordinal=1), descriptor("a4", 2, "41f09f988042")],
        [ledger("41c2", "a242"), ledger("41e2", "82ac42"), ledger("41f09f", "988042")],
        result([r2(), r3(ordinal=1), case_result("a4", 2,
            boundaries=[boundary(0, 0, 3, (1, 5), (1,), ((1, 0, 1),), (P4, MIX)), boundary(1, 3, 6)],
            values=(0, 0, 1, 1), entries=((1, 4, 1),))],
            values=(1, 1, 1, 3), entries=((1, 2, 1), (1, 3, 1), (1, 4, 1)), refs=(0, 1, 2, 0),
            selections=[selected(0, 0, 1, 2, (P2, MIX)), selected(1, 0, 1, 2, (P3, MIX)), selected(2, 0, 1, 3, (P4, MIX))], available=True))

    add("carried_scalar_not_wholly_contained", "Completing a scalar begun in the prior piece does not satisfy mixed.",
        [descriptor("carry", 0, "c2a2e282ac")], [ledger("c2", "a2e2", "82ac")],
        result([case_result("carry", 0, boundaries=[boundary(0, 0, 1, (0, 2), labels=(P2,)),
            boundary(1, 1, 3, (2, 5), labels=(P3,)), boundary(2, 3, 5)], values=(1, 1, 0, 0))],
            values=(1, 1, 0, 0), refs=(0, 1, None, None),
            selections=[selected(0, 0, 1, 1, (P2,)), selected(0, 1, 2, 3, (P3,))]))

    add("carry_then_whole_ASCII_then_pending", "A separate complete ASCII scalar within the piece qualifies after a carried scalar.",
        [descriptor("carry_ascii", 0, "c2a241e282ac")], [ledger("c2", "a241e2", "82ac")],
        result([case_result("carry_ascii", 0, boundaries=[boundary(0, 0, 1, (0, 2), labels=(P2,)),
            boundary(1, 1, 4, (3, 6), (1,), ((1, 2, 3),), (P3, MIX)), boundary(2, 4, 6)],
            values=(1, 1, 0, 1), entries=((1, 3, 1),))], values=(1, 1, 0, 1), entries=((1, 3, 1),), refs=(0, 1, None, 1),
            selections=[selected(0, 0, 1, 1, (P2,)), selected(0, 1, 2, 4, (P3, MIX))]))

    add("matrix_distinct_widths_not_scalar_count", "Repeated complete widths count once; one boundary increments multiple matrix rows.",
        [descriptor("repeats", 0, "4142c2a2c2a3e282ac5a")], [ledger("4142c2a2c2a3e2", "82ac5a")],
        result([case_result("repeats", 0, boundaries=[boundary(0, 0, 7, (6, 9), (1, 2), ((1, 0, 1), (2, 2, 4)), (P3, MIX)),
            boundary(1, 7, 10)], values=(0, 1, 0, 1), entries=((1, 3, 1), (2, 3, 1)))],
            values=(0, 1, 0, 1), entries=((1, 3, 1), (2, 3, 1)), refs=(None, 0, None, 0),
            selections=[selected(0, 0, 1, 7, (P3, MIX))]))

    add("zero_pieces_keep_original_token_ordinals", "Empty pieces remain in arrays/counts and prefix take; they are not candidate boundaries.",
        [a2("zero")], [ledger("", "41c2", "", "a242", "")],
        result([case_result("zero", 0, zero=3, boundaries=[boundary(0, 0, 0),
            boundary(1, 0, 2, (1, 3), (1,), ((1, 0, 1),), (P2, MIX)), boundary(2, 2, 2), boundary(3, 2, 4), boundary(4, 4, 4)],
            values=(1, 0, 0, 1), entries=((1, 2, 1),))], values=(1, 0, 0, 1), entries=((1, 2, 1),), refs=(0, None, None, 0),
            selections=[selected(0, 1, 2, 2, (P2, MIX))]))

    add("scan_all_cases_not_first_success_only", "Later eligible boundaries increase counts, while first selection stays the first ordinal.",
        [a2("first"), a2("later", 1)], [ledger("41c2", "a242"), ledger("41c2", "a242")],
        result([r2("first"), r2("later", 1)], values=(2, 0, 0, 2), entries=((1, 2, 2),), refs=(0, None, None, 0),
            selections=[selected(0, 0, 1, 2, (P2, MIX))]))

    add("only_source_flags_define_population", "Generation/semantic/harness exclusions are declarations, not observed membership filters.",
        [a2("generation_excluded", generation=False), a2("semantic_excluded", 1, semantic=False),
         descriptor("harness", 2, "00", False, False, False), descriptor("ASCII_population", 3, "41")],
        [ledger("41c2", "a242"), ledger("41c2", "a242"), None, ledger("41")],
        result([r2("generation_excluded", population=False), r2("semantic_excluded", 1, population=False),
                case_result("harness", 2, population=False, qc="harness_ineligible", reason="harness_declared"),
                case_result("ASCII_population", 3, boundaries=[boundary(0, 0, 1)])]))

    add("unknown_population_blocks_all_selectors", "Known later evidence is only a lower bound when an earlier population ledger is missing.",
        [a2("unknown"), a3("known", 1)], [None, ledger("41e2", "82ac42")],
        result([case_result("unknown", 0, qc="unknown", reason="missing_ledger"), r3("known", 1)],
            complete=False, all_qc=False, unknown=(0,), lower=(0, 1, 0, 1), lower_entries=((1, 3, 1),)))

    add("excluded_QC_unknown_does_not_change_population", "Excluded missing ledger remains QCunknown; coverage contribution is declared zero, overall case QC false.",
        [a2("excluded_unknown", generation=False), a2("known", 1)], [None, ledger("41c2", "a242")],
        result([case_result("excluded_unknown", 0, population=False, qc="unknown", reason="missing_ledger"), r2("known", 1)],
            values=(1, 0, 0, 1), entries=((1, 2, 1),), refs=(0, None, None, 0), all_qc=False,
            selections=[selected(1, 0, 1, 2, (P2, MIX))]))

    add("roundtrip_failure_is_unknown_not_zero", "Missing final byte cannot be normalized into known zero boundary counts.",
        [a2("bad_roundtrip")], [ledger("41c2", "a2")],
        result([case_result("bad_roundtrip", 0, qc="unknown", reason="roundtrip")], complete=False, all_qc=False, unknown=(0,)))

    add("ordinary_EOG_and_bounds_are_QC_failures", "Synthetic EOG/out-of-range labels invalidate eligible ledgers before geometry.",
        [a2("EOG"), a2("out_of_range", 1)], [ledger("41c2", "a242", ids=(99, 1)), ledger("41c2", "a242", ids=(100, 1))],
        result([case_result("EOG", 0, qc="unknown", reason="ordinary_EOG"), case_result("out_of_range", 1, qc="unknown", reason="token_id")],
            complete=False, all_qc=False, unknown=(0, 1)))

    add("shuffled_case_ordinals_rejected", "Do not silently sort caller cases into favorable selector order.",
        [a2("second", 1), a2("first", 0)], [ledger("41c2", "a242"), ledger("41c2", "a242")], exception="ValueError", message="case_order")
    add("duplicate_case_ordinals_rejected", "Duplicate ordinal is a descriptor error, not an ordering fallback.",
        [a2("first", 0), a2("duplicate", 0)], [ledger("41c2", "a242"), ledger("41c2", "a242")], exception="ValueError", message="case_order")
    measured = a2("forged_outcome"); measured["observed_native_membership"] = False
    add("native_outcome_is_not_an_API_input", "Measured success/failure must never become a population selection switch.",
        [measured], [ledger("41c2", "a242")], exception="ValueError")

    add("complete_widths_three_and_four", "Wholly contained three/four-byte scalars are both mixed witnesses before a two-byte pending tail.",
        [descriptor("complete34", 0, "e282acf09f9880c2a2")], [ledger("e282acf09f9880c2", "a2")],
        result([case_result("complete34", 0, boundaries=[boundary(0, 0, 8, (7, 9), (3, 4), ((3, 0, 3), (4, 3, 7)), (P2, MIX)),
            boundary(1, 8, 9)], values=(1, 0, 0, 1), entries=((3, 2, 1), (4, 2, 1)))],
            values=(1, 0, 0, 1), entries=((3, 2, 1), (4, 2, 1)), refs=(0, None, None, 0),
            selections=[selected(0, 0, 1, 8, (P2, MIX))]))

    assert len(vectors) == 15
    data = dict(schema_version=1, profile="synthetic_piece_interval_component_v1", contract_sha256=hashlib.sha256(CONTRACT.read_bytes()).hexdigest(),
        vectors=vectors, synthetic_token_labels_only=True, actual_tokenizer_or_vocabulary_observations=0,
        bounds=dict(maximum_vectors=16, maximum_case_instances=64, maximum_piece_entries=256, maximum_total_supplied_bytes=4096),
        scope="Literal byte-interval/count/witness/selector expectations. Not full v3 language cases, native pack or observed tokenizer outputs; real84case corpus remains independently frozen.")
    raw=(json.dumps(data,sort_keys=True,indent=2)+"\n").encode("utf-8")
    with TARGET.open("xb") as stream: stream.write(raw)
    frozen=dict(schema_version=1,status="frozen_synthetic_piece_API_vectors_before_analyzer_implementation",
        contract=dict(path=str(CONTRACT),bytes=CONTRACT.stat().st_size,sha256=hashlib.sha256(CONTRACT.read_bytes()).hexdigest()),
        vectors=dict(path=str(TARGET),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
        author=dict(path=str(Path(__file__).resolve()),sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
        counts=dict(vectors=len(vectors),case_instances=sum(len(v["cases"]) for v in vectors),
                    supplied_bytes=sum(len(bytes.fromhex(c["raw_hex"])) for v in vectors for c in v["cases"]),
                    piece_entries=sum(len(l["token_ids"]) for v in vectors for l in v["ledgers"] if l is not None)),
        analyzer_implemented=False,native_or_tokenizer_calls=0,CPU_GGUF_oldpack_operations=0,execution_authorized=False)
    assert frozen["counts"]["case_instances"]<=64 and frozen["counts"]["piece_entries"]<=256 and frozen["counts"]["supplied_bytes"]<=4096
    with FREEZE.open("x",encoding="utf-8",newline="\n") as stream:json.dump(frozen,stream,indent=2);stream.write("\n")
    print(json.dumps(dict(status=frozen["status"],counts=frozen["counts"],vectors_sha256=frozen["vectors"]["sha256"],contract_sha256=frozen["contract"]["sha256"])))


if __name__ == "__main__":
    main()
