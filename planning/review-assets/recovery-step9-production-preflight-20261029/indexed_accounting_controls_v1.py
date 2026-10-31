"""PRE-CODE six-control module: deterministic call-list visits, not timing.

No subject is imported or run at module import. make_tests receives fresh
accepted modules and fixed synthetic input metadata from an external runner.
indexed=False uses actual V2 append/store boundaries, never absent helpers.
"""
import copy
import unittest

class CountingList(list):
 def __init__(self):super().__init__();self.after_append=None;self.reset()
 def reset(self):self.counts=dict(iterated_items=0,membership_items=0,direct_index_items=0,slice_copied_items=0,len_calls=0,append_calls=0)
 def __iter__(self):
  for item in list.__iter__(self):self.counts['iterated_items']+=1;yield item
 def __contains__(self,needle):
  for item in list.__iter__(self):
   self.counts['membership_items']+=1
   if item is needle or item==needle:return True
  return False
 def __getitem__(self,key):
  value=list.__getitem__(self,key)
  if type(key) is slice:self.counts['slice_copied_items']+=list.__len__(value)
  else:self.counts['direct_index_items']+=1
  return value
 def __len__(self):self.counts['len_calls']+=1;return list.__len__(self)
 def append(self,value):
  self.counts['append_calls']+=1;list.append(self,value)
  if self.after_append is not None:self.after_append(value)
 def sample(self):return dict(self.counts)

