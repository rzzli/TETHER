"""Preserve first link failure; remove literal .def name quotes for next build."""
from pathlib import Path

here = Path(__file__).resolve().parent
text = (here/'build_typed_converter_bridge.py').read_text(encoding='utf-8')
old = '''    definition.write_text('LIBRARY "llama-common.dll"\\nEXPORTS\\n'+''.join('    "'+n+'"\\n' for n in selected.values()), encoding='ascii')'''
new = '''    assert all(not any(c.isspace() or c in '\\"=,;#' for c in n) for n in selected.values())
    definition.write_text('LIBRARY llama-common.dll\\nEXPORTS\\n'+''.join('    '+n+'\\n' for n in selected.values()), encoding='ascii')'''
assert old in text
text = text.replace(old, new)
text = text.replace("'TYPED-CONVERTER-BRIDGE-BUILD.json'", "'TYPED-CONVERTER-BRIDGE-BUILD-v2.json'")
needle = "    exe, obj = OUT/'typed_converter_bridge.exe', OUT/'typed_converter_bridge.obj'"
assert needle in text
text = text.replace(needle, '''    import_bytes = import_library.read_bytes()
    assert b'llama-common.dll\\0' in import_bytes
    for name in selected.values():
        assert (name+'\\0').encode('ascii') in import_bytes
        assert ('"'+name+'"').encode('ascii') not in import_bytes
''' + needle)
with (here/'build_typed_converter_bridge_v2.py').open('x', encoding='utf-8') as stream:
    stream.write(text)
