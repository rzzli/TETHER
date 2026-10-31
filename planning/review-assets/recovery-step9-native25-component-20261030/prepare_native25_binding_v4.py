"""Root binder for independently justified named code-expectation errata."""
from pathlib import Path
import hashlib

base=Path(__file__).resolve().parent;text=(base/"bind_native25_root_v3.py").read_text()
for old,new in (
    ("NATIVE25-COMPONENT-INDEPENDENT-STATIC-REVIEW-v3.json","NATIVE25-COMPONENT-INDEPENDENT-STATIC-REVIEW-v4.json"),
    ("9ad2bcac3d052c1c98191ce42e58895b999d460a5aa0d73df7dd53169c51dfa2","cb1def1aea2e638ec499c9cebd5b70df50101894fccf426e291a179819c5c3a3"),
    ("NATIVE25-COMPONENT-FREEZE-v3.json","NATIVE25-COMPONENT-FREEZE-v4.json"),
    ("3ec335327d414de40fe6e1c49ed726692995d629ef757c596716c80b3f26f987","c58b3404221e4f617e61bc3c06e23db7df1a89aa84c6e2363a8fbef43b522b95"),
    ("NATIVE25-COMPONENT-EXECUTION-SCOPE-v3.json","NATIVE25-COMPONENT-EXECUTION-SCOPE-v4.json"),
    ("NATIVE25-COMPONENT-BINDING-v3.json","NATIVE25-COMPONENT-BINDING-v4.json")):
    if text.count(old)!=1:raise ValueError("Unique binding replacement")
    text=text.replace(old,new)
text=text.replace('schema_version=3','schema_version=4')
before='    diagnostic="Callback-only control after first31/12proof2519: seven leading EntryWorld arguments fixed, case bodies/assertions/source unchanged. Resolve ten masked runtime behaviors; both valid-kind guards still require refusal and remain ordinary failures if absent. Preserve both results, no xfail or healing.",'
after='    diagnostic="Named normative-code errata5f80101c after retained31/12 and38/5 controls. N06base explicitly requires READ_PROGRESS_INCOMPLETE; unsupported generic N04/N07 mappings corrected to pre-existing source-specific refusals. Independently reviewed cb1def1a. All trailing raw/no-right/no-progress/no-retry checks stay strict; both kind guards remain ordinary failures if absent. Source4 unchanged, no healing.",'
if text.count(before)!=1:raise ValueError("Explicit normative control")
text=text.replace(before,after)
out=base/"bind_native25_root_v4.py"
with out.open("x",encoding="utf-8")as stream:stream.write(text)
print(hashlib.sha256(out.read_bytes()).hexdigest())
