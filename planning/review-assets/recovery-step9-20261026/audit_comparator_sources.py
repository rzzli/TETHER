"""Read-only local source metadata/AST audit. Never imports upstream code."""
import ast,hashlib,json
from pathlib import Path
ROOT=Path.cwd(); OUT=ROOT/'planning/review-assets/recovery-step9-20261026'
policy_path=ROOT/'planning/review-assets/science-prerequisites-20261018/item7/adapter-role-policy-r1.json'
policy=json.loads(policy_path.read_bytes()); upstream=Path(policy['source_root'])
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha((upstream/'manifest.json').read_bytes())==policy['source_manifest_sha256']
pins={}
for entry in policy['source_files']:
    path=upstream/entry['path']; data=path.read_bytes()
    assert sha(data)==entry['sha256'] and len(data)==entry['bytes']
    pins[str(path.relative_to(ROOT))]={'sha256':sha(data),'bytes':len(data)}
paths=[policy_path,upstream/'manifest.json']+[ROOT/p for p in [
 'tools/science/comparison_workflow.py','tools/science/role_backend.py','tools/science/run_comparison.py',
 'tools/science/comparison_evaluation.py','planning/protocols/science7-matched-t6-v0.2.json',
 'data/derived/virtual-biotech-compatibility-20261018-resume01/README.md',
 'data/derived/virtual-biotech-compatibility-20261018-resume01/src/config/models.py',
 'data/derived/virtual-biotech-compatibility-20261018-resume01/src/config/datasets.py',
 'data/derived/virtual-biotech-compatibility-20261018-resume01/environment.yml']]
for path in paths:
    data=path.read_bytes();pins[str(path.relative_to(ROOT))]={'sha256':sha(data),'bytes':len(data)}
tree=ast.parse((upstream/'src/agents/registry.py').read_text(encoding='utf-8'))
agents=[]
for node in ast.walk(tree):
    if isinstance(node,ast.Assign) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Name) and node.value.func.id=='AgentDefinition':
        target=node.targets[0]; name=ast.literal_eval(target.slice)
        kws={k.arg:k.value for k in node.value.keywords}
        agents.append({'name':name,'line':node.lineno,'tools':ast.literal_eval(kws['tools']),
            'model_expression':ast.unparse(kws['model']),'prompt_expression':ast.unparse(kws['prompt'])})
signature=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build_specialist_agents')
out={'schema_version':1,'role':'planning_only','source_revision':policy['source_revision'],
     'fresh_hash_checked_local_files':pins,'original_registry_signature':signature.name+'('+ast.unparse(signature.args)+')',
     'registered_agent_tool_names':agents,'mcp_argument_schemas':'Not established: implementations/schema exports absent from the scoped retained source bundle',
     'original_orchestrator_execution':False,'network_calls':0,'protected_data_read':False}
(OUT/'COMPARATOR-SOURCE-PINS.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(len(pins),'files freshly hashed;',len(agents),'agent definitions parsed without execution')
