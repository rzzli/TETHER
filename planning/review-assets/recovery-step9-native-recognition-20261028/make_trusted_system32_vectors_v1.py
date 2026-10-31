"""Author finite policy data vectors; reported module files are never accessed."""
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OUTPUT=HERE/"TRUSTED-SYSTEM32-MODULE-VECTORS-v1.json"
CONTRACT=HERE/"TRUSTED-SYSTEM32-MODULE-POLICY-v1.json"
CONTEXT=dict(expected_self=r"D:\PolicyFixture\app.exe",expected_runtime=r"D:\PolicyFixture\runtime")
CORE=("libomp.dll","ggml-base.dll","ggml.dll","llama.dll")


def pin(path):
    raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def base(context=None):
    context=context or CONTEXT
    return [dict(name=context["expected_self"].rsplit("\\",1)[-1],path=context["expected_self"]),
            *[dict(name=name,path=context["expected_runtime"]+"\\"+name) for name in CORE]]


def main():
    assert not OUTPUT.exists()
    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert pin(CONTRACT)["sha256"]=="fdd15d4f551efbd3c1ecb515b2724b4ee68cf08d3ea1ed2f5c2a576774da2ca4"
    cases=[]
    def add(identifier,modules,accepted,*,context=None,reason=None,classes=None):
        item=dict(id=identifier,context=copy.deepcopy(context or CONTEXT),modules=modules,accepted=accepted)
        if reason:item["reason_if_isolated"]=reason
        if classes is not None:item["expected_classes"]=classes
        cases.append(item)
    native_classes=["self_executable"]+["pinned_runtime"]*4
    add("exact_self_core4",base(),True,classes=native_classes)
    for name in ("apphelp.dll","KERNEL32.DLL","api-ms-win-core-example-l1-1-0.dll","new_platform_component.dll"):
        add("platform_"+name,base()+[dict(name=name,path="C:\\Windows\\System32\\"+name)],True,
            classes=native_classes+["trusted_platform_context"])
    add("ASCII_case_slash_equivalence",base()+[dict(name="APPHELP.DLL",path="c:/WINDOWS/SYSTEM32/apphelp.dll")],True,
        classes=native_classes+["trusted_platform_context"])
    many=[dict(name=f"platform_{i}.dll",path=rf"C:\Windows\System32\platform_{i}.dll") for i in range(60)]
    add("maximum64",base()+many[:59],True,classes=native_classes+["trusted_platform_context"]*59)
    add("65_reports",base()+many,False,reason="module_count_limit")
    add("empty_inventory",[],False,reason="module_count_limit")
    for i,label in enumerate(("self",*CORE)):
        rows=base();rows.pop(i)
        add("missing_"+label,rows,False,reason="missing_required_reports")
    rows=base();rows[0]=dict(name="app.exe",path=r"C:\Windows\System32\app.exe")
    add("reserved_self_in_System32",rows,False,reason="reserved_self_wrong_path")
    for i,name in enumerate(CORE,1):
        rows=base();rows[i]=dict(name=name,path="C:\\Windows\\System32\\"+name)
        add("wrong_path_"+name,rows,False,reason="protected_native_not_eligible")
    for name in ("ggml-cpu-x64.dll","ggml-vulkan.dll","ggml_extra.dll","llama_helper.dll","libomp140.dll"):
        for directory in (CONTEXT["expected_runtime"],r"C:\Windows\System32"):
            add("protected_"+name+"_"+("runtime" if directory==CONTEXT["expected_runtime"] else "System32"),
                base()+[dict(name=name,path=directory+"\\"+name)],False,reason="protected_native_not_eligible")
    add("unknown_inside_runtime",base()+[dict(name="extra.dll",path=CONTEXT["expected_runtime"]+r"\extra.dll")],False,reason="protected_native_not_eligible")
    for directory in (r"C:\NeverOpen",r"C:\Windows\SysWOW64",r"C:\Windows\System32extra",r"C:\Windows\System32\subdir"):
        add("outside_"+directory,base()+[dict(name="apphelp.dll",path=directory+r"\apphelp.dll")],False,reason="outside_declared_roots")
    for path in (r"C:Windows\System32\apphelp.dll",r"\Windows\System32\apphelp.dll",r"\\server\share\apphelp.dll",
                 r"\\?\C:\Windows\System32\apphelp.dll",r"\\.\C:\Windows\System32\apphelp.dll",
                 "C:\\Windows\\\\System32\\apphelp.dll",r"C:\Windows\System32\.\apphelp.dll",
                 r"C:\Windows\System32\..\System32\apphelp.dll",r"C:\Windows\System32\apphelp.dll:stream",
                 r"C:\Windows\System32\apphelp.dll.","C:\\Windows\\System32\\apphelp.dll ",
                 r"C:\WINDOW~1\System32\apphelp.dll",r"C:\NUL\apphelp.dll",r"C:\COM1\apphelp.dll",
                 "C:\\Windows\\System32\\bad\x7f\\apphelp.dll","C:\\Windows\\System32\\apphelp.dll\0"):
        add("noncanonical_"+str(len(cases)),base()+[dict(name="apphelp.dll",path=path)],False)
    for name in ("NUL.dll","CON.dll","COM1.dll","LPT9.dll","APPHEL~1.DLL","apphelp.dll ",".hidden.dll",
                 "safe+.dll","Unicode_\u212a.dll","Unicode_\uff47\uff47\uff4d\uff4c.dll"):
        add("unsafe_leaf_"+str(len(cases)),base()+[dict(name=name,path="C:\\Windows\\System32\\"+name)],False)
    add("name_path_mismatch",base()+[dict(name="different.dll",path=r"C:\Windows\System32\apphelp.dll")],False,reason="name_path_mismatch")
    add("duplicate_exact_row",base()+[copy.deepcopy(base()[1])],False,reason="duplicate_report")
    add("duplicate_name_precedes_wrong_path",base()+[dict(name="LLAMA.DLL",path=r"C:\Windows\System32\llama.dll")],False,reason="duplicate_report")
    add("duplicate_case_slash_platform",base()+[dict(name="apphelp.dll",path=r"C:\Windows\System32\apphelp.dll"),
        dict(name="APPHELP.DLL",path="c:/windows/system32/APPHELP.DLL")],False,reason="duplicate_report")
    rows=base();rows[-1]["extra"]="untrusted_category"
    add("extra_row_field",rows,False,reason="invalid_metadata")
    rows=base();rows[-1]["path"]=True
    add("wrong_scalar_type",rows,False,reason="invalid_path")
    add("unpaired_path_surrogate",base()+[dict(name="apphelp.dll",path="C:\\Windows\\System32\\\ud800\\apphelp.dll")],False)
    longname="n"*252+".dll"
    add("name256_UTF16_units",base()+[dict(name=longname,path="C:\\Windows\\System32\\"+longname)],False,reason="invalid_name")
    longpath="C:\\"+"a"*32760+"\\apphelp.dll"
    add("path_over32767_units",base()+[dict(name="apphelp.dll",path=longpath)],False,reason="invalid_path")
    unicode_context=dict(expected_self="D:\\PolicyFixture\\Caf\u00e9\\\U0001f600\\app.exe",
                         expected_runtime="D:\\PolicyFixture\\Caf\u00e9\\\U0001f600\\runtime")
    add("exact_scalar_native_context",base(unicode_context),True,context=unicode_context,classes=native_classes)
    rows=base(unicode_context);rows[-1]["path"]=rows[-1]["path"].replace("Caf\u00e9","Cafe\u0301")
    add("no_Unicode_normalization",rows,False,context=unicode_context,reason="protected_native_not_eligible")
    rows=base(unicode_context);rows[-1]["path"]=rows[-1]["path"].replace("Caf\u00e9","Caf\u00c9")
    add("no_nonASCII_casefold",rows,False,context=unicode_context,reason="protected_native_not_eligible")
    # This is the existing, independently verified single census, read as data once.
    verification=HERE/"SELF-MODULE-CENSUS-RESULT-VERIFICATION-v1.json"
    assert pin(verification)["sha256"]=="4b628df880898e892482399585436b5fa2a068aed607947cd59e5f3d2f8b3f1e"
    prior=json.loads(verification.read_text(encoding="utf-8"))
    run=Path(prior["output_directory"])
    result=run/"execution/child/result.jsonl"
    expected=next(item for item in prior["outputs"] if item["relative_path"]=="execution/child/result.jsonl")
    assert pin(result)=={k:expected[k] for k in ("path","bytes","sha256")}
    observed=[json.loads(line) for line in result.read_text(encoding="utf-8").split("\n") if line]
    modules=[dict(name=row["snapshot_name"]["utf8"],path=row["path"]["utf8"]) for row in observed if row.get("event")=="module_metadata"]
    description=next(row for row in observed if row.get("event")=="module_census_classification")
    config=json.loads((run/"effective-protocol.json").read_text(encoding="utf-8"))
    context=dict(expected_self=config["executable"]["path"],expected_runtime=config["argv"][2])
    mapping={"self_executable":"self_executable","pinned_runtime_report":"pinned_runtime",
             "listed_system_report":"trusted_platform_context","unlisted_report":"trusted_platform_context"}
    add("verified_current_census17_metadata_only",modules,True,context=context,
        classes=[mapping[row["category"]] for row in description["rows"]])
    assert len(modules)==17 and sum(c=="trusted_platform_context" for c in cases[-1]["expected_classes"])==12
    value=dict(schema_version=1,status="finite_shared_source_pure_policy_vectors_not_native_conformance",
        module_policy_id=contract["module_policy_id"],module_policy_sha256=contract["module_policy_sha256"],
        semantic_contract=pin(CONTRACT),census_verification=pin(verification),observed_metadata_artifact=pin(result),
        generator=pin(Path(__file__)),reason_grading="Admission/categories/fingerprint normative; exact reason only for explicitly isolated predicate; omitted reasons are intentionally ungraded",
        cases=cases,activity=dict(SDK_or_target_calls=0,children=0,reported_image_reads=0,new_census_or_tracing=0))
    with OUTPUT.open("x",encoding="utf-8",newline="\n") as stream:
        json.dump(value,stream,sort_keys=True,ensure_ascii=True,indent=2);stream.write("\n")
    print(json.dumps(dict(vectors=len(cases),sha256=pin(OUTPUT)["sha256"])))


if __name__=="__main__":main()
