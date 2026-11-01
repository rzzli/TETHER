# Resource phases with explicit overlap and unknowns

Do not add producer subphases to the producer total. Shared generation is counted once per native case. Phase-specific memory/CPU not measured stay unknown; process-lifetime peak is not an arm-specific peak. Physical I/O/platform cost are unknown. Policy projections are not separate end-to-end timing runs.

| phase | wall_seconds | cpu_seconds | sampled_process_rss_bytes | process_lifetime_peak_bytes | logical_completed_hash_bytes | overlap |
| --- | --- | --- | --- | --- | --- | --- |
| producer_total | 203.828 | 198.984 | 241364992 | 305827840 | 140452303784 | none |
| native_generation_pairs | 0.186 | 0.171875 | unknown | unknown | unknown | subphase within producer_total |
| native_scoring | 0.079 | 0.0625 | unknown | unknown | unknown | subphase within producer_total |
| amortized_source_verification | 197.812 | unknown | unknown | unknown | 140451850210 | subphase within producer_total |
| independent_source_audit | 7.125 | 7.04688 | 327589888 | 333893632 | 2897268566 | none |
