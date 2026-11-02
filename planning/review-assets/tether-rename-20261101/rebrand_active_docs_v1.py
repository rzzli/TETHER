"""Apply the authorized documentation/display rename without changing engine IDs."""
from pathlib import Path
import hashlib,json,os,re

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
EXCLUDED={
 'Expert Review Coordinator Guide 2026-10-26.md':'expert instrument/coordinator archive',
 'Independent Project Review 2026-10-26.md':'dated original review',
 'Opus_20261026T050236Z_review.md':'dated original model review',
 'T6_PRIMARY_REFERENCE.md':'dated primary-proof checkpoint',
 'T6_CONTEXTUAL_AUDIT.md':'research-pinned legacy contextual contract',
}
EXPANSION='Target Evidence Tracking Harness for Evaluation and Reproducibility'
def sha(b):return hashlib.sha256(b).hexdigest()
def write_new(path,raw):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb') as stream:stream.write(raw)
def replace_once(text,old,new):
 if text.count(old)!=1:raise ValueError('Expected exactly one document fragment: '+old[:70])
 return text.replace(old,new,1)
def diff(a,b,path='$'):
 if type(a)!=type(b):return [path]
 if isinstance(a,dict):
  if a.keys()!=b.keys():return [path+' keys']
  return sum((diff(a[k],b[k],path+'.'+k) for k in a),[])
 if isinstance(a,list):
  if len(a)!=len(b):return [path+' length']
  return sum((diff(x,y,path+f'[{i}]') for i,(x,y) in enumerate(zip(a,b))),[])
 return [] if a==b else [path]

