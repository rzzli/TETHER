"""Controlled Windows fixture lock; does not diagnose the original transient."""
import ctypes
from ctypes import wintypes
import hashlib,json,os
from pathlib import Path
import shutil,tempfile
from unittest.mock import patch
from tests.test_science_bounded_interpretation import InterpretationTests

ROOT=Path(__file__).resolve().parents[3]

def run():
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    create=kernel.CreateFileW
    create.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    create.restype=wintypes.HANDLE
    close=kernel.CloseHandle;close.argtypes=[wintypes.HANDLE];close.restype=wintypes.BOOL
    handles=[];locked=[]
    original=shutil.copytree
    def copied_with_open_case(source,destination,*args,**kwargs):
        result=original(source,destination,*args,**kwargs)
        case=Path(destination)/'case.json'
        if case.exists():
            handle=create(str(case),0x80000000,0x00000001|0x00000002,None,3,0x80,None)
            if handle==wintypes.HANDLE(-1).value:raise ctypes.WinError(ctypes.get_last_error())
            handles.append(handle);locked.append(dict(attributes=case.stat().st_file_attributes,bytes=case.stat().st_size))
        return result
    outcome=dict(schema='p09.interpretation_setup_lock_probe.v1',test_module_sha256=hashlib.sha256((ROOT/'tests/test_science_bounded_interpretation.py').read_bytes()).hexdigest(),
        controlled_fault='After fixture copy, hold a read handle that permits read/write sharing but denies delete sharing on copied case.json. No production I/O is mocked.',
        observed_original_root_cause='UNKNOWN: uncontrolled targeted run and core gate pass the original setup.',provider_reads=0)
    test=InterpretationTests('test_exact_quote_and_foreign_premise_rejected')
    try:
        with patch('tests.test_science_bounded_interpretation.shutil.copytree',side_effect=copied_with_open_case):
            test.setUp()
        test.test_exact_quote_and_foreign_premise_rejected()
        outcome.update(setup_and_behavior='PASS',exception_type=None,winerror=None)
    except BaseException as error:
        outcome.update(setup_and_behavior='FAIL',exception_type=type(error).__name__,winerror=getattr(error,'winerror',None),errno=getattr(error,'errno',None),error_stage='setup copied-case replace')
    finally:
        for handle in handles:close(handle)
        test.doCleanups()
    outcome['copied_case_handles']=len(handles);outcome['copied_case_metadata']=locked
    return outcome

if __name__=='__main__':
    import sys
    outcome=run();target=Path(sys.argv[1])
    with target.open('xb') as stream:stream.write(json.dumps(outcome,indent=2).encode()+b'\n')
    print(json.dumps(outcome,indent=2))
