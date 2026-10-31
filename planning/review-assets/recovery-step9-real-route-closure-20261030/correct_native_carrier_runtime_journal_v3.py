"""Apply acknowledged-tip/unknown-tail rules to the never-run runtime helper."""
from pathlib import Path
import hashlib
import json

base=Path(__file__).resolve().parent
prior=base/"run_native_carrier_fake_tests_v2.py";old=prior.read_bytes()
if hashlib.sha256(old).hexdigest()!="92790be7fb9b62328bda0c820a7ab5c567edcf50d945612944fddd7b52bdcd42":raise ValueError("Unchanged runtimeV2")
text=old.decode().replace('    started=time.monotonic();events=[];previous="0"*64\n',
                         '    started=time.monotonic();events=[];previous="0"*64\n    journal_complete=True;journal_acknowledged_events=0\n',1)
start=text.index('    def emit(kind,**fields):\n');end=text.index('    outcome="FAILED";',start)
text=text[:start]+'''    def emit(kind,**fields):
        nonlocal previous,journal_complete,journal_acknowledged_events
        if not journal_complete:
            raise RuntimeError("JOURNAL_APPEND_STATE_UNKNOWN: no chain repair permitted")
        value=dict(sequence=journal_acknowledged_events,previous_sha256=previous,kind=kind,
                   elapsed_seconds=time.monotonic()-started,**fields)
        raw=json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        prepared_hash=sha(raw);prepared_count=journal_acknowledged_events+1
        try:
            with(output/"run-journal.jsonl").open("ab")as stream:
                if stream.write(raw+b"\\n")!=len(raw)+1:
                    raise OSError("Journal append not completely acknowledged")
        except BaseException:
            journal_complete=False
            raise
        previous=prepared_hash;journal_acknowledged_events=prepared_count
        try:events.append(value)
        except BaseException:
            journal_complete=False
            raise
'''+text[end:]
text=text.replace('journal_events=len(events),journal_final_hash=previous,',
                  'journal_events=len(events),journal_final_hash=previous,journal_complete=journal_complete,\n                journal_acknowledged_events=journal_acknowledged_events,',1)
output=base/"run_native_carrier_fake_tests_v3.py";raw=text.encode()
with output.open("xb")as stream:stream.write(raw)
record=dict(schema_version=1,status="ROOT_PREFREEZE_RUNTIME_JOURNAL_CORRECTION_NO_IMAGE_EXECUTION",
    before=dict(path=str(prior),bytes=len(old),sha256=hashlib.sha256(old).hexdigest()),
    after=dict(path=str(output),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
    correction="Same acknowledged-tip/unknown-tail rule as independently cleared buildDriver6. Original runtimeV1/V2 retained. Exact79golden comparison/counters/extracted executor logic unchanged.",
    actual_image_dispatches=0,qualification="Runtime helper still requires static peer and exact separately bound compiled image.")
with(base/"NATIVE-CARRIER-RUNTIME-JOURNAL-CORRECTION-v3.json").open("x",encoding="utf-8")as stream:
    json.dump(record,stream,indent=2);stream.write("\n")
print(json.dumps(record["after"]))
