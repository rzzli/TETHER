"""Pinned one-shot offline token quotation and read-only anchored replay.

No backend, generation, server, automatic retry or StudySession policy change.
Asset sharing locks protect approved ordinary reads; they are not a sandbox.
"""

from __future__ import annotations

import ast
from collections.abc import Mapping
import hashlib
import os
from pathlib import Path
import re
import subprocess
import threading
import time

from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal
from tether_engine.serde import ContractError, canonical, fingerprint, freeze, parse_json
from .baseline_smoke import _prepare_parent
from .proofs import _no_links, capture_package_proof, verify_package_proof
from .stable_read import (
    checked_path,
    deadline_check,
    hash_file,
    read_file,
    stable_files,
)

RESOURCE = "resources/tokenizer-assets-v1.json"
RESOURCE_SHA256 = "7b1389cbde8166c5ba97089e50d297e3e787bfe6164dde5a668c2418c97537f8"
REQUIRED_RESOURCES = (RESOURCE,)
MAX_STREAM_BYTES = 2 * 1024 * 1024
MAX_PROMPT_BYTES = 32768
MAX_COUNT = 16384
POLICY = freeze(
    dict(
        schema_version=1,
        parser="llama-tokenize-ids-count-v1",
        preprocessing="exact_utf8_no_escape_no_bos_parse_special_v1",
        max_prompt_utf8_bytes=MAX_PROMPT_BYTES,
        max_stdout_bytes=MAX_STREAM_BYTES,
        max_stderr_bytes=MAX_STREAM_BYTES,
        max_child_seconds=30,
        max_preparation_seconds=300,
        token_margin=32,
        generation_calls=0,
        server_startups=0,
        provider_spend_usd=0,
        network_adapter=False,
        retries=0,
        trust_limits=(
            "OS and system DLLs",
            "directory additions are not sandboxed",
            "no hostile same-user/privileged actor isolation",
            "no CPU execution attestation",
        ),
    )
)


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _resource():
    payload = (Path(__file__).parent / RESOURCE).read_bytes()
    _need(
        hashlib.sha256(payload).hexdigest() == RESOURCE_SHA256,
        "Tokenizer resource differs",
    )
    return parse_json(payload)


def _bounded_deadline(deadline):
    deadline_check(deadline)
    _need(
        deadline <= time.monotonic() + 300, "Preparation deadline exceeds 300 seconds"
    )


def _argv(root, resource):
    exe = [
        a["relative_path"]
        for a in resource["assets"]
        if a["relative_path"].endswith("/llama-tokenize.exe")
    ]
    shard = [
        a["relative_path"]
        for a in resource["assets"]
        if "00001-of-00003.gguf" in a["relative_path"]
    ]
    _need(len(exe) == len(shard) == 1, "Approved tokenizer/model inventory malformed")
    return [
        str(Path(root).joinpath(*exe[0].split("/"))),
        "--offline",
        "--model",
        str(Path(root).joinpath(*shard[0].split("/"))),
        "--no-escape",
        "--no-bos",
        "--stdin",
        "--ids",
        "--show-count",
    ]


def _spec(resource, model_root):
    return dict(
        schema_version=1,
        kind="approved_offline_tokenizer_spec",
        resource_sha256=RESOURCE_SHA256,
        authority=dict(
            inventory_sha256=resource["inventory_sha256"],
            acquisition_sha256=resource["acquisition_sha256"],
            version=resource["version"],
        ),
        model_root=str(Path(model_root).absolute()),
        assets=resource["assets"],
        argv=_argv(model_root, resource),
        policy=POLICY,
    )


def _validate_spec(spec):
    _need(isinstance(spec, Mapping), "Invalid tokenizer specification")
    try:
        expected = _spec(_resource(), spec["model_root"])
        _need(
            canonical(spec) == canonical(expected),
            "Tokenizer specification/authority differs",
        )
        _need(Path(spec["model_root"]).is_absolute(), "Tokenizer root must be absolute")
        return freeze(expected)
    except (KeyError, TypeError, ValueError) as error:
        raise ContractError("Invalid tokenizer specification") from error


def _asset_paths(spec):
    return [
        checked_path(spec["model_root"], a["relative_path"]) for a in spec["assets"]
    ]


