"""Trusted text-only adapter author; never imports the under-test modules."""
import ast
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent
OLD = ASSETS / 'recovery-step9-entry-source3-20261030'
CONTRACT = ASSETS / 'recovery-step9-entry-contract-tests-20261030'


def save(name, text):
    ast.parse(text)
    path = HERE / name
    if path.exists():
        raise RuntimeError('preserve existing authored file: ' + name)
    path.write_bytes(text.encode('utf-8'))


support = (OLD / 'entry_independent_test_support_v3.py').read_bytes().decode('utf-8')
save('entry_independent_test_support_v4.py', support.replace('preflight_entry_kernel_v3', 'preflight_entry_kernel_v4'))

world = (OLD / 'entry_independent_world_v3.py').read_bytes().decode('utf-8')
world = world.replace('entry_independent_test_support_v3', 'entry_independent_test_support_v4')
world = world.replace('bulk_size=None, output_hook=None, raw_hook=None):',
                      'bulk_size=None, output_hook=None, raw_hook=None,\n                 policy_request=None, entry_basis_pins=None, policy_only=False):')
world = world.replace('        self.gate = gate\n', '        self.gate = gate\n        self.policy_only = policy_only\n        self.policy_entry_error = None\n', 1)
world = world.replace('        self.services = kernel.PreboundServices(',
'''        self.policy_request = (make_live_policy(inputs, self.specs)
                               if policy_request is None else clone_json(policy_request))
        if policy_only:
            self.specs = tuple(kernel.FileSpec('Z:\\\\policy\\\\input-%03d.bin' % i,
                               'hash_only_bulk', row['bytes'], row['sha256'], False, i)
                               for i, row in enumerate(entry_basis_pins or ()))
        binding = self.policy_request['binding']
        self.policy_binding = kernel.ManifestPolicyBinding(
            binding['mode'], binding['current_decision_id'], binding['current_output_ids'],
            binding['basis_ids'], binding['external_tcb_pins'], binding['prior_metadata_pins'])
        self.services = kernel.PreboundServices(''')
world = world.replace("            dict(scope='ROOT_AUTHORIZED_SYNTHETIC_ENTRY_SOURCE_TEST_ONLY'),\n            dict(self.loader.STDLIB))",
                      "            self.policy_request['envelope'],\n            dict(self.loader.STDLIB), self.policy_binding)")
world = world.replace("                                     names['codec'], kernel.PROFILE_ORIGINAL7_1M)\n",
'''                                     names['codec'], kernel.PROFILE_ORIGINAL7_1M)
        if policy_only:
            self.plan = (None if binding['mode'] == 'AUTHORING' else
                         kernel.EntryPlan(self.specs, (), (), inputs['output_key'],
                                          names['owner_ops'], names['file_view'], names['codec'],
                                          kernel.PROFILE_ORIGINAL7_1M))
''')
world = world.replace('        except BaseException:\n            self.state = self.attempt.state\n            raise\n',
'''        except BaseException as error:
            self.state = self.attempt.state
            self.policy_entry_error = error
            raise
''', 1)
world = world.replace("        self.file_refs = tuple(self.gate.invoke(self.state.file_ref, x.path) for x in self.specs)",
'''        if self.policy_only:
            return self.state
        self.file_refs = tuple(self.gate.invoke(self.state.file_ref, x.path) for x in self.specs)''')
world = world.replace('    def cleanup(self):\n',
'''    def cleanup(self):
        if self.policy_only:
            # Entry-only policy worlds never open originals. No forced plan,
            # output reservation or finalization is manufactured for evidence.
            require(not self.originals.calls, 'policy-only world has no original leases')
            return
''')
world += '''

def clone_json(value):
    # Exact literal JSON values only; no source object or custom hook is read.
    import json
    return json.loads(json.dumps(value, ensure_ascii=True, allow_nan=False))


def make_live_policy(inputs, specs):
    """Independent declared pins for the actual fresh helper/file fixture.

    This configuration is a synthetic external TCB assumption. It does not
    authenticate a launcher, physical path, native consumer or actual roster.
    """
    kernel_pin = inputs['source_map'][inputs['module_names']['kernel']]
    root = dict(id='root.kernel', bytes=kernel_pin['bytes'], sha256=kernel_pin['sha256'])
    ids = ['input.%03d' % i for i in range(len(specs))]
    outputs = ['run.output.%02d' % i for i in range(14)]
    binding = dict(mode='EXECUTION', current_decision_id='run.decision',
                   current_output_ids=outputs, basis_ids=ids,
                   external_tcb_pins=[root], prior_metadata_pins=[])
    nodes = [dict(root, role='EXTERNAL_TCB', state='PINNED', reason=None, pin_dependencies=[])]
    nodes += [dict(id=ident, role='INPUT', state='PINNED', bytes=spec.size,
                   sha256=spec.sha256, reason=None, pin_dependencies=['root.kernel'])
              for ident, spec in zip(ids, specs)]
    reason = 'CURRENT_RUN_NOT_A_STATIC_PIN'
    nodes.append(dict(id='run.decision', role='CURRENT_DECISION', state='CURRENT',
                      bytes=None, sha256=None, reason=reason, pin_dependencies=list(ids)))
    nodes += [dict(id=ident, role='CURRENT_OUTPUT', state='CURRENT', bytes=None,
                   sha256=None, reason=reason, pin_dependencies=['run.decision']) for ident in outputs]
    envelope = dict(schema_version=1, mode='EXECUTION', current_decision_id='run.decision',
                    current_output_ids=list(outputs), external_anchor_ids=['root.kernel'],
                    basis_ids=list(ids), nodes=nodes)
    return dict(binding=binding, envelope=envelope)
'''
save('entry_independent_world_v4.py', world)

reg = (OLD / 'entry_initial_regressions_v4.py').read_bytes().decode('utf-8')
reg = reg.replace('entry_independent_test_support_v3', 'entry_independent_test_support_v4')
old = 'services.executing_module, services.external_root_envelope, services.trusted_modules)'
assert reg.count(old) == 1
reg = reg.replace(old, 'services.executing_module, services.external_root_envelope, services.trusted_modules,\n        services.manifest_policy_binding)')
save('entry_initial_regressions_source4_v1.py', reg)

cases = (CONTRACT / 'entry_contract_cases_v2.py').read_bytes().decode('utf-8')
cases = cases.replace('entry_independent_test_support_v3', 'entry_independent_test_support_v4')
cases = cases.replace('exact executing Source3 module', 'exact executing Source4 module')
save('entry_contract_cases_source4_v1.py', cases)

print('Authored support/world and named five/causal adapters; AST only, no subject import.')
