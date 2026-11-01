# Manuscript content audit v1

Status: CHANGES_REQUESTED. Quantitative metadata comparison: PASS. Scientific validation remains not established.

Reviewed manuscript SHA256 `7d2abe8fa389c0eeab365160bbca8bfd6e76c67b176cdb31049094f694defc27`; supplement SHA256 `24646d961713192633629041366ba5525e0e45a3a86e72890366fbafddc0251e`. The JSON retains all supporting metadata byte hashes. No manuscript/results edits, raw source/reference values, protected material, model calls or network operations were used.

## MCA-01 (P2): Specify reproducible hash selection and no replacement

Locations: paper/manuscript.md:47, paper/supplement.md:53.

Identity-only ranking is described, but the seed, release inclusion, hash encoding/tie order and no-replacement treatment of selected missing/conflicting/blocked records are not explicit.

Requested change: State SHA256 of UTF-8 pipe-separated seed preprint-p05-deterministic-v1, release, targetId, diseaseId, studyLocusId; eligible unique units sort by unit_hash,target_id,disease_id,study_locus_id,release_id. Retain all fixed selected units without reranking or replacement for missingness, conflicts, blocking or candidate performance.

## MCA-02 (P2): Distinguish exact answered status from partial completion

Locations: paper/manuscript.md:67, paper/supplement.md:67.

Completion correctly permits answered/partial reports. The exactness definition says every fact and correct unknown reasons but does not explicitly require status answered and every slot exactly once.

Requested change: State that strict exact verification additionally requires answer_status answered, every requested slot exactly once, no critical error, and exact values/bindings/unknown reasons. A partial report cannot be exact even if its populated-value coverage reaches the threshold.

## MCA-03 (P3): Make the permitted parent boundary explicit

Locations: paper/manuscript.md:55, paper/supplement.md:59.

Separate source rereads and excluded answer-aware derivatives are described; the exact original-only value-parent rule and quarantine restriction are implicit.

Requested change: Clarify that value parents are approved original payloads/receipts plus validated neutral Task/Snapshot/case-plan/routing/config. Registry captures, mapping/coverage audits, SQL values, old candidate/gold/P02 selected-join descendants and evaluator registers cannot become generation/reference value parents. Distinguish neutral configuration from source-valued InputGraph parents.

## Checked quantities and boundaries

- source_inventory: 137 originals; 100 GWAS,25 credible,10 target,1 disease,1 HGNC; 2866248239 bytes; table row totals match retained audit metadata.
- selection: 1753850 GWAS rows =1681738 eligible +72112 excluded; overlapping reasons are not additive;12 fixed units,9 development symbols excluded.
- source_binding: 2862043 credible rows; one exact locus match per selected unit;24 selected source rows;180 bound requested slots.
- availability: 132 identity slots:108 populated24 null;48 measurement slots:40 populated8 null;148 populated32 null total.
- measurement_groups: 12 native answerable groups; answerable components 3,3,4,4,4,3,3,2,4,3,3,4; histogram2:1,3:6,4:5.
- missing_context: native beta null1,standardError null7,sampleSize unavailable10; sampleSize not a requested measurement.
- native_results: literal12/12 exact and12/12 completion at60,80,100 percent; abstain0/12 with0 emitted assertions and0 mismatch errors; literal180 entries includes32 unknowns.
- schedules: 38 outputs=24 native+14 constructed;90 decisions=48 native+42 constructed;36 normalized returned2 malformed;57 admitted33 rejected.
- constructed_admission: four valid and ten invalid; invalid admissions FULL0/10,WITHOUT_WRAPPER2/10,WIRE_ONLY7/10;valid rejections0/4 each.
- paired_discordance: constructed FULL-v-WITHOUT2/14,FULL-v-WIRE7/14,WITHOUT-v-WIRE5/14; paired logical policies on same bytes.
- secondary_denominator: 35 core-scored outputs; all-output denominators retained separately; zero-answerable group coverage undefined.
- producer_resources: 203.828s wall,198.984375s CPU,305827840B process peak;197.812s shared wrapper included, not added again;140452303784 logical source-hash bytes.
- audit_resources: 7.125s wall,7.046875s CPU,333893632B peak;2897268566 logical bytes; combined143349572350; physical I/O/platform cost unmeasured.
- P04_negative_probe: 12 scheduled cells;5 actual calls;4 malformed1 output-limit failure;0 strict success;13582 input5726 output tokens;424.516s; two earlier zero-call setup attempts retained.
- P04b_negative_probe: 2 calls;two-field control passes,eight-field malformed;1/2 observed control pass and both gate-closed;2501 input1881 output tokens;38.563s;no retry/scaling/native-model study.
- audit_and_presentation: source audit2414 checks; presentation351 checks;11 CSV392 rows,11 Markdown316 rows,3 figure-data/caption/vector sets;39 rebuild files including manifest.
- exact_hash_table: all seven presented exact-byte SHA256 values match named frozen artifacts, including READY49c2ce672356bfcfd572a7b6c963c56bd5c96e3d042a9972f2c36434ebb8de3f.

The current texts already resolve the emitted-entry label, locus-only/variant boundary, and C02 generic-JSON versus native-Parquet boundary. Negative generator probes remain conditional development evidence; no model ranking, clinical validity, causality, provider authenticity, independent-study inference or public-release readiness is established.
