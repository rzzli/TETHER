"""Pure retained-input preparation sizing; no admission, tokenizer or model calls."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from asof.journal import RunJournal, read_chain
from asof.serde import canonical, encode, fingerprint, parse_json
from asof.study.diagnostic import load_synthetic_request
from asof.study.diagnostic_codec import pointer, quote_choices
from asof.study.fixed_evidence import load_plan
from asof.study import interpretation_interface as old
from asof.study import interpretation_generation as new

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ARCHIVE = ROOT / 'data/cache/r09-native-duration-simulation-20261028T033510Z'
STAMP = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUT = ROOT / 'data/cache' / ('r09-generation-preparation-' + STAMP)
journal = RunJournal(OUT, kind='build')
started = time.monotonic()
denied = []


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_new(path, value):
    with Path(path).open('xb') as stream:
        stream.write(canonical(value) + b'\n')
        stream.flush()
        os.fsync(stream.fileno())


def audit(event, args):
    if event in ('subprocess.Popen', 'os.system', 'socket.__new__', 'socket.connect',
                 'socket.getaddrinfo', 'ctypes.dlopen'):
        denied.append(event)
        raise RuntimeError('Pure preparation forbids child/network/native dispatch')
    if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
        path = os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
        if path.startswith('e:') or '\\data\\benchmark\\' in path or path.endswith('.gguf'):
            denied.append(dict(event=event, path=path))
            raise RuntimeError('Only archived development request data may be used')


sys.addaudithook(audit)
try:
    assert sha(ARCHIVE / 'receipt.json') == 'eb04ce0235a44084b9a3fc6205d86a44f8cfc0e58e64d18c7e78b300422307a4'
    archive = parse_json((ARCHIVE / 'receipt.json').read_bytes())
    request_rel = 'preparation/literal_case_overlap_then_id_v1/request.json'
    coverage_rel = 'preparation/literal_case_overlap_then_id_v1/coverage.json'
    for name in (request_rel, coverage_rel):
        proof = archive['artifacts'][name]
        assert sha(ARCHIVE / name) == proof['sha256']
        assert (ARCHIVE / name).stat().st_size == proof['bytes']
    real_request = parse_json((ARCHIVE / request_rel).read_bytes())
    coverage = parse_json((ARCHIVE / coverage_rel).read_bytes())
    baseline = parse_json((HERE / 'BEFORE-IMPLEMENTATION.json').read_bytes())
    plan = load_plan()
    cases = [(name, load_synthetic_request(name), False) for name in plan['fixture_names']]
    cases.append(('exposed-IL6R-RA', real_request, True))
    rows, old_unchanged = [], 0
    for case, request, real in cases:
        aliases = list(quote_choices(request))
        for arm, stages in (
            ('asof_interpretation', plan['asof_stages']),
            ('adapted_virtual_biotech_interpretation', plan['stage_order']),
        ):
            for index, stage in enumerate(stages):
                history = [dict(stage=p, source_ids=aliases) for p in stages[:index]]
                prior = old.prepare_payload(request, arm, index, history)
                if not real:
                    expected = next(row for row in baseline['old_v2_cells']
                                    if (row['fixture'], row['arm'], row['index']) == (case, arm, index))
                    assert prior['payload_sha256'] == expected['payload_sha256']
                    assert prior['quote_catalog_sha256'] == expected['quote_catalog_sha256']
                    old_unchanged += 1
                prepared = new.prepare_payload(request, arm, index, history)
                assert fingerprint(new.request_from_payload(prepared['payload'])) == fingerprint(request)
                assert not prepared['execution_authorized'] and prepared['native_conformance'] == 'unverified'
                assert prepared['acceptance_schema_sha256'] == fingerprint(prior['payload']['json_schema'])
                directory = OUT / case / arm / f'{index:02d}-{stage}'
                directory.mkdir(parents=True)
                write_new(directory / 'preparation.json', prepared)
                # Fixtures, not model predictions or expert interpretations.
                document = dict(answer_status='abstained', claims=[], unresolved=[],
                                abstention_reason='Offline preparation fixture; scientific interpretation is unreviewed.')
                validated = new.validate_output(request, prepared['payload'], document)
                assert validated['features'] == {} and validated['clinical_probability'] is None
                write_new(directory / 'response-fixture.json', validated)
                grammar = prepared['generation_grammar']
                row = dict(case=case, development_exposed=real, arm=arm, index=index, stage=stage,
                           request_sha256=fingerprint(request), payload_sha256=prepared['payload_sha256'],
                           grammar_sha256=grammar['grammar_sha256'], grammar_bytes=grammar['grammar_bytes'],
                           grammar_json_string_bytes=len(canonical(grammar['grammar'])),
                           prompt_bytes=len(prepared['payload']['prompt'].encode('utf-8')),
                           payload_bytes=len(canonical(prepared['payload'])),
                           old_payload_bytes=len(canonical(prior['payload'])),
                           quote_ids=len(grammar['quote_ids']), literal_report_ids=len(grammar['source_report_ids']),
                           preparation_file=str(directory / 'preparation.json'),
                           response_fixture_sha256=fingerprint(validated), native_conformance='unverified')
                rows.append(row)
                journal.append('pure_preparation_checked', **row)
    assert len(rows) == 18 and old_unchanged == 12 and not denied
    report = dict(schema_version=1, status='passed_retained_preparation_only', output=str(OUT),
                  helper_sha256=sha(__file__), records=rows, preparations=18, original_v2_fingerprints_unchanged=12,
                  real_preparations=6, synthetic_preparations=12,
                  coverage=dict(available=coverage['parent_observations_available'],
                                missing=coverage['missing_input_count'], basis=coverage['missing_count_basis'],
                                selected=coverage['selected_count'], absence_claim=False),
                  source_scope='Archived receipt-bound request; original raw lineage not re-audited in this helper',
                  history_scope='Hypothetical source-ID preparation histories; no new accepted model predecessors',
                  response_scope='Authored abstention fixtures, not generated scientific assessments',
                  native_calls=0, tokenizer_children=0, model_calls=0, provider_spend_usd=0,
                  native_conformance='unverified', scientific_validation='not_established', guards=denied,
                  elapsed_seconds_before_sealing=time.monotonic()-started)
    write_new(OUT / 'report.json', report)
    journal.append('pure_preparation_terminal', preparations=18, report_sha256=sha(OUT / 'report.json'))
    journal.close()
    events = read_chain(OUT / 'journal.jsonl')
    outputs = {str(path.relative_to(OUT)): dict(bytes=path.stat().st_size, sha256=sha(path))
               for path in OUT.rglob('*') if path.is_file()}
    write_new(OUT / 'receipt.json', dict(schema_version=1, kind='pure_preparation_fixture_inventory',
                                       outputs=outputs, journal_tip_sha256=events[-1]['sha256']))
    write_new(HERE / 'PREPARATION-QUALIFICATION.json', dict(report, receipt_sha256=sha(OUT / 'receipt.json')))
    print(json.dumps(dict(status=report['status'], preparations=18, original_v2_unchanged=12,
                         maximum_prompt_bytes=max(r['prompt_bytes'] for r in rows),
                         maximum_payload_bytes=max(r['payload_bytes'] for r in rows), output=str(OUT))))
except BaseException as error:
    try:
        journal.fail(error, 'pure-preparation')
    finally:
        write_new(OUT / 'failure.json', dict(status='failed', error_class=type(error).__name__,
                                           message=str(error), native_calls=0, model_calls=0, guards=denied))
    raise
finally:
    journal.close()
