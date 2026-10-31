"""Import-only helper successors; parse source as data, never import it."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'recovery-step9-entry-source3-20261030'
DEST = HERE.parent / 'recovery-step9-entry-source4-20261030'
EXPECTED = {
    'preflight_owner_ops': 'e3a6e5177989b319cfe8e3080b9e511004bd5d7f392fabf9aef1a702e03b7cb7',
    'preflight_file_view': '96490b91af55567a5f76f3d54da1a83788076d5c5c03ed2f27b77ab4ea586ce6',
}
OLD = b'import preflight_entry_kernel_v3 as K'
NEW = b'import preflight_entry_kernel_v4 as K'


def main():
    scope = (HERE / 'E08-ENTRY-SUCCESSOR-AUTHORING-SCOPE-v1.json').read_bytes()
    if hashlib.sha256(scope).hexdigest() != '29f35d62699766b5a6eaf7aa00441af2410cff542a26a36c20b718dda3a47113':
        raise RuntimeError('Root authoring scope changed')
    DEST.mkdir(exist_ok=True)
    result = []
    for stem, digest in EXPECTED.items():
        before = (SOURCE / (stem + '_v3.py')).read_bytes()
        if hashlib.sha256(before).hexdigest() != digest or before.count(OLD) != 1:
            raise RuntimeError('frozen Source3 helper differs')
        after = before.replace(OLD, NEW)
        ast.parse(after)
        if ast.dump(ast.parse(after.replace(NEW, OLD))) != ast.dump(ast.parse(before)):
            raise RuntimeError('unexpected helper behavior delta')
        path = DEST / (stem + '_v4.py')
        with path.open('xb') as stream:
            stream.write(after)
        result.append(dict(path=str(path), bytes=len(after),
                           sha256=hashlib.sha256(after).hexdigest(), delta='import-only'))
    print(json.dumps(result))


if __name__ == '__main__':
    main()
