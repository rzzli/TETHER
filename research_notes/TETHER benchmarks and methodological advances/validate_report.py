"""Validate this documentation synthesis without importing TETHER or reading datasets."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTES = Path(__file__).resolve().parent
REPORT = ROOT / "reports/TETHER benchmarks and methodological advances.md"
RECORD = NOTES / "REPORT-VALIDATION.json"
BASELINE = "bc9d830"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8")


def main() -> None:
    RECORD.write_text('{"status":"RUNNING"}\n', encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    links = re.findall(r"\[[^\]]*\]\((?:<([^>]+)>|([^\s)]+))\)", report)
    checked = []
    errors = []
    external = []
    for angle, plain in links:
        target = angle or plain
        if target.startswith(("https://", "http://")):
            external.append(target)
            continue
        line_match = re.search(r":(\d+)$", target)
        line = int(line_match.group(1)) if line_match else None
        path_text = target[:line_match.start()] if line_match else target
        path = Path(path_text)
        if not path.is_absolute():
            path = REPORT.parent / path
        exists = path.is_file()
        in_range = exists
        if exists and line is not None:
            in_range = 1 <= line <= len(path.read_text(encoding="utf-8-sig").splitlines())
        checked.append({"target": target, "exists": exists, "line_in_range": in_range})
        if not exists or not in_range:
            errors.append(f"invalid local link: {target}")

    production = git("diff", "--name-only", BASELINE, "--", "src", "packages", "tools", "paper", "data/catalog")
    older = git("diff", "--name-only", BASELINE, "--", "reports/TETHER efficiency and comparative value.md", "research_notes/TETHER efficiency and comparative value")
    if production or older:
        errors.append("production or previous audit changed")
    before_todo = git("show", f"{BASELINE}:TODO.md")
    now_todo = (ROOT / "TODO.md").read_text(encoding="utf-8")
    status_pattern = r"^- \[[ x]\] (?:CE\d+|Q\d+[a-z]?|P\d+[a-z]?|C\d+|N\d+)\b.*$"
    old_status = re.findall(status_pattern, before_todo, re.M)
    new_status = re.findall(status_pattern, now_todo, re.M)
    statuses_match = old_status == new_status
    if not statuses_match:
        errors.append("prior task statuses changed")
    diff_check = subprocess.run(["git", "diff", "--check"], cwd=ROOT, text=True, capture_output=True)
    if diff_check.returncode:
        errors.append(diff_check.stdout + diff_check.stderr)

    docs = [REPORT, ROOT / "README.md", ROOT / "TODO.md", ROOT / "memory/MEMORY.md", ROOT / "memory/project-goals.md", ROOT / "memory/research-log-2026-11-02-benchmarks-and-methods.md"]
    source_notes = [NOTES / name for name in ("biomedical_benchmarks.md", "general_benchmarks_methods.md", "methodology_gap_mapping.md")]
    # Word count excludes Markdown URL targets, which otherwise inflate prose length.
    prose = re.sub(r"\]\((?:<[^>]+>|[^)]+)\)", "]", report)
    payload = {
        "status": "PASS" if not errors else "FAIL",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "baseline": BASELINE,
        "scope": "Documentation-only synthesis, local links/line bounds, source-note hashes, unchanged production and prior task statuses. No benchmark or software test execution.",
        "report_word_count_excluding_link_targets": len(prose.split()),
        "document_hashes": {p.relative_to(ROOT).as_posix(): sha(p) for p in docs},
        "research_note_hashes": {p.name: sha(p) for p in source_notes},
        "validator_sha256": sha(Path(__file__)),
        "links": {"local_count": len(checked), "local": checked, "external_occurrences": len(external), "external_unique_count": len(set(external)), "external_urls": sorted(set(external)), "external_access": "Primary-source access/version limits inherited from completed researcher notes. Writer made no new fetch and did not establish live URL status."},
        "preservation": {"production_diff": production, "previous_audit_diff": older, "prior_CE_Q_P_C_N_statuses_match": statuses_match, "status_rows_compared": len(old_status), "git_diff_check": diff_check.returncode == 0, "raw_datasets_read_or_rehashed": False},
        "limitations": ["No external benchmark, scorer, model or environment executed or acquired.", "Three preceding P2 defects and CE01-CE04 remain pending; Q04/Q05 not activated.", "Native benchmark adapters and task-capable components are proposals, not implemented capabilities.", "Some public dataset previews were development-exposed; see biomedical exposure ledger.", "Model-weight chronology cannot be inferred from eligible retrieved evidence.", "Original benchmark scores and proposed derived conformance tests must remain separate.", "No protected reviewer/clinical files were read; expert recruitment remains retired and author facts deferred."],
        "errors": errors,
    }
    RECORD.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": payload["status"], "words": payload["report_word_count_excluding_link_targets"], "local_links": len(checked), "external_unique": len(set(external)), "status_rows": len(old_status), "errors": errors}))
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
