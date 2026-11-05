"""Bounded, exclusive acquisition of public SciFact originals; no model execution."""
from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def fetch(directory, name, url, cap):
    receipt = {"url": url, "started_at_utc": now(), "byte_cap": cap,
               "path": str(directory / name), "status": "started"}
    started = time.monotonic()
    partial = directory / (name + ".partial")
    try:
        if urlsplit(url).scheme != "https":
            raise ValueError("HTTPS required")
        digest = hashlib.sha256()
        count = 0
        request = Request(url, headers={"User-Agent": "TETHER-public-benchmark-acquisition/1"})
        with urlopen(request, timeout=30) as response, partial.open("xb") as stream:
            if urlsplit(response.geturl()).scheme != "https":
                raise ValueError("Non-HTTPS redirect")
            receipt.update(final_url=response.geturl(), http_status=response.status,
                           headers={k: response.headers.get(k) for k in
                                    ("Content-Length", "Content-Type", "ETag", "Last-Modified")})
            declared = response.headers.get("Content-Length")
            if declared is not None and int(declared) > cap:
                raise ValueError("Declared length exceeds cap")
            while True:
                if time.monotonic() - started > 180:
                    raise TimeoutError("Total transfer deadline exceeded")
                chunk = response.read(min(1024 * 1024, cap - count + 1))
                if not chunk:
                    break
                if count + len(chunk) > cap:
                    raise ValueError("Actual length exceeds cap")
                stream.write(chunk)
                digest.update(chunk)
                count += len(chunk)
            if declared is not None and count != int(declared):
                raise ValueError("Incomplete declared transfer")
        # Windows rename refuses replacement; parent and names are fresh literals.
        partial.rename(directory / name)
        receipt.update(status="downloaded_not_parsed", bytes=count,
                       sha256=digest.hexdigest())
    except BaseException as error:
        receipt.update(status="failed", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        receipt.update(finished_at_utc=now(), elapsed_seconds=time.monotonic() - started)
        save(directory / (name + ".receipt.json"), receipt)
        print(json.dumps({"name": name, "status": receipt["status"],
                          "bytes": receipt.get("bytes"), "sha256": receipt.get("sha256")}), flush=True)
    return directory / name


def main():
    directory = Path(sys.argv[1]).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    save(directory / "STARTED.json", {"started_at_utc": now(), "scope": "public original acquisition only",
                                     "candidate_scoring": False, "provider_spend_usd": 0})
    try:
        commits = {}
        for repo in ("scifact", "scifact-evaluator"):
            metadata = fetch(directory, repo + "-commit.json",
                             f"https://api.github.com/repos/allenai/{repo}/commits/master", 1024 * 1024)
            commit = json.loads(metadata.read_text(encoding="utf-8"))["sha"]
            if len(commit) != 40 or any(c not in "0123456789abcdef" for c in commit):
                raise ValueError("Invalid repository commit")
            commits[repo] = commit
            fetch(directory, repo + "-source.zip",
                  f"https://codeload.github.com/allenai/{repo}/zip/{commit}", 8 * 1024 * 1024)
        fetch(directory, "scifact-data.tar.gz",
              "https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz", 64 * 1024 * 1024)
        save(directory / "COMPLETE.json", {"completed_at_utc": now(), "status": "downloaded_not_parsed",
                                          "commits": commits, "reference_role": "evaluator_only_until_projection",
                                          "historical_availability_established": False,
                                          "license_review": "pending_pinned_source_review"})
    except BaseException as error:
        save(directory / "FAILED.json", {"failed_at_utc": now(), "error_type": type(error).__name__,
                                        "error": str(error), "retry_policy": "fresh output only"})
        raise


if __name__ == "__main__":
    main()
