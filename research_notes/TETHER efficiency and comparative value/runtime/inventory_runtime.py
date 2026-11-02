"""Read-only runtime inventory and exact installed/source equality evidence."""
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
ROOT=Path(__file__).resolve().parents[3]
output=Path(sys.argv[1]);output.mkdir(parents=True,exist_ok=False)
def digest(payload):return hashlib.sha256(payload).hexdigest()
files=[]
for prefix in ("src/asof","packages/tether/src/tether"):
    for path in sorted((ROOT/prefix).rglob("*.py")):
        raw=path.read_bytes();tree=ast.parse(raw,filename=str(path))
        files.append(dict(path=path.relative_to(ROOT).as_posix(),sha256=digest(raw),bytes=len(raw),
            lines=len(raw.splitlines()),functions=sum(isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef)) for x in ast.walk(tree)),
            imports=[ast.unparse(x) for x in tree.body if isinstance(x,(ast.Import,ast.ImportFrom))]))
wheel=ROOT/"data/cache/tether-050-qualified-build/wheels/tether_target_agents-0.5.0-py3-none-any.whl"
with zipfile.ZipFile(wheel) as archive:
    members=[n for n in archive.namelist() if n.startswith("tether/") and n.endswith(".py")]
    matches={name:digest(archive.read(name))==digest((ROOT/"packages/tether/src"/name).read_bytes()) for name in members}
import asof,tether,importlib.metadata
installed_root=Path(asof.__file__).parent
engine_matches={row["path"]:digest((installed_root/Path(row["path"]).relative_to("src/asof")).read_bytes())==row["sha256"]
                for row in files if row["path"].startswith("src/asof/")}
result=dict(head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
    runtime_files=len(files),runtime_lines=sum(r["lines"] for r in files),all_ast_parsed=True,files=files,
    wheel=dict(path=str(wheel),sha256=digest(wheel.read_bytes()),source_member_matches=matches),
    engine_installed_source_matches=engine_matches,environment=dict(python=sys.version,interpreter=sys.executable,
        core=importlib.metadata.version("asof-target-agents"),facade=importlib.metadata.version("tether-target-agents")),
    tracked_runtime_diff=subprocess.check_output(["git","diff","--name-only","HEAD","--","src/asof","packages/tether/src/tether"],cwd=ROOT,text=True))
(output/"runtime_inventory.json").write_text(json.dumps(result,indent=2),encoding="utf-8")
print(json.dumps({key:result[key] for key in ("head","runtime_files","runtime_lines","all_ast_parsed","environment","tracked_runtime_diff")},indent=2))
print(json.dumps(dict(wheel_sha256=result["wheel"]["sha256"],wheel_members=len(matches),wheel_all_equal=all(matches.values()),
    engine_members=len(engine_matches),engine_all_equal=all(engine_matches.values())),indent=2))
