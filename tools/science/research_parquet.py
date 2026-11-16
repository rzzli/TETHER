"""Protected, projected Arrow batches for the experimental research reducer.

Original byte verification is local consistency only. Receipts, source-use grants,
release clocks and mapping membership must be qualified by the enclosing driver.
No network, output publication, production dispatch or role changes occur here.
"""
from copy import deepcopy
import hashlib
import math
import time

from tether_engine.serde import ContractError, fingerprint
from tether_engine.source_access import SourceAccess, selected_root, local_path
from tools.science.research_views import FIELDS, ProjectedBatch


def stream_rows(descriptors, hypotheses, *, expected_descriptors_sha256, source_roots,
                batch_rows=8192, max_bytes=256*1024**2, seconds=600, stats=None):
    """Yield physical batches, converting only target/disease candidates to Python.

    Exact-pair checking remains in the reducer. The Arrow mask is a conservative
    cross-product of selected target and disease IDs; therefore it may overselect
    candidates but cannot silently omit a selected pair. QC of omitted rows is
    outside this selected-hypothesis scope.
    """
    import pyarrow as pa
    import pyarrow.compute as pc
    import pyarrow.parquet as pq
    if pa.__version__ != '21.0.0':
        raise ContractError('Research source reading requires pyarrow==21.0.0')
    if fingerprint(descriptors) != expected_descriptors_sha256:
        raise ContractError('Source descriptor anchor differs')
    if (type(descriptors) is not list or not 0 < len(descriptors) <= 10000 or
            type(batch_rows) is not int or not 0 < batch_rows <= 8192 or
            type(max_bytes) is not int or max_bytes <= 0 or
            type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= 3600):
        raise ContractError('Invalid bounded research source request')
    descriptors, hypotheses = deepcopy(descriptors), deepcopy(hypotheses)
    if type(hypotheses) is not list or not hypotheses or len(hypotheses) > 10000:
        raise ContractError('Bounded hypothesis list required for source filtering')
    targets = {case['target_id'] for case in hypotheses}
    diseases = {case['indication_id'] for case in hypotheses}
    if not all(isinstance(x, str) and x for x in targets | diseases):
        raise ContractError('Explicit target and disease identifiers required')
    targets, diseases = pa.array(sorted(targets)), pa.array(sorted(diseases))
    started = time.monotonic()
    deadline = started+seconds
    access = SourceAccess(tuple(selected_root(root) for root in source_roots))
    paths, ids, total = {}, set(), 0
    for item in descriptors:
        if type(item) is not dict or set(item) != {'artifact_id', 'path', 'sha256', 'bytes'}:
            raise ContractError('Invalid research source descriptor')
        path = local_path(item['path'])
        if (not isinstance(item['artifact_id'], str) or not item['artifact_id'] or
                item['artifact_id'] in ids or path in paths or type(item['bytes']) is not int or
                not 0 < item['bytes'] <= 8*1024**2):
            raise ContractError('Duplicate or oversized research source')
        paths[path] = item
        ids.add(item['artifact_id'])
        total += item['bytes']
    if total > max_bytes:
        raise ContractError('Research source byte budget exceeded')
    prepared = access.prepare(paths, deadline=deadline)
    if any(prepared.identities[path][2] != item['bytes'] for path, item in paths.items()):
        raise ContractError('Source size differs before bounded read')
    if stats is None: stats = {}
    if type(stats) is not dict or stats:
        raise ContractError('Source statistics require an empty caller-owned dictionary')
    stats.update(status='reading', files_verified=0, bytes_hashed=0,
                 physical_rows=0, python_rows=0, outside_candidate_mask=0, batches=0)
    try:
        for path, item in paths.items():
            payload = prepared.read(path, 8*1024**2)
            stats['bytes_hashed'] += len(payload)
            if hashlib.sha256(payload).hexdigest() != item['sha256']:
                raise ContractError('Research source payload hash differs')
            stats['files_verified'] += 1
            with pq.ParquetFile(pa.BufferReader(payload), pre_buffer=False,
                                thrift_string_size_limit=8*1024**2, thrift_container_size_limit=1000000) as parquet:
                required = {'id', 'datasourceId', 'datatypeId', 'targetId', 'diseaseId'}
                if not required <= set(parquet.schema_arrow.names):
                    raise ContractError('Required research source columns are missing')
                columns = [name for name in FIELDS if name in parquet.schema_arrow.names]
                for group in range(parquet.num_row_groups):
                    start = 0
                    for batch in parquet.iter_batches(row_groups=[group], columns=columns, batch_size=batch_rows,
                                                      use_threads=False):
                        if time.monotonic() >= deadline:
                            raise TimeoutError('Research source deadline exceeded')
                        mask = pc.fill_null(pc.and_(pc.is_in(batch.column('targetId'), value_set=targets),
                                                    pc.is_in(batch.column('diseaseId'), value_set=diseases)), False)
                        offsets = pc.filter(pa.array(range(start, start+batch.num_rows)), mask).to_pylist()
                        filtered = batch.filter(mask)
                        values = filtered.to_pylist()
                        selected = tuple(dict(source_id=item['artifact_id'], row_group=group,
                                              row_index=index, values=value) for index, value in zip(offsets, values))
                        stats['physical_rows'] += batch.num_rows
                        stats['python_rows'] += len(selected)
                        stats['outside_candidate_mask'] += batch.num_rows-len(selected)
                        stats['batches'] += 1
                        yield ProjectedBatch(item['artifact_id'], group, start, batch.num_rows, selected, item['sha256'])
                        start += batch.num_rows
                    if start != parquet.metadata.row_group(group).num_rows:
                        raise ContractError('Physical row-group scan differs from source footer')
        stats['status'] = 'completed'
    except BaseException as error:
        stats.update(status='failed_or_interrupted', error_class=type(error).__name__)
        raise
    finally:
        stats['elapsed_seconds'] = time.monotonic()-started
