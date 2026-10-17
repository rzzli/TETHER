"""Prepare an exclusive recovery bundle, or test assets downloaded from private hosting.

No upload, deletion, database restart or credential collection is performed here.
"""
from pathlib import Path
import argparse
import hashlib
import json
import sqlite3
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[3]
EXTERNAL=Path('E:/projects_data/drug_target_agents_data')


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()


def write(path,value):
    with path.open('x',encoding='utf-8',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')


def prepare(workspace,destination):
    workspace=Path(workspace).resolve();destination=Path(destination).resolve()
    if not workspace.is_relative_to((ROOT/'data/benchmark/cohorts').resolve()):raise ValueError('Unexpected workspace')
    if not destination.is_relative_to((EXTERNAL/'backups').resolve()):raise ValueError('Use authorized backup root')
    destination.mkdir(parents=True,exist_ok=False)
    policy=json.loads((ROOT/'planning/protocols/registry-sizing-v0.4.json').read_text(encoding='utf-8'))
    frames=json.loads((workspace/'frames.json').read_text(encoding='utf-8'))
    sources={Path(x['path']).resolve() for x in frames['snapshots']}
    for folder in [workspace/'cohort-v04',workspace/'audit-v04']:
        sources.update(p for p in folder.rglob('*') if p.is_file())
    sources.update(p for p in workspace.iterdir() if p.is_file())
    for folder in [workspace,ROOT/'data/benchmark/cohorts/registry-sizing-20261017T200901Z',
                   ROOT/'data/benchmark/cohorts/registry-sizing-20261017T202534Z']:
        for p in folder.rglob('*'):
            if p.is_file() and p.parent.name in {x['date'] for x in policy['snapshots']} and p.name!='frame.stdout.log':sources.add(p)
    for name in ['cohort','cohort-final','cohort-reviewed','audit','audit-reviewed']:
        # Diagnostic accounting is retained, without duplicating multi-GB indices.
        folder=workspace/name
        for leaf in ['execution.json','resources.json','summary.json','technical-audit.json','failure.json']:
            if (folder/leaf).exists():sources.add(folder/leaf)
    sources.update(Path(x['path']).resolve() for x in policy['mapping_inputs'])
    entries=[]
    with zipfile.ZipFile(destination/'registry-evidence.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as archive:
        for p in sorted(sources):
            if any(x in {'.git','.local-postgres-secrets','pgdata','__pycache__'} for x in p.parts) or any(x in p.name.lower() for x in ['password','credential','signed_urls','secrets']):raise ValueError('Unsafe backup member')
            if p.is_relative_to(ROOT):name='project/'+p.relative_to(ROOT).as_posix()
            elif p.is_relative_to(EXTERNAL):name='external/'+p.relative_to(EXTERNAL).as_posix()
            else:raise ValueError('Source outside approved roots')
            initial=p.stat();h=hashlib.sha256();size=0
            with p.open('rb') as src,archive.open(name,'w',force_zip64=True) as dst:
                for block in iter(lambda:src.read(4*1024*1024),b''):dst.write(block);h.update(block);size+=len(block)
            final=p.stat()
            if (initial.st_size,initial.st_mtime_ns)!=(final.st_size,final.st_mtime_ns):raise ValueError('Changing source')
            entries.append({'archive_path':name,'source':str(p),'bytes':size,'sha256':h.hexdigest()})
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    subprocess.run(['git','bundle','create',str(destination/'repository.bundle'),'--all'],cwd=ROOT,check=True,capture_output=True)
    write(destination/'file-manifest.json',{'role':'evaluation_only','code_commit':head,'files':entries,
        'excluded':'Original AACT ZIPs/dumps/database pages and credentials; baseline evidence has its own release.'})
    write(destination/'asset-hashes.json',{'code_commit':head,'assets':{name:{'bytes':(destination/name).stat().st_size,'sha256':digest(destination/name)}
        for name in ['registry-evidence.zip','repository.bundle','file-manifest.json']}})
    print(json.dumps({'files':len(entries),'source_bytes':sum(e['bytes'] for e in entries),'archive_bytes':(destination/'registry-evidence.zip').stat().st_size,
        'asset_index_sha256':digest(destination/'asset-hashes.json'),'code_commit':head}))


def restore(download,destination,expected):
    download=Path(download).resolve();destination=Path(destination).resolve()
    if not destination.is_relative_to((EXTERNAL/'backups').resolve()):raise ValueError('Use authorized backup root')
    if digest(download/'asset-hashes.json')!=expected:raise ValueError('Wrong independently retained asset index')
    assets=json.loads((download/'asset-hashes.json').read_text(encoding='utf-8'))
    for name,item in assets['assets'].items():
        if name not in {'registry-evidence.zip','repository.bundle','file-manifest.json'}:raise ValueError('Unexpected asset')
        if digest(download/name)!=item['sha256'] or (download/name).stat().st_size!=item['bytes']:raise ValueError('Changed asset')
    destination.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((download/'file-manifest.json').read_text(encoding='utf-8'));seen=set()
    with zipfile.ZipFile(download/'registry-evidence.zip') as archive:
        if len(archive.infolist())!=len(manifest['files']):raise ValueError('Archive membership mismatch')
        for e in manifest['files']:
            path=(destination/e['archive_path']).resolve()
            if not path.is_relative_to(destination) or path in seen:raise ValueError('Unsafe/duplicate member')
            seen.add(path);path.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(e['archive_path']) as src,path.open('xb') as dst:
                for block in iter(lambda:src.read(4*1024*1024),b''):dst.write(block)
            if digest(path)!=e['sha256'] or path.stat().st_size!=e['bytes']:raise ValueError('Restored file mismatch')
    bundle=download/'repository.bundle'
    subprocess.run(['git','clone','--no-hardlinks',str(bundle),str(destination/'repository-restore')],check=True,capture_output=True)
    restored=subprocess.check_output(['git','rev-parse','HEAD'],cwd=destination/'repository-restore',text=True).strip()
    if restored!=assets['code_commit']:raise ValueError('Code restore differs')
    subprocess.run(['git','fsck','--full'],cwd=destination/'repository-restore',check=True,capture_output=True)
    dbs=[p for p in seen if p.name=='cohort.sqlite']
    if len(dbs)!=1:raise ValueError('Canonical SQLite index missing')
    db=sqlite3.connect('file:'+dbs[0].as_posix()+'?mode=ro',uri=True)
    if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Restored SQLite integrity failed')
    observations=db.execute('SELECT COUNT(*) FROM observations').fetchone()[0];db.close()
    report={'downloaded_asset_hashes':'passed','all_archived_files_restored_and_rehashed':len(seen),
        'code_commit':restored,'git_fsck':'passed','sqlite_integrity':'passed','restored_source_observations':observations,
        'source_bytes':sum(e['bytes'] for e in manifest['files']),'asset_index_sha256':expected,
        'coverage':'Registry frames, canonical index/outputs/audit, mapping inputs and diagnostic metadata; original full archives/databases excluded.'}
    write(destination/'restore-report.json',report);print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('prepare');a.add_argument('--workspace',type=Path,required=True);a.add_argument('--destination',type=Path,required=True)
    a=sub.add_parser('restore');a.add_argument('--download',type=Path,required=True);a.add_argument('--destination',type=Path,required=True);a.add_argument('--expected-index-sha256',required=True)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.workspace,a.destination)
    else:restore(a.download,a.destination,a.expected_index_sha256)
