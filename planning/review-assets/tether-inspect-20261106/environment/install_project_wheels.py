"""Root-authorized exact local product wheels, new Inspect environment only."""
import importlib.util
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(Path(__file__).parent))
import acquire_environment_v2 as guard

target = ROOT/"data/cache/tether-inspect-env-attempt02"
guard.base.TARGET = target
guard.base.EVIDENCE = Path(__file__).parent/"attempt02"
local = target/"project-wheels"
local.mkdir(exist_ok=False)
pins = {
    "asof_target_agents-0.3.13-py3-none-any.whl": ("b7446a71636841fe4ba96c0f94db6a42028d4358c6e452c843d0f7224c870ef2", 316024),
    "tether_target_agents-0.5.2-py3-none-any.whl": ("8fa010170b5bff38fbc41cedaf877a0a2308edb2b649271a37fccf12f9822ac2", 46561),
}
proofs = []
for name, (expected, size) in pins.items():
    source = ROOT/"data/cache/tether-052-installed-qualification-attempt01/wheels"/name
    raw = source.read_bytes()
    if guard.base.digest(raw) != expected or len(raw) != size:
        raise ValueError("Qualified project wheel differs")
    with (local/name).open("xb") as stream:
        stream.write(raw)
    proofs.append({"filename": name, "sha256": expected, "bytes": size, "source": str(source),
                   "retained_copy": str(local/name)})
guard.base.publish(guard.base.EVIDENCE/"PROJECT-WHEELS.json", {"wheels": proofs, "third_party_lock_modified": False})
env = {k: v for k, v in os.environ.items() if k.upper() in
       {"SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "PATH", "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS"}}
env.update(TEMP=str(target/"tmp"), TMP=str(target/"tmp"), PIP_CONFIG_FILE=os.devnull, PYTHONNOUSERSITE="1")
python = str(target/"environment/Scripts/python.exe")
guard.run("05-project-wheels-offline", [python, "-I", "-B", "-m", "pip", "--isolated",
    "--disable-pip-version-check", "--no-input", "--no-cache-dir", "install", "--no-index", "--no-deps",
    "--no-compile", *[str(local/name) for name in pins]], env, 120)
guard.run("06-pip-check-with-products", [python, "-I", "-B", "-m", "pip", "--isolated", "check"], env, 60)
