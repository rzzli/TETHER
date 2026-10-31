"""Preserve exact v2 helpers and create separate v3 source files, without execution."""
from pathlib import Path

here=Path(__file__).resolve().parent
for original,snapshot in (
    ('run_finite_converter_probe.py','run_finite_converter_probe_v2.py'),
    ('prepare_finite_converter_probe.py','prepare_finite_converter_probe_v2.py'),
):
    raw=(here/original).read_bytes()
    target=here/snapshot
    if target.exists():assert target.read_bytes()==raw
    else:
        with target.open('xb') as stream:stream.write(raw)
runner=(here/'run_finite_converter_probe.py').read_text(encoding='utf-8')
assert 'FINITE-CONVERTER-EXECUTION-PROTOCOL-v2.json' in runner
runner=runner.replace('FINITE-CONVERTER-EXECUTION-PROTOCOL-v2.json','FINITE-CONVERTER-EXECUTION-PROTOCOL-v3.json')
with (here/'run_finite_converter_probe_v3.py').open('x',encoding='utf-8') as stream:stream.write(runner)
prep=(here/'prepare_finite_converter_probe.py').read_text(encoding='utf-8')
prep=prep.replace('prepare_finite_converter_probe.py','prepare_finite_converter_probe_v3.py')
prep=prep.replace('run_finite_converter_probe.py','run_finite_converter_probe_v3.py')
prep=prep.replace('preparation_revision=2','preparation_revision=3')
prep=prep.replace('FINITE-CONVERTER-EXECUTION-PROTOCOL-v2.json','FINITE-CONVERTER-EXECUTION-PROTOCOL-v3.json')
with (here/'prepare_finite_converter_probe_v3.py').open('x',encoding='utf-8') as stream:stream.write(prep)
