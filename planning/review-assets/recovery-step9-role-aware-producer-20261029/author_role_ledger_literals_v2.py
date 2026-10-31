"""Fixture-only literal author. No validator, public codec, owner, or runtime API.

Authored values and fixed little-endian assignments create pre-implementation
goldens. The file reads only the pinned NEW schema/acceptance metadata.
"""
import base64
import copy
import hashlib
import json
import struct
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA_NAME = 'ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v2.json'
SCHEMA_SHA = 'b71cd8f49ccc8d4dc56b31915a3ed20465f58b08bb35b54df63a73a49e655b7a'
SCHEMA_RAW = (HERE / SCHEMA_NAME).read_bytes()
assert hashlib.sha256(SCHEMA_RAW).hexdigest() == SCHEMA_SHA
S = json.loads(SCHEMA_RAW)
E = S['enums']


def sha(b):
    return hashlib.sha256(b).hexdigest()


def pin(name):
    raw = (HERE / name).read_bytes()
    return {'path': str((HERE / name).resolve()), 'bytes': len(raw), 'sha256': sha(raw)}


def publish(name, value):
    raw = (json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2, allow_nan=False) + '\n').encode()
    with (HERE / name).open('xb') as f:
        f.write(raw)
    return pin(name)


def transport(v):
    if type(v) is bytes:
        return {'$bytes_hex': v.hex()}
    if type(v) is tuple:
        return {'$tuple': [transport(x) for x in v]}
    if type(v) is list:
        return [transport(x) for x in v]
    if type(v) is dict:
        return {k: transport(x) for k, x in v.items()}
    assert v is None or type(v) in (str, int, float, bool)
    return v


def blob(raw):
    return {'encoding': 'zlib-base64', 'bytes': len(raw), 'sha256': sha(raw),
            'data': base64.b64encode(zlib.compress(raw, 9)).decode('ascii')}


def atom(tag='UNOBSERVED', value=None):
    return {'tag': tag, 'value': value}


def flags(group, **on):
    result = {k: False for k in E[group]}
    assert not (on.keys() - result.keys())
    result.update(on)
    return result


def bits(group, value):
    return sum((1 << bit) for k, bit in E[group].items() if value[k])


def clock_bits(v):
    if v['tag'] == 'UNOBSERVED':
        return 0, 0
    if v['tag'] == 'I64':
        return 1, v['value'] & ((1 << 64) - 1)
    assert v['tag'] == 'F64'
    return 2, struct.unpack('<Q', struct.pack('<d', v['value']))[0]


def raw_bits(v):
    if v['tag'] in ('UNOBSERVED', 'NULL'):
        return 0
    return v['value'] & (0xffffffff if v['tag'] in ('BOOL', 'DWORD', 'COUNT32') else ((1 << 64)-1))


def header(profile='UNQUALIFIED_FRAGMENT', phase='FRAGMENT', status='INCOMPLETE'):
    return dict(profile=profile, phase=phase, status=status, origin_data_id=0x0102030405060708,
                ledger_sequence={'FRAGMENT': 0, 'CANDIDATE': 1, 'TERMINAL': 2}[phase],
                start_clock=atom('I64', 100), latest_clock=atom('I64', 109),
                freeze_clock=atom('I64', 110), previous_ledger_sha256=None,
                reserved_R=0, reserved_C=0, reserved_E=0, early_count=0,
                read_chunk=0 if profile == 'UNQUALIFIED_FRAGMENT' else (65536 if profile == 'ORIGINAL7_N4' else 1048576),
                flags=flags('header_flags_bits'))


def file_row(i, path, role='NONE_FRAGMENT_ONLY', size=None, target='ORIGINAL', qlen=0):
    capture = role in ('CAPTURED_SOFTWARE', 'CAPTURED_METADATA')
    pb = path.encode('utf-8')
    return dict(ordinal=i, role=role, capture_state='PENDING' if capture else 'NOT_REQUESTED',
                target_class=target, open_state='UNOPENED', identity_state='NOT_ATTEMPTED', close_state='NOT_ATTEMPTED',
                flags=flags('file_flags_bits', EXPECTED_DIGEST_PRESENT=size is not None,
                            EXPECTED_SIZE_PRESENT=size is not None, CAPTURE_REQUESTED=capture),
                descriptor_id=i, path_offset=0, path_bytes=len(pb), path_utf16_units=len(path.encode('utf-16-le'))//2,
                expected_size=size, expected_sha256=None if size is None else (hashlib.sha256(b'').digest() if size == 0 else hashlib.sha256(('synthetic:'+str(i)).encode()).digest()),
                actual_sha256=None, open_ordinal=None, close_ordinal=None, known_read_bytes=0, hashed_bytes=0,
                captured_bytes=0, query_offset=i*8218 if size is not None else 0, query_length=qlen,
                first_diagnostic=None, read_reservations=0, read_invocations=0, captured_blob_length=0,
                early_ordinal=None, path_id=i, read_generation=0, module_ordinal=None)


