"""Retain independent new-component source/pure evidence; no old payload I/O."""
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
import unittest

HERE = Path(__file__).parent


def pin(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path.absolute()), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    expected = {
        "unicode_piece_analyzer_v1.py": "537a780a3d2d3b95d5fe4976cd8a073cf528db908badf3edf3e861e729ff8f9d",
        "check_unicode_piece_analyzer_v1.py": "908e9be5d299e59dc4eb811c927cd8487815d4bc54a93388db963da2e042018b",
        "UNICODE-PIECE-ANALYZER-PURE-PROOF-v1.json": "34c7886a52b81f15c81df971222677682cbe0054d45f5e15f5e0b553e451ca54",
        "UNICODE-PIECE-ANALYZER-CONTRACT-v1.json": "05c214f42e9214691b5675cca58e67a6265dd069d2e7829f604df23c7ccca3e6",
        "UNICODE-PIECE-ANALYZER-VECTORS-v1.json": "150a6f0597c226f9aaddcb3f6a3506e9a0513a5cdd2f7da839b25cf56c0f9a79",
        "UNICODE-PIECE-ANALYZER-FREEZE-v1.json": "125d1474ed8498e7dd5bf00f7209fa36660d1326634e0e257b0b2c82f9578a10",
    }
    pins = {name: pin(HERE / name) for name in expected}
    assert all(pins[name]["sha256"] == expected[name] for name in expected)
    freeze = json.loads((HERE / "UNICODE-PIECE-ANALYZER-FREEZE-v1.json").read_text(encoding="utf-8"))
    assert freeze["contract"]["sha256"] == expected["UNICODE-PIECE-ANALYZER-CONTRACT-v1.json"]
    assert freeze["vectors"]["sha256"] == expected["UNICODE-PIECE-ANALYZER-VECTORS-v1.json"]
    checker_path = HERE / "check_unicode_piece_analyzer_peer_v1.py"
    spec = importlib.util.spec_from_file_location("analyzer_independent_probes", checker_path)
    checker = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = checker
    spec.loader.exec_module(checker)
    output = io.StringIO(); started = time.monotonic()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(checker.PeerChecks))
    elapsed = time.monotonic() - started
    assert result.wasSuccessful() and result.testsRun == 8
    record = dict(schema_version=1, recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status="CLEAR_SOURCE_PURE_COMPONENT_ONLY_NOT_TOKENIZER_OR_RUNTIME_QUALIFICATION",
        reviewer="Independent os_accounting_peer; analyzer author/root source left unchanged",
        artifacts=pins, independent_checker=pin(checker_path), recorder=pin(__file__),
        oracle_dependency=pin(checker.ORACLE), methods=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        elapsed_seconds=elapsed, test_output=output.getvalue(),
        independently_exercised=dict(frozen_literal_vectors=15, exhaustive_piece_partitions=272,
                                    authored_scalar_sequences=4, width_matrix_cells=12,
                                    selector_population_unknown_immutability_probes=True),
        source_findings=[
            "Whole-document strict scalar intervals precede piece analysis; a piece is never independently decoded or repaired.",
            "Nonempty strict-inside-scalar boundary excludes zeros/document end; bisect start excludes carried-in scalar witnesses.",
            "Mixed geometry uses wholly-contained intervals before pending scalar; earliest witness per distinct complete width and one matrix increment per width match contract.",
            "Population is source flags only. Unknown population preserves lower bounds but suppresses all complete totals/selectors; excluded unknown remains visible in all_case_QC_complete.",
            "Contiguous source case order and original token ordinals determine first selections; allocation uses width2/3/4/mixed priority and de-duplicates case/token identity.",
            "Mapping proxies/tuples and fresh to_dict containers preserve ordinary deep immutability; inputs are not mutated."],
        material_blockers=[],
        limitations=[
            "Supplied token labels/pieces are synthetic; no tokenizer, vocabulary or model-to-piece mapping was authenticated.",
            "The author's84full-document one-byte-piece scenario is retained author evidence, not independently rerun here and not native tokenization.",
            "coverage_complete/required_available are geometry flags only. An excluded unknown may coexist with required_availableTrue while all_case_QC_completeFalse; future profile gating must preserve that distinction.",
            "No native row-fit, whole-process memory/time, full vocabulary mask, grammar/native profile acceptance or scientific claim follows.",
            "Source/contract/dependency binding is a caller/future integration requirement; this component does not authenticate source or hostile Python."],
        activity=dict(frozen_author_source_edits=0, old_profile_or_original_payload_operations=0,
                      CPU_GGUF_pack_model_reads=0, SDK_native_tokenizer_compiler_dispatches=0,
                      new_pure_modules_imported_and_analyze_called=True),
        old_negative_and_timeout_unchanged=True)
    raw = (json.dumps(record, indent=2, allow_nan=False) + "\n").encode("utf-8")
    out = HERE / "UNICODE-PIECE-ANALYZER-INDEPENDENT-PEER-v1.json"
    with out.open("xb") as stream: stream.write(raw)
    print(json.dumps(pin(out)))


if __name__ == "__main__":
    main()
