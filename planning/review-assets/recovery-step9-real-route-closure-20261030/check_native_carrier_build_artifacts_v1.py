"""Own retained build bytes only. No SDK tool, image or C subject execution."""
import hashlib
import json
from pathlib import Path
import re
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BUILD = ROOT / 'data/cache/r09-native-carrier-component-build-20261030T055706Z'
OUT = HERE / 'NATIVE-CARRIER-BUILD-ARTIFACT-CHECK-v1.json'
checks = []


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    path = Path(path).resolve(); raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=sha(raw))


def check(name, value, detail=None):
    checks.append(dict(name=name, passed=bool(value), detail=detail))


def unpack(raw, offset, fmt):
    return struct.unpack_from('<' + fmt, raw, offset)


def asm_functions(text):
    functions = {}; current = None; pending = None
    for line in text.splitlines():
        start = re.match(r'^(\w+)\s+PROC\b', line)
        if start:
            current = start[1]; functions[current] = []; pending = None
            continue
        if re.match(r'^\w+\s+ENDP\b', line):
            assert pending is None
            current = None
        if current is None:
            continue
        start = re.match(r'^\s+([0-9a-fA-F]{5})\t(.*)$', line)
        if start:
            assert pending is None
            offset = int(start[1], 16); columns = start[2].split('\t')
            tokens = columns[0].strip().split()
            assert tokens and all(re.fullmatch(r'[0-9a-fA-F]{2}', t) for t in tokens)
            pending = dict(offset=offset, bytes=bytes.fromhex(' '.join(tokens)),
                           instruction=' '.join(c.strip() for c in columns[1:] if c.strip()))
        elif pending is not None:
            columns = line.lstrip('\t ').split('\t'); tokens = columns[0].strip().split()
            assert tokens and all(re.fullmatch(r'[0-9a-fA-F]{2}', t) for t in tokens)
            pending['bytes'] += bytes.fromhex(' '.join(tokens))
            pending['instruction'] = ' '.join(c.strip() for c in columns[1:] if c.strip())
        if pending is not None and pending['instruction']:
            functions[current].append(pending); pending = None
    return functions


def coff(raw):
    machine, count, timestamp, symbols_at, symbols_n, optional, flags = unpack(raw, 0, 'HHIIIHH')
    assert machine == 0x8664 and optional == 0
    strings_at = symbols_at + symbols_n * 18
    strings = raw[strings_at:]
    string_bytes, = unpack(strings, 0, 'I')
    assert string_bytes <= len(strings)

    def name(value):
        if value[:4] == b'\0' * 4:
            index, = unpack(value, 4, 'I')
            return strings[index:strings.index(0, index)].decode('ascii')
        return value.rstrip(b'\0').decode('ascii')

    sections = []
    for i in range(count):
        off = 20 + i * 40
        label = raw[off:off + 8].rstrip(b'\0').decode('ascii')
        size, pointer, reloc_at, ignored, reloc_n = unpack(raw, off + 16, 'IIIIH')
        assert pointer + size <= len(raw)
        relocs = [unpack(raw, reloc_at + j * 10, 'IIH') for j in range(reloc_n)]
        sections.append(dict(name=label, raw=raw[pointer:pointer + size], relocs=relocs))
    symbols = {}; index = 0
    while index < symbols_n:
        label, value, section, kind, storage, aux = unpack(raw, symbols_at + index * 18, '8sIhHBB')
        symbols[name(label)] = dict(index=index, value=value, section=section, kind=kind, storage=storage)
        index += aux + 1
    return sections, symbols


def pe_text(raw):
    assert raw[:2] == b'MZ'
    pe, = unpack(raw, 0x3c, 'I')
    assert raw[pe:pe + 4] == b'PE\0\0'
    machine, count, timestamp, symbols, symbol_count, optional_n, flags = unpack(raw, pe + 4, 'HHIIIHH')
    assert machine == 0x8664 and unpack(raw, pe + 24, 'H')[0] == 0x20b
    for i in range(count):
        off = pe + 24 + optional_n + i * 40
        label = raw[off:off + 8].rstrip(b'\0')
        virtual_size, rva, size, pointer = unpack(raw, off + 8, 'IIII')
        if label == b'.text':
            assert pointer + size <= len(raw)
            return raw[pointer:pointer + size], rva
    raise ValueError('linked image lacks .text')


result = json.loads((BUILD / 'build-result.json').read_bytes())
check('exact_first_build_result', pin(BUILD / 'build-result.json')['sha256'] ==
      '9275174036dfab54a50fea143cd3d547e5dbadd5e41af559d95b4eacbfc4fa8e')
