"""Close the one finite public-DATA precision batch; not component code."""
from datetime import datetime, timezone
import copy
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def pin(path):
    b=path.read_bytes();return dict(path=str(path),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def record(**fields):return dict(exact_keys=list(fields),fields=fields)
def main():
    prior=HERE/'SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-DRAFT-v1.json';target=HERE/'SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json';assert not target.exists()
    assert pin(prior)['sha256']=='1de34a270ee1e05c268553c40977c73032be7f53fe356fea2730ad407b7526af'
    peer=HERE/'SHARED-OWNER-PUBLIC-DATA-INDEPENDENT-PRECHECK-v1.json';assert pin(peer)['sha256']=='4c9b82ed1b5ed363331b737c2cf06d16c0ea32552d45679d1c0d195a4663a784'
    d=copy.deepcopy(json.loads(prior.read_text(encoding='utf-8')));d.update(schema_version=2,status='CLOSED_PUBLIC_INTERFACE_DATA_FOR_LITERAL_PREPARATION_NO_COMPONENT_IMPLEMENTATION',recorded_at_utc=datetime.now(timezone.utc).isoformat(),preserved_v1=pin(prior),finite_precheck=pin(peer),author=pin(Path(__file__)))
    methods=d['construction_and_methods']['shared_owner_v1.py'];methods[methods.index('owner.finalize(outcome) -> frozen FinalResult [once]')]='owner.finalize(outcome="incomplete") -> frozen FinalResult [external bootstrap-failure path only, once]'
    methods.extend(['owner.emit(event, details, cleanup=False) [existing closed journal primitive]'])
    d['lifecycle']+=' External finalize accepts ONLY the literal string incomplete. The normal controller derives consistent/negative from the accepted same-owner gates/verdicts and invokes its one terminal sequence internally; public callers cannot provide a ready/consistent/negative outcome.'
    d['terminal']['exact_keys'][d['terminal']['exact_keys'].index('result_returned')]='result_issued'
    d['terminal']['fields']['result_issued']=d['terminal']['fields'].pop('result_returned')
    d['terminal']['fields']['result_issued']='strictbool: frozen final result committed/issued byowner, NOT measuredreceiptbycaller'
    d['file']['fields']['close_return_observed']='strictbool derived ONLY from nonUNOBSERVED raw signed32 CloseHandle scalar, independent of wrapperreturn. A scalar then wrapperraise keepsknown close outcome.'
    d['read_only_ref_surface']={
      'FileRecordRef':['id','spec'],'CallRef':['ordinal','api','file_ref','requested','buffer_ref','buffer_generation'],'BufferRef':['capacity'],
      'rule':'All listed properties are read-only. Actual identity is opaque and externally compared with is; no public mutable record dictionaries. FileRecordRef.spec is the canonical immutable FileSpec; CallRef.file_ref is the SAME current canonical ref; BufferRef refers to the one owner buffer, not a copy. Only the owner can modify backing state.'}
    raw=['binding_invoke','pre_dispatch','after_scalar_before_aux','after_scalar_before_right_transfer','error_copy','RawReturn_allocation','after_count_before_aux','buffer_copy','hash_update','post_call_clock','identity_query','handoff','close_wrapper','cleanup_publication']
    public=['entry','bind_ports','bind_test_hooks','bind_test_compiler','admit_plan','reserve_output','capture_early','issue_continuation','claim_continuation','load_source','continue_once','finalize','journal_append','journal_close','publish_candidate','publish_cleanup','publish_failure','publish_receipt','publish_seal','original_close','diagnostic_format','final_clock']
    d['diagnostic_phase_enum']=list(dict.fromkeys(raw+public+d['stage_names']+['copy_bytes','before_final_ack']))
    d['diagnostic']['fields']['phase']='EXACT diagnostic_phase_enum member, never a scenario/case/fault label'
    d['serialized_journal_row']=record(sequence='strictint0..E-1',event='event_names member',stage='null|stage_names member',kind='null|candidate|cleanup|failure',file_id='null|strictint0..N-1',module='null|admitted module name',elapsed='finite nonbool seconds sinceoriginalstart')
    d['journal_serialization']='Prepare immutable UTF8 JSON row bytes BEFORE append dispatch, sort_keys=True,separators=(comma,colon),ensure_ascii=True,allow_nan=False, exactlyoneLF, <=1024B. Serialized row has ONLY serialized_journal_row keys: NO own return_observed/acknowledged/state fields. journal.events are separate registry-only append observations and may later gain ack facts; their updates do not rewrite stored bytes or self-certify a durable append. No tip/ack hash cycle.'
    d['event']['fields']['state']='registry-only operation_state enum; not serialized selfACK'
    d['event']['fields']['return_observed']='strictbool Python append return observation, not serialized'
    d['event']['fields']['acknowledged']='strictbool exactsourceackidentity, not serialized; never physical I/O proof'
    d['strict_numeric_domains']={
      'integers':'Every counter/ID/ordinal/length/capacity/sequence/size/schema-version field requires exact int, NEVER bool, float or coercion. Enforce the field cap with integer comparisons before allocation/dispatch; malformed/oversized values do not overflow via float conversion.',
      'bounds':'file IDs0..N-1; call ordinals0..C-1; eventsequence0..E-1; nextsequence0..E; filecounts nonnegative<=fieldplannedbound; bytes nonnegative<=their declared pool. Aggregate reserved capacities C/E are not actualcounts. Per-API invocation/scalar/wrapper/count axes never exceed created applicable records.',
      'times':'Time fields require exact int or finite float, NEVER bool/NaN/infinity; compare without unnecessary integer-to-float coercion. Original now is monotonic. Endpoints are originalstart+295/+300. Reporting snapshots do not sample clocks; invalidclock retains lastknownsample and cannot yield completion.',
      'other':'Flags require exactbool. Atoms enforce uint64 HANDLE/uint32 DWORD+COUNT/signed32 BOOL with rawvalues retained; no truthiness coercion. Strings/hex/digests retain their explicit bounded domains.'}
    d['callback_relations']={
      'unprepared':'Notprepared/notdispatched: attemptedFalse, return_observedFalse, acknowledgedFalse, prepared_bytes0, prepared_sha256null.',
      'prepared_undispatched':'A record may retain exact immutable prepared payload length/hash while attemptedFalse if a later predispatchclock/cap prevents invocation. Both returnflags false; prepared bytes remain debited, not retried. A prepared empty payload would use0 andSHA256(empty), distinct from unprepared0/null; generated journal/publish packets are nonempty.',
      'attempted':'Before callback dispatch set attemptedTrue once. A thrown/unreturned callback leaves return_observedFalse/ackFalse; an observed foreign/false reply has return_observedTrue/ackFalse. acknowledgedTrue implies bothpriorflagsTrue and exactcurrentackidentity. Retain return/ack before clockchecks.',
      'payload':'For append/publish, prepared_bytes/hash MUST match the actual captured callback payload bytes. Publish<=8192; append<=1024inclLF. Reserve/close_journal have no byte payload and keep0/null. Callback ack is not physical bytes/flush/close evidence.'}
    d['journal']['fields']['closed']='strictbool: one close RESERVATION consumed, append/reopen forbidden; doesNOTmeancloseACK'
    d['journal']['fields']['close_return_observed']='strictbool ofPython close_journal callbackreturn'
    d['journal']['fields']['close_acknowledged']='strictbool exactcallbackack, independentfromclosed consumedstate'
    d['journal']['fields']['tip']='null unlessallrowsacknowledged ANDcloseACK; otherwise exact{bytes,sha256} ofownerretained acknowledged serializedrowbytes; notphysicaldurability'
    d['terminal']['fields']['journal_closed']='strictbool means known close_journal callbackACK, not merely consumedclose reservation'
    d['journal_close_rule']='Set journal.closed=True when its one-shot close reservation is consumed BEFORE dispatch; fromthenon append/reopen/retry forbidden even ifcallbackunreturned ordispatchblocked. outputs.journal_close.attempted separately records actualcallbackdispatch; unknown/false close keepsACKFalse and tipnull. No reopen to improve evidence.'
    d['finalize_and_emit_rules']={
      'bootstrap':'External owner.finalize accepts ONLY outcome="incomplete". Wrongoutcome/type refuses; no caller-supplied consistency/negative/ready gate. Once finalized/issued, allfurtherfinalize/work/close/foreignclaim attempts refuse WITHOUT clock/error/counter/I/O mutation.',
      'controller':'continue_once on a valid alreadyclaimed Continuation entersonce and owns its terminal finally. Internal normal outcome derives from actual accepted ownergates/verdicts, never public finalizeinput. It returns the cached immutable FinalResult.',
      'emit':'owner.emit(event,details,cleanup=False) is public as alreadyproposed. event is event_names; details has ONLY optionalstage/kind/file_id/module fields with valid matching types, omittedvalues normalize tonull. No caller sequence/elapsed/ACK fields. Own clock/eventsequence is used. No emit after consumed journalclose or seal; inflight illegalemit latchesveto, postfinalized misuse doesnotmutateissuedresult.',
      'coverage':'No new ownerpublication API exists for isolated8193/repeatedkind injections. Sourceproducer guard plus actualSinkSpy checks ALLproduced payload bytes<=8192 and eachkind attemptedonce. This is structural/observed-output coverage, NOT an isolated cap-refusal probe.'}
    d['compact_publication_packet']=record(schema_version='exactint1',kind='oneofcandidate/cleanup/failure/receipt/seal',scope='constant pure_shared_owner_seam',status='currentstatus enum, never selfcertifiedcompletion',elapsed='finite0..300 atpreparation underoriginalclock',totals='compact totals record',gates='currentorderedacceptedgateprefix; no selfACKgate',original_closures='<=N {file_id,invoked,return_observed,success}; no paths',file_digests='<=N hashcomplete {file_id,size,sha256}; no paths',links='exact{candidate,cleanup,journal,receipt}: null|{bytes,sha256}',qualification='qualification_exact')
    assert len(d['compact_publication_packet']['exact_keys'])==11
    d['packet_totals']=record(N='strictint0..4',B='strictint0..2',M='strictint0..2',raw_calls='actualrecords<=C',journal_events='actualrows<=E',known_read_bytes='definedtotal',hashed_bytes='committedtotal',captured_bytes='committedtotal')
    d['packet_rules']='Encode only the closed ELEVEN-key compact packet as UTF8 JSON(sortkeys,compactseparators,ensure_ascii,allow_nanFalse)+oneLF. Enforce<=8192 BEFORE callback. Never serialize the full21call ledger, original path strings, diagnostics or live objects. Links may reference only earlier known acknowledged artifacts/tip; never currentpayload/selfhash. Candidate has no selfcandidate link; cleanup has no selfcleanup link; seal includes priorreceipt but no selfseal link. Receipt/seal observations are registry-only afterjournalclose. Harness independently checks actualpayloadlen/hash against callbackmetadata and compactshapes/IDs/links; no exactliteralpacket hash or realpacket-format qualification is inferred.'
    d['delta_scope']='One combined precision batch: resultissued naming; rawclose vswrapper; immutable journalrow vsregistryACK; finite diagnosticphases; exactreadonlyrefs; strictnumericdomains; callbackdefaults/closeconsumption; existing finalize/emit callability andcompact11field producer. No newhistory/group/realAPI/publicpublication entry or qualification policy.'
    with target.open('x',encoding='utf-8') as out:json.dump(d,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(pin(target)))
if __name__=='__main__':main()
