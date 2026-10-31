"""One root-selected fixture-only successor. Never imports a subject module."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def replace_once(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)


def new_file(name,text):
    with (HERE/name).open('x',encoding='utf-8',newline='\n') as f:f.write(text)


def main():
    decision=HERE/'ROLE-AWARE-FORMAT-LITERAL-ROOT-CORRECTION-v2.json'
    assert hashlib.sha256(decision.read_bytes()).hexdigest()=='9f4f3c413f8524cd0a33f036b24f38234d83f6f9b52bed966734342becca801a'
    author=(HERE/'author_role_ledger_literals_v1.py').read_text(encoding='utf-8')
    for stem in ('ROLE-AWARE-FORMAT-CORPUS-TEST-CONTRACT','ROLE-AWARE-FORMAT-LITERAL-CORPUS','ROLE-AWARE-FORMAT-LITERAL-PROVENANCE'):
        author=author.replace(stem+'-v1.json',stem+'-v2.json')
    author=replace_once(author,
        "expected_sha256=None if size is None else hashlib.sha256(('synthetic:'+str(i)).encode()).digest(),",
        "expected_sha256=None if size is None else (hashlib.sha256(b'').digest() if size == 0 else hashlib.sha256(('synthetic:'+str(i)).encode()).digest()),")
    author=replace_once(author,
        "count=0 if api == 6 and scalar['tag']=='BOOL' and scalar['value'] else (7 if api == 13 else None))",
        "count=0 if api == 6 and scalar['tag']=='BOOL' and scalar['value'] else (0 if api == 13 and scalar['tag']=='BOOL' and scalar['value']==0 else (7 if api == 13 else None)))")
    author=replace_once(author,
        "    # Reserved raw frame storage is not a claimed captured/defined query.\n",
        "    if api == 14 and scalar['tag'] != 'UNOBSERVED':\n        c['input_handle_atom'] = atom('HANDLE', 0)\n    # Reserved raw frame storage is not a claimed captured/defined query.\n")
    author=replace_once(author,
        "pin('ROLE-AWARE-PRODUCER-FORMAT-INDEPENDENT-REVIEW-v2.json'),pin('ROLE-AWARE-PRODUCER-FORMAT-SCHEMA-ACCEPTANCE-v2.json')],",
        "pin('ROLE-AWARE-PRODUCER-FORMAT-INDEPENDENT-REVIEW-v2.json'),pin('ROLE-AWARE-PRODUCER-FORMAT-SCHEMA-ACCEPTANCE-v2.json'),\n                         pin('ROLE-AWARE-FORMAT-LITERAL-ROOT-CORRECTION-v2.json'),pin('ROLE-AWARE-FORMAT-LITERAL-INDEPENDENT-REVIEW-v1.json'),\n                         pin('ROLE-AWARE-FORMAT-LITERAL-SELF-REVIEW-v1.json'),pin('ROLE-AWARE-FORMAT-LITERAL-STRUCTURE-PROOF-v1.json')],")
    author=replace_once(author,
        "reserved_regions=len(regions),full_cap_layout_controls=1),",
        "reserved_regions=len(regions),full_cap_layout_controls=1,\n                                     future_methods=4,value_type_refusal_probes=15,callback_exception_invocations=66,\n                                     callback_exception_families=11,predicted_entrypoint_invocations=387,predicted_getter_calls=158),")
    new_file('author_role_ledger_literals_v2.py',author)
    tests=(HERE/'role_ledger_independent_tests_v1.py').read_text(encoding='utf-8')
    tests=replace_once(tests,"                v=value_of(b);calln=[0]","                v=value_of(b);pristine=copy.deepcopy(v);calln=[0]")
    tests=replace_once(tests,"                assert type(actual) is bytes and actual==raw,b['id']","                assert type(actual) is bytes and actual==raw,b['id']\n                same(v,pristine)")
    tests=replace_once(tests,"counts['getter_calls']+=1;same(d,v)","counts['getter_calls']+=1;same(d,pristine)")
    tests=replace_once(tests,"                same(obj.to_dict(),v);counts['getter_calls']+=1","                same(obj.to_dict(),pristine);counts['getter_calls']+=1")
    new_file('role_ledger_independent_tests_v2.py',tests)
    checker=(HERE/'check_role_ledger_literal_structure_v1.py').read_text(encoding='utf-8')
    for stem in ('ROLE-AWARE-FORMAT-LITERAL-CORPUS','ROLE-AWARE-FORMAT-CORPUS-TEST-CONTRACT','ROLE-AWARE-FORMAT-LITERAL-PROVENANCE','ROLE-AWARE-FORMAT-LITERAL-STRUCTURE-PROOF'):
        checker=checker.replace(stem+'-v1.json',stem+'-v2.json')
    checker=checker.replace('author_role_ledger_literals_v1.py','author_role_ledger_literals_v2.py')
    checker=checker.replace('role_ledger_independent_tests_v1.py','role_ledger_independent_tests_v2.py')
    checker=checker.replace('preserve v1 before correction','corrected named v2 keeps preserved v1 evidence')
    new_file('check_role_ledger_literal_structure_v2.py',checker)
    print(json.dumps({'written':['author_role_ledger_literals_v2.py','role_ledger_independent_tests_v2.py','check_role_ledger_literal_structure_v2.py'],
                      'subject_imports':0,'subject_runs':0}))


if __name__=='__main__':main()
