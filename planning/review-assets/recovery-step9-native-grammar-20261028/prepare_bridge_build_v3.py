"""Preserve prior builds and use current process-lifetime-pinned author source."""
from pathlib import Path

here = Path(__file__).resolve().parent
text = (here/'build_typed_converter_bridge_v2.py').read_text(encoding='utf-8')
assert "'TYPED-CONVERTER-BRIDGE-BUILD-v2.json'" in text
text = text.replace("'TYPED-CONVERTER-BRIDGE-BUILD-v2.json'", "'TYPED-CONVERTER-BRIDGE-BUILD-v3.json'")
with (here/'build_typed_converter_bridge_v3.py').open('x', encoding='utf-8') as stream:
    stream.write(text)
