"""Independent bounded portable-logic probes using Python fakes only."""
import encodings.utf_16_le
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys
import types

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'portable_file_ports_v2.py'
OUT=HERE/'PORTABLE-FILE-PORTS-INDEPENDENT-AFTER-v2.json'
ACTIVE=[False];DENIALS=[]

def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def audit(event,args):
    if ACTIVE[0] and (event=='open' or event.startswith(('ctypes.','subprocess.','socket.')) or event in ('os.system','os.startfile')):
        DENIALS.append(event);raise AssertionError('Pure portable probe attempted external operation')

def main():
    assert not OUT.exists()
    source_pin=pin(SOURCE);assert source_pin['sha256']=='b7785bd67b461f41ae7beeb1ce2e3b1a8bd0f210ba875eae61aaa25732425aed'
    P=types.ModuleType('portable_peer_under_test_v2');P.__file__=str(SOURCE);sys.modules[P.__name__]=P
    exec(compile(SOURCE.read_bytes(),str(SOURCE),'exec'),P.__dict__)
    sys.addaudithook(audit)
    def raw(value=1,*,buffer=b'',count=None,count_defined=False,buffer_defined=False):
        return P.RawReturn(value,0,False,count,count_defined,buffer,buffer_defined)
    class API:
        def __init__(self,*,failed_identity=False,write_error=None,malformed_read=False):
            self.calls=[];self.failed_identity=failed_identity;self.write_error=write_error;self.malformed_read=malformed_read
        def __call__(self,name,args):
            self.calls.append((name,args))
            if name=='CreateFileW':return raw(101 if args['creation']==3 else 201)
            if name=='GetFileType':return raw(0 if self.failed_identity else 1)
            if name=='ReadFile':
                assert args['requested']==3
                return raw(True if self.malformed_read else 1,buffer=b'abc',count=3,count_defined=True,buffer_defined=True)
            if name=='WriteFile' and self.write_error is not None:raise self.write_error
            if name=='CloseHandle':return raw(1)
            raise AssertionError('Unexpected fake dispatch '+name)
    def build(api,clock=None,*,original=True):
        spec=P.FileSpec('D:\\Peer\\input.bin',3,hashlib.sha256(b'abc').hexdigest())
        box=[]
        P.begin_injected(clock or (lambda:0),lambda origin:box.append(P.PortableOwner(origin,api,lambda name:None,files=(spec,) if original else (),output='D:\\Peer\\output')))
        return box[0],spec
    def seed(owner,spec,*,kind='original_file',assume=False):
        identity='o0' if kind=='original_file' else 'w0'
        owner.seed_for_tests(namespace_owned=True,reservation_ready=True,slots=((identity,kind,101 if kind=='original_file' else 201,spec if kind=='original_file' else None),))
        if assume:owner.assume_seed_identity_for_tests(identity)
        return identity
    outcomes=[];errors=[]
    def probe(name,body):
        ACTIVE[0]=True
        try:outcomes.append(dict(id=name,passed=True,details=body()))
        except BaseException as error:errors.append(dict(id=name,error_class=type(error).__name__,error=str(error)[:512]))
        finally:ACTIVE[0]=False
    def failed_identity(original):
        api=API(failed_identity=True);o,s=build(api,original=original)
        o.seed_for_tests(namespace_owned=True,reservation_ready=True,slots=())
        caught=[]
        def action(owner):
            try:
                owner.open_original(s) if original else owner.open_output('verification-candidate.json','w0')
            except P.PortError as error:caught.append(error)
            slot=owner.slots[0];slot.identity_ok=True
            try:owner.assume_seed_identity_for_tests(slot.id)
            except P.PortError:pass
            else:raise AssertionError('Caught failed query converted to harness identity')
            owner.hash_capture(slot.id) if original else owner.write_record(slot.id,b'abc')
        r=o.run(action).to_dict();assert caught and r['primary']=='four_query_identity_required'
        assert r['api_attempts']['ReadFile']==r['api_attempts']['WriteFile']==0 and r['api_attempts']['CloseHandle']==1
        return dict(content_calls=0,close_calls=1,raw_boolean_not_authority=True)
    probe('caught_identity_failure_blocks_read',lambda:failed_identity(True))
    probe('caught_identity_failure_blocks_write',lambda:failed_identity(False))
    def missing_capability():
        a=API();o,s=build(a);seed(o,s);o.slots[0].identity_ok=True
        r=o.run(lambda owner:owner.hash_capture('o0')).to_dict()
        assert r['primary']=='four_query_identity_required' and r['api_attempts']['ReadFile']==0
        return dict(read_calls=0,identity_boolean_rejected=True)
    probe('seed_without_capability_is_not_identity',missing_capability)
    def valid_assumption():
        a=API();o,s=build(a);seed(o,s,assume=True)
        r=o.run(lambda owner:owner.hash_capture('o0')).to_dict()
        assert (r['known_read_bytes'],r['hashed_bytes'],r['captured_bytes'])==(3,3,3) and r['harness_identity_assumptions']==1
        assert r['test_seeded'] is True and r['FFI_registration_proven'] is r['production_owner_bound'] is False
        return dict(known=3,hashed=3,captured=3,harness_only=True)
    probe('explicit_pristine_harness_assumption',valid_assumption)
    def foreign_capability():
        aa=API();a,sa=build(aa);seed(a,sa);token=a.assume_seed_identity_for_tests('o0')
        ab=API();b,sb=build(ab);seed(b,sb);b._harness_identities['o0']=token
        r=b.run(lambda owner:owner.hash_capture('o0')).to_dict();a.run(lambda owner:None)
        assert r['primary']=='four_query_identity_required' and r['api_attempts']['ReadFile']==0
        return dict(foreign_owner_nonce_rejected=True,read_calls=0)
    probe('foreign_harness_identity_cannot_transfer',foreign_capability)
    def unreturned_write():
        marker=KeyboardInterrupt('synthetic entered write nonreturn');a=API(write_error=marker);o,s=build(a,original=False);seed(o,s,kind='output_file',assume=True)
        r=o.run(lambda owner:owner.write_record('w0',b'abc')).to_dict()
        assert o._primary_object is marker and r['write_count_unknown'] is True and r['known_write_bytes']==0
        assert r['api_attempts']['WriteFile']==1 and r['api_returns']['WriteFile']==0 and r['api_attempts']['CloseHandle']==1
        return dict(original_exception_identity=True,write_attempts=1,write_returns=0,unknown=True,known=0)
    probe('entered_write_nonreturn_is_unknown',unreturned_write)
    def read_precheck():
        values=iter((0,295,296,297));a=API();o,s=build(a,lambda:next(values));seed(o,s,assume=True)
        r=o.run(lambda owner:owner.hash_capture('o0')).to_dict()
        assert r['api_attempts']['ReadFile']==0 and r['read_count_unknown'] is False and o.slots[0].read_attempts==0
        assert r['api_attempts']['CloseHandle']==1 and r['known_read_bytes']==0
        return dict(read_attempts=0,unknown=False,known=0,cleanup_close=1)
    probe('read_preadmission_cutoff_is_known_no_call',read_precheck)
    def write_precheck():
        values=iter((0,300));a=API();o,s=build(a,lambda:next(values),original=False);seed(o,s,kind='output_file',assume=True)
        r=o.run(lambda owner:owner.write_record('w0',b'abc')).to_dict()
        assert r['api_attempts']['WriteFile']==r['api_attempts']['CloseHandle']==0 and r['write_count_unknown'] is False
        assert r['slots'][0]['close_state']=='not_dispatched_deadline' and r['known_write_bytes']==0
        return dict(write_attempts=0,unknown=False,known=0,posthard_API_calls=0)
    probe('write_preadmission_hard_cutoff_is_known_no_call',write_precheck)
    def malformed_read():
        a=API(malformed_read=True);o,s=build(a);seed(o,s,assume=True)
        r=o.run(lambda owner:owner.hash_capture('o0')).to_dict()
        assert r['api_attempts']['ReadFile']==r['api_returns']['ReadFile']==1 and r['read_count_unknown'] is True and r['known_read_bytes']==0
        assert o.slots[0].raw_reads[0].value is True
        return dict(returned_malformed_BOOL_retained=True,unknown=True,known=0)
    probe('entered_malformed_read_count_stays_unknown',malformed_read)
    assert pin(SOURCE)==source_pin
    record=dict(schema_version=1,status='passed' if not errors and not DENIALS else 'failed',recorded_at_utc=datetime.now(timezone.utc).isoformat(),source=source_pin,checker=pin(Path(__file__)),probes=len(outcomes)+len(errors),outcomes=outcomes,errors=errors,audit_denials=DENIALS,
        actual_Win32_FFI_calls=0,SDK_or_launcher_constructions=0,old_original_payload_operations=0,
        scope='Python fake behavior of portable primitives only. Harness identity is a fictional precondition, not observed four-query proof. Actual FFI raw-registration and production owner integration remain pending.',
        FFI_registration_qualified=False,production_owner_bound=False,profile_qualified=False,originals_authenticated=False,runtime_authorized=False)
    with OUT.open('x',encoding='utf-8',newline='\n') as out:json.dump(record,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(OUT),status=record['status'],probes=record['probes'])))
    if errors or DENIALS:raise SystemExit(1)

if __name__=='__main__':main()
