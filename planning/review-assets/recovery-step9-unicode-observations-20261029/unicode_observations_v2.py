"""Pure captured Unicode-control observations; no filesystem/native authority.

Fixed accepted dependencies are supplied by a separately bound source loader.
Only ordinary API typing/immutability is claimed, not hostile Python isolation.
"""
from dataclasses import dataclass
import hashlib
import json
from types import MappingProxyType
import unicode_pack_codec_v2 as _codec
import unicode_piece_analyzer_v1 as _analyzer
import recognition_module_policy_v1 as _modules
from unicode_observation_tables_v1 import TABLES as _T, SOURCE_PINS as TABLE_SOURCE_PINS

WIRE_SHA256="75605c03fb5b9bac659538035d8205b34df2ae1781b997a3181a1564676aa6c4"
CALL_SHA256="30d82a42c5338789644fea00f666e264fb3e4114637c2c37330386a177f17861"
MODULE_ID="trusted-System32-recognition-v1"
MODULE_SHA256="4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713"
PROFILE_ID="actual-v3-fullresponse-unicode-controls-v1"
BLOCK=65536
_ISSUED=object()
_NAMES=tuple(_T["API_accounting"]["names"])
_ROOT=frozenset(("schema_version","row_sequence","event","elapsed_ms","wire_semantics_sha256",
    "native_call_contract_sha256","native_call_counters","native_call_scope","unrecorded_killed_tail","native_state","body"))
_OBS=frozenset(_T["closure"]["observation"]["exact_keys"])
_REF=frozenset(("case_ordinal","case_id","stage_instance_id","grammar_sha256","raw_sha256","raw_bytes"))
_HEX=frozenset("0123456789abcdef")


def _freeze(value):
    if type(value) is dict: return MappingProxyType({key:_freeze(item) for key,item in value.items()})
    if type(value) in (tuple,list): return tuple(_freeze(item) for item in value)
    return value


def _thaw(value):
    if type(value) is MappingProxyType: return {key:_thaw(item) for key,item in value.items()}
    if type(value) is tuple: return [_thaw(item) for item in value]
    return value


def _same(a,b):
    if type(b) is MappingProxyType:
        return type(a) is dict and set(a)==set(b) and all(_same(a[k],b[k]) for k in b)
    if type(b) in (list,tuple):
        return type(a) is list and len(a)==len(b) and all(_same(x,y) for x,y in zip(a,b))
    if type(b) is dict:
        return type(a) is dict and set(a)==set(b) and all(_same(a[k],b[k]) for k in b)
    return type(a) is type(b) and a==b


def _uint(value,maximum=(1<<64)-1): return type(value) is int and 0<=value<=maximum
def _digest(value): return type(value) is str and len(value)==64 and all(c in _HEX for c in value)
def _canonical(value): return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode("utf-8")
def _ternary(value): return None if value==2 else bool(value)


@dataclass(frozen=True,slots=True)
class ShardDescriptor:
    path: str
    bytes: int
    sha256: str


@dataclass(frozen=True,slots=True)
class ObservationBindings:
    """Externally declared lexical context; no original/file/process authority."""
    expected_child_pid: int
    expected_self: str
    expected_runtime: str
    ordered_shard_descriptors: tuple
    expected_newpack_sha256: str


@dataclass(frozen=True,slots=True,init=False)
class Observation:
    _data: object
    _issued: object

    def to_dict(self): return _thaw(self._data)


class ObservationError(ValueError):
    def __init__(self,reason,*,row=None,byte_offset=None,validated_prefix=None):
        self.reason=reason
        self.row=row
        self.byte_offset=byte_offset
        self.validated_prefix=_freeze(validated_prefix or {})
        super().__init__(reason)

    def to_dict(self):
        return dict(reason=self.reason,row=self.row,byte_offset=self.byte_offset,validated_prefix=_thaw(self.validated_prefix))


def _issue(data):
    result=object.__new__(Observation)
    object.__setattr__(result,"_data",_freeze(data)); object.__setattr__(result,"_issued",_ISSUED)
    return result


