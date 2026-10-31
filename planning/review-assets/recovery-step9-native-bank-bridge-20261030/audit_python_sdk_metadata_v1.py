"""Read-only, bounded source/PE/COFF metadata audit. Never loads target images."""
from pathlib import Path
import collections
import datetime
import hashlib
import json
import re
import struct

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = Path('C:/Users/zzric/AppData/Roaming/uv/python/cpython-3.11-windows-x86_64-none')
VENV = ROOT / 'data/cache/recovery-step9-generation-wheel-20261028/environment'
OLD = ROOT / 'planning/review-assets/recovery-step9-real-route-closure-20261030'


def pin(path):
    path = path.resolve()
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def pe(path):
    raw = path.read_bytes()
    def get(fmt, offset):
        assert 0 <= offset <= len(raw)-struct.calcsize(fmt)
        return struct.unpack_from(fmt, raw, offset)
    assert raw[:2] == b'MZ'
    off = get('<I', 0x3c)[0]
    assert raw[off:off+4] == b'PE\0\0'
    machine, count, stamp, _, _, optional_bytes, characteristics = get('<HHIIIHH', off+4)
    assert 0 < count <= 96
    opt = off+24
    assert get('<H', opt)[0] == 0x20b and optional_bytes >= 112
    directories = get('<I', opt+108)[0]
    assert min(directories, 16)*8+112 <= optional_bytes
    sections = []
    for i in range(count):
        q = opt+optional_bytes+40*i
        name, virtual_size, rva, size, pointer = get('<8sIIII', q)
        assert pointer+size <= len(raw)
        sections.append((name.rstrip(b'\0').decode('ascii'), rva, virtual_size, pointer, size))
    def position(rva, size=1):
        for _, va, vs, ptr, physical in sections:
            if va <= rva and rva+size <= va+physical:
                return ptr+rva-va
        raise ValueError(('unmapped physical RVA', rva, size))
    def string(rva):
        q = position(rva)
        end = raw.find(b'\0', q, min(len(raw), q+4096))
        assert end >= q
        return raw[q:end].decode('ascii')
    def directory(index):
        return get('<II', opt+112+8*index) if directories > index else (0,0)
    imports = []
    rva, size = directory(1)
    if rva:
        assert size <= 1048576
        for i in range(size//20):
            values = get('<IIIII', position(rva+20*i, 20))
            if values == (0,0,0,0,0):
                break
            imports.append(string(values[3]))
        else:
            raise ValueError('No bounded import terminator')
    exports = []
    rva, size = directory(0)
    if rva:
        values = get('<IIHHIIIIIII', position(rva,40))
        names, name_rva = values[7], values[9]
        assert names < 100000
        for i in range(names):
            exports.append(string(get('<I',position(name_rva+4*i,4))[0]))
    fixed_versions=[]
    start=0
    while True:
        q=raw.find(struct.pack('<I',0xfeef04bd),start)
        if q<0: break
        start=q+4
        if q+52 <= len(raw):
            vals=get('<13I',q)
            fixed_versions.append({'offset':q,'structure_version':hex(vals[1]),'file_version':[vals[2]>>16,vals[2]&65535,vals[3]>>16,vals[3]&65535],'product_version':[vals[4]>>16,vals[4]&65535,vals[5]>>16,vals[5]&65535]})
    return {'pin':pin(path),'machine':hex(machine),'machine_is_amd64':machine==0x8664,'optional_magic':'0x20b','DLL_characteristic':bool(characteristics&0x2000),'linker_version':list(get('<BB',opt+2)),'timestamp_word':stamp,'timestamp_is_publication_proof':False,'imports':imports,'export_count':len(exports),'export_names':exports,'fixed_version_signature_candidates':fixed_versions,'parse_scope':'Bounded PE headers/import descriptor names/named exports and raw fixed-version signature candidates; no loader, relocation, signature, full resources or dependency closure.'}


def import_archive(path):
    raw=path.read_bytes()
    assert raw[:8]==b'!<arch>\n'
    q=8; members=[]; short=[]; machines=collections.Counter()
    while q<len(raw):
        assert q+60<=len(raw) and raw[q+58:q+60]==b'`\n'
        name=raw[q:q+16].decode('ascii').strip()
        size=int(raw[q+48:q+58])
        data=raw[q+60:q+60+size]
        assert len(data)==size
        kind='archive_index_or_long_names'
        machine=None
        if name not in ('/','//'):
            if data[:4]==b'\0\0\xff\xff':
                sig1,sig2,version,machine,stamp,size_data,hint,type_word=struct.unpack_from('<HHHHIIHH',data)
                assert len(data)>=20+size_data and version==0
                words=data[20:20+size_data].split(b'\0')
                assert len(words)>=3
                short.append({'symbol':words[0].decode('ascii'),'DLL':words[1].decode('ascii'),'machine':hex(machine),'kind':type_word&3,'name_type':(type_word>>2)&7})
                kind='short_import'
            else:
                assert len(data)>=20
                machine=struct.unpack_from('<H',data)[0]
                kind='ordinary_COFF'
            machines[hex(machine)]+=1
        members.append({'name':name,'bytes':size,'kind':kind,'machine':hex(machine) if machine is not None else None})
        q+=60+size+(size&1)
        assert len(members)<100000
    assert q==len(raw)
    return {'pin':pin(path),'archive_members':len(members),'member_kind_counts':dict(collections.Counter(x['kind'] for x in members)),'machine_counts':dict(machines),'all_object_members_amd64':set(machines)=={'0x8664'},'short_import_count':len(short),'DLL_names':sorted(set(x['DLL'] for x in short)),'short_imports':short,'parse_scope':'Archive member framing, ordinary COFF machine words and version0 short import object headers; no linker execution or complete linker-index validation.'}


binding_path=OLD/'NATIVE-CARRIER-COMPONENT-BUILD-BINDING-v1.json'
binding=json.loads(binding_path.read_text())
env_path=ROOT/binding['inputs']['build_environment']['path']
environment=json.loads(env_path.read_text())
includes=[Path(s).resolve() for s in environment['INCLUDE'].split(';') if s]
libraries=[Path(s).resolve() for s in environment['LIB'].split(';') if s]
python_include=BASE/'include'
seen=set(); pending=[python_include/'Python.h']; edges=[]; quoted_missing=[]; angles=collections.defaultdict(list)
while pending:
    p=pending.pop().resolve()
    if p in seen:continue
    seen.add(p)
    assert p.is_relative_to(python_include.resolve()) and len(seen)<1024
    text=p.read_text(encoding='utf-8',errors='strict')
    for line_no,line in enumerate(text.splitlines(),1):
        match=re.match(r'^\s*#\s*include\s*([<\"])([^>\"\n]+)[>\"]',line)
        if not match:continue
        delimiter,name=match.groups()
        if delimiter=='<':angles[name].append({'from':str(p),'line':line_no});continue
        resolved=next((x.resolve() for x in (p.parent/name,python_include/name) if x.is_file()),None)
        edge={'from':str(p),'line':line_no,'include':name,'resolved':str(resolved) if resolved else None}
        edges.append(edge)
        if resolved is None:quoted_missing.append(edge)
        else:pending.append(resolved)
system_headers=[]
for name,sites in sorted(angles.items()):
    p=next((d/name for d in includes if (d/name).is_file()),None)
    system_headers.append({'name':name,'sites':sites,'pin':pin(p) if p else None,'missing_meaning':'Non-preprocessed all-conditional textual closure; absence may be an inactive non-Windows branch.' if p is None else None})
selected_headers=[]
for name in ('windows.h','winnt.h','fileapi.h','errhandlingapi.h','synchapi.h','intrin.h','vcruntime.h','corecrt.h'):
    p=next((d/name for d in includes if (d/name).is_file()),None)
    selected_headers.append({'name':name,'pin':pin(p) if p else None})
selected_libs=[]
for name in ('kernel32.lib','msvcrt.lib','vcruntime.lib','ucrt.lib','libcmt.lib','libvcruntime.lib','libucrt.lib'):
    p=next((d/name for d in libraries if (d/name).is_file()),None)
    selected_libs.append({'name':name,'pin':pin(p) if p else None,'meaning':'Installed candidate under inherited selected LIB search directories, not a new extension link selection.'})
images={name:pe(p) for name,p in [('venv_python',VENV/'Scripts/python.exe'),('base_python',BASE/'python.exe'),('base_python311',BASE/'python311.dll'),('base_python3',BASE/'python3.dll'),('base_vcruntime140',BASE/'vcruntime140.dll'),('base_vcruntime140_1',BASE/'vcruntime140_1.dll')]}
archive=import_archive(BASE/'libs/python311.lib')
required=['PyLong_Type','PyLong_AsUnsignedLongLong','PyObject_GetBuffer','PyBuffer_Release','PyErr_Fetch','PyErr_Restore','PyErr_Occurred','PyErr_NormalizeException','PyObject_GC_Track','PyObject_GC_UnTrack','PyObject_GC_Del','_PyObject_GC_New','PyType_FromSpec','PyModule_Create2','_Py_Dealloc']
symbols=set(x['symbol'] for x in archive['short_imports'])
exports=set(images['base_python311']['export_names'])
symbol_checks=[{'symbol':n,'in_import_archive':n in symbols,'in_runtime_named_exports':n in exports} for n in required]
old_pin_checks=[]
for key in ('build_environment','toolchain_probe','compiler','linker'):
    old=binding['inputs'][key]
    p=Path(old['path'])
    if not p.is_absolute():p=ROOT/p
    actual=pin(p)
    old_pin_checks.append({'key':key,'expected':old,'actual':actual,'matches':actual['bytes']==old['bytes'] and actual['sha256']==old['sha256']})
report={'schema_version':1,'status':'LOCAL_PREREQUISITES_PRESENT_STATIC_METADATA_ONLY','reviewed_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reviewer':'/root/bridge_design_peer','scope':'Exact configured local Python3.11 headers/import library/runtime PE and inherited installed toolchain metadata only. No target image load, compiler, executable, import or subject/native/model action. No whole ABI equivalence or dependency/load closure.','helper':pin(Path(__file__)),'venv_configuration':{'pin':pin(VENV/'pyvenv.cfg'),'text':(VENV/'pyvenv.cfg').read_text()},'base_BUILD':{'pin':pin(BASE/'BUILD'),'text':(BASE/'BUILD').read_text().strip()},'header_identifiers':{'patchlevel':pin(python_include/'patchlevel.h'),'pyconfig':pin(python_include/'pyconfig.h'),'module_API':pin(python_include/'modsupport.h'),'version':'3.11.15','version_hex_derived':hex((3<<24)|(11<<16)|(15<<8)|(15<<4)),'release_serial':0,'platform_branch':'_MSC_VER + _WIN64 + _M_X64 selects win_amd64, 8-byte void*/Py_ssize_t and 2-byte WCHAR, shared Python DLL imports; this is source interpretation, not preprocessor output.','debug_selection':'_DEBUG defines Py_DEBUG and python311_d.lib; planned release build must not define _DEBUG.','limited_API_selection':'Py_LIMITED_API selects python3.lib; this private/full-API proposal has not selected Limited API.','autolink_release_full_API':'python311.lib'},'quoted_header_closure':{'method':'All textual quoted #include branches transitively from Python.h, resolved current header directory then selected include root; no preprocessor or macro/conditional evaluation.','count':len(seen),'bytes':sum(p.stat().st_size for p in seen),'pins':[pin(p) for p in sorted(seen)],'edges':edges,'missing':quoted_missing,'conditional_angle_headers':system_headers,'full_system_header_closure':False},'inherited_C79_toolchain':{'binding':pin(binding_path),'build_result':pin(ROOT/'data/cache/r09-native-carrier-component-build-20261030T055706Z/build-result.json'),'pin_rechecks':old_pin_checks,'include_search':list(map(str,includes)),'lib_search':list(map(str,libraries)),'selected_header_candidates':selected_headers,'selected_library_candidates':selected_libs,'old_recipe':'C79 uses /MT; it is a standalone fake-target EXE. Do not silently reuse its CRT recipe or COFF as a CPython extension.','planned_recipe_requirement':'Freeze a coherent release x64 CPython extension CRT/allocator recipe, preferably explicit /MD with all extension/C3 objects matching, _DEBUG/Py_DEBUG absent and explicit Python include/import-library paths. This audit does not authorize that build.'},'images':images,'python311_import_archive':archive,'required_symbol_checks':symbol_checks,'unqualified':['Actual venv runtime DLL load path, mapped module identity and OS loader dependency resolution','Full preprocessed C/API header closure, compiler macro output, sizeof/alignment assertions and CPython structure ABI','Selected extension build recipe, release CRT/allocator ownership and compile/link success','Extension exports/imports, dependency closure, compiled C3 first-store ordering and fake-bank runtime integration','Code signing/provenance, exact compiler equivalence to upstream Python build and ABI behavior','Real original7, native leases, physical14, resources, inference, new84 and all scientific/human gates'],'genuine_owner_blockers_identified':[],'activity':{'metadata_helper_execution_only':True,'new_compiler_or_toolchain_executions':0,'target_executables_or_DLL_loads':0,'subject_imports_or_runs':0,'SDK_or_original_model_payload_dispatches':0,'current_docs_edits':0},'primary_documents':[{'url':'https://docs.python.org/3.11/extending/windows.html','use':'Windows extension import library role, not an automatic ABI guarantee.'},{'url':'https://learn.microsoft.com/en-us/cpp/build/reference/md-mt-ld-use-run-time-library?view=msvc-170','use':'/MD DLL CRT versus /MT static CRT; coherent linked object runtime options.'},{'url':'https://learn.microsoft.com/en-us/windows/win32/debug/pe-format','use':'PE32+/AMD64, image/import/export, archive/COFF metadata interpretation.'}]}
assert not quoted_missing and all(x['matches'] for x in old_pin_checks)
assert archive['all_object_members_amd64']
assert all(x['machine_is_amd64'] for x in images.values())
assert all(x['in_import_archive'] and x['in_runtime_named_exports'] for x in symbol_checks)
out=HERE/'NATIVE-BANK-PYTHON-SDK-PREREQUISITES-v1.json'
assert not out.exists()
out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':report['status'],'output':pin(out),'headers':len(seen),'missing_quoted':len(quoted_missing),'conditional_system_unresolved':[x['name'] for x in system_headers if x['pin'] is None],'archive_members':archive['archive_members'],'imports':archive['short_import_count'],'symbols_checked':len(symbol_checks),'runtime_export_count':images['base_python311']['export_count']}))
