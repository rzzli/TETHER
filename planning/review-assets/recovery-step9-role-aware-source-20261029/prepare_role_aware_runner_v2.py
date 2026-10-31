"""Root-authorized runner-only deadline closure; no subject execution."""
import hashlib
from pathlib import Path

H=Path(__file__).resolve().parent
raw=(H/'run_role_aware_independent_v1.py').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='088759d53cba839a72499ac4c5be724eaea33b53fab59bd95376115f78ef4ac6'
t=raw.decode()
facade='''class DeadlineCodecFacade:
    """Forward actual source functions/data under one cooperative deadline.

    No source callback site is added. Only the supplied callback is wrapped;
    actual FormatError and actual DecodedLedger objects are exposed unchanged.
    A callback-free hang has no hard bound without a separately owned watchdog.
    """
    def __init__(self,actual,deadline):
        self.actual=actual;self.deadline=deadline;self.FormatError=actual.FormatError
        self.stats=dict(facade_attempts=0,preforward_deadline_refusals=0,actual_encode_calls=0,actual_decode_calls=0,
            actual_source_check_sites=0,original_callback_calls=0,original_callback_returns=0,original_callback_exceptions=0,
            actual_source_returns=0,actual_source_exceptions=0,postcall_late_vetoes=0,late_seen=False)
    def _late(self):
        late=time.monotonic()>=self.deadline
        if late:self.stats['late_seen']=True
        return late
    def _guard(self,where):
        if self._late():raise TimeoutError('original cooperative suite deadline: '+where)
    def _call(self,which,value,check):
        self.stats['facade_attempts']+=1
        try:self._guard('before actual codec call')
        except BaseException:
            self.stats['preforward_deadline_refusals']+=1
            raise
        def wrapped():
            self.stats['actual_source_check_sites']+=1
            self._guard('before original check callback')
            self.stats['original_callback_calls']+=1
            try:result=check()
            except BaseException:
                # Record lateness without replacing the ORIGINAL exception.
                self.stats['original_callback_exceptions']+=1
                self._late()
                raise
            self.stats['original_callback_returns']+=1
            self._guard('after original check callback')
            return result
        function=self.actual.encode_ledger if which=='encode' else self.actual.decode_ledger
        self.stats['actual_'+which+'_calls']+=1
        try:result=function(value,check=wrapped)
        except BaseException:
            self.stats['actual_source_exceptions']+=1
            self._late() # Never mask an original callback or source exception.
            raise
        self.stats['actual_source_returns']+=1
        if self._late():
            self.stats['postcall_late_vetoes']+=1
            raise TimeoutError('original cooperative suite deadline after actual codec return')
        return result
    def encode_ledger(self,value,*,check):return self._call('encode',value,check)
    def decode_ledger(self,value,*,check):return self._call('decode',value,check)


'''
assert t.count('class Results(unittest.TextTestResult):')==1
t=t.replace('class Results(unittest.TextTestResult):',facade+'class Results(unittest.TextTestResult):')
t=t.replace("D=None;binding=None;source_pins={};modules={};record=None;codec_result=None;runs=[];focused=[]",
            "D=None;binding=None;source_pins={};modules={};record=None;codec_result=None;codec_forwarding=None;runs=[];focused=[]")
assert t.count("codec_result=T.run(modules['role_ledger_codec_v1'],corpus)")==1
t=t.replace("codec_result=T.run(modules['role_ledger_codec_v1'],corpus)\n            status='PASS' if codec_result['status']=='PASS' else 'FIRST_FAILURES_RETAINED'",
            "facade=DeadlineCodecFacade(modules['role_ledger_codec_v1'],started+60)\n            codec_result=T.run(facade,corpus)\n            late_suite_veto=facade._late()\n            codec_forwarding=dict(facade.stats)\n            codec_forwarding['post_suite_late_veto']=late_suite_veto\n            status='PASS' if codec_result['status']=='PASS' and not late_suite_veto else 'FIRST_FAILURES_RETAINED'")
t=t.replace('codec=codec_result,legacy_runs=runs,same8_observations=focused,',
            'codec=codec_result,codec_forwarding=codec_forwarding,legacy_runs=runs,same8_observations=focused,')
t=t.replace('message=str(err)[:2048],traceback=traceback.format_exc(),codec=codec_result,legacy_runs=runs,same8_observations=focused,',
            'message=str(err)[:2048],traceback=traceback.format_exc(),codec=codec_result,codec_forwarding=codec_forwarding,legacy_runs=runs,same8_observations=focused,')
t=t.replace("clocks='Single real suite deadline bounds tests only. Every genuine owner retains its own original synthetic100/395/400 clock; readonly negative projection does not resample it.',",
            "clocks='One original real60s cooperative suite deadline is checked around actual codec calls/original callbacks and after the suite. Original callback exceptions/False returns remain unchanged. Every genuine owner retains original synthetic100/395/400 clock; readonly negative projection does not resample it.',\n            hard_wall_time_guard=False,callback_free_hang_bound='UNKNOWN_NO_OWNED_OUTER_WATCHDOG',")
t=t.replace('ROLE-AWARE-INDEPENDENT-SOURCE-BINDING-v1.json','ROLE-AWARE-INDEPENDENT-SOURCE-BINDING-v2.json')
t=t.replace("+'-PROOF-v1.json'","+'-PROOF-v2.json'")
t=t.replace("+'-ATTEMPT-v1.json'","+'-ATTEMPT-v2.json'")
t=t.replace('ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v1.json','ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v2.json')
assert 'Single real suite deadline bounds tests' not in t
with (H/'run_role_aware_independent_v2.py').open('x',encoding='utf-8',newline='\n') as f:f.write(t)
print('Prepared run_role_aware_independent_v2.py; subject imports/runs0')
