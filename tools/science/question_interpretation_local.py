"""Optional loopback transport for question contracts; no launcher or retries.

Owned pinned assets must be verified by a separately frozen launcher. Metadata
here is declared local provenance, never remote execution or scientific attestation.
"""
import base64
from contextlib import contextmanager
import hashlib
from pathlib import Path
import threading
import urllib.request

from tether_engine.agents import Usage
from tether_engine.local_model import NoRedirect
from tether_engine.serde import ContractError, canonical, encode, fingerprint, freeze, parse_json
from tools.science.bounded_interpretation import Generated, checked_usage, need
from tools.science.local_interpretation import validate_config, verify_native_binding
from tools.science.question_interpretation_render import render_prompt, output_schema, materialize
from tools.science.run_comparison import check_pin

MAX_NATIVE_BYTES = 1024*1024


@contextmanager
def _preserve_primary(manager):
    """Cleanup must neither suppress nor replace a read/parse interruption."""
    response=manager.__enter__()
    try:
        yield response
    except BaseException as primary:
        try:manager.__exit__(type(primary),primary,primary.__traceback__)
        except BaseException as secondary:
            primary.add_note('Secondary native response close failed: '+type(secondary).__name__)
        raise
    else:
        manager.__exit__(None,None,None)


def payload_for(request, config):
    validate_config(config)
    prompt = render_prompt(request,max_prompt_bytes=config['max_prompt_bytes'],max_output_tokens=config['max_output_tokens'])
    return dict(prompt=prompt,n_predict=config['max_output_tokens'],temperature=0.0,seed=config['seed'],
                cache_prompt=False,json_schema=encode(output_schema(request)),stop=['<|im_end|>'],stream=False)


def native_complete(native):
    # Deliberate compatibility copy: changing the legacy module would invalidate
    # its exact-code archives. Both completion paths retain explicit regressions.
    need(isinstance(native,dict) and native.get('truncated') is False,'Native prompt completeness unqualified')
    for key in ('stopped_eos','stopped_word'):
        need(key not in native or type(native[key]) is bool,'Native stop cause must be boolean')
    need(not (native.get('stopped_eos') is True and native.get('stopped_word') is True),'Native stop causes conflict')
    if 'stop_type' in native:
        need(native.get('stop') is True and isinstance(native['stop_type'],str) and
             native['stop_type'] in {'eos','word'} and
             ('stopped_limit' not in native or native['stopped_limit'] is False),'Native completion cause unqualified')
        for key,cause in [('stopped_eos','eos'),('stopped_word','word')]:
            need(key not in native or native[key] is (native['stop_type']==cause),'Modern/legacy stop causes conflict')
        need(native.get('stopping_word')=='<|im_end|>' if native['stop_type']=='word' else
             native.get('stopping_word') in (None,''),'Unexpected native stop word')
    else:
        need(native.get('stopped_limit') is False and ('stop' not in native or native['stop'] is True),
             'Legacy output completeness unqualified')
        need(native.get('stopping_word')=='<|im_end|>' if native.get('stopped_word') is True else
             native.get('stopping_word') in (None,''),'Legacy stop word conflicts')


def _native_usage(native):
    need(isinstance(native,dict),'Native response must be object')
    return checked_usage(Usage(native.get('tokens_evaluated'),native.get('tokens_predicted'),0.0))


def _translate(request,payload,native,quote):
    usage = _native_usage(native); verify_native_binding(native,payload); native_complete(native)
    need(usage.input_tokens<=quote.input_tokens and usage.output_tokens<=quote.output_tokens,'Native exceeds reservation')
    need(isinstance(native.get('content'),str),'Native JSON content missing')
    response = materialize(request,parse_json(native['content']))
    return response,usage


