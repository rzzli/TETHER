"""Audit only the already-retained fixed large result; imports no subject/helper.

No generated input hashing, owner, producer, native API or replay. Binary reads
below are fixed-artifact field comparisons against the pinned format metadata,
not a reusable decoder or producer implementation.
"""
import hashlib
import json
import math
from pathlib import Path
import struct
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PROOF_SHA = '7cefbe0e5dc71f950a3537be9f30790d0c7501ca7c5c3446c3c331567a98cedf'
FORMAT_SHA = 'b71cd8f49ccc8d4dc56b31915a3ed20465f58b08bb35b54df63a73a49e655b7a'
REPORT = HERE / 'ROLE-AWARE-LARGE-INJECTED-INDEPENDENT-ACTUAL-PEER-v1.json'
API = ('CreateFileW', 'GetFileType', 'GetFileInformationByHandleEx', 'GetFinalPathNameByHandleW', 'GetFileSizeEx', 'ReadFile', 'CloseHandle')
CHUNK = 1048576
SPY = struct.Struct('<IHHQQQddIIQ')
CHECKS = 0


def need(value, label):
    global CHECKS
    CHECKS += 1
    if not value:
        raise AssertionError(label)


def same(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return set(a) == set(b) and all(same(a[k], b[k]) for k in a)
    if type(a) in (list, tuple):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if type(a) is float:
        return struct.pack('<d', a) == struct.pack('<d', b)
    return a == b


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode()


def pairs(items):
    out = {}
    for key, value in items:
        need(key not in out, 'duplicate JSON key')
        out[key] = value
    return out


def parse(raw):
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))


def digest(path):
    path = Path(path)
    need(path.resolve().is_relative_to(ROOT.resolve()), 'new repository artifact only')
    count = 0
    h = hashlib.sha256()
    with path.open('rb') as src:
        for raw in iter(lambda: src.read(65536), b''):
            count += len(raw)
            h.update(raw)
    return dict(path=str(path.resolve()), bytes=count, sha256=h.hexdigest())


def pinned(value):
    got = digest(value['path'])
    need(type(value['bytes']) is int and got['bytes'] == value['bytes'] and got['sha256'] == value['sha256'], 'retained pin bytes/hash')
    return got


def exact_bytes(src, n):
    raw = src.read(n)
    need(len(raw) == n, 'complete bounded artifact read')
    return raw


def frame(d, api):
    if api == API[2]:
        return struct.pack('<II', 128, 0)
    if api == API[4]:
        return struct.pack('<q', d['size'])
    raw = ('\\\\?\\' + d['path']).encode('utf-16-le') + bytes(2)
    return raw + bytes(8202 - len(raw))


def sequence(ds):
    generation = 0
    for d in ds:
        for api in API[:5]:
            yield d['file_id'], api, 0, 0
        remaining = d['size']
        while remaining:
            n = min(CHUNK, remaining)
            yield d['file_id'], API[5], n, generation
            generation += 1
            remaining -= n
    for d in reversed(ds):
        yield d['file_id'], API[6], 0, 0


def atom(tag, value):
    return dict(tag=tag, value=value)


U = atom('UNOBSERVED', None)
NULL = atom('NULL', None)


def fields(raw, layout):
    out = {}
    for f in layout:
        part = raw[f['offset']:f['offset'] + f['bytes']]
        need(len(part) == f['bytes'], 'fixed field length')
        kind = f['type']
        if kind == 'zero_bytes':
            need(not any(part), 'zero padding')
            continue
        if kind.startswith(('u', 'optional_u')) or kind == 'typed_clock_bits':
            out[f['name']] = int.from_bytes(part, 'little')
        else:
            out[f['name']] = part
    return out


def expect_fields(actual, expected, label):
    for k, v in expected.items():
        need(k in actual and same(actual[k], v), label + ':' + k)


def bitmask(schema, key, names):
    return sum(1 << schema['enums'][key][n] for n in names)


