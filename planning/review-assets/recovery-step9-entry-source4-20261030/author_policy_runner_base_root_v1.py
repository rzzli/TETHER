"""Mechanical trusted-harness copy only; no module import or test execution."""
import ast
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent / 'recovery-step9-entry-contract-tests-20261030' / 'run_entry_contract_suite_v2.py'
NEW = HERE / 'run_entry_policy_suite_v1.py'

raw = OLD.read_bytes()
if hashlib.sha256(raw).hexdigest() != 'cbaa75873d6f5d3fdace3d91f753d18e1bf3f4ed95e7004b195d64bf3865b792':
    raise RuntimeError('accepted retention runner changed')
text = raw.decode('utf-8')
for before, after in (
    ('ENTRY-CONTRACT-SUITE-BINDING-v2', 'ENTRY-E08-SUITE-BINDING-v1'),
    ('ENTRY-CONTRACT-SUITE-ATTEMPT-v2', 'ENTRY-E08-SUITE-ATTEMPT-v1'),
    ('ENTRY-CONTRACT-SUITE-PROOF-v2', 'ENTRY-E08-SUITE-PROOF-v1'),
    ('ENTRY-CONTRACT-SUITE-ARTIFACTS-v2', 'ENTRY-E08-SUITE-ARTIFACTS-v1'),
    ('entry_independent_test_support_v3', 'entry_independent_test_support_v4'),
    ('entry_independent_world_v3', 'entry_independent_world_v4'),
):
    text = text.replace(before, after)
ast.parse(text)
with NEW.open('xb') as stream:
    stream.write(text.encode('utf-8'))
print('Saved mechanical runner base; main/context are unfinished and unbound.')
