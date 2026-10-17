"""Self-check: recompute the numbers quoted in 'Claude Review and Plan_claude10172026.md' from the saved results
and the repository, and report PASS/FAIL per assertion. Stdlib only; run from anywhere.

It checks the review's own claims (the 'claims made by this session'), not the project's.
"""
import glob
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(r"D:\Projects\drug_target_agents")
REVIEW = ROOT / "planning" / "Claude Review and Plan_claude10172026.md"
RES = ROOT / "planning" / "review-assets" / "claude-review-20261017" / "results"
text = REVIEW.read_text(encoding="utf-8")
checks = []


def check(name, actual, expected):
    checks.append((name, actual == expected, actual, expected))


def load(name):
    return json.loads((RES / name).read_text(encoding="utf-8-sig"))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT).decode()


# --- repository state -------------------------------------------------------------------------------------
OWN = ("Claude Review and Plan", "claude-review-20261017", "research-log-2026-10-17-claude-review")
status = [line for line in git("status", "--short").splitlines()
          if line.strip() and not any(token in line for token in OWN)]  # exclude this review's own files
check("uncommitted paths (before this review)", len(status), 58)
check("modified", sum(line.startswith(" M") for line in status), 16)
check("untracked", sum(line.startswith("??") for line in status), 42)
check("untracked public 2026-10-17 manifests",
      sum("data/manifests/public/2026-10-17-" in line and line.startswith("??") for line in status), 9)
check("commits", len(git("log", "--oneline").splitlines()), 11)
check("last commit", git("log", "-1", "--format=%h").strip(), "0ca0b19")
check("git remotes", git("remote", "-v").strip(), "")
tests = sum(len(re.findall(r"^    def test_", p.read_text(encoding="utf-8"), re.M)) for p in (ROOT / "tests").glob("test_*.py"))
check("test methods", tests, 173)
check("src lines", sum(len(p.read_text(encoding="utf-8").splitlines()) for p in (ROOT / "src" / "asof").glob("*.py")), 3350)
tool_files = list((ROOT / "tools").glob("*/*.py")) + list((ROOT / "tools").glob("*.py"))
check("tools lines", sum(len(p.read_text(encoding="utf-8").splitlines()) for p in tool_files), 3964)
check("cohort directories", sum(p.is_dir() for p in (ROOT / "data/benchmark/cohorts").iterdir()), 8)
check("public manifests", len(list((ROOT / "data/manifests/public").glob("*.json"))), 35)
check("planning notes", len(list((ROOT / "planning").glob("*.md"))) - 1, 21)  # minus this review
check("memory notes (before this review's log)", len([q for q in (ROOT / "memory").glob("*.md") if "claude-review" not in q.name]), 17)
catalog = json.loads((ROOT / "data/catalog/sources.json").read_text(encoding="utf-8"))
check("catalog", (len(catalog["providers"]), len(catalog["datasets"])), (83, 178))
receipts = list((ROOT / "data/benchmark/cohorts/clinical-long-session-20261017T064802Z/primary-source-receipts").iterdir())
check("primary-source receipt files", len(receipts), 43)

# --- saved verification results ---------------------------------------------------------------------------
seals = load("seals.json")
check("sealed files re-hashed (cohort)", sum(v["listed"] for v in seals.values()), 659)
check("seal problems", sum(len(v["problems"]) for v in seals.values()), 0)
anchors = load("public-anchors.json")
check("anchor pairs", sum(v["pairs"] for v in anchors.values()), 49)
check("anchor ok", sum(v["ok"] for v in anchors.values()), 48)
check("anchor mismatches", sum(len(v["mismatch"]) for v in anchors.values()), 1)
registry = load("registry-verify.json")
check("dossiers verified", sum(v["exit"] == 0 and v["result"]["status"] == "integrity_verified"
                               for v in registry["verifications"]), 10)
check("registry entries", len(registry["entries"]), 11)
archives = load("aact-archives.json")
check("archives matched", sum(r["match"] for r in archives["results"]), 6)
check("archive bytes", archives["total_bytes"], 12932171157)
inputs = load("rehash-inputs.json")
check("raw inputs ok", (inputs["ok"], inputs["files"], inputs["total_bytes"]), (2206, 2206, 9038960079))
sha1 = load("publisher-sha1.json")
check("publisher sha1", (sha1["match"], sha1["mismatch"], sha1["publisher_entries"]), (2205, [], 22557))
audit = load("source-audit.json")
check("rows scanned / matched", (audit["physical_rows_scanned"], audit["matched_rows_total"]), (29823171, 26985))
check("per-case equality", all(c["equal"] for c in audit["comparison"]), True)
check("trace", (audit["trace"]["checked"], audit["trace"]["fields_compared"], len(audit["trace"]["mismatches"])),
      (213, 13845, 0))