def call_row(i, api, file_id=0, *, scalar=None, invoked=True, original=False, captured=False, handle=0x0102030405060708,
             requested=None, frame_length=0, frame_offset=0, data=False, count=None):
    a = S['apis'][api-1]
    scalar = atom() if scalar is None else scalar
    observed = scalar['tag'] != 'UNOBSERVED'
    valid = observed and scalar['tag'] == a['scalar']
    if a['scalar'] == 'HANDLE' and scalar['tag'] == 'NULL':
        valid = True
    malformed = observed and not valid
    f = flags('call_flags_bits', INVOKED=invoked, SCALAR_OBSERVED=observed,
              SCALAR_NULL=scalar['tag'] == 'NULL', SCALAR_DOMAIN_VALID=valid,
              STOPPED=not observed or malformed, WRAPPER_RETURNED=observed,
              CAPTURE_REQUESTED=captured, MALFORMED_RAW=malformed,
              PRE_CLOCK_ATTEMPTED=True, PRE_CLOCK_RETURN_OBSERVED=True,
              POST_CLOCK_ATTEMPTED=observed, POST_CLOCK_RETURN_OBSERVED=observed)
    has_handle = api in (2,3,4,5,6,7,10,11,13,14)
    f['INPUT_HANDLE_PRESENT'] = has_handle
    f['REQUESTED_PRESENT'] = requested is not None
    f['BUFFER_PRESENT'] = frame_length > 0 or requested is not None
    f['QUERY_SPAN_PRESENT'] = frame_length > 0
    if count is not None:
        f['COUNT_OBSERVED'] = f['COUNT_DOMAIN_VALID'] = True
        f['COUNT_DEFINED'] = valid and scalar['tag'] == 'BOOL' and scalar['value'] != 0 and count <= requested
    f['IDENTITY_VERIFIED_AT_DISPATCH'] = original and api == 6 and invoked
    f['CLOSE_RIGHT_CONSUMED'] = api in (7, 11)
    if data:
        f['BUFFER_DATA_OBSERVED'] = True
    if frame_length and data:
        f['QUERY_CAPTURE_OBSERVED'] = f['QUERY_DEFINED'] = valid and scalar['value'] != 0
    return dict(ordinal=i, file_id=file_id, api=a['name'], record_version=1, flags=f,
                requested=0 if requested is None else requested,
                buffer_id=None if not f['BUFFER_PRESENT'] else (1 if frame_length else (2 if api == 13 else 0)),
                phase='fragment' if not original else 'binding_invoke', generation=1 if f['BUFFER_PRESENT'] else 0,
                buffer_written=frame_length if data and frame_length else (count if data and count is not None else 0),
                scalar_atom=scalar, count_atom=atom() if count is None else atom('COUNT32', count),
                error_atom=atom(), error_definition_atom=atom(), hashed_contribution=0, captured_contribution=0,
                known_count_contribution=count if original and api == 6 and f['COUNT_DEFINED'] else 0,
                query_offset=frame_offset if frame_length else 0, query_length=frame_length,
                input_handle_atom=atom('HANDLE', handle) if has_handle else atom(),
                pre_dispatch_clock=atom('I64',100), post_binding_clock=atom('I64',100) if observed else atom(),
                error_id=None, path_id=file_id, fold_state='COMMITTED' if original and api == 6 and f['COUNT_DEFINED'] else 'PENDING',
                buffer_state='DEFINED' if data else ('RESERVED' if f['BUFFER_PRESENT'] else 'NOT_APPLICABLE'))


def empty_value(h, files, calls, paths, queries):
    return dict(header=h, files=files, calls=calls, queries=queries, paths=paths,
                modules=[], module_names=b'', module_edges=(), diagnostics=[])


def fragment(api, scalar, suffix, definition=None, error=None):
    a = S['apis'][api-1]
    qlen = a['query_frame_bytes']
    path = 'D:\\fictional\\fragment_'+str(api)
    f = file_row(0, path, target=a['target'], qlen=qlen)
    c = call_row(0, api, scalar=scalar, requested=9 if api in (6,13) else None,
                 frame_length=qlen, count=0 if api == 6 and scalar['tag']=='BOOL' and scalar['value'] else (0 if api == 13 and scalar['tag']=='BOOL' and scalar['value']==0 else (7 if api == 13 else None)))
    if api == 14 and scalar['tag'] != 'UNOBSERVED':
        c['input_handle_atom'] = atom('HANDLE', 0)
    # Reserved raw frame storage is not a claimed captured/defined query.
    c['flags']['QUERY_CAPTURE_OBSERVED'] = c['flags']['QUERY_DEFINED'] = False
    if definition is not None:
        c['error_definition_atom'] = atom('DEFINEDNESS', definition)
        c['flags']['ERROR_DEFINITION_OBSERVED'] = True
        c['flags']['ERROR_DEFINED'] = definition
    if error is not None:
        c['error_atom'] = atom('DWORD', error)
        c['flags']['ERROR_OBSERVED'] = c['flags']['ERROR_DOMAIN_VALID'] = True
    if api in (1,9):
        f['open_ordinal'] = 0
        if scalar['tag']=='UNOBSERVED':
            f['open_state']='ENTERED_RETURN_UNKNOWN'
        elif scalar['tag']=='NULL' or scalar['value']==0:
            f['open_state']='OWNERSHIP_UNKNOWN'
        elif scalar['value']==0xffffffffffffffff:
            f['open_state']='KNOWN_FAILURE_NO_HANDLE'
        else:
            f['open_state']='OWNED'
    if api in (7,11):
        f['close_ordinal']=0
        f['flags']['CLOSE_RESERVED']=True
        if scalar['tag']=='BOOL':
            f['flags']['CLOSE_SUCCESS_KNOWN']=True
            f['flags']['CLOSE_SUCCESS_TRUE']=scalar['value']!=0
            f['close_state']='RETURNED_SUCCESS' if scalar['value'] else 'RETURNED_FAILURE'
        else:
            f['close_state']='ENTERED_RETURN_UNKNOWN'
    if api==6:
        f['read_reservations']=f['read_invocations']=1
        f['read_generation']=1
        if scalar['tag']=='UNOBSERVED':
            f['flags']['READ_UNKNOWN']=True
    h=header()
    h['flags']['READ_UNKNOWN']=f['flags']['READ_UNKNOWN']
    # Vary independent clocks across literal fragments, without rounding integers.
    if api in (1,2):
        for key,n in (('start_clock',0),('latest_clock',1),('freeze_clock',2)):
            h[key]=atom('I64',9007199254740993+n)
        c['pre_dispatch_clock']=atom('I64',9007199254740993)
        c['post_binding_clock']=atom('I64',9007199254740994) if scalar['tag']!='UNOBSERVED' else atom()
    elif api in (3,4):
        h['start_clock']=atom('F64',-0.0);h['latest_clock']=atom('F64',1.25);h['freeze_clock']=atom('F64',2.5)
        c['pre_dispatch_clock']=atom('F64',-0.0)
        c['post_binding_clock']=atom('F64',0.5) if scalar['tag']!='UNOBSERVED' else atom()
    return 'fragment_'+str(api).zfill(2)+'_'+suffix, empty_value(h,[f],[c],path.encode(),bytes(qlen))