class _Reader:
    def __init__(self,profile,bindings,check):
        self.profile,self.bindings,self.check=profile,bindings,check
        self.row_index=0; self.offset=0; self.validated_rows=0; self.cases=[]; self.ledgers=[None]*84
        self.strata=[0]*6; self.native_geometry=0; self.known_membership=0; self.harness=0
        self.nv=None; self.eogs=None; self.analysis=None; self.summary=None
        self.selection=False; self.prefixes=[]; self.cleanup=False; self.batch=False; self.normal=False
        self.failure=None; self.failure_line=None; self.marker_seen=False; self.marker=None
        self.previous=None; self.previous_time=0; self.reported_budget_violations=[]; self.opaque_diagnostic=False
        self.raw_digest=None; self.raw_size=None; self.tail=None; self.capture_present=False
        self.buckets=dict(setup=0,before=0,case=0,selected=0,footer=0)

    def snapshot(self):
        return dict(validated_rows=self.validated_rows,validated_case_rows=len(self.cases),
            validated_native_geometry_rows=self.native_geometry,known_membership_outcomes=self.known_membership,
            validated_harness_rows=self.harness,stratum_validated_counts=list(self.strata),
            unique_selected_prefix_results=len(self.prefixes),case_collection_complete=len(self.cases)==84,
            normal_schedule_complete=self.normal,terminal_negative_seen=self.failure is not None or self.marker_seen,
            source_cleanup_consistent=self.clean(self.previous) if self.previous is not None else False,
            reported_budget_violations=list(self.reported_budget_violations))

    def need(self,condition,reason):
        if not condition:
            raise ObservationError(reason,row=self.row_index,byte_offset=self.offset,validated_prefix=self.snapshot())

    def callback(self): self.check()

    def hash(self,raw):
        self.callback(); state=hashlib.sha256()
        view=memoryview(raw)
        for start in range(0,len(raw),BLOCK):
            self.callback(); state.update(view[start:start+BLOCK]); self.callback()
        result=state.hexdigest(); self.callback(); return result

    def keys(self,value,keys,reason):
        self.need(type(value) is dict and all(type(k) is str for k in value) and set(value)==set(keys),reason)

    def scalar_tree(self,value,depth=0):
        self.need(depth<=32,"JSON_nesting_cap")
        if type(value) is str:
            self.need(all(not 0xd800<=ord(c)<=0xdfff for c in value),"JSON_unpaired_surrogate")
        elif type(value) is dict:
            for key,item in value.items(): self.scalar_tree(key,depth+1); self.scalar_tree(item,depth+1)
        elif type(value) is list:
            for item in value: self.scalar_tree(item,depth+1)
        else: self.need(value is None or type(value) in (bool,int),"JSON_scalar_type")

    def parse(self,raw):
        # No callback/take/hash dispatch occurs within these data-only catches.
        self.callback()
        self.need(not raw.startswith(b"\xef\xbb\xbf") and b"\r" not in raw and raw!=b"","JSON_row_encoding")
        quoted=False; escaped=False; depth=0
        for byte in raw:
            if quoted:
                if escaped: escaped=False
                elif byte==92: escaped=True
                elif byte==34: quoted=False
            elif byte==34: quoted=True
            else:
                self.need(byte not in (9,10,13,32),"JSON_not_compact")
                if byte in (91,123): depth+=1; self.need(depth<=32,"JSON_nesting_cap")
                elif byte in (93,125): depth-=1
        def pairs(items):
            out={}
            for key,value in items:
                self.need(key not in out,"JSON_duplicate_key"); out[key]=value
            return out
        def nonfinite(_): self.need(False,"JSON_nonfinite")
        try:
            text=raw.decode("utf-8","strict")
            result=json.loads(text,object_pairs_hook=pairs,parse_constant=nonfinite)
        except ObservationError:
            raise
        except (UnicodeError,ValueError,RecursionError) as error:
            raise ObservationError("JSON_data",row=self.row_index,byte_offset=self.offset,validated_prefix=self.snapshot()) from error
        self.callback(); self.scalar_tree(result); self.need(type(result) is dict,"JSON_object"); self.callback()
        return result

    def validate_bindings(self):
        b=self.bindings
        self.need(type(b) is ObservationBindings,"bindings_type")
        self.need(type(b.expected_child_pid) is int and 1<=b.expected_child_pid<=0xffffffff,"declared_PID")
        self.need(type(b.ordered_shard_descriptors) is tuple and len(b.ordered_shard_descriptors)==3,"declared_shards")
        self.need(_digest(b.expected_newpack_sha256),"declared_pack_digest")
        paths=[]
        self.callback()
        try:
            _modules.canonical_path(b.expected_self); _modules.canonical_path(b.expected_runtime)
            for shard in b.ordered_shard_descriptors:
                self.need(type(shard) is ShardDescriptor,"declared_shard_type")
                paths.append(_modules.canonical_path(shard.path))
                self.need(_uint(shard.bytes) and shard.bytes>0 and _digest(shard.sha256),"declared_shard_pin")
        except _modules.ModulePolicyError as error:
            raise ObservationError("declared_lexical_context",validated_prefix=self.snapshot()) from error
        self.callback(); self.need(len(set(paths))==3,"declared_shard_duplicate")

    def common(self,row,*,marker=False):
        if not marker: self.keys(row,_ROOT,"root_fields")
        self.need(type(row["schema_version"]) is int and row["schema_version"]==1,"schema_version")
        self.need(_uint(row["elapsed_ms"]),"elapsed_type")
        self.need(row["elapsed_ms"]>=self.previous_time,"elapsed_order")
        self.need(row["wire_semantics_sha256"]==WIRE_SHA256 and type(row["wire_semantics_sha256"]) is str,"wire_fingerprint")
        self.need(row["native_call_contract_sha256"]==CALL_SHA256 and type(row["native_call_contract_sha256"]) is str,"call_fingerprint")
        self.need(row["native_call_scope"]=="explicit_bridge_export_calls_only","call_scope")
        self.need(row["unrecorded_killed_tail"]=="unknown_since_last_acknowledged_snapshot","tail_scope")
        counters=row["native_call_counters"]; self.keys(counters,_NAMES,"counter_names")
        attempts=returns=0
        for name in _NAMES:
            c=counters[name]; self.keys(c,("attempted","returned"),"counter_fields")
            self.need(_uint(c["attempted"],_T["API_accounting"]["hard_caps"][name]) and _uint(c["returned"],c["attempted"]),"counter_type_or_cap")
            if self.previous is not None:
                self.need(all(c[k]>=self.previous["native_call_counters"][name][k] for k in ("attempted","returned")),"counter_decreased")
            attempts+=c["attempted"]; returns+=c["returned"]
        self.need(attempts<=4276181,"aggregate_call_cap")
        s=row["native_state"]; self.keys(s,_T["framing"]["native_state_fields"],"native_state_fields")
        for name,rule in _T["framing"]["native_state_fields"].items():
            value=s[name]
            if rule=="strict bool": self.need(type(value) is bool,"state_bool_"+name)
            elif type(rule) is MappingProxyType:
                lo,hi=rule["strict_int_range"]; self.need(type(value) is int and lo<=value<=hi,"state_int_"+name)
            elif type(rule) is tuple:
                self.need(any(type(value) is type(option) and value==option for option in rule),"state_enum_"+name)
            else: self.need(type(value) is list and len(value)==6 and all(_uint(n,84) for n in value),"state_strata")
        self.need((s["total_attempted"],s["total_returned"])==(attempts,returns),"state_counter_totals")
        self.need(sum(s["stratum_computed"])==s["cases_computed"] and sum(s["stratum_results_written"])==s["case_results_written"],"state_stratum_totals")
        self.need(s["case_results_written"]<=s["cases_computed"] and s["selected_prefix_results_written"]<=s["selected_prefixes_computed"],"state_written_order")
        self.need(all(a<=b for a,b in zip(s["stratum_results_written"],s["stratum_computed"])),"state_stratum_written")
        for prefix,api in (("model","llama_model_free"),("backend","llama_backend_free")):
            c=counters[api]
            self.need(s[prefix+"_free_attempted"] is (c["attempted"]>0) and s[prefix+"_free_return_observed"] is (c["returned"]>0),"free_return_state")
            self.need(s[prefix+"_release_unknown"] is (c["attempted"]>c["returned"]),"free_unknown_state")
            self.need(not s[prefix+"_free_attempted"] or not s[prefix+"_owned"],"owned_after_free_reservation")
        self.need(s["model_load_return_observed"] is (counters["llama_model_load_from_splits"]["returned"]>0) and
            s["backend_init_return_observed"] is (counters["llama_backend_init"]["returned"]>0) and
            s["cpu_load_return_observed"] is (counters["ggml_backend_load"]["returned"]>0),"initialization_return_state")
        self.need(s["model_owned"] is (s["model_return_nonnull"] and not s["model_free_attempted"]) and
            s["backend_owned"] is (s["backend_init_return_observed"] and not s["backend_free_attempted"]),"session_ownership_state")
        if self.previous is not None:
            old=self.previous["native_state"]
            for name in ("EOG_ids_examined","cases_computed","case_results_written","selected_prefixes_computed",
                    "selected_prefix_results_written","token_work_reserved","sampler_nonnull_returns","sampler_free_returned_nonnull","exceptions"):
                self.need(s[name]>=old[name],"state_decreased_"+name)
            for name in ("cpu_load_return_observed","cpu_registry_nonnull","backend_init_return_observed","backend_free_attempted",
                    "backend_free_return_observed","model_load_return_observed","model_return_nonnull","model_free_attempted","model_free_return_observed"):
                self.need(not old[name] or s[name],"state_flag_decreased_"+name)
        self.need(s["sampler_nonnull_returns"]<=counters["llama_sampler_init_grammar"]["returned"] and s["sampler_free_returned_nonnull"]<=counters["llama_sampler_free"]["returned"],"sampler_return_state")
        self.need(s["samplers_owned"]+s["sampler_release_unknown"]==s["sampler_nonnull_returns"]-s["sampler_free_returned_nonnull"],"sampler_ownership_balance")
        self.need(s["sampler_release_unknown"]<=counters["llama_sampler_free"]["attempted"]-counters["llama_sampler_free"]["returned"],"sampler_unknown_balance")
        pending_init=counters["llama_sampler_init_grammar"]["attempted"]>counters["llama_sampler_init_grammar"]["returned"]
        pending_model=counters["llama_model_load_from_splits"]["attempted"]>counters["llama_model_load_from_splits"]["returned"]
        self.need(not (pending_init or s["samplers_owned"] or s["sampler_release_unknown"]) or not s["model_free_attempted"],"unsafe_model_teardown")
        self.need(not (pending_init or pending_model or s["samplers_owned"] or s["sampler_release_unknown"] or s["model_release_unknown"]) or not s["backend_free_attempted"],"unsafe_backend_teardown")
        self.need((s["last_attempt"] is None)==(attempts==0) and (s["last_return"] is None)==(returns==0),"last_call_nullness")
        self.need(s["last_return_kind"]==0 if returns==0 else 1<=s["last_return_kind"]<=4,"last_return_kind")
        if s["last_attempt"] is not None: self.need(counters[s["last_attempt"]]["attempted"]>0,"last_attempt_unobserved")
        if s["last_return"] is not None: self.need(counters[s["last_return"]]["returned"]>0,"last_return_unobserved")
        self.callback()

    def delta(self,row,expected,token_work=0):
        previous=self.previous["native_call_counters"] if self.previous is not None else {n:dict(attempted=0,returned=0) for n in _NAMES}
        for name in _NAMES:
            for outcome in ("attempted","returned"):
                self.need(row["native_call_counters"][name][outcome]-previous[name][outcome]==expected.get(name,0),"phase_call_delta_"+name)
        if token_work is not None:
            prior=self.previous["native_state"]["token_work_reserved"] if self.previous is not None else 0
            self.need(row["native_state"]["token_work_reserved"]-prior==token_work,"token_work_delta")

    def clean(self,row):
        if row is None: return False
        s=row["native_state"]; c=row["native_call_counters"]
        return (all(v["attempted"]==v["returned"] for v in c.values()) and
            c["llama_model_free"]["returned"]==1 and c["llama_backend_free"]["returned"]==1 and
            s["model_free_return_observed"] and s["backend_free_return_observed"] and
            not any(s[k] for k in ("model_owned","backend_owned","model_release_unknown","backend_release_unknown","samplers_owned","sampler_release_unknown","cleanup_failed","exceptions")))

    def progress(self,row,*,case=False,prefix=False,failure=False):
        s=row["native_state"]; n=len(self.cases); p=len(self.prefixes)
        if failure:
            self.need(s["cases_computed"]>=n and s["case_results_written"]<=s["cases_computed"],"failure_progress")
            self.need(s["cases_computed"]<=min(84,n+1) and s["case_results_written"]<=n,"failure_unobserved_case_count")
            self.need(s["selected_prefixes_computed"]>=p and s["selected_prefixes_computed"]<=min(4,p+1) and s["selected_prefix_results_written"]<=p,"failure_prefix_progress")
            return
        counts=list(self.strata)
        if case: counts[self.profile.cases[n].stratum_index]+=1
        self.need(s["cases_computed"]==n+int(case) and s["case_results_written"]==n,"case_publication_lag")
        self.need(_same(s["stratum_computed"],counts) and _same(s["stratum_results_written"],self.strata),"stratum_publication_lag")
        self.need(s["selected_prefixes_computed"]==p+int(prefix) and s["selected_prefix_results_written"]==p,"prefix_publication_lag")
        event=row["event"]
        current=n if event=="unicode_before_case" or case else min(n-1,83)
        self.need(s["current_case_index"]==current,"current_case_index")
        self.need(s["current_selected_prefix_index"]==(p if prefix else p-1),"current_prefix_index")
        expected="not_computed" if self.summary is None and event!="unicode_coverage_summary" else None
        if self.summary is not None:
            expected="unknown" if not self.summary["coverage_complete"] else "complete_available" if self.summary["required_available"] else "complete_unavailable"
        if expected is not None: self.need(s["coverage_state"]==expected,"coverage_state_before_summary")

    def module_report(self,body,phase):
        self.need(type(body.get("module_policy_id")) is str and body["module_policy_id"]==MODULE_ID and
            type(body.get("module_policy_sha256")) is str and body["module_policy_sha256"]==MODULE_SHA256 and
            type(body.get("module_policy_phase")) is str and body["module_policy_phase"]==phase,"module_policy_binding")
        self.need(_modules.POLICY_ID==MODULE_ID and _modules.POLICY_SHA256==MODULE_SHA256,"matcher_semantics")
        self.callback()
        try:
            report=_modules.match_modules(body["modules"],expected_self=self.bindings.expected_self,
                expected_runtime=self.bindings.expected_runtime,phase=phase)
        except _modules.ModulePolicyError as error:
            raise ObservationError("module_report_"+error.reason,row=self.row_index,byte_offset=self.offset,validated_prefix=self.snapshot()) from error
        self.callback(); return report

    def setup(self,row):
        index=self.validated_rows; definition=_T["event_order"]["setup_events"][index]
        self.need(row["event"]==definition["event"],"setup_order")
        body=row["body"]; schema=_T["event_order"]["setup_body_schemas"][row["event"]]
        self.keys(body,schema["exact_body_keys"],"setup_body_fields")
        for name,rule in schema["fields"].items():
            if type(rule) is MappingProxyType:
                self.need(_same(body[name],rule.get("const",rule.get("exact_typed_value"))),"setup_field_"+name)
        changes={}
        if index in (1,11,12,14):
            changes["module_report"]=self.module_report(body,"pre_cpu" if index==1 else "post_cpu")
        if index==3:
            self.need(body["pack_sha256"]==self.pack_digest and body["wire_semantics_sha256"]==WIRE_SHA256,"pack_report_binding")
        if 4<=index<=9:
            shard_index=(index-4)//2; descriptor=self.bindings.ordered_shard_descriptors[shard_index]
            self.need(type(body["index"]) is int and body["index"]==shard_index,"shard_order")
            if index%2==0:
                self.need(type(body["path"]) is str and body["path"]==descriptor.path and _uint(body["expected_bytes"]) and body["expected_bytes"]==descriptor.bytes,"shard_declaration")
            else:
                self.need(_uint(body["bytes"]) and body["bytes"]==descriptor.bytes and _digest(body["sha256"]) and body["sha256"]==descriptor.sha256,"shard_return")
        nv=self.nv
        if index==14:
            nv=body["vocabulary_count"]; eogs=body["EOG_ids"]
            self.need(type(nv) is int and 1<=nv<=262144,"vocabulary_count")
            self.need(type(eogs) is list and 1<=len(eogs)<=64 and all(type(n) is int and 0<=n<nv for n in eogs),"EOG_ids")
            self.need(eogs==sorted(set(eogs)),"EOG_order")
            self.need(_digest(body["EOG_JSON_sha256"]) and body["EOG_JSON_sha256"]==self.hash(_canonical(eogs)),"EOG_digest")
            changes["vocabulary"]=(nv,tuple(eogs))
        expected={name:(nv if type(n) is str else n) for name,n in definition["cumulative_attempted_equals_returned"].items()}
        for name,value in expected.items():
            self.need(_same(row["native_call_counters"][name],dict(attempted=value,returned=value)),"setup_counter_vector")
        self.progress(row)
        s=row["native_state"]; c=row["native_call_counters"]
        self.need(s["token_work_reserved"]==0 and s["sampler_nonnull_returns"]==0 and s["sampler_free_returned_nonnull"]==0,"setup_no_document_work")
        self.need(s["cpu_load_return_observed"] is (index>=11) and s["cpu_registry_nonnull"] is (index>=11),"setup_CPU_state")
        self.need(s["backend_init_return_observed"] is (index>=12) and s["backend_owned"] is (index>=12),"setup_backend_state")
        self.need(s["model_load_return_observed"] is (index>=14) and s["model_return_nonnull"] is (index>=14) and s["model_owned"] is (index>=14),"setup_model_state")
        self.need(s["EOG_ids_examined"]==(nv if index==14 else 0) and s["last_EOG_id"]==(nv-1 if index==14 else -1),"setup_EOG_scan_state")
        self.need(s["last_EOG_returned"] is (index==14),"setup_EOG_return_state")
        if index==14: self.need(s["last_EOG_value"] is ((nv-1) in changes["vocabulary"][1]),"setup_final_EOG_value")
        self.need(s["exceptions"]==0 and not s["cleanup_failed"],"setup_exception")
        return changes

    def reference(self,body,index,before=False):
        c=self.profile.cases[index]; stage=self.profile.stages[c.stage_index]
        expected=dict(case_ordinal=index,case_id=c.id,stage_instance_id=stage.id,
            grammar_sha256=self.profile.grammars[stage.grammar_index].sha256,raw_sha256=c.sha256,raw_bytes=len(c.raw))
        self.need(all(_same(body.get(key),value) for key,value in expected.items()),"source_case_reference")
        if before: self.need(body["declared_native_byte_eligible"] is c.native_byte_eligible,"source_case_eligibility")
        return c

    def analyzer_case(self,c,ordinal=None):
        return dict(id=c.id,ordinal=c.ordinal if ordinal is None else ordinal,raw_bytes=c.raw,native_byte_eligible=c.native_byte_eligible,
            generation_member=c.authored_dimensions[3]==1,semantic_eligible=c.authored_dimensions[2]==1)

    def analyze(self,cases,ledgers):
        self.callback()
        try: result=_analyzer.analyze(cases,ledgers,self.nv,self.eogs).to_dict()
        except ValueError as error:
            raise ObservationError("analyzer_data",row=self.row_index,byte_offset=self.offset,validated_prefix=self.snapshot()) from error
        self.callback(); return result

    def ledger(self,value,c):
        self.keys(value,("token_ids","piece_byte_lengths","piece_hex"),"ledger_fields")
        self.need(all(type(value[k]) is list for k in value),"ledger_arrays")
        ids,lengths,spelling=(value[k] for k in ("token_ids","piece_byte_lengths","piece_hex"))
        n=len(ids); self.need(1<=n<=c.token_cap and len(lengths)==len(spelling)==n,"ledger_count")
        self.need(all(type(t) is int and 0<=t<self.nv and t not in self.eogs for t in ids),"ordinary_token_id")
        self.need(all(_uint(n,len(c.raw)) for n in lengths),"piece_length")
        self.need(sum(lengths)==len(c.raw),"piece_roundtrip_size")
        pieces=[]
        for n,text in zip(lengths,spelling):
            self.need(type(text) is str and len(text)==2*n and all(char in _HEX for char in text),"piece_hex")
            pieces.append(bytes.fromhex(text))
        self.need(b"".join(pieces)==c.raw,"piece_roundtrip_bytes")
        result={key:tuple(items) for key,items in value.items()}
        analyzed=self.analyze((self.analyzer_case(c,0),),(result,))["cases"][0]
        self.need(analyzed["qc_status"]=="ok","ledger_analyzer_QC")
        return result,analyzed

    def membership(self,value,lengths):
        self.keys(value,_OBS,"observation_fields")
        status=value["status"]; rejection=("first_rejected_token_index","first_rejected_byte_start","first_rejected_byte_end")
        self.need(type(status) is str and status in _T["closure"]["observation"]["ordinary_membership_union"],"observation_union")
        n=len(lengths); rejected=None
        if status=="native_token_rejection":
            r=value["first_rejected_token_index"]
            self.need(type(r) is int and 0<=r<n,"rejected_token_index")
            start=sum(lengths[:r]); end=start+lengths[r]
            self.need(type(value[rejection[1]]) is int and type(value[rejection[2]]) is int and
                (value[rejection[1]],value[rejection[2]])==(start,end),"rejected_piece_span")
            self.need(value["all_input_tokens_admitted"] is False and value["native_member"] is False and value["completion_EOG"] is None,"token_rejection_union")
            rejected=r
        else:
            self.need(all(value[k] is None for k in rejection) and value["all_input_tokens_admitted"] is True,"completed_token_union")
            eog=value["completion_EOG"]
            self.need(type(eog) is list and len(eog)==len(self.eogs),"completion_EOG_count")
            flags=[]
            for row,token in zip(eog,self.eogs):
                self.keys(row,("id","admitted"),"completion_EOG_fields")
                self.need(type(row["id"]) is int and row["id"]==token and type(row["admitted"]) is bool,"completion_EOG_order_or_type")
                flags.append(row["admitted"])
            member=True if all(flags) else False if not any(flags) else None
            expected="native_member" if member is True else "native_eog_rejection" if member is False else "native_EOG_disagreement"
            self.need(status==expected and value["native_member"] is member,"completion_EOG_union")
        return value["native_member"],rejected

    def document(self,row):
        index=len(self.cases); body=row["body"]
        self.keys(body,_REF|{"authored_expected","QC","observation","ledger","compact_analysis","matches_authored_native_expectation"},"case_body_fields")
        c=self.reference(body,index)
        expected=dict(native_member=_ternary(c.authored_dimensions[4]),generation_member=_ternary(c.authored_dimensions[3]),
            semantic_eligible=_ternary(c.authored_dimensions[2]),coverage_population=c.native_byte_eligible and c.authored_dimensions[3]==1 and c.authored_dimensions[2]==1)
        self.need(_same(body["authored_expected"],expected),"authored_expectations")
        qc=body["QC"]; self.keys(qc,("status","reason"),"QC_fields")
        self.keys(body["compact_analysis"],("counts","matrix","zero_piece_count"),"compact_fields")
        self.keys(body["observation"],_OBS,"observation_fields")
        result=dict(case_ordinal=index,case_id=c.id,QC=qc,observation=body["observation"],ledger=body["ledger"],
            compact_analysis=body["compact_analysis"],matches_authored_native_expectation=body["matches_authored_native_expectation"])
        ledger=geometry=None; delta={}; token_work=0
        if not c.native_byte_eligible:
            status="harness_raw_nul_rejection" if c.harness_kind==2 else "harness_utf8_rejection"
            self.need(_same(qc,dict(status="harness_ineligible",reason=status)),"harness_QC")
            self.need(body["observation"]["status"]==status and all(v is None for k,v in body["observation"].items() if k!="status"),"harness_observation")
            self.need(body["ledger"] is None and body["matches_authored_native_expectation"] is None and all(v is None for v in body["compact_analysis"].values()),"harness_nulls")
        elif qc["status"]=="unknown":
            self.need(type(qc["reason"]) is str and qc["reason"] in _T["closure"]["QC"]["unknown_reason_enum"],"QC_unknown_reason")
            self.need(body["observation"]["status"]=="not_attempted_QC_unknown" and all(v is None for k,v in body["observation"].items() if k!="status"),"QC_unknown_observation")
            self.need(body["ledger"] is None and body["matches_authored_native_expectation"] is None and all(v is None for v in body["compact_analysis"].values()),"QC_unknown_nulls")
            for name,counter in row["native_call_counters"].items():
                prior=self.previous["native_call_counters"][name]
                if name not in ("llama_tokenize","llama_token_to_piece"):
                    self.need(_same(counter,prior),"QC_unknown_non_geometry_call")
                else:
                    cap=2 if name=="llama_tokenize" else 2*c.token_cap
                    self.need(all(0<=counter[k]-prior[k]<=cap for k in ("attempted","returned")),"QC_unknown_geometry_cap")
            prior_work=self.previous["native_state"]["token_work_reserved"]
            self.need(0<=row["native_state"]["token_work_reserved"]-prior_work<=c.token_cap,"QC_unknown_token_reservation")
            token_work=None
        else:
            self.need(_same(qc,dict(status="ok",reason=None)),"QC_ok")
            ledger,geometry=self.ledger(body["ledger"],c)
            compact={key:geometry[key] for key in ("counts","matrix","zero_piece_count")}
            self.need(_same(body["compact_analysis"],compact),"compact_analysis_disagreement")
            member,rejected=self.membership(body["observation"],ledger["piece_byte_lengths"])
            match=None if member is None else member is expected["native_member"]
            self.need(body["matches_authored_native_expectation"] is match,"membership_match_claim")
            n=len(ledger["token_ids"]); token_work=n
            delta=dict(llama_tokenize=1 if n==1 else 2,llama_token_to_piece=n+sum(length>1 for length in ledger["piece_byte_lengths"]),
                llama_sampler_init_grammar=1,llama_sampler_free=1,llama_sampler_apply=rejected+1 if rejected is not None else n+len(self.eogs),
                llama_sampler_accept=rejected if rejected is not None else n)
        if qc["status"]!="unknown": self.delta(row,delta,token_work)
        expected_samplers=self.native_geometry+len(self.prefixes)+int(geometry is not None)
        self.need(row["native_state"]["sampler_nonnull_returns"]==expected_samplers and
            row["native_state"]["sampler_free_returned_nonnull"]==expected_samplers and
            row["native_state"]["samplers_owned"]==0 and row["native_state"]["sampler_release_unknown"]==0,"case_sampler_ownership")
        self.progress(row,case=True)
        return dict(case=(result,ledger,geometry))

    def whole_analysis(self):
        return self.analyze(tuple(self.analyzer_case(c) for c in self.profile.cases),tuple(self.ledgers))

    def coverage(self,row):
        result=self.whole_analysis()
        summary={key:value for key,value in result.items() if key!="cases"}
        expected=dict(summary,case_counts=dict(expected=84,computed=84,written=84,native=78,harness=6,population=68))
        self.need(_same(row["body"],expected),"coverage_summary_disagreement")
        state="unknown" if not summary["coverage_complete"] else "complete_available" if summary["required_available"] else "complete_unavailable"
        self.need(row["native_state"]["coverage_state"]==state,"coverage_state_disagreement")
        self.delta(row,{}); self.progress(row)
        return dict(coverage=(result,summary))

    def selected_prefix(self,row):
        index=len(self.prefixes); choices=self.summary["selected_prefixes"]
        self.need(choices is not None and index<len(choices),"unexpected_selected_prefix")
        choice=choices[index]; c=self.profile.cases[choice["case_ordinal"]]
        boundary=self.analysis["cases"][c.ordinal]["boundaries"][choice["token_ordinal"]]
        expected=dict(selection_index=index,**choice,pending_interval=[boundary["pending_start"],boundary["pending_end"]],
            piece_interval=[boundary["start"],boundary["end"]],complete_widths=boundary["complete_widths"],
            witnesses=boundary["witnesses"],prefix_sha256=self.hash(c.raw[:choice["byte_cut"]]))
        body=row["body"]; self.keys(body,_T["coverage"]["selected_prefix_body_keys"],"prefix_body_fields")
        self.need(all(_same(body[key],value) for key,value in expected.items()),"selected_prefix_geometry")
        lengths=self.ledgers[c.ordinal]["piece_byte_lengths"][:choice["take_tokens"]]
        member,rejected=self.membership(body["observation"],lengths)
        matches=body["observation"]["all_input_tokens_admitted"] is True and member is False
        self.need(body["matches_expected"] is matches,"selected_prefix_matches")
        n=choice["take_tokens"]
        self.delta(row,dict(llama_sampler_init_grammar=1,llama_sampler_free=1,
            llama_sampler_apply=rejected+1 if rejected is not None else n+len(self.eogs),
            llama_sampler_accept=rejected if rejected is not None else n),n)
        count=self.native_geometry+len(self.prefixes)+1
        self.need(row["native_state"]["sampler_nonnull_returns"]==count and
            row["native_state"]["sampler_free_returned_nonnull"]==count and
            row["native_state"]["samplers_owned"]==0 and row["native_state"]["sampler_release_unknown"]==0,"prefix_sampler_ownership")
        self.progress(row,prefix=True)
        return dict(prefix=body)

    def normal_footer(self,row):
        event=row["event"]; body=row["body"]
        if event=="unicode_cleanup_returned":
            self.keys(body,_T["event_order"]["cleanup_body_keys"],"cleanup_body_fields")
            self.delta(row,dict(llama_model_free=1,llama_backend_free=1)); self.progress(row)
            s=row["native_state"]; c=row["native_call_counters"]
            expected=dict(sampler_init_returns=c["llama_sampler_init_grammar"]["returned"],
                sampler_free_returns=c["llama_sampler_free"]["returned"],samplers_owned=s["samplers_owned"],
                sampler_release_unknown=s["sampler_release_unknown"],model_free_return_observed=s["model_free_return_observed"],
                backend_free_return_observed=s["backend_free_return_observed"],cleanup_failed=s["cleanup_failed"])
            self.need(_same(body,expected) and self.clean(row),"cleanup_return_inconsistent")
            return dict(cleanup=True)
        self.delta(row,{}); self.progress(row)
        if event=="unicode_batch_returned":
            self.keys(body,_T["event_order"]["batch_body_keys"],"batch_body_fields")
            u=len(self.prefixes)
            expected=dict(cases_computed=84,case_results_written=84,stratum_computed=self.strata,
                stratum_results_written=self.strata,native_case_results=78,harness_dispositions=6,
                selected_prefixes_computed=u,selected_prefix_results_written=u,required_available=True,
                all_case_QC_complete=True,all_expected_membership_outcomes_match=True,
                total_token_work_reserved=row["native_state"]["token_work_reserved"],scientific_validation="not_established")
            self.need(all(_same(body[k],v) for k,v in expected.items()),"batch_claims")
            self.need(self.summary["required_available"] is True and self.summary["all_case_QC_complete"] is True and
                self.known_membership==78 and all(c["matches_authored_native_expectation"] is True for c in self.cases if c["QC"]["status"]!="harness_ineligible") and
                all(p["matches_expected"] is True for p in self.prefixes),"batch_not_successful")
            self.need(self.clean(row) and row["native_call_counters"]["llama_sampler_init_grammar"]["returned"]==78+u and
                row["native_call_counters"]["llama_sampler_free"]["returned"]==78+u,"batch_sampler_counts")
            self.need(row["native_state"]["total_attempted"]<=530477 and row["native_state"]["token_work_reserved"]<=69108,"fixed_profile_work_cap")
            self.module_report(body,"post_cpu")
            return dict(batch=True)
        self.keys(body,("status","elapsed_ms"),"normal_body_fields")
        self.need(body["status"]=="unicode_controls_observations_complete_independent_qualification_pending","normal_status")
        self.need(_uint(body["elapsed_ms"]) and self.previous_time<=body["elapsed_ms"]<=row["elapsed_ms"],"normal_body_time")
        return dict(normal=True)

    def failure_identity(self,error_class,reason,elapsed,sequence):
        self.need(type(error_class) is str and error_class in _T["closure"]["failure"]["child_error_class_enum"],"failure_error_class")
        self.need(type(reason) is str and reason in _T["closure"]["failure"]["reason_code_enum"],"failure_reason")
        if error_class=="StandardException": self.need(reason=="nonprotocol_cpp_exception","standard_failure_reason")
        if error_class=="UnknownException": self.need(reason=="unknown_cpp_exception","unknown_failure_reason")
        if error_class=="BridgeError": self.need(reason not in ("nonprotocol_cpp_exception","unknown_cpp_exception"),"bridge_failure_reason")
        return self.hash(_canonical(dict(pid=self.bindings.expected_child_pid,error_class=error_class,reason_code=reason,
            elapsed_ms=elapsed,row_sequence_reserved=sequence)))

    def failure_tail(self,row):
        """Bound unknown work to the next DECLARED phase, never new documents."""
        self.progress(row,failure=True)
        if len(self.cases)!=84: return "unfinished_setup_or_case"
        choices=self.summary["selected_prefixes"] if self.summary is not None else None
        prefix_phase=self.selection and choices is not None and len(self.prefixes)<len(choices)
        permitted={"llama_model_free","llama_backend_free"}
        token_delta=row["native_state"]["token_work_reserved"]-self.previous["native_state"]["token_work_reserved"]
        if prefix_phase:
            n=choices[len(self.prefixes)]["take_tokens"]
            caps=dict(llama_sampler_init_grammar=1,llama_sampler_free=1,llama_sampler_apply=n+len(self.eogs),llama_sampler_accept=n)
            permitted.update(caps)
            for name,cap in caps.items():
                self.need(all(0<=row["native_call_counters"][name][k]-self.previous["native_call_counters"][name][k]<=cap for k in ("attempted","returned")),"failure_prefix_call_cap")
            self.need(0<=token_delta<=n,"failure_prefix_token_work")
        else: self.need(token_delta==0,"failure_new_token_work")
        for name,c in row["native_call_counters"].items():
            if name not in permitted:
                self.need(_same(c,self.previous["native_call_counters"][name]),"failure_after_completed_phase_new_work")
        return "declared_next_prefix" if prefix_phase else "completed_work_cleanup_only"

    def failure_row(self,row):
        body=row["body"]; self.keys(body,_T["closure"]["failure"]["JSONL_exact_body_keys"],"failure_body_fields")
        failure_id=self.failure_identity(body["error_class"],body["reason_code"],row["elapsed_ms"],row["row_sequence"])
        self.need(_digest(body["primary_failure_id"]) and body["primary_failure_id"]==failure_id,"failure_identity")
        self.need(body["diagnostic_file"] in (None,"failure.json") and body["profile_qualification"]=="not_established","failure_disposition")
        tail_phase=self.failure_tail(row)
        if self.summary is not None:
            reason=body["reason_code"]
            if reason=="required_coverage_unavailable": self.need(self.summary["required_available"] is False,"failure_coverage_cause")
            if reason=="required_coverage_unknown": self.need(self.summary["coverage_complete"] is False,"failure_unknown_coverage_cause")
            if reason=="document_QC_unknown": self.need(self.summary["all_case_QC_complete"] is False,"failure_QC_cause")
            if reason=="case_expectation_mismatch": self.need(any(c["QC"]["status"]!="harness_ineligible" and c["matches_authored_native_expectation"] is not True for c in self.cases),"failure_membership_cause")
        return dict(failure=row,failure_tail_phase=tail_phase)

    def expected_event(self):
        if self.validated_rows<15: return _T["event_order"]["setup_events"][self.validated_rows]["event"]
        if len(self.cases)<84:
            return "unicode_before_case" if self.validated_rows==15+2*len(self.cases) else "unicode_case_result"
        if self.summary is None: return "unicode_coverage_summary"
        if not self.selection: return "unicode_selection_plan"
        selected=self.summary["selected_prefixes"]
        if selected is not None and len(self.prefixes)<len(selected): return "unicode_selected_prefix_result"
        if not self.cleanup: return "unicode_cleanup_returned"
        if not self.batch: return "unicode_batch_returned"
        if not self.normal: return "child_normal_completion"
        return None

    def process(self,row,line):
        self.common(row)
        self.need(type(row["row_sequence"]) is int and row["row_sequence"]==self.validated_rows and row["row_sequence"]<276,"row_sequence")
        event=row["event"]; self.need(type(event) is str,"event_type")
        self.need(self.failure is None,"completed_row_after_failure")
        setup_events=tuple(r["event"] for r in _T["event_order"]["setup_events"])
        bucket="setup" if event in setup_events else {"unicode_before_case":"before","unicode_case_result":"case","unicode_selected_prefix_result":"selected"}.get(event,"footer")
        cap=65536 if bucket in ("case","selected") else 8192
        self.need(len(line)<=cap,"event_row_byte_cap")
        limits=dict(setup=64,before=96,case=96,selected=4,footer=16)
        self.need(self.buckets[bucket]<limits[bucket],"event_bucket_cap")
        self.need(type(row["body"]) is dict,"body_object")
        if event=="failure": changes=self.failure_row(row)
        else:
            self.need(event==self.expected_event(),"event_order")
            if self.previous is not None:
                self.need(all(c["attempted"]==c["returned"] for c in self.previous["native_call_counters"].values()),"new_work_after_unreturned_call")
            if self.validated_rows<15: changes=self.setup(row)
            elif event=="unicode_before_case":
                self.keys(row["body"],_T["event_order"]["before_case_body_keys"],"before_body_fields")
                self.reference(row["body"],len(self.cases),before=True); self.delta(row,{}); self.progress(row); changes={}
            elif event=="unicode_case_result": changes=self.document(row)
            elif event=="unicode_coverage_summary": changes=self.coverage(row)
            elif event=="unicode_selection_plan":
                self.need(_same(row["body"],dict(selectors=self.summary["selectors"],selected_prefixes=self.summary["selected_prefixes"])),"selection_plan_disagreement")
                self.need(self.summary["required_available"] is True,"selection_without_required_coverage")
                self.delta(row,{}); self.progress(row); changes=dict(selection=True)
            elif event=="unicode_selected_prefix_result": changes=self.selected_prefix(row)
            else: changes=self.normal_footer(row)
        self.callback()
        # Only after every row/body/source/accounting check succeeds do source
        # instrumentation and ledgers enter the validator's committed prefix.
        if "vocabulary" in changes: self.nv,self.eogs=changes["vocabulary"]
        if "case" in changes:
            result,ledger,geometry=changes["case"]; index=len(self.cases)
            self.cases.append(result); self.ledgers[index]=ledger; self.strata[self.profile.cases[index].stratum_index]+=1
            self.native_geometry+=int(geometry is not None)
            self.known_membership+=int(type(result["observation"]["native_member"]) is bool)
            self.harness+=int(result["QC"]["status"]=="harness_ineligible")
        if "coverage" in changes: self.analysis,self.summary=changes["coverage"]
        if "prefix" in changes: self.prefixes.append(changes["prefix"])
        for flag in ("selection","cleanup","batch","normal"):
            if flag in changes: setattr(self,flag,changes[flag])
        if "failure" in changes: self.failure=changes["failure"]; self.failure_line=line
        if "failure_tail_phase" in changes: self.failure_tail_phase=changes["failure_tail_phase"]
        if event in _T["times"]["work_events"] and row["elapsed_ms"]>117000:
            self.reported_budget_violations.append(dict(row=self.validated_rows,kind="reported_work_elapsed"))
        if row["elapsed_ms"]>120000 or event=="child_normal_completion" and row["body"]["elapsed_ms"]>120000:
            self.reported_budget_violations.append(dict(row=self.validated_rows,kind="reported_whole_child_elapsed"))
        self.buckets[bucket]+=1; self.validated_rows+=1; self.previous=row; self.previous_time=row["elapsed_ms"]

    def marker_record(self,raw):
        self.marker_seen=True
        self.need(type(raw) is bytes and 1<=len(raw)<=65536,"marker_type_or_cap")
        content=raw[:-1] if raw.endswith(b"\n") else raw
        marker=self.parse(content)
        common=_ROOT-{"row_sequence","event","body"}
        extra={"status","profile_id","pid","row_sequence_reserved","primary_failure_id","error_class","reason_code","failure_row_publication","diagnostic"}
        self.keys(marker,common|extra,"marker_fields")
        # A marker uses a reused logical failure-reservation time. With a row it
        # is equal, otherwise it follows the last completed normal prefix.
        self.common(marker,marker=True)
        self.need(marker["status"]=="failed" and marker["profile_id"]==PROFILE_ID,"marker_disposition")
        self.need(type(marker["pid"]) is int and marker["pid"]==self.bindings.expected_child_pid,"marker_PID")
        sequence=marker["row_sequence_reserved"]
        self.need(_uint(sequence,275),"marker_reserved_sequence")
        identity=self.failure_identity(marker["error_class"],marker["reason_code"],marker["elapsed_ms"],sequence)
        self.need(_digest(marker["primary_failure_id"]) and marker["primary_failure_id"]==identity,"marker_identity")
        publication=marker["failure_row_publication"]
        self.keys(publication,_T["closure"]["failure"]["publication_exact_keys"],"publication_fields")
        self.need(all(type(publication[k]) is bool for k in ("attempt_reserved","write_attempted","return_observed")),"publication_flags")
        self.need(not publication["write_attempted"] or publication["attempt_reserved"],"publication_write_reservation")
        self.need(not publication["return_observed"] or publication["write_attempted"],"publication_return_attempt")
        self.need(publication["known_bytes"] is None or _uint(publication["known_bytes"],8192),"publication_known_count")
        self.need(publication["sha256"] is None or _digest(publication["sha256"]),"publication_digest_type")
        self.need(publication["error_class"] is None or type(publication["error_class"]) is str and publication["error_class"] in _T["closure"]["failure"]["child_error_class_enum"],"publication_error")
        if publication["sha256"] is not None:
            self.need(publication["known_bytes"] is not None and publication["write_attempted"],"publication_known_digest")
        if self.failure is not None:
            failure=self.failure
            self.need(sequence==failure["row_sequence"] and marker["elapsed_ms"]==failure["elapsed_ms"],"marker_failure_reservation")
            self.need(all(marker[k]==failure["body"][k] for k in ("primary_failure_id","error_class","reason_code")),"marker_failure_binding")
            self.need(_same(marker["native_call_counters"],failure["native_call_counters"]) and _same(marker["native_state"],failure["native_state"]),"marker_native_snapshot")
            if publication["sha256"] is not None:
                self.need(publication["sha256"]==self.hash(self.failure_line) and publication["known_bytes"]==len(self.failure_line),"publication_exact_row")
        else:
            self.need(sequence>=self.validated_rows,"marker_absent_row_reservation")
            self.failure_tail_phase=self.failure_tail(marker)
        diagnostic=marker["diagnostic"]; self.keys(diagnostic,("kind","value"),"diagnostic_fields")
        self.need(type(diagnostic["kind"]) is str and diagnostic["kind"] in ("none","module_policy_rejection"),"diagnostic_kind")
        if diagnostic["kind"]=="none": self.need(diagnostic["value"] is None,"diagnostic_none")
        else:
            self.need(type(diagnostic["value"]) is dict,"diagnostic_module_object")
            self.opaque_diagnostic=True
        self.marker=marker; self.callback()

    def finish(self):
        # Recompute lower bounds even for a missing suffix once nv/EOG is known.
        analysis=self.analysis
        if analysis is None and self.nv is not None: analysis=self.whole_analysis()
        summary={k:v for k,v in analysis.items() if k!="cases"} if analysis is not None else None
        negative=self.failure is not None or self.marker_seen
        clean=self.clean(self.marker if self.marker is not None else self.previous)
        complete=self.normal and not negative and not self.tail and not self.reported_budget_violations
        if complete: classification="complete_success_consistent"
        elif len(self.cases)==84 and negative and clean and not self.tail and not self.opaque_diagnostic:
            classification="complete_negative_consistent"
        else: classification="partial_observation"
        snapshot=self.snapshot()
        snapshot.update(classification=classification,source_cleanup_consistent=clean,
            raw_capture_present=self.capture_present,raw_bytes=self.raw_size,raw_sha256=self.raw_digest,
            unterminated_tail=self.tail,recomputed_summary=summary,cases=self.cases,selected_prefixes=self.prefixes,
            final_native_state=None if self.previous is None else self.previous["native_state"],
            final_native_call_counters=None if self.previous is None else self.previous["native_call_counters"],
            all_expected_membership_outcomes_match=(all(c["matches_authored_native_expectation"] is True for c in self.cases if c["QC"]["status"]!="harness_ineligible")
                if self.known_membership==78 else None),
            first_problem=None if complete else ("terminal_negative" if negative else "reported_budget" if self.reported_budget_violations else "incomplete_observation"),
            failure=None if self.failure is None else self.failure["body"],failure_marker=self.marker,
            terminal_source_phase=getattr(self,"failure_tail_phase",None),
            module_diagnostic_consistency="external_pending" if self.opaque_diagnostic else "not_applicable",
            external_pending_bindings=_thaw(_T["external_pending"]),profile_qualified=False,originals_authenticated=False,
            runtime_authorized=False,scientific_validation="not_established")
        self.callback(); result=_issue(snapshot); self.callback(); return result


