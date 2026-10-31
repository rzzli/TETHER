"""Read public tag metadata without credentials, clone, checkout or model execution."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
log=ROOT/'runs/r07-native-diagnostic-20261026T165505Z/server.stderr.log'
lines=log.read_text(encoding='utf-8').splitlines()
build_line=next(line for line in lines if 'build 11717 (' in line)
assert '848bbda90' in build_line and 'Clang 20.1.8' in build_line
git=shutil.which('git');assert git
argv=[git,'-c','credential.helper=','-c','credential.interactive=never','-c','core.askPass=',
    '-c','http.lowSpeedLimit=1','-c','http.lowSpeedTime=10','ls-remote',
    'https://github.com/ggml-org/llama.cpp.git','refs/tags/b11717','refs/tags/b11717^{}']
report=dict(schema_version=1,recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    argv=argv,credentials_disabled=True,repository_clone=False,checkout=False,
    runtime_startup_log=dict(path=log.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(log.read_bytes()).hexdigest(),build_line=build_line),
    runtime_reported_short_commit='848bbda90',runtime_reported_compiler='Clang20.1.8 Windows x86_64',
    tag='b11717',model_calls=0,servers=0,new_runtime_downloads=0)
try:
    result=subprocess.run(argv,cwd=HERE,env=dict(os.environ,GIT_TERMINAL_PROMPT='0'),capture_output=True,timeout=25)
    (HERE/'TAG-STDOUT-authorized.txt').write_bytes(result.stdout)
    (HERE/'TAG-STDERR-authorized.txt').write_bytes(result.stderr)
    report['exit_code']=result.returncode
    if result.returncode:
        report.update(status='tag_resolution_failed',full_source_commit=None)
    else:
        refs={}
        for line in result.stdout.decode('ascii').splitlines():
            digest,name=line.split('\t');assert re.fullmatch('[0-9a-f]{40}',digest)
            refs[name]=digest
        assert set(refs) in ({'refs/tags/b11717'},{'refs/tags/b11717','refs/tags/b11717^{}'})
        commit=refs.get('refs/tags/b11717^{}',refs['refs/tags/b11717'])
        assert commit.startswith('848bbda90')
        report.update(status='public_tag_matches_retained_runtime_short_commit',refs=refs,full_source_commit=commit,
            build_equivalence='Commit prefix matched; compiler flags/dependency/build equivalence not established')
except subprocess.TimeoutExpired as error:
    (HERE/'TAG-STDOUT-authorized.txt').write_bytes(error.stdout or b'')
    (HERE/'TAG-STDERR-authorized.txt').write_bytes(error.stderr or b'')
    report.update(status='tag_resolution_timeout',full_source_commit=None)
with (HERE/'SOURCE-TAG-IDENTITY-authorized.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report))
