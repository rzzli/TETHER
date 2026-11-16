"""Bounded three-view reduction over externally verified nonclinical inputs.

This pure research reducer grants no filesystem or agent access. Its caller must
verify original bytes, source-use grants and mapping membership before use. The
output explicitly leaves those assurances unverified here. Production admission
is unchanged; evaluator-only ancestors are rejected even in current views.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
import re

from tether_engine.serde import ContractError, fingerprint
from tether_engine.temporal import utc_instant
from tools.science.temporal_dates import calendar_interval, compare_calendar


VIEWS = ('archived', 'current_filtered', 'current_unfiltered')
SOURCES = {'gene_burden': 'genetic_association', 'uniprot_literature': 'genetic_association',
           'expression_atlas': 'rna_expression'}
FIELDS = ('id', 'datasourceId', 'datatypeId', 'targetId', 'diseaseId', 'literature',
          'publicationYear', 'publicationDate', 'evidenceDate', 'releaseDate', 'releaseVersion',
          'studyId', 'studySampleSize', 'pValueMantissa', 'pValueExponent', 'beta',
          'betaConfidenceIntervalLower', 'betaConfidenceIntervalUpper', 'oddsRatio',
          'oddsRatioConfidenceIntervalLower', 'oddsRatioConfidenceIntervalUpper',
          'log2FoldChangeValue', 'log2FoldChangePercentileRank')
HYPOTHESIS = ('target_id', 'indication_id', 'target_namespace_version', 'indication_namespace_version',
              'intended_action', 'modality', 'tissue')
COUNTERS = ('physical_rows', 'outside_case_universe', 'failed_qc_rows', 'selected_rows',
            'duplicate_rows', 'conflicting_rows', 'date_not_comparable', 'date_rejected',
            'accepted_rows', 'case_records')


@dataclass(frozen=True)
class ProjectedBatch:
    """A physical Arrow batch; omitted rows fail the target/disease candidate mask.

    Selected rows keep absolute offsets within their original row group. This
    avoids creating Python dictionaries for irrelevant source records.
    """
    source_id: str
    row_group: int
    first_row: int
    physical_rows: int
    selected: tuple
    source_sha256: str


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _hash(value):
    _need(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value), 'Invalid research fingerprint')


def build_views(frame, rows, *, expected_frame_sha256):
    """Reduce located rows; no row iterator access occurs before frame validation.

    ``rows`` emits source_id, zero-based row_group/row_index and values from the
    declared nonclinical projection. The eventual I/O adapter must preserve the
    original physical locators and authenticate each source before yielding.
    Counts refer to this selected-source stream, never the complete database.
    """
    _hash(expected_frame_sha256)
    _need(fingerprint(frame) == expected_frame_sha256, 'Research frame anchor differs')
    frame = deepcopy(frame)
    _need(type(frame.get('schema_version')) is int and frame['schema_version'] == 1,
          'Unsupported research frame version')
    _need(isinstance(frame.get('view_policy_id'), str) and frame['view_policy_id'], 'Missing view policy identity')
    _hash(frame.get('method_sha256'))
    origin = utc_instant(frame.get('decision_origin'))
    _need(origin.hour == origin.minute == origin.second == origin.microsecond == 0,
          'Calendar-filter research origin must be UTC midnight')
    cutoff = origin.date().isoformat()
    _need(frame.get('filter_field') == 'publicationDate', 'Unsupported research row-date field')
    for limit in ('max_rows', 'max_selected_rows'):
        _need(type(frame.get(limit)) is int and 0 < frame[limit] <= 1000000, 'Invalid research row budget')
    cases = frame.get('hypotheses')
    _need(type(cases) is list and 0 < len(cases) <= 10000, 'Bounded hypothesis universe required')
    by_pair, case_ids = defaultdict(list), set()
    for case in cases:
        _need(type(case) is dict and set(case) == {'case_id', *HYPOTHESIS}, 'Invalid hypothesis shape')
        _need(all(isinstance(case[k], str) and case[k] for k in ('case_id', *HYPOTHESIS[:-1])) and
              (case['tissue'] is None or isinstance(case['tissue'], str) and case['tissue']), 'Invalid hypothesis identity')
        _need(case['case_id'] not in case_ids, 'Duplicate case ID')
        case_ids.add(case['case_id'])
        case['hypothesis_sha256'] = fingerprint({k: case[k] for k in HYPOTHESIS})
        by_pair[case['target_id'], case['indication_id']].append(case['case_id'])
    case_hash = fingerprint(cases)
    listed = frame.get('sources')
    _need(type(listed) is list and 0 < len(listed) <= 10000 and all(type(s) is dict for s in listed),
          'Bounded source lineage required')
    _need(all(isinstance(s.get('artifact_id'), str) and s['artifact_id'] for s in listed), 'Invalid source identity')
    sources = {s['artifact_id']: s for s in listed}
    _need(len(sources) == len(listed), 'Duplicate source identity')
    closures, active = {}, set()

    def closure(key, depth=0):
        _need(depth <= 64, 'Research lineage exceeds depth limit')
        _need(key in sources, 'Missing research lineage parent')
        _need(key not in active, 'Research lineage cycle')
        if key in closures: return closures[key]
        source = sources[key]
        _hash(source.get('sha256'))
        _need(source.get('role') in ('agent_evidence', 'reference') and
              source.get('purpose') in ('nonclinical_evidence', 'identifier_mapping', 'release_proof'),
              'Forbidden research ancestor role or purpose')
        _need(isinstance(source.get('release'), str) and source['release'], 'Missing source release')
        if source.get('available_by') is not None: utc_instant(source['available_by'])
        parents = source.get('parents')
        _need(type(parents) is list and all(isinstance(p, str) for p in parents) and
              len(set(parents)) == len(parents), 'Invalid source parents')
        if source['purpose'] == 'nonclinical_evidence':
            _need(isinstance(source.get('datasource'), str) and source['datasource'] in SOURCES,
                  'Forbidden or unsupported nonclinical source')
        active.add(key)
        found = {key}
        for parent in parents: found.update(closure(parent, depth+1))
        active.remove(key)
        closures[key] = found
        return found

    views = frame.get('views')
    _need(type(views) is dict and set(views) == set(VIEWS), 'Exactly three research views required')
    _need(views['current_filtered'] == views['current_unfiltered'], 'Current arms require the same source list')
    used, view_closures, view_releases = set(), {}, {}
    for view, ids in views.items():
        _need(type(ids) is list and ids and all(isinstance(k, str) for k in ids) and
              len(set(ids)) == len(ids), 'Nonempty unique view source list required')
        refs = set()
        for key in ids:
            refs.update(closure(key))
            _need(sources[key]['purpose'] == 'nonclinical_evidence', 'View input is not nonclinical evidence')
        used.update(refs)
        _need(any(sources[k]['purpose'] == 'identifier_mapping' for k in refs), 'Missing view mapping ancestor')
        releases = {sources[k]['release'] for k in ids}
        _need(len(releases) == 1, 'View mixes evidence releases')
        view_releases[view] = next(iter(releases))
        if view == 'archived':
            _need(all(sources[k].get('available_by') is not None and
                      utc_instant(sources[k]['available_by']) <= origin for k in refs),
                  'Archived lineage has unknown or later availability')
        view_closures[view] = refs
    _need(used == set(sources), 'Unused source lineage is not permitted')
    _need(view_releases['archived'] != view_releases['current_filtered'], 'Archive/current releases must differ')
    admitted = set().union(*(set(ids) for ids in views.values()))
    source_views = {key: tuple(v for v in VIEWS if key in views[v]) for key in admitted}
    counters = {v: Counter({key: 0 for key in COUNTERS}) for v in VIEWS}
    selected = {v: defaultdict(list) for v in VIEWS}
    locators, count, selected_count = set(), 0, 0
    intervals = defaultdict(list)
    positions_by_group = defaultdict(set)

    def located_rows():
        nonlocal count
        for block in rows:
            if not isinstance(block, ProjectedBatch):
                count += 1
                _need(count <= frame['max_rows'], 'Research row budget exceeded')
                if type(block) is dict:
                    key = (block.get('source_id'), block.get('row_group'))
                    if isinstance(key[0], str) and type(key[1]) is int and type(block.get('row_index')) is int:
                        _need(not any(a <= block['row_index'] < b for a, b in intervals[key]), 'Overlapping physical locator')
                yield block
                continue
            _need(isinstance(block.source_id, str) and block.source_id in admitted,
                  'Batch uses an unselected source')
            _need(block.source_sha256 == sources[block.source_id]['sha256'],
                  'Batch payload hash differs from frame source')
            _need(all(type(value) is int and value >= 0 for value in (block.row_group, block.first_row)) and
                  type(block.physical_rows) is int and block.physical_rows > 0,
                  'Invalid physical batch locator')
            _need(type(block.selected) is tuple and len(block.selected) <= block.physical_rows,
                  'Invalid selected batch rows')
            start, end = block.first_row, block.first_row + block.physical_rows
            key = (block.source_id, block.row_group)
            _need(not any(start < b and end > a for a, b in intervals[key]) and
                  not any(start <= i < end for i in positions_by_group[key]),
                  'Overlapping physical batch locator')
            indices = set()
            for row in block.selected:
                _need(type(row) is dict and row.get('source_id') == block.source_id and
                      row.get('row_group') == block.row_group and type(row.get('row_index')) is int and
                      start <= row['row_index'] < end and row['row_index'] not in indices,
                      'Selected row differs from physical batch locator')
                indices.add(row['row_index'])
            intervals[key].append((start, end))
            count += block.physical_rows
            _need(count <= frame['max_rows'], 'Research row budget exceeded')
            omitted = block.physical_rows - len(block.selected)
            for v in source_views[block.source_id]:
                counters[v]['physical_rows'] += omitted
                counters[v]['outside_case_universe'] += omitted
            yield from block.selected

    for row in located_rows():
        _need(type(row) is dict and isinstance(row.get('source_id'), str) and row['source_id'] in admitted,
              'Row uses an unselected source')
        source_id = row['source_id']
        _need(all(type(row.get(k)) is int and row[k] >= 0 for k in ('row_group', 'row_index')), 'Invalid physical locator')
        locator = (source_id, row['row_group'], row['row_index'])
        _need(locator not in locators, 'Repeated physical source locator')
        locators.add(locator)
        positions_by_group[source_id, row['row_group']].add(row['row_index'])
        values = row.get('values')
        _need(type(values) is dict, 'Row values must be an object')
        datasource = sources[source_id]['datasource']
        relevant = source_views[source_id]
        for v in relevant: counters[v]['physical_rows'] += 1
        # Match the Arrow adapter: omitted target/disease candidates receive no
        # scientific QC verdict. Their other fields never need Python decoding.
        pair = values.get('targetId'), values.get('diseaseId')
        matches = by_pair.get(pair, ()) if all(isinstance(value, str) for value in pair) else ()
        if not matches:
            for v in relevant: counters[v]['outside_case_universe'] += 1
            continue
        if (values.get('datasourceId') != datasource or values.get('datatypeId') != SOURCES[datasource] or
                not all(isinstance(values.get(k), str) and values[k] for k in ('id', 'targetId', 'diseaseId'))):
            for v in relevant: counters[v]['failed_qc_rows'] += 1
            continue
        year = values.get('publicationYear')
        publication = calendar_interval(values.get('publicationDate'))
        year_interval = calendar_interval(year)
        if year is not None and (type(year) is not int or year_interval['status'] != 'valid' or
                                 publication['status'] == 'valid' and not
                                 year_interval['lower'] <= publication['lower'] < publication['upper'] <= year_interval['upper']):
            for v in relevant: counters[v]['failed_qc_rows'] += 1
            continue
        selected_count += 1
        _need(selected_count <= frame['max_selected_rows'], 'Research selected-row budget exceeded')
        projected = {key: deepcopy(values[key]) for key in FIELDS if key in values}
        record = dict(source_id=source_id, source_sha256=sources[source_id]['sha256'],
                      row_group=row['row_group'], row_index=row['row_index'],
                      case_ids=list(matches), values=projected, features={}, probability=None)
        for v in relevant:
            counters[v]['selected_rows'] += 1
            selected[v][datasource, values['id']].append(record)

    outputs = {}
    for v in VIEWS:
        coverage, records = counters[v], []
        for key in sorted(selected[v]):
            group = selected[v][key]
            if len({fingerprint(r['values']) for r in group}) != 1:
                coverage['conflicting_rows'] += len(group)
                continue
            coverage['duplicate_rows'] += len(group)-1
            record = group[0]
            date = calendar_interval(record['values'].get(frame['filter_field']))
            relation = compare_calendar(date, cutoff)
            if relation == 'not_comparable': coverage['date_not_comparable'] += 1
            # The research filter never falls back to a publication year, but an
            # explicit future year is still inconsistent with archived content.
            year_relation = compare_calendar(calendar_interval(record['values'].get('publicationYear')), cutoff)
            reject = (v == 'current_filtered' and relation != 'entirely_before' or
                      v == 'archived' and (relation in ('at_or_after', 'crossing') or
                                           year_relation in ('at_or_after', 'crossing')))
            if reject:
                coverage['date_rejected'] += 1
                continue
            records.append(record)
        coverage['accepted_rows'] = len(records)
        case_counts = Counter(c for record in records for c in record['case_ids'])
        coverage['case_records'] = sum(case_counts.values())
        _need(coverage['physical_rows'] == coverage['outside_case_universe'] + coverage['failed_qc_rows'] + coverage['selected_rows'] and
              coverage['selected_rows'] == sum(coverage[k] for k in ('accepted_rows', 'duplicate_rows', 'conflicting_rows', 'date_rejected')),
              'Research coverage accounting differs')
        refs = sorted(view_closures[v])
        later = any(sources[k].get('available_by') is not None and utc_instant(sources[k]['available_by']) > origin for k in refs)
        unknown = any(sources[k].get('available_by') is None for k in refs)
        verdict = 'later_information' if later else 'availability_unknown' if unknown else 'eligible_by_declared_lineage'
        outputs[v] = dict(view_policy_id=frame['view_policy_id'], decision_origin=frame['decision_origin'],
                          case_universe_sha256=case_hash, hypotheses=deepcopy(cases), method_sha256=frame['method_sha256'],
                          source_release=view_releases[v], mapping_releases=sorted({sources[k]['release'] for k in refs if sources[k]['purpose'] == 'identifier_mapping'}),
                          lineage=[deepcopy(sources[k]) for k in refs], temporal_verdict=verdict,
                          filter_field=frame['filter_field'] if v == 'current_filtered' else None,
                          filter_rule=('reported_calendar_interval_entirely_before_origin' if v == 'current_filtered' else
                                       'exclude_explicit_future_publication_conflicts' if v == 'archived' else 'none'),
                          coverage=dict(coverage), records=deepcopy(records),
                          case_coverage={c: dict(accepted_rows=case_counts[c], interpretation='selected_input_present' if case_counts[c] else 'no_selected_input_not_biological_absence') for c in sorted(case_ids)})
    return dict(schema_version=1, frame_sha256=expected_frame_sha256,
                integrity_verdict='requires_external_source_byte_verification',
                source_use_verdict='requires_external_artifact_grant_verification',
                mapping_membership='requires_external_mapping_verification',
                scientific_validation='not_established', views=outputs)
