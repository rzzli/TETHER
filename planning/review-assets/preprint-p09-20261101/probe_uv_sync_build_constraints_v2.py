"""Isolated offline fictional sync probe; never targets the project environment."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[3]
CACHE=Path(r"C:\Users\zzric\AppData\Local\uv\cache")


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def run():
    base=ROOT/"data/cache"/("p09-uv-sync-config-probe-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:6])
    base.mkdir(exist_ok=False)
    config=ROOT/"paper/release/uv-build-constraints.toml"
    before={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/"pyproject.toml",ROOT/"uv.lock",ROOT/".venv/pyvenv.cfg")}
    version=subprocess.run(["uv","--version"],capture_output=True,text=True,check=True).stdout.strip()
    reports=[]
    for label in ("positive","negative"):
        project=base/label;project.mkdir()
        for name in ("pyproject.toml","uv.lock","LICENSE"):
            shutil.copyfile(ROOT/name,project/name)
        package=project/"src/asof";package.mkdir(parents=True)
        (package/"__init__.py").write_text('"""Invented empty package; build-constraint probe only."""\n',encoding="utf-8")
        selected=config
        if label=="negative":
            selected=base/"impossible-build-constraint.toml"
            selected.write_text('build-constraint-dependencies = ["setuptools==999999"]\n',encoding="utf-8")
        target=project/".venv"
        environment=dict(os.environ,UV_CACHE_DIR=str(CACHE),UV_PROJECT_ENVIRONMENT=str(target),UV_OFFLINE="1",UV_PYTHON_DOWNLOADS="never")
        command=["uv","--config-file",str(selected),"sync","--offline","--locked","--project",str(project),"--python",sys.executable]
        started=time.monotonic()
        outcome=subprocess.run(command,cwd=ROOT,env=environment,capture_output=True,text=True,timeout=120)
        (base/(label+".stdout.txt")).write_text(outcome.stdout,encoding="utf-8")
        (base/(label+".stderr.txt")).write_text(outcome.stderr,encoding="utf-8")
        wheels=list((target/"Lib/site-packages").glob("asof_target_agents-0.3.11.dist-info/WHEEL"))
        wheel=wheels[0].read_text() if wheels else None
        passed=(outcome.returncode==0 and wheel is not None and "Generator: setuptools (84.0.0)" in wheel) if label=="positive" else (
            outcome.returncode!=0 and wheel is None and "999999" in outcome.stderr)
        reports.append(dict(label=label,command=command,exit_code=outcome.returncode,wall_seconds=time.monotonic()-started,
            expected_constraint="setuptools==84.0.0" if label=="positive" else "setuptools==999999",passed=passed,
            editable_dist_info_wheel=wheel,fixture_lock_unchanged=sha(project/"uv.lock")==before["uv.lock"],
            stdout_sha256=sha(base/(label+".stdout.txt")),stderr_sha256=sha(base/(label+".stderr.txt"))))
    after={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/"pyproject.toml",ROOT/"uv.lock",ROOT/".venv/pyvenv.cfg")}
    return dict(schema="p09.uv_sync_build_constraint_probe.v1",status="PASS" if all(r["passed"] and r["fixture_lock_unchanged"] for r in reports) and before==after else "FAIL",
        uv_version=version,config_path="paper/release/uv-build-constraints.toml",config_sha256=sha(config),probe_root=str(base),
        cache_scope="Existing local C: uv cache only; offline and Python downloads disabled",project_inputs_before=before,project_inputs_after=after,
        project_environment_targeted=False,reports=reports,network_calls=0,provider_source_reads=0)


if __name__=="__main__":
    result=run(); output=Path(__file__).with_name("UV-SYNC-BUILD-CONSTRAINT-PROBE-v2.json")
    with output.open("xb") as stream:stream.write(json.dumps(result,indent=2).encode()+b"\n")
    print(json.dumps(result,indent=2))
