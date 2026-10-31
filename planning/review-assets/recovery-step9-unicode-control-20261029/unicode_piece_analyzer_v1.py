"""Pure geometry of supplied token pieces, not tokenization or native validation.

Implements frozen contract 05c214f4... against literal independent vectors.
The scalar oracle is a separately accepted pure dependency. No filesystem,
vocabulary, native operation or observed membership is part of this API.
"""
from bisect import bisect_left
from dataclasses import dataclass
from types import MappingProxyType
from strict_utf8_oracle_v1 import StrictUtf8Oracle

CLASSES = ("pending_width2", "pending_width3", "pending_width4",
           "same_piece_complete_scalar_then_pending")
CASE_KEYS = {"id", "ordinal", "raw_bytes", "native_byte_eligible",
             "generation_member", "semantic_eligible"}
LEDGER_KEYS = {"token_ids", "piece_byte_lengths", "piece_hex"}
FLAGS = ("native_byte_eligible", "generation_member", "semantic_eligible")
HEX = frozenset("0123456789abcdef")


def _require(value, reason):
    if not value:
        raise ValueError(reason)


def _freeze(value):
    if type(value) is dict:
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) in (tuple, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value):
    if type(value) is MappingProxyType:
        return {key: _thaw(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class Analysis:
    _data: object

    def to_dict(self):
        return _thaw(self._data)


def _counts():
    return dict.fromkeys(CLASSES, 0)


def _matrix():
    return [[0, 0, 0] for _ in range(4)]


def _validate_inputs(cases, ledgers, vocabulary_size, eog_ids):
    _require(type(vocabulary_size) is int and 1 <= vocabulary_size <= 262144,
             "vocabulary_size")
    _require(type(eog_ids) is tuple and 1 <= len(eog_ids) <= 64, "eog_ids")
    _require(all(type(value) is int and 0 <= value < vocabulary_size for value in eog_ids),
             "eog_ids")
    _require(eog_ids == tuple(sorted(set(eog_ids))), "eog_ids")
    _require(type(cases) is tuple and 1 <= len(cases) <= 96, "cases")
    _require(type(ledgers) is tuple and len(ledgers) == len(cases), "ledgers")
    identities = set()
    for index, case in enumerate(cases):
        _require(type(case) is dict and set(case) == CASE_KEYS and
                 all(type(key) is str for key in case), "case_schema")
        _require(type(case["ordinal"]) is int and case["ordinal"] == index, "case_order")
        identity = case["id"]
        _require(type(identity) is str and 1 <= len(identity) <= 128 and
                 all(not 0xD800 <= ord(c) <= 0xDFFF for c in identity), "case_id")
        _require(identity not in identities, "case_id")
        identities.add(identity)
        _require(type(case["raw_bytes"]) is bytes and 1 <= len(case["raw_bytes"]) <= 1024,
                 "raw_bytes")
        _require(all(type(case[key]) is bool for key in FLAGS), "case_flags")


def _raw_intervals(raw):
    # Whole-document validation is essential: individual pieces may end in the
    # middle of a scalar. They must never be decoded/repaired independently.
    _require(b"\0" not in raw, "raw_NUL")
    state = StrictUtf8Oracle().feed(raw, final=True)
    _require(state.status == "finished", "raw_utf8")
    intervals, pending, position = [], {}, 0
    for scalar in state.decoded_scalars:
        width = 1 if scalar <= 0x7F else 2 if scalar <= 0x7FF else 3 if scalar <= 0xFFFF else 4
        interval = (position, position + width, width)
        intervals.append(interval)
        for cut in range(position + 1, position + width):
            pending[cut] = interval
        position += width
    _require(position == len(raw), "raw_utf8")
    return intervals, pending


def _geometry(raw, ledger, vocabulary_size, eog_ids):
    intervals, pending = _raw_intervals(raw)
    _require(type(ledger) is dict and set(ledger) == LEDGER_KEYS and
             all(type(key) is str for key in ledger), "ledger_schema")
    _require(all(type(ledger[key]) is tuple for key in LEDGER_KEYS), "ledger_arrays")
    ids, lengths, spellings = (ledger[key] for key in
                               ("token_ids", "piece_byte_lengths", "piece_hex"))
    size, n = len(raw), len(ids)
    _require(n == len(lengths) == len(spellings), "ledger_lengths")
    _require(n <= min(65536, 4 * size + 32), "token_cap")
    _require(all(type(value) is int and 0 <= value < vocabulary_size for value in ids), "token_id")
    _require(not any(value in eog_ids for value in ids), "ordinary_EOG")
    _require(all(type(value) is int and 0 <= value <= size for value in lengths), "piece_length")
    _require(sum(lengths) == size, "roundtrip")
    pieces = []
    for length, spelling in zip(lengths, spellings):
        _require(type(spelling) is str and len(spelling) == 2 * length and
                 all(c in HEX for c in spelling), "piece_hex")
        pieces.append(bytes.fromhex(spelling))
    _require(b"".join(pieces) == raw, "roundtrip")

    counts, matrix, boundaries = _counts(), _matrix(), []
    starts = [interval[0] for interval in intervals]
    start = 0
    for index, length in enumerate(lengths):
        end = start + length
        row = {"token_ordinal": index, "start": start, "end": end,
               "pending_start": None, "pending_end": None, "complete_widths": [],
               "witnesses": [], "classes": []}
        interval = pending.get(end) if length and end < size else None
        if interval is not None:
            scalar_start, scalar_end, width = interval
            category = CLASSES[width - 2]
            row.update(pending_start=scalar_start, pending_end=scalar_end,
                       classes=[category])
            counts[category] += 1
            # Pieces occupy disjoint byte intervals. Only intervals wholly
            # inside this piece can be witnesses; no carried scalar qualifies.
            witness_by_width = {}
            cursor = bisect_left(starts, start)
            while cursor < len(intervals) and intervals[cursor][1] <= scalar_start:
                left, right, complete_width = intervals[cursor]
                witness_by_width.setdefault(complete_width, [complete_width, left, right])
                cursor += 1
            if witness_by_width:
                row["classes"].append(CLASSES[3])
                counts[CLASSES[3]] += 1
                row["complete_widths"] = sorted(witness_by_width)
                row["witnesses"] = [witness_by_width[w] for w in row["complete_widths"]]
                for complete_width in row["complete_widths"]:
                    matrix[complete_width - 1][width - 2] += 1
        boundaries.append(row)
        start = end
    return boundaries, counts, matrix, lengths.count(0)


def _case_result(case, ledger, vocabulary_size, eog_ids):
    population = all(case[key] for key in FLAGS)
    row = {"id": case["id"], "ordinal": case["ordinal"], "population": population,
           "qc_status": "unknown", "qc_reason": None, "zero_piece_count": None,
           "boundaries": None, "counts": None, "matrix": None}
    if not case["native_byte_eligible"]:
        row["qc_status"] = "harness_ineligible" if ledger is None else "unknown"
        row["qc_reason"] = "harness_declared" if ledger is None else "harness_ledger_present"
    elif ledger is None:
        row["qc_reason"] = "missing_ledger"
    else:
        try:
            boundaries, counts, matrix, zeros = _geometry(case["raw_bytes"], ledger,
                                                         vocabulary_size, eog_ids)
        except ValueError as error:
            row["qc_reason"] = str(error)
        else:
            row.update(qc_status="ok", boundaries=boundaries, counts=counts,
                       matrix=matrix, zero_piece_count=zeros)
    return row


def analyze(cases, ledgers, vocabulary_size, eog_ids):
    """Validate supplied geometry. Completeness/availability never qualify a run."""
    _validate_inputs(cases, ledgers, vocabulary_size, eog_ids)
    rows = [_case_result(case, ledger, vocabulary_size, eog_ids)
            for case, ledger in zip(cases, ledgers)]
    counts, matrix, unknown = _counts(), _matrix(), []
    for row in rows:
        if not row["population"]:
            continue
        if row["qc_status"] != "ok":
            unknown.append(row["ordinal"])
            continue
        for category in CLASSES:
            counts[category] += row["counts"][category]
        for i in range(4):
            for j in range(3):
                matrix[i][j] += row["matrix"][i][j]
    complete = not unknown
    selectors, selected, indexed = None, None, {}
    if complete:
        selectors, selected = {}, []
        for category in CLASSES:
            found = next(((row, boundary) for row in rows if row["population"]
                          for boundary in row["boundaries"] if category in boundary["classes"]), None)
            if found is None:
                selectors[category] = None
                continue
            row, boundary = found
            identity = (row["ordinal"], boundary["token_ordinal"])
            if identity not in indexed:
                indexed[identity] = len(selected)
                selected.append({"case_ordinal": identity[0], "token_ordinal": identity[1],
                                 "take_tokens": identity[1] + 1, "byte_cut": boundary["end"],
                                 "classes": boundary["classes"]})
            selectors[category] = indexed[identity]
    return Analysis(_freeze({
        "cases": rows, "coverage_complete": complete,
        "all_case_QC_complete": all(row["qc_status"] in ("ok", "harness_ineligible") for row in rows),
        "counts": counts if complete else None, "matrix": matrix if complete else None,
        "known_counts_lower_bound": counts, "known_matrix_lower_bound": matrix,
        "unknown_population_ordinals": unknown, "selectors": selectors,
        "selected_prefixes": selected,
        "required_available": all(value > 0 for value in counts.values()) if complete else None,
    }))