class LocalQuestionInterpreter:
    backend_id = 'explicit-loopback-question-interpretation-v2'

    def __init__(self,config_path):
        path = Path(config_path).resolve()
        with path.open('rb') as stream: raw = stream.read(65537)
        need(len(raw)<=65536,'Local question configuration exceeds cap')
        config = parse_json(raw); validate_config(config); self.config=freeze(config); self.records=[]
        self._dispatch_lock=threading.Lock()
        self.provenance=freeze(dict(kind='explicit_question_local',config=config,
            config_original_utf8=raw.decode('utf-8'),config_sha256=hashlib.sha256(raw).hexdigest(),
            qualification='Pinned launcher declaration required; not remote attestation',provider_cost_usd=0))
        self.opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())

    def quote(self,request):
        need(not self.records,'Local question interpreter is one-use; do not repeat calls')
        payload=payload_for(request,self.config)
        return Usage(len(payload['prompt'].encode('utf-8'))+32,self.config['max_output_tokens'],0.0)

    def execution_document(self):
        return freeze(dict(schema_version=1,kind='question_local_execution',attempts=encode(self.records)))

    def generate(self,request,timeout_seconds):
        need(type(timeout_seconds) in (int,float) and timeout_seconds>0,'No native dispatch time')
        payload=payload_for(request,self.config);quote=self.quote(request)
        row=dict(request_sha256=fingerprint(request),payload=payload,payload_sha256=fingerprint(payload),status='dispatched')
        with self._dispatch_lock:
            need(not self.records,'Local question interpreter is one-use; do not repeat calls')
            self.records.append(row)
        http=urllib.request.Request(self.config['endpoint'].rstrip('/')+'/completion',data=canonical(payload),
            headers={'Content-Type':'application/json'},method='POST')
        try:
            with _preserve_primary(self.opener.open(http,timeout=min(timeout_seconds,self.config['timeout_seconds']))) as response:
                raw=response.read(MAX_NATIVE_BYTES+1)
                row.update(response_base64=base64.b64encode(raw).decode('ascii'),response_bytes_retained=len(raw),
                    native_response_sha256=hashlib.sha256(raw).hexdigest(),native_capture_complete=len(raw)<=MAX_NATIVE_BYTES)
                need(row['native_capture_complete'],'Native response exceeds cap; retained prefix is incomplete')
                native=parse_json(raw);row['native_response']=native
                usage=_native_usage(native);row['measured_usage']=encode(usage)
            translated,usage=_translate(request,payload,native,quote)
            row['status']='accepted';row['response_sha256']=fingerprint(translated)
            return Generated(canonical(translated).decode('utf-8'),usage)
        except BaseException as error:
            partial=getattr(error,'partial',None)
            if 'response_base64' not in row and isinstance(partial,bytes):
                retained=partial[:MAX_NATIVE_BYTES+1]
                row.update(response_base64=base64.b64encode(retained).decode('ascii'),response_bytes_retained=len(retained),
                    native_response_sha256=hashlib.sha256(retained).hexdigest(),native_capture_complete=False)
            row.update(status='rejected_or_failed_native',error_class=type(error).__name__)
            if 'measured_usage' in row and not isinstance(error,(KeyboardInterrupt,SystemExit)):
                # A typed diagnostic envelope lets the durable runtime account known
                # usage; it fails v2 validation. Original native bytes remain separate.
                return Generated(canonical({'rejected_native_question_response':type(error).__name__}).decode('utf-8'),
                                 _native_usage(row['native_response']))
            raise


def verify_local_execution(request,config,response,execution,report):
    """Explicit trusted runtime callback. Never connects to a server or generates."""
    need(config['backend_id']==LocalQuestionInterpreter.backend_id and
         check_pin(config['adapter_code'])==Path(__file__).resolve(),'Wrong local question adapter identity')
    provenance=config['adapter_provenance']
    need(isinstance(provenance,dict) and set(provenance)=={'kind','config','config_original_utf8',
         'config_sha256','qualification','provider_cost_usd'} and provenance['kind']=='explicit_question_local' and
         isinstance(provenance['config_original_utf8'],str) and provenance['provider_cost_usd']==0,
         'Invalid local question provenance')
    raw_config=provenance['config_original_utf8'].encode('utf-8')
    need(len(raw_config)<=65536 and hashlib.sha256(raw_config).hexdigest()==provenance['config_sha256'] and
         fingerprint(parse_json(raw_config))==fingerprint(provenance['config']),'Local configuration bytes differ')
    local=provenance['config'];validate_config(local);payload=payload_for(request,local)
    if report['calls']==0:
        need(execution is None and response['answer_status']=='abstained','Undispatched local execution differs')
        return
    need(report['calls']==1 and isinstance(execution,dict) and set(execution)=={'schema_version','kind','attempts'} and
         type(execution['schema_version']) is int and execution['schema_version']==1 and
         execution['kind']=='question_local_execution' and isinstance(execution['attempts'],list) and
         len(execution['attempts'])==1,'Invalid local execution document')
    row=execution['attempts'][0]
    need(row.get('status')=='accepted' and row.get('request_sha256')==fingerprint(request) and
         row.get('payload_sha256')==fingerprint(payload)==fingerprint(row.get('payload')) and
         row.get('native_capture_complete') is True and type(row.get('response_bytes_retained')) is int and
         isinstance(row.get('response_base64'),str),'Native execution request/capture differs')
    try:raw=base64.b64decode(row['response_base64'],validate=True)
    except (ValueError,TypeError) as error:raise ContractError('Invalid native response base64') from error
    need(len(raw)<=MAX_NATIVE_BYTES and len(raw)==row['response_bytes_retained'] and
         hashlib.sha256(raw).hexdigest()==row['native_response_sha256'],'Native captured bytes differ')
    native=parse_json(raw);need(fingerprint(native)==fingerprint(row['native_response']),'Native object differs from bytes')
    quote=Usage(len(payload['prompt'].encode('utf-8'))+32,local['max_output_tokens'],0.0)
    expected,usage=_translate(request,payload,native,quote)
    need(fingerprint(expected)==fingerprint(response) and row['response_sha256']==fingerprint(expected) and
         fingerprint(encode(usage))==fingerprint(row['measured_usage'])==fingerprint(report['measured_usage']),
         'Native response translation/accounting differs')
