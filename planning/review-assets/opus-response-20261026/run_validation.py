"""Run existing full validation with writable, workspace-local temporary storage."""
import faulthandler
import os
import runpy
import sys
import tempfile
from pathlib import Path

project = Path(__file__).resolve().parents[3]
temporary = project / 'data/cache/opus-response-validation-tmp-20261026'
temporary.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(temporary)
os.environ['TMP'] = os.environ['TEMP'] = str(temporary)
os.environ['UV_OFFLINE'] = '1'
os.environ['PATH'] = str(project / 'data/cache/powershell-7.4.6-portable') + os.pathsep + os.environ['PATH']
sys.path.insert(0, str(project))
faulthandler.dump_traceback_later(180, repeat=True)
report_name = 'opus-response-full-validation-unsandboxed-20261026.json' if '--unsandboxed-report' in sys.argv else 'opus-response-full-validation-workspace-20261026.json'
sys.argv = ['tools/validate.py', '--mode', 'full', '--package', '--report',
            str(project / 'data/cache' / report_name)]
runpy.run_path(str(project / 'tools/validate.py'), run_name='__main__')