def _inventory(spec):
    runtime = Path(spec["argv"][0]).parent
    _no_links(runtime)
    expected = {
        Path(spec["model_root"]).joinpath(*a["relative_path"].split("/"))
        for a in spec["assets"]
        if a["relative_path"].lower().endswith(".dll")
    }
    actual = {p.absolute() for p in runtime.iterdir() if p.suffix.casefold() == ".dll"}
    _need(actual == expected, "Extra or missing runtime DLL")


def _verify_assets(spec, deadline):
    _inventory(spec)
    for asset, path in zip(spec["assets"], _asset_paths(spec)):
        actual = hash_file(path, deadline)
        _need(
            actual["sha256"] == asset["sha256"] and actual["bytes"] == asset["bytes"],
            "Approved tokenizer asset differs: " + asset["relative_path"],
        )
    _inventory(spec)


def prepare_tokenizer_spec(authority, roots, *, deadline):
    """Authenticate fixed R05 proof files and all approved assets, without child IO.

    authority has inventory/acquisition root_id+relative_path locators. roots maps
    those explicit approved root IDs, including 'model', to physical directories.
    The accepted proof hashes and exact asset list come from the packaged resource.
    """
    _bounded_deadline(deadline)
    _need(
        isinstance(authority, Mapping)
        and set(authority) == {"inventory", "acquisition"}
        and isinstance(roots, Mapping)
        and "model" in roots,
        "Explicit fixed tokenizer authority required",
    )
    _need(
        Path(roots["model"]).is_absolute()
        and not Path(roots["model"]).drive.startswith("\\\\"),
        "Tokenizer model root must be an absolute local directory",
    )
    resource, paths = _resource(), []
    for name in ("inventory", "acquisition"):
        locator = authority[name]
        _need(
            isinstance(locator, Mapping)
            and set(locator) == {"root_id", "relative_path"}
            and locator["root_id"] in roots,
            "Invalid tokenizer authority locator",
        )
        paths.append(checked_path(roots[locator["root_id"]], locator["relative_path"]))
    spec = _spec(resource, roots["model"])
    assets = _asset_paths(spec)
    with stable_files([*paths, *assets], deadline=deadline):
        for name, path in zip(("inventory", "acquisition"), paths):
            actual = hash_file(path, deadline)
            _need(
                actual["sha256"] == resource[name + "_sha256"],
                "R05 tokenizer authority hash differs",
            )
        _verify_assets(spec, deadline)
    return freeze(spec)


def parse_token_trace(stdout):
    """Only the pinned CLI's complete ID list plus exact count line is accepted."""
    _need(
        isinstance(stdout, bytes) and len(stdout) <= MAX_STREAM_BYTES,
        "Invalid token trace bytes",
    )
    try:
        text = stdout.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContractError("Token trace is not UTF8") from error
    match = re.fullmatch(
        r"\s*(\[[\d, \r\n]*\])\s*Total number of tokens:\s*(\d+)\s*", text
    )
    _need(match is not None, "Malformed or incomplete token trace")
    try:
        ids = ast.literal_eval(match[1])
        reported_count = int(match[2])
    except (SyntaxError, ValueError, TypeError, RecursionError) as error:
        raise ContractError("Malformed tokenizer ID list") from error
    _need(
        isinstance(ids, list)
        and len(ids) <= MAX_COUNT
        and all(type(x) is int and 0 <= x <= 2147483647 for x in ids)
        and reported_count == len(ids),
        "Tokenizer ID/count mismatch",
    )
    return len(ids)


def _environment():
    # Small explicit loader environment. No inherited PATH, model overrides or
    # credentials. The Windows loader/system files remain an OS trust dependency.
    env = {
        name: os.environ[name]
        for name in ("SystemRoot", "WINDIR", "TEMP", "TMP")
        if name in os.environ
    }
    if os.name == "nt":
        system = Path(env.get("SystemRoot", r"C:\Windows")) / "System32"
        env["PATH"] = str(system)
    env["LLAMA_ARG_OFFLINE"] = "1"
    return env


