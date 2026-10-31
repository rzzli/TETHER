"""Advance only acknowledged journal rows; never append over an unknown tail."""
import ast
import hashlib
import json
from pathlib import Path

base=Path(__file__).resolve().parent
prior=base/"build_native_carrier_component_v5.py";old=prior.read_bytes()
if hashlib.sha256(old).hexdigest()!="a7b50c609af910b9af568b4d07c1fee90669d51b994003ca860b137bc471025e":raise ValueError("UnchangedV5")
text=old.decode().replace('    previous = "0" * 64\n','    previous = "0" * 64\n    journal_complete = True\n    journal_acknowledged_events = 0\n',1)
start=text.index('    def emit(kind, **fields):\n');end=text.index('    def run(label, argv):\n',start)
replacement='''    def emit(kind, **fields):
        nonlocal previous, journal_complete, journal_acknowledged_events
        if not journal_complete:
            raise RuntimeError("JOURNAL_APPEND_STATE_UNKNOWN: no append or chain repair permitted")
        row = dict(sequence=journal_acknowledged_events, previous_sha256=previous,
                   elapsed_seconds=time.monotonic() - start, kind=kind, **fields)
        raw = json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        prepared_hash = digest(raw)
        prepared_count = journal_acknowledged_events + 1
        try:
            with (out / "build-journal.jsonl").open("ab") as stream:
                if stream.write(raw + b"\\n") != len(raw) + 1:
                    raise OSError("Journal append was not completely acknowledged")
        except BaseException:
            journal_complete = False
            raise
        # Successful ordinary append AND close precede acknowledgment.
        previous = prepared_hash
        journal_acknowledged_events = prepared_count
        try:
            events.append(row)
        except BaseException:
            journal_complete = False
            raise

'''
text=text[:start]+replacement+text[end:]
text=text.replace('                  journal_final_hash=previous, commands=results, artifacts=artifacts,',
                  '                  journal_final_hash=previous, journal_complete=journal_complete,\n                  journal_acknowledged_events=journal_acknowledged_events, commands=results, artifacts=artifacts,',1)
output=base/"build_native_carrier_component_v6.py";raw=text.encode()
with output.open("xb")as stream:stream.write(raw)
def run_node(payload):
    main=next(n for n in ast.parse(payload).body if isinstance(n,ast.FunctionDef)and n.name=="main")
    return next(n for n in main.body if isinstance(n,ast.FunctionDef)and n.name=="run")
same=ast.dump(run_node(old),include_attributes=False)==ast.dump(run_node(raw),include_attributes=False)
if not same:raise ValueError("Subprocess function unchanged")
record=dict(schema_version=1,status="NAMED_JOURNAL_ACKNOWLEDGMENT_CORRECTION_NOT_EXECUTED",
    before=dict(path=str(prior),bytes=len(old),sha256=hashlib.sha256(old).hexdigest()),
    after=dict(path=str(output),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),
    finding="Same independentD1 persistence batch: prior emit advanced tip before write/close, allowing an unacknowledged row to appear final and a later append to reuse its sequence against the wrong persisted prefix.",
    correction="Prepare hash/count first; acknowledge only after successful full ordinary write and close. Failed/partial append latches journal_complete=false and stops all subsequent appends; report last acknowledged tip/count separately. No chain repair, retry, flush/durability or process-tree claim.",
    subprocess_function_AST_unchanged=same,activity=dict(C_builds=0,native_runs=0,original_target_reads=0))
with(base/"NATIVE-CARRIER-BUILD-JOURNAL-CORRECTION-v6.json").open("x",encoding="utf-8")as stream:
    json.dump(record,stream,indent=2);stream.write("\n")
print(json.dumps(record["after"]))
