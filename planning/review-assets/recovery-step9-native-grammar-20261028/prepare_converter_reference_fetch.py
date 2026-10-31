"""Specialize the already checked bounded text fetcher for five converter references."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
original=HERE/'fetch_source_references.py'
protocol=json.loads((HERE/'SOURCE-TEXT-PROTOCOL-v2.json').read_bytes())
assert hashlib.sha256(original.read_bytes()).hexdigest()==protocol['helper_sha256']
text=original.read_text(encoding='utf-8')
start=text.index('PATHS=');end=text.index('\nPROTOCOL=',start)
text=text[:start]+"PATHS=('common/json-schema-to-grammar.h','common/json.h','common/json-schema.h',\n       'common/json.cpp','common/json-schema-to-grammar.cpp')"+text[end:]
text=text.replace("PROTOCOL=HERE/'SOURCE-TEXT-PROTOCOL-v2.json'","PROTOCOL=HERE/'CONVERTER-SOURCE-TEXT-PROTOCOL.json'")
text=text.replace("'data/cache/r09-native-grammar-source-'","'data/cache/r09-native-converter-source-'")
text=text.replace("        supersedes_unexecuted_protocol='SOURCE-TEXT-PROTOCOL.json',\n",'')
text=text.replace("HERE/'SOURCE-TEXT-ACQUISITION.json'","HERE/'CONVERTER-SOURCE-TEXT-ACQUISITION.json'")
assert "PATHS=('common/json-schema-to-grammar.h'" in text
with (HERE/'fetch_converter_references.py').open('x',encoding='utf-8') as stream:stream.write(text)
print('Five-file bounded converter reference helper prepared')
