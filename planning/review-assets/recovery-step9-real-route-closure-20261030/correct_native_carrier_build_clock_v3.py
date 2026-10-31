"""Debit journal/process-start latency from the same reviewed build clock."""
from pathlib import Path
import hashlib
import json

base=Path(__file__).resolve().parent
prior=base/"build_native_carrier_component_v2.py"
raw=prior.read_bytes()
if hashlib.sha256(raw).hexdigest()!="6f83b18c02a058074bb5b571edf63b7d3bd79f1cbd894d6a2d4371e6d7e1f848":
    raise ValueError("UnchangedV2")
text=raw.decode()
before='''        emit("dispatch_reserved", label=label, argv=argv)
        process = subprocess.Popen'''
after='''        emit("dispatch_reserved", label=label, argv=argv)
        if 60 - (time.monotonic() - start) <= 2:
            raise TimeoutError("Build work deadline before process creation: " + label)
        process = subprocess.Popen'''
if text.count(before)!=1:raise ValueError("Unique precreation check")
text=text.replace(before,after)
before='''            stdout, stderr = process.communicate(timeout=remaining - 2)
            output_complete = True'''
after='''            work_remaining = 60 - (time.monotonic() - start) - 2
            if work_remaining <= 0:
                raise TimeoutError("Build work deadline after process creation: " + label)
            stdout, stderr = process.communicate(timeout=work_remaining)
            output_complete = True'''
if text.count(before)!=1:raise ValueError("Unique communicate budget")
text=text.replace(before,after)
out=base/"build_native_carrier_component_v3.py";new=text.encode()
with out.open("xb")as stream:stream.write(new)
record=dict(schema_version=1,status="NAMED_SAME_CLOCK_PRECISION_CORRECTION_NOT_BUILT_OR_RUN",
    before=dict(path=str(prior),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
    after=dict(path=str(out),bytes=len(new),sha256=hashlib.sha256(new).hexdigest()),
    finding="Independent residual D1: V2's pre-emit/Popen sample could overstate communicate's remaining work time after slow journal/spawn. Final veto prevented late PASS but did not debit that wait precisely.",
    correction="Same original start, fresh precreation guard, and fresh post-Popen work_remaining. If no work time remains after creation, retain the known process and original TimeoutError through existing bounded cleanup. No clock reset or cap change.",
    preservation="V1,V2,reviews and Root3fake regression report unchanged. C source/header/79oracle untouched. No C/compiler/native execution observed.")
with(base/"NATIVE-CARRIER-BUILD-CLOCK-CORRECTION-v3.json").open("x",encoding="utf-8")as stream:
    json.dump(record,stream,indent=2);stream.write("\n")
print(json.dumps(record["after"]))
