# SC03 fixed-retrieval comparison

Separate experimental code for the full-context SciFact comparison. It does not
change the frozen sparse baseline or the production T6 backend.

- `inputs.py`: label-free primary input construction and explicit diagnostic sentence lineage.
- `prepare.py`: source-inclusive preparation of all five 300-claim conditions.
- `worker.py`: resident-model execution, durable per-pair results, hash-chained journal, explicit incomplete outcomes and no retries.
- `qualify_inputs.py` / `qualify_worker.py`: retained fictional tests.

The [protocol](<../../planning/TETHER SciFact Full Context Protocol 2026-11-06.md>)
fixes conditions, measurements and scientific limits before prediction. The
[checkpoint](https://github.com/rzzli/TETHER/blob/tether-pre-namespace-migration-20261106/planning/review-assets/tether-semantic-20261106/sc03/STATUS.md)
records actual qualification. Presence of prepared inputs or a successful
fictional rehearsal does not establish benchmark completion or performance.
