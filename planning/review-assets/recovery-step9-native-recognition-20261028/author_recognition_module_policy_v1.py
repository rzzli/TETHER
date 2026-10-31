"""Author a separate phase policy from frozen lexical primitives; no image or runtime access."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OLD=HERE/'trusted_system32_module_policy_v1.py'
old=OLD.read_bytes()
assert hashlib.sha256(old).hexdigest()=='77e39b3bb82fb83049aba9956da0251b4a8d914f167dc6d6512d554ad7bfb3a8'
text=old.decode('utf-8');tree=ast.parse(text)
semantic_node=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SEMANTICS' for t in n.targets))
# The approved ABI contract supplies the fully materialized semantic object.
semantics=json.loads((HERE/'TRUSTED-SYSTEM32-MODULE-POLICY-v1.json').read_text(encoding='utf-8'))['semantic_policy']
semantics=dict(semantics)
semantics.update(policy_id='trusted-System32-recognition-v1',mode='recognition_only',
    phases={'pre_cpu':dict(eligible_native_names=semantics['core_names'],required_native_names=semantics['core_names'],CPU_module_eligible=False),
            'post_cpu':dict(eligible_native_names=semantics['declared_runtime_names'],required_native_names=semantics['declared_runtime_names'],CPU_module_eligible=True)},
    model_access_authorized_by_module_reports=False)
semantics.pop('CPU_or_model_eligibility')
body=json.dumps(semantics,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')
fingerprint=hashlib.sha256(body).hexdigest()
prefix=text[:text.index('SEMANTICS =')]+('SEMANTICS = '+repr(semantics)+'\n')
prefix=prefix.replace('Data-only ABI module matcher.','Data-only recognition-phase module matcher.')
prefix+=text[text.index('POLICY_ID ='):text.index('def match_modules(')]
matcher='''def match_modules(rows, *, expected_self, expected_runtime, phase):
    """Pure report classifier; native file/lease authority belongs to the external caller.

    A phase flag supplied by a child is never itself authority to load a CPU/model.
    The qualified parent selects phase from the expected exact event sequence.
    """
    if type(phase) is not str or phase not in SEMANTICS["phases"]:fail("invalid_phase")
    policy=SEMANTICS["phases"][phase]
    eligible=frozenset(policy["eligible_native_names"])
    try:
        self_path=canonical_path(expected_self);runtime=canonical_path(expected_runtime)
        platform=canonical_path(SEMANTICS["platform_root"])
    except ModulePolicyError:fail("invalid_context")
    self_name=self_path.rsplit("\\\\",1)[1]
    if type(rows) is not list or not 1<=len(rows)<=SEMANTICS["maximum_modules"]:fail("module_count_limit")
    names,paths=set(),set();required={"self_executable":0,**{name:0 for name in policy["required_native_names"]}}
    results=[]
    for ordinal,row in enumerate(rows,1):
        if type(row) is not dict or set(row)!={"name","path"}:fail("invalid_metadata",ordinal)
        try:name=canonical_name(row["name"]);path=canonical_path(row["path"])
        except ModulePolicyError as error:fail(error.reason,ordinal)
        parent,basename=path.rsplit("\\\\",1)
        if name!=basename:fail("name_path_mismatch",ordinal)
        if name in names or path in paths:fail("duplicate_report",ordinal)
        names.add(name);paths.add(path)
        if path==self_path:category="self_executable";required["self_executable"]+=1
        elif name==self_name:fail("reserved_self_wrong_path",ordinal)
        elif parent==runtime or name in _NATIVE or any(name.startswith(prefix) for prefix in SEMANTICS["protected_prefixes"]):
            if name not in eligible or path!=runtime+"\\\\"+name:fail("protected_native_not_eligible",ordinal)
            category="pinned_runtime";required[name]+=1
        elif parent==platform:
            if re.fullmatch(SEMANTICS["platform_basename_pattern"],name,flags=re.ASCII) is None:fail("unsafe_platform_basename",ordinal)
            category="trusted_platform_context"
        else:fail("outside_declared_roots",ordinal)
        results.append(dict(ordinal=ordinal,name=row["name"],path=row["path"],policy_class=category))
    if any(count!=1 for count in required.values()):fail("missing_required_reports")
    return dict(module_policy_id=POLICY_ID,module_policy_sha256=POLICY_SHA256,module_policy_phase=phase,
        reports=results,required_report_counts=required,maximum_modules=64,
        platform_image_authentication="not_established",CPU_module_eligible=policy["CPU_module_eligible"],model_access_authorized=False,
        trust_scope="Externally pinned/leased native context and canonical reported platform context; no image authentication or model/CPU execution permission")
'''
source=HERE/'recognition_module_policy_v1.py'
with source.open('x',encoding='utf-8',newline='\n') as out:out.write(prefix+matcher)
ast.parse(source.read_text(encoding='utf-8'))
value=dict(schema_version=1,status='recognition_source_semantics_not_execution_authority',semantic_policy=semantics,
    module_policy_id=semantics['policy_id'],module_policy_sha256=fingerprint,
    fingerprint_definition='SHA256 of UTF8 compact sorted semantic_policy JSON; excludes current/future code, binary, proof and protocol hashes',
    root_source_decision_sha256='20ea58d6626b82dd55c7b823ed1bd729134ecac15470fcc6c4c1ad69d92a5399',
    old_ABI_policy_sha256='807995f6061d7a2c85144c58668fc2e4ecb79a4fb51d462e43d0a8dfc586d589',
    phase_authority='Parent selects pre_cpu/post_cpu from exact configured event sequence; child-reported phase/verified flags never grant eligibility',
    wire=dict(module_rows_exact_fields=['name','path'],outer_fields=['module_policy_id','module_policy_sha256','module_policy_phase'],
        classifications_recomputed_by_parent=True,CPU_load_authority_from_module_reports=False,model_access_authority_from_module_reports=False),
    rejection_reasons=['invalid_phase','invalid_metadata','invalid_path','invalid_name','invalid_context','name_path_mismatch','duplicate_report',
        'reserved_self_wrong_path','protected_native_not_eligible','unsafe_platform_basename','outside_declared_roots','missing_required_reports','module_count_limit'],
    reasons_scope='Exact labels for isolated predicates; multiple simultaneous invalidities need not be cross-implementation equivalent',
    execution_authorized=False,activity=dict(CPU_binary_reads=0,GGUF_reads=0,SDK_constructors=0,children=0,compiler_calls=0))
contract=HERE/'RECOGNITION-MODULE-POLICY-v1.json'
with contract.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
print(json.dumps(dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),contract=str(contract),contract_sha256=hashlib.sha256(contract.read_bytes()).hexdigest(),semantic_sha256=fingerprint)))
