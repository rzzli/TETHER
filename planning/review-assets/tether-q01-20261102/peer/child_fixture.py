"""Harmless independent child-process fixtures: no model, data or network calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time


def emit_journal(output, accounted):
    output.mkdir(exist_ok=False)
    previous = None
    entries = [
        ("run_reserved", {"fixture": True}),
        ("dispatch", {"attempt_id": "fictional:1", "reserved": {
            "input_tokens": 7, "output_tokens": 11, "cost_usd": 0}}),
    ]
    if accounted:
        entries.append(("attempt_accounted", {"attempt_id": "fictional:1",
            "basis": "adapter_reported", "usage": {
                "input_tokens": 3, "output_tokens": 5, "cost_usd": 0}}))
    with (output / "journal.jsonl").open("xb") as stream:
        for index, (kind, details) in enumerate(entries):
            event = dict(sequence=index, event=kind, details=details,
                         previous_sha256=previous)
            payload = json.dumps(event, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False, allow_nan=False).encode()
            event["sha256"] = previous = hashlib.sha256(payload).hexdigest()
            stream.write(json.dumps(event, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False).encode() + b"\n")
        stream.flush()
        os.fsync(stream.fileno())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode")
    parser.add_argument("--bytes", type=int, default=128)
    parser.add_argument("--marker", type=Path)
    parser.add_argument("--engine-output", type=Path)
    args = parser.parse_args()
    if args.marker:
        with args.marker.open("ab") as marker:
            marker.write(b"dispatch\n")
            marker.flush()
            os.fsync(marker.fileno())
    if args.engine_output:
        emit_journal(args.engine_output, args.mode == "accounted_block")

    if args.mode in ("exact", "overflow"):
        total = args.bytes + int(args.mode == "overflow")
        first = total // 2
        os.write(sys.stdout.fileno(), b"A" * first)
        os.write(sys.stderr.fileno(), b"B" * (total - first))
    elif args.mode in ("block", "accounted_block"):
        time.sleep(10)  # Finite fallback even if the candidate supervisor fails.
    elif args.mode == "trickle":
        for _ in range(200):
            os.write(sys.stdout.fileno(), b"x")
            time.sleep(0.05)
    elif args.mode.startswith("flood"):
        def flood(fd):
            for _ in range(4096):
                os.write(fd, b"X" * 4096)
        if args.mode == "flood_both":
            thread = threading.Thread(target=flood, args=(sys.stderr.fileno(),))
            thread.start()
            flood(sys.stdout.fileno())
            thread.join()
        else:
            flood(sys.stderr.fileno() if args.mode == "flood_stderr" else sys.stdout.fileno())
    elif args.mode == "nonzero":
        os.write(sys.stdout.fileno(), b"retained output")
        os.write(sys.stderr.fileno(), b"retained error")
        return 7
    elif args.mode == "inherited_pipe":
        subprocess.Popen([sys.executable, "-I", "-c", "import time; time.sleep(1.5)"])
        os.write(sys.stdout.fileno(), b"parent exited")
    else:
        raise ValueError(args.mode)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
