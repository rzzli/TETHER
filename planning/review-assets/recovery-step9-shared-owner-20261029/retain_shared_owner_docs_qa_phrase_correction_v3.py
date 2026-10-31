"""Preserve a phrase-only metadata check failure and correct that check narrowly."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
old_path = HERE / "check_shared_owner_current_docs_v2.py"
raw = old_path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == "a5611a70d3ed4b555006d731ccb05f9649e45170545ec6ebe6735669a4e518fb"
old = raw.decode("utf-8")
needle = 'assert "[x] Implement/review one canonical shared-owner continuation" in todo'
assert old.count(needle) == 1
replacement = '''completed = [line for line in todo.splitlines() if line.startswith("- [x]") and "canonical shared-owner continuation" in line]
assert len(completed) == 1
assert all(token in completed[0] for token in ("small fictional", "7e0d9484", "13b1e793"))'''
corrected = old.replace(needle, replacement).replace('"SHARED-OWNER-CURRENT-DOCS-QA-v2.json"', '"SHARED-OWNER-CURRENT-DOCS-QA-v3.json"')
failure = {
    "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "PRESERVED_ROOT_METADATA_PHRASE_ASSERTION_FAILURE",
    "checker": old_path.name, "checker_sha256": hashlib.sha256(raw).hexdigest(),
    "assertion": needle,
    "reason": "The completed TODO item says 'the small fictional canonical shared-owner continuation' and includes exact7e0/13b1 scope. The old checker required a different literal prose prefix; no source or documentation semantics failed.",
    "correction": "Identify the one completed canonical-continuation item and still require its small-fictional qualifier plus exact scoped acceptance/peer. All20status, actualpending/human, numeric/chronology/link/acceptance checks stay unchanged.",
    "under_test_or_application_changed": False, "subject_tests_rerun": False,
}
with (HERE / "SHARED-OWNER-CURRENT-DOCS-QA-FIRST-FAILURE-v2.json").open("x", encoding="utf-8", newline="\n") as stream:
    json.dump(failure, stream, indent=2, sort_keys=True)
    stream.write("\n")
destination = HERE / "check_shared_owner_current_docs_v3.py"
with destination.open("x", encoding="utf-8", newline="\n") as stream:
    stream.write(corrected)
print(json.dumps({"status": "metadata_checker_only_corrected", "checker": destination.name, "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))
