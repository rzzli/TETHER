"""Read-only evidence/document checks; writes only this phase's final QA report."""
from pathlib import Path
import hashlib
import json
import re
from urllib.parse import unquote

from asof.journal import read_chain

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = ROOT / 'data/cache/r09-finite-converter-execution-20261028T043655Z'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


baseline = load(ROOT / 'data/cache/recovery-step9-duration-validation-20261028/code-validation.json')
assert len(baseline['source_pins']) == 324
assert all(sha(ROOT / name) == value for name, value in baseline['source_pins'].items())
# Hash-only protected checks: never decode or parse these two outcome payloads.
assert all(sha(ROOT / name) == value for name, value in baseline['protected_hashes'].items())
assert sha(ROOT / 'planning/review-assets/recovery-step9-native-duration-20261028/acceptance.json') == '27f33a36fd01d48b79e1492ad6b4b185a60e4bd662bb1ee0d955e5a284079cdc'
assert sha(RUN / 'receipt.json') == '73c3f2bede92d2f51238831dea8012e3e4d20a0dd9655002d9f51432bdefcaa4'
assert sha(RUN / 'seal-state.json') == '2d1d4eff84ec786907fba754eb46c5db610463384708b2a5ba23869708866ffe'
assert not (RUN / 'failure.json').exists()
receipt = load(RUN / 'receipt.json')
assert len(receipt['outputs']) == 48
for name, proof in receipt['outputs'].items():
    path = RUN / name
    assert path.is_relative_to(RUN) and path.is_file()
    assert sha(path) == proof['sha256'] and path.stat().st_size == proof['bytes']
events = read_chain(RUN / 'journal.jsonl')
assert len(events) == 14 and events[-1]['sha256'] == receipt['journal_tip_sha256']
review = load(HERE / 'RESULT-VERIFICATION.json')
assert review['status'] == 'verified_sealed_negative_converter_gate'
assert review['external_pin_entries_verified'] == 150
terminal = load(RUN / 'terminal-report.json')
assert terminal['status'] == 'closed_negative_conversion_incomplete_warning'
assert terminal['native_children'] == 2
assert terminal['model_calls'] == terminal['servers'] == terminal['vocabulary_loads'] == 0
assert terminal['guards']['denied'] == []

documents = [
    ROOT / 'README.md', ROOT / 'TODO.md', ROOT / 'docs/NATIVE_INTERPRETATION.md',
    ROOT / 'planning/Project Recovery and Evaluation Plan 2026-10-26.md',
    ROOT / 'planning/Recovery Status and Next Gates 2026-10-26.md',
    ROOT / 'planning/Project Progress Reassessments.md',
    ROOT / 'planning/Project Progress Reassessment 2026-10-28 - R09 Converter.md',
    ROOT / 'memory/MEMORY.md', ROOT / 'memory/project-goals.md',
    ROOT / 'memory/research-log-2026-10-28-r09-converter.md',
    HERE / 'DISPOSITION.md', HERE / 'RESULT-REVIEW.md',
    HERE / 'CONTRACT-CORRECTION-OPTIONS.md', HERE / 'FINITE-CONVERTER-READINESS-v3.md',
]
links = 0
for doc in documents:
    text = doc.read_text(encoding='utf-8')
    for match in re.finditer(r'\[[^\]]+\]\((?:<([^>]+)>|([^\)]+))\)', text):
        target = (match.group(1) or match.group(2)).strip()
        if re.match(r'^(?:https?://|mailto:|#)', target):
            continue
        target = re.sub(r':\d+(?:-\d+)?$', '', unquote(target.split('#')[0]))
        path = Path(target)
        if not path.is_absolute():
            path = doc.parent / path
        assert path.exists(), (str(doc), target)
        links += 1
assessment = documents[6].read_text(encoding='utf-8')
assert all(f'R{i:02}' in assessment for i in range(1, 17))
assert all(f'HR{i}' in assessment for i in range(1, 5))
assert load(HERE / 'RESULT.json')['status'] == 'closed_negative_conversion_incomplete_warning'
evidence_names = ['RESULT.json', 'RESULT-VERIFICATION.json', 'RESULT-REVIEW-QA.json',
                  'FINITE-CONVERTER-EXECUTION-PROTOCOL-v3.json', 'FINITE-CONVERTER-ROOT-DECISION-v3.json']
report = dict(schema_version=1, status='passed', native_gate='sealed_negative',
              source_pins_unchanged=324, protected_hashes_only_unchanged=2,
              receipt_outputs_verified=48, journal_events=14,
              independent_external_pins_verified=150, focused_harness_regressions=3,
              native_children=2, model_calls=0, vocabulary_loads=0, servers=0,
              accepted_version='0.3.10', previous_full_tests=1737, full_tests_rerun=False,
              documents_checked=len(documents), local_links_checked=links,
              document_hashes={str(p.relative_to(ROOT)): sha(p) for p in documents},
              evidence_hashes={name: sha(HERE / name) for name in evidence_names},
              human_reviews='pending', entire_R09_complete=False)
with (HERE / 'FINAL-CHECK.json').open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
    stream.write('\n')
print(json.dumps({k: v for k, v in report.items() if k not in ('document_hashes', 'evidence_hashes')}))
