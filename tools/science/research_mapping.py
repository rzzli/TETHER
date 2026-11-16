"""Build a small identifier-membership index from pinned OT24.09 originals.

This is a diagnostic projection with no actor-use grant. Originals, transport
receipts and old mapping products are unchanged. Only IDs and display labels are
decoded; synonym expansion, modern normalization and clinical fields are absent.
"""
import argparse
from collections import Counter
import hashlib
import math
from pathlib import Path
import time

from tether_engine.atomic import publish_bytes
from tether_engine.ingest import peak_memory_bytes
from tether_engine.journal import RunJournal
from tether_engine.serde import ContractError, canonical, parse_json
from tether_engine.source_access import SourceAccess, selected_root, local_path
from tether_engine.study.proofs import _no_links
from tether_engine.temporal import utc_instant
from tools.science.historical_inputs import BASE, NOTICE, availability, integrity_map


COLUMNS = {'targets': ('id', 'approvedSymbol'), 'diseases': ('id', 'name')}


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def build_index(manifest_path, expected_sha256, output, *, source_roots,
                max_bytes=256*1024**2, seconds=600):
    import pyarrow as pa
    import pyarrow.parquet as pq
    _need(pa.__version__ == '21.0.0', 'Mapping inspection requires pyarrow==21.0.0')
    _need(type(max_bytes) is int and max_bytes > 0 and type(seconds) in (int, float) and
          math.isfinite(seconds) and 0 < seconds <= 3600, 'Invalid mapping resource bounds')
    started = time.monotonic(); deadline = started+seconds
    manifest_path, output = local_path(manifest_path), local_path(output)
    access = SourceAccess(tuple(selected_root(root) for root in source_roots))
    _no_links(output.parent)
    if output.exists() or output.is_symlink(): _no_links(output)
    journal = RunJournal(output, kind='build')
    counts = Counter(); failure = None
    try:
        journal.append('mapping_inspection_started', manifest_sha256=expected_sha256,
                       source_columns=COLUMNS, max_bytes=max_bytes)
        raw = access.prepare([manifest_path], deadline=deadline).read(manifest_path, 16*1024**2)
        _need(hashlib.sha256(raw).hexdigest() == expected_sha256, 'Mapping manifest anchor differs')
        counts['metadata_bytes_hashed'] += len(raw)
        manifest = parse_json(raw)
        _need(manifest.get('release_id') == '24.09' and manifest.get('future_fallback') is False,
              'Expected pinned 24.09 mapping without modern fallback')
        files = manifest.get('files'); metadata = manifest.get('metadata'); products = manifest.get('products')
        _need(type(files) is list and type(metadata) is list and type(products) is list and
              len(files)+len(metadata) <= 10000, 'Bounded mapping inventory required')
        selected, declared = {}, {}
        for kind in COLUMNS:
            prefix = BASE+'output/etl/parquet/'+kind+'/'
            selected[kind] = [item for item in files if item.get('source_url', '').startswith(prefix)]
            matches = [item for item in products if item.get('product') == kind]
            _need(selected[kind] and len(matches) == 1, 'Missing or ambiguous mapping product')
            declared[kind] = matches[0]
            _need(type(declared[kind].get('rows')) is int and declared[kind]['rows'] >= 0 and
                  type(declared[kind].get('parents')) is list and
                  all(isinstance(p, str) for p in declared[kind]['parents']) and
                  len(set(declared[kind]['parents'])) == len(declared[kind]['parents']),
                  'Invalid mapping row count or parent declaration')
        urls = (NOTICE, BASE+'release_data_integrity', BASE+'release_data_integrity.sha1')
        proofs = []
        for url in urls:
            matches = [item for item in metadata if item.get('source_url') == url]
            _need(len(matches) == 1, 'Mapping requires one pinned notice and publisher integrity proof')
            proofs.append(matches[0])
        all_items = proofs + [item for kind in COLUMNS for item in selected[kind]]
        paths, estimated = set(), len(raw)
        for item in all_items:
            path, receipt = local_path(item['path']), local_path(item['receipt_path'])
            _need(path not in paths and receipt not in paths and path != receipt, 'Duplicate mapping input path')
            _need(not path.is_relative_to(output) and not receipt.is_relative_to(output), 'Mapping output overlaps input')
            _need(type(item.get('bytes')) is int and 0 < item['bytes'] <= 8*1024**2, 'Mapping source size exceeds bound')
            paths.update((path, receipt)); estimated += item['bytes']
        prepared = access.prepare(paths, deadline=deadline)
        estimated += sum(prepared.identities[local_path(item['receipt_path'])][2] for item in all_items)
        _need(estimated <= max_bytes, 'Mapping read budget exceeded')
        for item in all_items:
            _need(prepared.identities[local_path(item['path'])][2] == item['bytes'], 'Mapping size changed before read')
            _need(prepared.identities[local_path(item['receipt_path'])][2] <= 1024**2, 'Mapping receipt exceeds bound')
        ancestors = []

        def read_original(item, category):
            payload = prepared.read(local_path(item['path']), 8*1024**2)
            counts[category+'_bytes_hashed'] += len(payload)
            _need(hashlib.sha256(payload).hexdigest() == item['sha256'], 'Mapping original hash differs')
            receipt_bytes = prepared.read(local_path(item['receipt_path']), 1024**2)
            counts['receipt_bytes_hashed'] += len(receipt_bytes)
            _need(hashlib.sha256(receipt_bytes).hexdigest() == item['receipt_sha256'], 'Mapping receipt hash differs')
            receipt = parse_json(receipt_bytes)
            _need(receipt.get('status') == 'completed' and type(receipt.get('http_status')) is int and
                  receipt['http_status'] == 200 and receipt.get('source_url') == item['source_url'] and
                  receipt.get('sha256') == item['sha256'] and type(receipt.get('bytes')) is int and
                  receipt['bytes'] == len(payload), 'Mapping transport receipt differs')
            observed_at = utc_instant(receipt.get('retrieval_completed_at'))
            _need(utc_instant(receipt.get('retrieval_started_at')) <= observed_at,
                  'Mapping retrieval chronology differs')
            ancestors.append({key: item[key] for key in ('path', 'sha256', 'bytes', 'receipt_path', 'receipt_sha256', 'source_url')})
            counts['originals_verified'] += 1
            return payload

        notice, listing, checksum = [read_original(item, 'metadata') for item in proofs]
        _need(hashlib.sha1(listing).hexdigest() == checksum.decode('utf-8').split()[0],
              'Publisher mapping manifest checksum differs')
        publisher = integrity_map(listing.decode('utf-8'))
        available_by = availability(parse_json(notice))
        _need(available_by == manifest.get('available_by'), 'Mapping availability differs from original notice')
        indices = {}; source_rows = {}
        for kind, items in selected.items():
            prefix = 'output/etl/parquet/'+kind+'/'
            expected_paths = {name for name in publisher if name.startswith(prefix) and name.endswith('.parquet')}
            actual_paths = [item['source_url'].removeprefix(BASE) for item in items]
            _need(set(actual_paths) == expected_paths and len(actual_paths) == len(expected_paths) and
                  set(declared[kind].get('parents', ())) == expected_paths,
                  'Mapping publisher partition membership differs')
            index = {}; rows = 0
            for item in items:
                payload = read_original(item, 'source')
                relative = item['source_url'].removeprefix(BASE)
                _need(hashlib.sha1(payload).hexdigest() == publisher[relative] == item.get('publisher_sha1'),
                      'Mapping publisher payload checksum differs')
                with pq.ParquetFile(pa.BufferReader(payload), pre_buffer=False,
                                    thrift_string_size_limit=8*1024**2, thrift_container_size_limit=1000000) as parquet:
                    _need('id' in parquet.schema_arrow.names, 'Mapping is missing canonical identifiers')
                    columns = [key for key in COLUMNS[kind] if key in parquet.schema_arrow.names]
                    file_rows = 0
                    for group in range(parquet.num_row_groups):
                        offset = 0
                        for batch in parquet.iter_batches(row_groups=[group], columns=columns, batch_size=8192, use_threads=False):
                            if time.monotonic() >= deadline: raise TimeoutError('Mapping projection deadline exceeded')
                            counts['decoded_arrow_bytes'] += batch.nbytes
                            for position, row in enumerate(batch.to_pylist(), start=offset):
                                key = row.get('id'); label = row.get(COLUMNS[kind][1])
                                _need(isinstance(key, str) and key, 'Mapping has an unresolved identifier')
                                _need(label is None or isinstance(label, str), 'Mapping label is malformed')
                                _need(key not in index, 'Duplicate or conflicting canonical mapping identifier')
                                index[key] = dict(label=label, source_sha256=item['sha256'], row_group=group, row_index=position)
                                if label is None: counts[kind+'_missing_labels'] += 1
                            offset += batch.num_rows
                        _need(offset == parquet.metadata.row_group(group).num_rows, 'Mapping physical row-group count differs')
                        file_rows += offset
                    rows += file_rows
                journal.append('mapping_partition_projected', product=kind, sha256=item['sha256'], rows=file_rows)
            _need(rows == declared[kind].get('rows'), 'Mapping complete-product row count differs')
            indices[kind] = index; source_rows[kind] = rows
        report = dict(schema_version=1, status='identifier_membership_projection_verified',
                      manifest_sha256=expected_sha256, release_id='24.09', available_by=available_by,
                      availability_basis='retained_official_release_notice', indices=indices,
                      source_rows=source_rows, ancestors=ancestors, resource_counts=dict(counts),
                      actor_access_granted=False, source_roles_changed=False, scientific_validation='not_established',
                      elapsed_seconds=time.monotonic()-started, peak_memory_bytes=peak_memory_bytes(),
                      code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                      availability_code_sha256=hashlib.sha256(Path(__file__).with_name('historical_inputs.py').read_bytes()).hexdigest())
        encoded = canonical(report)+b'\n'
        _need(len(encoded) <= 64*1024**2, 'Mapping index exceeds output bound')
        publish_bytes(output/'index.json', encoded)
        digest = hashlib.sha256(encoded).hexdigest()
        terminal = journal.append('build_completed', index_sha256=digest, source_rows=source_rows)
        journal.seal(canonical(dict(schema_version=1, index_sha256=digest, journal_head=terminal['sha256'])),
                     name='terminal-seal.json', deadline=deadline)
        return report
    except BaseException as error:
        failure = error
        try: journal.fail(error, 'identifier_membership_projection')
        except BaseException as secondary: error.add_note('Mapping failure journal: '+type(secondary).__name__)
        raise
    finally:
        try: journal.close()
        except BaseException as secondary:
            if failure is None: raise
            failure.add_note('Mapping journal close: '+type(secondary).__name__)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-root', type=Path, action='append', required=True)
    args = parser.parse_args()
    result = build_index(args.manifest.absolute(), args.sha256, args.output.absolute(), source_roots=args.source_root)
    print(canonical({key: result[key] for key in ('status', 'source_rows', 'resource_counts', 'elapsed_seconds', 'peak_memory_bytes')}).decode())


if __name__ == '__main__': main()
