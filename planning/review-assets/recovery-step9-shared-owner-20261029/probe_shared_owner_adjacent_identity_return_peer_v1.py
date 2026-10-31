"""Two independent injected-source counterprobes; no original or target I/O."""
import builtins
import dataclasses
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import types

ROOT = Path(__file__).resolve().parent
SOURCES = {
    "shared_owner_v1": "76384e02282b1ce2437b9ff342913297f58ea0858752308724bef912b9e2643b",
    "shared_file_ports_v1": "d80f980c771e11ba0116aa3a1a8e526015ce43cafeacc6cf8bc2890f86b4c900",
    "continue_verification_v1": "7f52397a8293ae133f019ede1da78881814eb547b026768f072a34e4a4cf8eb2",
}


class Clock:
    def __init__(self, now=100):
        self.now = now

    def __call__(self):
        return self.now


class Sink:
    def __init__(self):
        self.operations = []

    def reserve(self, key, ack, end):
        self.operations.append(("reserve", end))
        return ack

    def append(self, raw, ack, end):
        self.operations.append(("append", end))
        return ack

    def publish(self, kind, raw, ack, end):
        self.operations.append((kind, end))
        return ack

    def close_journal(self, ack, end):
        self.operations.append(("journal_close", end))
        return ack


def main():
    names = [name + ".py" for name in SOURCES]
    names += ["SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json",
              "SHARED-OWNER-PUBLIC-OBSERVATION-SCHEMA-v2.json",
              "SHARED-OWNER-ROOT-SOURCE-SCOPE-v1.json", Path(__file__).name]
    raw = {name: (ROOT / name).read_bytes() for name in names}
    pins = {name: dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            for name, data in raw.items()}
    for name, digest in SOURCES.items():
        assert pins[name + ".py"]["sha256"] == digest
    assert pins[names[3]]["sha256"] == "eb5147d200bcc0108b71968d69f6b251c29b56dd52d926a8606504682134d9b8"
    assert pins[names[4]]["sha256"] == "50ee2d7a9285370e6a3f0d18801c43e441b327f7ceac9eb46ebdf0463eff28d6"
    assert pins[names[5]]["sha256"] == "4db8622f185edb1488a0066205b6248f0eb37b539e0806d04d748f277ea8e6ee"
    cohort = json.loads(raw[names[3]])
    payloads = {item["path"]: bytes.fromhex(item["utf8_hex"]) for item in cohort["blobs"]}
    "".encode("utf-16-le")
    trusted = {name: sys.modules[name] for name in ("dataclasses", "hashlib", "json", "math", "types", "struct")}
    loaded = {}
    active, denials = True, []

    def audit(event, arguments):
        if active and (event == "open" or event.startswith(("os.", "socket.", "subprocess.", "ctypes."))):
            denials.append(event)
            raise RuntimeError("peer source I/O denied: " + event)

    def closed_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level or name not in loaded and name not in trusted:
            raise ImportError(name)
        return loaded[name] if name in loaded else trusted[name]

    sys.addaudithook(audit)
    observations = []
    try:
        for name in SOURCES:
            module = types.ModuleType(name)
            module.__builtins__ = dict(vars(builtins), __import__=closed_import)
            sys.modules[name] = module
            loaded[name] = module
            exec(compile(raw[name + ".py"], "<captured peer:" + name + ">", "exec"), module.__dict__)
        S, P, C = (loaded[name] for name in SOURCES)
        specs = tuple(S.FileSpec(item["path"], item["role"], item["bytes"], item["sha256"], True)
                      for item in cohort["blobs"])
        early_paths = tuple(item["path"] for item in cohort["blobs"] if item["phase"] == "early_source")
        by_module = {item["module"]: item["path"] for item in cohort["blobs"] if "module" in item}
        # Cohort module descriptors pair with early blobs in its frozen declared order.
        if not by_module:
            by_module = {item["fullname"]: specs[i].path for i, item in enumerate(cohort["closed_modules"])}
        rules = tuple(S.ModuleRule(item["fullname"], by_module[item["fullname"]], tuple(item["dependencies"]))
                      for item in cohort["closed_modules"])

        class Binding:
            def __init__(self):
                self.calls = []

            def invoke(self, ref, arguments, hooks):
                self.calls.append((ref.api, dict(arguments)))
                api = ref.api
                if api == "CreateFileW":
                    hooks.store_scalar(ref, 501 + ref.file_ref.id)
                elif api == "GetFileType":
                    hooks.store_scalar(ref, 1)
                elif api == "GetFileInformationByHandleEx":
                    hooks.buffer_write(ref, ref.buffer_ref, ref.buffer_generation, struct.pack("<II", 128, 0))
                    hooks.store_scalar(ref, 1)
                elif api == "GetFinalPathNameByHandleW":
                    text = "\\\\?\\" + ref.file_ref.spec.path
                    encoded = (text + "\0").encode("utf-16-le")
                    hooks.buffer_write(ref, ref.buffer_ref, ref.buffer_generation, encoded + bytes(8202 - len(encoded)))
                    hooks.store_scalar(ref, len(text))
                elif api == "GetFileSizeEx":
                    hooks.buffer_write(ref, ref.buffer_ref, ref.buffer_generation, struct.pack("<q", ref.file_ref.spec.size))
                    hooks.store_scalar(ref, 1)
                elif api == "ReadFile":
                    data = payloads[ref.file_ref.spec.path]
                    assert len(data) == arguments["requested"]
                    hooks.buffer_write(ref, ref.buffer_ref, ref.buffer_generation, data)
                    hooks.store_scalar(ref, 1)
                    hooks.store_count(ref, len(data))
                elif api == "CloseHandle":
                    hooks.store_scalar(ref, 1)
                else:
                    raise AssertionError(api)

        def create(now=100, compiler=None):
            clock, sink, binding = Clock(now), Sink(), Binding()
            if compiler is None:
                def compiler(name, captured, resolver):
                    assert captured == payloads[by_module[name]]
                    return types.SimpleNamespace(name=name)
            def setup(owner):
                owner.bind_ports(P.FilePortView(owner, binding), sink)
                owner.bind_test_compiler(compiler)
                return owner
            return S.start_injected(clock, setup), clock, sink, binding

        def prepare(owner):
            owner.admit_plan(specs, early_paths, rules)
            owner.reserve_output("peer-fictional")
            owner.capture_early()
            return owner.issue_continuation().claim()

        def finish(owner, continuation):
            handlers = tuple((lambda context, stage=stage: C.TestObservation(
                context, stage, "consistent", (specs[0].path,))) for stage in S.CHECKS)
            factories = C.test_factories(owner, lambda: C.TestAuthority(owner, specs, S.CHECKS),
                                        lambda: C.TestCheckerPorts(owner, S.CHECKS, handlers))
            return C.continue_once(continuation, C.Request("peer-fictional", specs), *factories)

        # Ordinary assignment only: no private-slot/object.__setattr__ mutation.
        owner, clock, sink, binding = create()
        continuation = prepare(owner)
        owner.load_source("cohort_entry")
        original_origin, original_registry = owner.origin, owner.registry
        other_owner, other_clock, other_sink, other_binding = create(200)
        clock.now = original_origin.work_end
        owner.origin = other_owner.origin
        result = finish(owner, continuation).to_dict()
        observations.append(dict(
            name="ordinary_owner_origin_rebind",
            reproduced=(result["pure_seam_complete"] is True and owner.origin is other_owner.origin),
            original_start=original_origin.start, original_work_end=original_origin.work_end,
            original_hard_end=original_origin.hard_end, original_clock_now=clock.now,
            replacement_start=owner.origin.start, replacement_work_end=owner.origin.work_end,
            replacement_hard_end=owner.origin.hard_end,
            continuation_still_same_owner=continuation.owner is owner,
            registry_still_same_object=owner.registry is original_registry,
            result_status=result["status"], pure_seam_complete=result["pure_seam_complete"],
            final_report_origin=result["origin"], original_dispatches=len(binding.calls),
            other_owner_original_dispatches=len(other_binding.calls),
            other_owner_output_operations=len(other_sink.operations)))

        holder = {}
        compiler_values = []
        def late_compiler(name, captured, resolver):
            assert captured == payloads[by_module[name]]
            value = types.SimpleNamespace(name=name)
            compiler_values.append(value)
            holder["clock"].now = 395
            return value
        owner, clock, sink, binding = create(compiler=late_compiler)
        holder["clock"] = clock
        prepare(owner)
        caught = None
        try:
            owner.load_source("cohort_entry")
        except BaseException as error:
            caught = error
        data = owner.snapshot().to_dict()
        record = data["loader"]["records"][0]
        observations.append(dict(
            name="known_late_compiler_return_projection",
            reproduced=(len(compiler_values) == 1 and record["return_observed"] is True
                        and record["accepted"] is False and data["loader"]["returned"] == []),
            actual_compiler_returns=len(compiler_values), compile_record=record,
            loader_attempted=data["loader"]["attempted"], loader_returned=data["loader"]["returned"],
            error_class=type(caught).__name__, refusal_code=getattr(caught, "code", None),
            original_error_latched=owner.primary is caught,
            compiled_value_cached="cohort_entry" in owner.loader.loaded,
            pure_seam_complete=data["pure_seam_complete"]))
        owner.finalize()
    finally:
        active = False
    output = dict(schema_version=1, status="REPRODUCED_SOURCE_COUNTEREXAMPLES" if all(
        item["reproduced"] for item in observations) and not denials else "REVIEW_REQUIRED",
        scope="two_finite_source_contract_probes_only", inputs=pins, observations=observations,
        denied_operation_attempts=denials, toy_helper_execution=0, actual_API_calls=0,
        original_or_payload_operations=0, fixtures_or_expected_outcomes_read=0,
        production_owner_bound=False, runtime_authorized=False, profile_qualified=False,
        verification_complete=False)
    destination = ROOT / "SHARED-OWNER-ADJACENT-IDENTITY-RETURN-BEFORE-v1.json"
    with destination.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(output, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    encoded = destination.read_bytes()
    print(json.dumps(dict(path=str(destination), bytes=len(encoded), sha256=hashlib.sha256(encoded).hexdigest(),
                          status=output["status"], observations=observations), sort_keys=True))


if __name__ == "__main__":
    main()