def observe(raw,profile,bindings,*,failure_marker=None,check):
    if not callable(check): raise ObservationError("required_check_callback")
    check()
    reader=_Reader(profile,bindings,check)
    reader.marker_seen=failure_marker is not None
    reader.need(type(profile) is _codec.ValidatedProfile and getattr(profile,"_factory",None) is _codec._FACTORY,"factory_profile_required")
    reader.need(profile.source_pins==_codec.SOURCE_PINS and len(profile.cases)==84 and len(profile.stages)==4 and len(profile.grammars)==2,"profile_source_scope")
    reader.validate_bindings()
    # Dependency encode carries the ORIGINAL check through its own isolated
    # data catches; no wrapper catches caller exceptions from this call.
    encoded=_codec.encode(profile,check=check)
    reader.pack_digest=reader.hash(encoded)
    reader.need(len(encoded)==37766 and reader.pack_digest==bindings.expected_newpack_sha256,"deterministic_pack_binding")
    reader.need(raw is None or type(raw) is bytes,"capture_type")
    if raw is not None:
        reader.capture_present=True; reader.need(len(raw)<=8*1024*1024 and len(raw)<=7995392,"JSONL_byte_cap")
        reader.raw_size=len(raw); reader.raw_digest=reader.hash(raw)
        at=0
        while at<len(raw):
            reader.offset=at; reader.row_index=reader.validated_rows
            reader.callback(); end=raw.find(b"\n",at)
            if end<0:
                tail=raw[at:]; reader.need(len(tail)<=65536,"unterminated_tail_cap")
                reader.tail=dict(offset=at,bytes=len(tail),sha256=reader.hash(tail)); break
            reader.need(reader.validated_rows<276 and end+1-at<=65536,"row_frame_cap")
            line=raw[at:end+1]; reader.callback()
            parsed=reader.parse(line[:-1]); reader.process(parsed,line)
            at=end+1
    if failure_marker is not None:
        reader.row_index=reader.validated_rows; reader.offset=reader.raw_size
        reader.marker_record(failure_marker)
    return reader.finish()


def require_complete_success(observation,*,check):
    if not callable(check): raise ObservationError("required_check_callback")
    check()
    if type(observation) is not Observation or getattr(observation,"_issued",None) is not _ISSUED:
        raise ObservationError("source_issued_observation_required")
    if observation._data["classification"]!="complete_success_consistent":
        prefix={key:observation._data[key] for key in ("validated_rows","validated_case_rows","validated_native_geometry_rows",
            "known_membership_outcomes","validated_harness_rows","case_collection_complete","normal_schedule_complete","terminal_negative_seen")}
        raise ObservationError("complete_success_required",validated_prefix=prefix)
    check(); return observation