def _run_child(
    argv, prompt, deadline, output, journal, *, process_factory=subprocess.Popen
):
    """Bound all three pipes concurrently; clean up only the retained child handle."""
    deadline_check(deadline)
    child_deadline = min(deadline, time.monotonic() + 30)
    child = None
    streams = {"stdout": bytearray(), "stderr": bytearray()}
    faults, overflow, threads = [], threading.Event(), []
    primary = None
    record = dict(started=False, pid=None, exit_code=None, stdin_bytes_written=0)

    def drain(name, stream):
        try:
            while True:
                block = stream.read(65536)
                if not block:
                    break
                remaining = MAX_STREAM_BYTES - len(streams[name])
                streams[name].extend(block[:remaining])
                if len(block) > remaining:
                    overflow.set()
                    break
        except BaseException as error:
            faults.append(error)

    def feed(stream):
        try:
            view = memoryview(prompt)
            while view:
                written = stream.write(view)
                if not written:
                    raise OSError("Tokenizer stdin write failed")
                record["stdin_bytes_written"] += written
                view = view[written:]
            stream.close()
        except BaseException as error:
            faults.append(error)

    started = time.monotonic()
    try:
        child = process_factory(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            cwd=Path(argv[0]).parent,
            env=_environment(),
            bufsize=0,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if os.name == "nt"
            else 0,
        )
        record.update(started=True, pid=child.pid)
        journal.append("tokenizer_started", pid=child.pid)
        deadline_check(child_deadline)
        for target, args in (
            (drain, ("stdout", child.stdout)),
            (drain, ("stderr", child.stderr)),
            (feed, (child.stdin,)),
        ):
            thread = threading.Thread(target=target, args=args, daemon=True)
            threads.append(thread)
            thread.start()
        while True:
            deadline_check(child_deadline)
            _need(not overflow.is_set(), "Tokenizer stream exceeds 2 MiB")
            if faults:
                raise faults[0]
            status = child.poll()
            if status is not None and all(not thread.is_alive() for thread in threads):
                _need(not overflow.is_set(), "Tokenizer stream exceeds 2 MiB")
                if faults:
                    raise faults[0]
                record["exit_code"] = status
                break
            time.sleep(min(0.01, max(0, child_deadline - time.monotonic())))
        _need(
            record["exit_code"] == 0 and record["stdin_bytes_written"] == len(prompt),
            "Tokenizer exited incompletely or unsuccessfully",
        )
    except BaseException as error:
        primary = error
    finally:
        if child is not None:
            running = True
            try:
                running = child.poll() is None
            except BaseException as error:
                if primary is None:
                    primary = error
                else:
                    primary.add_note("Tokenizer cleanup poll: " + type(error).__name__)
            try:
                if running:
                    child.kill()
                record["exit_code"] = child.wait(timeout=5)
            except BaseException as error:
                if primary is None:
                    primary = error
                else:
                    primary.add_note("Tokenizer child cleanup: " + type(error).__name__)
            for stream in (child.stdin, child.stdout, child.stderr):
                try:
                    stream.close()
                except BaseException as error:
                    if primary is None:
                        primary = error
                    else:
                        primary.add_note(
                            "Tokenizer pipe close: " + type(error).__name__
                        )
            for thread in threads:
                thread.join(timeout=1)
            if any(thread.is_alive() for thread in threads):
                error = ContractError("Tokenizer pipe worker failed to stop")
                if primary is None:
                    primary = error
                else:
                    primary.add_note(str(error))
            if primary is None and overflow.is_set():
                primary = ContractError("Tokenizer stream exceeds 2 MiB")
            if primary is None and faults:
                primary = faults[0]
        elapsed = None
        try:
            elapsed = time.monotonic() - started
        except BaseException as error:
            record["timing_error_class"] = type(error).__name__
            if primary is None:
                primary = error
            else:
                primary.add_note("Tokenizer cleanup clock: " + type(error).__name__)
        record.update(
            elapsed_seconds=elapsed,
            stdout_bytes=len(streams["stdout"]),
            stderr_bytes=len(streams["stderr"]),
            overflow=overflow.is_set(),
        )
        for name in ("stdout", "stderr"):
            try:
                publish_bytes(output / (name + ".bin"), bytes(streams[name]))
            except BaseException as error:
                if primary is None:
                    primary = error
                else:
                    primary.add_note(
                        "Tokenizer stream retention: " + type(error).__name__
                    )
        try:
            publish_bytes(output / "child.json", canonical(record))
        except BaseException as error:
            if primary is None:
                primary = error
            else:
                primary.add_note("Tokenizer child record: " + type(error).__name__)
    if primary is not None:
        raise primary
    return record


