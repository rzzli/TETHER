"""Version only source bindings and attach the frozen three regressions."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
driver=(HERE/'raw_adoption_fixture_driver_v2.py').read_text(encoding='utf-8')
driver=driver.replace('Independent literal dispatcher/comparator;','Independent v3 literal dispatcher/comparator;',1)
with (HERE/'raw_adoption_fixture_driver_v3.py').open('x',encoding='utf-8',newline='\n') as out:out.write(driver)
checker=(HERE/'check_raw_adoption_core_v2.py').read_text(encoding='utf-8')
for before,after in (
    ('raw_adoption_fixture_driver_v2 as D','raw_adoption_fixture_driver_v3 as D'),
    ('raw_adoption_core_v2.py','raw_adoption_core_v3.py'),
    ('a6877861860ba7a42d22d581d4bfa565984e6ce377d937ff3c4525b04130fd8a','f4fcae07926927f509f455b1b8e243cec2be8fdbc91fa710aacf14618e9b5bea'),
    ('RAW-ADOPTION-CORE-DRIVER-PURE-PROOF-v2.json','RAW-ADOPTION-CORE-DRIVER-PURE-PROOF-v3.json'),
    ('raw_adoption_fixture_driver_v2.py','raw_adoption_fixture_driver_v3.py')):
    assert checker.count(before)==1,before
    checker=checker.replace(before,after)
assert checker.count('if __name__=="__main__":')==1
checker=checker.replace('if __name__=="__main__":','import raw_adoption_regressions_v3 as REGRESSIONS\nREGRESSIONS.add_tests(CoreTests,D,CORE,fresh)\n\n\nif __name__=="__main__":')
before='runs=RUNS,extras=EXTRA,'
assert checker.count(before)==1
checker=checker.replace(before,'preserved_v2_proof=D.pin(HERE/"RAW-ADOPTION-CORE-DRIVER-PURE-PROOF-v2.json"),three_before=D.pin(HERE/"RAW-ADOPTION-INDEPENDENT-THREE-REGRESSIONS-BEFORE-v3.json"),regressions=D.pin(HERE/"raw_adoption_regressions_v3.py"),\n        runs=RUNS,extras=EXTRA,')
with (HERE/'check_raw_adoption_core_v3.py').open('x',encoding='utf-8',newline='\n') as out:out.write(checker)
print('Independent driver/checker v3 authored; all16 existing tests unchanged plus3 frozen regressions. No core call.')
