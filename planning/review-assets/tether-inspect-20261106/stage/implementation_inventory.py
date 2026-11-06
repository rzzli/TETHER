"""Descriptive source surface, not a minimal implementation or effort estimate."""
import argparse
import ast
import hashlib
import json
from pathlib import Path


def describe(path, project):
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    tree = ast.parse(text)
    try:
        label = path.relative_to(project).as_posix()
    except ValueError:
        label = str(path)
    lines = text.splitlines()
    return {"path": label, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
            "physical_lines": len(lines),
            "nonblank_lines_not_starting_hash": sum(bool(x.strip()) and not x.lstrip().startswith("#") for x in lines),
            "functions": sum(isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) for x in ast.walk(tree)),
            "classes": sum(isinstance(x, ast.ClassDef) for x in ast.walk(tree))}


def group(paths, project, scope):
    files = [describe(p, project) for p in sorted(set(paths))]
    fields = ("bytes", "physical_lines", "nonblank_lines_not_starting_hash", "functions", "classes")
    return {"scope": scope, "file_count": len(files),
            **{key: sum(x[key] for x in files) for key in fields}, "files": files}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.project.resolve()
    if args.output.exists():
        raise FileExistsError(args.output)
    review = root / "planning/review-assets/tether-inspect-20261106"
    matrix = json.loads((review / "policy/OBLIGATION-MATRIX.json").read_text())
    extension = root / "experiments/inspect_policy"
    installed = root / "data/cache/tether-inspect-env-attempt02/environment/Lib/site-packages"
    main_names = ("__init__.py", "records.py", "accounting.py", "archive.py", "evidence.py", "task.py", "runtime.py", "network.py")
    witness_names = ("witnesses.py", "witness_worker.py", "process_witnesses.py")
    expected_new = set(main_names) | set(witness_names) | {"controller.py"}
    actual_new = {p.name for p in extension.glob("*.py")}
    if actual_new != expected_new:
        raise ValueError("New source inventory must be classified explicitly: " + str(actual_new ^ expected_new))
    groups = {
        "new_policy_and_inspect_runtime": group([extension / p for p in main_names], root,
            "Includes common archive/record utilities also used by the bare arms; not all Inspect-only overhead."),
        "shared_experiment_controller": group([extension / "controller.py"], root,
            "Shared three-arm supervision, preparation, measurement and sealing; not native Inspect policy."),
        "fictional_runtime_witness_helpers": group([extension / p for p in witness_names], root,
            "Fixture construction and live qualification orchestration; separate from production policy."),
        "maintained_extension_tests": group(list((extension / "tests").glob("*.py")), root,
            "Includes fixture utilities; physical lines are not independent test assertions."),
        "reused_independent_validator": group([root / row["path"] for row in matrix["reused_validator"]["files"]], root,
            "Full eight-file independent policy closure; not new Inspect integration."),
        "reused_reference_adapters": group([root / "experiments/equal_policy/reference.py", root / "experiments/equal_policy_v2/reference.py"], root,
            "Standalone native-product adapter; includes unused materialization helpers, not a minimal runtime estimate."),
        "independent_analysis_and_tests": group(list((review / "reconstruction").glob("*.py")), root,
            "Independent result/receipt/native-log reconstruction and its tests; not producer runtime."),
        "measurement_acquisition_and_review_support": group(
            [p for folder in ("stage", "environment", "controller", "policy", "integration") for p in (review / folder).glob("*.py")], root,
            "Root measurement/qualification, dependency acquisition, rehearsal and review support, including preserved superseded helpers; not the maintained policy runtime."),
        "installed_product_python": group(list((installed / "asof").rglob("*.py")) + list((installed / "tether").rglob("*.py")), root,
            "Full85-file installed project Python surface; includes unrelated therapeutic/study capabilities. Not the minimum comparator."),
        "inspect_upstream_python": group(list((installed / "inspect_ai").rglob("*.py")), root,
            "Full pinned upstream Inspect Python source, including unrelated providers/tools; excludes third-party dependencies/non-Python assets. Not a minimum equivalent port."),
    }
    reused = groups["reused_independent_validator"]
    expected = matrix["reused_validator"]
    for key in ("file_count", "bytes", "physical_lines"):
        if reused[key] != expected[key]:
            raise ValueError("Reused validator surface differs from pinned design")
    for actual, old in zip(reused["files"], sorted(expected["files"], key=lambda x: x["path"])):
        if actual["path"] != old["path"] or actual["sha256"] != old["sha256"]:
            raise ValueError("Reused validator code differs")
    report = {"schema_version": 1, "groups": groups, "helper_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "limitations": ["Physical source surface is descriptive, not complexity, development time, maintenance cost or proof of simplicity.",
                        "The nonblank_lines_not_starting_hash field is a lexical proxy: it includes docstring text but excludes even docstring lines beginning with '#'; it is not a token-accurate code count.",
                        "Full installed products/upstream contain unrelated features; group totals cannot establish minimal functional equivalence.",
                        "The common parent reuses TETHER process supervision and its imports. This is not a TETHER-free executable stack.",
                        "Native runtime port omits full eight-specialist scheduling and positive review retries; retain this functionality difference."]}
    with args.output.open("x", encoding="utf-8", newline="\n") as out:
        json.dump(report, out, indent=2, sort_keys=True)
        out.write("\n")
    print(json.dumps({key: {k: v for k, v in value.items() if k != "files"} for key, value in groups.items()}, indent=2))


if __name__ == "__main__":
    main()
