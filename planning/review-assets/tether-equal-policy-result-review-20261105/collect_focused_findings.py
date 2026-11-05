"""Extract retained EP057/EP075/EP077 results without rescoring or editing them."""
import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
CORPUS = PROJECT / 'data/benchmark/tether-equal-policy-20261102-attempt03'


def read(path):
    return json.loads(path.read_bytes())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    analysis = read(CORPUS / 'ANALYSIS.json')
    case_ids = ('EP057', 'EP075', 'EP077')
    schedule = read(CORPUS / 'case-preparation-schedule.json')['cases']
    records = []
    for case in case_ids:
        for repetition in (1, 2, 3):
            for implementation in ('tether', 'independent', 'hash_schema', 'reject_all'):
                path = CORPUS / 'comparison' / f'{case}-r{repetition}-{implementation}' / 'RESULT.json'
                value = read(path)
                projected = next(row for row in analysis['rows'] if row['cell'] == path.parent.name)
                records.append(dict(path=path.relative_to(PROJECT).as_posix(), sha256=sha(path),
                    control_id=case, repetition=repetition, implementation=implementation,
                    disposition=value['disposition'], result=value['result'],
                    primary_analysis=projected))
    report = dict(schema_version=1, scope='Post-hoc focused source audit; unchanged frozen scores',
        corpus=str(CORPUS), freeze_sha256=sha(CORPUS / 'FROZEN.json'),
        primary_analysis_sha256=sha(CORPUS / 'ANALYSIS.json'),
        script_sha256=sha(Path(__file__)),
        cases=[row for row in schedule if row['control_id'] in case_ids],
        records=records,
        hash_schema_error_cells=[row['cell'] for row in analysis['rows']
            if row['implementation'] == 'hash_schema' and row['observed_decision'] == 'error'])
    output = Path(__file__).with_name('FOCUSED-RESULT-EVIDENCE.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
        stream.write('\n')
    print(json.dumps(dict(path=str(output), sha256=sha(output), retained_cells=len(records),
        hash_schema_error_cells=report['hash_schema_error_cells'])))


if __name__ == '__main__':
    main()
