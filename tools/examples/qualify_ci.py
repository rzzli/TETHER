"""Installed example qualification; network is explicit and fixed-source only."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time


def qualify(output: Path, *, source_root: Path | None = None, allow_network: bool = False) -> dict[str, object]:
    if source_root is None and not allow_network:
        raise ValueError('Supply existing --source-root or explicitly authorize --allow-network')
    if source_root is not None and allow_network:
        raise ValueError('Choose existing originals or bounded retrieval, not both')
    # Canonicalize only the caller-selected scratch parent (macOS /var alias).
    output=output.absolute().parent.resolve(strict=True)/output.name
    output.mkdir()
    reports=output/'reports';reports.mkdir()
    scratch=output/'scratch';scratch.mkdir()
    environment=dict(os.environ,TMPDIR=str(scratch),TEMP=str(scratch),TMP=str(scratch),PYTHONDONTWRITEBYTECODE='1')
    environment.pop('PYTHONPATH',None)
    environment.pop('PYTHONHOME',None)
    here=Path(__file__).resolve().parent
    steps=[]
    def run(name, script, arguments):
        started=time.monotonic()
        try:
            result=subprocess.run([sys.executable,'-I','-B',str(here/script),*map(str,arguments)],
                env=environment,capture_output=True,timeout=600)
        except subprocess.TimeoutExpired as error:
            (reports/(name+'.stdout')).write_bytes(error.stdout or b'')
            (reports/(name+'.stderr')).write_bytes(error.stderr or b'')
            steps.append(dict(name=name,status='timeout',elapsed_seconds=time.monotonic()-started))
            raise
        (reports/(name+'.stdout')).write_bytes(result.stdout)
        (reports/(name+'.stderr')).write_bytes(result.stderr)
        steps.append(dict(name=name,returncode=result.returncode,elapsed_seconds=time.monotonic()-started))
        (reports/'progress.json').write_text(json.dumps(steps,indent=2),encoding='utf-8')
        if result.returncode:
            raise RuntimeError(name+' failed; inspect retained logs')
        return json.loads(result.stdout)
    try:
        if source_root is None:
            source_root=output/'download'
            run('download','fetch_il6r.py',['--output',source_root,'--allow-network'])
        inputs=output/'inputs'
        prepared=run('prepare','prepare_il6r.py',['--source-root',source_root,'--output',inputs])
        native,bundle,reading=output/'run',output/'bundle',output/'reading'
        result=run('execute','run_offline.py',['--inputs',inputs,'--output',native,'--bundle-output',bundle,
                                           '--frame-sha256',prepared['frame_sha256']])
        if result['elapsed_seconds']>=300:
            raise RuntimeError('Run/export/verification exceeded five minutes')
        audit=run('source-audit','audit_il6r.py',['--inputs',inputs,'--run-dir',native,'--output',reading,
            '--receipt-sha256',result['receipt_sha256'],'--engine-receipt-sha256',result['engine_receipt_sha256']])
        parked=output/'inputs-unavailable'
        moved=output/'relocated-Ω'
        for path in (inputs,parked,bundle,moved):
            if not path.is_relative_to(output) or path==output:
                raise ValueError('Move outside owned qualification output')
        if parked.exists() or moved.exists():
            raise ValueError('Unexpected relocation destination exists')
        bundle.rename(moved)
        inputs.rename(parked)
        try:
            if inputs.exists() or bundle.exists():
                raise RuntimeError('Staged original paths still exist')
            from tether.api import BundleArtifact, verify_bundle
            replay=verify_bundle(BundleArtifact(moved,result['manifest_sha256']))
        finally:
            if inputs.exists():
                raise RuntimeError('Unexpected new input directory; refusing to overwrite')
            parked.rename(inputs)
        for name in ('reading-view.html','reading-view.json','audit.json'):
            shutil.copyfile(reading/name,reports/name)
        report=dict(status='passed',steps=steps,python=sys.version,platform=sys.platform,
            prepared=prepared,execution=result,source_audit=audit,relocated=replay,
            staged_input_paths_unavailable_during_replay=True,network_enabled=allow_network,
            scientific_validation='not_established',provider_spending_usd=0)
    except BaseException as error:
        report=dict(status='failed',steps=steps,error_type=type(error).__name__,error=str(error),
                    automatic_retry=False,scientific_validation='not_established')
        (reports/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        raise
    (reports/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--source-root',type=Path)
    parser.add_argument('--allow-network',action='store_true')
    args=parser.parse_args()
    result=qualify(args.output,source_root=args.source_root,allow_network=args.allow_network)
    print(json.dumps(dict(status=result['status'],report=str(args.output/'reports/report.json'))))
