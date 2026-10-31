"""Retain the reviewed dependency-free/legacy helper under the new phase."""
from pathlib import Path

HERE=Path(__file__).resolve().parent
old=HERE.parent/'recovery-step9-retrieval-20261026/verify_installed.py'
text=old.read_text(encoding='utf-8')
needle="environment = Path(sys.prefix).resolve()"
assert text.count(needle)==1
text=text.replace(needle,needle+"\nfrom importlib.metadata import version\nassert sys.flags.isolated and version('asof-target-agents')=='0.3.7'\ntry:\n    version('pyarrow')\nexcept Exception as error:\n    from importlib.metadata import PackageNotFoundError\n    assert isinstance(error, PackageNotFoundError)\nelse:\n    raise AssertionError('Default installed environment must remain dependency-free')")
needle="        path = normalized(os.fsdecode(args[0]))"
assert text.count(needle)==1
text=text.replace(needle,needle+"\n        if path.startswith('e:') or '\\\\data\\\\benchmark\\\\' in path:\n            forbidden_reads.append(dict(event=event,path=path))\n            raise PermissionError('Original assets and benchmark payloads unavailable')")
with (HERE/'verify_default_installed.py').open('x',encoding='utf-8') as stream:
    stream.write(text)
print('Retained default installed helper without altering predecessors')
