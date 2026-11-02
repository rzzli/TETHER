"""Independent wheel ZIP/RECORD/source/metadata audit; never installs or imports it."""
from pathlib import Path,PurePosixPath
from email.parser import BytesParser
import base64,configparser,csv,hashlib,io,json,re,stat,struct,zipfile
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
PIN='26bb8059ac0eb1e1b9d6c965dedae2409f7d418fbdb48d13f0c524f8354c4ddf'
DIST='tether_target_agents-0.4.0.dist-info'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
 location=json.loads((HERE/'WHEEL-BUILD-LOCATION.json').read_text(encoding='utf-8'));path=Path(location['wheel'])
 checks=[];issues=[];source_map={};privacy=[]
 def need(name,okay):
  checks.append({'check':name,'passed':bool(okay)})
  if not okay:issues.append(name)
 raw=path.read_bytes();need('independent_external_wheel_pin',sha(raw)==PIN and len(raw)==24538)
 need('build_location_agrees',location['sha256']==PIN and location['bytes']==len(raw) and path.name=='tether_target_agents-0.4.0-py3-none-any.whl')
 sources={p.relative_to(ROOT/'packages/tether/src').as_posix():p for p in (ROOT/'packages/tether/src/tether').rglob('*.py') if '__pycache__' not in p.parts}
 metadata={DIST+'/'+name for name in ['METADATA','WHEEL','entry_points.txt','top_level.txt','RECORD','licenses/LICENSE']}
 expected=set(sources)|metadata
 need('reviewed14_source_inventory',len(sources)==14)
 review=json.loads((HERE/'FRONTDOOR-NAMESPACE-INDEPENDENT-REVIEW-v2.json').read_text(encoding='utf-8'))
 need('corrected_runtime_review_anchor',sha((HERE/'FRONTDOOR-NAMESPACE-INDEPENDENT-REVIEW-v2.json').read_bytes())=='a2c23240e78b4046bacc774d5f388cfc3f5630aee9a1c5ae1d6c0d3937130f87')
 with zipfile.ZipFile(io.BytesIO(raw)) as archive:
  infos=archive.infolist();names=[x.filename for x in infos]
  need('exact20_allowlisted_members',set(names)==expected and len(names)==20)
  need('no_alias_duplicates_or_comment',len(set(names))==len({n.casefold() for n in names})==len(names) and not archive.comment)
  need('small_known_uncompressed_inventory',sum(x.file_size for x in infos)<1024*1024)
  eocd=struct.unpack('<4s4H2LH',raw[-22:])
  need('single_disk_EOCD_exact_end',eocd[0]==b'PK\x05\x06' and eocd[1:3]==(0,0) and eocd[3]==eocd[4]==len(names) and eocd[7]==0 and eocd[6]+eocd[5]==len(raw)-22)
  offset=0
  for info in infos:
   name=info.filename;p=PurePosixPath(name)
   need('safe_regular_member:'+name,not p.is_absolute() and '..' not in p.parts and '\\' not in name and ':' not in name and not info.is_dir() and stat.S_IFMT(info.external_attr>>16) in (0,stat.S_IFREG))
   need('standard_unencrypted_header:'+name,info.compress_type==zipfile.ZIP_DEFLATED and info.flag_bits==0 and not info.extra and not info.comment and info.header_offset==offset)
   header=struct.unpack_from('<I5H3I2H',raw,offset);name_len,extra_len=header[-2:]
   local_name=raw[offset+30:offset+30+name_len]
   need('local_and_central_metadata_match:'+name,header[0]==0x04034b50 and header[2]==info.flag_bits and header[3]==info.compress_type and header[6:9]==(info.CRC,info.compress_size,info.file_size) and local_name.decode('utf-8')==name and extra_len==0)
   offset+=30+name_len+extra_len+info.compress_size
  need('no_hidden_local_padding_or_trailing_payload',offset==eocd[6])
  need('all_member_CRCs_match',archive.testzip() is None)
  records=list(csv.reader(io.StringIO(archive.read(DIST+'/RECORD').decode('utf-8'))))
  need('RECORD_exact_unique_closure',all(len(row)==3 for row in records) and len(records)==len(names) and len({row[0] for row in records})==len(names) and {row[0] for row in records}==set(names))
  record_map={row[0]:row[1:] for row in records}
  for name in names:
   payload=archive.read(name);hash_value,length=record_map[name]
   if name==DIST+'/RECORD':need('RECORD_self_excluded_hash_and_size',hash_value==length=='')
   else:
    expected_digest='sha256='+base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b'=').decode('ascii')
    need('RECORD_digest_size:'+name,hash_value==expected_digest and length==str(len(payload)))
   text=payload.decode('utf-8')
   if re.search(r'(?i)(?:zzric|[A-Z]:[\\/]Users[\\/]|[A-Z]:[\\/]Projects(?:_data)?[\\/]|/Users/|/home/|drug_target_agents_data)',text.replace('\\\\','\\')):privacy.append(name+':private_root')
   if re.search(r'(?:sk-[A-Za-z0-9_-]{24,}|AKIA[A-Z0-9]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)',text):privacy.append(name+':credential_pattern')
  for name,source in sources.items():
   payload=archive.read(name);data=source.read_bytes();proof=review['subjects'][source.relative_to(ROOT).as_posix()]
   need('source_byte_exact_and_reviewed:'+name,payload==data and sha(payload)==proof['sha256'] and len(payload)==proof['bytes'])
   source_map[name]={'sha256':sha(payload),'bytes':len(payload)}
  need('no_legacy_ownership_or_other_payload',not any(n.startswith(('asof/','asof_target_agents')) or n.endswith(('.pth','.pyc','.ttf','.otf','.parquet','.png','.pdf')) or '.data/' in n for n in names))
  md=BytesParser().parsebytes(archive.read(DIST+'/METADATA'))
  need('metadata_no_parse_defects',not md.defects)
  need('canonical_metadata_name_version',md.get_all('Name')==['tether-target-agents'] and md.get_all('Version')==['0.4.0'] and md.get_all('Metadata-Version')==['2.4'])
  need('python_requirement',md.get_all('Requires-Python')==['>=3.11'])
  need('only_pinned_core_and_optional_Arrow',md.get_all('Requires-Dist')==['asof-target-agents==0.3.11','pyarrow==21.0.0; extra == "ingest"'] and md.get_all('Provides-Extra')==['ingest'])
  need('no_direct_URL_or_editable_dependency',not any('@' in v or 'file:' in v for v in md.get_all('Requires-Dist',[])))
  need('license_file_declaration',md.get_all('License-File')==['LICENSE'])
  need('Apache_license_exact',archive.read(DIST+'/licenses/LICENSE')==(ROOT/'packages/tether/LICENSE').read_bytes()==(ROOT/'LICENSE').read_bytes())
  wheel=BytesParser().parsebytes(archive.read(DIST+'/WHEEL'))
  need('pure_python_wheel_tag_and_backend',wheel.get_all('Wheel-Version')==['1.0'] and wheel.get_all('Root-Is-Purelib')==['true'] and wheel.get_all('Tag')==['py3-none-any'] and wheel.get_all('Generator')==['setuptools (84.0.0)'] and not wheel.defects)
  parser=configparser.ConfigParser();parser.read_string(archive.read(DIST+'/entry_points.txt').decode())
  need('only_canonical_console_entrypoint',parser.sections()==['console_scripts'] and dict(parser['console_scripts'])=={'tether':'tether._cli:main'})
  need('only_tether_top_level',archive.read(DIST+'/top_level.txt')==b'tether\n')
  need('public_payload_privacy_scan',not privacy)
 report={'schema_version':1,'method':'tether.independent_wheel_review.v1','status':'PASS_WHEEL_PEER_REVIEW' if not issues else 'FAIL_WHEEL_PEER_REVIEW','role':'evaluation_only','agent_visible':False,'wheel':{'path':path.relative_to(ROOT).as_posix(),'sha256':sha(raw),'bytes':len(raw),'members':len(names),'source_payloads':len(source_map),'metadata_payloads':len(metadata)},'checks_evaluated':len(checks),'checks_passed':sum(c['passed'] for c in checks),'unresolved_findings':issues,'privacy_findings':privacy,'checks':checks,'source_payload_map':source_map,
  'runtime_review_sha256':'a2c23240e78b4046bacc774d5f388cfc3f5630aee9a1c5ae1d6c0d3937130f87','limits':['No wheel import/install, CLI execution, broad test run or provider/human/protected input read. Root separately owns installed tests/demo/proof.','Complete outer ZIP and RECORD closure checked independently with stdlib, without producer archive helper imports.','Legacy asof dependency is metadata only; the wheel owns only tether payloads. Existing engine/receipts/releases remain unchanged.','Byte/packaging checks establish no scientific validity, redistribution right for external data, or public-deposit authorization.'],'scientific_validation':'not_established','new_model_calls':0,'new_network_calls':0,'new_downloads':0}
 with (HERE/'WHEEL-PEER-REVIEW-v1.json').open('x',encoding='utf-8') as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps({k:report[k] for k in ['status','wheel','checks_evaluated','checks_passed','unresolved_findings','privacy_findings']},indent=2))
 if issues:raise SystemExit(1)
if __name__=='__main__':main()
