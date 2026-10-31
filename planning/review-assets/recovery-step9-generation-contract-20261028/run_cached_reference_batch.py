"""PREPARED ONLY: one independent schema batch after separate owner approval.

Arguments: exact expected ENVIRONMENT-RECEIPT.json SHA256. The owner must run this
single child under an outer 120-second timeout, retain stdout/stderr and never
restart it automatically. This script imports no AsOf code or native target.
"""
import hashlib
import importlib.abc
from importlib import metadata
import json
import os
from pathlib import Path
import re
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ENV_ROOT = ROOT / "data/cache/r09-jsonschema-reference-environment-20261028"
ENV = ENV_ROOT / "environment"
OUT = ROOT / "data/cache/r09-jsonschema-reference-batch-20261028"
DATA = ROOT / "data/cache/r09-generation-corpus-extension-v1-20261028"
ORIGINAL = ROOT / "data/cache/r09-native-grammar-corpus-20261028/cases.json"
PINS = {
    DATA / "FROZEN-INPUTS.json": "1b80e365e42b28fe237c22fc35e215d1a0410729203a77255fc628309a9da414",
    DATA / "FUTURE-NATIVE-CORPUS-MANIFEST.json": "43aa4b18d3d9c7393198d0eaa93095999d1ef54f0d2757ffe6265c7d95a26e4a",
    DATA / "COMPARISON-RESULTS.json": "95c2c30fa8ef69dca5122e22ce32fe3b636e812d3a8f8f05c685b366e323316a",
    ORIGINAL: "01286d35689c7005ea67fa817c4b4098cecd05c4233c3949e7ec744bc5f5d97a",
}
VERSIONS = {"jsonschema": "4.26.0", "referencing": "0.37.0", "jsonschema-specifications": "2025.9.1",
            "attrs": "26.1.0", "rpds-py": "2026.6.3", "typing-extensions": "4.15.0"}
KEYWORDS = {"additionalProperties", "anyOf", "const", "enum", "items", "maxItems", "maxLength",
            "minItems", "minLength", "pattern", "properties", "required", "type", "uniqueItems"}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(contents):
    return hashlib.sha256(contents).hexdigest()


def read_pinned(path, expected):
    contents = path.read_bytes()
    require(len(contents) <= 4 * 1024 * 1024 and sha(contents) == expected, f"Input pin/cap failed: {path}")
    return contents


def normalized(path):
    return os.path.normcase(os.path.abspath(os.fsdecode(path)))


def under(path, root):
    try:
        return os.path.commonpath([path, normalized(root)]) == normalized(root)
    except ValueError:
        return False


def controls():
    # Fixed prospective Unicode controls, separate from the unchanged167 corpus.
    return [
        ("empty_min0_max0", "", 0, 0, True), ("empty_min1", "", 1, 1, False),
        ("ascii_one", "a", 1, 1, True), ("ascii_two", "aa", 1, 1, False),
        ("astral_one", "😀", 1, 1, True), ("astral_two", "😀😀", 1, 1, False),
        ("combining_pair_max1", "e\u0301", 1, 1, False), ("combining_pair_max2", "e\u0301", 1, 2, True),
        ("combining_900_max1800", "e\u0301" * 900, 1, 1800, True),
        ("combining_901_max1800", "e\u0301" * 901, 1, 1800, False),
        ("precomposed_1800", "é" * 1800, 1, 1800, True),
        ("precomposed_1801", "é" * 1801, 1, 1800, False),
        ("mixed_astral_combining_max3", "😀e\u0301", 1, 3, True),
        ("mixed_astral_combining_max2", "😀e\u0301", 1, 2, False),
        ("combining_900_min1800", "e\u0301" * 900, 1800, 1800, True),
        ("combining_899_min1800", "e\u0301" * 899, 1800, 1800, False),
    ]


