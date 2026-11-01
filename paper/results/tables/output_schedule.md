# Complete 38-output terminal accounting

All scheduled outputs remain in accounting, including the two malformed constructed returns. Native and constructed strata are separate; this mixed schedule is not a success denominator.

| cell_id | case_id | arm | stratum | terminal | received_terminal | raw_bytes | exact_report | full_source_admitted | full_verified_exact |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| N-L-p05-01 | p05-01 | L | native | returned | returned | 5617 | true | true | true |
| N-A-p05-01 | p05-01 | A | native | returned | returned | 256 | false | true | false |
| N-L-p05-02 | p05-02 | L | native | returned | returned | 5616 | true | true | true |
| N-A-p05-02 | p05-02 | A | native | returned | returned | 256 | false | true | false |
| N-L-p05-03 | p05-03 | L | native | returned | returned | 5605 | true | true | true |
| N-A-p05-03 | p05-03 | A | native | returned | returned | 256 | false | true | false |
| N-L-p05-04 | p05-04 | L | native | returned | returned | 5597 | true | true | true |
| N-A-p05-04 | p05-04 | A | native | returned | returned | 256 | false | true | false |
| N-L-p05-05 | p05-05 | L | native | returned | returned | 5623 | true | true | true |
| N-A-p05-05 | p05-05 | A | native | returned | returned | 256 | false | true | false |
| N-L-p05-06 | p05-06 | L | native | returned | returned | 5622 | true | true | true |
| N-A-p05-06 | p05-06 | A | native | returned | returned | 256 | false | true | false |
| N-L-p05-07 | p05-07 | L | native | returned | returned | 5616 | true | true | true |
| N-A-p05-07 | p05-07 | A | native | returned | returned | 256 | false | true | false |
| N-L-p05-08 | p05-08 | L | native | returned | returned | 5614 | true | true | true |
| N-A-p05-08 | p05-08 | A | native | returned | returned | 256 | false | true | false |
| N-L-p05-09 | p05-09 | L | native | returned | returned | 5584 | true | true | true |
| N-A-p05-09 | p05-09 | A | native | returned | returned | 256 | false | true | false |
| N-L-p05-10 | p05-10 | L | native | returned | returned | 5615 | true | true | true |
| N-A-p05-10 | p05-10 | A | native | returned | returned | 256 | false | true | false |
| N-L-p05-11 | p05-11 | L | native | returned | returned | 5623 | true | true | true |
| N-A-p05-11 | p05-11 | A | native | returned | returned | 256 | false | true | false |
| N-L-p05-12 | p05-12 | L | native | returned | returned | 5593 | true | true | true |
| N-A-p05-12 | p05-12 | A | native | returned | returned | 256 | false | true | false |
| S-C01 | C01 | fixture | fictional_json_core | returned | returned | 5392 | true | true | true |
| S-C02 | C02 | fixture | fictional_json_core | returned | returned | 5441 | true | true | true |
| S-C03 | C03 | fixture | fictional_json_core | returned | returned | 7790 | true | true | true |
| S-C04 | C04 | fixture | fictional_json_core | returned | returned | 5455 | true | true | true |
| S-F01 | F01 | fixture | fictional_json_core | returned | returned | 5392 | unknown | false | false |
| S-F02 | F02 | fixture | fictional_json_core | returned | returned | 5392 | unknown | false | false |
| S-F03 | F03 | fixture | fictional_json_core | returned | returned | 5392 | true | false | false |
| S-F04 | F04 | fixture | fictional_json_core | returned | returned | 5392 | true | false | false |
| S-F05 | F05 | fixture | fictional_json_core | returned | returned | 5392 | false | true | false |
| S-F06 | F06 | fixture | fictional_json_core | returned | returned | 5394 | false | true | false |
| S-F07 | F07 | fixture | fictional_json_core | returned | returned | 5443 | false | true | false |
| S-F08 | F08 | fixture | fictional_json_core | malformed | returned | 5412 | false | true | false |
| S-F09 | F09 | fixture | fictional_json_core | returned | returned | 5392 | unknown | false | false |
| S-F10 | F10 | fixture | fictional_json_core | malformed | returned | 262145 | false | true | false |
