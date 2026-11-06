"""Post hoc descriptive join; no inference, references or causal interpretation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EVAL = ROOT / 'data/benchmark/labbench/evaluation-20261106T011303Z-attempt01'
SEAL = '118711b7e7552750e441380b7abf8f60b68096ae98ef3163cf96754e7423fa6f'
DOI = ROOT / 'planning/review-assets/tether-labbench-20261106/operational-audit/SOURCE-DOI-02.json'
DOI_SHA = 'd8bba9effebaf5d1292ea61a57b61501f8f67ed43e1bccd4d9e371a42fcf11d7'


def read(path, expected):
    raw = path.read_bytes()
    assert len(raw) < 8 * 1024**2 and hashlib.sha256(raw).hexdigest() == expected
    return json.loads(raw)


def main():
    seal = read(EVAL/'SEALED.json', SEAL)
    evaluation = read(EVAL/'evaluation.json', seal['outputs']['evaluation.json']['sha256'])
    report = read(EVAL/'REPORT.json', seal['outputs']['REPORT.json']['sha256'])
    sources = read(DOI, DOI_SHA)
    by_id = {row['id']: row for row in sources['cases']}
    cases = evaluation['case_results']
    assert len(by_id) == len(cases) == len({row['id'] for row in cases}) == 199
    assert set(by_id) == {row['id'] for row in cases}
    cells = {key: dict(scheduled=0, correct=0, incorrect_substantive=0, unsure=0,
                      operational_failure=0, substantive=0) for key in ('annotated_doi_hit', 'no_annotated_doi_hit')}
    for row in cases:
        source = by_id[row['id']]
        assert source['annotated_doi_count'] > 0
        cell = cells['annotated_doi_hit' if source['selected_nonconflicting_hit_count'] else 'no_annotated_doi_hit']
        cell['scheduled'] += 1
        cell['correct'] += row['raw_correct']
        cell['substantive'] += row['raw_answered']
        cell['incorrect_substantive'] += row['raw_answered'] and not row['raw_correct']
        cell['unsure'] += row['native_unsure']
        cell['operational_failure'] += row['producer_status'] != 'produced'
    assert sum(c['correct'] for c in cells.values()) == report['counts']['raw_correct']
    assert sum(c['substantive'] for c in cells.values()) == report['counts']['raw_answered']
    assert cells['annotated_doi_hit']['scheduled'] == sources['metrics']['selected_nonconflicting']['hit_questions']
    for cell in cells.values():
        assert sum(cell[k] for k in ('correct','incorrect_substantive','unsure','operational_failure')) == cell['scheduled']
    result = dict(status='pass', analysis='posthoc_descriptive_source_identity_answer_contingency',
                  evaluation_seal_sha256=SEAL, source_audit_sha256=DOI_SHA, cells=cells,
                  code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  interpretation='Unadjusted association; annotated paper identity is not decisive-passage coverage or entailment. Different groups may differ in question difficulty, access and other causes. No causal effect, independence, calibration or new model experiment claimed.',
                  new_model_calls=0, new_network_requests=0, reopened_original_references=False)
    output = Path(__file__).with_name('SOURCE-ANSWER-CONTINGENCY-01.json')
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
