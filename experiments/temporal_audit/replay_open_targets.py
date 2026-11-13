"""Replay aggregate pair/date cells from nine pinned local OT partitions.

Optional dependency: install the repository's ingestion extra (pyarrow==21.0.0).
Run directly from a source checkout; no PYTHONPATH, Git, network or registry data
is required. The manifest is an explicit inventory, not proof of publisher-wide
completeness. Only four columns are decoded. Literal dates are calendar intervals,
not historical availability, and pair overlap is not scientific validation.
"""
from __future__ import annotations

import argparse
import hashlib
import io
from itertools import combinations
import json
from pathlib import Path
import re
import sys
import time

if __package__ in (None, ''):
    _checkout = Path(__file__).resolve().parents[2]
    sys.path[:0] = [str(_checkout / 'src'), str(_checkout)]

from tether_engine.atomic import publish_bytes
from tether_engine.bundle_files import checked_output, checked_root, logical_parts, read_local
from tether_engine.ingest import arrow
from tether_engine.serde import ContractError, canonical, parse_json
from tools.science.temporal_dates import calendar_interval, compare_calendar

RELEASES = ('22.11', '24.09', '25.09')
SOURCES = ('gene_burden', 'uniprot_literature', 'expression_atlas')
ROLES = tuple((release, source) for source in SOURCES for release in RELEASES)
CLOCKS = (('22.11', '2022-11-25'), ('24.09', '2024-09-19'))
COLUMNS = ('targetId', 'diseaseId', 'evidenceDate', 'publicationDate')
DATE_FIELDS = COLUMNS[2:]
DATE_STATES = ('entirely_before', 'at_or_after', 'crossing', 'missing_column',
               'null', 'empty', 'malformed', 'unsupported')
MAX_FILES, MAX_ROWS = 2000, 2_000_000
MAX_FILE_BYTES, MAX_TOTAL_BYTES = 64 * 1024**2, 1024**3


def _need(condition, message):
    if not condition: raise ContractError(message)


def provider_prefix(release, source):
    middle = 'output/etl/parquet/evidence' if release in ('22.11', '24.09') else 'output/evidence'
    return f'{release}/{middle}/sourceId={source}/'


def _manifest(path, expected):
    _need(type(expected) is str and re.fullmatch('[0-9a-f]{64}', expected), 'Exact manifest SHA256 required')
    payload = read_local(path, 2 * 1024**2)
    _need(hashlib.sha256(payload).hexdigest() == expected, 'Manifest hash mismatch')
    value = parse_json(payload)
    _need(type(value) is dict and set(value) == {'schema_version', 'kind', 'partitions'} and
          type(value['schema_version']) is int and value['schema_version'] == 1 and
          value['kind'] == 'ot_temporal_replay_manifest_v1', 'Invalid source replay manifest')
    partitions = value['partitions']
    _need(type(partitions) is list and len(partitions) == len(ROLES), 'Exactly nine source/release roles required')
    roles, paths, provider_paths, total, count = {}, set(), set(), 0, 0
    for part in partitions:
        _need(type(part) is dict and set(part) == {'release', 'source', 'files'} and
              type(part['release']) is str and type(part['source']) is str, 'Invalid partition fields')
        role = (part['release'], part['source'])
        _need(role in ROLES and role not in roles, 'Unknown or duplicate source/release role')
        files = part['files']
        _need(type(files) is list and files, 'Every source/release role requires files')
        for item in files:
            _need(type(item) is dict and set(item) == {'path', 'provider_path', 'sha256', 'bytes'}, 'Invalid file fields')
            logical_parts(item['path']); logical_parts(item['provider_path'])
            prefix = provider_prefix(*role)
            _need(item['provider_path'].startswith(prefix) and
                  '/' not in item['provider_path'][len(prefix):] and item['provider_path'].endswith('.parquet'),
                  'File is outside the declared provider partition')
            _need(item['path'].casefold() not in paths and item['provider_path'].casefold() not in provider_paths,
                  'Duplicate or aliased source file')
            paths.add(item['path'].casefold()); provider_paths.add(item['provider_path'].casefold())
            _need(type(item['bytes']) is int and 0 < item['bytes'] <= MAX_FILE_BYTES and
                  type(item['sha256']) is str and re.fullmatch('[0-9a-f]{64}', item['sha256']), 'Invalid file size or digest')
            total += item['bytes']; count += 1
        roles[role] = files
    _need(set(roles) == set(ROLES) and count <= MAX_FILES and total <= MAX_TOTAL_BYTES, 'Source inventory scope or byte limit')
    return roles, total, count


def pair_counts(left, right):
    shared, union = len(left & right), len(left | right)
    return dict(left_keys=len(left), right_keys=len(right), shared=shared,
                left_unmatched=len(left - right), right_unmatched=len(right - left),
                union=union, jaccard=shared / union if union else None)


