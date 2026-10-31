"""Author fictional complete histories; no observation validator or native calls.

Only explicit NEW review metadata/pure modules are read. Complete new pack bytes
remain in memory. Native calls below are arithmetic events on a fictional book.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import time
import types

HERE = Path(__file__).resolve().parent
REVIEW = HERE.parent
CONTROL = REVIEW / "recovery-step9-unicode-control-20261029"
WIRE = REVIEW / "recovery-step9-unicode-wire-20261029"
CODEC = REVIEW / "recovery-step9-unicode-codec-20261029"
ORACLE = REVIEW / "recovery-step9-utf8-oracle-20261029"
TARGET = HERE / "UNICODE-OBSERVATIONS-TRACE-FIXTURES-v1.json"
FREEZE = HERE / "UNICODE-OBSERVATIONS-TRACE-FREEZE-v1.json"
CONTEXT = HERE / "UNICODE-OBSERVATIONS-SYNTHETIC-CONTEXT-v1.json"
PLAN = HERE / "UNICODE-OBSERVATIONS-TRACE-AUTHORING-PLAN-v2.json"
DESIGN = HERE / "UNICODE-OBSERVATIONS-DESIGN-CONTRACT-v2.json"
CLASSES = ("pending_width2", "pending_width3", "pending_width4", "same_piece_complete_scalar_then_pending")
STRATA = ("stage_source_report", "scalar_field_grid", "ASCII_escape_counterparts", "mixed_normalization_escape",
          "grammar_semantic_JSON_controls", "byte_harness_guards")
WIRE_FP = "75605c03fb5b9bac659538035d8205b34df2ae1781b997a3181a1564676aa6c4"
CALL_FP = "30d82a42c5338789644fea00f666e264fb3e4114637c2c37330386a177f17861"
MODULE_ID = "trusted-System32-recognition-v1"
MODULE_FP = "4d5e09d70d0f6e4cec6c1754dbbec1add6b2985754ead811128a27eb6a138713"
PROFILE_ID = "actual-v3-fullresponse-unicode-controls-v1"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(raw): return hashlib.sha256(raw).hexdigest()


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=digest(raw))


def load(path, expected, name):
    raw = path.read_bytes(); assert digest(raw) == expected
    module = types.ModuleType(name); module.__file__ = str(path); sys.modules[name] = module
    exec(compile(raw, str(path), "exec"), module.__dict__)
    return module


def authored_pieces(raw, mixed):
    join = next((i-1 for i in range(1, len(raw)) if 0xc2 <= raw[i] <= 0xf4 and raw[i-1] < 0x80), None) if mixed else None
    answer = [b""]; at = 0
    while at < len(raw):
        width = 2 if at == join else 1
        answer.append(raw[at:at+width]); at += width
    return answer


def authored_geometry(raw, pieces):
    """Independent literal scalar/piece arithmetic, not a JSONL reader."""
    intervals = []; at = 0
    for scalar in raw.decode("utf-8", "strict"):
        width = len(scalar.encode("utf-8")); intervals.append((at, at+width, width)); at += width
    assert at == len(raw) and b"".join(pieces) == raw
    rows = []; counts = dict.fromkeys(CLASSES, 0); matrix = [[0]*3 for _ in range(4)]; start = 0
    for ordinal, piece in enumerate(pieces):
        end = start+len(piece)
        row = dict(token_ordinal=ordinal, start=start, end=end, pending_start=None, pending_end=None,
                   complete_widths=[], witnesses=[], classes=[])
        pending = next((s for s in intervals if s[0] < end < s[1]), None) if piece else None
        if pending:
            left, right, width = pending; row.update(pending_start=left, pending_end=right)
            row["classes"].append(CLASSES[width-2]); counts[CLASSES[width-2]] += 1
            by_width = {}
            for a, b, w in intervals:
                if start <= a and b <= left: by_width.setdefault(w, [w, a, b])
            if by_width:
                row["classes"].append(CLASSES[3]); counts[CLASSES[3]] += 1
                row["complete_widths"] = sorted(by_width)
                row["witnesses"] = [by_width[w] for w in sorted(by_width)]
                for w in by_width: matrix[w-1][width-2] += 1
        rows.append(row); start = end
    return dict(boundaries=rows, counts=counts, matrix=matrix, zero_piece_count=sum(not p for p in pieces))


def authored_summary(source, geometries):
    counts = dict.fromkeys(CLASSES, 0); matrix = [[0]*3 for _ in range(4)]
    unknown = []
    for case, geometry in zip(source, geometries):
        if not case["coverage_population"]: continue
        if geometry is None: unknown.append(case["ordinal"]); continue
        for name in CLASSES: counts[name] += geometry["counts"][name]
        for i in range(4):
            for j in range(3): matrix[i][j] += geometry["matrix"][i][j]
    selectors = {} if not unknown else None; selected = [] if not unknown else None; indexed = {}
    for name in CLASSES if not unknown else ():
        found = next(((case, boundary) for case, geometry in zip(source, geometries) if case["coverage_population"]
                     for boundary in geometry["boundaries"] if name in boundary["classes"]), None)
        if found is None: selectors[name] = None; continue
        case, boundary = found; pair = (case["ordinal"], boundary["token_ordinal"])
        if pair not in indexed:
            indexed[pair] = len(selected)
            selected.append(dict(case_ordinal=pair[0], token_ordinal=pair[1], take_tokens=pair[1]+1,
                                 byte_cut=boundary["end"], classes=boundary["classes"]))
        selectors[name] = indexed[pair]
    return dict(coverage_complete=not unknown,
                all_case_QC_complete=all(not case["expected"]["native_byte_eligible"] or geometry is not None for case, geometry in zip(source, geometries)),
                counts=counts if not unknown else None, matrix=matrix if not unknown else None,
                known_counts_lower_bound=copy.deepcopy(counts), known_matrix_lower_bound=copy.deepcopy(matrix),
                unknown_population_ordinals=unknown, selectors=selectors, selected_prefixes=selected,
                required_available=all(counts[name] > 0 for name in CLASSES) if not unknown else None)


class FictionalBook:
    """Arithmetically authored attempted/returned side effects; never dispatch."""
    def __init__(self, semantics):
        self.names = semantics["API_accounting"]["names"]
        self.counters = {name: dict(attempted=0, returned=0) for name in self.names}
        self.state = {}
        for name, rule in semantics["framing"]["native_state_fields"].items():
            if rule == "strict bool": value = False
            elif isinstance(rule, dict): value = 0
            elif isinstance(rule, list): value = None if None in rule else rule[0]
            else: value = [0]*6
            self.state[name] = value
        self.state.update(current_case_index=-1, current_selected_prefix_index=-1, last_EOG_id=-1)
        assert len(self.state) == 45

    def call(self, name, kind=1, value=0):
        c, s = self.counters[name], self.state
        c["attempted"] += 1; s["total_attempted"] += 1; s["last_attempt"] = name
        if name == "llama_sampler_free":
            assert s["samplers_owned"] > 0; s["samplers_owned"] -= 1; s["sampler_release_unknown"] += 1
        if name in ("llama_model_free", "llama_backend_free"):
            prefix = "model" if name == "llama_model_free" else "backend"
            s[prefix+"_free_attempted"] = True; s[prefix+"_owned"] = False; s[prefix+"_release_unknown"] = True
        c["returned"] += 1; s["total_returned"] += 1; s["last_return"] = name; s["last_return_kind"] = kind
        if kind == 2:
            s["last_scalar"] = int(value)
            if name == "llama_tokenize": s["last_tokenize_return"] = int(value)
            if name == "llama_token_to_piece": s["last_piece_return"] = int(value)
        if kind == 3:
            s["last_pointer_nonnull"] = bool(value)
            if name == "ggml_backend_load": s.update(cpu_load_return_observed=True, cpu_registry_nonnull=bool(value))
            if name == "llama_model_load_from_splits": s.update(model_load_return_observed=True, model_return_nonnull=bool(value), model_owned=bool(value))
            if name == "llama_sampler_init_grammar" and value:
                s["sampler_nonnull_returns"] += 1; s["samplers_owned"] += 1
        if name == "llama_backend_init": s.update(backend_init_return_observed=True, backend_owned=True)
        if name == "llama_sampler_free": s["sampler_release_unknown"] -= 1; s["sampler_free_returned_nonnull"] += 1
        if name in ("llama_model_free", "llama_backend_free"):
            prefix = "model" if name == "llama_model_free" else "backend"
            s[prefix+"_free_return_observed"] = True; s[prefix+"_release_unknown"] = False

    def identity(self, initial):
        if initial:
            self.call("ggml_backend_load", 3, True)
            self.call("ggml_backend_reg_dev_count", 2, 1); self.call("ggml_backend_reg_dev_get", 3, True)
        else: self.call("llama_backend_init")
        for name, kind, value in (("ggml_backend_reg_count",2,1),("ggml_backend_reg_get",3,True),
                ("ggml_backend_reg_name",3,True),("ggml_backend_reg_dev_count",2,1),("ggml_backend_reg_dev_get",3,True),
                ("ggml_backend_dev_count",2,1),("ggml_backend_dev_get",3,True),("ggml_backend_dev_name",3,True),("ggml_backend_dev_type",2,0)):
            self.call(name, kind, value)

    def tokenize_and_pieces(self, pieces):
        n = len(pieces)
        self.call("llama_tokenize", 2, 1 if n == 1 else -n)
        if n != 1: self.call("llama_tokenize", 2, n)
        for piece in pieces:
            self.call("llama_token_to_piece", 2, len(piece) if len(piece) <= 1 else -len(piece))
            if len(piece) > 1: self.call("llama_token_to_piece", 2, len(piece))
        self.state["token_work_reserved"] += n

    def grammar(self, n, member, *, prefix=False, eog_reject=False):
        self.call("llama_sampler_init_grammar", 3, True)
        rejected = None if member or prefix or eog_reject else n-1
        for index in range(n):
            admitted = rejected is None or index < rejected
            self.call("llama_sampler_apply"); self.state.update(last_apply_return_observed=True,
                last_apply_shape_valid=True, last_apply_logit_kind=2 if admitted else 1)
            if not admitted: break
            self.call("llama_sampler_accept")
        if rejected is None:
            for _ in range(2):
                self.call("llama_sampler_apply"); self.state.update(last_apply_return_observed=True,
                    last_apply_shape_valid=True, last_apply_logit_kind=1 if prefix or eog_reject or not member else 2)
        self.call("llama_sampler_free")
        return rejected

    def cleanup(self):
        assert not self.state["samplers_owned"] and not self.state["sampler_release_unknown"]
        self.call("llama_model_free"); self.call("llama_backend_free")


class TraceAuthor:
    def __init__(self, semantics, context, source, profile, pack_sha, mixed=True, conflict=False, unknown=False):
        self.semantics, self.context, self.source, self.profile, self.pack_sha = semantics, context, source, profile, pack_sha
        self.book = FictionalBook(semantics); self.rows = []; self.marker = None; self.conflict = conflict; self.unknown = unknown
        self.table = {row["piece_hex"]: row["id"] for row in context["ordinary_piece_table"]}
        self.pieces = [authored_pieces(c.raw, mixed) if c.native_byte_eligible else None for c in profile.cases]
        self.geometries = [authored_geometry(c.raw, p) if p is not None else None for c, p in zip(profile.cases, self.pieces)]
        if unknown: self.geometries[4] = None
        self.summary = authored_summary(source, self.geometries)
        self.ledgers = [None if p is None else dict(token_ids=[self.table[x.hex()] for x in p],
            piece_byte_lengths=[len(x) for x in p], piece_hex=[x.hex() for x in p]) for p in self.pieces]
        if unknown: self.ledgers[4] = None
        self.conflict_index = 4
        assert source[self.conflict_index]["expected"]["native_membership"] is True

    def emit(self, event, body):
        row = dict(schema_version=1, row_sequence=len(self.rows), event=event, elapsed_ms=100+10*len(self.rows),
                   wire_semantics_sha256=WIRE_FP, native_call_contract_sha256=CALL_FP,
                   native_call_counters=copy.deepcopy(self.book.counters), native_call_scope="explicit_bridge_export_calls_only",
                   unrecorded_killed_tail="unknown_since_last_acknowledged_snapshot", native_state=copy.deepcopy(self.book.state), body=copy.deepcopy(body))
        self.rows.append(row)
        return row

    def modules(self, phase):
        runtime = self.context["expected_runtime"]
        rows = [dict(name="recognizer.exe", path=self.context["expected_self"])]
        rows += [dict(name=name, path=runtime+"\\"+name) for name in ("libomp.dll","ggml-base.dll","ggml.dll","llama.dll")]
        if phase == "post_cpu": rows.append(dict(name="ggml-cpu-x64.dll", path=runtime+r"\ggml-cpu-x64.dll"))
        return dict(module_policy_id=MODULE_ID, module_policy_sha256=MODULE_FP, module_policy_phase=phase, modules=rows)

    def setup(self):
        schemas = self.semantics["event_order"]["setup_body_schemas"]
        for index, entry in enumerate(self.semantics["event_order"]["setup_events"]):
            event = entry["event"]; body = {}
            if index == 0: body = dict(dependency_native_initialization_possible=True)
            elif index == 1:
                body = self.modules("pre_cpu"); body["layouts"] = schemas[event]["fields"]["layouts"]["exact_typed_value"]
            elif index == 2:
                self.book.call("llama_version",3,True); self.book.call("llama_model_default_params",4)
                body = dict(version="0.7.0-dev", defaults=schemas[event]["fields"]["defaults"]["exact_typed_value"], no_backend_or_model_call_so_far=True)
            elif index == 3:
                body = dict(pack_sha256=self.pack_sha, wire_semantics_sha256=WIRE_FP,
                    corpus_sha256="13e2c2f2900802729c0d39fa9b7851c56ab3db6afdc45c4b15c2f7f80bd6523c",
                    stages_sha256="ad688168a366d5e95413ec69731d030c54431663e6574fb93445ced2b580413a",
                    cases=84, stage_instances=4, unique_grammars=2, coverage_classes=4)
            elif 4 <= index <= 9:
                shard = (index-4)//2; record = self.context["ordered_shard_descriptors"][shard]
                body = dict(index=shard, path=record["path"], expected_bytes=record["bytes"]) if index % 2 == 0 else dict(index=shard, bytes=record["bytes"], sha256=record["sha256"])
            elif index == 10: body = dict(weight_file_hash_reads=True, tensor_weight_allocation_claim=False)
            elif index == 11:
                self.book.identity(True); body = self.modules("post_cpu")
                body.update(registry_count=1,device_count=1,registry_name="CPU",device_name="CPU")
            elif index == 12: self.book.identity(False); body = self.modules("post_cpu")
            elif index == 13:
                body = dict(effective_params=schemas[event]["fields"]["effective_params"]["exact_typed_value"],
                    empty_devices_array_nonnull=True, cooperative_deadline_not_interruptible_native_call=True)
            elif index == 14:
                self.book.call("llama_model_load_from_splits",3,True); self.book.call("llama_model_get_vocab",3,True)
                self.book.call("llama_vocab_n_tokens",2,1024)
                for value in range(1024):
                    yes = value in (1022,1023); self.book.call("llama_vocab_is_eog",2,int(yes))
                    self.book.state.update(EOG_ids_examined=value+1,last_EOG_id=value,last_EOG_returned=True,last_EOG_value=yes)
                body = self.modules("post_cpu"); body.update(vocabulary_count=1024,EOG_ids=[1022,1023],EOG_JSON_sha256=digest(canonical([1022,1023])))
            expected = {name:1024 if isinstance(value,str) else value for name,value in entry["cumulative_attempted_equals_returned"].items()}
            assert {name:row["attempted"] for name,row in self.book.counters.items()} == expected
            self.emit(event,body)

    def case_reference(self, index):
        case, source = self.profile.cases[index], self.source[index]
        return dict(case_ordinal=index,case_id=case.id,stage_instance_id=source["stage_id"],
                    grammar_sha256=source["grammar_sha256"],raw_sha256=case.sha256,raw_bytes=len(case.raw))

    def empty_observation(self, status):
        return dict(status=status,native_member=None,all_input_tokens_admitted=None,
                    first_rejected_token_index=None,first_rejected_byte_start=None,first_rejected_byte_end=None,completion_EOG=None)

    def all_cases(self):
        for index, (case, source, pieces, geometry, ledger) in enumerate(zip(self.profile.cases,self.source,self.pieces,self.geometries,self.ledgers)):
            self.book.state["current_case_index"] = index
            reference = self.case_reference(index)
            self.emit("unicode_before_case",dict(reference,declared_native_byte_eligible=case.native_byte_eligible))
            expected = source["expected"]
            authored = dict(native_member=expected["native_membership"],generation_member=expected["generation_grammar_membership"],
                            semantic_eligible=expected["complete_v3_semantic_validation"],coverage_population=source["coverage_population"])
            if not case.native_byte_eligible:
                status = "harness_raw_nul_rejection" if case.harness_kind == 2 else "harness_utf8_rejection"
                qc = dict(status="harness_ineligible",reason=status); observation = self.empty_observation(status)
                compact = dict(counts=None,matrix=None,zero_piece_count=None); matches = None
            elif self.unknown and index == 4:
                self.book.call("llama_tokenize",2,0)
                qc = dict(status="unknown",reason="tokenize_size_invalid")
                observation = self.empty_observation("not_attempted_QC_unknown")
                compact = dict(counts=None,matrix=None,zero_piece_count=None); matches = None
            else:
                self.book.tokenize_and_pieces(pieces)
                member = expected["native_membership"]
                conflicting = self.conflict and index == self.conflict_index
                rejected = self.book.grammar(len(pieces),member,eog_reject=conflicting)
                if rejected is not None:
                    start = sum(len(p) for p in pieces[:rejected]); end = start+len(pieces[rejected])
                    observation = dict(status="native_token_rejection",native_member=False,all_input_tokens_admitted=False,
                        first_rejected_token_index=rejected,first_rejected_byte_start=start,first_rejected_byte_end=end,completion_EOG=None)
                else:
                    admitted = bool(member) and not conflicting
                    observation = dict(status="native_member" if admitted else "native_eog_rejection",native_member=admitted,
                        all_input_tokens_admitted=True,first_rejected_token_index=None,first_rejected_byte_start=None,
                        first_rejected_byte_end=None,completion_EOG=[dict(id=token,admitted=admitted) for token in self.context["EOG_ids"]])
                qc = dict(status="ok",reason=None)
                compact = {key:copy.deepcopy(geometry[key]) for key in ("counts","matrix","zero_piece_count")}
                matches = observation["native_member"] is member
            state = self.book.state; stratum = STRATA.index(source["stratum"])
            state["cases_computed"] += 1; state["stratum_computed"][stratum] += 1
            self.emit("unicode_case_result",dict(reference,authored_expected=authored,QC=qc,observation=observation,
                ledger=ledger,compact_analysis=compact,matches_authored_native_expectation=matches))
            state["case_results_written"] += 1; state["stratum_results_written"][stratum] += 1

    def coverage(self):
        state = self.book.state
        state["coverage_state"] = ("unknown" if not self.summary["coverage_complete"] else
                                   "complete_available" if self.summary["required_available"] else "complete_unavailable")
        body = dict(copy.deepcopy(self.summary),case_counts=dict(expected=84,computed=84,written=84,native=78,harness=6,population=68))
        self.emit("unicode_coverage_summary",body)

    def prefixes(self):
        selected = self.summary["selected_prefixes"]
        self.emit("unicode_selection_plan",dict(selectors=self.summary["selectors"],selected_prefixes=selected))
        for index, choice in enumerate(selected):
            case_index, token_index = choice["case_ordinal"], choice["token_ordinal"]
            case = self.profile.cases[case_index]; boundary = self.geometries[case_index]["boundaries"][token_index]
            n = choice["take_tokens"]; state = self.book.state
            state["current_selected_prefix_index"] = index; state["token_work_reserved"] += n
            self.book.grammar(n,False,prefix=True)
            state["selected_prefixes_computed"] += 1
            observation = dict(status="native_eog_rejection",native_member=False,all_input_tokens_admitted=True,
                first_rejected_token_index=None,first_rejected_byte_start=None,first_rejected_byte_end=None,
                completion_EOG=[dict(id=token,admitted=False) for token in self.context["EOG_ids"]])
            body = dict(selection_index=index,case_ordinal=case_index,token_ordinal=token_index,take_tokens=n,
                byte_cut=choice["byte_cut"],classes=choice["classes"],pending_interval=[boundary["pending_start"],boundary["pending_end"]],
                piece_interval=[boundary["start"],boundary["end"]],complete_widths=boundary["complete_widths"],witnesses=boundary["witnesses"],
                prefix_sha256=digest(case.raw[:choice["byte_cut"]]),observation=observation,matches_expected=True)
            self.emit("unicode_selected_prefix_result",body)
            state["selected_prefix_results_written"] += 1

    def cleanup_row(self):
        self.book.cleanup(); state = self.book.state
        self.emit("unicode_cleanup_returned",dict(sampler_init_returns=self.book.counters["llama_sampler_init_grammar"]["returned"],
            sampler_free_returns=self.book.counters["llama_sampler_free"]["returned"],samplers_owned=state["samplers_owned"],
            sampler_release_unknown=state["sampler_release_unknown"],model_free_return_observed=True,
            backend_free_return_observed=True,cleanup_failed=False))

    def finish_success(self):
        self.prefixes(); self.cleanup_row(); state = self.book.state; u = len(self.summary["selected_prefixes"])
        body = dict(cases_computed=84,case_results_written=84,stratum_computed=list(state["stratum_computed"]),
            stratum_results_written=list(state["stratum_results_written"]),native_case_results=78,harness_dispositions=6,
            selected_prefixes_computed=u,selected_prefix_results_written=u,required_available=True,all_case_QC_complete=True,
            all_expected_membership_outcomes_match=True,total_token_work_reserved=state["token_work_reserved"],
            **self.modules("post_cpu"),scientific_validation="not_established")
        self.emit("unicode_batch_returned",body)
        self.emit("child_normal_completion",dict(status="unicode_controls_observations_complete_independent_qualification_pending",
                                                 elapsed_ms=100+10*len(self.rows)-5))

    def fail(self, reason, *, cleanup=True):
        if cleanup: self.book.cleanup()
        elapsed = 100+10*len(self.rows); sequence = len(self.rows)
        identity = dict(pid=self.context["expected_child_pid"],error_class="BridgeError",reason_code=reason,
                        elapsed_ms=elapsed,row_sequence_reserved=sequence)
        failure_id = digest(canonical(identity))
        row = self.emit("failure",dict(primary_failure_id=failure_id,error_class="BridgeError",reason_code=reason,
                                        diagnostic_file="failure.json",profile_qualification="not_established"))
        raw = canonical(row)+b"\n"
        marker = {key:copy.deepcopy(value) for key,value in row.items() if key not in ("row_sequence","event","body")}
        marker.update(status="failed",profile_id=PROFILE_ID,pid=self.context["expected_child_pid"],
            row_sequence_reserved=sequence,primary_failure_id=failure_id,error_class="BridgeError",reason_code=reason,
            failure_row_publication=dict(attempt_reserved=True,write_attempted=True,return_observed=True,
                                        known_bytes=len(raw),sha256=digest(raw),error_class=None),diagnostic=dict(kind="none",value=None))
        self.marker = marker

    def capture(self, identity, classification):
        lines = [canonical(row)+b"\n" for row in self.rows]; raw = b"".join(lines)
        return dict(id=identity,raw_hex=raw.hex(),bytes=len(raw),sha256=digest(raw),row_count=len(lines),
            row_offsets=[sum(map(len,lines[:i])) for i in range(len(lines))],
            failure_marker_hex=None if self.marker is None else (canonical(self.marker)+b"\n").hex(),
            bindings={key:copy.deepcopy(self.context[key]) for key in ("expected_child_pid","expected_self","expected_runtime",
                "ordered_shard_descriptors","expected_newpack_sha256")},
            expected_projection=dict(classification=classification,validated_case_rows=84,validated_harness_rows=6,
                case_collection_complete=True,normal_schedule_complete=classification=="complete_success_consistent",
                terminal_negative_seen=classification!="complete_success_consistent",profile_qualified=False,
                originals_authenticated=False,runtime_authorized=False),
            authored_geometry_summary=self.summary,authored_final_counters=copy.deepcopy(self.book.counters),
            source_scope="FICTIONAL whole-source history, not native observations or complete profile authority")


def null_measurements(): return dict(counts=None,matrix=None,zero_piece_count=None)


def scenario(base, identity, *, prefix=None, replacements=(), appends=(), tail=b"", marker_override="inherit",
             classification=None, cases=None, raises=None, strict_reject=False, purpose=""):
    """Frame literal mutations; this never parses or validates an observation."""
    raw = bytes.fromhex(base["raw_hex"])
    assert raw.endswith(b"\n")
    lines = [line+b"\n" for line in raw[:-1].split(b"\n")]
    # All authored base lines contain only source-generated LF framing. Arbitrary
    # test tails are added below, not split or decoded by this author.
    selected = lines if prefix is None else lines[:prefix]
    selected = list(selected)
    literal = []
    for index, row in replacements:
        value = canonical(row)+b"\n" if type(row) is dict else row
        selected[index] = value; literal.append(dict(index=index,raw_hex=value.hex()))
    appended = [canonical(row)+b"\n" if type(row) is dict else row for row in appends]
    materialized = b"".join(selected+appended)+tail
    expected = dict(profile_qualified=False,originals_authenticated=False,runtime_authorized=False)
    if classification: expected["classification"] = classification
    if cases is not None: expected["validated_case_rows"] = cases
    if raises: expected["raises"] = raises
    if strict_reject: expected["strict_requires"] = "ObservationError"
    return dict(id=identity,purpose=purpose,base_trace=base["id"],base_sha256=base["sha256"],
        prefix_rows=prefix,replace_rows=literal,append_rows_hex=[raw.hex() for raw in appended],tail_hex=tail.hex(),
        failure_marker="inherit" if marker_override == "inherit" else marker_override,
        materialized_bytes=len(materialized),materialized_sha256=digest(materialized),expected_projection=expected)


def main():
    started = time.monotonic()
    assert not TARGET.exists() and not FREEZE.exists()
    context = json.loads(CONTEXT.read_bytes())
    assert pin(CONTEXT)["sha256"] == "e3d8c2f45d333bdeab161ab12f06a9a6b284cda351496273cfc514d1e189c565"
    corpus_path = CONTROL / "UNICODE-CONTROL-CORPUS-v1.json"
    base_path = WIRE / "UNICODE-WIRE-DESIGN-CONTRACT-v2.json"
    framing_path = WIRE / "UNICODE-WIRE-FRAMING-CONTRACT-v1.json"
    corpus = json.loads(corpus_path.read_bytes())["cases"]
    semantics = json.loads(base_path.read_bytes())["semantic_contract"]
    load(ORACLE/"strict_utf8_oracle_v1.py", "4e5d36afa001339735a349a8ebab88a312cde1cb57fa43336e38ee4195134c21", "strict_utf8_oracle_v1")
    analyzer = load(CONTROL/"unicode_piece_analyzer_v1.py", "537a780a3d2d3b95d5fe4976cd8a073cf528db908badf3edf3e861e729ff8f9d", "fixture_corroborating_analyzer")
    codec = load(CODEC/"unicode_pack_codec_v2.py", "8ff0d6228fbec2900d52125f2e94e311cc22762d2d0b8b52c3eaadf0e59be91a", "fixture_profile_codec")
    paths = dict(base_design=base_path,framing_contract=framing_path,corpus=corpus_path,
                 stages=CONTROL/"UNICODE-CONTROL-STAGES-v1.json",profile_contract=CONTROL/"UNICODE-CONTROL-CONTRACT-v2.json",
                 analyzer_contract=CONTROL/"UNICODE-PIECE-ANALYZER-CONTRACT-v1.json")
    def budget(): assert time.monotonic()-started < 20, "Fictional trace author20s budget"
    profile = codec.make_profile(codec.SourceBytes(**{key:path.read_bytes() for key,path in paths.items()}),check=budget)
    in_memory_pack = codec.encode(profile,check=budget)
    assert len(in_memory_pack) == 37766 and digest(in_memory_pack) == context["expected_newpack_sha256"]
    analyzer_cases = tuple(dict(id=case.id,ordinal=case.ordinal,raw_bytes=case.raw,native_byte_eligible=case.native_byte_eligible,
        generation_member=source["expected"]["generation_grammar_membership"] is True,
        semantic_eligible=source["expected"]["complete_v3_semantic_validation"] is True) for case,source in zip(profile.cases,corpus))
    authors = []
    for identity, mixed, conflict, unknown in (("complete_positive",True,False,False),("complete_known_mixed_unavailable",False,False,False),
            ("complete_membership_conflict",True,True,False),("complete_population_QC_unknown",True,False,True)):
        budget(); author = TraceAuthor(semantics,context,corpus,profile,digest(in_memory_pack),mixed,conflict,unknown)
        supplied = tuple(None if ledger is None else {key:tuple(value) for key,value in ledger.items()} for ledger in author.ledgers)
        corroboration = analyzer.analyze(analyzer_cases,supplied,1024,(1022,1023)).to_dict()
        for key,value in author.summary.items(): assert corroboration[key] == value, (identity,key)
        for index, geometry in enumerate(author.geometries):
            if geometry is not None:
                for key,value in geometry.items(): assert corroboration["cases"][index][key] == value
        author.setup(); author.all_cases(); author.coverage()
        if identity == "complete_positive":
            assert author.summary["required_available"] is True and len(author.summary["selected_prefixes"]) == 3
            assert author.summary["selectors"][CLASSES[0]] == author.summary["selectors"][CLASSES[3]]
            author.finish_success()
        else:
            reason = "required_coverage_unknown" if unknown else "case_expectation_mismatch" if conflict else "required_coverage_unavailable"
            author.fail(reason)
        for api,row in author.book.counters.items():
            assert row["attempted"] == row["returned"] <= semantics["API_accounting"]["hard_caps"][api]
        authors.append((identity,author))
    bases = [author.capture(identity,"complete_success_consistent" if identity=="complete_positive" else "complete_negative_consistent") for identity,author in authors]
    positive = bases[0]; positive_author = authors[0][1]
    assert len(positive_author.rows) == 191
    assert [row["event"] for row in positive_author.rows[:15]] == [row["event"] for row in semantics["event_order"]["setup_events"]]
    positive["expected_projection"].update(validated_native_geometry_rows=78,known_membership_outcomes=78,
        unique_selected_prefix_results=3,all_expected_membership_outcomes_match=True)
    for base,(_,author) in zip(bases[1:],authors[1:]):
        base["expected_projection"].update(validated_native_geometry_rows=77 if author.unknown else 78,
            known_membership_outcomes=77 if author.unknown else 78,unique_selected_prefix_results=0,
            all_expected_membership_outcomes_match=None if author.unknown else not author.conflict)
    scenarios = []
    def add(identity, **kwargs): scenarios.append(scenario(positive,identity,**kwargs))
    add("setup_prefix_only",prefix=15,classification="partial_observation",cases=0,purpose="No completed cases or cleanup inferred from setup only.")
    add("before_case_without_result",prefix=16,classification="partial_observation",cases=0,purpose="Source before-case instrumentation is not a committed result.")
    add("first_case_own_write_lag",prefix=17,classification="partial_observation",cases=1,purpose="Valid case body commits1; source current row still reports written0 until future witness.")
    add("unterminated_mid_scalar_tail",prefix=16,tail=b'{"unclosed":"\xe2\x82',classification="partial_observation",cases=0,purpose="Truncated UTF8 tail is unknown and is never globally decoded as a completed row.")
    def changed(index, edit):
        row = copy.deepcopy(positive_author.rows[index]); edit(row); return (index,row)
    mutations = [
        ("bool_sequence",0,lambda r:r.update(row_sequence=True)),
        ("extra_ready_flag",0,lambda r:r.update(ready=True)),
        ("wrong_effective_fingerprint",0,lambda r:r.update(wire_semantics_sha256="0"*64)),
        ("wrong_setup_vector",14,lambda r:r["native_call_counters"]["llama_vocab_is_eog"].update(returned=1023)),
        ("case_claims_own_write",16,lambda r:r["native_state"].update(case_results_written=1)),
        ("wrong_stratum_progress",16,lambda r:r["native_state"]["stratum_computed"].__setitem__(0,2)),
        ("wrong_source_digest",16,lambda r:r["body"].update(raw_sha256="f"*64)),
        ("ordinary_EOG_token",16,lambda r:r["body"]["ledger"]["token_ids"].__setitem__(0,1022)),
        ("empty_piece_dropped",16,lambda r:[r["body"]["ledger"][key].pop(0) for key in ("token_ids","piece_byte_lengths","piece_hex")]),
        ("null_observation_object",16,lambda r:r["body"].update(observation=None)),
        ("wrong_native_membership_union",16,lambda r:r["body"]["observation"].update(native_member=False)),
        ("selector_not_first",184,lambda r:r["body"]["selectors"].update(pending_width2=1)),
        ("duplicate_prefix_selection",184,lambda r:r["body"]["selected_prefixes"].append(copy.deepcopy(r["body"]["selected_prefixes"][0]))),
        ("wrong_prefix_interval",185,lambda r:r["body"]["piece_interval"].__setitem__(1,r["body"]["byte_cut"]+1)),
        ("prefix_EOG_admitted",185,lambda r:r["body"]["observation"]["completion_EOG"][0].update(admitted=True)),
        ("old190_sampler_claim",188,lambda r:r["body"].update(sampler_init_returns=190)),
        ("body_time_after_common",190,lambda r:r["body"].update(elapsed_ms=r["elapsed_ms"]+1)),
        ("bool_common_time",190,lambda r:r.update(elapsed_ms=True)),
    ]
    for identity,index,edit in mutations:
        add(identity,replacements=[changed(index,edit)],raises="ObservationError",purpose="Authored isolated field/reference fault; no future validator used to generate expectation.")
    swapped = [(15,dict(copy.deepcopy(positive_author.rows[16]),row_sequence=15)),(16,dict(copy.deepcopy(positive_author.rows[15]),row_sequence=16))]
    add("result_before_before_case",replacements=swapped,raises="ObservationError",purpose="Valid body bytes cannot replace closed source order.")
    first_raw = canonical(positive_author.rows[0])+b"\n"
    add("completed_invalid_UTF8",replacements=[(0,first_raw[:-2]+b'\xff}\n')],raises="ObservationError")
    add("CRLF_row",replacements=[(0,first_raw[:-1]+b"\r\n")],raises="ObservationError")
    add("BOM_row",replacements=[(0,b"\xef\xbb\xbf"+first_raw)],raises="ObservationError")
    add("duplicate_JSON_key",replacements=[(0,first_raw.replace(b'{',b'{"schema_version":1,',1))],raises="ObservationError")
    add("nonfinite_JSON",replacements=[(0,first_raw.replace(b'"elapsed_ms":100',b'"elapsed_ms":NaN'))],raises="ObservationError")
    # Late work remains source-reported negative evidence, not a good strict result.
    late = []
    for index,row in enumerate(positive_author.rows):
        value=copy.deepcopy(row); value["elapsed_ms"] += 117001
        if value["event"] == "child_normal_completion": value["body"]["elapsed_ms"] += 117001
        late.append((index,value))
    add("reported_work_budget_exceeded",replacements=late,strict_reject=True,purpose="Reported late work cannot pass117000 even when other source claims look complete.")
    # Marker-only failure is distinct from an appended completed failure row.
    marker_author = copy.deepcopy(positive_author); marker_author.fail("output_commit_failed",cleanup=False)
    marker_raw = canonical(marker_author.marker)+b"\n"
    marker_only = copy.deepcopy(marker_author.marker)
    marker_only["failure_row_publication"].update(write_attempted=False,return_observed=False,known_bytes=None,sha256=None)
    add("marker_only_after_complete_rows",marker_override=(canonical(marker_only)+b"\n").hex(),classification="complete_negative_consistent",cases=84,strict_reject=True)
    add("terminal_failure_after_complete_rows",appends=[marker_author.rows[-1]],marker_override=marker_raw.hex(),classification="complete_negative_consistent",cases=84,strict_reject=True)
    failure_base=bases[1]; failure_rows=authors[1][1].rows
    after=copy.deepcopy(positive_author.rows[-1]); after.update(row_sequence=len(failure_rows),elapsed_ms=failure_rows[-1]["elapsed_ms"]+1)
    scenarios.append(scenario(failure_base,"completed_row_after_terminal_failure",appends=[after],raises="ObservationError"))
    scenarios.append(scenario(failure_base,"duplicate_terminal_failure",appends=[dict(copy.deepcopy(failure_rows[-1]),row_sequence=len(failure_rows))],raises="ObservationError"))
    mismatched_marker=copy.deepcopy(authors[1][1].marker); mismatched_marker["elapsed_ms"]+=1
    scenarios.append(scenario(failure_base,"failure_identity_sample_mismatch",marker_override=(canonical(mismatched_marker)+b"\n").hex(),raises="ObservationError"))
    add("malformed_marker_veto",marker_override=b'{"authoritative":false,"authoritative":true}\n'.hex(),raises="ObservationError",strict_reject=True,
        purpose="Presence veto remains before malformed marker parsing; these are intentionally NOT valid child marker fields.")
    # Source-state-only unknown release: no backend free is invented after it.
    unknown_release=copy.deepcopy(positive_author.rows[187])
    unknown_release.update(row_sequence=188,event="failure",elapsed_ms=1980)
    s=unknown_release["native_state"]; c=unknown_release["native_call_counters"]
    s["selected_prefix_results_written"]=3; s["model_owned"]=False; s["model_free_attempted"]=True; s["model_release_unknown"]=True
    s["cleanup_failed"]=True; s["exceptions"]=1; s["last_attempt"]="llama_model_free"; s["total_attempted"]+=1
    c["llama_model_free"]["attempted"]=1
    identity=dict(pid=4242,error_class="BridgeError",reason_code="native_ownership_or_cleanup_unknown",elapsed_ms=1980,row_sequence_reserved=188)
    unknown_release["body"]=dict(primary_failure_id=digest(canonical(identity)),error_class="BridgeError",reason_code=identity["reason_code"],diagnostic_file=None,profile_qualification="not_established")
    add("unknown_model_release_no_backend_free",prefix=188,appends=[unknown_release],classification="partial_observation",cases=84,strict_reject=True)
    callback_cases=[dict(id="callback_"+name,trace="complete_positive",action="observe",exception=name,
        positions=["first_callback","middle_callback_of_noop_baseline","final_callback_of_noop_baseline"],
        expected="original_exception_object_propagates_no_result") for name in
        ("UnicodeError","UnicodeDecodeError","UnicodeEncodeError","UnicodeTranslateError","ValueError","JSONDecodeError","RecursionError","TimeoutError","KeyboardInterrupt","SystemExit","custom_BaseException")]
    tracked=[DESIGN,PLAN,CONTEXT,HERE/"UNICODE-OBSERVATIONS-TRACE-FORMAT-v1.json",
        HERE/"UNICODE-OBSERVATIONS-ROOT-TRACE-FIXTURE-SCOPE-v2.json",*paths.values(),CODEC/"unicode_pack_codec_v2.py",
        CONTROL/"unicode_piece_analyzer_v1.py",ORACLE/"strict_utf8_oracle_v1.py"]
    fixture=dict(schema_version=1,status="FROZEN_FICTIONAL_FULL_SOURCE_TRACES_BEFORE_OBSERVATION_VALIDATOR",
        sources=[pin(path) for path in tracked],synthetic_context_sha256=pin(CONTEXT)["sha256"],base_traces=bases,
        scenarios=scenarios,callback_cases=callback_cases,
        source_links=dict(setup="Pinned base event_order.setup_events and exact25vectors",cases="All84 immutable accepted codec profile rows",
            geometry="Independent scalar interval/piece arithmetic corroborated by accepted analyzer",counters="Fictional arithmetic reservations/returns; no export was called",
            traces="Expected classifications authored before any observation validator exists"),
        in_memory_pack=dict(bytes=len(in_memory_pack),sha256=digest(in_memory_pack),persisted=False),
        validator_implemented=False,actual_native_observations=0,SDK_native_payload_operations=0,old_run_operations=0,
        profile_qualified=False,originals_authenticated=False,runtime_authorized=False)
    budget(); raw=canonical(fixture)+b"\n"
    with TARGET.open("xb") as out: out.write(raw)
    freeze=dict(schema_version=1,status="complete_fictional_trace_fixtures_frozen_before_validator_code",fixtures=pin(TARGET),
        author=pin(Path(__file__).resolve()),inputs=fixture["sources"],base_traces=len(bases),scenarios=len(scenarios),callback_families=len(callback_cases),
        positive_rows=191,positive_unique_prefixes=3,positive_class_selectors=positive_author.summary["selectors"],
        elapsed_seconds=time.monotonic()-started,source_original_qualification=False,runtime_pack_file=False,
        observation_validator_implemented=False,SDK_native_payload_operations=0,profile_qualified=False)
    with FREEZE.open("xb") as out: out.write(canonical(freeze)+b"\n")
    print(json.dumps(dict(fixtures=pin(TARGET),freeze=pin(FREEZE),base_traces=len(bases),scenarios=len(scenarios),positive_rows=191)))


if __name__ == "__main__": main()

