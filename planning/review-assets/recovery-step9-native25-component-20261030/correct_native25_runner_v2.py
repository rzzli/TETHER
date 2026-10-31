"""Root metadata/source correction for the first static HOLD; no subject import."""
import hashlib
import json
from pathlib import Path
import symtable

BASE=Path(__file__).resolve().parent
def pin(path):
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(path,value):
    raw=(json.dumps(value,indent=2)+"\n").encode()
    with path.open("xb")as stream:stream.write(raw)
    return pin(path)
prior=BASE/"run_native25_component_v1.py";old=prior.read_bytes()
if hashlib.sha256(old).hexdigest()!="281ca0d14c8d12c025e0a4c2a6b43912d822fc130a9714369d340f757727fcaa":raise ValueError("Unchanged runnerV1")
text=old.decode()
for tag in("ATTEMPT","PROOF","ARTIFACTS","FREEZE","BINDING"):
    prefix="NATIVE25-COMPONENT-"+tag+"-v1"
    if text.count(prefix)!=1:raise ValueError("Unique versioned output: "+tag)
    text=text.replace(prefix,"NATIVE25-COMPONENT-"+tag+"-v2")
before='        self.unexpected_returns = []\n'
if text.count(before)!=2:raise ValueError("Known constructor/start fields")
text=text.replace(before,before+'        self.persistence_progress = None\n',1)
start=text.index('    def persist(self):\n');end=text.index('\n\ndef main():\n',start)
replacement='''    def persist(self):
        result = dict(worlds=[], data=[], snapshots=[], artifacts=self.artifacts,
                      persistence_complete=False, persistence_stage='worlds',
                      known_world_count=len(self.worlds), known_data_count=len(self.data_objects),
                      known_snapshot_references=len(self.snapshots))
        self.persistence_progress = result
        for world in self.worlds:
            number = self.world_ids[id(world)]
            state = world.state if world.state is not None else world.attempt.state
            row = dict(id=number, core_present=state is not None,
                       entry_attempted=world.attempt.attempted, start=clean(world.attempt.start_cell, self.K),
                       first_entry_error=describe(world.attempt.error),
                       original_calls=clean(world.originals.calls, self.K),
                       fixture_completed_delivery=world.originals.delivered,
                       fixture_close_counter=world.originals.close_attempts,
                       output_callbacks=clean(world.output.callbacks, self.K),
                       compiler_callbacks=clean(world.loader.compiler_observations, self.K),
                       cleanup_skipped=bool(world.skip_cleanup),
                       cleanup_blocked_hard_deadline=bool(getattr(world, 'native25_hard_stop', False)),
                       persistence='PENDING_BANK', bank=None)
            result['worlds'].append(row)
            if state is not None:
                row.update(primary=describe(state.primary), secondary=[describe(x) for x in state.secondary],
                           origin=dict(start=clean(state.origin.start, self.K), now=clean(state.origin.now, self.K), latest=clean(state.origin.raw_latest, self.K)),
                           final_snapshot_issued=state._final is not None)
                if state._final is not None and not any(s is state._final for _, s in self.snapshots):
                    self.snapshots.append((world, state._final))
                result['known_snapshot_references'] = len(self.snapshots)
                row['bank'] = self.persist_bank('world-%03d'%number, state, state.registry._calls)
            row['persistence'] = 'COMPLETE'
        result['persistence_stage'] = 'data'
        for value in self.data_objects:
            number = self.data_ids[id(value)]
            row = dict(id=number, scope=value.scope, bank=None, persistence='PENDING_BANK')
            result['data'].append(row)
            row['bank'] = self.persist_bank('data-%03d'%number, value, value._calls)
            row['persistence'] = 'COMPLETE'
        result['persistence_stage'] = 'snapshots'
        seen = set()
        for world, snapshot in self.snapshots:
            if id(snapshot) in seen:
                continue
            seen.add(id(snapshot))
            number = len(result['snapshots'])+1
            retained = dict(raw=None, metadata=None, persistence='PENDING_RAW')
            result['snapshots'].append(retained)
            raw_path = ARTIFACTS / ('snapshot-%03d.raw256.bin'%number)
            raw_hash = hashlib.sha256();size = 0
            with raw_path.open('xb') as stream:
                for row in snapshot._raw_calls:
                    raw = row.raw_row;stream.write(raw);raw_hash.update(raw);size += len(raw)
            rp = dict(path=str(raw_path), bytes=size, sha256=raw_hash.hexdigest(), semantics='ALREADY_COPIED_IMMUTABLE_GENUINE_KERNEL_SNAPSHOT')
            self.artifacts.append(rp);retained['raw'] = rp;retained['persistence'] = 'PENDING_METADATA'
            meta = dict(world=self.world_ids[id(world)], partial=snapshot.partial_capture,
                        copied_bytes=snapshot.copied_native_bytes, raw_rows=snapshot.raw_call_count,
                        capture_error=describe(snapshot.capture_error), data=clean(snapshot.to_dict(), self.K))
            mp = write_json(ARTIFACTS / ('snapshot-%03d.json'%number), meta)
            self.artifacts.append(mp);retained['metadata'] = mp;retained['persistence'] = 'COMPLETE'
        result['persistence_stage'] = 'generated'
        # Copy only already-retained source objects; never regenerate/retry.
        for world in self.worlds:
            state = world.state if world.state is not None else world.attempt.state
            if state is None:
                continue
            for kind, record in state._generated.items():
                raw = record.get('raw')
                if type(raw) is bytes:
                    path = ARTIFACTS / ('world-%03d.generated.%s'%(self.world_ids[id(world)], kind))
                    with path.open('xb') as stream:stream.write(raw)
                    self.artifacts.append(dict(path=str(path), bytes=len(raw), sha256=digest(raw),
                                               semantics='HARNESS_COPY_OF_ACTUAL_SOURCE_GENERATED_OBJECT', eligible=record.get('eligible')))
        result['persistence_complete'] = True;result['persistence_stage'] = 'COMPLETE'
        return result
'''
text=text[:start]+replacement+text[end:]
before='''        try:evidence = ctx.persist()
        except BaseException as error:evidence_error = describe(error)
'''
after='''        try:evidence = ctx.persist()
        except BaseException as error:
            evidence_error = describe(error)
            # Existing harness-owned prefix only: no source call or persistence retry.
            evidence = ctx.persistence_progress
            if evidence is None:
                evidence = dict(artifacts=ctx.artifacts, persistence_complete=False,
                                persistence_stage='NOT_STARTED_OR_UNAVAILABLE')
'''
if text.count(before)!=1:raise ValueError("Unique partial-evidence fallback")
text=text.replace(before,after)
before="    status = 'COMPONENT_FAILURES_WITH_EXPLICIT_DEFERRED' if setup_error or evidence_error or changed or late or counts.get('FAIL') or counts.get('UNKNOWN_DEADLINE') else 'COMPONENT_OBSERVATIONS_PASSED_WITH_EXPLICIT_DEFERRED'"
after="    audit_denials = [] if gate is None else gate.audit_denials\n    status = 'COMPONENT_FAILURES_WITH_EXPLICIT_DEFERRED' if setup_error or evidence_error or changed or late or audit_denials or counts.get('FAIL') or counts.get('UNKNOWN_DEADLINE') else 'COMPONENT_OBSERVATIONS_PASSED_WITH_EXPLICIT_DEFERRED'"
if text.count(before)!=1:raise ValueError("Unique audit veto")
text=text.replace(before,after).replace("audit_denials=[] if gate is None else gate.audit_denials,","audit_denials=audit_denials,",1)
before="    return 0 if not setup_error and not evidence_error and not changed and not late and not counts.get('FAIL') and not counts.get('UNKNOWN_DEADLINE') else 1"
if text.count(before)!=1:raise ValueError("Unique return veto")
text=text.replace(before,"    return 0 if status == 'COMPONENT_OBSERVATIONS_PASSED_WITH_EXPLICIT_DEFERRED' else 1")
output=BASE/"run_native25_component_v2.py"
symtable.symtable(text,str(output),"exec")
with output.open("xb")as stream:stream.write(text.encode())
hold=pin(BASE/"NATIVE25-COMPONENT-INDEPENDENT-STATIC-HOLD-v1.json")
delta=write(BASE/"NATIVE25-COMPONENT-RUNNER-DELTA-v2.json",dict(schema_version=1,
    status="ROOT_NAMED_HARNESS_CORRECTION_NOT_EXECUTED",before=pin(prior),after=pin(output),
    first_static_hold=hold,corrections=["R1 audit denials veto both status and return", "R2 incremental harness-owned persistence progress survives first persistence failure without requery/retry"],
    unchanged="All43executable cases/48matrix rows/subjects/inputs/oracles unchanged. No first source outcome has been observed. V1freeze/HOLD retained.",
    subject_runs=0,C_or_native_actions=0,lexical_check="PASS"))
