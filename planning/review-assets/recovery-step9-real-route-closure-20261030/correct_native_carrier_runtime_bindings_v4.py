"""Correct an unexecuted lexical-binding defect and check Python symbol tables."""
import hashlib
import json
from pathlib import Path
import symtable

base=Path(__file__).resolve().parent
prior=base/"run_native_carrier_fake_tests_v3.py";old=prior.read_bytes()
if hashlib.sha256(old).hexdigest()!="d4dd3d59e701d710d82db986851527cb3e12420b9f53a724a13675fb2bbc6c64":raise ValueError("Unchanged runtimeV3")
text=old.decode()
before='    started=time.monotonic();events=[];previous="0"*64;commands=[]\n'
after=before+'    journal_complete=True;journal_acknowledged_events=0\n'
if text.count(before)!=1:raise ValueError("Unique enclosing journal bindings")
text=text.replace(before,after)
output=base/"run_native_carrier_fake_tests_v4.py";raw=text.encode()
symtable.symtable(text,str(output),"exec")
with output.open("xb")as stream:stream.write(raw)
record=dict(schema_version=1,status="NAMED_LEXICAL_BINDING_CORRECTION_NO_IMAGE_EXECUTION",
    before=dict(path=str(prior),bytes=len(old),sha256=hashlib.sha256(old).hexdigest()),
    after=dict(path=str(output),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
    finding="OS independent static review:V3emit declared two nonlocals without enclosing assignments; Root's initial string replacement did not match the combined initialization line. AST parsing alone did not check lexical bindings.",
    correction="Assert unique actual line, initialize journal_complete and acknowledged-event count before emitter, run symbol-table lexical validation without import/execution. Everything else unchanged; firstV3 preserved.",
    lexical_check="PASS",actual_image_dispatches=0)
with(base/"NATIVE-CARRIER-RUNTIME-BINDINGS-CORRECTION-v4.json").open("x",encoding="utf-8")as stream:
    json.dump(record,stream,indent=2);stream.write("\n")
print(json.dumps(record["after"]))
