"""Bounded fresh mock qualification, preserving the first failed smoke."""
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import acquire_environment_v2 as guard

target = guard.base.ROOT/"data/cache/tether-inspect-env-attempt02"
guard.base.TARGET = target
guard.base.EVIDENCE = Path(__file__).parent/"attempt02"
env = {k: v for k, v in os.environ.items() if k.upper() in
       {"SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "PATH", "PROCESSOR_ARCHITECTURE", "NUMBER_OF_PROCESSORS"}}
env.update(TEMP=str(target/"tmp"), TMP=str(target/"tmp"), PIP_CONFIG_FILE=os.devnull,
           PYTHONNOUSERSITE="1", PYTHON_DOTENV_DISABLED="1")
guard.run("08-mock-qualification", [str(target/"environment/Scripts/python.exe"), "-I", "-B",
    str(Path(__file__).with_name("mock_qualification_v2.py"))], env, 90)