def run():
    need(not REPORT.exists(), 'retain first peer report')
    proof_path = HERE / 'ROLE-AWARE-LARGE-INJECTED-PROOF-v3.json'
    need(digest(proof_path)['sha256'] == PROOF_SHA, 'exact first proof')
    p = parse(proof_path.read_bytes())
    need(p['status'] == 'PASS_SOURCE_PURE_LARGE_GENERATED_ONLY', 'first actual large pass')
    bpath = HERE / 'ROLE-AWARE-LARGE-INJECTED-BINDING-v3.json'
    bp = digest(bpath)
    need(bp['sha256'] == p['binding_sha256'], 'proof binding digest')
    b = parse(bpath.read_bytes())
    pin_results = []
    for x in (b['execution_scope'], b['reference'], b['source_pause'], b['adapter'], b['helper'], *b['source_map'].values(), *b['required_evidence'].values()):
        pin_results.append(pinned(x))
    scope = parse(Path(b['execution_scope']['path']).read_bytes())
    pause = parse(Path(b['source_pause']['path']).read_bytes())
    need(b['source_map'] == pause['sources'] == p['source_pins'], 'coherent exact source map')
    need(all(v is True for v in p['source_and_harness_unchanged'].values()), 'reported stability true')
    for x in p['harness_pins'].values():
        pin_results.append(pinned(x))
    attempt = parse((HERE / 'ROLE-AWARE-LARGE-INJECTED-ATTEMPT-v3.json').read_bytes())
    need(attempt['binding_sha256'] == bp['sha256'] and attempt['subject_imported'] is False and attempt['root_scope'] == b['execution_scope'], 'exclusive first attempt provenance')
    ref = parse(Path(b['reference']['path']).read_bytes())
    ds = ref['descriptors']
    need(len(ds) == 216 and ref['status'] == 'REFERENCE_COMPLETE', 'fixed complete fictional reference')
    need(sum(d['size'] for d in ds) == 9017363601 and sum(d['size'] for d in ds[:3]) == 209, 'declared total/capture')
    for i, d in enumerate(ds):
        need(type(d['file_id']) is int and d['file_id'] == i and type(d['size']) is int and d['size'] > 0 and d['capture'] is (i < 3), 'descriptor identity/role size')
        if i < 3:
            need(hashlib.sha256(bytes.fromhex(d['utf8_hex'])).hexdigest() == d['sha256'], 'invented captured bytes digest')
        else:
            need(d['sha256'] == ref['checkpoint_sha256'][str(d['size'])], 'periodic prefix checkpoint binding')
    q = sum(d['size'] // CHUNK + bool(d['size'] % CHUNK) for d in ds)
    need((q, q + 16*216, q + 22*216, 6*216 + 8 + 192) == (8799, 12255, 13551, 1496), 'independent reservations')
    saved = {Path(x['path']).name: x for x in p['evidence']}
    need(len(saved) == len(p['evidence']) == 15, 'exact 15 retained artifacts')
    artifact_hashes = [pinned(x) for x in p['evidence']]
    evdir = HERE / 'large-injected-evidence-v3'
    need(all(Path(x['path']).resolve().parent == evdir.resolve() for x in p['evidence']), 'fixed current evidence universe')
    schema_path = HERE.parent / 'recovery-step9-role-aware-producer-20261029' / 'ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v2.json'
    need(digest(schema_path)['sha256'] == FORMAT_SHA, 'pinned format metadata')
    schema = parse(schema_path.read_bytes())
    start = p['original_entry_monotonic']
    need(type(start) is float and start == attempt['original_entry_monotonic'] and p['work_end'] == start+295 and p['hard_end'] == start+300, 'one original clock')
    need(p['first_exception'] is None and p['evidence_publication_error'] is None and not p['monitor_violations'] and not p['audit_denials'], 'no unknown failure/veto')
    need(all(v is False for v in p['qualification'].values()), 'all real qualification false')
    first = p['first_actual_terminal']
    verified = p['positive_verification']
    need(first['issued'] is True and first['finalized'] is True and first['status'] == 'PURE_SEAM_COMPLETE_CONSISTENT' and first['errors'] == dict(primary=None, secondary=[]), 'actual genuine complete terminal summary')
    for key in ('origin', 'plan', 'byte_totals', 'api_counters', 'terminal', 'status', 'pure_seam_complete'):
        need(same(first[key], verified[key]), 'first terminal versus positive verification:' + key)
    need(all(v is True for v in first['terminal'].values()) and all(v is False for v in first['qualification'].values()), 'source ACKs not authority')
    need(p['actual_original_dispatches'] == 10095 and p['actual_read_dispatch_attempts'] == p['helper_completed_read_deliveries'] == 8799 and p['actual_close_attempts'] == p['canonical_known_successful_close_returns'] == 216 and p['helper_completed_delivery_bytes'] == 9017363601, 'precise attempted/completed summary counts')
    ledgers = []
    for terminal, filename in ((False, 'candidate-ledger.bin'), (True, 'terminal-ledger.bin')):
        path = evdir / filename
        hfile = path.open('rb')
        head = exact_bytes(hfile, 4096)
        h = fields(head, schema['header']['fields'])
        calls = 10095 if terminal else 9879
        expect_fields(h, dict(magic=b'RAPLEDG1', format_version=1, value_schema_version=2, profile=2, phase=2 if terminal else 1, status=1, header_bytes=4096, section_count=8, file_count=216, call_count=calls, module_count=2, diagnostic_count=0, edge_count=1, flags=64 if terminal else 0, total_bytes=saved[filename]['bytes'], captured_input_bytes=209, known_read_bytes=9017363601, hashed_bytes=9017363601, copied_bytes=209, origin_data_id=1, ledger_sequence=2 if terminal else 1, start_clock_bits=int.from_bytes(struct.pack('<d', start),'little'), clock_tags=42, previous_ledger_sha256=bytes.fromhex(saved['candidate-ledger.bin']['sha256']) if terminal else bytes(32), qualification_bits=0, reserved_R=12255, reserved_C=13551, reserved_E=1496, early_count=2, module_count_repeat=2, read_chunk=CHUNK, path_policy=1), 'independent actual header')
        for field in ('latest_clock_bits', 'freeze_clock_bits'):
            need(start <= struct.unpack('<d', h[field].to_bytes(8, 'little'))[0] < start+300, 'header raw clock window')
        sections = {}
        offset = 4096
        counts = (216, calls, 1775088, 9495, 2, 23, 1, 0)
        for i, spec in enumerate(schema['sections']):
            desc = fields(head[256+64*i:320+64*i], schema['section_descriptor']['fields'])
            expect_fields(desc, dict(id=i+1, record_size=spec['record_bytes'], count=counts[i], offset=offset, length=counts[i]*spec['record_bytes'], flags=0), 'section descriptor')
            hfile.seek(offset)
            dh = hashlib.sha256()
            remaining = desc['length']
            while remaining:
                raw = exact_bytes(hfile, min(65536, remaining)); dh.update(raw); remaining -= len(raw)
            need(dh.digest() == desc['sha256'], 'actual section digest')
            sections[spec['name']] = desc
            offset += desc['length']
        need(offset == saved[filename]['bytes'], 'complete contiguous ledger extent')
        ledgers.append(dict(name=filename, file=hfile, sections=sections, calls=calls))
    open_ordinals = []
    bases = []
    at = reads = 0
    pathoff = 0
    for i, d in enumerate(ds):
        qn = d['size']//CHUNK + bool(d['size']%CHUNK)
        open_ordinals.append(at); bases.append(reads); at += 5+qn; reads += qn
        for z, ledger in enumerate(ledgers):
            src = ledger['file']; src.seek(ledger['sections']['files']['offset'] + 256*i)
            row = fields(exact_bytes(src,256), schema['file_record']['fields'])
            names = {'EXPECTED_DIGEST_PRESENT','ACTUAL_DIGEST_PRESENT','HASH_ATTEMPTED','HASH_COMPLETE','EXPECTED_SIZE_PRESENT'}
            if i < 3: names |= {'CAPTURE_REQUESTED','CAPTURE_COMPLETE','BLOB_ISSUED'}
            if i < 2: names.add('EARLY')
            if z: names |= {'CLOSE_RESERVED','CLOSE_SUCCESS_KNOWN','CLOSE_SUCCESS_TRUE'}
            expect_fields(row, dict(ordinal=i, role=1 if i<2 else 2 if i==2 else 3, capture_state=2 if i<3 else 0, target_class=1, open_state=3, identity_state=2, close_state=3 if z else 0, flags=bitmask(schema,'file_flags_bits',names), descriptor_id=i, path_offset=pathoff, path_bytes=len(d['path'].encode()), path_utf16_units=len(d['path'].encode('utf-16-le'))//2, expected_size=d['size'], expected_sha256=bytes.fromhex(d['sha256']), actual_sha256=bytes.fromhex(d['sha256']), open_ordinal=open_ordinals[i], close_ordinal=9879+215-i if z else 0xffffffff, known_read_bytes=d['size'], hashed_bytes=d['size'], captured_bytes=d['size'] if i<3 else 0, query_offset=8218*i, query_length=8218, first_diagnostic=0xffffffff, read_reservations=qn, read_invocations=qn, captured_blob_length=d['size'] if i<3 else 0, early_ordinal=i if i<2 else 65535, path_id=i, read_generation=bases[i]+qn-1, module_ordinal=i if i<2 else 65535), 'independent file row')
            src.seek(ledger['sections']['paths']['offset']+pathoff)
            need(exact_bytes(src,len(d['path'].encode())) == d['path'].encode(), 'full original path bytes')
        pathoff += len(d['path'].encode())
    need((at,reads,pathoff)==(9879,8799,9495), 'complete independent positive geometry')
    totals = dict(rows=0,reads=0,known=0,hashed=0,copied=0,queries=0,query_bytes=0,closes=0)
    by_api = {name:0 for name in API}
    delivered = [0]*216
    closes = [0]*216
    last_post = start
    with (evdir/'independent-canonical-raw-facts.jsonl').open('rb') as rawfile, (evdir/'independent-original-dispatches.bin').open('rb') as spyfile, (evdir/'independent-canonical-query-frames.bin').open('rb') as queries:
        for j, (i, api, requested, generation) in enumerate(sequence(ds)):
            line = rawfile.readline(4097)
            need(line.endswith(b'\n') and len(line)<=4096, 'bounded LF raw sidecar row')
            row = parse(line)
            need(canonical(row)==line, 'canonical raw row')
            spy = SPY.unpack(exact_bytes(spyfile,64))
            d=ds[i]; read=api==API[5]; query=api in API[2:5]; captured=i<3; handle=1000+i
            scalar=handle if api==API[0] else len(('\\\\?\\'+d['path']).encode('utf-16-le'))//2 if api==API[3] else 1
            qraw=frame(d,api) if query else None
            qgen=3*i+API[2:5].index(api) if query else generation if read else None
            pre=row['clocks']['pre_raw']; post=row['clocks']['post_raw']
            need(pre['tag']==post['tag']=='FLOAT64_BITS', 'actual raw F64 clocks')
            pretime=struct.unpack('<d',bytes.fromhex(pre['bits']))[0]; posttime=struct.unpack('<d',bytes.fromhex(post['bits']))[0]
            need(last_post<=pretime<=spy[6]<=spy[7]<=posttime<start+(300 if api==API[6] else 295), 'independent actual call clock order')
            last_post=posttime
            expected_query=dict(capture_observed=False, offset=None, bytes=None, sha256=None)
            if query:
                need(exact_bytes(queries,len(qraw))==qraw, 'exact canonical query sidecar bytes')
                expected_query=dict(capture_observed=True, offset=totals['query_bytes'], bytes=len(qraw), sha256=hashlib.sha256(qraw).hexdigest())
                totals['queries']+=1; totals['query_bytes']+=len(qraw)
                for ledger in ledgers:
                    src=ledger['file']; src.seek(ledger['sections']['queries']['offset']+expected_query['offset'])
                    need(exact_bytes(src,len(qraw))==qraw, 'both ledgers exact retained query bytes')
            expected=dict(schema_version=1, ordinal=j,file_id=i,api=api,prepared=True,invoked=True,scalar=atom('INT',scalar),count=atom('INT',requested) if read else U,error=U,error_definition=U,input_handle=U if api==API[0] else atom('INT',handle),wrapper_return_observed=True,wrapper_state='returned',stopped=False,close_right_consumed=api==API[6],auxiliary=dict(scalar_ack=False,count_ack=False,right_transfer_ack=False),reservation_fold='committed',read_fold=dict(phase='committed' if read else 'pending',contribution=requested if read else None),hash=dict(attempted=read,raw_return=NULL if read else U,stored_count_field=0,fold_phase='applied' if read else 'pending'),copy=dict(attempted=read and captured,raw_return=NULL if read and captured else U,stored_count_field=0,fold_phase='applied' if read and captured else 'pending'),clocks=dict(pre_attempted=True,pre_raw=pre,post_attempted=True,post_raw=post),buffer=dict(present=read or query,generation=qgen,state='raw_retained' if read else 'defined' if query else 'not_applicable',written=requested if read else len(qraw) if query else 0),query=expected_query)
            need(same(row,expected), 'entire raw row versus independent facts')
            need(spy[:6]==(j,i,API.index(api)+1,requested,requested if read else 0,scalar) and spy[8:]==(generation,15 if read else 11,handle), 'spy observed values/completed hooks versus independent recipe')
            flags={'INVOKED','SCALAR_OBSERVED','WRAPPER_RETURNED','SCALAR_DOMAIN_VALID','PRE_CLOCK_ATTEMPTED','POST_CLOCK_ATTEMPTED','PRE_CLOCK_RETURN_OBSERVED','POST_CLOCK_RETURN_OBSERVED'}
            if api!=API[0]:flags.add('INPUT_HANDLE_PRESENT')
            if captured:flags.add('CAPTURE_REQUESTED')
            if read or query:flags |= {'BUFFER_PRESENT','BUFFER_DATA_OBSERVED'}
            if query:flags |= {'QUERY_CAPTURE_OBSERVED','QUERY_DEFINED','QUERY_SPAN_PRESENT'}
            if read:flags |= {'COUNT_OBSERVED','COUNT_DEFINED','COUNT_DOMAIN_VALID','IDENTITY_VERIFIED_AT_DISPATCH','REQUESTED_PRESENT','HASH_ATTEMPTED','HASH_RETURN_OBSERVED'}
            if read and captured:flags |= {'COPY_ATTEMPTED','COPY_RETURN_OBSERVED'}
            if api==API[6]:flags.add('CLOSE_RIGHT_CONSUMED')
            for ledger in ledgers:
                if j>=ledger['calls']:continue
                src=ledger['file'];src.seek(ledger['sections']['calls']['offset']+256*j)
                wire=fields(exact_bytes(src,256),schema['call_record']['fields'])
                expect_fields(wire,dict(ordinal=j,file_id=i,api=API.index(api)+1,record_version=1,fact_flags=bitmask(schema,'call_flags_bits',flags),requested=requested,buffer_id=0 if read else 1 if query else 65535,phase=schema['enums']['phase_code']['original_close' if api==API[6] else 'binding_invoke'],generation=qgen or 0,buffer_written=requested if read else len(qraw) if query else 0,raw_scalar_bits=scalar,raw_count=requested if read else 0,raw_error=0,hashed_contribution=requested if read else 0,captured_contribution=requested if read and captured else 0,known_count_contribution=requested if read else 0,query_offset=expected_query['offset'] if query else 0,query_length=len(qraw) if query else 0,input_handle_bits=0 if api==API[0] else handle,pre_dispatch_clock_bits=int.from_bytes(bytes.fromhex(pre['bits']),'little'),post_binding_clock_bits=int.from_bytes(bytes.fromhex(post['bits']),'little'),error_id=0xffffffff,path_id=i,reserved_zero=0,fold_state=2 if read else 0,buffer_state=2 if read else 3 if query else 0),'actual complete call wire')
            totals['rows']+=1;by_api[api]+=1
            if read:
                totals['reads']+=1;totals['known']+=requested;totals['hashed']+=requested;totals['copied']+=requested if captured else 0;delivered[i]+=requested
            if api==API[6]:totals['closes']+=1;closes[i]+=1
        need(rawfile.read(1)==spyfile.read(1)==queries.read(1)==b'', 'no raw/spy/query trailing or omitted data')
    need(totals==dict(rows=10095,reads=8799,known=9017363601,hashed=9017363601,copied=209,queries=648,query_bytes=1775088,closes=216), 'all streamed independent totals')
    close_facts=parse((evdir/'independent-close-facts.json').read_bytes())
    need(same(close_facts,dict(opened=[True]*216,close_counts=closes,delivered=delivered)) and closes==[1]*216 and delivered==[d['size'] for d in ds], 'retained close/delivery facts exactly once')
    for api,n in by_api.items():
        need(first['api_counters'][api]==dict(reserved=n,invocations=n,scalar_returns=n,wrapper_returns=n,count_values=n if api==API[5] else 0), 'source API counters versus independent rows')
    for ledger in ledgers:
        src=ledger['file'];sections=ledger['sections']
        for i,name in enumerate(('cohort_leaf','cohort_entry')):
            src.seek(sections['modules']['offset']+64*i)
            row=fields(exact_bytes(src,64),schema['module_record']['fields'])
            expect_fields(row,dict(ordinal=i,file_ordinal=i,flags=14,dependency_count=i,name_offset=0 if i==0 else 11,name_length=len(name),edge_offset=0,first_diagnostic=0xffffffff,attempt_order=1-i,return_order=i,cache_hit_count=0),'independent closed module row')
        src.seek(sections['module_names']['offset']);need(exact_bytes(src,23)==b'cohort_leafcohort_entry','complete module names')
        src.seek(sections['module_edges']['offset']);need(exact_bytes(src,2)==bytes(2),'exact entry to leaf edge')
        src.close()
    consumption=parse((evdir/'independent-ledger-consumption.json').read_bytes())
    need(same(consumption,p['consumer_passes']), 'separately retained full-consumer record')
    for i,c in enumerate(consumption):
        need(c['complete'] is True and c['kind']==ledgers[i]['name'] and c['counts']==dict(header=1,files=216,calls=9879 if i==0 else 10095,modules=2,module_edges=1,diagnostics=0,queries=1,paths=1,module_names=1), 'actual full consumer exact cardinalities')
        need(c['pool_bytes']==dict(queries=1775088,paths=9495,module_names=23) and 0<=c['elapsed_start']<=c['elapsed_end']<300, 'actual full consumer pool extent/window')
    callbacks=parse((evdir/'independent-sink-callback-metadata.json').read_bytes())
    appends=[];other=[];last=start
    for c in callbacks:
        need(all(c[k] is True for k in ('ack_supplied','return_prepared','source_acknowledged','source_return_observed')), 'prepared ACK separately observed by source')
        need(last<=c['entry']<=c['prepared_at']<start+300,'one monotonic callback window');last=c['prepared_at']
        if c['target']=='append':appends.append(c['sequence'])
        else:other.append(c['target'])
    need(other==['reserve','publish_candidate','publish_cleanup','close_journal','publish_receipt','publish_seal'] and appends==list(range(1331)), 'callback once order / contiguous ACK journal')
    events=0;elapsed=0.0
    with (evdir/'journal.jsonl').open('rb') as src:
        for line in src:
            need(len(line)<=1024 and line.endswith(b'\n'),'bounded complete journal row')
            row=parse(line);need(canonical(row)==line and set(row)=={'sequence','event','stage','kind','file_id','module','elapsed'},'exact journal framing')
            need(type(row['sequence']) is int and row['sequence']==events and type(row['elapsed']) is float and elapsed<=row['elapsed']<300,'journal sequence/time')
            elapsed=row['elapsed'];events+=1
    need(events==first['plan']['events_used']==1331 and saved['journal.jsonl']['sha256']==saved['independent-callback-journal.jsonl']['sha256'],'all actual acknowledged journal rows retained')
    packet_summaries={}
    for kind in ('candidate','cleanup','receipt','seal'):
        raw=(evdir/(kind+'.json')).read_bytes(); packet=parse(raw)
        need(len(raw)<=8192 and canonical(packet)==raw and len(packet)==11 and packet['kind']==kind and packet['schema_version']==2 and packet['scope']=='role_aware_producer_format_v1' and packet['status']=='OBSERVED_COMPLETE','actual bounded canonical packet alias')
        need(all(v is False for v in packet['qualification'].values()) and packet['diagnostic_counts']==dict(committed=0,formatter=0,primary=0,secondary=0),'packet qualification/diagnostics')
        for value in (*packet['ledger_refs'].values(),*packet['links'].values()):
            if value is None:continue
            target=saved[value['kind']]
            need((value['bytes'],value['sha256'])==(target['bytes'],target['sha256']),'causal packet artifact link')
        need(packet['links']['receipt'] is None if kind!='seal' else packet['links']['receipt']['kind']=='receipt.json','acyclic receipt/seal links')
        packet_summaries[kind]=dict(bytes=len(raw),sha256=saved[kind+'.json']['sha256'])
    report_data=parse((evdir/'producer-report.json').read_bytes())
    need(report_data['counts']==dict(M=2,N=216,used_C=10095,used_E=1330) and all(v is False for v in report_data['qualification'].values()),'phase frozen report is earlier than own append ACK')
    need(report_data['totals']['known_read_bytes']==report_data['totals']['hashed_bytes']==9017363601 and report_data['totals']['copied_bytes']==209, 'phase report raw totals')
    need(p['source_stack_unwound_elapsed']<300 and first['origin']['now']<start+300,'actual original source window')
    need(p['canonical_raw_sidecar']==dict(bytes=saved['independent-canonical-raw-facts.jsonl']['bytes'],query_bytes=1775088,rows_expected=10095,rows_written=10095,state='COMPLETE_EXISTING_FACTS',unencodable_atoms=0),'first raw sidecar progress exact')
    return dict(status='CLEAR_SOURCE_PURE_LARGE_GENERATED_RESULT_ONLY',material_blockers=[],proof=pinned(dict(path=str(proof_path),bytes=len(proof_path.read_bytes()),sha256=PROOF_SHA)),binding=bp,checked_input_pins=pin_results,retained_artifacts=artifact_hashes,streamed_totals=totals,api_invocations=by_api,actual_source_elapsed=p['source_stack_unwound_elapsed'],separate_harness_persistence_elapsed=p['evidence_publication_elapsed'],candidate=dict(bytes=saved['candidate-ledger.bin']['bytes'],sha256=saved['candidate-ledger.bin']['sha256'],calls=9879),terminal=dict(bytes=saved['terminal-ledger.bin']['bytes'],sha256=saved['terminal-ledger.bin']['sha256'],calls=10095),packets=packet_summaries,journal_rows=1331,sink_callbacks=len(callbacks),consumer_passes=2,independent_binary_rows=dict(files=432,calls=19974,modules=4,edges=2),checks=CHECKS,qualification=p['qualification'],activity=dict(subject_imports=0,producer_runs=0,native_calls=0,old_payload_operations=0,bulk_generation_or_rehash=0),limits='One retained synthetic periodic 216-descriptor result. Digest/slot identity is verified from immutable retained evidence and previously reviewed genuine source paths, not reconstructed live authority. Independent reference preparation and harness persistence are separate from owner time. No empirical RSS/commit/VRAM/Job fit, physical output/readback, actual first entry/FFI, complete real roster, distinct84/native protocol or scientific qualification. Earlier failures and consumed original experiment remain unchanged.')


if __name__ == '__main__':
    try:
        result=run()
    except BaseException as error:
        result=dict(status='HOLD_RETAINED_EVIDENCE_REVIEW_FAILED',material_blockers=[dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())],checks=CHECKS,activity=dict(subject_imports=0,producer_runs=0,native_calls=0))
    result['checker']=digest(Path(__file__))
    with REPORT.open('xb') as out:
        out.write((json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
    print(json.dumps(dict(status=result['status'],checks=result['checks'],report=digest(REPORT))))
    raise SystemExit(0 if result['status'].startswith('CLEAR_') else 1)