check('built_not_executed_clean', result['status'] == 'BUILT_NOT_EXECUTED' and
      result['failure'] is None and not result['secondary_errors'] and result['artifact_inventory_complete']
      and result['executable_dispatches'] == result['original_payload_reads'] == 0)
check('three_known_commands', [row['label'] for row in result['commands']] ==
      ['compile-carrier', 'compile-tests', 'link-tests'] and all(row['returncode'] == 0 and
      row['output_complete'] and row['main_exit_observed'] and row['primary_error'] is None and
      not row['cleanup_errors'] for row in result['commands']))
artifact_pins = []
for value in result['artifacts']:
    path = (ROOT / value['path']).resolve()
    assert path.parent == BUILD.resolve()
    actual = pin(path)
    check('artifact/' + path.name, actual['bytes'] == value['bytes'] and actual['sha256'] == value['sha256'])
    artifact_pins.append(actual)
check('inventory_exact', {p.name for p in BUILD.iterdir()} ==
      {Path(v['path']).name for v in result['artifacts']} | {'build-result.json'})
journal = (BUILD / 'build-journal.jsonl').read_bytes().splitlines()
tip = '0' * 64; journal_rows = []
for index, raw in enumerate(journal):
    value = json.loads(raw)
    assert value['sequence'] == index and value['previous_sha256'] == tip
    tip = sha(raw); journal_rows.append(value)
check('eight_acknowledged_journal_rows', len(journal) == result['events'] == result['journal_acknowledged_events'] == 8
      and result['journal_complete'] is True and tip == result['journal_final_hash'])
check('journal_command_results_match', [row for row in journal_rows if row['kind'] == 'dispatch_returned_or_failed'] ==
      [dict(row, kind='dispatch_returned_or_failed', sequence=journal_rows[i]['sequence'],
            previous_sha256=journal_rows[i]['previous_sha256'], elapsed_seconds=journal_rows[i]['elapsed_seconds'])
       for row, i in zip(result['commands'], (2, 4, 6))])
check('original_build_budget', result['elapsed_seconds'] < 60 and
      all(0 <= row['elapsed_seconds'] <= result['elapsed_seconds'] for row in journal_rows))

listing = (BUILD / 'carrier.asm').read_bytes().decode('ascii')
functions = asm_functions(listing)
sections, symbols = coff((BUILD / 'carrier.obj').read_bytes())
image_text, image_rva = pe_text((BUILD / 'native-carrier-fake-tests.exe').read_bytes())
names = ['pf14_create_file', 'pf14_get_type', 'pf14_get_information', 'pf14_get_path',
         'pf14_get_size', 'pf14_read', 'pf14_close', 'pf14_get_attributes',
         'pf14_find_first', 'pf14_find_next', 'pf14_find_close', 'pf14_create_directory',
         'pf14_write', 'pf14_flush']
machine_maps = {}; coverage_bytes = 0
for name in names + ['pf14_initialize', 'publish', 'finish', 'begin', 'metadata_valid']:
    symbol = symbols[name]; section = sections[symbol['section'] - 1]
    body = section['raw'][symbol['value']:]
    mask = [True] * len(body)
    for offset, target, kind in section['relocs']:
        assert kind == 4  # AMD64_REL32, the four-byte linker displacement only.
        for j in range(offset - symbol['value'], offset - symbol['value'] + 4):
            assert 0 <= j < len(mask); mask[j] = False
    for instruction in functions[name]:
        start = instruction['offset']; expected = instruction['bytes']
        assert body[start:start + len(expected)] == expected
        coverage_bytes += len(expected)
    prefix_n = next((i for i, value in enumerate(mask) if not value), len(body))
    assert prefix_n >= 8
    anchor = body[:prefix_n]; candidates = []; start = 0
    while True:
        at = image_text.find(anchor, start)
        if at < 0:
            break
        if at + len(body) <= len(image_text) and all(not keep or image_text[at + i] == byte
                 for i, (byte, keep) in enumerate(zip(body, mask))):
            candidates.append(at)
        start = at + 1
    check('listing_object_image/' + name, len(candidates) == 1)
    machine_maps[name] = dict(coff_section=symbol['section'], object_bytes=len(body),
        listing_instructions=len(functions[name]), image_matches=len(candidates),
        image_RVA=None if len(candidates) != 1 else image_rva + candidates[0],
        link_relocation_count=len(section['relocs']))

resolved_local_calls = []
symbol_by_index = {value['index']: name for name, value in symbols.items()}
for name, mapping in machine_maps.items():
    if mapping['image_RVA'] is None:
        continue
    section = sections[symbols[name]['section'] - 1]
    for offset, index, kind in section['relocs']:
        target = symbol_by_index.get(index)
        if target not in machine_maps or machine_maps[target]['image_RVA'] is None:
            continue
        at = mapping['image_RVA'] - image_rva + offset - symbols[name]['value']
        displacement, = unpack(image_text, at, 'i')
        actual_target = image_rva + at + 4 + displacement
        wanted_target = machine_maps[target]['image_RVA']
        check('linked_local_call/' + name + '/' + str(offset), actual_target == wanted_target)
        resolved_local_calls.append(dict(source=name, offset=offset, target=target,
                                         actual_RVA=actual_target, expected_RVA=wanted_target))

