"""Separate unexecuted extension phase; preserve runnerV3 byte-for-byte."""
import hashlib
from pathlib import Path

H=Path(__file__).resolve().parent
b=(H/'run_role_aware_independent_v3.py').read_bytes()
assert hashlib.sha256(b).hexdigest()=='dd909a12e68c1073e1814519316940000ea39930dfb83e01827cc2a8932bfe89'
t=b.decode()
t=t.replace("('CODEC_FIRST','LEGACY48_FIRST')","('EXTENSIONS_FIRST',)")
t=t.replace('ROLE-AWARE-INDEPENDENT-SOURCE-BINDING-v3.json','ROLE-AWARE-EXTENSIONS-SOURCE-BINDING-v1.json')
t=t.replace("'ROLE-AWARE-INDEPENDENT-'+phase+'-PROOF-v3.json'","'ROLE-AWARE-EXTENSIONS-'+phase+'-PROOF-v1.json'")
t=t.replace("'ROLE-AWARE-INDEPENDENT-'+phase+'-ATTEMPT-v3.json'","'ROLE-AWARE-EXTENSIONS-'+phase+'-ATTEMPT-v1.json'")
t=t.replace('ROLE-AWARE-INDEPENDENT-UNBOUND-ERROR-v3.json','ROLE-AWARE-EXTENSIONS-UNBOUND-ERROR-v1.json')
start=t.index("        if phase=='CODEC_FIRST':\n")
end=t.index('        common_post_suite_late_veto=',start)
replacement='''        fixture,schema,public,cohort=D.literals()
        roles['role_ledger_codec_v1']=modules['role_ledger_codec_v1']
        I=load_harness('role_aware_exact_indexed6_adapter_v1',binding['harness_pins']['indexed6_adapter'])
        E=load_harness('role_aware_actual_producer_extensions_v1',binding['harness_pins']['extension_tests'])
        suite=unittest.TestSuite()
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(I.make_tests(D,roles,fixture,public,cohort,validator,indexed_observations,indexed=True)))
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(E.make_tests(D,roles,fixture,public,cohort,validator,extension_observations)))
        result=unittest.TextTestRunner(verbosity=2,resultclass=Results).run(suite)
        status='PASS' if result.wasSuccessful() else 'FIRST_FAILURES_RETAINED';methods=result.testsRun;method_outcomes=result.outcomes
        failures=[dict(test=str(t),traceback=x) for t,x in result.failures];errors=[dict(test=str(t),traceback=x) for t,x in result.errors]
'''
t=t[:start]+replacement+t[end:]
t=t.replace("phase='UNBOUND';report_path=None","phase='UNBOUND';report_path=None;indexed_observations=[];extension_observations=[]")
t=t.replace('codec=codec_result,codec_forwarding=codec_forwarding,legacy_runs=runs,same8_observations=focused,',
    'codec=codec_result,codec_forwarding=codec_forwarding,legacy_runs=runs,same8_observations=focused,indexed6_observations=indexed_observations,producer_extension_observations=extension_observations,')
with (H/'run_role_aware_extensions_v1.py').open('x',encoding='utf-8',newline='\n') as f:f.write(t)
print('Prepared separate EXTENSIONS_FIRST runner; no source import/run')
