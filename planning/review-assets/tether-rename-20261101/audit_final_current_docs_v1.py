"""Final bounded current-document QA; no inputs are edited or experiments rerun."""
from pathlib import Path
from urllib.parse import unquote,urlsplit
import hashlib,json,re,zipfile,posixpath
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 inv=json.loads((HERE/'ACTIVE-DOCS-BRANDING-CHANGES-v1.json').read_text(encoding='utf-8'))
 guides=[x['path'] for x in inv['changed_files'] if x['path'].startswith('docs/')]
 extra=['README.md','TODO.md','paper/README.md','planning/README.md','planning/TETHER Naming and Compatibility Plan 2026-11-01.md','planning/TETHER Rename Completion and Project Status 2026-11-01.md','planning/Project Progress Reassessments.md','memory/MEMORY.md','memory/project-goals.md','memory/research-log-2026-11-01-tether-renaming.md','data/README.md','data/DATA_PLAN.md','data/catalog/README.md','packages/tether/README.md','planning/review-assets/tether-rename-20261101/ACTIVE-WORK-STATE.md','paper/release/tether/README.md']
 paths=guides+extra;subjects={};texts={};checks=[];issues=[];links=[];legacy=[]
 def need(name,value):
  checks.append({'check':name,'passed':bool(value)})
  if not value:issues.append(name)
 for name in paths:
  b=(ROOT/name).read_bytes();subjects[name]={'sha256':sha(b),'bytes':len(b)};text=b.decode('utf-8')
  if name=='memory/MEMORY.md':text=text.split('- [[research-log-2026-11-01-working-paper-packet]]')[0]
  if name=='memory/project-goals.md':text=text.split('### Pre-rename working-paper checkpoint')[0]
  texts[name]=text;need('current_identity:'+name,'TETHER' in text)
  for number,line in enumerate(text.splitlines(),1):
   if re.search(r'\bAsOf\b',line):legacy.append({'path':name,'line':number,'text':line,'disposition':'Compatibility engine/version, fixed arm or temporal/schema/dataset identity, historical path/link, or explicitly retained dated chronology; manually reviewed.'})
 # Name resolution uses filenames only, without reading historical/protected targets.
 candidates={}
 for directory in [ROOT,ROOT/'docs',ROOT/'planning',ROOT/'memory',ROOT/'data']:
  for p in directory.glob('*.md'):candidates.setdefault(p.stem.casefold(),[]).append(p)
 packet_record=json.loads((ROOT/'paper/release/tether/RELEASE-RECORD.json').read_text(encoding='utf-8'))
 with zipfile.ZipFile(ROOT/packet_record['archive']['workspace_path']) as z:packet_names=set(z.namelist())
 for name,text in texts.items():
  parent=(ROOT/name).parent
  targets=[]
  for m in re.finditer(r'\[[^\]\n]+\]\((?:<([^>\n]+)>|([^\)\n]+))\)',text):targets.append(('markdown',m.group(1) or m.group(2)))
  for m in re.finditer(r'\[\[([^\]\n]+)\]\]',text):targets.append(('wiki',m.group(1).split('|',1)[0]))
  for kind,target in targets:
   u=urlsplit(target)
   if u.scheme or u.netloc:continue
   part=unquote(u.path);possible=[parent/part,ROOT/part]
   if kind=='wiki':possible += [parent/(part+'.md'),ROOT/(part+'.md')]+candidates.get(Path(part).name.casefold(),[])
   resolved=next((p for p in possible if p.exists()),None)
   okay=resolved is not None
   if name=='paper/release/tether/README.md':
    virtual=posixpath.normpath(part)
    okay=virtual in packet_names or any(n.startswith(virtual.rstrip('/')+'/') for n in packet_names)
   if okay and u.fragment in ['installation-and-compatibility','tether-cli-run-layout']:
    heading={'installation-and-compatibility':'## Installation and compatibility','tether-cli-run-layout':'## TETHER CLI run layout'}[u.fragment];okay=heading in resolved.read_text(encoding='utf-8')
   links.append({'source':name,'kind':kind,'target':target,'resolved':okay});need('local_link:'+str(len(links)),okay)
 def metadata(rel):
  raw=(ROOT/rel).read_bytes();subjects[rel]={'sha256':sha(raw),'bytes':len(raw)};return json.loads(raw)
 record=metadata('paper/release/tether/RELEASE-RECORD.json');qual=metadata('paper/release/tether/QUALIFICATION.json')
 packet=json.loads((HERE/'PACKET-PEER-REVIEW.json').read_text(encoding='utf-8'));paper=json.loads((HERE/'PAPER-RENAME-PEER-REVIEW.json').read_text(encoding='utf-8'))
 need('current_packet_exact_counts_and_pins',record['archive']['sha256']==packet['archive_sha256']=='e57af7f4e99cf879f9944c83a19d2106f013935ff99f8681803124ed63443b8c' and record['archive']['members']==packet['members']==72 and record['archive']['bytes']==packet['archive_bytes']==21552273 and packet['check_count']==946 and packet['unresolved_findings']==[])
 need('current_qualification_byte_authority',subjects['paper/release/tether/QUALIFICATION.json']['sha256']==record['qualification_sha256']=='69ffeb1b4ac59dd2c5f4dee5afd2a3442d0adf9558fd0d2ba784a8f8e3dfbbdc')
 need('packet_readme_input_unchanged',subjects['paper/release/tether/README.md']['sha256']==qual['payloads']['README.md']['sha256'])
 need('current_pdf_counts',paper['check_count']==1222 and paper['pdf']['pages']==18 and paper['pdf']['independent_visible_units']==274 and paper['pdf']['vector_figures']==3 and paper['pdf']['links']==29 and paper['unresolved_findings']==[])
 for label,count,executed,skips in [('tether_full',49,49,0),('tether_core',49,49,0),('legacy_targeted_full',115,115,0),('legacy_targeted_core',115,96,19)]:
  row=qual['checks'][label];need('reported_suite:'+label,row['tests_collected']==count and row['tests_executed']==executed and row['approved_optional_skips']==skips and row['errors']==row['failures']==0)
 need('declared_science_publication_boundaries',all(d['scientific_validation']==d['study_independence']=='not_established' and d['owner_declarations']=='deferred' and d['submission_ready'] is False and d['publication_authorized'] is False and d['public_deposit'] is None for d in [qual,record]))
 for name in guides:need('guide_explains_legacy_and_layout:'+name,'frozen AsOf 0.3.11' in texts[name] and 'Direct API aliases preserve legacy outputs' in texts[name] and 'tether._presentation' in texts[name])
 for name in ['README.md','docs/FRAMEWORK.md','docs/V02_MIGRATION.md']:need('canonical_CLI_examples:'+name,'uv run --project packages/tether --no-sync tether' in texts[name] and 'uv run --no-sync asof ' not in texts[name])
 need('outer_layout_and_receipts_clear',all(x in texts['README.md'] for x in ['tether-manifest.json','tether-receipt.json','attempt/journal.jsonl','`asof verify --run-dir OUT/engine`','Outer verification rejects `--outputs-only`']))
 for name in ['data/README.md','data/DATA_PLAN.md']:need('historical_and_current_packet_separate:'+name,'historical pre-rename 53-member' in texts[name] and '72-member TETHER' in texts[name] and '946' in texts[name])
 need('present_tense_data_identity_correct','inventory for AsOf' not in texts['data/README.md'] and 'inventory for TETHER' in texts['data/README.md'])
 need('memory_no_premature_N01_N06_completion','N01-N06 are implemented and' not in texts['memory/research-log-2026-11-01-tether-renaming.md'] and 'N01-N06 track the completed' not in texts['memory/project-goals.md'])
 todo=texts['TODO.md'];need('N05_N06_pending_allowed_at_review',all(re.search(r'^- \[ \] '+n+r'\b',todo,re.M) for n in ['N05','N06']))
 cat=metadata('data/catalog/sources.json');old=(ROOT/'data/catalog/history/sources-pre-tether-20261101.json').read_bytes();now=(ROOT/'data/catalog/sources.json').read_bytes()
 need('only_two_catalog_display_changes',now==old.replace(b'AsOf dataset requirements and acquisition inventory',b'TETHER dataset requirements and acquisition inventory',1).replace(b'AsOf project-generated assets',b'TETHER project-generated assets',1) and len(cat['providers'])==83 and len(cat['datasets'])==178)
 report={'schema_version':1,'method':'tether.final_current_documentation_qa.v1','status':'PASS_CURRENT_DOCS_NAMING_LINKS_STATUS' if not issues else 'FAIL_CURRENT_DOCS_QA','role':'evaluation_only','agent_visible':False,'checks_evaluated':len(checks),'checks_passed':sum(c['passed'] for c in checks),'unresolved_findings':issues,'subjects':subjects,'content_scope':{'current_guides':len(guides),'text_documents':len(paths),'memory_review':'Current sections only; whole-file hashes retain exact subject authority.','historical_targets':'Link names/existence only; old content/protected data not opened.'},'checks':checks,'local_links':links,'remaining_AsOf_occurrences':legacy,
 'closed_initial_findings':[{'id':'CURRENT-01','initial':'Memory said all N01-N06 implemented/validated and final checkpoint existed while TODO left N05/N06 pending.','resolution':'Current memory wording now tracks migration/final validation/checkpoint without claiming completion.'},{'id':'CURRENT-02','initial':'Current data summaries gave53/200 without clearly distinguishing the new72/946 packet.','resolution':'Historical pre-rename53/200 and current72/946 are now explicit with current links.'},{'id':'CURRENT-03','initial':'Unlabeled present-tense data inventory paragraph still named AsOf.','resolution':'That sentence now names TETHER; dated names/IDs remain preserved.'}],
 'pending_completion_allowance':{'at_review':['N05','N06'],'permitted_followup':'Root may mark only those completion checkboxes after current-doc/static-CI validation and record the timestamped local commit. This report does not certify a future commit or hosted run.'},
 'retained_quantity_evidence':{'packet_peer_sha256':sha((HERE/'PACKET-PEER-REVIEW.json').read_bytes()),'paper_peer_sha256':sha((HERE/'PAPER-RENAME-PEER-REVIEW.json').read_bytes()),'wheel_review_sha256':sha((HERE/'WHEEL-PEER-REVIEW-v1.json').read_bytes()),'frontdoor_review_sha256':sha((HERE/'FRONTDOOR-NAMESPACE-INDEPENDENT-REVIEW-v2.json').read_bytes())},
 'checker_initial_diagnostic':'Initial report retained separately: eight standalone-packet README links were initially resolved against checkout instead of ZIP root. Corrected virtual-packet resolution changed no document or packet. All other checks were already passing.',
 'limits':['No packet input, runtime, source, guide or status file edited by this checker.','Existing dated logs/proposals, code/module CLIs, schema/method/dataset/temporal IDs and frozen artifacts remain explained historical compatibility exemptions.','No PDF rerender, original/provider/human/protected input read, install, broad test rerun, network/model/download/publication/hosted execution.','Static CI is reviewed by a separate agent; current configured jobs do not establish hosted success.','Original1973 broad acceptance is historical; new49 and115/96+19 scopes and all overlapping audit counts remain distinct.'],
 'scientific_validation':'not_established','new_model_calls':0,'new_network_calls':0,'new_downloads':0}
 with (HERE/'FINAL-CURRENT-DOCS-QA-v1.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({k:report[k] for k in ['status','checks_evaluated','checks_passed','unresolved_findings']},indent=2));print('text_documents',len(paths),'local_links',len(links),'AsOf_occurrences',len(legacy))
 if issues:raise SystemExit(1)
if __name__=='__main__':main()