wrappers = []
for api, name in enumerate(names, 1):
    instructions = functions[name]
    calls = [(i, row) for i, row in enumerate(instructions)
             if re.match(r'^call (?:QWORD PTR \[|r[a-z0-9]+\b)', row['instruction'])]
    assert len(calls) == 1
    index, call = calls[0]
    after = instructions[index + 1:]
    store_i = next(i for i, row in enumerate(after) if re.match(
        r'^mov (?:DWORD|QWORD) PTR \[[^]]+\],', row['instruction']))
    store = after[store_i]
    width = 'QWORD' if api in (1, 9) else 'DWORD'
    returned = 'rax' if width == 'QWORD' else 'eax'
    check('first_scalar_store/' + name,
          bool(re.fullmatch(r'mov ' + width + r' PTR \[rsi\+128\], ' + returned, store['instruction']))
          and all(not row['instruction'].startswith(('call ', 'push ', 'xchg ')) for row in after[:store_i]))
    check('store_then_publish/' + name, after[store_i + 1]['instruction'] == 'call publish')
    operand = call['instruction'][5:]
    table = operand
    if operand == 'rax':
        table = next(row['instruction'].split(', ', 1)[1] for row in reversed(instructions[:index])
                     if re.match(r'^mov rax, QWORD PTR \[rdi(?:\+\d+)?\]$', row['instruction']))
    expected_table = 'QWORD PTR [rdi' + ('' if api == 1 else '+' + str(8 * (api - 1))) + ']'
    check('typed_function_table_slot/' + name, table == expected_table)
    wrappers.append(dict(api=api, function=name, target_call_offset=call['offset'],
        target_call=call['instruction'], function_table_slot=table, scalar_store_offset=store['offset'],
        scalar_store=store['instruction'], intervening_register_only=[r['instruction'] for r in after[:store_i]],
        publish_offset=after[store_i + 1]['offset'], linked_image_RVA=machine_maps[name]['image_RVA']))

publication = [row['instruction'] for row in functions['publish']]
check('publish_stage_then_atomic_commit', publication == ['mov eax, 1', 'mov DWORD PTR [rcx+16], eax',
      'xchg DWORD PTR [rcx+20], eax', 'ret 0'])
finish = [row['instruction'] for row in functions['finish']]
check('error_transport_slot_and_direct_DWORD_store', 'call QWORD PTR [rdx+112]' in finish and
      'mov DWORD PTR [rdi+192], eax' in finish and finish.index('call QWORD PTR [rdx+112]') <
      finish.index('mov DWORD PTR [rdi+192], eax'))
check('count_scratch_and_exit_phase', 'mov eax, DWORD PTR [rdi+64]' in finish and
      'mov DWORD PTR [rcx], eax' in finish and 'xchg DWORD PTR [rdi+72], eax' in finish)

report = dict(schema_version=1, status='PASS' if all(row['passed'] for row in checks) else 'HOLD',
    checker=pin(__file__), build_result=pin(BUILD / 'build-result.json'), checks=checks,
    counts=dict(checks=len(checks), passed=sum(row['passed'] for row in checks),
                failed=sum(not row['passed'] for row in checks), artifacts=len(artifact_pins),
                artifact_bytes=sum(row['bytes'] for row in artifact_pins), wrappers=len(wrappers),
                listing_instruction_bytes_matched_to_object=coverage_bytes),
    artifact_pins=artifact_pins, wrappers=wrappers, compiled_function_maps=machine_maps,
    resolved_local_calls=resolved_local_calls,
    exact_scope='Own new build bytes only: compiler listing instructions match COFF bytes; linkedPE function bodies match every non-REL32 byte, with a unique location. No compiler or executable was invoked. REL32 displacements are linker-mutated bytes, not silently compared as unchanged.',
    actual_process_execution_by_reviewer=0, SDK_or_FFI_calls=0, original_target_reads=0,
    qualification='Compiled layout/assertion and local selected-image ordering only. No C fake-target execution, actual Win32, genuine Core bank/ticket/lifetime, physical14/nativeinput or resource qualification.')
with OUT.open('xb') as stream:
    stream.write((json.dumps(report, indent=2, sort_keys=True) + '\n').encode())
print(json.dumps(dict(status=report['status'], report=pin(OUT), counts=report['counts'])))
