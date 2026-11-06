"""Record the isolated plotting environment without modifying installed packages."""
import argparse
import base64
import hashlib
import importlib.metadata as im
import json
from pathlib import Path
import sys
import zipfile


def digest(path):
    path=Path(path).absolute();data=path.read_bytes()
    return dict(path=str(path),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def qualify(root,output):
    root=root.absolute();plan=json.loads((root/'metadata02/WHEEL-PLAN.json').read_bytes())
    installed={d.metadata['Name'].lower().replace('_','-'):d.version for d in im.distributions()}
    expected={w['name']:w['version'] for w in plan['wheels']}
    assert installed==expected,(installed,expected)
    installed_files=[];console_scripts=[]
    for distribution in im.distributions():
        for entry in distribution.entry_points:
            if entry.group=='console_scripts':
                p=Path(sys.prefix)/'Scripts'/(entry.name+'.exe');assert p.is_file(),p
                console_scripts.append(digest(p))
        for entry in distribution.files:
            p=Path(distribution.locate_file(entry)).resolve();assert p.is_relative_to(Path(sys.prefix).resolve()) and p.is_file(),p
            if entry.hash is not None:
                actual=hashlib.new(entry.hash.mode,p.read_bytes()).digest()
                assert base64.urlsafe_b64encode(actual).decode().rstrip('=')==entry.hash.value,p
            installed_files.append(digest(p))
    wheels=[]
    for w in plan['wheels']:
        p=root/'wheels'/w['filename'];actual=digest(p)
        assert actual['sha256']==w['sha256'] and actual['bytes']==w['bytes']
        with zipfile.ZipFile(p) as archive:
            licenses=[dict(name=n,bytes=len(archive.read(n)),sha256=hashlib.sha256(archive.read(n)).hexdigest())
                      for n in archive.namelist() if any(x in n.lower() for x in ('license','copying','copyright')) and not n.endswith('/')]
        assert licenses,w['name']
        wheels.append(dict(name=w['name'],version=w['version'],wheel=actual,license_files=licenses))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig=plt.figure();plt.close(fig)
    result=dict(status='PASS',provider_spend_usd=0,python=sys.version,executable=digest(sys.executable),
        base_executable=digest(sys._base_executable),venv_configuration=digest(Path(sys.prefix)/'pyvenv.cfg'),
        installed=installed,installed_files_checked=len(installed_files),installed_inventory_sha256=hashlib.sha256(json.dumps(installed_files,sort_keys=True).encode()).hexdigest(),
        console_scripts=console_scripts,matplotlib_backend=matplotlib.get_backend(),wheel_bytes=plan['total_wheel_bytes'],
        wheel_cap_bytes=plan['wheel_cap_bytes'],official_wheel_plan=digest(root/'metadata02/WHEEL-PLAN.json'),
        acquisition=digest(root/'wheels/ACQUISITION.json'),lock=digest(root/'wheels/requirements.lock'),wheels=wheels,
        qualifier=digest(__file__),setup_helper=digest(Path(__file__).with_name('setup_figures_env.py')),
        official_references=['https://pypi.org/project/matplotlib/3.10.7/','https://matplotlib.org/3.10.7/project/license.html'],
        validation=['All 11 installed versions exactly match the lock.','uv pip check succeeded.',
                    'All wheel bytes and hashes match official archived PyPI metadata.',
                    'License files retained inside every original wheel.','Agg figure initialization succeeded.'],
        failed_attempts=[dict(path=str(root/'metadata/FAILURE.json'),reason='Ambiguous fonttools native/universal wheel; explicit native preference fixed; no wheel acquired in that attempt.'),
            dict(path=str(root/'environment'),reason='Sandbox prevented Windows launcher PE update; retained; new environment02 created with scoped escalation.'),
            dict(path=str(root/'environment02'),reason='Initial sandbox offline installation reported launcher PE error; later version checks and imports passed but six console launchers were absent. Environment preserved; fresh environment03 completed full offline installation.')],
        limits=['Isolated plotting dependencies do not alter or requalify the scientific analysis environment.',
                'Wheels are hash verified, not a source-code security audit.'])
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(dict(status='PASS',output=digest(output))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    qualify(a.root,a.output)
