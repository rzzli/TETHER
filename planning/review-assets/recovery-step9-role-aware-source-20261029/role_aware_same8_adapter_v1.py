"""Eight focused tests for five known source families; frozen oracle untouched.

Expected causal facts come from the retained v1 counterexamples and DATA50ee.
The v1 BEFORE replay is retrospective after v2 source publication, not a claim
that this test module preceded the correction implementation.
"""
import copy
import unittest

def make_tests(D,modules,fixture,public,cohort,validator,observations):
 def world(callbacks=(),overrides=(),start=100,compiler=None,capture=True,claim=True,load=False):
  w=D.Runtime(modules,fixture,public,cohort,dict(binding_overrides=list(overrides),callback_rules=list(callbacks)))
  w.clock=D.Clock(start)
  if compiler is not None:w.compiler=compiler(w)
  D.invoke(w.S.start_injected,w.clock,w.setup)
  D.invoke(w.owner.admit_plan,w.specs,tuple(b['path'] for b in w.blobs[:2]),w.rules)
  if capture:
   D.invoke(w.owner.reserve_output,fixture['common']['output_key'])
   D.invoke(w.owner.capture_early)
  token=continuation=None
  if claim:
   token=D.invoke(w.owner.issue_continuation);continuation=D.invoke(token.claim)
  if load:
   module=D.invoke(w.owner.load_source,'cohort_entry')
   D.invoke(w.owner.check)
   actual=D.invoke(module.run)
   if actual!=('cohort-entry-v1','cohort-leaf-v1'):raise D.HarnessError('actual marker body mismatch')
   D.invoke(w.owner.check)
  return w,token,continuation
 def capture(w,name):
  calls=w.clock.calls;issued=D.invoke(w.owner.snapshot);legacy=D.projected_snapshot(w,issued);raw=D.invoke(legacy.to_dict)
  if calls!=w.clock.calls:raise D.HarnessError('focused snapshot sampledclock')
  # Retain selected actual facts before validating; no opaque token leakage.
  observations.append(dict(name=name,status=raw['status'],origin=raw['origin'],terminal=raw['terminal'],publications=raw['outputs']['publications'],loader=raw['loader'],calls=raw['calls'],byte_totals=raw['byte_totals'],binding_dispatches=len(w.binding.records),sink_callbacks=len(w.sink.records),violations=list(w.violations),primary_class=None if w.owner.primary is None else type(w.owner.primary).__name__,qualification=raw['qualification']))
  def token_check(token):
   error=w.owner.exception_for_token(token)
   return isinstance(error,BaseException) and (error is w.owner.primary or any(error is other for other in w.owner.secondary))
  D.invoke(validator.validate_snapshot,raw,diagnostic_identity_check=token_check)
  return raw
 def cleanup(w,original_origin=None):
  if w.owner.finalized:return
  if original_origin is not None and w.owner.origin is not original_origin:
   observations.append(dict(name='cleanup_not_admitted_after_origin_corruption',known_owned_originals_not_relabelled_closed=True))
   return
  D.invoke(w.owner.finalize,'incomplete')

 class FiveFamilyTests(unittest.TestCase):
  def test_normal_wrapper_return_keeps_returned_state_after_recorded_stop(self):
   overrides=[dict(api='ReadFile',file_id=0,occurrence=1,actions=[dict(hook='buffer_write',frame='cohort_leaf_read'),dict(hook='store_scalar',value=1),dict(hook='store_count',value=58),dict(hook='raise_exception',exception='err0',phase='after_count_before_aux')],**{'return':'normal_None'})]
   w,_,_=world(overrides=overrides,capture=False,claim=False)
   D.invoke(w.owner.reserve_output,fixture['common']['output_key'])
   try:
    try:D.invoke(w.owner.capture_early)
    except BaseException as caught:self.assertIs(caught,w.errors['err0'])
    else:self.fail('original recorded stop was suppressed')
    raw=capture(w,'normal_wrapper_return_stop')
    read=next(c for c in raw['calls'] if c['api']=='ReadFile')
    self.assertIs(w.owner.primary,w.errors['err0'])
    self.assertEqual(read['wrapper_return_observed'],True)
    self.assertEqual(read['wrapper_state'],'returned')
    self.assertEqual(read['stopped'],True)
    self.assertEqual(raw['byte_totals']['known_read_bytes'],58)
    self.assertEqual(raw['byte_totals']['hashed_bytes'],0)
    self.assertEqual(raw['byte_totals']['captured_bytes'],0)
    self.assertEqual(w.violations,[])
   finally:cleanup(w)

  def test_continuation_public_owner_is_readonly_bound_to_issuer(self):
   a,_,continuation=world();b,_,_=world()
   try:
    before=capture(a,'continuation_before_assignment')
    self.assertIsNot(a.owner,b.owner)
    self.assertEqual(a.owner.origin.start,b.owner.origin.start)
    rejected=False
    try:D.invoke(setattr,continuation,'owner',b.owner)
    except (TypeError,AttributeError,a.S.SharedOwnerError):rejected=True
    self.assertTrue(rejected,'ordinary public Continuation.owner reassignment accepted')
    self.assertIs(continuation.owner,a.owner)
    self.assertEqual(capture(a,'continuation_after_assignment'),before)
   finally:cleanup(a);cleanup(b)

  def test_original_owner_origin_is_readonly_not_renewed_by_other_origin(self):
   a,_,_=world();b,_,_=world(start=200,capture=False,claim=False)
   original=a.owner.origin
   try:
    a.clock.set(395)
    rejected=False
    try:D.invoke(setattr,a.owner,'origin',b.owner.origin)
    except (TypeError,AttributeError,a.S.SharedOwnerError):rejected=True
    actual=capture(a,'origin_assignment_attempt')
    self.assertTrue(rejected,'ordinary public origin reassignment renewed ownerwindow')
    self.assertIs(a.owner.origin,original)
    self.assertEqual((actual['origin']['start'],actual['origin']['work_end'],actual['origin']['hard_end']),(100,395,400))
    with self.assertRaises(a.S.SharedOwnerError):D.invoke(a.owner.check)
   finally:cleanup(a,original);cleanup(b)

  def _known_late_ack(self,kind,terminal_field):
   callbacks=[dict(target='publish_'+kind,occurrence=1,actions=[dict(action='clock_set',value=400)])]
   w,_,continuation=world(callbacks=callbacks,load=True)
   result=D.invoke(w.C.continue_once,continuation,w.C.Request(fixture['common']['output_key'],w.specs),*w.factories('exact','consistent'))
   raw=capture(w,'known_late_'+kind+'_ACK')
   actual=raw['outputs']['publications'][kind]
   self.assertTrue(actual['attempted'] and actual['return_observed'] and actual['acknowledged'])
   self.assertTrue(raw['terminal'][terminal_field],'known returned ACK lost in terminal projection')
   self.assertEqual(raw['origin']['now'],400)
   self.assertFalse(raw['terminal']['pure_owner_ack'])
   self.assertFalse(raw['terminal']['final_clock_passed'])
   self.assertFalse(raw['pure_seam_complete'])
   self.assertIn(raw['status'],('REFUSED','INCOMPLETE'))
   self.assertEqual(w.violations,[])
   self.assertEqual(w.sink.records[-1]['target'],'publish_'+kind)
   self.assertTrue(all(v is False for v in raw['qualification'].values()))

  def test_candidate_late_ACK_is_retained_without_completion(self):self._known_late_ack('candidate','candidate_acknowledged')
  def test_cleanup_late_ACK_is_retained_without_completion(self):self._known_late_ack('cleanup','cleanup_acknowledged')
  def test_receipt_late_ACK_is_retained_without_completion(self):self._known_late_ack('receipt','receipt_acknowledged')
  def test_seal_late_ACK_is_retained_without_completion(self):self._known_late_ack('seal','seal_acknowledged')

  def test_known_late_compiler_return_is_recorded_before_acceptance(self):
   def factory(w):
    def late(fullname,raw,resolver):
     self.assertEqual(fullname,'cohort_entry')
     self.assertEqual(raw,bytes.fromhex(w.blobs[1]['utf8_hex']))
     self.assertIs(raw,w.owner.early_context.bytes_for(w.blobs[1]['path']))
     # Deliberate late generic callback return, not a successful source stub.
     w.clock.set(395)
     return object()
    return late
   w,_,_=world(compiler=factory)
   try:
    with self.assertRaises(w.S.SharedOwnerError):D.invoke(w.owner.load_source,'cohort_entry')
    raw=capture(w,'known_late_compiler_return')
    self.assertEqual(raw['loader']['attempted'],['cohort_entry'])
    self.assertEqual(raw['loader']['returned'],['cohort_entry'])
    self.assertEqual(raw['loader']['records'][0]['return_observed'],True)
    self.assertEqual(raw['loader']['records'][0]['accepted'],False)
    self.assertEqual(raw['loader']['cache_hits'],[])
    self.assertEqual(w.owner.loader.loaded,{})
    self.assertFalse(raw['pure_seam_complete'])
    self.assertEqual(w.violations,[])
   finally:cleanup(w)
 return FiveFamilyTests
