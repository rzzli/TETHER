# Formal design review: finite generation grammar

28 October 2026 UTC. Review by `grammar_no_compiler_feasibility` against the frozen
[prospective contract](CONTRACT.md). This is pure construction analysis, not native
recognition, model execution, scientific validation or authorization to retry the
failed converter. The old 109 documents and terminal negative result remain intact.

## Acceptance domain and character construction

The proposed serialization restriction preserves decoded answers: compact JSON,
fixed sorted keys, no Unicode normalization, and a value-preserving spelling for
each eligible source-report literal. Free strings may use raw scalar characters,
short JSON escapes, non-surrogate BMP escapes, or a complete high/low surrogate
escape pair. Count that pair as one decoded character. Reject lone/reversed
surrogates. Raw characters exclude C0, quote, backslash, surrogate code points and
`<`; permit DEL, noncharacters, combining marks and the complete scalar range.
Escaped controls remain valid decoded values. Always escape decoded `<`, including
inside known literals; then no runtime `<|...` delimiter can form across atoms.

Partition the logical-character alphabet by the existing explicit 29-character
`str.strip()` set. Whitespace is U+0009–000D, U+001C–0020, U+0085, U+00A0, U+1680,
U+2000–200A, U+2028–2029, U+202F, U+205F and U+3000. U+200B and U+FEFF are nonblank.
Classify escapes by their decoded scalar, including case-insensitive hex digits.
A numeric hex trie/complement avoids enumerating every BMP code point. Short
escapes and surrogate-pair syntax must be partitioned without overlap with BMP
escapes. There is no need to alter the trusted post-validator.

## Joint length/nonblank proof

Let `A`, `W`, `N` mean any, all-whitespace, or contains-nonblank strings. At exact
length `2m`, construct `A=A_m A_m`, `W=W_m W_m`, and
`N=N_m A_m | W_m N_m`. The last alternatives are disjoint according to whether
the first block already contains a nonblank character.

For at most `n`, take its largest power of two `m` and `r=n-m`:

```text
A<=n = A<=m-1 | A_m A<=r
N<=n = N<=m-1 | N_m A<=r | W_m N<=r
```

`A<=0` is epsilon; `N<=0` is the empty language, so omit that branch. Length
ranges and the nonblank partition prove soundness, completeness and unique
whole-word derivation by induction. Memoization shares bounded/exact helpers;
the safe construction bound is logarithmic squared in the maximum length.
Independent exhaustive W/N-language checks for bounds zero through eight find
exact equality and maximum derivation count one. They validate the recurrence,
not its eventual native implementation. Do not use independently optional
half-ranges, or bound a whitespace prefix and suffix separately: those approaches
introduce ambiguity or accept excessive total lengths. Native prefix-stack cost
still needs measurement.

## Reference and object construction

A balanced catalog tree exposes each subtree's IDs and distinct ordered pairs.
For `S=L∪R`, `P(S)=P(L)|P(R)|IDs(L),IDs(R)|IDs(R),IDs(L)`; singleton pair
languages are omitted. Each distinct ordered pair belongs to its unique lowest
common ancestor, establishing coverage without duplicate references or quadratic
enumeration. Preserve both orders. Every ID stays available even if its quote is
too long for a source report. Source-report rules bind the exact safe literal to
its own single ID; share equal literal strings without merging their IDs.

Fixed object productions enforce three states, exact fields, active claim cap,
list lengths, source-report pairing and inference/caution limitations. Generic
nonblank text is bounded at 1,800 characters; reason at 512. Keep global
claim-text uniqueness and raw/canonical response byte limits in post-validation.
Source authority, temporal eligibility and scientific entailment remain outside
grammar. Alternate JSON key orders/spellings remain semantically acceptable to
the unchanged validator; distinguish them from the declared generation domain.

## Provisional size and feasibility

The retained [sizing helper](provisional_sizing.py) and [measurements](PROVISIONAL-SIZING.json)
contain no native execution. The shared 1,800/512 length structure uses 57 rules,
1,557 raw bytes and 1,618 JSON-string bytes. At 256 IDs, reference structure uses
511 rules, 20,731 raw bytes and 26,876 JSON-string bytes. Short unique literals add
4,900 raw bytes in the illustrative catalog. These figures exclude Unicode atoms,
object/list productions, report binding, original prompt and complete HTTP body.
Only the finished builder and canonical payload can establish actual fit.

There is no general all-maxima fit guarantee: 256 independent 1,800-character
ASCII quotes contain 460,800 literal characters before framing; the original
32,768-byte prompt already cannot contain them. The nominal catalog maximum is
conditional on all byte caps. Enforce raw grammar 65,536, original prompt 32,768,
full JSON-escaped HTTP 65,536 and response 256 KiB without truncation. An otherwise
supported retained request failing the new cap is a stop, not permission to prune.
The 1,024 output-token limit also cannot guarantee every long semantic answer.

## Required next evidence and boundaries

Implement only a new pure builder and separately versioned preparation module.
Require deterministic/deeply immutable artifacts, strict IDs/scalars, closure and
acyclicity checks, exhaustive small-language/reference checks, Unicode/escape and
cap boundaries, complete retained-request sizing and unchanged-v2 fingerprints.
Keep original corpus and a separate extension with independent semantic/domain
labels. Native grammar parsing, document completion and actual-vocabulary EOG
remain later gates with a fixed protocol; no pure oracle substitutes for them.
The 295.922/300-second simulated case leaves 4.078 seconds before startup or
inference; profile it prospectively before an actual case. Human reviews remain
pending, but this bounded engineering work can proceed without substituting
agents for independent scientific references.
