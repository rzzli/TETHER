"""Small read-only documentation/interface check; no CLI or science execution."""
from pathlib import Path
from urllib.parse import unquote,urlsplit
import ast,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def load(name):return json.loads((HERE/name).read_text(encoding='utf-8'))
def main():
 previous=load('ACTIVE-DOCS-BRANDING-CHANGES-v1.json');change=load('ACTIVE-DOCS-CLI-LAYOUT-CHANGES-v2.json');checks=[];issues=[];links=[]
 def need(name,okay):
  checks.append({'check':name,'passed':bool(okay)})
  if not okay:issues.append(name)
 prior={r['path']:r for r in previous['changed_files']};current={r['path']:r for r in change['changed_files']}
 need('exact_21_owned_files',set(current)=={'README.md'}|{p for p in prior if p.startswith('docs/')} and len(current)==21)
 for name,row in current.items():
  need('v1_to_v2_exact_chain:'+name,row['before_sha256']==prior[name]['after_sha256'])
  need('current_doc_hash:'+name,sha((ROOT/name).read_bytes())==row['after_sha256'])
 for name,row in prior.items():
  if name not in current:need('data_catalog_unchanged_since_v1:'+name,sha((ROOT/name).read_bytes())==row['after_sha256'])
 for name,digest in change['contract_sources'].items():need('CLI_contract_code_pin:'+name,sha((ROOT/name).read_bytes())==digest)
 presentation=ast.parse((ROOT/'packages/tether/src/tether/_presentation.py').read_text(encoding='utf-8'))
 constants={node.targets[0].id:ast.literal_eval(node.value) for node in presentation.body if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in {'MANIFEST','RECEIPT','FAILURE','JOURNAL'}}
 need('presentation_exact_filenames',constants=={'MANIFEST':'tether-manifest.json','RECEIPT':'tether-receipt.json','FAILURE':'tether-failure.json','JOURNAL':'attempt/journal.jsonl'})
 readme=(ROOT/'README.md').read_text(encoding='utf-8')
 for text in ['## TETHER CLI run layout','engine/','tether-manifest.json','tether-receipt.json','attempt/journal.jsonl','engine-stdout.txt','engine-stderr.txt','`asof verify --run-dir OUT/engine`','Outer verification rejects `--outputs-only`','Direct API aliases']:
  # Root uses a prose API-alias explanation rather than this guide phrase.
  if text=='Direct API aliases':continue
  need('documented_layout:'+text,text in readme)
 need('API_and_CLI_separation','with their existing output layouts. They do not automatically create branded' in readme and '`tether._presentation`' in readme)
 need('delegate_layout_preserved','`inspect-source`, `build-snapshot` and `evaluate`' in readme and 'existing engine output layouts' in readme)
 need('outer_source_and_legacy_receipt_distinct','source-inclusive engine verification' in readme and 'separate engine\nreceipt hash' in readme and 'printed **outer** receipt hash' in readme)
 need('failure_inspection_no_retry','`tether-failure.json`' in readme and 'never automatically repeat execution' in readme)
 for name in current:
  text=(ROOT/name).read_text(encoding='utf-8')
  if name.startswith('docs/'):
   need('guide_API_scope:'+name,'Direct API aliases preserve legacy outputs' in text and '`tether._presentation`' in text and 'Delegated source inspection, snapshot construction and evaluation keep their engine layouts.' in text)
  for m in re.finditer(r'\[[^\]\n]+\]\((?:<([^>\n]+)>|([^\)\n]+))\)',text):
   target=m.group(1) or m.group(2);u=urlsplit(target)
   if u.scheme or u.netloc:continue
   p=(ROOT/name).parent/unquote(u.path) if u.path else ROOT/name
   okay=p.exists()
   if u.fragment in ('installation-and-compatibility','tether-cli-run-layout'):
    heading={'installation-and-compatibility':'## Installation and compatibility','tether-cli-run-layout':'## TETHER CLI run layout'}[u.fragment]
    okay=okay and heading in p.read_text(encoding='utf-8')
   links.append({'source':name,'target':target,'resolved':okay});need('relative_link:'+str(len(links)),okay)
 for name in ['docs/FRAMEWORK.md','docs/V02_MIGRATION.md']:
  text=(ROOT/name).read_text(encoding='utf-8');need('legacy_receipt_scope:'+name,'OUT/engine' in text and 'rejects' in text and '`--outputs-only`' in text)
 need('git_diff_check',subprocess.run(['git','diff','--check','--',*current],cwd=ROOT,capture_output=True).returncode==0)
 report={'schema_version':1,'method':'tether.active_cli_layout_documentation_validation.v2','status':'PASS' if not issues else 'FAIL','checks_evaluated':len(checks),'checks_passed':sum(c['passed'] for c in checks),'unresolved_findings':issues,'checks':checks,'relative_links':links,
  'v1_evidence_carried_forward':'Original221-check report retained unchanged; this v2 checks the21 owned doc changes and unchanged data/catalog hashes without repeating runtime/source qualification.',
  'v1_validation_sha256':sha((HERE/'ACTIVE-DOCS-BRANDING-VALIDATION-v1.json').read_bytes()),'change_inventory_sha256':sha((HERE/'ACTIVE-DOCS-CLI-LAYOUT-CHANGES-v2.json').read_bytes()),'contract_sources':change['contract_sources'],
  'scope_limits':['Read-only documentation/interface inspection; no TETHER CLI/API invocation, install, broad tests or original-source reads.','CLI filenames/layout confirmed stable by author; code/API qualification and new package tests are separate.','Legacy IDs, API objects, engine layouts, old receipts/READY/release artifacts and scientific results retain their identity.'],
  'new_model_calls':0,'new_network_calls':0,'study_rerun':False,'scientific_validation':'not_established'}
 with (HERE/'ACTIVE-DOCS-CLI-LAYOUT-VALIDATION-v2.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
 print(json.dumps({k:report[k] for k in ['status','checks_evaluated','checks_passed','unresolved_findings']},indent=2))
 print('relative_links',len(links))
 if issues:raise SystemExit(1)
if __name__=='__main__':main()
