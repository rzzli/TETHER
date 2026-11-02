"""Scoped checks for the TETHER documentation/catalog rename; no source replay."""
from pathlib import Path
from urllib.parse import unquote,urlsplit
import ast,hashlib,json,re,subprocess
from asof.maintenance import validate_catalog

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
 inventory=json.loads((HERE/'ACTIVE-DOCS-BRANDING-CHANGES-v1.json').read_text(encoding='utf-8'))
 checks=[];links=[];failures=[]
 def need(label,okay):
  checks.append({'check':label,'passed':bool(okay)})
  if not okay:failures.append(label)
 for row in inventory['changed_files']:
  path=ROOT/row['path'];need('recorded_current_hash:'+row['path'],sha(path.read_bytes())==row['after_sha256'])
 oldraw=(ROOT/inventory['catalog']['history_path']).read_bytes();raw=(ROOT/'data/catalog/sources.json').read_bytes()
 need('pre_rename_catalog_exact_pin',sha(oldraw)==inventory['catalog']['original_sha256']=='3c3108e6318e791985892fecea6ca9ea6185af7810a5ffd4a6311be3ca6f6109')
 need('only_two_display_strings_change',raw==oldraw.replace(b'AsOf dataset requirements and acquisition inventory',b'TETHER dataset requirements and acquisition inventory',1).replace(b'AsOf project-generated assets',b'TETHER project-generated assets',1))
 old=json.loads(oldraw);new=json.loads(raw)
 validate_catalog(old);validate_catalog(new);need('both_catalogs_pass_unchanged_core_validator',True)
 index=set(re.findall(r'^\| `([^`]+)` \|',(ROOT/'data/DATA_PLAN.md').read_text(encoding='utf-8'),re.M))
 need('all_178_dataset_ids_documented',{d['dataset_id'] for d in new['datasets']}.issubset(index) and len(new['datasets'])==178 and len(new['providers'])==83)
 markdown=[ROOT/r['path'] for r in inventory['changed_files'] if r['path'].endswith('.md')]+[ROOT/'data/catalog/README.md']
 for path in markdown:
  text=path.read_text(encoding='utf-8');rel=path.relative_to(ROOT).as_posix()
  need('current_document_has_TETHER:'+rel,'TETHER' in text)
  for match in re.finditer(r'\[[^\]\n]+\]\((?:<([^>\n]+)>|([^\)\n]+))\)',text):
   target=match.group(1) or match.group(2);url=urlsplit(target)
   if url.scheme or url.netloc:continue
   resolved=(path.parent/unquote(url.path)).resolve() if url.path else path
   okay=resolved.exists()
   if url.fragment=='installation-and-compatibility':okay=okay and '## Installation and compatibility' in resolved.read_text(encoding='utf-8')
   need('local_link:'+str(len(links)),okay);links.append({'source':rel,'target':target,'exists':okay})
  if rel.startswith('docs/'):
   before=subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT).decode('utf-8')
   module_commands=re.findall(r'python (?:-I )?-m asof[\w.]+[^\n`]*',before)
   need('legacy_module_commands_preserved:'+rel,all(command.rstrip('\r') in text for command in module_commands))
   need('guide_identity_and_history_note:'+rel,'tether-target-agents' in text and 'frozen AsOf 0.3.11' in text and 'Historical version/arm names' in text)
 for rel in ['README.md','docs/FRAMEWORK.md','docs/V02_MIGRATION.md']:
  text=(ROOT/rel).read_text(encoding='utf-8')
  need('canonical_main_CLI:'+rel,'uv sync --project packages/tether --python 3.11' in text and 'uv run --project packages/tether --no-sync tether' in text and 'uv run --no-sync asof ' not in text)
 for name in inventory['legacy_exemptions']['docs']:
  rel='docs/'+name
  need('excluded_doc_unmodified:'+rel,not subprocess.check_output(['git','diff','--name-only','HEAD','--',rel],cwd=ROOT).strip())
 for name in ['rebrand_active_docs_v1.py','validate_active_docs_v1.py']:ast.parse((HERE/name).read_text(encoding='utf-8'))
 need('retained_scripts_parse_without_execution',True)
 whitespace=subprocess.run(['git','diff','--check','--','README.md','docs','data/README.md','data/DATA_PLAN.md','data/catalog/sources.json'],cwd=ROOT,capture_output=True,text=True)
 need('git_diff_check',whitespace.returncode==0)
 report={'schema_version':1,'method':'tether.scoped_active_docs_validation.v1','status':'PASS' if not failures else 'FAIL','checks_evaluated':len(checks),'checks_passed':sum(c['passed'] for c in checks),'unresolved_findings':failures,'checks':checks,'local_links':links,'catalog':inventory['catalog'],
  'counts':{'changed_existing_files':len(inventory['changed_files']),'current_guides':sum(r['path'].startswith('docs/') for r in inventory['changed_files']),'local_markdown_links':len(links),'providers':len(new['providers']),'datasets':len(new['datasets'])},
  'limits':['No package install, CLI execution, original source reads, broad suite, model or network activity. Namespace/CLI agents separately validate the new TETHER entry points.','Existing frozen study/release artifacts and legacy code remain outside this edit scope.','Accepted AsOf versions, fixed arm labels, module commands and ID spellings are deliberate compatibility/history exemptions.'],
  'new_model_calls':0,'new_network_calls':0,'study_rerun':False,'scientific_validation':'not_established'}
 with (HERE/'ACTIVE-DOCS-BRANDING-VALIDATION-v1.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
 print(json.dumps({k:report[k] for k in ['status','checks_evaluated','checks_passed','unresolved_findings','counts']},indent=2))
 if failures:raise SystemExit(1)

if __name__=='__main__':main()