def _reserve(output):
    root = Path(output).absolute()
    _prepare_parent(root.parent)
    _no_links(root.parent)
    return root, RunJournal(root, kind="build")


def _member_hashes(root, deadline):
    result = {}
    for path in sorted(root.iterdir()):
        _no_links(path)
        _need(path.is_file(), "Unexpected token preparation member")
        if path.name != "receipt.json":
            result[path.name] = hash_file(path, deadline)
    return result


def tokenize_prompt(prompt, spec, deadline, output, *, payload_sha256=None):
    """Execute one approved tokenizer once and return an externally retainable anchor.

    payload_sha256 separately binds a finalized HTTP/schema envelope; it is not
    included in tokenizer stdin and never changes the prompt-only token count.
    """
    _bounded_deadline(deadline)
    _need(isinstance(prompt, str), "Prompt must be Unicode text")
    raw = prompt.encode("utf-8")
    _need(len(raw) <= MAX_PROMPT_BYTES, "Prompt exceeds tokenizer byte safety cap")
    _need(
        payload_sha256 is None
        or isinstance(payload_sha256, str)
        and re.fullmatch("[0-9a-f]{64}", payload_sha256),
        "Invalid payload binding",
    )
    spec = _validate_spec(spec)
    root, journal = _reserve(output)
    stage = "reservation"
    started = time.monotonic()
    try:
        publish_bytes(root / "spec.json", canonical(spec))
        publish_bytes(root / "prompt.bin", raw)
        package = capture_package_proof(
            {RESOURCE: "study/" + RESOURCE}, REQUIRED_RESOURCES
        )
        publish_bytes(root / "package-proof.json", canonical(package))
        stage = "asset_verification"
        journal.append("build_stage", stage=stage)
        with stable_files(_asset_paths(spec), deadline=deadline):
            _verify_assets(spec, deadline)
            stage = "tokenizer_child"
            journal.append("build_stage", stage=stage)
            child = _run_child(list(spec["argv"]), raw, deadline, root, journal)
            stage = "trace_validation"
            journal.append("build_stage", stage=stage)
            stdout = read_file(root / "stdout.bin", deadline, MAX_STREAM_BYTES)
            count = parse_token_trace(stdout)
            _verify_assets(spec, deadline)
        quote = dict(
            schema_version=1,
            kind="offline_cli_token_quote",
            prompt_sha256=hashlib.sha256(raw).hexdigest(),
            prompt_utf8_bytes=len(raw),
            spec_sha256=fingerprint(spec),
            payload_sha256=payload_sha256,
            tokenization_key=fingerprint(
                dict(
                    prompt_sha256=hashlib.sha256(raw).hexdigest(),
                    spec_sha256=fingerprint(spec),
                    implementation_sha256=fingerprint(package),
                    parser=POLICY["parser"],
                    preprocessing=POLICY["preprocessing"],
                )
            ),
            token_count=count,
            input_reservation=count + 32,
            count_basis="anchored_pinned_cli_trace_not_generation_usage",
            generation_calls=0,
            model_usage_tokens=0,
            provider_spend_usd=0,
            vocab_upper_bound="not_independently_qualified",
            child=child,
            elapsed_seconds=time.monotonic() - started,
        )
        publish_bytes(root / "quote.json", canonical(quote))
        journal.append("build_stage", stage="complete", status="passed")
        journal.close()
        deadline_check(deadline)
        receipt = dict(
            schema_version=1,
            kind="offline_tokenization_receipt",
            files=_member_hashes(root, deadline),
            quote_sha256=fingerprint(quote),
            spec_sha256=fingerprint(spec),
            prompt_sha256=quote["prompt_sha256"],
        )
        receipt_raw = canonical(receipt)
        deadline_check(deadline)
        publish_bytes(root / "receipt.json", receipt_raw)
        deadline_check(deadline)
        return freeze(
            dict(receipt_sha256=hashlib.sha256(receipt_raw).hexdigest(), quote=quote)
        )
    except BaseException as error:
        try:
            journal.fail(error, stage)
        except BaseException as secondary:
            error.add_note("Token journal retention: " + type(secondary).__name__)
        try:
            publish_bytes(
                root / "failure.json",
                canonical(
                    dict(
                        schema_version=1,
                        stage=stage,
                        error_class=type(error).__name__,
                        status="interrupted"
                        if isinstance(error, KeyboardInterrupt)
                        else "failed",
                        generation_calls=0,
                        recovery="inspect only; replacement requires a new output directory",
                    )
                ),
            )
        except BaseException as secondary:
            error.add_note("Token failure retention: " + type(secondary).__name__)
        raise
    finally:
        journal.close()


