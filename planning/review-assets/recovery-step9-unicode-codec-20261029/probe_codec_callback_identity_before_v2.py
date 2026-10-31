"""Independent valid-data probe; all new pack bytes remain in memory."""
import hashlib
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent


def main():
    source_path = HERE / "unicode_pack_codec_v1.py"
    source = source_path.read_bytes()
    digest = hashlib.sha256(source).hexdigest()
    assert digest == "c2e579f9a5f0e485d4af1fe5bfeaed75c62debffb5f779391b294d740f1f5b40"
    module = types.ModuleType("codec_callback_identity_before_v2")
    module.__file__ = str(source_path)
    sys.modules[module.__name__] = module
    exec(compile(source, str(source_path), "exec"), module.__dict__)
    wire = ASSETS / "recovery-step9-unicode-wire-20261029"
    control = ASSETS / "recovery-step9-unicode-control-20261029"
    inputs = module.SourceBytes(
        (wire / "UNICODE-WIRE-DESIGN-CONTRACT-v2.json").read_bytes(),
        (wire / "UNICODE-WIRE-FRAMING-CONTRACT-v1.json").read_bytes(),
        (control / "UNICODE-CONTROL-CORPUS-v1.json").read_bytes(),
        (control / "UNICODE-CONTROL-STAGES-v1.json").read_bytes(),
        (control / "UNICODE-CONTROL-CONTRACT-v2.json").read_bytes(),
        (control / "UNICODE-PIECE-ANALYZER-CONTRACT-v1.json").read_bytes(),
    )
    profile = module.make_profile(inputs, check=lambda: None)
    encoded = module.encode(profile, check=lambda: None)
    assert module.decode(encoded, profile, check=lambda: None).bytes == len(encoded)
    failure = UnicodeError("synthetic_check_callback_failure")
    fired = False

    def check():
        nonlocal fired
        frame = sys._getframe(1)
        if not fired and frame.f_code.co_name == "take" and frame.f_locals.get("n") == 9:
            fired = True
            raise failure

    observed = None
    try:
        module.decode(encoded, profile, check=check)
    except BaseException as error:
        observed = error
    report = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {"path": str(source_path), "bytes": len(source), "sha256": digest},
        "status": "REPRODUCED_CALLBACK_EXCEPTION_WRAPPED_AS_DATA_ERROR" if fired and observed is not failure else "NOT_REPRODUCED",
        "callback_fired": fired, "expected_exception_class": type(failure).__name__,
        "observed_exception_class": None if observed is None else type(observed).__name__,
        "original_exception_propagated": observed is failure,
        "original_retained_only_as_cause": observed is not None and observed.__cause__ is failure,
        "data_was_valid_before_callback": True,
        "complete_pack_bytes": len(encoded), "pack_persisted": False,
        "scope": "A callback UnicodeError during a valid ID-field take is caught by the ID decoding handler. This violates generic callback propagation; no runtime/profile qualification is involved.",
        "old_payload_or_native_or_SDK_operations": 0,
    }
    output = HERE / "UNICODE-PACK-CODEC-CALLBACK-BEFORE-v2.json"
    with output.open("xb") as stream:
        stream.write((json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": report["status"], "observed": report["observed_exception_class"],
                      "same_exception": report["original_exception_propagated"],
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
    assert report["status"] == "REPRODUCED_CALLBACK_EXCEPTION_WRAPPED_AS_DATA_ERROR"


if __name__ == "__main__":
    main()
