"""Isolated, bounded PyPI wheel acquisition for SC04 figures; no installation."""
import argparse
from datetime import datetime,timezone
import hashlib,json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,urlopen

PINS={'matplotlib':'3.10.7','contourpy':'1.3.3','cycler':'0.12.1','fonttools':'4.60.1','kiwisolver':'1.4.9',
      'numpy':'2.3.4','packaging':'25.0','pillow':'12.0.0','pyparsing':'3.2.5','python-dateutil':'2.9.0.post0','six':'1.17.0'}
CAP=250*1024**2

def need(value,message):
 if not value:raise ValueError(message)
def sha(value):return hashlib.sha256(value).hexdigest()
def write(path,value):
 with Path(path).open('xb') as stream:stream.write(json.dumps(value,indent=2,sort_keys=True).encode()+b'\n')
def fetch(url,path,limit):
 need(urlsplit(url).scheme=='https' and urlsplit(url).netloc in ('pypi.org','files.pythonhosted.org'),'Approved PyPI origin')
 start=datetime.now(timezone.utc).isoformat();size=0;digest=hashlib.sha256()
 with urlopen(Request(url,headers={'User-Agent':'TETHER-public-research-figures/1.0','Accept-Encoding':'identity'}),timeout=30) as response:
  need(response.status==200 and urlsplit(response.url).scheme=='https' and urlsplit(response.url).netloc in ('pypi.org','files.pythonhosted.org'),'Approved PyPI response')
  headers=dict(response.headers);need(int(response.headers.get('Content-Length','0'))<=limit,'Response content length exceeds cap')
  with Path(path).open('xb') as stream:
   while True:
    part=response.read(min(65536,limit-size+1))
    if not part:break
    size+=len(part);need(size<=limit,'Transfer byte cap');stream.write(part);digest.update(part)
 return dict(url=url,final_url=response.url,http_status=200,headers=headers,bytes=size,sha256=digest.hexdigest(),started_at_utc=start,completed_at_utc=datetime.now(timezone.utc).isoformat(),retries=0)

def metadata(output):
 output.mkdir(parents=True,exist_ok=False);selected=[];receipts=[]
 try:
  for name,version in PINS.items():
   file=output/(name+'.json');receipt=fetch(f'https://pypi.org/pypi/{name}/{version}/json',file,2*1024**2);receipts.append(receipt)
   write(output/(name+'.receipt.json'),receipt);data=json.loads(file.read_bytes());need(data['info']['version']==version,'Pinned release identity')
   candidates=[f for f in data['urls'] if f['packagetype']=='bdist_wheel' and not f['yanked'] and
    (f['filename'].endswith('-cp311-cp311-win_amd64.whl') or f['filename'].endswith('-py3-none-any.whl') or f['filename'].endswith('-py2.py3-none-any.whl'))]
   native=[f for f in candidates if f['filename'].endswith('-cp311-cp311-win_amd64.whl')]
   candidates=native or candidates
   need(len(candidates)==1,'Unambiguous preferred Python3.11Windows64 or universalwheel for '+name)
   f=candidates[0];need(Path(f['filename']).name==f['filename'],'Wheel filename')
   selected.append(dict(name=name,version=version,filename=f['filename'],url=f['url'],bytes=f['size'],sha256=f['digests']['sha256'],
    upload_time=f['upload_time_iso_8601'],requires_python=f['requires_python'],requires_dist=data['info']['requires_dist'],
    license=data['info'].get('license'),license_expression=data['info'].get('license_expression'),project_urls=data['info'].get('project_urls')))
  total=sum(f['bytes'] for f in selected);need(total<=CAP,'Aggregatewheel acquisition cap')
  plan=dict(status='metadata_verified',platform='CPython3.11Windowsamd64',wheels=selected,total_wheel_bytes=total,wheel_cap_bytes=CAP,
   metadata_bytes=sum(r['bytes'] for r in receipts),provider_cost_usd=0,automatic_retry=False)
  write(output/'WHEEL-PLAN.json',plan);print(json.dumps(dict(status=plan['status'],wheels=len(selected),total_wheel_bytes=total)))
 except BaseException as error:
  write(output/'FAILURE.json',dict(stage='official_metadata',error_type=type(error).__name__,captured_responses=len(receipts),automatic_retry=False));raise

def wheels(plan_path,output):
 plan=json.loads(plan_path.read_bytes());need(plan['status']=='metadata_verified' and plan['total_wheel_bytes']==sum(w['bytes'] for w in plan['wheels'])<=CAP,'Pinned bounded wheelplan')
 output.mkdir(parents=True,exist_ok=False);receipts=[]
 try:
  for wheel in plan['wheels']:
   path=output/wheel['filename'];need(path.parent==output and not path.exists(),'Fresh single wheel path')
   receipt=fetch(wheel['url'],path,wheel['bytes']);receipts.append(receipt)
   need(receipt['bytes']==wheel['bytes'] and receipt['sha256']==wheel['sha256'],'Official wheel byte/hash verification')
   write(output/(wheel['filename']+'.receipt.json'),receipt)
  lock='\n'.join(f'{w["name"]}=={w["version"]} --hash=sha256:{w["sha256"]}' for w in plan['wheels'])+'\n'
  (output/'requirements.lock').write_text(lock,encoding='utf-8',newline='\n')
  write(output/'ACQUISITION.json',dict(status='complete',wheel_plan_path=str(plan_path.absolute()),wheel_plan_sha256=sha(plan_path.read_bytes()),
   wheel_bytes=sum(r['bytes'] for r in receipts),metadata_bytes=plan['metadata_bytes'],wheels=plan['wheels'],provider_cost_usd=0,retries=0))
  print(json.dumps(dict(status='complete',wheels=len(receipts),wheel_bytes=sum(r['bytes'] for r in receipts))))
 except BaseException as error:
  write(output/'FAILURE.json',dict(stage='wheel_acquisition',error_type=type(error).__name__,captured_responses=len(receipts),automatic_retry=False));raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('stage',choices=('metadata','wheels'));p.add_argument('--output',type=Path,required=True);p.add_argument('--plan',type=Path);a=p.parse_args()
 if a.stage=='metadata':metadata(a.output)
 else:need(a.plan is not None,'Wheelplanrequired');wheels(a.plan,a.output)