class _View:
    def __init__(self, release, source, name):
        self.release, self.source, self.name = release, source, name
        self.rows, self.valid = 0, 0
        self.pairs = set()
        self.dates = {field: {cutoff: dict.fromkeys(DATE_STATES, 0) for _, cutoff in CLOCKS}
                      for field in DATE_FIELDS}

    def add(self, pair, intervals):
        self.rows += 1
        if pair is not None:
            self.valid += 1; self.pairs.add(pair)
        for field in DATE_FIELDS:
            for _, cutoff in CLOCKS:
                interval = intervals[field]
                state = compare_calendar(interval, cutoff) if interval['status'] == 'valid' else interval['status']
                self.dates[field][cutoff][state] += 1

    def summary(self):
        _need(all(sum(counts.values()) == self.rows for cutoffs in self.dates.values() for counts in cutoffs.values()),
              'Date denominator mismatch')
        return dict(release=self.release, source=self.source, view=self.name,
                    rows={'physical_rows': self.rows},
                    pairs=dict(valid_key_rows=self.valid, invalid_key_rows=self.rows-self.valid, unique_keys=len(self.pairs)),
                    date_views=self.dates)


def replay(manifest_path, expected_manifest_sha256, root):
    """Read exact manifest bytes and hash each bounded original before decoding it."""
    started = time.monotonic()
    roles, original_bytes, file_count = _manifest(Path(manifest_path), expected_manifest_sha256)
    root = checked_root(root)
    pq = arrow()
    import pyarrow as pa
    views, comparisons, total_rows = [], [], 0
    all_views = {}
    for release, source in ROLES:
        full = _View(release, source, 'full')
        filtered = {(field, cutoff): _View(release, source, f'literal:{field}:{cutoff}')
                    for field in DATE_FIELDS for _, cutoff in CLOCKS} if release == '25.09' else {}
        for item in roles[(release, source)]:
            _need(time.monotonic()-started < 600, 'Source replay time limit')
            path = root.joinpath(*logical_parts(item['path']))
            payload = read_local(path, item['bytes'])
            _need(len(payload) == item['bytes'] and hashlib.sha256(payload).hexdigest() == item['sha256'],
                  'Original size or hash mismatch')
            # Arrow reads exactly these already verified bytes, not a reopened path.
            try:
                parquet = pq.ParquetFile(io.BytesIO(payload))
                names = parquet.schema_arrow.names
                _need(len(names) == len(set(names)), 'Duplicate source columns')
                selected = [name for name in COLUMNS if name in names]
                rows = 0
                for batch in parquet.iter_batches(batch_size=8192, columns=selected, use_threads=False):
                    _need(time.monotonic()-started < 600, 'Source replay time limit')
                    rows += batch.num_rows; total_rows += batch.num_rows
                    _need(total_rows <= MAX_ROWS, 'Source replay row limit')
                    for row in batch.to_pylist() if selected else [{}] * batch.num_rows:
                        target, disease = row.get('targetId'), row.get('diseaseId')
                        pair = (target, disease) if (type(target) is str and target.strip() and
                                                    type(disease) is str and disease.strip()) else None
                        intervals = {field: calendar_interval(row[field]) if field in row else {'status':'missing_column'}
                                     for field in DATE_FIELDS}
                        full.add(pair, intervals)
                        for (field, cutoff), view in filtered.items():
                            if compare_calendar(intervals[field], cutoff) == 'entirely_before': view.add(pair, intervals)
                _need(rows == parquet.metadata.num_rows, 'Footer/scanned row mismatch')
            except ContractError:
                raise
            except (pa.ArrowException, OSError, ValueError, TypeError, OverflowError) as error:
                raise ContractError('Source replay Parquet decoding failed') from error
        all_views[(release, source)] = full
        views.append(full.summary())
        for view in filtered.values():
            views.append(view.summary()); all_views[(view.name, source)] = view
    for source in SOURCES:
        pairs = [(all_views[(left, source)], all_views[(right, source)]) for left, right in combinations(RELEASES, 2)]
        pairs += [(all_views[(release, source)], all_views[(f'literal:{field}:{cutoff}', source)])
                  for field in DATE_FIELDS for release, cutoff in CLOCKS]
        for left, right in pairs:
            comparisons.append(dict(source=source, left_release=left.release, right_release=right.release,
                                    left_view=left.name, right_view=right.name, pairs=pair_counts(left.pairs, right.pairs)))
    from tools.science import temporal_dates
    return dict(schema_version=1, kind='ot_temporal_aggregate_replay_v1', status='aggregate_replayed',
                role='evaluation_only', agent_visible=False, manifest_sha256=expected_manifest_sha256,
                file_count=file_count, compressed_original_bytes=original_bytes, physical_rows=total_rows,
                projection=list(COLUMNS), release_clocks=[list(item) for item in CLOCKS],
                views=views, comparisons=comparisons, pyarrow_version=pa.__version__,
                code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                calendar_parser_module_sha256=hashlib.sha256(Path(temporal_dates.__file__).read_bytes()).hexdigest(),
                elapsed_seconds=round(time.monotonic()-started, 6),
                scope='Manifest-declared stored-product aggregate cells; no provider-ID or reference comparisons.',
                historical_actor_inputs_qualified=False, clinical_labels_qualified=False,
                publisher_completeness_independently_established=False, source_values_emitted=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        root = checked_root(args.root)
        output = checked_output(args.output, (root,))
        checked_root(output.parent)
        result = replay(args.manifest, args.manifest_sha256, root)
        checked_output(output, (root,))
        publish_bytes(output, canonical(result) + b'\n')
    except (ContractError, OSError) as error:
        print('Source replay failed: ' + str(error), file=sys.stderr)
        return 1
    print(json.dumps(dict(status=result['status'], file_count=result['file_count'], physical_rows=result['physical_rows'])))
    return 0


if __name__ == '__main__': raise SystemExit(main())