def diagnostic(i, severity='PRIMARY', fallback=False):
    cl=b'MemoryError' if fallback else b'RuntimeError'
    msg=b'bounded literal fallback' if fallback else 'synthetic \u03b1 diagnostic'.encode()
    args=b'[]' if fallback else b'["first","second"]'
    return dict(ordinal=i,state='FORMAT_FALLBACK' if fallback else 'COMMITTED',
                flags=flags('diagnostic_flags_bits',FORMAT_FAILED=fallback),phase='diagnostic_format' if fallback else 'hash_update',
                opaque_identity_id=i+1,call_ordinal=None,secondary_of=None if i==0 else 0,
                class_bytes=len(cl),message_bytes=len(msg),args_bytes=len(args),clock_atom=atom('I64',117+i),
                severity=severity,class_utf8=cl,message_utf8=msg,args_utf8=args)


def complete_value(profile, roles, sizes, *, incomplete=False):
    h=header(profile,'TERMINAL' if incomplete else 'CANDIDATE','INCOMPLETE' if incomplete else 'OBSERVED_COMPLETE')
    paths=[];files=[];calls=[];q=bytearray(8218*len(roles));names=b'';modules=[];edges=[]
    for i,(role,size) in enumerate(zip(roles,sizes)):
        p='D:\\fictional\\source_'+str(i)+'.py' if role=='CAPTURED_SOFTWARE' else 'C:\\fictional\\metadata_'+str(i)+'.json'
        f=file_row(i,p,role,size,qlen=8218);f['path_offset']=sum(map(len,paths));paths.append(p.encode())
        f['open_state']='OWNED';f['identity_state']='VERIFIED';f['flags']['HASH_ATTEMPTED']=True
        captured=role!='HASH_ONLY_BULK';handle=0x0102030405060708+i
        f['open_ordinal']=len(calls)
        calls.append(call_row(len(calls),1,i,scalar=atom('HANDLE',handle),original=True,captured=captured))
        calls.append(call_row(len(calls),2,i,scalar=atom('DWORD',1),original=True,captured=captured,handle=handle))
        # Attributes, canonical final-path witness and signed64 size are literal raw frames.
        struct.pack_into('<II',q,i*8218,0x80,0)
        fp=('\\\\?\\'+p).encode('utf-16-le')+b'\0\0'
        q[i*8218+8:i*8218+8+len(fp)]=fp
        struct.pack_into('<q',q,i*8218+8210,size)
        for api,off,n,scalar in ((3,0,8,atom('BOOL',2)),(4,8,8202,atom('DWORD',len(fp)//2-1)),(5,8210,8,atom('BOOL',-1))):
            calls.append(call_row(len(calls),api,i,scalar=scalar,original=True,captured=captured,handle=handle,
                                  frame_length=n,frame_offset=i*8218+off,data=True))
        if size:
            c=call_row(len(calls),6,i,scalar=atom('BOOL',2),original=True,captured=captured,
                       handle=handle,requested=size,count=size,data=True)
            c['flags']['HASH_ATTEMPTED']=True;c['flags']['HASH_RETURN_OBSERVED']=not incomplete
            c['hashed_contribution']=0 if incomplete else size
            c['flags']['COPY_ATTEMPTED']=captured and not incomplete
            c['flags']['COPY_RETURN_OBSERVED']=captured and not incomplete
            c['captured_contribution']=size if captured and not incomplete else 0
            if incomplete:
                c['flags']['ACCOUNTING_FAULT']=c['flags']['STOPPED']=True
                c['fold_state']='FAILED_BEFORE_COMMIT';c['buffer_state']='INCOMPLETE_UNKNOWN';c['error_id']=0
            calls.append(c);f['known_read_bytes']=size;f['hashed_bytes']=0 if incomplete else size
            f['captured_bytes']=size if captured and not incomplete else 0
            f['read_reservations']=f['read_invocations']=1;f['read_generation']=1
        if incomplete:
            f['flags']['HASH_UNKNOWN']=True;f['flags']['ASSEMBLY_RETAINED']=captured
            f['capture_state']='FAILED' if captured else 'NOT_REQUESTED';f['first_diagnostic']=0
        else:
            f['actual_sha256']=f['expected_sha256'];f['flags']['ACTUAL_DIGEST_PRESENT']=f['flags']['HASH_COMPLETE']=True
            if captured:
                f['capture_state']='COMPLETE';f['flags']['CAPTURE_COMPLETE']=f['flags']['BLOB_ISSUED']=True
                f['captured_blob_length']=size
        if role=='CAPTURED_SOFTWARE':
            mi=len(modules);f['module_ordinal']=mi;f['early_ordinal']=mi;f['flags']['EARLY']=True
            name=('toy'+str(mi)).encode();dep=() if mi==0 else (0,)
            modules.append(dict(ordinal=mi,file_ordinal=i,flags=flags('module_flags',RETURN_OBSERVED=True,ACCEPTED=True,CACHED=True),
                                dependency_count=len(dep),name_offset=len(names),name_length=len(name),edge_offset=len(edges)*2,
                                first_diagnostic=None,attempt_order=mi,return_order=mi,cache_hit_count=0))
            names+=name;edges.extend(dep)
        files.append(f)
    h['early_count']=len(modules)
    h['reserved_R']=sum((n//h['read_chunk']+(n%h['read_chunk']!=0)+16) for n in sizes if n)
    h['reserved_C']=6*len(files)+h['reserved_R'];h['reserved_E']=6*len(files)+4*len(modules)+192
    v=empty_value(h,files,calls,b''.join(paths),bytes(q));v.update(modules=modules,module_names=names,module_edges=tuple(edges))
    if incomplete:
        h['flags'].update(HASH_UNKNOWN=True,ACCOUNTING_FAULT=True,PRIMARY_PRESENT=True)
        h['latest_clock']=atom('I64',119);h['freeze_clock']=atom('I64',120)
        v['diagnostics']=[diagnostic(0),diagnostic(1,'FORMATTER_FAILURE',True)]
    return v


def terminal(candidate, previous):
    v=copy.deepcopy(candidate);h=v['header'];h['phase']='TERMINAL';h['ledger_sequence']=2
    h['previous_ledger_sha256']=bytes.fromhex(previous);h['flags']['PREVIOUS_LEDGER_PRESENT']=True
    h['latest_clock']=atom('I64',112);h['freeze_clock']=atom('I64',113)
    for i,f in enumerate(v['files']):
        f['close_ordinal']=len(v['calls']);f['close_state']='RETURNED_SUCCESS'
        f['flags'].update(CLOSE_RESERVED=True,CLOSE_SUCCESS_KNOWN=True,CLOSE_SUCCESS_TRUE=True)
        c=call_row(len(v['calls']),7,i,scalar=atom('BOOL',-1 if i%2 else 2),original=True,
                   captured=True,handle=0x0102030405060708+i)
        c['pre_dispatch_clock']=c['post_binding_clock']=atom('I64',111)
        v['calls'].append(c)
    return v


def full_shape():
    # Intentionally not a live history: an invalid API0 makes this a whole-buffer
    # capacity/section-hashing rejection control, not manufactured native success.
    h=header('ORIGINAL7_PROSPECTIVE','TERMINAL','INCOMPLETE');h.update(reserved_R=14848,reserved_C=16384,reserved_E=2240,early_count=128)
    h['flags']['PRIMARY_PRESENT']=True
    fs=[];ps=[];names=b'';ms=[];es=[]
    for i in range(256):
        tail=str(i).zfill(3);p='D:\\'+'\u4e00'*(4093-len(tail))+tail
        role='CAPTURED_SOFTWARE' if i<128 else 'HASH_ONLY_BULK';size=0 if i<128 else 100*1048576
        f=file_row(i,p,role,size,qlen=8218);f['path_offset']=sum(map(len,ps));ps.append(p.encode())
        if i<128:
            f['flags']['EARLY']=True;f['early_ordinal']=i;f['module_ordinal']=i
            name=('x'*507+('.m'+str(i).zfill(3))).encode();assert len(name)==512
            dep=tuple(range(i))
            ms.append(dict(ordinal=i,file_ordinal=i,flags=flags('module_flags'),dependency_count=i,
                           name_offset=len(names),name_length=512,edge_offset=2*len(es),first_diagnostic=None,
                           attempt_order=None,return_order=None,cache_hit_count=0));names+=name;es.extend(dep)
        fs.append(f)
    cs=[]
    template=call_row(0,1,scalar=atom(),invoked=False,original=True,captured=True)
    template['flags']['STOPPED']=False;template['flags']['PRE_CLOCK_ATTEMPTED']=template['flags']['PRE_CLOCK_RETURN_OBSERVED']=False
    template['pre_dispatch_clock']=atom();template['api']=0
    for i in range(16384):
        c=copy.deepcopy(template);c['ordinal']=i;c['file_id']=c['path_id']=i%256
        c['flags']['CAPTURE_REQUESTED']=i%256<128;cs.append(c)
    v=empty_value(h,fs,cs,b''.join(ps),bytes(8218*256));v.update(modules=ms,module_names=names,module_edges=tuple(es))
    v['diagnostics']=[diagnostic(i,'PRIMARY' if i==0 else 'SECONDARY') for i in range(5056)]
    for d in v['diagnostics']:
        d['clock_atom']=atom()
    return v


def fixed_record(table, values, kinds):
    out=bytearray(S[table]['bytes'])
    for f in S[table]['fields']:
        name=f['name'];n=f['bytes'];off=f['offset'];typ=f['type']
        if name.startswith('reserved'):
            continue
        val=values[name]
        if name in kinds:
            val=E[kinds[name]][val] if type(val) is str else bits(kinds[name],val)
        if val is None:
            val=0xffff if typ=='optional_u16' else (0xffffffff if typ=='optional_u32' else 0)
        if type(val) is bytes:
            assert len(val)<=n;out[off:off+len(val)]=val
        else:
            struct.pack_into({1:'<B',2:'<H',4:'<I',8:'<Q'}[n],out,off,val)
    return bytes(out)


def file_bytes(f):
    d=dict(f)
    d['expected_size']=0 if f['expected_size'] is None else f['expected_size']
    d['expected_sha256']=f['expected_sha256'] or bytes(32);d['actual_sha256']=f['actual_sha256'] or bytes(32)
    return fixed_record('file_record',d,dict(role='role',capture_state='capture',target_class='target',open_state='open',
                        identity_state='identity',close_state='close',flags='file_flags_bits'))


def call_bytes(c):
    d=dict(c);f=bits('call_flags_bits',c['flags']);a,pre=clock_bits(c['pre_dispatch_clock']);b,post=clock_bits(c['post_binding_clock'])
    d.update(api=next((x['id'] for x in S['apis'] if x['name']==c['api']),c['api']),fact_flags=f|(a<<32)|(b<<34),
             raw_scalar_bits=raw_bits(c['scalar_atom']),raw_count=raw_bits(c['count_atom']),raw_error=raw_bits(c['error_atom']),
             input_handle_bits=raw_bits(c['input_handle_atom']),pre_dispatch_clock_bits=pre,post_binding_clock_bits=post,
             buffer_id=0xffff if c['buffer_id'] is None else c['buffer_id'])
    return fixed_record('call_record',d,dict(phase='phase_code',fold_state='fold',buffer_state='buffer'))


def diag_bytes(d):
    q=dict(d);q['clock_tag'],q['clock_bits']=clock_bits(d['clock_atom'])
    return fixed_record('diagnostic_record',q,dict(state='diagnostic_state',flags='diagnostic_flags_bits',phase='phase_code',severity='severity'))


def literal_bytes(v):
    # No semantic validation or decode path. These are fixed layout assignments
    # for this authored corpus, not a production encoder entry point.
    sections=[b''.join(map(file_bytes,v['files'])),b''.join(map(call_bytes,v['calls'])),v['queries'],v['paths'],
              b''.join(fixed_record('module_record',m,dict(flags='module_flags')) for m in v['modules']),
              v['module_names'],b''.join(struct.pack('<H',x) for x in v['module_edges']),b''.join(map(diag_bytes,v['diagnostics']))]
    widths=[256,256,1,1,64,1,2,1024]
    h=v['header'];out=bytearray(4096);out[:8]=b'RAPLEDG1'
    nums={8:(2,1),10:(2,2),12:(2,E['profile'][h['profile']]),14:(2,E['phase'][h['phase']]),16:(2,E['status'][h['status']]),
          18:(2,4096),20:(2,8),22:(2,len(v['files'])),24:(4,len(v['calls'])),28:(2,len(v['modules'])),30:(2,len(v['diagnostics'])),
          32:(4,len(v['module_edges'])),36:(4,bits('header_flags_bits',h['flags'])),40:(8,4096+sum(map(len,sections))),
          48:(8,sum(f['captured_blob_length'] for f in v['files'] if f['flags']['BLOB_ISSUED'])),
          56:(8,sum(f['known_read_bytes'] for f in v['files'])),64:(8,sum(f['hashed_bytes'] for f in v['files'])),
          72:(8,sum(f['captured_bytes'] for f in v['files'])),80:(8,h['origin_data_id']),88:(8,h['ledger_sequence']),
          168:(4,h['reserved_R']),172:(4,h['reserved_C']),176:(4,h['reserved_E']),180:(2,h['early_count']),
          182:(2,len(v['modules'])),184:(4,h['read_chunk']),188:(2,1)}
    tags=0
    for shift,off,name in ((0,96,'start_clock'),(2,104,'latest_clock'),(4,112,'freeze_clock')):
        t,n=clock_bits(h[name]);tags|=t<<shift;nums[off]=(8,n)
    nums[120]=(1,tags)
    for off,(n,x) in nums.items():struct.pack_into({1:'<B',2:'<H',4:'<I',8:'<Q'}[n],out,off,x)
    out[128:160]=h['previous_ledger_sha256'] or bytes(32)
    pos=4096;layout=[]
    for i,(raw,width) in enumerate(zip(sections,widths)):
        off=256+64*i;struct.pack_into('<HHIQQ',out,off,i+1,width,len(raw)//width,pos,len(raw));out[off+24:off+56]=hashlib.sha256(raw).digest()
        layout.append(dict(id=i+1,name=S['sections'][i]['name'],offset=pos,bytes=len(raw),record_size=width,count=len(raw)//width,sha256=sha(raw)))
        pos+=len(raw)
    return bytes(out)+b''.join(sections),layout


def verify_anchors(raw, v, layout):
    anchors=[dict(offset=0,hex='5241504c45444731',meaning='fixed magic'),dict(offset=8,hex='01000200',meaning='format1 and value schema2')]
    c=v['calls'][0];off=layout[1]['offset']
    # Hand-pinned discriminating scalar patterns, not obtained by decoding.
    x=c['scalar_atom'];patterns={('BOOL',-1):'ffffffff00000000',('BOOL',-2147483648):'0000008000000000',
                                ('BOOL',2147483647):'ffffff7f00000000',('DWORD',0xffffffff):'ffffffff00000000',
                                ('DWORD',0x12345678):'7856341200000000',('HANDLE',0x0102030405060708):'0807060504030201',
                                ('HANDLE',0xffffffffffffffff):'ffffffffffffffff'}
    key=(x['tag'],x['value'])
    if key in patterns:anchors.append(dict(offset=off+32,hex=patterns[key],meaning='independent little-endian raw scalar anchor'))
    anchors.append(dict(offset=off+104,hex='ffffffff' if c['error_id'] is None else '00000000',meaning='optional diagnostic id differs from raw error DWORD0'))
    for a in anchors:assert raw[a['offset']:a['offset']+len(bytes.fromhex(a['hex']))]==bytes.fromhex(a['hex'])
    return anchors


def mutate(raw, pos, replacement, *, rehash=False):
    b=bytearray(raw);b[pos:pos+len(replacement)]=replacement
    if rehash:
        for i in range(8):
            d=256+64*i;off,n=struct.unpack_from('<QQ',b,d+8)
            b[d+24:d+56]=hashlib.sha256(b[off:off+n]).digest()
    return bytes(b)


def main():
    cases=[]
    # Exactly 14 observed API base fragments, with deliberately varied raw facts.
    observed=[atom('HANDLE',0x0102030405060708),atom('DWORD',0),atom('BOOL',-2147483648),atom('DWORD',0xffffffff),
              atom('BOOL',0),atom('BOOL',2),atom('BOOL',-1),atom('NULL'),atom('HANDLE',0x0102030405060708),
              atom('BOOL',0),atom('BOOL',2147483647),atom('BOOL',2),atom('BOOL',0),atom('BOOL',-1)]
    defs={2:(True,0),5:(False,5),6:(False,7),10:(True,18)}
    for api,a in enumerate(observed,1):
        d,e=defs.get(api,(None,None));cases.append(fragment(api,a,'observed',d,e))
    for api in range(1,15):cases.append(fragment(api,atom(),'unobserved'))
    for api in (1,9):
        for name,a in [('null',atom('NULL')),('zero',atom('HANDLE',0)),('invalid',atom('HANDLE',0xffffffffffffffff))]:
            definition=True if name=='invalid' and api==1 else None
            error=0 if name=='invalid' and api==9 else None
            cases.append(fragment(api,a,name,definition,error))
    cases.append(fragment(2,atom('DWORD',0x12345678),'nontrivial'))
    c=complete_value('ORIGINAL7_N4',['CAPTURED_SOFTWARE','CAPTURED_SOFTWARE','CAPTURED_METADATA','CAPTURED_METADATA'],[0,3,5,7])
    candidate_raw,_=literal_bytes(c)
    cases.extend([('n4_candidate_captured',c),('n4_terminal_captured',terminal(c,sha(candidate_raw))),
                  ('prospective_mixed_roles',complete_value('ORIGINAL7_PROSPECTIVE',['CAPTURED_SOFTWARE','CAPTURED_METADATA','HASH_ONLY_BULK'],[0,0,7])),
                  ('n4_hash_failure_terminal',complete_value('ORIGINAL7_N4',['CAPTURED_METADATA'],[3],incomplete=True)),
                  ('prospective_full_cap_shape_invalid_api',full_shape())])
    assert len(cases)==40
    golden=[];raws={};values={};layouts={}
    for ident,v in cases:
        raw,layout=literal_bytes(v);raws[ident]=raw;values[ident]=v;layouts[ident]=layout
        shape=ident.endswith('invalid_api')
        golden.append(dict(id=ident,layer='FULL_CAP_SHAPE' if shape else 'PURE_FORMAT',
                           semantic_value=blob(json.dumps(transport(v),sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()),
                           raw=blob(raw),layout=layout,anchors=verify_anchors(raw,v,layout),
                           expected=dict(accepted=not shape,required_code='ENUM_DOMAIN' if shape else None,
                                         exact_canonical_value=not shape,source_or_native_history=False)))
    mutations=[]
    def add(ident,base,pos,replacement,code=None,rehash=False):
        r=mutate(raws[base],pos,replacement,rehash=rehash)
        mutations.append(dict(id=ident,base=base,patch=dict(offset=pos,hex=replacement.hex(),rehash_sections=rehash),
                              bytes=len(r),sha256=sha(r),expected=dict(accepted=False,required_code=code)))
    base='n4_hash_failure_terminal';lay=layouts[base]
    # Every reserved REGION: first, middle and last byte. This does not claim
    # one test for each of several thousand individual reserved bytes.
    regions=[]
    for table,origin in [('header',0),('file_record',lay[0]['offset']),('call_record',lay[1]['offset']),
                         ('module_record',layouts['n4_candidate_captured'][4]['offset']),('diagnostic_record',lay[7]['offset'])]:
        b='n4_candidate_captured' if table=='module_record' else base
        for f in S[table]['fields']:
            if f['name'].startswith('reserved'):
                regions.append(dict(base=b,table=table,name=f['name'],offset=origin+f['offset'],bytes=f['bytes']))
    for i in range(8):
        regions.extend([dict(base=base,table='section_descriptor',name='flags',offset=256+64*i+56,bytes=4),
                        dict(base=base,table='section_descriptor',name='reserved_zero_tail',offset=256+64*i+60,bytes=4)])
    for ri,r in enumerate(regions):
        for oi,o in enumerate(sorted(set([0,r['bytes']//2,r['bytes']-1]))):
            add('reserved_'+str(ri).zfill(2)+'_'+str(oi),r['base'],r['offset']+o,b'\x01','RESERVED_NONZERO',r['offset']>=4096)
    for off,n,val,name,code in [(0,1,0,'magic','MAGIC_VERSION'),(8,2,2,'format','MAGIC_VERSION'),(10,2,99,'value_schema','MAGIC_VERSION'),
                              (12,2,65535,'profile','ENUM_DOMAIN'),(14,2,65535,'phase','ENUM_DOMAIN'),(16,2,65535,'status','ENUM_DOMAIN'),
                              (22,2,257,'files_cap','SIZE_CAP'),(24,4,16385,'calls_cap','SIZE_CAP'),(28,2,129,'modules_cap','SIZE_CAP'),
                              (30,2,5057,'diagnostics_cap','SIZE_CAP'),(160,8,1,'qualification','RESERVED_NONZERO')]:
        add('header_'+name,base,off,val.to_bytes(n,'little'),code)
    for i in range(8):
        o=256+64*i
        for delta,n,val,name,code in [(0,2,99,'id','SECTION_LAYOUT'),(2,2,65535,'record_size','SECTION_LAYOUT'),
                                    (4,4,0xffffffff,'count','SECTION_LAYOUT'),(8,8,4095,'offset','SECTION_LAYOUT'),
                                    (16,8,0xffffffffffffffff,'length','SECTION_LAYOUT')]:
            add('section_'+str(i+1)+'_'+name,base,o+delta,val.to_bytes(n,'little'),code)
        add('section_'+str(i+1)+'_digest',base,o+24,b'\xff'*32,'SECTION_DIGEST')
    # Unknown bits and invalid tags are isolated after repairing section hashes.
    for ident,b,pos,n,val,code in [
        ('header_flag_bit31',base,36,4,0x80000000,'RESERVED_NONZERO'),
        ('header_clock_tag3',base,120,1,3,'CLOCK_DOMAIN'),('header_clock_high',base,120,1,0xc0,'RESERVED_NONZERO'),
        ('call_flag_bit63',base,lay[1]['offset']+8,8,1<<63,'RESERVED_NONZERO'),
        ('file_flag_bit63',base,lay[0]['offset']+8,8,1<<63,'RESERVED_NONZERO'),
        ('module_flag_bit15','n4_candidate_captured',layouts['n4_candidate_captured'][4]['offset']+4,2,1<<15,'RESERVED_NONZERO'),
        ('diagnostic_flag_bit7',base,lay[7]['offset']+5,1,128,'RESERVED_NONZERO')]:
        add(ident,b,pos,val.to_bytes(n,'little'),code,pos>=4096)
    enums=[('file_role',lay[0]['offset']+2,1),('file_capture',lay[0]['offset']+3,1),('file_target',lay[0]['offset']+4,1),
           ('file_open',lay[0]['offset']+5,1),('file_identity',lay[0]['offset']+6,1),('file_close',lay[0]['offset']+7,1),
           ('call_api',lay[1]['offset']+6,1),('call_phase',lay[1]['offset']+22,2),('call_fold',lay[1]['offset']+112,4),
           ('call_buffer',lay[1]['offset']+116,4),('diag_state',lay[7]['offset']+4,1),('diag_phase',lay[7]['offset']+6,2),
           ('diag_severity',lay[7]['offset']+41,1)]
    for name,pos,n in enums:add('enum_'+name,base,pos,((1<<(8*n))-1).to_bytes(n,'little'),'ENUM_DOMAIN',True)
    # Structural/layout contradictions and immutable lower-bound evidence.
    semantics=[('file_path_span',lay[0]['offset']+24,4,0xffffffff,'PATH_DOMAIN'),
               ('file_query_span',lay[0]['offset']+140,4,8217,'QUERY_SPAN'),
               ('call_optional_error_ref',lay[1]['offset']+104,4,2,'REFERENCE_DOMAIN'),
               ('diag_identity',lay[7]['offset']+8,8,0,'DIAGNOSTIC_LAYOUT'),
               ('diag_class_length',lay[7]['offset']+24,2,97,'DIAGNOSTIC_LAYOUT')]
    for name,pos,n,val,code in semantics:add(name,base,pos,val.to_bytes(n,'little'),code,True)
    # Selected missing-boundary/trailing controls do not pretend the schema
    # fixed a unique diagnostic code among length/layout failure categories.
    cuts=sorted(set([0,1,7,8,255,256,767,768,4095,4096]+[f['offset']+f['bytes'] for f in S['header']['fields']]+[x['offset']+x['bytes']-1 for x in lay]))
    for n in cuts:
        if n>=len(raws[base]):continue
        r=raws[base][:n]
        mutations.append(dict(id='truncated_'+str(n),base=base,truncate=n,bytes=n,sha256=sha(r),expected=dict(accepted=False,required_code=None)))
    r=raws[base]+b'\0'
    mutations.append(dict(id='trailing_one',base=base,append_hex='00',bytes=len(r),sha256=sha(r),expected=dict(accepted=False,required_code='TRAILING_BYTES')))
    assert len(mutations)<=512
    contract=dict(schema_version=1,status='FROZEN_LITERAL_PREPARATION_BEFORE_CODEC_SOURCE',
                  basis=[pin(SCHEMA_NAME),pin('ROLE-AWARE-PRODUCER-FORMAT-FREEZE-v2.json'),
                         pin('ROLE-AWARE-PRODUCER-FORMAT-INDEPENDENT-REVIEW-v2.json'),pin('ROLE-AWARE-PRODUCER-FORMAT-SCHEMA-ACCEPTANCE-v2.json'),
                         pin('ROLE-AWARE-FORMAT-LITERAL-ROOT-CORRECTION-v2.json'),pin('ROLE-AWARE-FORMAT-LITERAL-INDEPENDENT-REVIEW-v1.json'),
                         pin('ROLE-AWARE-FORMAT-LITERAL-SELF-REVIEW-v1.json'),pin('ROLE-AWARE-FORMAT-LITERAL-STRUCTURE-PROOF-v1.json')],
                  actual_counts=dict(base_histories=40,positive_data_bases=39,shape_only_negative_bases=1,
                                     byte_negative_expansions=len(mutations),anchors=sum(len(x['anchors']) for x in golden),
                                     reserved_regions=len(regions),full_cap_layout_controls=1,
                                     future_methods=4,value_type_refusal_probes=15,callback_exception_invocations=66,
                                     callback_exception_families=11,predicted_entrypoint_invocations=387,predicted_getter_calls=158),
                  transport=dict(bytes='$bytes_hex exact lowerhex',tuple='$tuple recursively transported members',
                                 stored_blob='zlib-base64 containing exact pinned raw bytes or canonical JSON transport; no codec is used to decompress'),
                  expected_scope=dict(code='required_code is normative only when nonnull; all negatives must refuse and expose the closed immutable FormatError surface',
                                      offsets='raw mode exact nonbool offset within0..len(raw) or None; value mode None; no guessed implementation-specific path',
                                      immutable='all canonical exact types and cached raw bytes; each to_dict detached',
                                      cancellations='11 original BaseException families at first/middle/final actual check sites for both public codec entrypoints; getters never call check',
                                      claimed_histories='Authored data only. Full-cap invalid API0 layout is NOT a live history and must reject. Decoder never creates owner/handle/diagnostic authority.'),
                  mutation_isolation='Reserved/table semantic changes recompute all section digests, descriptor/hash/length tests do not. Truncation retains original declared length.',
                  future_test_methods=['literal_encode_decode_and_anchors','byte_negative_expansions','strict_types_and_detached_mutation','callback_identity_and_cached_getters'],
                  producer_queued=['first sentinel slot before auxiliary/fold/packing failure','D borrow-release across>=16384 successes and protected cleanup identities',
                                   'genuine GeneratedArtifactBytes/candidate-terminal nonaliasing and same-owner full-byte consumers',
                                   'actual unchanged legacy48+8+16 parity and opaque token/ref is checks','hash-only context byte-getter refusal and capture-not-requested state'],
                  publication_queued='schema2 packets/scope/11 exact keys, complete14 artifact DAG and physical writer remain actual producer slice controls; no imaginary pure packet codec API',
                  qualification={k:False for k in ['codec_implemented','producer_implemented','real_entry','real_FFI','physical_IO','full_roster','new84_runtime','resource_fit','scientific']},
                  subject_imports=0,subject_runs=0,target_operations=0)
    cp=publish('ROLE-AWARE-FORMAT-CORPUS-TEST-CONTRACT-v2.json',contract)
    corpus=dict(schema_version=1,status='SYNTHETIC_PREIMPLEMENTATION_LITERAL_GOLDENS',contract=cp,bases=golden,byte_negatives=mutations)
    fp=publish('ROLE-AWARE-FORMAT-LITERAL-CORPUS-v2.json',corpus)
    provenance=dict(schema_version=1,status='LITERALS_AUTHORED_WITHOUT_TARGET_CODEC',author=pin(Path(__file__).name),
                    contract=cp,corpus=fp,counts=contract['actual_counts'],
                    golden_source='Hand-authored semantic facts plus direct documented little-endian field assignments. No target encoder/decoder/reference validator or producer source was imported or consulted.',
                    full_cap=dict(raw_bytes=len(raws[cases[-1][0]]),section_layout=layouts[cases[-1][0]],
                                  reserved_ledger_cap=14800384,claim='Complete used-capacity table extents with intentionally invalid API0; shape/hash rejection control only.'),
                    activity=dict(subject_imports=0,subject_runs=0,ordinary_toy_helper_execution=0,original_or_payload_operations=0,native_or_physical_operations=0))
    pp=publish('ROLE-AWARE-FORMAT-LITERAL-PROVENANCE-v2.json',provenance)
    print(json.dumps({'contract':cp,'corpus':fp,'provenance':pp,'counts':contract['actual_counts']}))


if __name__=='__main__':
    main()
