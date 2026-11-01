"""Offline two-step sync/install against new fictional environments only."""
from datetime import datetime,timezone
import hashlib,json,os
from pathlib import Path
import shutil,subprocess,sys,time,uuid

ROOT=Path(__file__).resolve().parents[3]
CACHE=Path(r"C:\Users\zzric\AppData\Local\uv\cache")

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def run():
    base=ROOT/"data/cache"/("p09-uv-two-step-probe-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:6]);base.mkdir(exist_ok=False)
    monitored=(ROOT/"pyproject.toml",ROOT/"uv.lock",ROOT/".venv/pyvenv.cfg")
    before={str(p.relative_to(ROOT)):sha(p) for p in monitored}
    result=[]
    for label in ("positive","negative"):
        project=base/label;project.mkdir()
        for name in ("pyproject.toml","uv.lock","LICENSE"):shutil.copyfile(ROOT/name,project/name)
        package=project/"src/asof";package.mkdir(parents=True)
        (package/"__init__.py").write_text('"""Invented package for offline CI constraint enforcement."""\n',encoding="utf-8")
        constraints=ROOT/"paper/release/build-constraints.txt"
        if label=="negative":
            constraints=base/"impossible-build-constraints.txt";constraints.write_text("setuptools==999999\n",encoding="utf-8")
        target=project/".venv"
        environment=dict(os.environ,UV_CACHE_DIR=str(CACHE),UV_PROJECT_ENVIRONMENT=str(target),UV_OFFLINE="1",UV_PYTHON_DOWNLOADS="never",UV_LINK_MODE="copy")
        commands=[
            ["uv","sync","--offline","--locked","--no-install-project","--project",str(project),"--python",sys.executable],
            ["uv","pip","install","--offline","--no-deps","--python",str(target/"Scripts/python.exe"),"--editable",str(project),"--build-constraints",str(constraints)]
        ]
        phases=[];started=time.monotonic()
        for i,command in enumerate(commands):
            p=subprocess.run(command,cwd=project,env=environment,text=True,capture_output=True,timeout=120)
            stem=base/(label+"-"+str(i+1))
            Path(str(stem)+".stdout.txt").write_text(p.stdout,encoding="utf-8");Path(str(stem)+".stderr.txt").write_text(p.stderr,encoding="utf-8")
            phases.append(dict(command=command,exit_code=p.returncode,stdout_sha256=sha(Path(str(stem)+".stdout.txt")),stderr_sha256=sha(Path(str(stem)+".stderr.txt"))))
            if i==0 and p.returncode:break
        wheels=list((target/"Lib/site-packages").glob("asof_target_agents-0.3.11.dist-info/WHEEL"))
        wheel=wheels[0].read_text() if wheels else None
        passed=len(phases)==2 and phases[0]["exit_code"]==0 and (phases[1]["exit_code"]==0 and wheel is not None and "Generator: setuptools (84.0.0)" in wheel if label=="positive" else phases[1]["exit_code"]!=0 and wheel is None and "999999" in p.stderr)
        result.append(dict(label=label,passed=passed,phases=phases,wall_seconds=time.monotonic()-started,editable_dist_info_wheel=wheel,fixture_lock_unchanged=sha(project/"uv.lock")==before["uv.lock"]))
    after={str(p.relative_to(ROOT)):sha(p) for p in monitored}
    return dict(schema="p09.uv_two_step_constraint_probe.v3",status="PASS" if all(r["passed"] and r["fixture_lock_unchanged"] for r in result) and before==after else "FAIL",probe_root=str(base),uv_version=subprocess.run(["uv","--version"],capture_output=True,text=True,check=True).stdout.strip(),
        build_constraints_sha256=sha(ROOT/"paper/release/build-constraints.txt"),project_inputs_before=before,project_inputs_after=after,results=result,network_calls=0,provider_source_reads=0,
        project_environment_targeted=False,scope="Existing C: offline cache; new exclusive D: fictional environments. Exact copied root pyproject/uv.lock, invented one-file package. No actual provider sources.")

if __name__=="__main__":
    report=run();p=Path(__file__).with_name("UV-TWO-STEP-CONSTRAINT-PROBE-v3.json")
    with p.open("xb") as s:s.write(json.dumps(report,indent=2).encode()+b"\n")
    print(json.dumps(report,indent=2))
