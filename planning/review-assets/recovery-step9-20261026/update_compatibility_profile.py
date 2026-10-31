"""Record a reviewed version-only legacy dependency delta, not a pin bypass."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = ROOT / "data/reference/recovery-r07-verifier-031-20261026"
old_bytes = (ARCHIVE / "semantic_dependencies.json").read_bytes()
resource = ROOT / "src/asof/archive/semantic_dependencies.json"
assert resource.read_bytes() == old_bytes
old_init = (ARCHIVE / "__init__.py").read_bytes()
new_init = (ROOT / "src/asof/__init__.py").read_bytes()
assert new_init == old_init.replace(b'"0.3.1"', b'"0.3.2"')
profile = json.loads(old_bytes)
for name, expected in profile["modules"].items():
    if name != "__init__.py":
        assert hashlib.sha256((ROOT / "src/asof" / name).read_bytes()).hexdigest() == expected
profile["executing_build_profile"] = "recovery-r09-0.3.2-20261026"
profile["previous_resource_sha256"] = hashlib.sha256(old_bytes).hexdigest()
profile["scope"] = "Version-only change from0.3.1 to0.3.2; legacy semantic helpers unchanged. New synthetic baseline modules are not imported by this compatibility engine."
profile["compatibility_review"] = "planning/review-assets/recovery-step9-20261026/compatibility-profile-review.md"
profile["modules"]["__init__.py"] = hashlib.sha256(new_init).hexdigest()
resource.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "version_only_profile_recorded_pending_replays",
                  "previous_sha256": hashlib.sha256(old_bytes).hexdigest(),
                  "new_sha256": hashlib.sha256(resource.read_bytes()).hexdigest()}))
