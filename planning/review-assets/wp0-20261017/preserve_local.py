"""Create/test an exclusive local recovery copy. No external transmission or deletion."""
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[3]
EXTERNAL=Path('E:/projects_data/drug_target_agents_data')


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()


def preserve(destination):
    destination=Path(destination).resolve()
    if not destination.is_relative_to((EXTERNAL/'backups').resolve()):
        raise ValueError('Destination must be within authorized E project backups')
    destination.mkdir(parents=True,exist_ok=False)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    subprocess.run(['git','bundle','create',str(destination/'repository.bundle'),'--all'],cwd=ROOT,check=True)
    subprocess.run(['git','bundle','verify',str(destination/'repository.bundle')],cwd=ROOT,check=True,capture_output=True)
    sources=[]
    for folder in [ROOT/'data/benchmark',ROOT/'data/derived']:
        for p in sorted(folder.rglob('*')):
            if p.is_file() and not any(x in {'__pycache__','.local-postgres-secrets','private'} for x in p.parts):
                if any(word in p.name.lower() for word in ['password','credential','secrets','signed_urls']):
                    raise ValueError('Sensitive filename in backup scope; review before copying')
                sources.append(('project/'+p.relative_to(ROOT).as_posix(),p))
    # Retain external proof manifests and sanitized restore-evidence copies only;
    # exclude originals, databases, credentials and large raw genetics matrices.
    for current,dirs,files in os.walk(EXTERNAL/'derived'):
        dirs[:]=[d for d in dirs if d not in {'pgdata','extracted','.local-postgres-secrets','__pycache__'}]
        folder=Path(current)
        for name in sorted(files):
            if name=='evidence-manifest.json' or 'sealed-evidence' in folder.parts:
                p=folder/name;sources.append(('external/'+p.relative_to(EXTERNAL).as_posix(),p))
    entries=[]
    with zipfile.ZipFile(destination/'evidence.zip','x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as archive:
        for name,p in sources:
            initial=p.stat();h=hashlib.sha256();size=0
            with p.open('rb') as source,archive.open(name,'w',force_zip64=True) as target:
                for block in iter(lambda:source.read(4*1024*1024),b''):
                    target.write(block);h.update(block);size+=len(block)
            final=p.stat()
            if (initial.st_size,initial.st_mtime_ns)!=(final.st_size,final.st_mtime_ns) or size!=initial.st_size:
                raise ValueError('Source changed during recovery copy: '+str(p))
            entries.append({'archive_path':name,'source':str(p),'bytes':size,'sha256':h.hexdigest()})
    with zipfile.ZipFile(destination/'evidence.zip') as archive:
        if len(archive.infolist())!=len(entries):raise ValueError('Backup membership differs')
        for row in entries:
            h=hashlib.sha256();size=0
            with archive.open(row['archive_path']) as f:
                for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block);size+=len(block)
            if h.hexdigest()!=row['sha256'] or size!=row['bytes']:raise ValueError('Backup verification failed')
        restore=destination/'restore-test';restore.mkdir()
        prefix='project/data/benchmark/cohorts/advancement-rules-20261017T152107Z/'
        restored=[]
        for row in entries:
            if row['archive_path'].startswith(prefix):
                relative=Path(row['archive_path'][len(prefix):]);target=(restore/relative).resolve()
                if not target.is_relative_to(restore.resolve()):raise ValueError('Unsafe archive path')
                target.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(row['archive_path']) as src,target.open('xb') as dst:
                    for block in iter(lambda:src.read(1024*1024),b''):dst.write(block)
                if digest(target)!=row['sha256']:raise ValueError('Restore digest differs')
                restored.append(relative.as_posix())
        manifest=json.loads((restore/'evidence-manifest.json').read_text(encoding='utf-8'))
        for row in manifest['files']:
            if digest(restore/row['path'])!=row['sha256']:raise ValueError('Restored milestone seal differs')
    subprocess.run(['git','clone','--no-hardlinks',str(destination/'repository.bundle'),str(destination/'repository-restore-test')],check=True,capture_output=True)
    clone_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=destination/'repository-restore-test',text=True).strip()
    if clone_commit!=commit:raise ValueError('Restored code commit differs')
    report={'created_at_utc':datetime.now(timezone.utc).isoformat(),'code_commit':commit,'code_restore_commit':clone_commit,
        'local_only':True,'off_machine_backup':False,'source_files':len(entries),'source_bytes':sum(r['bytes'] for r in entries),
        'archive_bytes':(destination/'evidence.zip').stat().st_size,'archive_sha256':digest(destination/'evidence.zip'),
        'git_bundle_sha256':digest(destination/'repository.bundle'),'all_archive_entries_rehashed':True,
        'milestone_restored_files':len(restored),'restored_seal_files_checked':len(manifest['files']),
        'excluded':'Bulk raw archives, PostgreSQL pages/credentials, large external scientific payloads and off-machine protection',
        'entries':entries}
    (destination/'recovery-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in report.items() if k!='entries'}))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--destination',required=True,type=Path)
    preserve(p.parse_args().destination)
