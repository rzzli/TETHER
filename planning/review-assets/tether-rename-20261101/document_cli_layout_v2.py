"""Document the new CLI-only outer presentation; preserve v1 review evidence."""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def once(text,old,new):
 if text.count(old)!=1:raise ValueError('Expected unique text: '+old[:60])
 return text.replace(old,new,1)
def main():
 prior=json.loads((HERE/'ACTIVE-DOCS-BRANDING-CHANGES-v1.json').read_text(encoding='utf-8'))
 changes=[]
 def edit(rel,fn):
  p=ROOT/rel;before=p.read_bytes();nl='\r\n' if b'\r\n' in before else '\n';text=before.decode().replace('\r\n','\n')
  after=fn(text).replace('\n',nl).encode()
  if before!=after:p.write_bytes(after);changes.append({'path':rel,'before_sha256':sha(before),'after_sha256':sha(after),'before_bytes':len(before),'after_bytes':len(after)})
 def readme(text):
  text=once(text,'The `tether.*` import namespace exposes the same legacy objects as `asof.*`.',
   'The public API aliases under `tether.*` expose the same legacy objects as `asof.*`\nwith their existing output layouts. They do not automatically create branded\nouter artifacts. The separate `tether._presentation` layer implements that CLI\npresentation for `demo` and `run`.')
  old='''Choose a new output directory for each execution. `dossier.md` is the readable report;
`ledger.json`, `features.json`, `prediction.json`, `inputs.json`, `run.json`,
`trace.jsonl`, `journal.jsonl` and `receipt.json` retain evidence and accounting.
CLI runs also archive `request.json`. Save the printed receipt hash independently:
'''
  new='''## TETHER CLI run layout

Choose an existing parent and a new output directory for each `tether demo` or
`tether run` execution. These commands reserve `OUT` and create a separately
sealed outer presentation:

```text
OUT/
  dossier.md
  tether-manifest.json
  tether-receipt.json
  attempt/journal.jsonl
  engine-stdout.txt
  engine-stderr.txt
  engine/
    dossier.md
    receipt.json
    journal.jsonl
    ...
```

The outer `dossier.md` changes only the first engine dossier header to TETHER;
the rest of its bytes match `engine/dossier.md`. The manifest binds this
projection, all engine files and the launcher code/version. The outer attempt
journal closes before `tether-receipt.json` is published. The unchanged engine
directory contains `ledger.json`, `features.json`, `prediction.json`, `inputs.json`,
`run.json`, `trace.jsonl`, its journal/receipt and the CLI `request.json`.
Save the printed **outer** receipt hash independently:
'''
  text=once(text,old,new)
  marker='''Verification reports byte integrity, semantic consistency, source binding and scientific
validity separately.'''
  replacement='''`tether verify --run-dir OUT` checks the outer seal, launcher, inventory, journal
and exact dossier projection, then performs source-inclusive engine verification.
`tether inspect-run --run-dir OUT` reads retained outer and engine attempts without
retrying. Outer verification rejects `--outputs-only`. For a legacy-only check,
`asof verify --run-dir OUT/engine` remains valid; save/use the separate engine
receipt hash for that check. `inspect-source`, `build-snapshot` and `evaluate`
continue to delegate with their existing engine output layouts.

Failures or interruptions preserve `tether-failure.json`, the outer attempt and
any inner journal. Inspect the failed attempt before choosing a fresh output;
verification and inspection never automatically repeat execution.

Verification reports byte integrity, semantic consistency, source binding and scientific
validity separately.'''
  return once(text,marker,replacement)
 edit('README.md',readme)
 addition=' Direct API aliases preserve legacy outputs; only the separate `tether._presentation` CLI layer wraps `demo`/`run` in the [TETHER run layout](../README.md#tether-cli-run-layout). Delegated source inspection, snapshot construction and evaluation keep their engine layouts.'
 end='Historical version/arm names, module commands, source paths and wire IDs below remain unchanged; the rename does not reactivate retired study or expert-review branches.'
 for row in prior['changed_files']:
  rel=row['path']
  if not rel.startswith('docs/'):continue
  def guide(text):
   text=once(text,end,end+addition)
   if rel=='docs/FRAMEWORK.md':
    text=once(text,'The default CLI behavior and budget caps are unchanged.',
     'The default engine behavior and budget caps are unchanged; the TETHER CLI adds\nits separately sealed outer presentation for `demo` and `run`.')
    text=once(text,'## Durable execution and verification\n',
     '## Durable execution and verification\n\nThe engine details below apply inside `OUT/engine` for a TETHER CLI run, or at\nthe original output root for legacy API/module commands. TETHER seals the outer\npresentation separately; its source-inclusive verification rejects `--outputs-only`.\n')
    text=text.replace('Source binding | Complete admitted artifact/ancestor proofs and originals agree; `--outputs-only` checks archived fingerprints instead |',
     'Source binding | Complete admitted artifact/ancestor proofs and originals agree; legacy engine `--outputs-only` checks archived fingerprints instead (the TETHER outer verifier rejects it) |')
   if rel=='docs/V02_MIGRATION.md':
    text=once(text,'## Backends, replay and durable outputs\n',
     '## Backends, replay and durable outputs\n\nThe receipt and journal details below describe the unchanged engine artifacts.\nFor `tether run --output OUT` they live in `OUT/engine`; the outer `dossier.md`,\n`tether-manifest.json`, `tether-receipt.json` and `attempt/journal.jsonl` form a\nseparate presentation seal. Direct API aliases preserve the legacy output root.\n')
    text=once(text,'independently. Source-inclusive verification binds current originals; `--outputs-only`\nexplicitly supplies the weaker archived-fingerprint check.',
     'independently. Source-inclusive engine verification binds current originals; legacy\n`--outputs-only` explicitly supplies the weaker archived-fingerprint check. The\nTETHER outer verifier requires source-inclusive verification and rejects that flag.')
   return text
  edit(rel,guide)
 report={'schema_version':1,'method':'tether.active_cli_layout_documentation.v2','parent_inventory_sha256':sha((HERE/'ACTIVE-DOCS-BRANDING-CHANGES-v1.json').read_bytes()),'changed_files':changes,
  'contract_sources':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p.read_bytes()) for p in [ROOT/'packages/tether/src/tether/_cli.py',ROOT/'packages/tether/src/tether/_presentation.py',ROOT/'packages/tether/README.md']},
  'scope':'Only README and 20 previously owned active guides. No paper/memory/TODO/planning status, data/catalog, production code or old evidence changes.',
  'new_model_calls':0,'new_network_calls':0,'scientific_validation':'not_established'}
 with (HERE/'ACTIVE-DOCS-CLI-LAYOUT-CHANGES-v2.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
 print(json.dumps({'changed_files':len(changes),'contract_sources':report['contract_sources']},indent=2))
if __name__=='__main__':main()
