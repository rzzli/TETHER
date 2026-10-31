"""Coherent namespace-only FileView successor; Source1 bytes stay unchanged."""
import ast
import hashlib
import json
from pathlib import Path

H=Path(__file__).resolve().parent
old=H.parent/'recovery-step9-entry-source-20261029/preflight_file_view_v1.py'
raw=old.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='79c371a201c9450bb7f50cef3ac0340fee782e744bf00390c4683e66d4c34daf'
assert raw.count(b'import preflight_entry_kernel_v1 as K')==1
new=raw.replace(b'import preflight_entry_kernel_v1 as K',b'import preflight_entry_kernel_v2 as K',1)
path=H/'preflight_file_view_v2.py'
with path.open('xb')as out:out.write(new)
ast.parse(new,str(path))
assert old.read_bytes()==raw
print(json.dumps(dict(status='AUTHORED_AST_ONLY_NAMESPACE_CHANGE',bytes=len(new),sha256=hashlib.sha256(new).hexdigest(),source1_unchanged=True,subject_imports=0,subject_tests=0)))
