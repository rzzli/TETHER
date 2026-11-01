"""Exact archive and installation contract for the two P09 project wheels.

This fixed verifier accepts the observed setuptools 84 wheel format. It neither
installs packages nor treats arbitrary dependency wheels as project assets.
"""
from __future__ import annotations

import base64
from collections import Counter
import csv
from email.parser import BytesParser
from email.policy import default
import hashlib
import io
from pathlib import Path
import re
import stat
import zipfile


SPECS = {
    "asof": {
        "distribution": "asof-target-agents", "version": "0.3.11",
        "summary": "Dated evidence workflows for auditable target and clinical-program assessment",
        "python": ">=3.11", "extras": ("ingest",),
        "dependencies": ('pyarrow==21.0.0; extra == "ingest"',),
        "entrypoint": "asof = asof.cli:main",
    },
    "asof_p05_replay": {
        "distribution": "asof-p05-replay", "version": "0.1.0",
        "summary": "Versioned source-inclusive reconstruction of the AsOf P05 technical study",
        "python": "<3.12,>=3.11", "extras": (),
        "dependencies": ("asof-target-agents==0.3.11", "pyarrow==21.0.0"),
        "entrypoint": "asof-p05-replay = asof_p05_replay.cli:main",
    },
}


def need(condition, message):
    if not condition:
        raise ValueError(message)


def _safe_name(name):
    need(type(name) is str and name and not name.startswith("/")
         and not any(ord(char) < 32 or ord(char) == 127 for char in name)
         and "\\" not in name and ":" not in name
         and all(part not in ("", ".", "..") and part == part.strip() for part in name.split("/")),
         "Unsafe wheel member name")


def _headers(raw, expected, *, repeats=()):
    message = BytesParser(policy=default).parsebytes(raw)
    need(not message.defects and message.get_payload() == "", "Malformed wheel metadata")
    need(Counter(message.keys()) == Counter({key: len(value) if key in repeats else 1 for key, value in expected.items()}),
         "Unexpected or duplicate wheel metadata fields")
    for key, value in expected.items():
        values = tuple(str(item) for item in message.get_all(key, []))
        if key in repeats:
            need(Counter(values) == Counter(value), "Wheel metadata differs: " + key)
        elif key == "License":
            need(len(values) == 1 and " ".join(values[0].split()) == " ".join(value.split()),
                 "Wheel embedded license metadata differs")
        else:
            need(values == (value,), "Wheel metadata differs: " + key)


def verify_wheel(path, prefix, expected_payloads, license_bytes):
    """Return exact package SHA map after validating the whole project wheel.

    expected_payloads is the independently reviewed relative package .py/.json
    inventory. license_bytes is the exact separately allowlisted project LICENSE.
    Unknown package families, archive members, metadata and entrypoints fail.
    """
    need(prefix in SPECS, "Unknown P09 project wheel")
    need(type(expected_payloads) is dict and bool(expected_payloads), "Expected wheel package inventory required")
    need(type(license_bytes) is bytes and bool(license_bytes), "Expected project license bytes required")
    spec = SPECS[prefix]
    dist = spec["distribution"].replace("-", "_") + "-" + spec["version"]
    info = dist + ".dist-info/"
    path = Path(path)
    need(path.name == dist + "-py3-none-any.whl", "Wheel filename distribution/version/tag differs")
    for name, digest in expected_payloads.items():
        _safe_name(name)
        need(name.endswith((".py", ".json")) and type(digest) is str and re.fullmatch(r"[0-9a-f]{64}", digest),
             "Invalid expected package payload")
    package_members = {prefix + "/" + name for name in expected_payloads}
    metadata_members = {info + name for name in ("METADATA", "WHEEL", "entry_points.txt", "top_level.txt", "RECORD", "licenses/LICENSE")}
    required = package_members | metadata_members
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        names = [member.filename for member in members]
        need(not archive.comment, "Unreviewed wheel archive comment")
        for member in members:
            _safe_name(member.filename)
            mode = member.external_attr >> 16
            need(stat.S_IFMT(mode) in (0, stat.S_IFREG) and not member.is_dir()
                 and not member.flag_bits & 1 and not member.comment and not member.extra
                 and member.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
                 "Unreviewed wheel member type or metadata")
        need(len(names) == len(set(names)) == len({name.casefold() for name in names}), "Duplicate or aliased wheel members")
        need(set(names) == required, "Whole wheel positive allowlist differs")
        payloads = {name: archive.read(name) for name in names}
    observed = {name: hashlib.sha256(payloads[prefix + "/" + name]).hexdigest() for name in expected_payloads}
    need(observed == expected_payloads, "Wheel differs from reviewed package payloads")
    need(payloads[info + "licenses/LICENSE"] == license_bytes, "Wheel license file differs")
    metadata = {
        "Metadata-Version": "2.4", "Name": spec["distribution"], "Version": spec["version"],
        "Summary": spec["summary"], "License": license_bytes.decode("utf-8"), "Requires-Python": spec["python"],
        "License-File": "LICENSE", "Dynamic": "license-file", "Requires-Dist": spec["dependencies"],
    }
    if spec["extras"]:
        metadata["Provides-Extra"] = spec["extras"]
    _headers(payloads[info + "METADATA"], metadata, repeats=("Requires-Dist", "Provides-Extra"))
    _headers(payloads[info + "WHEEL"], {
        "Wheel-Version": "1.0", "Generator": "setuptools (84.0.0)", "Root-Is-Purelib": "true", "Tag": "py3-none-any",
    })
    need(payloads[info + "entry_points.txt"] == ("[console_scripts]\n" + spec["entrypoint"] + "\n").encode(),
         "Wheel console entrypoint differs")
    need(payloads[info + "top_level.txt"] == (prefix + "\n").encode(), "Wheel top-level package differs")
    rows = list(csv.reader(io.StringIO(payloads[info + "RECORD"].decode("utf-8"), newline=""), strict=True))
    need(all(len(row) == 3 for row in rows), "Malformed wheel RECORD")
    need(len(rows) == len(required) and len({row[0] for row in rows}) == len(rows)
         and {row[0] for row in rows} == required, "Incomplete or duplicated wheel RECORD")
    for name, digest, size in rows:
        if name == info + "RECORD":
            need(digest == size == "", "Wheel RECORD self-entry differs")
        else:
            raw = payloads[name]
            expected = "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b"=").decode("ascii")
            need(digest == expected and size == str(len(raw)), "Wheel RECORD hash or size differs")
    return observed