def main():
    require(len(sys.argv) == 2 and re.fullmatch(r"[a-f0-9]{64}", sys.argv[1])
            and sys.flags.isolated and Path(sys.prefix).resolve() == ENV.resolve(),
            "Use the new isolated environment and explicit external environment-receipt hash")
    require(not OUT.exists(), "Batch attempt exists; no automatic retry")
    OUT.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    deadline = started + 100
    report = dict(schema_version=1, status="failed_or_incomplete", expected_environment_receipt_sha256=sys.argv[1],
                  helper_sha256=sha(Path(__file__).read_bytes()), cases=[], controls=[], guard_attempts=[],
                  target_native_calls=0, model_calls=0, tokenizer_calls=0, provider_cost_usd=0.0,
                  restart_allowed=False, strict_validator_rerun=False, powershell_rerun=False,
                  native_conformance="unverified", scientific_validation="not_attempted")
    (OUT / "attempt.json").write_text(json.dumps(dict(status="reserved_once_only", helper_sha256=report["helper_sha256"])), encoding="utf-8")
    progress = (OUT / "progress.jsonl").open("x", encoding="utf-8")
    try:
        receipt_path = ENV_ROOT / "ENVIRONMENT-RECEIPT.json"
        receipt = json.loads(read_pinned(receipt_path, sys.argv[1]))
        require(receipt["status"] == "offline_reference_environment_materialized_not_import_qualified", "Environment not materialized")
        require(receipt["copied_files"] == 139 and receipt["copied_bytes"] == 1640116, "Wrong package closure")
        site = ENV / "Lib/site-packages"

        def package_hashes():
            for package in receipt["selected"]:
                for relative, expected in package["files"].items():
                    data = (site / relative).read_bytes()
                    require(len(data) == expected["bytes"] and sha(data) == expected["sha256"], f"Changed package: {relative}")

        package_hashes()
        seed = {str(path): read_pinned(path, expected) for path, expected in PINS.items()}
        frozen = json.loads(seed[str(DATA / "FROZEN-INPUTS.json")])
        future = json.loads(seed[str(DATA / "FUTURE-NATIVE-CORPUS-MANIFEST.json")])
        labels = {row["id"]: row["authored_expectations"]["schema_accepted"]
                  for row in json.loads(seed[str(DATA / "COMPARISON-RESULTS.json")])}
        originals = {row["id"]: row for row in json.loads(seed[str(ORIGINAL)])}
        require(len(originals) == 109 and len(future["cases"]) == len(labels) == 167, "Wrong frozen case counts")
        require(set(labels) == {row["id"] for row in future["cases"]}, "Label/case mismatch")
        input_bytes, schemas, allowed_inputs = {}, {}, set(map(normalized, PINS))
        for variant, assets in future["variants"].items():
            entry = assets["schema.json"]
            path = ROOT / entry["path"]
            require(path.is_relative_to(DATA) and frozen["files"][entry["path"]] == entry["sha256"], "Unapproved schema path")
            schemas[variant] = json.loads(read_pinned(path, entry["sha256"]))
            allowed_inputs.add(normalized(path))
        for row in future["cases"]:
            if row["source"] == "unchanged_original_109":
                original = originals[row["original_corpus_case_id"]]
                contents = original["document_json"].encode("utf-8")
                require(sha(original["schema_json"].encode("utf-8")) == future["variants"][row["variant"]]["schema.json"]["sha256"],
                        "Original case schema differs from the full pinned variant")
            else:
                path = ROOT / row["document_path"]
                require(path.is_relative_to(DATA) and frozen["files"][row["document_path"]] == row["document_sha256"], "Unapproved document path")
                contents = read_pinned(path, row["document_sha256"])
                allowed_inputs.add(normalized(path))
            require(len(contents) == row["document_bytes"] <= 512 * 1024 and sha(contents) == row["document_sha256"], "Original document changed")
            input_bytes[row["id"]] = contents

        def audit(event, args):
            if event in ("socket.__new__", "socket.connect", "socket.getaddrinfo", "subprocess.Popen", "os.system", "ctypes.dlopen"):
                report["guard_attempts"].append(event)
                raise PermissionError("Independent schema batch cannot dispatch or load target libraries")
            if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
                path = normalized(args[0])
                mode = args[1] if len(args) > 1 else None
                flags = args[2] if len(args) > 2 and isinstance(args[2], int) else 0
                writing = bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)) or (isinstance(mode, str) and any(c in mode for c in "wax+"))
                denied = path.startswith("e:") or "\\data\\benchmark\\" in path
                if writing:
                    denied = denied or not under(path, OUT)
                else:
                    denied = denied or not (path in allowed_inputs or path == normalized(receipt_path)
                        or under(path, ENV) or under(path, sys.base_prefix) or path == normalized(__file__))
                if denied:
                    report["guard_attempts"].append(dict(event=event, path=path, writing=writing))
                    raise PermissionError("Only pinned inputs and isolated installed reference engine")

        class NoProject(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split(".")[0] in ("asof", "tools", "planning"):
                    report["guard_attempts"].append(dict(import_name=fullname))
                    raise ImportError("Project runtime cannot act as independent schema reference")

        sys.meta_path.insert(0, NoProject())
        sys.addaudithook(audit)
        require({name: metadata.version(name) for name in VERSIONS} == VERSIONS, "Installed tool versions differ")
        from jsonschema import Draft202012Validator
        import jsonschema
        from referencing import Registry
        from referencing.exceptions import NoSuchResource
        require(Path(jsonschema.__file__).resolve().is_relative_to(ENV), "Reference engine outside isolated environment")
        require(KEYWORDS <= Draft202012Validator.VALIDATORS.keys(), "Missing full-schema keyword implementation")

        def deny_retrieve(uri):
            report["guard_attempts"].append(dict(remote_reference=uri))
            raise NoSuchResource(ref=uri)

        registry = Registry(retrieve=deny_retrieve)
        meta = Draft202012Validator(Draft202012Validator.META_SCHEMA, registry=registry)
        validators = {}
        for variant, schema in schemas.items():
            require(next(meta.iter_errors(schema), None) is None, "Invalid full acceptance schema")
            validators[variant] = Draft202012Validator(schema, registry=registry)
        report["engine_import_abi"] = "import_returned_and_metadata_matched"
        for row in future["cases"]:
            require(time.monotonic() < deadline, "Batch deadline before case")
            duplicate_keys, parse_error, non_scalar = [], None, False
            def pairs(items):
                result = {}
                for key, value in items:
                    if key in result:
                        duplicate_keys.append(key)
                    result[key] = value
                return result
            def scan(value):
                if isinstance(value, str):
                    return any(0xD800 <= ord(c) <= 0xDFFF for c in value)
                if isinstance(value, dict):
                    return any(scan(key) or scan(item) for key, item in value.items())
                if isinstance(value, list):
                    return any(scan(item) for item in value)
                return False
            try:
                instance = json.loads(input_bytes[row["id"]].decode("utf-8"), object_pairs_hook=pairs)
                non_scalar = scan(instance)
                error = next(validators[row["variant"]].iter_errors(instance), None)
                accepted = error is None
            except (ValueError, UnicodeError) as error:
                accepted = False
                parse_error = dict(error_class=type(error).__name__, message=str(error)[:1024])
            expected = labels[row["id"]]
            result = dict(id=row["id"], document_sha256=row["document_sha256"], schema_accepted=accepted,
                expected_schema_accepted=expected, typed_expectation=isinstance(expected, bool),
                matches_expected=(accepted == expected) if isinstance(expected, bool) else None,
                parse_error=parse_error, duplicate_keys=duplicate_keys, non_scalar_strings=non_scalar,
                parser_policy="Python json: duplicate keys last value retained; scalar flags observed without strict post-policy")
            report["cases"].append(result)
            progress.write(json.dumps(result, ensure_ascii=True) + "\n")
            progress.flush()
            require(time.monotonic() < deadline, "Batch deadline after case")
        for name, instance, minimum, maximum, expected in controls():
            require(time.monotonic() < deadline, "Batch deadline before Unicode control")
            schema = dict(type="string", minLength=minimum, maxLength=maximum)
            accepted = Draft202012Validator(schema, registry=registry).is_valid(instance)
            report["controls"].append(dict(id=name, codepoints=len(instance), instance_sha256=sha(instance.encode("utf-8")),
                schema=schema, accepted=accepted, expected=expected, matches_expected=accepted == expected))
        package_hashes()
        for path, expected in PINS.items():
            read_pinned(path, expected)
        typed = [row for row in report["cases"] if row["typed_expectation"]]
        require(len(typed) == 162 and len(report["cases"]) - len(typed) == 5, "Typed/parse-edge case classification changed")
        require(not report["guard_attempts"] and time.monotonic() < deadline, "Guard/deadline failure")
        matched = all(row["matches_expected"] for row in typed) and all(row["matches_expected"] for row in report["controls"])
        report.update(status="passed_reference_schema_expectations" if matched else "reference_expectation_mismatch_stop",
                      typed_schema_cases=len(typed), explicit_parse_edge_cases=5, unicode_controls=len(report["controls"]),
                      elapsed_seconds=time.monotonic() - started)
    except BaseException as error:
        report.update(status="failed_no_automatic_retry", failure=dict(error_class=type(error).__name__, message=str(error)),
                      elapsed_seconds=time.monotonic() - started)
    finally:
        progress.close()
        with (OUT / "REFERENCE-BATCH-RESULT.json").open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, ensure_ascii=True)
            stream.write("\n")
    print(json.dumps({key: report[key] for key in ("status", "elapsed_seconds")}))
    return 0 if report["status"] == "passed_reference_schema_expectations" else 1


if __name__ == "__main__":
    raise SystemExit(main())