vb = load("vb-counts.json")
check("vb counts", (vb["label_rows"], vb["decisive_primary_endpoints"], vb["linkage_rows"],
                    vb["linkage_unique_target_disease_pairs"], vb["linkage_unique_targets"],
                    vb["linkage_unique_diseases"]), (56707, 29100, 488361, 72158, 1520, 2559))
ld = load("ld-matrix.json")
check("ld", (ld["entries_recomputed"], ld["matrix_rank_tol_1e-8"], ld["max_abs_diff_vs_stored"] < 1e-14),
      (8874441, 502, True))
sizing = load("crude-pair-sizing.json")
configs = {c["label"]: c for c in sizing["configs"]}
check("sizing unrestricted", (configs["all pairs with Phase<=2 trial at origin (24 months)"]["at_risk_pairs"],
                              configs["all pairs with Phase<=2 trial at origin (24 months)"]["pair_level_transitions"]),
      (46819, 659))
check("sizing recent", (configs["recent-activity restricted (24 months)"]["at_risk_pairs"],
                        configs["recent-activity restricted (24 months)"]["pair_level_transitions"]), (15631, 485))
check("sizing 12 months", configs["recent-activity restricted (12 months)"]["pair_level_transitions"], 343)
coverage = load("publisher-coverage.json")
check("publisher coverage", (coverage["evidence"]["present_locally"], coverage["evidence"]["absent"],
                             coverage["target"]["present_locally"], coverage["disease"]["present_locally"],
                             coverage["publisher_chembl_evidence_files_excluded_by_design"]),
      (2194, ["output/evidence/_SUCCESS"], 10, 1, 100))
stamps = load("publisher-timestamps-all.json")
check("publisher timestamps", (stamps["ok"], stamps["error_count"], list(stamps["distinct_days"])),
      (2204, 1, ["2025-08-19"]))  # the single transient error was retried by hand (also 2025-08-19)
full = load("validate-full-powershell-7.6.7.json")
check("full validation", (full["tests"]["run"], full["tests"]["skipped"], full["powershell_syntax"], full["status"]),
      (173, [], True, "passed"))

timeline = json.loads((ROOT / "data/benchmark/cohorts/clinical-long-session-20261017T064802Z/timeline/timeline.json").read_bytes().decode("utf-8-sig"))
check("timeline observations", (len(timeline), sum(len(r["observations"]) for r in timeline)), (24, 120))

# --- dossier sizes ----------------------------------------------------------------------------------------
cftr = ROOT / "runs/literature-coverage-20261017T082208Z/cftr-mondo_0009061-activate-small_molecule"
check("CFTR ledger MiB", round((cftr / "ledger.json").stat().st_size / 1048576, 1), 128.2)
check("CFTR % of 256 MiB", round(100 * (cftr / "ledger.json").stat().st_size / 1048576 / 256, 1), 50.1)

# --- ledger tally in the review itself ----------------------------------------------------------------------
section = text.split("## 3. Verification ledger")[1].split("### G. Not verifiable here")[0]
rows = [line for line in section.splitlines() if re.match(r"\| [A-F]\d+ \|", line)]
check("ledger rows", len(rows), 42)
confirmed = [r for r in rows if re.search(r"\*\*Confirmed\*\*", r)]
qualified = [r for r in rows if re.search(r"\*\*Confirmed \(", r) or re.search(r"\*\*Confirmed in code\*\*", r)]
flagged = [r for r in rows if re.search(r"\*\*(Stale|Overstated)\*\*", r)]
check("tally confirmed/qualified/flagged", (len(confirmed), len(qualified), len(flagged)), (35, 4, 3))

failed = [c for c in checks if not c[1]]
for name, ok, actual, expected in checks:
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  actual={actual!r} expected={expected!r}"))
print(f"\n{len(checks) - len(failed)}/{len(checks)} assertions passed")
raise SystemExit(1 if failed else 0)
