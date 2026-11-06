"""Restore current-doc UTF-8/newline conventions after a cp1252 read mistake.

Only four explicitly named mutable documents are touched; all experiment bytes
remain unchanged. Prior current-doc bytes are retained in git commit eda8118.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[3]
changed = []


def old(name):
    return subprocess.check_output(["git", "show", "e8e40af:" + name], cwd=root).decode("utf-8")


def publish(name, text):
    path = root / name
    before = path.read_bytes()
    after = text.replace("\r\n", "\n").encode("utf-8")
    path.write_bytes(after)
    changed.append({"path": name, "before_sha256": hashlib.sha256(before).hexdigest(),
                    "after_sha256": hashlib.sha256(after).hexdigest(),
                    "before_bytes": len(before), "after_bytes": len(after)})


s = old("README.md")
s = s.replace("qualification. Equal-policy Inspect and the final audit follow.",
              "qualification. The Inspect comparison is also complete in its declared scope; the final goal audit follows.")
a = "equivalent-policy Inspect remains in preparation under the [prospective protocol](<planning/TETHER Inspect Comparison Protocol 2026-11-06.md>). Its isolated0.3.287 environment and native mock qualify; new extension defects are being corrected before the comparison is frozen."
b = "the [Inspect comparison](<planning/TETHER Inspect Comparison Results 2026-11-06.md>) independently reconstructs all981 conformance cells and19 intended runtime dispositions. The median paired Inspect/TETHER batch time is1.5465; substantial reused code and explicit runtime gaps prevent a simpler-complete-replacement claim. BG06 is the remaining active goal audit."
assert a in s
publish("README.md", s.replace(a, b))

name = "memory/MEMORY.md"
current = (root/name).read_text(encoding="utf-8")
new_line = next(line for line in current.splitlines() if line.startswith("- [[research-log-2026-11-06-inspect-results]]"))
s = old(name).replace("# TETHER research memory index\n", "# TETHER research memory index\n\n"+new_line+"\n", 1)
publish(name, s)

name = "memory/project-goals.md"
current = (root/name).read_text(encoding="utf-8")
start, end = "Current November 6 UTC execution:", "## Current recovery execution"
new_section = current[current.index(start):current.index(end)]
s = old(name)
s = s[:s.index(start)] + new_section + s[s.index(end):]
s = s.replace("Next,\nimplement and evaluate policy-equivalent Inspect, then audit the complete goal.",
              "The Inspect comparison is also complete in its declared scope. Next, audit the complete goal.")
publish(name, s)

name = "planning/TETHER Inspect Comparison Results 2026-11-06.md"
s = (root/name).read_text(encoding="utf-8")
repairs = []


def repair(match):
    fragment = match.group(0)
    try:
        clean = fragment.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return fragment
    repairs.append({"before": fragment, "after": clean})
    return clean


s = re.sub("(?:\u00e2.{2}|[\u00c2\u00c3].|\u00f0.{3})", repair, s)
publish(name, s)
out = root/"planning/review-assets/tether-benchmark-goal-audit-20261106/TEXT-ENCODING-CORRECTION-01.json"
with out.open("x", encoding="utf-8", newline="\n") as stream:
    json.dump({"schema_version": 1, "status": "pass", "base_commit": "e8e40af",
               "retained_mistaken_checkpoint": "eda8118", "files": changed,
               "result_report_replacements": repairs,
               "scope": "Current documentation only; original historical memory restored from exact UTF-8 git content with intended status edits."}, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(json.dumps({"status": "pass", "files": len(changed), "report_repairs": len(repairs)}))
