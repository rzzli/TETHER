"""Check the narrow JSON-link formatter correction without creating a PDF."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph

ROOT = Path(__file__).resolve().parents[3]
OLD = ROOT / "tools/presentation/build_tether_manuscript.py"
NEW = ROOT / "tools/presentation/build_tether_manuscript_v2.py"
before, after = OLD.read_bytes(), NEW.read_bytes()
needle = br"\.md(?:#[^\s)]*)?"
replacement = br"\.(?:md|json)(?:#[^\s)]*)?"
assert before.count(needle) == 1
assert before.replace(needle, replacement) == after

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    item = importlib.util.module_from_spec(spec)
    sys.modules[name] = item
    spec.loader.exec_module(item)
    return item

old = module("old_formatter", OLD)
new = module("new_formatter", NEW)
style = getSampleStyleSheet()["BodyText"]
text = "See [software qualification](../documentation/SOFTWARE-QUALIFICATION.json)."
old_visible = Paragraph(old.inline_markup(text, {}, set()), style).getPlainText()
assert old.text_key(old_visible) != old.text_key(old.visible_text(text))
cases = [text, "See [guide](../documentation/guide.md).",
         "See [JSON anchor](../data.json#section).",
         "See [official source](https://example.org/source)."]
for item in cases:
    seen = Paragraph(new.inline_markup(item, {}, set()), style).getPlainText()
    assert new.text_key(seen) == new.text_key(new.visible_text(item))

out = Path(__file__).with_name("FORMATTER-DELTA-CHECK.json")
record = dict(status="PASS_NARROW_FORMATTER_CORRECTION", old_failure_reproduced=True,
              corrected_inline_cases=len(cases), exact_single_regex_delta=True,
              original_sha256=hashlib.sha256(before).hexdigest(),
              corrected_sha256=hashlib.sha256(after).hexdigest(),
              pdf_created=False, source_values_read=False)
with out.open("x", encoding="utf-8") as stream:
    json.dump(record, stream, indent=2)
    stream.write("\n")
print(json.dumps(record, sort_keys=True))
