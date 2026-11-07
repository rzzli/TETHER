"""Source-inclusive SC03 input preparation; no model dispatch or native scoring."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]

from experiments.scifact_comparison.inputs import CONDITIONS, build_primary, build_condition, encoded, need
from experiments.scifact.data_views import verify_preparation, load_product
from experiments.scifact.tether_adapter import authorize_products
from tether_engine.serde import encode

PREPARATION_SHA = 'cb32f1384c49b66b912a62120abd7137a8a19b303f3ad052f035f21779c131f8'
BASELINE_SHA = '3a997165aac2f0a85a93890f5e10a66d8117563e380e98f892dd3cb8a93f8968'
SC02_SHA = 'bb21dfe9c08f01796457dcf634dcc9a9bc9082c9aec711e765d1b71b5a974ef4'


def pin(path):
    path = Path(path)
    digest = hashlib.sha256()
    count = 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
            count += len(block)
    return dict(path=str(path.resolve()), bytes=count, sha256=digest.hexdigest())


def read(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(64*1024*1024+1)
    need(len(raw) <= 64*1024*1024, 'Input control exceeds 64 MiB')
    return json.loads(raw)


def write(path, value):
    with path.open('xb') as stream:
        stream.write(encoded(value) + b'\n')


def write_rows(path, rows):
    with path.open('xb') as stream:
        for row in rows:
            stream.write(encoded(row) + b'\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    need(output.is_relative_to(ROOT) and output != ROOT, 'Output must be in workspace')
    output.mkdir(parents=True, exist_ok=False)
    write(output/'STARTED.json', dict(started_utc=datetime.now(timezone.utc).isoformat(), model_execution=False))
    try:
        prepared = ROOT/'data/benchmark/scifact/preparation-20261105-attempt03'
        baseline = ROOT/'data/benchmark/scifact/native-20261105T234805Z-attempt01'
        accepted = ROOT/'planning/review-assets/tether-semantic-20261106/sc02-acceptance-attempt01/ROOT-ACCEPTANCE.json'
        need(pin(accepted)['sha256'] == SC02_SHA and read(accepted)['status'] == 'PASS', 'SC02 gate not accepted')
        need(pin(baseline/'RECEIPT.json')['sha256'] == BASELINE_SHA, 'Baseline external anchor differs')
        receipt = read(baseline/'RECEIPT.json')
        parents = [pin(accepted), pin(baseline/'RECEIPT.json'), pin(prepared/'manifest.json')]
        for relative in ('DEV-FROZEN.json', 'check-inputs/candidates.json'):
            proof = pin(baseline/relative)
            need(proof['sha256'] == receipt['outputs'][relative], 'Baseline output binding differs: ' + relative)
            parents.append(proof)
        manifest = verify_preparation(prepared, PREPARATION_SHA)
        authorize_products(manifest, ['corpus', 'queries_dev'], 'predict')
        corpus = encode(load_product(prepared, manifest, 'corpus', 'predict'))
        queries = encode(load_product(prepared, manifest, 'queries_dev', 'predict'))
        schedule = read(baseline/'DEV-FROZEN.json')['dev_schedule']
        need(len(schedule) == 300 and len(corpus) == 5183, 'Actual release denominator differs')
        primary, retrieved = build_primary(queries, corpus, read(baseline/'check-inputs/candidates.json'), schedule)
        # Freeze the primary request bytes before loading diagnostic references.
        primary_dir = output/'primary'
        primary_dir.mkdir()
        requests, lineage = build_condition(primary, 'primary')
        write_rows(primary_dir/'requests.jsonl', requests)
        write_rows(primary_dir/'lineage.jsonl', lineage)
        write_rows(output/'retrieval.jsonl', retrieved)
        conditions = {}
        def condition_record(name, requests, lineages):
            folder = output/name
            documents = [d for r in lineages for d in r['documents']]
            return dict(requests=pin(folder/'requests.jsonl'), lineage=pin(folder/'lineage.jsonl'),
                claims=len(requests), scheduled_pairs=len(documents),
                ready_pairs=sum(d['disposition'] == 'ready' for d in documents),
                unavailable_pairs=sum(d['disposition'] == 'input_unavailable' for d in documents),
                annotated_pairs=sum(d['annotated_rationale_applicable'] is True for d in documents),
                worker_fields=['id', 'claim', 'documents'], references_visible_to_worker=False)
        conditions['primary'] = condition_record('primary', requests, lineage)
        authorize_products(manifest, ['references_dev'], 'evaluate')
        references = encode(load_product(prepared, manifest, 'references_dev', 'evaluate'))
        for name in CONDITIONS[1:]:
            folder = output/name
            folder.mkdir()
            request_rows, lineage_rows = build_condition(primary, name,
                references=references if name in ('rationale_only', 'evidence_removal') else None)
            write_rows(folder/'requests.jsonl', request_rows)
            write_rows(folder/'lineage.jsonl', lineage_rows)
            conditions[name] = condition_record(name, request_rows, lineage_rows)
        for key in ('corpus', 'queries_dev', 'references_dev'):
            parents.append(pin(prepared/manifest['products'][key]['path']))
        for key in ('path', 'receipt_path'):
            parents.append(pin(manifest['archive'][key]))
        sources = [pin(Path(__file__)), pin(Path(__file__).with_name('inputs.py'))]
        sources += [pin(ROOT/p) for p in ('experiments/scifact/data_views.py', 'experiments/scifact/split.py',
                    'experiments/scifact/tether_adapter.py', 'src/tether_engine/serde.py')]
        protocol = ROOT/'planning/TETHER SciFact Full Context Protocol 2026-11-06.md'
        with (output/'PROTOCOL.md').open('xb') as stream:
            stream.write(protocol.read_bytes())
        result = dict(schema_version=1, kind='sc03_prepared_inputs', status='prepared', schedule=schedule,
            conditions=conditions, retrieval=pin(output/'retrieval.jsonl'), source_parents=parents,
            preparation_manifest_sha256=PREPARATION_SHA, baseline_receipt_sha256=BASELINE_SHA,
            source_pins=sources, protocol=pin(output/'PROTOCOL.md'), model_execution=False,
            scope='Reference-separated primary inputs and explicitly reference-informed diagnostics; no performance result.')
        write(output/'MANIFEST.json', result)
        write(output/'RECEIPT.json', dict(status='PASS', manifest=pin(output/'MANIFEST.json')))
        print(json.dumps(dict(status='PASS', manifest=pin(output/'MANIFEST.json'),
              conditions={k:{f:v[f] for f in ('claims','scheduled_pairs','ready_pairs','unavailable_pairs','annotated_pairs')}
                          for k,v in conditions.items()})))
    except BaseException as error:
        write(output/'FAILED.json', dict(status='FAIL', error_type=type(error).__name__, error=str(error)))
        raise


if __name__ == '__main__':
    main()
