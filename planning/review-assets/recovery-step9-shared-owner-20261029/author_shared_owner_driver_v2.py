"""Version harness for the coherent v2 source map, frozen oracle unchanged."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
text=(HERE/'shared_owner_fixture_driver_v1.py').read_text(encoding='utf-8')
text=text.replace('Independent generic driver for the frozen synthetic cohort','Independent v2 generic driver for the frozen synthetic cohort',1)
old="original=r.errors[a['exception']];hooks.raise_exception(call_ref,original,a['phase'])"
assert text.count(old)==1
text=text.replace(old,old+";self.stopped=True")
with (HERE/'shared_owner_fixture_driver_v2.py').open('x',encoding='utf-8',newline='\n') as out:out.write(text)
print('Versioned harness; stop monitor also records a reported stop when binding normally returns. No source run.')
