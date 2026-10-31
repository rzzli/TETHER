"""Named callback-control Root binder, preserving all V2 failure evidence."""
from pathlib import Path
import hashlib

base=Path(__file__).resolve().parent
prior=base/"bind_native25_root_v2.py";text=prior.read_text()
for old,new in (
    ("NATIVE25-COMPONENT-INDEPENDENT-STATIC-REVIEW-v2.json","NATIVE25-COMPONENT-INDEPENDENT-STATIC-REVIEW-v3.json"),
    ("97d47d457fe737a8c88ec2c0d30446d28a127f9ddf7092ce77dde64fa7463f4e","9ad2bcac3d052c1c98191ce42e58895b999d460a5aa0d73df7dd53169c51dfa2"),
    ("NATIVE25-COMPONENT-FREEZE-v2.json","NATIVE25-COMPONENT-FREEZE-v3.json"),
    ("fd479a87b768be50d39dda27f0ad85c931753f171aeef5b4e1e37f7dc435e1e8","3ec335327d414de40fe6e1c49ed726692995d629ef757c596716c80b3f26f987"),
    ("NATIVE25-COMPONENT-EXECUTION-SCOPE-v2.json","NATIVE25-COMPONENT-EXECUTION-SCOPE-v3.json"),
    ("NATIVE25-COMPONENT-BINDING-v2.json","NATIVE25-COMPONENT-BINDING-v3.json")):
    if text.count(old)!=1:raise ValueError("Unique binder selection: "+old)
    text=text.replace(old,new)
text=text.replace('scope=dict(schema_version=1,','scope=dict(schema_version=3,',1)
text=text.replace('binding=dict(schema_version=2,','binding=dict(schema_version=3,',1)
before='    diagnostic="Both frozen valid-alternate API/axis-kind controls require NATIVE_STATE_NOT_REPRESENTABLE. Preserve first actual failures; no xfail, outcome weakening, subject edit, retry or failed-case removal.",'
after='    diagnostic="Callback-only control after first31/12proof2519: seven leading EntryWorld arguments fixed, case bodies/assertions/source unchanged. Resolve ten masked runtime behaviors; both valid-kind guards still require refusal and remain ordinary failures if absent. Preserve both results, no xfail or healing.",'
if text.count(before)!=1:raise ValueError("Explicit callback control")
text=text.replace(before,after)
output=base/"bind_native25_root_v3.py"
with output.open("x",encoding="utf-8")as stream:stream.write(text)
print(hashlib.sha256(output.read_bytes()).hexdigest())