def verify_tokenization(
    path,
    receipt_sha256,
    expected_prompt_sha256,
    expected_spec_sha256,
    *,
    expected_payload_sha256=None,
    deadline=None,
):
    """Verify an externally anchored quote; never open model assets or spawn a child."""
    root = Path(path).absolute()
    deadline = time.monotonic() + 300 if deadline is None else deadline
    _bounded_deadline(deadline)
    _no_links(root)
    for value in (receipt_sha256, expected_prompt_sha256, expected_spec_sha256):
        _need(
            isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value),
            "External token proof anchor required",
        )
    raw = read_file(root / "receipt.json", deadline, MAX_STREAM_BYTES)
    _need(
        hashlib.sha256(raw).hexdigest() == receipt_sha256,
        "Token receipt anchor differs",
    )
    receipt = parse_json(raw)
    _need(
        set(receipt)
        == {
            "schema_version",
            "kind",
            "files",
            "quote_sha256",
            "spec_sha256",
            "prompt_sha256",
        }
        and receipt["schema_version"] == 1
        and receipt["kind"] == "offline_tokenization_receipt",
        "Invalid token receipt",
    )
    required = {
        "spec.json",
        "prompt.bin",
        "package-proof.json",
        "journal.jsonl",
        "stdout.bin",
        "stderr.bin",
        "child.json",
        "quote.json",
    }
    _need(
        set(receipt["files"]) == required
        and {p.name for p in root.iterdir()} == required | {"receipt.json"},
        "Token member inventory differs",
    )
    _need(
        canonical(_member_hashes(root, deadline)) == canonical(receipt["files"]),
        "Token member bytes differ",
    )

    def member(name, bound=MAX_STREAM_BYTES):
        data = read_file(root / name, deadline, bound)
        _need(
            canonical(dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)))
            == canonical(receipt["files"][name]),
            "Decoded token member differs from anchored bytes",
        )
        return data

    spec = _validate_spec(parse_json(member("spec.json")))
    prompt = member("prompt.bin", MAX_PROMPT_BYTES)
    _need(
        hashlib.sha256(prompt).hexdigest()
        == expected_prompt_sha256
        == receipt["prompt_sha256"]
        and fingerprint(spec) == expected_spec_sha256 == receipt["spec_sha256"],
        "Token prompt/spec binding differs",
    )
    try:
        prompt.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ContractError("Archived prompt is not exact UTF8") from error
    package = parse_json(member("package-proof.json"))
    _need(
        isinstance(package.get("resources"), Mapping)
        and set(package["resources"]) == set(REQUIRED_RESOURCES)
        and package["resources"][RESOURCE].get("relative_path") == "study/" + RESOURCE,
        "Token package resource path differs",
    )
    verify_package_proof(package, required_resources=REQUIRED_RESOURCES)
    stdout = member("stdout.bin")
    count = parse_token_trace(stdout)
    quote = parse_json(member("quote.json"))
    child = parse_json(member("child.json"))
    _need(
        set(quote)
        == {
            "schema_version",
            "kind",
            "prompt_sha256",
            "prompt_utf8_bytes",
            "spec_sha256",
            "payload_sha256",
            "tokenization_key",
            "token_count",
            "input_reservation",
            "count_basis",
            "generation_calls",
            "model_usage_tokens",
            "provider_spend_usd",
            "vocab_upper_bound",
            "child",
            "elapsed_seconds",
        },
        "Invalid token quote fields",
    )
    _need(
        quote["schema_version"] == 1
        and quote["kind"] == "offline_cli_token_quote"
        and quote["prompt_sha256"] == expected_prompt_sha256
        and quote["spec_sha256"] == expected_spec_sha256
        and quote["payload_sha256"] == expected_payload_sha256
        and quote["prompt_utf8_bytes"] == len(prompt)
        and quote["tokenization_key"]
        == fingerprint(
            dict(
                prompt_sha256=expected_prompt_sha256,
                spec_sha256=expected_spec_sha256,
                implementation_sha256=fingerprint(package),
                parser=POLICY["parser"],
                preprocessing=POLICY["preprocessing"],
            )
        )
        and type(quote["token_count"]) is int
        and quote["token_count"] == count
        and quote["input_reservation"] == count + 32
        and type(quote["generation_calls"]) is int
        and quote["generation_calls"] == 0
        and type(quote["model_usage_tokens"]) is int
        and quote["model_usage_tokens"] == 0
        and type(quote["provider_spend_usd"]) in (int, float)
        and quote["provider_spend_usd"] == 0
        and quote["count_basis"] == "anchored_pinned_cli_trace_not_generation_usage"
        and quote["vocab_upper_bound"] == "not_independently_qualified"
        and quote["child"] == child
        and fingerprint(quote) == receipt["quote_sha256"],
        "Token quote semantics differ",
    )
    journal_raw = member("journal.jsonl")
    _need(journal_raw.endswith(b"\n"), "Incomplete token journal")
    events, previous = [], None
    for line in journal_raw.splitlines():
        deadline_check(deadline)
        event = parse_json(line)
        _need(
            isinstance(event, dict)
            and set(event)
            == {"sequence", "event", "details", "previous_sha256", "sha256"},
            "Invalid token journal envelope",
        )
        digest = event.pop("sha256")
        _need(
            type(event["sequence"]) is int
            and event["sequence"] == len(events)
            and event["previous_sha256"] == previous
            and fingerprint(event) == digest,
            "Token journal hash-chain differs",
        )
        event["sha256"] = digest
        events.append(event)
        previous = digest
    _need(
        [e["event"] for e in events]
        == [
            "build_reserved",
            "build_stage",
            "build_stage",
            "tokenizer_started",
            "build_stage",
            "build_stage",
        ]
        and [e["details"].get("stage") for e in events if e["event"] == "build_stage"]
        == ["asset_verification", "tokenizer_child", "trace_validation", "complete"]
        and events[-1]["details"].get("status") == "passed",
        "Token journal ordering differs",
    )
    _need(
        set(child)
        == {
            "started",
            "pid",
            "exit_code",
            "stdin_bytes_written",
            "elapsed_seconds",
            "stdout_bytes",
            "stderr_bytes",
            "overflow",
        }
        and child["started"] is True
        and type(child["pid"]) is int
        and child["pid"] > 0
        and events[3]["details"] == {"pid": child["pid"]}
        and type(child["exit_code"]) is int
        and child["exit_code"] == 0
        and child["overflow"] is False
        and type(child["stdin_bytes_written"]) is int
        and child["stdin_bytes_written"] == len(prompt)
        and type(child["stdout_bytes"]) is int
        and child["stdout_bytes"] == len(stdout)
        and type(child["stderr_bytes"]) is int
        and child["stderr_bytes"] == receipt["files"]["stderr.bin"]["bytes"]
        and type(child["elapsed_seconds"]) in (int, float)
        and 0 <= child["elapsed_seconds"] <= 30
        and type(quote["elapsed_seconds"]) in (int, float)
        and child["elapsed_seconds"] <= quote["elapsed_seconds"] <= 300,
        "Token child accounting differs",
    )
    _need(
        canonical(_member_hashes(root, deadline)) == canonical(receipt["files"]),
        "Token members changed during verification",
    )
    _need(
        hashlib.sha256(
            read_file(root / "receipt.json", deadline, MAX_STREAM_BYTES)
        ).hexdigest()
        == receipt_sha256,
        "Token receipt changed during verification",
    )
    deadline_check(deadline)
    return freeze(quote)
