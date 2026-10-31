"""Fixed public text references only; never import/build/execute fetched material."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
COMMIT='848bbda9041decd87904f7eb5a2990863ecce03b'
PATHS=('include/llama.h','src/llama-sampler.cpp','src/llama-grammar.cpp',
       'src/llama-grammar.h','tests/test-grammar-integration.cpp',
       'tests/test-gbnf-validator.cpp','grammars/README.md','LICENSE')
PROTOCOL=HERE/'SOURCE-TEXT-PROTOCOL-v2.json'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def files():
    return [dict(index=i,path=p,url=f'https://raw.githubusercontent.com/ggml-org/llama.cpp/{COMMIT}/{p}')
            for i,p in enumerate(PATHS)]


def checked_protocol():
    raw=PROTOCOL.read_bytes();p=json.loads(raw)
    assert p['files']==files() and p['helper_sha256']==sha(Path(__file__).read_bytes())
    assert p['per_file_bytes']==524288 and p['aggregate_bytes']==2097152 and p['per_file_timeout_seconds']==15
    cache=ROOT/p['cache_relative_path']
    assert cache.resolve().is_relative_to((ROOT/'data/cache').resolve())
    return p,sha(raw),cache


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None


def one(index,expected_protocol,remaining):
    protocol,digest,cache=checked_protocol();assert digest==expected_protocol
    entry=protocol['files'][index];cap=min(524288,remaining);assert 0<cap<=524288
    started=time.monotonic();report=dict(**entry,role='source_reference_only',status='not_attempted',http_status=None)
    def audit(event,args):
        if event in ('subprocess.Popen','os.system'):
            raise RuntimeError('Fetch child cannot dispatch')
        if event=='socket.getaddrinfo':assert args[0]=='raw.githubusercontent.com' and args[1]==443
    sys.addaudithook(audit)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    request=urllib.request.Request(entry['url'],headers={'User-Agent':'AsOf-source-reference/1.0','Accept':'text/plain'})
    raw=b''
    try:
        with opener.open(request,timeout=14) as response:
            report.update(http_status=response.status,final_url=response.geturl(),content_type=response.headers.get('Content-Type'))
            assert response.status==200 and response.geturl()==entry['url']
            assert response.headers.get_content_type()=='text/plain'
            length=response.headers.get('Content-Length')
            if length is not None:assert 0<=int(length)<=cap
            raw=response.read(cap)
            assert time.monotonic()-started<15 and len(raw)<=cap and b'\0' not in raw
            assert (length is not None and len(raw)==int(length)) or (length is None and len(raw)<cap)
            raw.decode('utf-8')
        target=cache/'sources'/entry['path'];target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write(raw)
        report.update(status='retained_utf8_text',relative_path=target.relative_to(ROOT).as_posix())
    except urllib.error.HTTPError as error:
        report.update(status='http_error',http_status=error.code,final_url=error.geturl())
        raw=error.read(min(4096,cap));error.close()
        target=cache/'errors'/f'{index:02d}.http-body.bin';target.parent.mkdir(exist_ok=True)
        with target.open('xb') as stream:stream.write(raw)
        report['error_body_path']=target.relative_to(ROOT).as_posix()
    except Exception as error:
        report.update(status='failed',error_class=type(error).__name__,message=str(error))
    report.update(bytes=len(raw),sha256=sha(raw),elapsed_seconds=time.monotonic()-started)
    print(json.dumps(report),flush=True)


def prepare():
    protocol=dict(schema_version=1,role='prospective_source_reference_acquisition',
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),commit=COMMIT,
        helper_sha256=sha(Path(__file__).read_bytes()),files=files(),
        cache_relative_path='data/cache/r09-native-grammar-source-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
        per_file_bytes=524288,aggregate_bytes=2097152,per_file_timeout_seconds=15,
        max_concurrent_requests=1,attempts_per_url=1,credentials=False,proxies=False,redirects=False,
        execute_external_material=False,build=False,import_external_material=False,
        model_calls=0,servers=0,permitted_content='UTF-8 public source/license reference text only',
        supersedes_unexecuted_protocol='SOURCE-TEXT-PROTOCOL.json',
        timeout_enforcement='Owned fetch child killed after 15-second wait; elapsed includes cleanup overhead')
    with PROTOCOL.open('x',encoding='utf-8') as stream:json.dump(protocol,stream,indent=2)
    print(json.dumps(dict(status='source_text_protocol_frozen',protocol_sha256=sha(PROTOCOL.read_bytes()))))


def fetch():
    protocol,digest,cache=checked_protocol();cache.mkdir(exist_ok=False)
    (cache/'results').mkdir();records=[];used=0;unknown_received=False
    for entry in protocol['files']:
        remaining=protocol['aggregate_bytes']-used
        if remaining<=0 or unknown_received:
            records.append(dict(**entry,status='not_attempted_unknown_or_exhausted_aggregate'));continue
        argv=[sys.executable,'-I',str(Path(__file__).resolve()),'--one',str(entry['index']),digest,str(remaining)]
        started=time.monotonic()
        try:
            result=subprocess.run(argv,capture_output=True,timeout=15,shell=False,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0) if os.name=='nt' else 0)
            (cache/'results'/f"{entry['index']:02d}.stdout.json").write_bytes(result.stdout)
            (cache/'results'/f"{entry['index']:02d}.stderr.txt").write_bytes(result.stderr)
            assert result.returncode==0
            record=json.loads(result.stdout);assert record['url']==entry['url']
            record.update(child_exit_code=result.returncode,outer_elapsed_seconds=time.monotonic()-started)
        except subprocess.TimeoutExpired as error:
            (cache/'results'/f"{entry['index']:02d}.stdout.partial.bin").write_bytes(error.stdout or b'')
            (cache/'results'/f"{entry['index']:02d}.stderr.partial.bin").write_bytes(error.stderr or b'')
            record=dict(**entry,status='timeout_child_killed',outer_elapsed_seconds=time.monotonic()-started,bytes=0)
            unknown_received=True
        except Exception as error:
            record=dict(**entry,status='fetch_child_failed',error_class=type(error).__name__,message=str(error),bytes=0)
            unknown_received=True
        records.append(record);used+=record.get('bytes',0)
        print(json.dumps(dict(index=entry['index'],path=entry['path'],status=record['status'],bytes=record.get('bytes',0))),flush=True)
    retained=list((cache/'sources').rglob('*')) if (cache/'sources').exists() else []
    retained=[p for p in retained if p.is_file()]
    assert sum(p.stat().st_size for p in retained)<=2097152 and used<=2097152
    report=dict(schema_version=1,status='source_references_retained' if all(r['status']=='retained_utf8_text' for r in records)
        else 'source_reference_acquisition_terminal_with_missing_or_failed_inputs',
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=digest,
        cache_relative_path=cache.relative_to(ROOT).as_posix(),commit=COMMIT,records=records,
        known_response_bytes=used,unknown_response_bytes=unknown_received,retained_source_files=len(retained),model_calls=0,servers=0,builds=0,
        external_code_executed=False,external_code_imported=False,scientific_validation='not_attempted')
    with (HERE/'SOURCE-TEXT-ACQUISITION.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps(dict(status=report['status'],files=len(retained),known_response_bytes=used,unknown_response_bytes=unknown_received)),flush=True)


if __name__=='__main__':
    if sys.argv[1]=='--prepare':prepare()
    elif sys.argv[1]=='--fetch':fetch()
    elif sys.argv[1]=='--one':one(int(sys.argv[2]),sys.argv[3],int(sys.argv[4]))
    else:raise ValueError('Unknown fixed source-acquisition mode')