freeze=json.loads((BASE/"NATIVE25-COMPONENT-FREEZE-v1.json").read_text())
freeze["schema_version"]=2;freeze["pins"]["runner"]=pin(output)
freeze["pins"]["successor_preparer"]=pin(Path(__file__).resolve())
freeze["pins"]["prior_static_hold"]=hold;freeze["pins"]["runner_delta"]=delta
freeze["successor_scope"]="Only R1/R2 harness correction and new output names. All subject/case/matrix/input bytes unchanged; source failures remain expected diagnostic outcomes."
freeze_pin=write(BASE/"NATIVE25-COMPONENT-FREEZE-v2.json",freeze)
outline=json.loads((BASE/"NATIVE25-COMPONENT-BINDING-OUTLINE-v1.json").read_text())
outline["schema_version"]=2;outline["future_binding_filename"]="NATIVE25-COMPONENT-BINDING-v2.json"
outline["required_binding"]["freeze"]=freeze_pin
outline["invocation"]="python -I -B run_native25_component_v2.py only after independent exact successor peer and Root binding"
outline["outputs"]=["NATIVE25-COMPONENT-ATTEMPT-v2.json","NATIVE25-COMPONENT-ARTIFACTS-v2","NATIVE25-COMPONENT-PROOF-v2.json"]
outline_pin=write(BASE/"NATIVE25-COMPONENT-BINDING-OUTLINE-v2.json",outline)
print(json.dumps(dict(runner=pin(output),freeze=freeze_pin,outline=outline_pin)))
