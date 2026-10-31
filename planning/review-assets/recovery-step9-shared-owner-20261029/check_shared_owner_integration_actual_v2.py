"""Coherent corrected v2 actual48 plus SAME8, frozen expectations unchanged."""
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from shared_owner_actual_suite_runner_v2 import run
if __name__=='__main__':
 raise SystemExit(run(2,True,'SHARED-OWNER-INTEGRATION-ACTUAL-PROOF-v2.json',Path(__file__).resolve()))
