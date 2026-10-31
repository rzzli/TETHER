"""Prepare an independent legacy harness adapter, never execute subjects."""
import hashlib
from pathlib import Path

HERE=Path(__file__).resolve().parent
SHARED=HERE.parent/'recovery-step9-shared-owner-20261029'


def once(text,old,new):
    assert text.count(old)==1,(old,text.count(old))
    return text.replace(old,new)


def main():
    raw=(SHARED/'shared_owner_fixture_driver_v2.py').read_bytes()
    assert hashlib.sha256(raw).hexdigest()=='a97ae3ca57ce6f1b97e5a382a4051714242621c11b3d1756262f1f8025c8f566'
    t=raw.decode('utf-8')
    t=once(t,'import math\n','import math\nimport re\n')
    t=once(t,'HERE=Path(__file__).resolve().parent\n',
        "HERE=Path(__file__).resolve().parent\nLITERALS_DIR=HERE.parent/'recovery-step9-shared-owner-20261029'\nTEST_DEADLINE=None\nSUBJECT_FILENAMES=set()\nPROJECTOR_OBSERVATIONS=[]\n")
    t=once(t,"raw=(HERE/name).read_bytes()","raw=(LITERALS_DIR/name).read_bytes()")
    t=once(t,"'types':types,'struct':struct}","'types':types,'struct':struct,'re':re}")
    t=once(t,"  source_bytes[name]=raw","  source_bytes[name]=raw\n  SUBJECT_FILENAMES.add(str(Path(expected['path'])))")
    start=t.index('def audit(event,args):\n');end=t.index('sys.addaudithook(audit)\n',start)
    t=t[:start]+'''def audit(event,args):
 dangerous=(event=='open' or event=='import' or event.startswith(('ctypes.','subprocess.','socket.','os.')))
 if not dangerous:return
 active=ACTIVE[0]
 frame=sys._getframe()
 for _ in range(512):
  if frame is None:break
  if frame.f_code.co_filename in SUBJECT_FILENAMES:active=True;break
  frame=frame.f_back
 if active:
  AUDIT_DENIALS.append(event);raise HarnessError('unexpected_IO_or_import_during_subject')
'''+t[end:]
    insertion='''
def subject_role(legacy):
 if legacy=='software':return 'captured_software'
 if legacy in ('owner_metadata','artifact'):return 'captured_metadata'
 raise HarnessError('undeclared legacy input role')

def projected_snapshot(world,issued):
 # Diagnostic projection is an immutable observation, including after the
 # synthetic owner's hard cutoff. Its cancellation uses the ONE externally
 # established real suite deadline, never a renewed owner or a no-op callback.
 if type(issued) is not world.S.ProducerSnapshot:raise HarnessError('nongenuine producer snapshot')
 def check():
  if TEST_DEADLINE is None:raise HarnessError('external test deadline not installed')
  if time.monotonic()>=TEST_DEADLINE:raise TimeoutError('original independent suite deadline')
 projected=invoke(world.S.project_legacy,issued,check=check)
 PROJECTOR_OBSERVATIONS.append(dict(actual_producer_snapshot=True,actual_projector=True,
     same_owner_token_resolution_external=True,owner_clock_resampled=False))
 return projected

'''
    t=once(t,'class Clock:\n',insertion+'class Clock:\n')
    old="   keys=r.public['serialized_journal_row']['exact_keys'] if target=='append' else r.public['compact_publication_packet']['exact_keys']"
    new="   keys=r.public['serialized_journal_row']['exact_keys'] if target=='append' else ('schema_version','kind','scope','status','elapsed','totals','gates','ledger_refs','links','diagnostic_counts','qualification')"
    t=once(t,old,new)
    t=once(t,"   if target!='append' and decoded['qualification']!=r.public['qualification_exact']:r.violate('fictional packet qualification changed')",
        "   if target!='append':\n    qnames=('originals','real_entry','real_FFI','physical_IO','new84_runtime','resource_fit','scientific')\n    if decoded['schema_version']!=2 or type(decoded['schema_version']) is not int or decoded['scope']!='role_aware_producer_format_v1':r.violate('wrong new packet version/scope')\n    if decoded['kind']!=kind+'.json' or decoded['status'] not in ('OBSERVED_COMPLETE','OBSERVED_NEGATIVE','INCOMPLETE'):r.violate('wrong new packet kind/status')\n    if type(decoded['qualification']) is not dict or set(decoded['qualification'])!=set(qnames) or any(x is not False for x in decoded['qualification'].values()):r.violate('new packet qualification changed')")
    t=once(t,"self.S.FileSpec(b['path'],b['role'],b['bytes'],b['sha256'],b['capture'])",
        "self.S.FileSpec(b['path'],subject_role(b['role']),b['bytes'],b['sha256'],b['capture'],legacy_role=b['role'])")
    t=once(t,"files[0]=self.S.FileSpec(b['path'],'owner_metadata' if variant=='role_changed' else b['role'],b['bytes'],'0'*64 if variant=='hash_changed' else b['sha256'],False if variant=='capture_changed' else True)",
        "files[0]=self.S.FileSpec(b['path'],'captured_metadata' if variant=='role_changed' else subject_role(b['role']),b['bytes'],'0'*64 if variant=='hash_changed' else b['sha256'],False if variant=='capture_changed' else True,legacy_role='owner_metadata' if variant=='role_changed' else b['role'])")
    t=once(t,"alias=w.S.FileSpec(s.path.replace('\\\\','/').upper(),s.role,s.size,s.sha256,s.capture)",
        "alias=w.S.FileSpec(s.path.replace('\\\\','/').upper(),s.role,s.size,s.sha256,s.capture,legacy_role=s.legacy_role)")
    t=once(t,"  raw=invoke(issued.to_dict)","  legacy=projected_snapshot(w,issued)\n  raw=invoke(legacy.to_dict)")
    t=once(t,"   issued=o.snapshot();before=issued.to_dict()","   issued=projected_snapshot(w,invoke(o.snapshot));before=invoke(issued.to_dict)")
    t=once(t,"   foreign=peer.owner.snapshot().to_dict()['errors']['primary']['identity']",
        "   foreign=invoke(projected_snapshot(peer,invoke(peer.owner.snapshot)).to_dict)['errors']['primary']['identity']")
    t=t.replace('Independent v2 generic driver for the frozen synthetic cohort (not real ports).',
        'Independent role-aware adapter of the frozen synthetic cohort driver.\n\nOnly FileSpec role tags, schema2 packet transport and genuine snapshot projection\nare adapted. Frozen histories/expectations, actual identity assertions, ordinary\nread-only ref checks, strict snapshot validator and fault/cutoff monitors persist.')
    with (HERE/'role_aware_legacy_fixture_adapter_v1.py').open('x',encoding='utf-8',newline='\n') as f:f.write(t)
    print('Prepared role_aware_legacy_fixture_adapter_v1.py; subject imports/runs0')


if __name__=='__main__':main()
