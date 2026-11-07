# Fixed-retrieval SciFact comparison

This module implements a full-context SciFact comparison separately from the sparse
baseline and production T6 workflow.

- `inputs.py`: label-free primary inputs and explicit diagnostic sentence lineage.
- `prepare.py`: source-inclusive preparation of the declared comparison conditions.
- `worker.py`: resident-model execution, durable pair results, a hash-chained journal
  and explicit incomplete outcomes without automatic retries.
- `qualify_inputs.py` / `qualify_worker.py`: invented-data checks.

The byte-pinned [protocol](PROTOCOL.md) fixes the comparison conditions,
measurements and scientific limits. Its original scope is retained; it does not
certify a new runtime, dataset version or model execution. Prepared inputs and
fictional rehearsals do not establish benchmark performance.
