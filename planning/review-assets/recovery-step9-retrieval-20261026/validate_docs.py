"""Check current documentation links and retained planning JSON without data reads."""
import json
from pathlib import Path
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
names = ('README.md','TODO.md','CHANGELOG.md','docs/STUDY_RUNTIME.md',
         'docs/SOURCE_AND_TOKEN_PREPARATION.md','docs/FIXED_EVIDENCE_COMPARISON.md',
         'docs/BOUNDED_RETRIEVAL.md',
         'planning/Project Recovery and Evaluation Plan 2026-10-26.md',
         'planning/Recovery Status and Next Gates 2026-10-26.md',
         'memory/MEMORY.md','memory/project-goals.md',
         'memory/research-log-2026-10-26-r09-retrieval.md')
missing, links, parsed = [], 0, 0
for name in (*names, str((HERE/'CLOSEOUT.md').relative_to(ROOT))):
    path = ROOT/name
    for target in re.findall(r'\[[^\]]+\]\((<[^>]+>|[^)]+)\)', path.read_text(encoding='utf-8-sig')):
        target = unquote(target.strip('<>').split('#')[0])
        if not target or target.startswith(('https:','http:','app:','plugin:','codex:','mailto:')):
            continue
        links += 1
        destination = Path(target) if Path(target).is_absolute() else path.parent/target
        if not destination.exists():
            missing.append(dict(source=name, target=target))
for folder in (HERE, HERE.parent/'recovery-step9-four-arm-20261026'):
    for path in folder.rglob('*.json'):
        json.loads(path.read_bytes())
        parsed += 1
report = dict(schema_version=1, status='passed' if not missing else 'failed',
              documents=len(names)+1, local_links=links, planning_json_parsed=parsed,
              missing=missing, data_payloads_read=False)
with (HERE/'DOCUMENTATION-CHECK.json').open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
print(json.dumps(report))
assert not missing
