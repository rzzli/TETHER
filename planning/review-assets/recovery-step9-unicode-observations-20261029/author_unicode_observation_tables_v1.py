"""Copy exact NEW pinned normative metadata into a fixed pure-source literal."""
import hashlib
import json
from pathlib import Path
import pprint

HERE=Path(__file__).resolve().parent
WIRE=HERE.parent/"recovery-step9-unicode-wire-20261029"
INPUTS=((WIRE/"UNICODE-WIRE-DESIGN-CONTRACT-v2.json","ddf9fd360d72def0b91bd99b047422bf8ee623c0f8d6e0ba73535e04a7af1abc"),
    (WIRE/"UNICODE-WIRE-FRAMING-CONTRACT-v1.json","4c4645f53c878e03cf1f0eaec575b3dcf1dcc006375aadc0080819393e4c3d24"),
    (HERE/"UNICODE-OBSERVATIONS-DESIGN-CONTRACT-v2.json","edacdc2bddbceab5735699ee9d973f89bad46b64713b193fe43ab80ed989101f"))
documents=[]
for path,expected in INPUTS:
    raw=path.read_bytes(); assert hashlib.sha256(raw).hexdigest()==expected
    documents.append(json.loads(raw))
base,closure,design=documents
semantic=base["semantic_contract"]
tables={key:semantic[key] for key in ("API_accounting","framing","event_order","case_row","coverage","bounds")}
tables.update(closure=closure["framing_semantics"],times=design["reported_time_samples"],external_pending=design["external_pending_bindings"])
source='''"""Fixed immutable captured-source format tables; no filesystem/runtime authority."""
from types import MappingProxyType

def _freeze(value):
    if type(value) is dict: return MappingProxyType({key:_freeze(item) for key,item in value.items()})
    if type(value) is list: return tuple(_freeze(item) for item in value)
    return value

SOURCE_PINS = '''+repr(tuple(expected for _,expected in INPUTS))+"\nTABLES = _freeze("+pprint.pformat(tables,sort_dicts=True,width=120)+")\n"
target=HERE/"unicode_observation_tables_v1.py"
with target.open("xb") as out: out.write(source.encode("utf-8"))
print(json.dumps(dict(name=target.name,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest())))