def main():
 inventory=[]
 def edit(rel,transform):
  path=ROOT/rel;before=path.read_bytes();newline='\r\n' if b'\r\n' in before else '\n'
  text=before.decode('utf-8').replace('\r\n','\n');changed=transform(text)
  after=changed.replace('\n',newline).encode('utf-8')
  if after!=before:
   path.write_bytes(after);inventory.append({'path':rel,'before_sha256':sha(before),'after_sha256':sha(after),'before_bytes':len(before),'after_bytes':len(after)})

 catalog=ROOT/'data/catalog/sources.json';old=catalog.read_bytes()
 archive=ROOT/'data/catalog/history/sources-pre-tether-20261101.json'
 write_new(archive,old)
 olddoc=json.loads(old);new=old
 for prior,current in [
  ('AsOf dataset requirements and acquisition inventory','TETHER dataset requirements and acquisition inventory'),
  ('AsOf project-generated assets','TETHER project-generated assets')]:
  if new.count(prior.encode())!=1:raise ValueError('Catalog display occurrence mismatch')
  new=new.replace(prior.encode(),current.encode(),1)
 newdoc=json.loads(new);changed=diff(olddoc,newdoc)
 project_index=next(i for i,p in enumerate(olddoc['providers']) if p.get('name')=='AsOf project-generated assets')
 allowed=['$.title',f'$.providers[{project_index}].name']
 if sorted(changed)!=sorted(allowed):raise ValueError('Noncosmetic catalog change')
 lock=catalog.with_name(catalog.name+'.lock')
 with lock.open('x') as stream:stream.write(json.dumps({'pid':os.getpid(),'operation':'authorized_tether_display_rename'}))
 try:
  if catalog.read_bytes()!=old:raise ValueError('Catalog changed after capture')
  catalog.write_bytes(new)
 finally:lock.unlink()
 inventory.append({'path':'data/catalog/sources.json','before_sha256':sha(old),'after_sha256':sha(new),'before_bytes':len(old),'after_bytes':len(new)})

 compatibility=(
  f'TETHER ({EXPANSION}) is the current project name. '
  'The `tether-target-agents` 0.4.0 package in `packages/tether` supplies the '
  '`tether` CLI and import namespace over the frozen AsOf 0.3.11 engine. '
  'See [installation and compatibility](../README.md#installation-and-compatibility). '
  'Historical version/arm names, module commands, source paths and wire IDs below '
  'remain unchanged; the rename does not reactivate retired study or expert-review branches.'
 )
 for path in sorted((ROOT/'docs').glob('*.md')):
  if path.name in EXCLUDED:continue
  def guide(text):
   text=text.replace('title: AsOf Framework Implementation','title: TETHER Framework Implementation').replace('title: AsOf v0.2 Migration','title: TETHER v1-to-v2 Contract Migration')
   text=text.replace('  - asof\n','  - tether\n')
   match=re.search(r'^# (.+)$',text,re.M)
   if not match:raise ValueError('Missing guide title')
   title=match.group(1)
   if title=='AsOf framework v0.2':title='framework: legacy v2 contracts'
   title='TETHER — '+title
   text=text[:match.start()]+f'# {title}\n\n{compatibility}'+text[match.end():]
   text=text.replace('uv sync --python 3.11','uv sync --project packages/tether --python 3.11')
   text=text.replace('uv run --no-sync asof ','uv run --project packages/tether --no-sync tether ')
   if path.name=='FRAMEWORK.md':
    text=text.replace('AsOf follows [[AsOf Feasibility Analysis and Peer Survey]]:', 'TETHER follows the retained [[AsOf Feasibility Analysis and Peer Survey]]:')
   return text
  edit(path.relative_to(ROOT).as_posix(),guide)

 def readme(text):
  text=replace_once(text,'# AsOf target-evaluation agents','# TETHER\n\n**'+EXPANSION+'**')
  text=replace_once(text,'AsOf turns dated evidence','TETHER turns dated evidence')
  text=replace_once(text,'**Current software: 0.3.11, with v2 execution contracts.**',
   '**Current distribution: `tether-target-agents` 0.4.0 in `packages/tether`, over the frozen AsOf 0.3.11 engine and v2 execution contracts.**')
  text=replace_once(text,'acceptance is retained with its matching historical code. Final local gates at',
   'acceptance is retained with its matching historical code. The following local gates describe the retained engine before the TETHER rename; rename-specific checks are recorded separately. Final local gates at')
  section='''## Installation and compatibility

TETHER is the current project and CLI name. Install the canonical local package
from the repository root with `uv sync --project packages/tether --python 3.11`
(add `--extra ingest` for the pinned optional Parquet dependency), then use
`uv run --project packages/tether --no-sync tether ...`.

The `tether.*` import namespace exposes the same legacy objects as `asof.*`.
The frozen `src/asof/` engine, legacy `asof` command, module entry points,
distribution IDs in old wheels, schemas, dataset IDs and recorded paths remain
available for compatibility. Existing receipts, READY authorities and scientific
results keep their original bytes and names. The earlier AsOf paper/release
artifacts are historical versions; the rename alone makes no new study or
qualification claim. The current [catalog and its preserved predecessor](data/catalog/README.md)
distinguish display names from committed source identities.

'''
  text=replace_once(text,'## Run the offline demonstration\n',section+'## Run the offline demonstration\n')
  text=text.replace('uv sync --python 3.11','uv sync --project packages/tether --python 3.11')
  text=text.replace('uv run --no-sync asof ','uv run --project packages/tether --no-sync tether ')
  text=text.replace('uv run --no-sync python -m unittest discover -s tests -v\n','')
  text=replace_once(text,'For the shared local/CI validation command, use',
   'The legacy engine checkout retains its separate root environment (`uv sync --python 3.11`, optionally `--extra ingest`). For its shared local/CI validation command, use')
  text=replace_once(text,'| `src/asof/` | Immutable contracts, provenance, workflow, ingestion and CLI |',
   '| `packages/tether/` | Canonical TETHER distribution, CLI and compatible import namespace |\n| `src/asof/` | Frozen AsOf engine: contracts, provenance, workflow, ingestion and CLI |')
  return text
 edit('README.md',readme)

 current='''**Current TETHER checkpoint, 1 November 2026:** the bounded source-reporting
study, P09 installed Windows reconstruction and P10b local working packet are
complete within their declared technical scopes. The retained P09 run reproduces
38 output hashes and 90 policy decisions from 137 complete originals; the separate
source audit passes 6,862 checks. The 53-member P10b packet repeats byte-for-byte
and passes 200 independent archive checks. Owner declarations and final author
acceptance remain deferred, so P08/P10 and submission readiness remain incomplete.
No public deposit, current hosted-CI result or new scientific validation is claimed.
See the [current local-package assessment](<../planning/Project Progress Reassessment 2026-11-01 - Local Preprint Package.md>).
The rename changes no collection status, original, receipt, dataset role or study
selection. Earlier dated acquisition and development checkpoints below retain
their original scope.
'''
 def datareadme(text):
  text=text.replace('title: AsOf Data Workspace','title: TETHER Data Workspace').replace('# AsOf data workspace','# TETHER data workspace').replace('  - asof\n','  - tether\n')
  text=text.replace('updated: 2026-10-31','updated: 2026-11-01',1)
  text=replace_once(text,'# TETHER data workspace\n','# TETHER data workspace\n\n'+current+'\n'+
   f'TETHER means {EXPANSION}. The [catalog compatibility note](catalog/README.md) preserves the pre-rename master catalog and explains legacy IDs.\n')
  text=text.replace('P03 now enforces source/receipt/role/lineage rules for the new typed-reporting references; P04 must build independent agent-visible packets, never consume evaluator references or descendants.',
   'The retained source-reporting path enforces source/receipt/role/lineage rules; generation packets never consume evaluator references or descendants.')
  text=text.replace('Current implementation: [P03 source-fact evaluator and P04 prerequisites]', 'Retained P03 development checkpoint: [source-fact evaluator and P04 prerequisites]',1)
  return text
 edit('data/README.md',datareadme)
 def dataplan(text):
  text=text.replace('title: AsOf Full Data Requirements and Acquisition Plan','title: TETHER Full Data Requirements and Acquisition Plan').replace('# AsOf full data requirements and acquisition plan','# TETHER full data requirements and acquisition plan').replace('  - asof\n','  - tether\n')
  start=text.index('**1 November paper checkpoint:**');end=text.index('**Current evaluation policy, 31 October 2026:**',start)
  text=text[:start]+current+'\n'+f'TETHER means {EXPANSION}. See [catalog identity and history](catalog/README.md); the frozen AsOf engine and temporal/dataset identifiers remain compatible.\n\n'+text[end:]
  text=text.replace('Current implementation: [P02a credible-set completion]','Retained source-preparation chronology: [P02a credible-set completion]',1)
  text=text.replace('P07 descriptive tables/figures now pass351 independent checks and local byte-identical rebuild; manuscript/release remain pending.',
   'At that checkpoint, P07 descriptive tables/figures passed351 independent checks and local byte-identical rebuild; manuscript/release were still pending. The current checkpoint above records their later technical completion and remaining owner facts.',1)
  return text
 edit('data/DATA_PLAN.md',dataplan)

 catalog_note=f'''# TETHER catalog identity and history

TETHER means **{EXPANSION}**.
The [active master catalog](sources.json) retains its existing schema, provider and
dataset IDs, roles, date fields, acquisition facts and scientific-status values.
The rename changes only its top-level title and the project-generated-assets
provider display name. It does not promote collection, parsing or validation.

The exact pre-rename bytes are preserved at
[sources-pre-tether-20261101.json](history/sources-pre-tether-20261101.json):
`{sha(old)}` (SHA-256; {len(old):,} bytes).
The cosmetically renamed catalog is
`{sha(new)}` (SHA-256; {len(new):,} bytes).
Historical snapshots, receipts and READY authorities continue to bind their
original catalog bytes; editing a display name does not preserve that byte hash.
New builds must bind their genuine current catalog fingerprint.

Legacy keys such as `asof_release_date` and `asofDate` express temporal/contract
semantics. The `asof_normalized_packets` dataset ID, archived paths and all other
identifiers remain unchanged. They are not instructions to use a new source role
or replace a sealed artifact. The canonical package is `tether-target-agents`
0.4.0 in `packages/tether`; its CLI/import aliases retain the frozen AsOf 0.3.11
engine. See [installation and compatibility](../../README.md#installation-and-compatibility).

The history copy is evidence, not an acquisition queue or a new reference/generation
input. Existing P05/P06/P09/P10 results, old releases and failed attempts remain
unchanged. Provider rights still apply independently of the project name.
'''
 write_new(ROOT/'data/catalog/README.md',catalog_note.encode())
 report={'schema_version':1,'method':'tether.active_documentation_branding.v1','changed_files':inventory,
  'new_files':['data/catalog/README.md','data/catalog/history/sources-pre-tether-20261101.json'],
  'catalog':{'history_path':archive.relative_to(ROOT).as_posix(),'original_sha256':sha(old),'current_sha256':sha(new),'original_bytes':len(old),'current_bytes':len(new),'changed_json_paths':changed,'all_other_json_values_equal':True,'original_bytes_exact':archive.read_bytes()==old},
  'legacy_exemptions':{'docs':EXCLUDED,'directories':['docs/history','planning/review-assets (previous evidence)','paper','memory','src','data originals/receipts/sealed artifacts'],
   'identifiers':['asof imports/module commands','legacy wheel/distribution names','wire/schema/method IDs','asofDate','asof_release_date','asof_normalized_packets','actual src/asof and retained filesystem paths'],
   'historical_prose':'Accepted AsOf version statements and fixed study arm names are retained as engine/history labels, not current product branding.'},
  'no_study_or_source_execution':True,'new_model_calls':0,'new_network_calls':0,'scientific_validation':'not_established'}
 write_new(HERE/'ACTIVE-DOCS-BRANDING-CHANGES-v1.json',(json.dumps(report,indent=2)+'\n').encode())
 print(json.dumps({'changed':len(inventory),'catalog':report['catalog'],'excluded_docs':list(EXCLUDED)},indent=2))

if __name__=='__main__':main()
