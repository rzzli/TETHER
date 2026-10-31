"""Exercise only the Windows publisher in a new, retained D: fixture directory."""

import ast
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
HELPER = HERE / "accept_generation_v5.py"
OUTPUT = ROOT / "data/cache/r09-generation-publication-fixtures-20261028"
REPORT = HERE / "ACCEPTANCE-PUBLICATION-V5-RESULT.json"


def main():
    assert os.name == "nt" and OUTPUT.resolve().is_relative_to(ROOT)
    assert not OUTPUT.exists() and not REPORT.exists()
    OUTPUT.mkdir()
    definitions = [node for node in ast.parse(HELPER.read_text(encoding="utf-8")).body
                   if isinstance(node, ast.FunctionDef)
                   and node.name in {"require", "publish_acceptance"}]
    assert len(definitions) == 2
    namespace = dict(os=os, Path=Path, tempfile=tempfile)
    exec(compile(ast.Module(body=definitions, type_ignores=[]),
                 str(HELPER) + "::publisher_only", "exec"), namespace)
    publish = namespace["publish_acceptance"]
    results = []

    def directory(name):
        value = OUTPUT / name
        value.mkdir()
        namespace["HERE"] = value
        return value

    value = directory("success")
    publish(b'{"fixture":"complete"}\n')
    assert (value / "acceptance.json").read_bytes() == b'{"fixture":"complete"}\n'
    assert not list(value.glob("acceptance-pending-*"))
    results.append(dict(case="successful_same_directory_publication", passed=True))

    value = directory("existing-destination")
    (value / "acceptance.json").write_bytes(b"existing sentinel")
    try:
        publish(b"must never replace")
    except FileExistsError:
        pass
    else:
        raise AssertionError("An existing destination was replaced")
    assert (value / "acceptance.json").read_bytes() == b"existing sentinel"
    assert not list(value.glob("acceptance-pending-*"))
    results.append(dict(case="existing_destination_preserved", passed=True))

    value = directory("two-writers")
    def writer(payload):
        try:
            publish(payload)
            return "published"
        except FileExistsError:
            return "existing_destination"
    payloads = [b'{"writer":1}\n', b'{"writer":2}\n']
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(writer, payloads))
    assert sorted(outcomes) == ["existing_destination", "published"]
    assert (value / "acceptance.json").read_bytes() in payloads
    assert not list(value.glob("acceptance-pending-*"))
    results.append(dict(case="concurrent_writers_exactly_one_complete_winner", passed=True))

    value = directory("fsync-failure")
    with patch.object(os, "fsync", side_effect=OSError("Injected fixture failure")):
        try:
            publish(b"must remain unpublished")
        except OSError as error:
            assert "Injected fixture" in str(error)
        else:
            raise AssertionError("Failed fsync was accepted")
    assert not (value / "acceptance.json").exists()
    assert not list(value.glob("acceptance-pending-*"))
    results.append(dict(case="failed_fsync_never_publishes", passed=True))

    value = directory("non-windows-guard")
    namespace["os"] = SimpleNamespace(name="posix")
    try:
        publish(b"must remain unpublished")
    except RuntimeError as error:
        assert "Windows" in str(error)
    else:
        raise AssertionError("Unsafe cross-platform rename was admitted")
    namespace["os"] = os
    assert not list(value.iterdir())
    results.append(dict(case="non_windows_stops_before_file_creation", passed=True))

    record = dict(schema_version=1, status="passed_five_publication_fixtures",
                  helper_sha256=hashlib.sha256(HELPER.read_bytes()).hexdigest(),
                  fixture_helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  scope="publisher_only_no_acceptance_aggregation_or_runtime_execution",
                  output=str(OUTPUT), cases=results, runtime_model_or_native_calls=0,
                  original_acceptance_exists=(HERE / "acceptance.json").exists())
    assert record["original_acceptance_exists"] is False
    with REPORT.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    print(json.dumps(dict(status=record["status"], tests=len(results),
                          report=str(REPORT))))


if __name__ == "__main__":
    main()
