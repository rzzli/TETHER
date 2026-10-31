"""Hash/limit checks and quoted-include closure; do not execute retained C++ material."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


protocol_path=HERE/'CONVERTER-SOURCE-TEXT-PROTOCOL.json'
acquisition_path=HERE/'CONVERTER-SOURCE-TEXT-ACQUISITION.json'
protocol=json.loads(protocol_path.read_bytes())
acquisition=json.loads(acquisition_path.read_bytes())
assert acquisition['status']=='source_references_retained' and acquisition['protocol_sha256']==sha(protocol_path)
assert protocol['helper_sha256']==sha(HERE/'fetch_converter_references.py')
records=acquisition['records'];assert len(records)==5 and acquisition['known_response_bytes']==78445
assert not acquisition['unknown_response_bytes']
assert all(r['status']=='retained_utf8_text' and r['http_status']==200 and r['final_url']==r['url']
    and r['bytes']<=524288 and r['elapsed_seconds']<15 and r['outer_elapsed_seconds']<15
    and r['role']=='source_reference_only' for r in records)
assert all(sha(ROOT/r['relative_path'])==r['sha256'] and (ROOT/r['relative_path']).stat().st_size==r['bytes']
    and (ROOT/r['relative_path']).resolve().is_relative_to((ROOT/'data/cache').resolve()) for r in records)
by_name={Path(r['path']).name:r for r in records}
headers=('json-schema-to-grammar.h','json-schema.h','json.h')
edges=[];standard=set();unresolved=[]
for name in headers:
    text=(ROOT/by_name[name]['relative_path']).read_text(encoding='utf-8')
    for target in re.findall(r'^\s*#\s*include\s*"([^"]+)"',text,re.M):
        edges.append(dict(source=name,target=target))
        if target not in headers:unresolved.append(dict(source=name,target=target))
    standard.update(re.findall(r'^\s*#\s*include\s*<([^>]+)>',text,re.M))
assert not unresolved
assert {e['target'] for e in edges}=={'json-schema.h','json.h'}
report=dict(schema_version=1,status='five_converter_references_and_consumer_header_closure_verified',
    recorded_at_utc=datetime.now(timezone.utc).isoformat(),acquisition_sha256=sha(acquisition_path),
    protocol_sha256=sha(protocol_path),files=5,bytes=78445,
    converter_consumer_headers=[by_name[name] for name in headers],quoted_include_edges=edges,
    standard_library_headers=sorted(standard),unresolved_project_includes=unresolved,
    external_cpp_files_compiled=False,vendor_nlohmann_needed_by_consumer_headers=False,
    ggml_needed_by_converter_only_consumer_headers=False,
    native_methods_needed=['common_json::parse','common_json::~common_json','json_schema_to_grammar(common_json const&,bool)'],
    external_code_executed=False,libraries_loaded=0,model_calls=0,servers=0,builds=0,
    abi_compatibility='not_yet_executed_or_qualified',grammar_conformance='unverified')
with (HERE/'CONVERTER-HEADER-CLOSURE.json').open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
print(json.dumps(dict(status=report['status'],headers=len(headers),files=5,bytes=78445,missing=unresolved)))
