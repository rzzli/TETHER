"""Author closed synthetic schedules/expectations BEFORE any cohort source.

This file frames literal inputs and authored causal assertions. It neither
imports reviewed components nor interprets state transitions or executes toys.
"""
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(name,digest):
 path=HERE/name;assert pin(path)['sha256']==digest
 return json.loads(path.read_bytes())
def write(name,value):
 with (HERE/name).open('xb') as out:out.write((json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8'))
PUBLIC=read('SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json','50ee2d7a9285370e6a3f0d18801c43e441b327f7ceac9eb46ebdf0463eff28d6')
COHORT=read('SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json','eb5147d200bcc0108b71968d69f6b251c29b56dd52d926a8606504682134d9b8')
ROSTER=read('SHARED-OWNER-INTEGRATION-HISTORY-ROSTER-DRAFT-v1.json','ec53fce7dbb317bb284b0c8924eac4655b28c04df86166178b4538191cb0850a')
INPUTS=read('SHARED-OWNER-INTEGRATION-BINDING-INPUTS-DRAFT-v1.json','3c9f1c84571f740affa7f9730b4afe7c88c4d9724669557d3202b122dd1aa2c3')
assert not (HERE/'shared_owner_v1.py').exists() and not (HERE/'shared_file_ports_v1.py').exists() and not (HERE/'continue_verification_v1.py').exists()

operations={
 'setup': ['op'],
 'admit': ['op','spec_variant'],
 'reserve': ['op'],
 'capture_early': ['op'],
 'issue': ['op'],
 'claim': ['op'],
 'load': ['op','module'],
 'probe_load_refused': ['op','module'],
 'probe_claim_refused': ['op'],
 'continue': ['op','factory_variant','verdict'],
 'finalize_incomplete': ['op'],
 'close': ['op','file_id'],
 'clock_set': ['op','value'],
 'foreign_control': ['op','control'],
 'emit': ['op','event','details','cleanup'],
 'mutate_issued': ['op'],
 'diagnostic_foreign_control': ['op'],
 'probe_forbidden_claimed_keyword': ['op','keyword','value'],
 'snapshot': ['op','name'],
}
schema=dict(schema_version=1,status='CLOSED_LITERAL_INTERCHANGE_BEFORE_COMPONENT_IMPLEMENTATION',
 public_schema=pin(HERE/'SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json'),
 proposal=pin(HERE/'SHARED-OWNER-CONTINUATION-PROPOSAL-v2.json'),
 root_scope=pin(HERE/'SHARED-OWNER-ROOT-PREPARATION-SCOPE-v2.json'),
 cohort=pin(HERE/'SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json'),
 bounds=dict(histories=48,groups=14,steps_per_history=32,binding_actions_per_rule=12,overlay_rules_per_history=17,assertions_per_history=180,fixture_bytes=2097152),
 case_exact_keys=['id','group','steps','binding_overrides','callback_rules','checks','external_identity_checks','coverage'],
 spec_variants=['exact','canonical_alias','N5_B3_M3_invalid'],
 factory_variants=['exact','role_changed','capture_changed','hash_changed','unbranded','foreign_context','foreign_factory_owner','foreign_authority_owner'],
 factory_variant_rule='exact uses canonical tuple/orderedfourIDs. role_changed/capture_changed/hash_changed alter ONLY early leaf metadata returned by branded authority, not its bytes. unbranded returns ordinary dict from the wrapped checker callback. foreign_context returns TestObservation bound to the SAME owner-issued stale EarlySourceContext instead of current EvidenceContext (no fake context constructor/ready dict); this is exact-context/type refusal, not an isolated cross-owner-full-context proof. Foreign factory/authority owner uses a second genuine synthetic owner with same100/395/400 numericclock and metadata-only admitted roster, ZERO original dispatch; its refs are never adopted into subject.',
 spec_variant_rule='canonical_alias adds a fourth descriptor with uppercase/slash equivalent leaf path using same literalbytes/hash. N5_B3_M3_invalid supplies five duplicate existing descriptors/three early references/duplicate module rules; reject malformed pre-admission, not an isolated proof of allthree cap branches. No additional file contents or original labels are supplied.',
 step_exact_keys=operations,
 check_exact_keys=['at','path','relation','value'],
 check_relations=['eq','len','le','ge','unchanged_since','all_false','original_exception_is','no_exception_leaves','same_object'],
 check_paths='Closed public snapshot paths only; dotted dict keys and bounded numeric list indices. At=checkpoint name or final. len applies only to a listed source array. No eval/executable snippets. same_object/original identity are external harness assertions, not trusted report flags.',
 binding_override_exact_keys=['api','file_id','occurrence','actions','return'],
 binding_action_exact_shapes=dict(buffer_write=['hook','frame'],store_scalar=['hook','value'],store_count=['hook','value'],store_error=['hook','value','defined'],aux=['hook','field'],raise_exception=['hook','exception','phase'],clock_set=['hook','value'],throw=['hook','exception']),
 binding_override_rule='Generic binding invokes ONLY the seven exact proposal hook methods on current source CallRef. Rules match api/currentfileordinal/occurrence; rule/case/fault labels and expected data never enter source. return is normal_None or throw_original. Baseline inputs supply valid bytes/scalars for unmodified calls; only owned-file cleanup inputs remain permitted after a failed prefix. No conditional source recovery or retries are generated.',
 callback_rule_exact_keys=['target','occurrence','actions'],
 callback_targets=['reserve','append','publish_seal','hash_update','copy_bytes','before_final_ack','compiler_entry','checker_archive'],
 callback_actions=['return_foreign_ack','throw_original','clock_set','emit_forbidden','resolve_undeclared','return_foreign_context'],
 callback_action_exact_shapes=dict(return_foreign_ack=['action'],throw_original=['action','exception'],clock_set=['action','value'],emit_forbidden=['action','event','details','cleanup'],resolve_undeclared=['action','module'],return_foreign_context=['action']),
 callback_rule='All callbacks are generic SYNTHETIC_ONLY harness objects. Error references mint one original object per id. Hash/copy hooks are BEFORE commit, before_final_ack AFTER sealACK and BEFORE final clock/issue. No source case selector or fake ready predicate.',
 foreign_control_rules={
 'equal_time_other_owner_factory':'Create another legitimate synthetic owner with start100/work395/hard400 and no original dispatch; use its branded factory with subject Continuation. This is a composite actual-owner/Origin/nonce identity test, not isolated field mutation.',
 'other_owner_nonce_factory':'Other owner same descriptors/times; its source-issued wrapper/nonce must refuse at subject continuation before remaining acquire.',
 'other_registry_file_ref':'Other owner admits same metadata only; subject FilePortView.inspect(other.file_ref(path0)) refuses before any query. Do not copy handle or ready dict.',
 'other_owner_port':'Subject already has its legitimate view after setup; attempt to rebind other actual owner FilePortView before plan. Reject without replacing original port. Composite once-binding/foreign-owner control, not isolated portpredicate order. No private mutation.',
 'copied_dict_continuation':'Pass ordinary copied report-shaped dict to continue_once. No source owner may be inferred from that dict. Harness records external rejection then subject.finalize(incomplete).',
 'second_claim':'Call same genuine token.claim twice; no second event/owner/source execution.',
 },
 driver_setup_rule='The generic setup op runs INSIDE start_injected setup: constructs canonical FileSpecs/ModuleRules from cohort metadata, creates subject FilePortView/fake sink and binds compiler/TestHooks once. Tests for foreign refs may mint a separate legitimate metadata-only peer owner with equal numericclock, never reset/adopt it into subject. Hooks/compilers/factory callbacks receive no case id/fault label/expected data. Ordinary compiler execution is future authorized source-test work only, not preparation.',
 expected_comparison='Integers/flags/atoms strictly typed. Time fields allow equal finite nonbool int/float values. Source-issued tokens are inspected before label normalization; own exception getter must preserve actual identity. Every snapshot/result has exact PUBLIC record keys and false qualification. The harness observes callback bytes directly for packet/row bounds, canonical framing and SHA, never derives expected semantic verdict from an owner report.',
 exception_inputs=dict(err0=dict(type='RuntimeError',message='synthetic original stop'),ki=dict(type='KeyboardInterrupt',message='synthetic interruption'),se=dict(type='SystemExit',message='synthetic exit'),mem=dict(type='MemoryError',message='synthetic allocation stop'),timeout=dict(type='TimeoutError',message='synthetic late observation'),source_error=dict(type='SharedOwnerError',code='INVALID_INPUT')),
 finalize_policy='Only continue_once finalizes after engine entry. A failed/rejected bootstrap prefix calls public owner.finalize("incomplete") once; that cannot mint normal/negative gates. For external unentered TypeError checkpoint snapshot is unchanged before separate incomplete cleanup. Never finalize a returned result twice.',
 step_error_policy='An expected error in an ordinary step skips subsequent ordinary work. A specifically declared probe_load_refused/probe_claim_refused/foreign_control is a deliberate fail-closed guard assertion, not a recovery/retry. KI/SE/work/hard-stop paths admit only snapshot and once-finalize cleanup. A valid Continuation entering continue_once owns its finally even on factory refusal; never call external finalize afterward. Source code receives only individual generic calls/bytes/refs/original exceptions, not this policy or expected data.',
 external_identity_applicability='Always require actual subject owner/Origin/nonce/registry/port/sink/journal identity across phases where bound. Loader/early/full contexts/blob identity checks require the declared issued references; missing contexts must match their declared null/partial state and are NOT counted as successful None-is-None identity checks.',
 physical_and_real_nonclaims='All sink callbacks are fictional. No original source/physical Win32/FFI/first-entry/real checker/profile qualification follows from any complete pure-seam status.',
 implementation_authorized=False,actual_API_calls=0)
write('SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v1.json',schema)

def step(op,**kwargs):return dict(op=op,**kwargs)
SETUP=[step('setup'),step('admit',spec_variant='exact'),step('reserve'),step('capture_early')]
CLAIM=SETUP+[step('issue'),step('claim')]
LOADED=CLAIM+[step('load',module='cohort_entry')]
BASE=LOADED+[step('continue',factory_variant='exact',verdict='consistent')]
def ck(path,value,relation='eq',at='final'):return dict(at=at,path=path,relation=relation,value=value)
def vals(mapping,at='final'):return [ck(k,v,at=at) for k,v in mapping.items()]
common=vals({'scope':'pure_shared_owner_seam','phase':'FINALIZED','finalized':True,'origin.start':100,'origin.work_end':395,'origin.hard_end':400})+[ck('qualification',PUBLIC['qualification_exact'])]
normal=vals({'status':'PURE_SEAM_COMPLETE_CONSISTENT','pure_seam_complete':True,'refusal_code':None,'origin.now':100,'plan.N':3,'plan.B':2,'plan.M':2,'plan.R':51,'plan.C':69,'plan.E':218,'plan.calls_used':21,'plan.events_used':53,'byte_totals.known_read_bytes':209,'byte_totals.hashed_bytes':209,'byte_totals.captured_bytes':209,'byte_totals.early_known_read_bytes':141,'byte_totals.early_hashed_bytes':141,'byte_totals.early_captured_bytes':141,'byte_totals.remaining_known_read_bytes':68,'byte_totals.remaining_hashed_bytes':68,'byte_totals.remaining_captured_bytes':68,'byte_totals.early_reopens_after_claim':0,'byte_totals.early_rehashes_after_claim':0,'byte_totals.read_count_unknown':False,'early_context.file_ids':[0,1],'early_context.captured_bytes':141,'evidence_context.file_ids':[0,1,2],'evidence_context.captured_bytes':209,'loader.attempted':['cohort_entry','cohort_leaf'],'loader.returned':['cohort_leaf','cohort_entry'],'journal.reservation':218,'journal.next_sequence':53,'journal.closed':True,'journal.close_acknowledged':True,'errors.primary':None,'errors.secondary':[],'gates':PUBLIC['required_gate_order'],'terminal.original_closures_complete':True,'terminal.seal_acknowledged':True,'terminal.final_clock_passed':True,'terminal.pure_owner_ack':True,'terminal.result_issued':True})+[ck('files',3,'len'),ck('calls',21,'len'),ck('journal.events',53,'len')]
for api in ('CreateFileW','GetFileType','GetFileInformationByHandleEx','GetFinalPathNameByHandleW','GetFileSizeEx','ReadFile','CloseHandle'):
 for field in ('reserved','invocations','scalar_returns','wrapper_returns'):normal.append(ck('api_counters.'+api+'.'+field,3))
 normal.append(ck('api_counters.'+api+'.count_values',3 if api=='ReadFile' else 0))
for i,n in enumerate((58,83,68)):
 normal+=vals({f'files.{i}.known_read_bytes':n,f'files.{i}.hashed_bytes':n,f'files.{i}.captured_bytes':n,f'files.{i}.open_invocations':1,f'files.{i}.read_invocations':1,f'files.{i}.close_invocations':1,f'files.{i}.close_return_observed':True,f'files.{i}.close_success':True,f'files.{i}.hash_complete':True,f'files.{i}.capture_complete':True})
identity=['same_subject_owner_origin_nonce_registry_port_sink_loader_journal','same_canonical_file_refs_across_capture_claim_controller_close','same_early_context_and_same_early_blob_objects_in_full_context','no_new_subject_owner_origin_output_or_close_right','source_snapshot_has_no_live_exception_or_mutable_record_leaves']
cases=[]
for row in ROSTER['cases']:
 cases.append(dict(id=row['id'],group=row['group'],steps=copy.deepcopy(BASE),binding_overrides=[],callback_rules=[],checks=copy.deepcopy(common)+vals({'pure_seam_complete':False,'terminal.pure_owner_ack':False}),external_identity_checks=identity.copy(),coverage=[row['authored_causal_expectation']]))
BY={c['id']:c for c in cases}
def choose(identity,steps=None,expect=None,normal_result=False):
 c=BY[identity]
 if steps is not None:c['steps']=copy.deepcopy(steps)
 c['checks']=copy.deepcopy(common)+(copy.deepcopy(normal) if normal_result else vals({'pure_seam_complete':False,'terminal.pure_owner_ack':False}))
 if expect:c['checks']+=vals(expect)
 return c
def before_engine(c,steps):c['steps']=copy.deepcopy(steps)+[step('finalize_incomplete')]
def bind_rule(c,api,file_id,actions,ret='normal_None',occurrence=1):
 c['binding_overrides'].append(dict(api=api,file_id=file_id,occurrence=occurrence,actions=actions,**{'return':ret}))
def callback(c,target,actions):c['callback_rules'].append(dict(target=target,occurrence=1,actions=actions))
def action(hook,**kwargs):return dict(hook=hook,**kwargs)

choose('baseline_consistent',normal_result=True)
c=choose('baseline_core_negative',normal_result=True);c['steps'][-1]['verdict']='negative'
next(x for x in c['checks'] if x['path']=='status')['value']='PURE_SEAM_COMPLETE_NEGATIVE'
c['checks']+=vals({'stages.7.verdict':'negative'})
c=choose('work_cutoff_before_stage',expect={'origin.now':395,'byte_totals.known_read_bytes':141,'byte_totals.hashed_bytes':141,'byte_totals.captured_bytes':141,'files.2.open_invocations':0,'terminal.seal_acknowledged':False})
c['steps']=copy.deepcopy(LOADED)+[step('clock_set',value=395),step('continue',factory_variant='exact',verdict='consistent')]
c['coverage']+=['Clock already spent289seconds at a preceding checkpoint389; advance to395 before continuation. No new work clock.']
c['steps'].insert(4,step('clock_set',value=389))
c=choose('hard_cutoff_before_cleanup',expect={'origin.now':400,'terminal.pure_owner_ack':False,'outputs.publications.seal.attempted':False})
before_engine(c,CLAIM+[step('clock_set',value=400)])

foreign_ops={'foreign_origin':'equal_time_other_owner_factory','foreign_nonce':'other_owner_nonce_factory','foreign_registry':'other_registry_file_ref','foreign_port':'other_owner_port','copied_continuation_dict':'copied_dict_continuation','repeated_continuation_claim':'second_claim'}
for name,control in foreign_ops.items():
 c=choose(name,expect={'byte_totals.early_reopens_after_claim':0,'byte_totals.early_rehashes_after_claim':0})
 prefix=[step('setup')] if name=='foreign_port' else copy.deepcopy(CLAIM)
 before_engine(c,prefix+[step('foreign_control',control=control)])
 c['coverage']+=['Composite actual-identity rejection; equal numeric fields are not isolated identity authority. Other owner does not dispatch originals.']
 if name=='repeated_continuation_claim':c['checks']+=vals({'journal.next_sequence':15},at='after_rejected_control')
# Factory/owner controls enter the legitimate subject continuation, so its
# controller owns finalization; the bootstrap driver must not finalize twice.
for name,variant in [('foreign_origin','foreign_factory_owner'),('foreign_nonce','foreign_authority_owner')]:
 BY[name]['steps']=copy.deepcopy(LOADED)+[step('continue',factory_variant=variant,verdict='consistent')]

for name,variant in [('early_role_changed','role_changed'),('early_capture_changed','capture_changed'),('early_hash_changed','hash_changed')]:
 c=choose(name,expect={'files.2.open_invocations':0,'byte_totals.known_read_bytes':141})
 c['steps'][-1]['factory_variant']=variant
c=choose('canonical_path_alias',expect={'outputs.reservation.attempted':False,'byte_totals.known_read_bytes':0})
before_engine(c,[step('setup'),step('admit',spec_variant='canonical_alias')])

for name,scalar in [('early_closed_success',1),('early_closed_failure',0),('early_close_unobserved',None)]:
 c=choose(name,expect={'files.0.close_invocations':1,'byte_totals.known_read_bytes':141,'byte_totals.early_reopens_after_claim':0})
 before_engine(c,SETUP+[step('issue'),step('close',file_id=0),step('probe_claim_refused')])
 if scalar==0:bind_rule(c,'CloseHandle',0,[action('store_scalar',value=0),action('store_error',value=5,defined=True)])
 elif scalar is None:bind_rule(c,'CloseHandle',0,[action('raise_exception',exception='mem',phase='close_wrapper')],'throw_original')
 c['checks']+=vals({'files.0.close_return_observed':scalar is not None,'files.0.close_success':None if scalar is None else bool(scalar)})

c=choose('compile_original_failure',expect={'loader.attempted':['cohort_entry'],'loader.returned':[],'files.2.open_invocations':0,'byte_totals.captured_bytes':141})
before_engine(c,LOADED+[step('probe_load_refused',module='cohort_entry')]);callback(c,'compiler_entry',[dict(action='throw_original',exception='mem')])
c=choose('undeclared_source_import',expect={'loader.attempted':['cohort_entry'],'loader.returned':[],'files.2.open_invocations':0})
before_engine(c,LOADED);callback(c,'compiler_entry',[dict(action='resolve_undeclared',module='not_declared')])
c=choose('cache_return_after_early_close',expect={'loader.attempted':['cohort_entry','cohort_leaf'],'loader.returned':['cohort_leaf','cohort_entry'],'files.1.close_invocations':1,'files.2.open_invocations':0})
before_engine(c,LOADED+[step('close',file_id=1),step('probe_load_refused',module='cohort_entry')])

for name,error,phase in [('open_scalar_then_KI','ki','after_scalar_before_aux'),('open_scalar_then_SE','se','after_scalar_before_right_transfer')]:
 c=choose(name,expect={'files.0.handle_fact':dict(tag='HANDLE',value=101),'files.0.close_invocations':1,'files.0.known_read_bytes':0,'api_counters.CreateFileW.scalar_returns':1,'api_counters.CreateFileW.wrapper_returns':0})
 before_engine(c,SETUP)
 bind_rule(c,'CreateFileW',0,[action('store_scalar',value=101),action('raise_exception',exception=error,phase=phase)],'throw_original')
 c['checks'].append(ck('errors.primary',error,'original_exception_is'))
 c['checks']+=vals({'calls.0.scalar_aux_ack':False,'calls.0.right_transfer_ack':False})
for name,value,tag in [('open_scalar_unobserved','UNOBSERVED','UNOBSERVED'),('open_observed_NULL',None,'NULL'),('open_observed_INVALID',2**64-1,'HANDLE')]:
 c=choose(name,expect={'files.0.handle_fact':dict(tag=tag,value=None if tag=='UNOBSERVED' else value),'files.0.close_invocations':0,'files.0.known_read_bytes':0})
 before_engine(c,SETUP)
 acts=[] if tag=='UNOBSERVED' else [action('store_scalar',value=value)]
 if name=='open_observed_INVALID':acts.append(action('store_error',value=2,defined=True))
 bind_rule(c,'CreateFileW',0,acts)
 c['checks']+=vals({'api_counters.CreateFileW.scalar_returns':0 if tag=='UNOBSERVED' else 1,'api_counters.CreateFileW.wrapper_returns':1})

for name in ['read_count_then_deadline','read_hash_KI','read_copy_MemoryError','read_defined_zero','read_false_observed_zero','wrapper_return_then_later_stop','injected_source_error_class']:
 c=choose(name);before_engine(c,SETUP)
 c['checks']+=vals({'files.0.close_invocations':1,'files.0.read_invocations':1,'api_counters.ReadFile.invocations':1})
c=BY['read_count_then_deadline'];bind_rule(c,'ReadFile',0,[action('buffer_write',frame='cohort_leaf_read'),action('store_scalar',value=1),action('store_count',value=58),action('clock_set',value=395)])
c['checks']+=vals({'origin.now':395,'byte_totals.known_read_bytes':58,'byte_totals.hashed_bytes':0,'byte_totals.captured_bytes':0,'api_counters.ReadFile.wrapper_returns':1})
c['checks']+=vals({'calls.5.raw_count':dict(tag='COUNT32',value=58),'calls.5.wrapper_return_observed':True,'calls.5.wrapper_state':'returned'})
for name,target,error,hashed in [('read_hash_KI','hash_update','ki',0),('read_copy_MemoryError','copy_bytes','mem',58),('wrapper_return_then_later_stop','hash_update','err0',0),('injected_source_error_class','copy_bytes','source_error',58)]:
 c=BY[name];callback(c,target,[dict(action='throw_original',exception=error)])
 c['checks']+=vals({'byte_totals.known_read_bytes':58,'byte_totals.hashed_bytes':hashed,'byte_totals.captured_bytes':0,'api_counters.ReadFile.wrapper_returns':1})
 c['checks']+=vals({'calls.5.wrapper_return_observed':True,'calls.5.wrapper_state':'returned','calls.5.raw_count':dict(tag='COUNT32',value=58)})
 c['checks'].append(ck('errors.primary',error,'original_exception_is'))
 c['external_identity_checks']+=['stopped_read_buffer_same_object_generation_and_bytes_no_reuse','no_duplicate_latch_of_same_original_error']
for name,boolean,unknown in [('read_defined_zero',1,False),('read_false_observed_zero',0,True)]:
 c=BY[name];bind_rule(c,'ReadFile',0,[action('buffer_write',frame='cohort_leaf_read'),action('store_scalar',value=boolean),action('store_count',value=0)])
 c['checks']+=vals({'byte_totals.known_read_bytes':0,'byte_totals.hashed_bytes':0,'byte_totals.captured_bytes':0,'byte_totals.read_count_unknown':unknown,'api_counters.ReadFile.count_values':1})
 c['checks']+=vals({'calls.5.raw_scalar':dict(tag='BOOL32',value=boolean),'calls.5.raw_count':dict(tag='COUNT32',value=0),'calls.5.count_defined':not unknown})
 c['coverage']+=['Defined rawzero is NOT whole-file EOF/fullcapture completeness; failedBOOL/observedzero is not a defined count.']

for name,target,acts in [('reservation_foreign_ack','reserve',[dict(action='return_foreign_ack')]),('reservation_unreturned','reserve',[dict(action='throw_original',exception='err0')]),('owned_append_original_failure','append',[dict(action='throw_original',exception='err0')])]:
 c=choose(name,expect={'byte_totals.known_read_bytes':0,'outputs.publications.seal.attempted':False});before_engine(c,SETUP);callback(c,target,acts)
 if name!='owned_append_original_failure':c['checks']+=vals({'outputs.reservation.acknowledged':False,'outputs.journal_close.attempted':False})
for name,variant in [('checker_factory_unbranded','unbranded'),('checker_foreign_context','foreign_context')]:
 c=choose(name,expect={'terminal.seal_acknowledged':False})
 c['steps'][-1]['factory_variant']=variant
c=choose('checker_return_late',expect={'origin.now':395,'byte_totals.captured_bytes':209,'terminal.seal_acknowledged':False})
callback(c,'checker_archive',[dict(action='clock_set',value=395)])

c=choose('original_close_false',expect={'files.2.close_invocations':1,'files.2.close_return_observed':True,'files.2.close_success':False,'terminal.original_closures_complete':False,'outputs.publications.seal.attempted':False})
bind_rule(c,'CloseHandle',2,[action('store_scalar',value=0),action('store_error',value=5,defined=True)])
c=choose('original_close_unreturned',expect={'files.2.close_invocations':1,'files.2.close_return_observed':False,'files.2.close_success':None,'terminal.original_closures_complete':False,'outputs.publications.seal.attempted':False})
bind_rule(c,'CloseHandle',2,[action('raise_exception',exception='err0',phase='close_wrapper')],'throw_original')
c=choose('seal_ack_late',expect={'origin.now':400,'terminal.seal_acknowledged':True,'terminal.final_clock_passed':False,'terminal.pure_owner_ack':False})
callback(c,'publish_seal',[dict(action='clock_set',value=400)])
c=choose('postseal_no_new_output',expect={'terminal.seal_acknowledged':True,'terminal.pure_owner_ack':False,'journal.next_sequence':53,'terminal.final_clock_passed':False})
callback(c,'before_final_ack',[dict(action='emit_forbidden',event='stage_reserved',details=dict(stage='core'),cleanup=True)])
c['coverage']+=['In-flight illegal emit AFTER sealACK but BEFORE finalclock/ownerissue; no retroactive invalidation of an already returned result.']

c=choose('preopen_roster_bounds',expect={'outputs.reservation.attempted':False,'byte_totals.known_read_bytes':0});before_engine(c,[step('setup'),step('admit',spec_variant='N5_B3_M3_invalid')])
c['coverage']+=['Uses only duplicate/relabelled existing blob descriptors, no invented payload. Combined malformed pre-admission refusal; not isolated proof of each cap predicate.']
c=choose('forged_derived_caps',expect={'outputs.reservation.attempted':False,'byte_totals.known_read_bytes':0})
before_engine(c,[step('setup'),step('snapshot',name='before_kw'),step('probe_forbidden_claimed_keyword',keyword='claimed_C',value=1),step('snapshot',name='after_kw')])
c['checks']+=[ck('$snapshot','before_kw','unchanged_since',at='after_kw')]
c['coverage']+=['External unentered TypeError; ownerprimary/attempts/counters/clock unchanged at checkpoint. Separate incomplete finalizer is not body-entry evidence.']
c=choose('short_read_attempt_exhaustion',expect={'byte_totals.known_read_bytes':17,'byte_totals.hashed_bytes':17,'byte_totals.captured_bytes':17,'files.0.read_invocations':17,'files.1.open_invocations':0,'files.0.hash_complete':False,'files.0.capture_complete':False})
before_engine(c,SETUP)
for i in range(17):
 c['binding_overrides'].append(dict(api='ReadFile',file_id=0,occurrence=i+1,actions=[action('buffer_write',frame='leaf_byte_'+str(i)),action('store_scalar',value=1),action('store_count',value=1)],**{'return':'normal_None'}))
c['coverage']+=['17 one-byte slices of exact leaf prefix,41bytes remain; refusal BEFORE18th dispatch even aggregateR51 unused. No extra frame perread, no post-stop reuse.']
c=choose('publication_attempt_or_size_cap',normal_result=True)
c['coverage']=['STRUCTURAL/actual-future-SinkSpy observed-output bound: all produced packetbytes<=8192 and each of five kinds attempted at most once; no new publication API. Isolated rejected8193/repeatedkind injection is NOT exercised.']
c=choose('snapshot_and_exception_mutation',expect={'byte_totals.known_read_bytes':58,'byte_totals.hashed_bytes':0,'byte_totals.captured_bytes':0})
before_engine(c,SETUP);callback(c,'hash_update',[dict(action='throw_original',exception='err0')]);c['steps']+=[step('snapshot',name='issued'),step('mutate_issued'),step('snapshot',name='after_mutation')]
c['checks']+=[ck('$snapshot','issued','unchanged_since',at='after_mutation'),ck('errors.primary','err0','original_exception_is')]
c=choose('foreign_diagnostic_and_nonowning_view',expect={'byte_totals.known_read_bytes':58})
before_engine(c,SETUP);callback(c,'hash_update',[dict(action='throw_original',exception='err0')]);c['steps']+=[step('snapshot',name='issued'),step('diagnostic_foreign_control'),step('snapshot',name='after_foreign')]
c['checks']+=[ck('$snapshot','issued','unchanged_since',at='after_foreign')]
c['coverage']+=['Foreign diagnostic lookup and nonowning misuse after issuance must not mutate cached result/clock/rights; no isolated pre-final type-policy proof claimed.']

# Strict per-case static inputs; no rule is selected from a source result.
assert len(cases)==48 and len({c['group'] for c in cases})==14
frames=copy.deepcopy(INPUTS['frames_hex'])
leaf=bytes.fromhex(COHORT['blobs'][0]['utf8_hex'])
for i in range(17):frames['leaf_byte_'+str(i)]=leaf[i:i+1].hex()
events=[]
def ev(event,stage=None,kind=None,file_id=None,module=None):events.append(dict(sequence=len(events),event=event,stage=stage,kind=kind,file_id=file_id,module=module,elapsed=0))
def pair(a,b,**kwargs):ev(a,**kwargs);ev(b,**kwargs)
ev('output_reserved')
for i in (0,1):
 pair('source_open_reserved','source_open_returned',file_id=i)
 pair('source_identity_reserved','source_identity_returned',file_id=i)
 pair('source_hash_reserved','source_hash_returned',file_id=i)
ev('handoff_reserved');ev('handoff_claimed')
ev('source_compile_reserved',module='cohort_entry');ev('source_compile_reserved',module='cohort_leaf')
ev('source_compile_returned',module='cohort_leaf');ev('source_compile_returned',module='cohort_entry')
for name in ('authority_factory','checker_factory','admit_reconcile'):pair('stage_reserved','stage_returned',stage=name)
ev('stage_reserved',stage='hash_remaining')
pair('file_open_reserved','file_open_returned',file_id=2);pair('file_hash_reserved','file_hash_returned',file_id=2)
ev('stage_returned',stage='hash_remaining')
for name in ('archive','journal','resources','core','consistency'):pair('stage_reserved','stage_returned',stage=name)
ev('finalization_reserved');pair('publication_reserved','publication_returned',kind='candidate')
for i in (2,1,0):pair('original_close_reserved','original_close_returned_or_unknown',file_id=i)
pair('publication_reserved','publication_returned',kind='cleanup');ev('journal_close_reserved')
assert len(events)==53
fixture=dict(schema_version=1,status='AUTHORED_CLOSED_LITERAL_INTEGRATION_HISTORIES_BEFORE_IMPLEMENTATION',schema=pin(HERE/'SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v1.json'),public_schema=pin(HERE/'SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json'),public_schema_peer=pin(HERE/'SHARED-OWNER-PUBLIC-DATA-INDEPENDENT-PEER-v2.json'),cohort=pin(HERE/'SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json'),root_scope=pin(HERE/'SHARED-OWNER-ROOT-PREPARATION-SCOPE-v2.json'),author=pin(Path(__file__).resolve()),common=dict(clock_start=100,initial_clock=100,work_end=395,hard_end=400,output_key='synthetic-shared-owner-v1',full_file_ids=[0,1,2],early_file_ids=[0,1],load_module='cohort_entry',checker_ids=[['archive','toy_archive'],['journal','toy_journal'],['resources','toy_resources'],['core','toy_core']],expected_plan=dict(N=3,B=2,M=2,R=51,C=69,E=218),expected_normal_original_call_count=21,expected_normal_journal_row_count=53),baseline_binding_inputs=INPUTS['baseline_binding_script'],expected_baseline_serialized_rows=events,frames_hex=frames,exception_inputs=schema['exception_inputs'],cases=cases,comparison_policy=schema['expected_comparison'],qualification=PUBLIC['qualification_exact'],actual_API_calls=0,fake_binding_dispatches=0,reviewed_components_imported=False,toy_helpers_executed=False,fixture_behavior_qualified=False,source_implementation_authorized=False)
write('SHARED-OWNER-INTEGRATION-FIXTURES-v1.json',fixture)
print(json.dumps(dict(schema=pin(HERE/'SHARED-OWNER-INTEGRATION-FIXTURE-SCHEMA-v1.json'),fixture=pin(HERE/'SHARED-OWNER-INTEGRATION-FIXTURES-v1.json'),histories=48,groups=14)))
