"""Retrospective SAME8 on preserved v1; not historical-before-code evidence."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from shared_owner_actual_suite_runner_v2 import run
if __name__=='__main__':
 raise SystemExit(run(1,False,'SHARED-OWNER-FIVE-REGRESSIONS-BEFORE-v2.json',Path(__file__).resolve()))
