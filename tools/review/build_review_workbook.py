"""Create a portable offline expert workbook from hash-verified unanswered forms."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import zipfile

from tether_engine.maintenance import write_new_json
from tether_engine.serde import ContractError, read_json, safe_child, sha256_file

LABELS = {
    'EFO_0003060': 'Non-small cell lung carcinoma', 'EFO_0000729': 'Ulcerative colitis',
    'EFO_0000305': 'Breast carcinoma', 'EFO_0004911': 'Familial hypercholesterolemia',
    'EFO_0000685': 'Rheumatoid arthritis', 'MONDO_0009061': 'Cystic fibrosis',
    'MONDO_0005148': 'Type 2 diabetes mellitus', 'EFO_0005762': 'Neuropathic pain',
}


def build(project: Path, source: Path, output: Path):
    project, source, output = project.resolve(), source.resolve(), output.resolve()
    area = project/'data/benchmark/gold_evidence'
    if not source.is_relative_to(area) or not output.is_relative_to(area):
        raise ContractError('Workbooks and review inputs must remain evaluator-only')
    if output.exists():
        raise ContractError('Workbook exists; use a fresh output directory')
    manifest = read_json(source/'manifest.json')
    if manifest['role'] != 'evaluation_only' or manifest['status'] != 'prepared_unreviewed':
        raise ContractError('Expected an unanswered evaluator-only package')
    forms = []
    for entry in manifest['files']:
        path = safe_child(source, entry['path'])
        if sha256_file(path) != entry['sha256']:
            raise ContractError('Review form hash mismatch')
        form = read_json(path)
        if form['role'] != 'evaluation_only' or form['status'] != 'unreviewed':
            raise ContractError('Expected unreviewed form')
        if any(v is not None for v in form['case_assessment'].values()) or form['reviewer'] is not None:
            raise ContractError('Refuse to publish prefilled judgments')
        for item in form['claims']:
            if any(v is not None for v in item['assessment'].values()):
                raise ContractError('Refuse to publish prefilled claim judgments')
            # Retain relative original locators, but omit machine-specific source paths.
            item['original_reference'].pop('source_path', None)
        case = form['case']
        form['display'] = {'symbol': case['case_id'].split('-')[0].upper(),
                           'indication': LABELS[case['hypothesis']['indication_id']]}
        forms.append(form)
    if len(forms) != 10 or sum(len(form['claims']) for form in forms) != 20:
        raise ContractError('Expected ten cases and twenty selected claims')
    packet = {'schema_version': 1, 'package_id': sha256_file(source/'manifest.json'),
              'role': 'evaluation_only', 'forms': forms}
    template = Path(__file__).with_name('review_workbook.html').read_text(encoding='utf-8')
    serialized = json.dumps(packet, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
    rendered = template.replace('__REVIEW_DATA__', serialized)
    output.mkdir(parents=True, exist_ok=False)
    (output/'Review.html').write_text(rendered, encoding='utf-8')
    guide = '''EXPERT REVIEW — START HERE

1. Open Review.html in Chrome, Edge, Firefox or Safari. No installation or account is needed.
2. Enter your name or reviewer ID. Read the short guide at the top.
3. Review one case at a time. Each has two evidence cards and plain-language questions.
4. Choose “Cannot assess” when the supplied evidence is insufficient. Explain your judgments.
5. Click “Export answers” to save your work and send that file to the study coordinator.
   “Readable summary” creates a text report; “Print” supports paper review or Save as PDF.

Drafts are saved in this browser when storage is available. Export a backup before closing
or moving the HTML file. To resume on another machine, open Review.html and choose “Import draft”.
Each reviewer should start from a fresh copy. Do not share another reviewer's completed answers
before independent review. Use “Start a new review” to clear this browser's draft after exporting it.

The workbook works offline. Publication/reference links need internet and may show current
records, not the pinned source version. No review answers are uploaded automatically.
Keep exported answers in evaluator-only storage. The workbook includes selected normalized
evidence, not full articles or bulk source datasets. Source-specific terms still apply.

This is an unblinded development review of 20 purposively selected claims from ten hypotheses.
It is not a representative benchmark or a clinical prediction assessment. The questions concern
the supplied excerpt; consult additional evidence if needed and record it in your notes.
Completed answers require later adjudication; nothing is pre-rated.
'''
    (output/'START_HERE.txt').write_text(guide, encoding='utf-8')
    with zipfile.ZipFile(output/'Expert-review.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for filename in ('Review.html', 'START_HERE.txt'):
            archive.write(output/filename, filename)
    write_new_json(output/'manifest.json', {'schema_version': 1, 'role': 'evaluation_only',
        'status': 'prepared_unreviewed', 'source_manifest_sha256': packet['package_id'],
        'cases': 10, 'claims': 20, 'scientific_adjudication': 'not_run',
        'outputs': {name: sha256_file(output/name) for name in ('Review.html', 'START_HERE.txt', 'Expert-review.zip')}})
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(build(args.project_root, args.source, args.output))
