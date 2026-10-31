"""Produce import-only successor copies; AST inspection, never subject import."""
import ast
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEST = HERE.parent / 'recovery-step9-entry-source3-20261030'
EXPECTED = {
    'preflight_owner_ops': 'e438b8862b84309777c6c97eae79f0d1967c943525fc18b27b28f2c5e0e16a33',
    'preflight_file_view': '9b782a58d450543989fa79be0325ac24038b4b8a1338cf52069a53e8067c4f0e',
}
OLD = b'import preflight_entry_kernel_v2 as K'
NEW = b'import preflight_entry_kernel_v3 as K'


def main():
    scope = (HERE / 'ENTRY-SOURCE3-CORRECTION-AUTHORING-SCOPE-v1.json').read_bytes()
    if hashlib.sha256(scope).hexdigest() != '92efd17643ecaf7ed0d303225fe9616d5fa921cce48c365a904a0b9d49381b0b':
        raise RuntimeError('Root authoring scope changed')
    DEST.mkdir(exist_ok=True)
    rows = []
    for stem, digest in EXPECTED.items():
        before = (HERE / (stem + '_v2.py')).read_bytes()
        if hashlib.sha256(before).hexdigest() != digest or before.count(OLD) != 1:
            raise RuntimeError('frozen predecessor differs')
        after = before.replace(OLD, NEW)
        ast.parse(after)
        if ast.dump(ast.parse(after.replace(NEW, OLD))) != ast.dump(ast.parse(before)):
            raise RuntimeError('unexpected behavior delta')
        path = DEST / (stem + '_v3.py')
        with path.open('xb') as stream:
            stream.write(after)
        rows.append(dict(path=str(path), bytes=len(after),
                         sha256=hashlib.sha256(after).hexdigest(), delta='exact import-only'))
    print(json.dumps(rows))


if __name__ == '__main__':
    main()