def make_tests(D,modules,fixture,public,cohort,validator,observations,*,indexed=False):
 S=modules['shared_owner_v1'];P=modules['shared_file_ports_v1']
 def start_world(level='all',script=None):
  w=D.Runtime(modules,fixture,public,cohort,script or dict(binding_overrides=[],callback_rules=[]))
  original=S.Registry.__init__
  def counted_init(registry,owner):
   original(registry,owner)
   if registry._calls:raise D.HarnessError('instrumentation after facts would copy authority')
   object.__setattr__(registry,'_calls',CountingList())
  S.Registry.__init__=counted_init
  try:D.invoke(S.start_injected,w.clock,w.setup)
  finally:S.Registry.__init__=original
  calls=w.owner.registry._calls
  D.invoke(w.owner.admit_plan,w.specs,tuple(b['path'] for b in w.blobs[:2]),w.rules)
  D.invoke(w.owner.reserve_output,fixture['common']['output_key'])
  if level=='empty':return w,calls
  D.invoke(w.owner.capture_early)
  if level in ('metadata_identity','all'):
   ref=D.invoke(w.view.acquire,w.specs[2]);D.invoke(w.view.inspect,ref)
   if level=='all':D.invoke(w.view.hash_capture,ref)
  return w,calls
 def snapshot(w,calls,name):
  calls.reset() # EXPLICIT allowed cold-report window, not hidden in hot probe.
  raw=D.invoke(w.owner.snapshot).to_dict()
  def identity(token):
   error=w.owner.exception_for_token(token)
   return isinstance(error,BaseException) and (error is w.owner.primary or any(error is e for e in w.owner.secondary))
  D.invoke(validator.validate_snapshot,raw,diagnostic_identity_check=identity)
  observations.append(dict(name=name,window='canonical_report_allowed',metrics=calls.sample(),calls=len(raw['calls']),known=raw['byte_totals'],last_call=None if not raw['calls'] else raw['calls'][-1],primary=None if w.owner.primary is None else type(w.owner.primary).__name__,qualification=raw['qualification']))
  return raw
 def cleanup(w):
  if not w.owner.finalized:D.invoke(w.owner.finalize,'incomplete')
  if w.violations:raise D.HarnessError('monitor violations: '+repr(w.violations))
 def hot(test,w,calls,name,action,expected):
  r=list.__len__(calls);calls.reset()
  actual=D.invoke(action);metrics=calls.sample()
  observations.append(dict(name=name,window='clean_hot',canonical_records=r,metrics=metrics,actual=actual if type(actual) in (int,str,bool,type(None)) else 'actual_canonical_state',expected=expected))
  if expected is not None:test.assertEqual(actual,expected)
  test.assertEqual(metrics['iterated_items'],0,'hot canonical iteration is linear in prior calls')
  test.assertEqual(metrics['membership_items'],0,'hot canonical membership is a scan')
  test.assertEqual(metrics['slice_copied_items'],0,'hot canonical slice copied records')
  test.assertLessEqual(metrics['direct_index_items'],16)
  test.assertLessEqual(metrics['len_calls'],32)
  return actual
 def canonical_error_checks(test,w,calls,error,name,known):
  first=snapshot(w,calls,name+'_first_report');second=snapshot(w,calls,name+'_second_report')
  test.assertIs(w.owner.primary,error)
  test.assertFalse(any(error is e for e in w.owner.secondary),'same original error double-latched')
  test.assertEqual(first['byte_totals']['known_read_bytes'],known)
  test.assertEqual(second['byte_totals'],first['byte_totals'])
  test.assertFalse(first['pure_seam_complete'])
  if indexed:
   test.assertIs(w.owner._accounting_fault,error)
   # Reporting is not a cache repair or a fresh eligibility stamp.
   for _ in range(2):
    with test.assertRaises(BaseException):D.invoke(w.owner.read_known,w.owner.file_state(w.owner.file_ref(w.blobs[0]['path'])))
    test.assertIs(w.owner._accounting_fault,error)
  before=len(w.binding.records)
  with test.assertRaises(BaseException):D.invoke(w.view.acquire,w.specs[1])
  test.assertEqual(len(w.binding.records),before,'fresh work reached binding after fault')
  return first

 class Controls(unittest.TestCase):
  def test_01_clean_handle_no_global_scan(self):
   w,calls=start_world()
   try:
    file=w.owner.file_state(w.owner.file_ref(w.blobs[2]['path']))
    hot(self,w,calls,'handle',lambda:w.owner.handle(file),103)
   finally:cleanup(w)

  def test_02_clean_known_bytes_no_global_scan(self):
   w,calls=start_world()
   try:
    file=w.owner.file_state(w.owner.file_ref(w.blobs[2]['path']))
    hot(self,w,calls,'read_known',lambda:w.owner.read_known(file),68)
   finally:cleanup(w)

  def test_03_real_ref_guard_no_membership_scan(self):
   w,calls=start_world();other,other_calls=start_world('empty')
   try:
    foreign=D.invoke(other.view.acquire,other.specs[0]);foreign_call=other.binding.actual_refs[0]
    hooks=P.AdoptionHooks(w.owner);ref=w.binding.actual_refs[-1]
    calls.reset();actual=D.invoke(hooks._state,ref);measured=calls.sample()
    # Invalid same-type/ordinal ref STILL refused, measured separately.
    with self.assertRaises(S.SharedOwnerError):D.invoke(hooks._state,foreign_call)
    self.assertIs(actual,ref._state)
    observations.append(dict(name='ref_membership',window='clean_hot',canonical_records=list.__len__(calls),metrics=measured,foreign_genuine_ref_rejected=True))
    self.assertEqual(measured['iterated_items'],0);self.assertEqual(measured['membership_items'],0)
    self.assertLessEqual(measured['direct_index_items'],16)
   finally:cleanup(w);cleanup(other)

  def test_04_real_read_admission_no_global_quota_scan(self):
   w,calls=start_world('metadata_identity')
   try:
    file=w.owner.file_state(w.owner.file_ref(w.blobs[2]['path']))
    before_clock=w.clock.calls
    c=hot(self,w,calls,'read_admission',lambda:w.view._call('ReadFile',file,dict(handle=103,requested=68,overlapped=None),68),None)
    self.assertEqual((c.scalar,c.count),(1,68))
    self.assertGreaterEqual(w.clock.calls-before_clock,2,'do not replace original pre/post clocks with no-ops')
    self.assertEqual(calls.counts['append_calls'],1)
   finally:cleanup(w)

  def test_05_reserved_index_failure_raw_unentered_and_cleanup(self):
   modes=('canonical_append_after','before','after') if indexed else ('canonical_append_after',)
   for mode in modes:
    with self.subTest(mode=mode):
     w,calls=start_world('metadata_identity');error=MemoryError('reserved index interruption')
     restore=None
     if indexed and mode!='canonical_append_after':
      original=S.SharedOwner._index_reserved_call
      def interrupted(owner,c):
       if c.api=='ReadFile' and c.file.id==2:
        w.binding.stopped=True
        if mode=='after':original(owner,c)
        raise error
       return original(owner,c)
      S.SharedOwner._index_reserved_call=interrupted
      restore=lambda:setattr(S.SharedOwner,'_index_reserved_call',original)
     else:
      def append_fault(c):
       if c.api=='ReadFile' and c.file.id==2:w.binding.stopped=True;raise error
      calls.after_append=append_fault
      restore=lambda:setattr(calls,'after_append',None)
     try:
      try:D.invoke(w.view.hash_capture,w.owner.file_ref(w.blobs[2]['path']))
      except BaseException as actual:self.assertIs(actual,error)
      else:self.fail('reservation fault suppressed')
      raw=canonical_error_checks(self,w,calls,error,'index_'+mode,141)
      last=raw['calls'][-1]
      self.assertEqual(last['api'],'ReadFile');self.assertIs(last['invocation_reserved'],False)
      self.assertEqual(last['raw_scalar'],dict(tag='UNOBSERVED',value=None))
      self.assertEqual(last['raw_count'],dict(tag='UNOBSERVED',value=None))
      self.assertIs(raw['byte_totals']['read_count_unknown'],False)
      self.assertEqual(sum(r['api']=='ReadFile' and r['file_id']==2 for r in w.binding.records),0)
      if indexed:self.assertIs(last['stopped'],True)
     finally:
      restore();cleanup(w)
      final=w.owner.snapshot().to_dict();self.assertTrue(all(f['close_invocations']==1 for f in final['files']))

  def test_06_count_fold_raw_first_before_after_and_healthy_replay(self):
   modes=('before','after') if indexed else ('raw_count_after',)
   for mode in modes:
    with self.subTest(mode=mode):
     w,calls=start_world('empty');error=MemoryError('defined count fold interruption')
     if indexed:
      original=S.SharedOwner._fold_read_fact
      def interrupted(owner,c):
       if c.api=='ReadFile' and c.file.id==0 and c.count is not S.UNOBSERVED:
        w.binding.stopped=True
        if mode=='after':original(owner,c)
        raise error
       return original(owner,c)
      S.SharedOwner._fold_read_fact=interrupted
      restore=lambda:setattr(S.SharedOwner,'_fold_read_fact',original)
     else:
      original=P.AdoptionHooks.store_count
      def interrupted(hooks,ref,value):
       original(hooks,ref,value)
       if ref.api=='ReadFile' and ref.file_ref.id==0:w.binding.stopped=True;raise error
      P.AdoptionHooks.store_count=interrupted
      restore=lambda:setattr(P.AdoptionHooks,'store_count',original)
     try:
      try:D.invoke(w.owner.capture_early)
      except BaseException as actual:self.assertIs(actual,error)
      else:self.fail('fold fault suppressed')
      raw=canonical_error_checks(self,w,calls,error,'fold_'+mode,58)
      read=next(c for c in raw['calls'] if c['api']=='ReadFile')
      self.assertEqual(read['raw_scalar'],dict(tag='BOOL32',value=1));self.assertEqual(read['raw_count'],dict(tag='COUNT32',value=58))
      self.assertIs(read['count_aux_ack'],False);self.assertTrue(read['count_defined'])
      self.assertEqual((raw['byte_totals']['hashed_bytes'],raw['byte_totals']['captured_bytes']),(0,0))
     finally:restore();cleanup(w)
   # A committed healthy identical cell may be re-observed; it contributes once.
   w,calls=start_world('empty')
   try:
    ref=D.invoke(w.view.acquire,w.specs[0]);D.invoke(w.view.inspect,ref);D.invoke(w.view.hash_capture,ref)
    call=w.binding.actual_refs[-1];file=w.owner.file_state(ref);hooks=P.AdoptionHooks(w.owner)
    self.assertEqual(D.invoke(w.owner.read_known,file),58)
    D.invoke(hooks.store_count,call,58);D.invoke(hooks.store_count,call,58)
    self.assertEqual(D.invoke(w.owner.read_known,file),58)
    raw=snapshot(w,calls,'healthy_identical_count_replay');self.assertEqual(raw['byte_totals']['known_read_bytes'],58)
    if indexed:self.assertEqual((call._state._read_contribution,call._state._read_fold_phase),(58,'committed'))
   finally:cleanup(w)
   # Partial pair is unknown, whereas a defined raw0 is a real zero contribution.
   for kind in ('partial_scalar','defined_zero'):
    actions=[dict(hook='buffer_write',frame='cohort_leaf_read'),dict(hook='store_scalar',value=1)]
    if kind=='partial_scalar':actions+=[dict(hook='raise_exception',exception='mem',phase='after_scalar_before_aux')]
    else:actions+=[dict(hook='store_count',value=0)]
    rule=dict(api='ReadFile',file_id=0,occurrence=1,actions=actions,**{'return':'throw_original' if kind=='partial_scalar' else 'normal_None'})
    w,calls=start_world('empty',dict(binding_overrides=[rule],callback_rules=[]))
    try:
     with self.assertRaises(BaseException):D.invoke(w.owner.capture_early)
     raw=snapshot(w,calls,kind);read=next(c for c in raw['calls'] if c['api']=='ReadFile')
     self.assertEqual(raw['byte_totals']['known_read_bytes'],0)
     self.assertIs(read['count_defined'],kind=='defined_zero')
     self.assertIs(raw['byte_totals']['read_count_unknown'],kind=='partial_scalar')
     if indexed:
      state=next(ref._state for ref in w.binding.actual_refs if ref.api=='ReadFile')
      self.assertIs(state._read_contribution,None) if kind=='partial_scalar' else self.assertEqual(state._read_contribution,0)
    finally:cleanup(w)
 return Controls
