"""Apply narrow current-state navigation updates; preserve dated prior assessments."""
from pathlib import Path
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent


def pin(path):
    raw = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    names = ["README.md", "TODO.md", "planning/Project Recovery and Evaluation Plan 2026-10-26.md",
             "planning/Recovery Status and Next Gates 2026-10-26.md", "planning/Project Progress Reassessments.md",
             "planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md",
             "memory/MEMORY.md", "memory/project-goals.md",
             "planning/Project Progress Reassessment 2026-10-31 - Component Guards.md",
             "memory/research-log-2026-10-31-component-guards.md"]
    before = {name: pin(ROOT / name) for name in names}
    current = ("Current checkpoint, 31 October UTC: {link} accepts only Source5's API/axis-kind guard: "
               "43 executable controls PASS (21 source-runtime / 22 data), four DEFERRED and one STATIC. "
               "Root ec290b97 / independent actual peer 69d14742; 1,493 retained-data checks and all "
               "188 artifact hashes pass. The first suite reports 0.250s; only the two intended "
               "failures change to exact refusals, with raw bytes and prior31/12,38/5,41/2 controls retained. "
               "Full native25, native bank/bridge, real Win32, leases, physical14/new84, resources and science remain open.")
    next_step = ("Next: close the four native-bank design joins (canonical handle before C3 initialization, "
                 "source/native buffer epochs, backend-neutral committed/cold observations and native-mode "
                 "synthetic-mutation refusal), then freeze independent positive bank/ticket expectations "
                 "before a named kernel/CPython extension implementation. Compile/fake-bridge and owned-D "
                 "original7 gates remain separate. The actual new84 roster/core4 roles, joint physical14 "
                 "and held-lease child/image route remain pending; illustrative19,079 calls are not fit. "
                 "AsOf0.3.11/defaultv2 retains1,774 tests/327 unchanged pins without rerun. Original "
                 "FAILED/INCOMPLETE_TIMEOUT, missing data and human/scientific gates remain; $0 and "
                 "downloader/stopped monitor unchanged.")
    for name in names[:6]:
        path = ROOT / name
        raw = path.read_bytes().decode("utf-8")
        target = ("planning/" if name in ("README.md", "TODO.md") else "") + "Project Progress Reassessment 2026-10-31 - Component Guards.md"
        link = "[Source5 component guards](<" + target + ">)"
        raw, count = re.subn(r"^Current checkpoint, 30 October UTC: [^\n]+", lambda _: current.format(link=link), raw, count=1, flags=re.M)
        assert count == 1, name
        raw, count = re.subn(r"^Next: correct only the two remaining native25[^\n]+", lambda _: next_step, raw, count=1, flags=re.M)
        assert count == 1, name
        if name == "TODO.md":
            raw, count = re.subn(r"^- \[ \] Implement and validate the complete entry/operations/file-view route\.[^\n]+",
                "- [ ] Implement and validate the complete entry/operations/file-view route. Source4 E08/122 and Source5's 43 executable component controls are accepted; native25 retains four deferrals and one static row. Actual native bank/bridge, real roster/consumers, positive leases, physical14/new84, resources and science remain pending. Both historical E16 invocations and prior failures remain preserved.", raw, count=1, flags=re.M)
            assert count == 1
            raw += ("\n- [x] Correct and independently validate only Source5 API/axis-kind guards: root ec290b97 / peer69d14742;43 executable controls PASS, four DEFERRED, one STATIC;1,493 retained-data checks/188 artifact hashes pass. No full-native25 or real bridge qualification.\n"
                    "- [ ] Reassess all R01–R16/HR1–HR4 after Source5 guards and pass independent current-document/memory QA. Assessment: planning/Project Progress Reassessment 2026-10-31 - Component Guards.md; documentation QA pending.\n")
        elif name == "planning/Project Progress Reassessments.md":
            raw += ("\n| R09 Source5 API/axis-kind guard accepted | [31 October UTC component-guard snapshot](<Project Progress Reassessment 2026-10-31 - Component Guards.md>) | Root ec290b97 / actual peer69d14742:43 executable PASS, four DEFERRED, one STATIC;1,493 retained-data checks/188 artifacts pass. Only two intended failures change; full native25/native bank/physical/resources/science remain open. Current documentation QA pending. |\n")
        elif name == "planning/Recovery Status and Next Gates 2026-10-26.md":
            raw = raw.replace("Updated 30 October 2026 UTC.", "Updated 31 October 2026 UTC.", 1)
        elif name == "planning/Project Recovery and Evaluation Plan 2026-10-26.md":
            raw = raw.replace("**Status updated:** 30 October UTC / 29 October Los Angeles.", "**Status updated:** 31 October UTC / 30 October Los Angeles.", 1)
        with path.open("w", encoding="utf-8", newline="") as stream:
            stream.write(raw)
    path = ROOT / "memory/MEMORY.md"
    raw = path.read_bytes().decode("utf-8")
    entry = ("- [[research-log-2026-10-31-component-guards]] - Root ec290b97 / actual peer69d14742 accepts only the Source5 API/axis-kind guard:43 executable PASS, four DEFERRED, one STATIC;1,493 retained-data checks/188 artifacts pass,0.250s. Prior failures and raw bytes retained. Full native25/native bank/bridge/physical/new84/resources/science/humans stay open. Next close four bridge design joins, then independent positive native expectations.327 application pins match;1,774 tests retained/no rerun. Current documentation QA pending.\n\n")
    assert raw.startswith("# Research memory index\n\n")
    raw = raw.replace("# Research memory index\n\n", "# Research memory index\n\n" + entry, 1)
    with path.open("w", encoding="utf-8", newline="") as stream:stream.write(raw)
    path = ROOT / "memory/project-goals.md"
    raw = path.read_bytes().decode("utf-8")
    start = "Current checkpoint: [[Project Progress Reassessment 2026-10-30 - C Return Capture]]."
    assert raw.count(start) == 1
    new = ("Current checkpoint: [[Project Progress Reassessment 2026-10-31 - Component Guards]].\n"
           "Root ec290b97 / peer69d14742 accepts only Source5's exact API/axis-kind guard:\n"
           "43 executable PASS (21 runtime/22 data), four DEFERRED and one STATIC;1,493 retained-data\n"
           "checks and188 artifact hashes pass in the0.250s suite. Only the two intended failures\n"
           "change; prior31/12,38/5,41/2 and raw bits remain preserved. Full native25/entry/native\n"
           "bank/bridge/Win32/leases/physical14/new84/resources/science remain open. Next close\n"
           "the four actual bridge joins and independent positive bank/ticket oracle before source.\n"
           "AsOf0.3.11/defaultv2 retains1,774 tests/327 unchanged pins; no app-suite rerun or\n"
           "default change. Data65/labels36/states17of32/joint-ready0of12 and HR1–HR4 remain\n"
           "pending; features empty/probabilities null. $0, downloader/monitor unchanged.\n"
           "See [[research-log-2026-10-31-component-guards]]. Current documentation QA pending.\n\n"
           "### Prior C-return checkpoint (retained history)\n\n"
           "Prior checkpoint: [[Project Progress Reassessment 2026-10-30 - C Return Capture]].")
    raw = raw.replace(start, new, 1).replace("updated: 2026-10-30", "updated: 2026-10-31", 1)
    with path.open("w", encoding="utf-8", newline="") as stream:stream.write(raw)
    after = {name: pin(ROOT / name) for name in names}
    report = dict(schema_version=1, status="AUTHORING_COMPLETE_PENDING_INDEPENDENT_DOC_QA",
                  documents_before=before, documents_final=after,
                  limits="Current navigation/status, two new Source5 TODO entries and memory/index only. Prior dated assessments/logs, other TODO gates and source unchanged.",
                  source_imports=0, subject_runs=0, provider_spend_usd=0)
    with (BASE / "SOURCE5-CURRENT-DOCS-AUTHORING-v1.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, indent=2);stream.write("\n")
    print(json.dumps({"documents": len(after), "source_imports": 0, "subject_runs": 0}))


if __name__ == "__main__":main()
