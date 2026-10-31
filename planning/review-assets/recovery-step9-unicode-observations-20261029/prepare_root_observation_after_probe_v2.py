"""Preserve before vectors and prepare their separately named v2 regression."""
import hashlib
from pathlib import Path

here = Path(__file__).resolve().parent
raw = (here / "probe_root_observation_boundaries_v1.py").read_text(encoding="utf-8")
changes = {
    '"recovery-step9-unicode-observations-20261029/unicode_observations_v1.py", "unicode_observations_v1", "58d6a62fe6a9416c94e5637b615886cecd90bc78ef1559f05f7d1d1ebd6e32c0"':
    '"recovery-step9-unicode-observations-20261029/unicode_observations_v2.py", "unicode_observations_v2", "47c7cc1fc3889e32c5a3ff3efff50425ef208a041a308f5a447872bd788414b6"',
    'observer = modules["unicode_observations_v1"]': 'observer = modules["unicode_observations_v2"]',
    'assert prefix["terminal_negative_seen"] is False': 'assert prefix["terminal_negative_seen"] is True',
    '"observed_terminal_negative_seen": False': '"observed_terminal_negative_seen": True',
    'def delayed_issue(data):': 'def delayed_issue(*args, **kwargs):',
    'result = original_issue(data)': 'result = original_issue(*args, **kwargs)',
    '"TWO_PURE_BOUNDARY_DEFECTS_REPRODUCED"': '"TWO_PURE_BOUNDARY_REGRESSIONS_PASS_ON_V2"',
    'First implementation only; no source byte edits.': 'Corrected implementation; original before vectors retained without source byte edits.',
    '"UNICODE-OBSERVATIONS-ROOT-BOUNDARY-BEFORE-v1.json"': '"UNICODE-OBSERVATIONS-ROOT-BOUNDARY-AFTER-v2.json"',
}
for old, new in changes.items():
    assert raw.count(old) == 1, old
    raw = raw.replace(old, new)
start = raw.index('try:\n    result = observer.observe(bytes.fromhex(base["raw_hex"])')
end = raw.index('\nfinally:\n    observer._issue = original_issue', start)
raw = raw[:start] + '''try:
    try:
        observer.observe(bytes.fromhex(base["raw_hex"]), profile, bindings, check=check)
    except BaseException as error:
        assert expired and error is stop, type(error).__name__
        outcomes.append({"id": "post_result_freeze_callback_present", "passed": True,
            "same_deadline_object_propagated": True, "success_returned": False,
            "callback_calls": calls, "runtime_profile_qualified": False})
    else:
        raise AssertionError("A result was returned after the synthetic finalization deadline")
''' + raw[end:]
raw = raw.replace('"inputs": inputs, "outcomes": outcomes,',
    '"inputs": inputs, "outcomes": outcomes,\n    "original_before_report_sha256": "e6ebbb0fc2c9e237edad11c3d00b85c52e697db139730b0b0401a5d7f98d9282",\n    "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),')
output = here / "probe_root_observation_boundaries_v2.py"
with output.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(raw)
print("Created exact-vector v2 root regression helper; v1 remains unchanged.")
