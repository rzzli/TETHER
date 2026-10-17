"""Evaluator-only development cohort rules; no runtime/model dependencies."""
from __future__ import annotations

import calendar
from datetime import date
import hashlib
import json
from pathlib import Path
import re


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def date_bounds(value):
    """Retain report precision without inventing an event date."""
    if value is None:
        return None
    if re.fullmatch(r"\d{4}", value):
        year = int(value)
        return date(year, 1, 1).isoformat(), date(year, 12, 31).isoformat()
    if re.fullmatch(r"\d{4}-\d{2}", value):
        year, month = map(int, value.split("-"))
        return date(year, month, 1).isoformat(), date(year, month, calendar.monthrange(year, month)[1]).isoformat()
    parsed = date.fromisoformat(value).isoformat()
    return parsed, parsed


def report_window(value, origin, endpoint):
    bounds = date_bounds(value)
    if not bounds:
        return "unknown"
    low, high = bounds
    if high <= origin:
        return "preorigin"
    if low > endpoint:
        return "postendpoint"
    if low > origin and high <= endpoint:
        return "within_window"
    return "straddles_boundary"


def phase_screen(phase, status, anchor_role="experimental"):
    phase = re.sub(r"[^a-z0-9]", "", (phase or "").lower())
    status = re.sub(r"[^a-z0-9]", "", (status or "").lower())
    if anchor_role in {"rescue", "background", "comparator", "closed_arm"}:
        return "excluded_anchor_role"
    if status == "notyetrecruiting":
        return "excluded_not_active_at_origin"
    if phase == "phase3":
        return "excluded_phase3"
    if status not in {"recruiting", "activenotrecruiting"}:
        return "unresolved_activity"
    if phase in {"phase1", "phase2"}:
        return "provisional_origin_screen_pass"
    return "unresolved_arm_stage"


def incident_supported(event, origin, endpoint):
    interval = event.get("event_interval") or {}
    low, high = interval.get("lower"), interval.get("upper")
    if low:
        date.fromisoformat(low)
    if high:
        date.fromisoformat(high)
    if low and high and low > high:
        raise ValueError("Reversed event interval")
    return bool(low and high and origin < low <= high <= endpoint
                and event.get("scope_match") == "qualified"
                and event.get("content_status") == "primary_report_or_manuscript_reviewed"
                and event.get("report_window") == "within_window")


def verify_manifest(path, expected):
    path = Path(path)
    if sha(path) != expected:
        raise ValueError("Parent manifest anchor changed")
    seen = set()
    for row in load(path)["files"]:
        source = (path.parent / row["path"]).resolve()
        if not source.is_relative_to(path.parent.resolve()) or source in seen:
            raise ValueError("Unsafe or duplicate manifest path")
        seen.add(source)
        if sha(source) != row["sha256"]:
            raise ValueError(f"Parent changed: {source}")
    return len(seen)


def validate_bundle(bundle, selected):
    cases = {c["candidate_id"] for c in selected}
    dispositions = bundle["dispositions"]
    if len(dispositions) != len(cases) or {c["candidate_id"] for c in dispositions} != cases:
        raise ValueError("Incomplete or duplicate cohort accounting")
    programs = bundle["programs"]
    pids = {p["program_id"] for p in programs}
    if len(pids) != len(programs):
        raise ValueError("Duplicate program ID")
    arms = {a["arm_id"]: a for a in bundle["trial-arm-links"]}
    if len(arms) != len(bundle["trial-arm-links"]):
        raise ValueError("Duplicate arm ID")
    for p in programs:
        if p["candidate_id"] not in cases or p["role"] != "evaluation_only":
            raise ValueError("Invalid program role or candidate")
        for aid in p["arm_ids"]:
            if aid not in arms or arms[aid]["candidate_id"] != p["candidate_id"]:
                raise ValueError("Platform/arm leakage")
        if p.get("historically_certified"):
            raise ValueError("This development protocol does not certify historical mappings")
    for d in dispositions:
        if not set(d["program_ids"]) <= pids:
            raise ValueError("Broken disposition reference")
    reports = bundle["reports"]
    rids = {r["report_id"] for r in reports}
    report_index = {r["report_id"]: r for r in reports}
    program_index = {p["program_id"]: p for p in programs}
    if len(rids) != len(reports):
        raise ValueError("Duplicate report ID")
    semantic_keys = [(r["candidate_id"], r["source_id"]) for r in reports]
    if len(set(semantic_keys)) != len(semantic_keys):
        raise ValueError("Duplicate source report")
    eids = set()
    for e in bundle["events"]:
        if e["event_id"] in eids or not set(e["report_ids"]) <= rids:
            raise ValueError("Duplicate event or broken report reference")
        eids.add(e["event_id"])
        if not set(e["candidate_program_ids"]) <= pids:
            raise ValueError("Broken event program reference")
        if any(report_index[r]["candidate_id"] != e['candidate_id'] for r in e['report_ids']):
            raise ValueError("Report assigned to wrong candidate")
        if any(program_index[p]['candidate_id'] != e['candidate_id'] for p in e['candidate_program_ids']):
            raise ValueError("Event assigned to wrong program")
        supported = incident_supported(e, "2023-01-01", "2025-01-01")
        if e["incident_supported"] != supported:
            raise ValueError("Unsupported incident classification")
    followup = bundle["followup-assessments"]
    if len(followup) != len(cases) or {f["candidate_id"] for f in followup} != cases:
        raise ValueError("Incomplete follow-up accounting")
    for f in followup:
        if f["clinical_label"] is not None or f["censoring_date"] is not None:
            raise ValueError("Development records cannot manufacture labels/censoring")
    return {"status": "passed", "cases": len(cases), "program_candidates": len(pids),
            "reports": len(reports), "events": len(eids), "scientific_validation": "not_established"}
