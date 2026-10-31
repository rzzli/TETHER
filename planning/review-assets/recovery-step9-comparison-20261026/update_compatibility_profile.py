"""Record the0.3.2 to0.3.3 initializer-only legacy compatibility delta."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ARCHIVE = ROOT / "data/reference/recovery-r09-verifier-032-20261026"
old = (ARCHIVE / "semantic_dependencies.json").read_bytes()
resource = ROOT / "src/asof/archive/semantic_dependencies.json"
assert resource.read_bytes() == old
old_init = (ARCHIVE / "__init__.py").read_bytes()
new_init = (ROOT / "src/asof/__init__.py").read_bytes()
assert new_init == old_init.replace(b'"0.3.2"', b'"0.3.3"')
profile = json.loads(old)
for name, expected in profile["modules"].items():
    if name != "__init__.py":
        assert hashlib.sha256((ROOT / "src/asof" / name).read_bytes()).hexdigest() == expected
profile["executing_build_profile"] = "recovery-r09-comparison-0.3.3-20261026"
profile["previous_resource_sha256"] = hashlib.sha256(old).hexdigest()
profile["scope"] = "Version-only change from0.3.2 to0.3.3; declared legacy semantic helpers unchanged. New synthetic fixed-evidence study modules are not imported by the compatibility engine."
profile["compatibility_review"] = "planning/review-assets/recovery-step9-comparison-20261026/compatibility-profile-review.md"
profile["modules"]["__init__.py"] = hashlib.sha256(new_init).hexdigest()
resource.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": "initializer_only_delta_recorded_pending_replays", "previous_sha256": hashlib.sha256(old).hexdigest(), "new_sha256": hashlib.sha256(resource.read_bytes()).hexdigest()}))
