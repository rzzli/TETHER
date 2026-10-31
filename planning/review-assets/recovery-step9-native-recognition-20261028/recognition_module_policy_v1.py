"""Data-only recognition-phase module matcher. No reported path is opened, resolved, hashed or loaded."""
import hashlib
import json
import re

SEMANTICS = {'case': 'ASCII_A_to_Z_only', 'classification_order': ['exact_self', 'reserved_self_rejection', 'protected_native', 'trusted_platform', 'rejection'], 'core_names': ['libomp.dll', 'ggml-base.dll', 'ggml.dll', 'llama.dll'], 'declared_runtime_names': ['libomp.dll', 'ggml-base.dll', 'ggml.dll', 'llama.dll', 'ggml-cpu-x64.dll'], 'drive': 'ASCII_letter_colon_separator', 'filesystem_alias_resolution': False, 'forbidden_ascii_units': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 127], 'forbidden_component_characters': '<>:"|?*~', 'forbidden_component_endings': ['.', ' '], 'forbidden_components': ['', '.', '..'], 'forbidden_device_stems': ['con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9', 'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'], 'maximum_modules': 64, 'maximum_name_utf16_units': 255, 'maximum_path_utf16_units': 32767, 'mode': 'recognition_only', 'platform_basename_pattern': '[a-z0-9_][a-z0-9_.-]*\\.dll', 'platform_root': 'C:\\Windows\\System32', 'policy_id': 'trusted-System32-recognition-v1', 'protected_prefixes': ['ggml', 'llama', 'libomp'], 'reported_platform_image_operations': 0, 'schema_version': 1, 'self_and_each_core_required_once': True, 'separator': 'slash_to_backslash', 'unicode_scalars_required': True, 'unique_ascii_folded_names_and_paths': True, 'phases': {'pre_cpu': {'eligible_native_names': ['libomp.dll', 'ggml-base.dll', 'ggml.dll', 'llama.dll'], 'required_native_names': ['libomp.dll', 'ggml-base.dll', 'ggml.dll', 'llama.dll'], 'CPU_module_eligible': False}, 'post_cpu': {'eligible_native_names': ['libomp.dll', 'ggml-base.dll', 'ggml.dll', 'llama.dll', 'ggml-cpu-x64.dll'], 'required_native_names': ['libomp.dll', 'ggml-base.dll', 'ggml.dll', 'llama.dll', 'ggml-cpu-x64.dll'], 'CPU_module_eligible': True}}, 'model_access_authorized_by_module_reports': False}
POLICY_ID = SEMANTICS["policy_id"]
POLICY_SHA256 = hashlib.sha256(json.dumps(SEMANTICS, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
_TRANSLATION = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ/", "abcdefghijklmnopqrstuvwxyz\\")
_CONTROLS = frozenset(SEMANTICS["forbidden_ascii_units"])
_DEVICES = frozenset(SEMANTICS["forbidden_device_stems"])
_CORE = frozenset(SEMANTICS["core_names"])
_NATIVE = frozenset(SEMANTICS["declared_runtime_names"])


class ModulePolicyError(ValueError):
    def __init__(self, reason, ordinal=None):
        self.reason, self.ordinal = reason, ordinal
        super().__init__(reason)


def fail(reason, ordinal=None):
    raise ModulePolicyError(reason, ordinal)


def scalar_length(value, limit, reason):
    if type(value) is not str or not value or len(value)>limit:
        fail(reason)
    try:
        count=len(value.encode("utf-16-le", errors="strict"))//2
    except UnicodeError:
        fail(reason)
    if count>limit:fail(reason)
    return count


def fold(value):
    return value.translate(_TRANSLATION)


def component(value, reason):
    if value in SEMANTICS["forbidden_components"] or value.endswith(tuple(SEMANTICS["forbidden_component_endings"])):
        fail(reason)
    if any(ord(char) in _CONTROLS or char in SEMANTICS["forbidden_component_characters"] for char in value):
        fail(reason)
    if fold(value.split(".",1)[0]) in _DEVICES:fail(reason)


def canonical_path(value):
    scalar_length(value,SEMANTICS["maximum_path_utf16_units"],"invalid_path")
    if len(value)<4 or value[0] not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz" or value[1] != ":" or value[2] not in "\\/":
        fail("invalid_path")
    converted=value.replace("/","\\")
    for part in converted[3:].split("\\"):
        component(part,"invalid_path")
    return fold(converted)


def canonical_name(value):
    scalar_length(value,SEMANTICS["maximum_name_utf16_units"],"invalid_name")
    if "\\" in value or "/" in value:fail("invalid_name")
    component(value,"invalid_name")
    return fold(value)


def match_modules(rows, *, expected_self, expected_runtime, phase):
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
    self_name=self_path.rsplit("\\",1)[1]
    if type(rows) is not list or not 1<=len(rows)<=SEMANTICS["maximum_modules"]:fail("module_count_limit")
    names,paths=set(),set();required={"self_executable":0,**{name:0 for name in policy["required_native_names"]}}
    results=[]
    for ordinal,row in enumerate(rows,1):
        if type(row) is not dict or set(row)!={"name","path"}:fail("invalid_metadata",ordinal)
        try:name=canonical_name(row["name"]);path=canonical_path(row["path"])
        except ModulePolicyError as error:fail(error.reason,ordinal)
        parent,basename=path.rsplit("\\",1)
        if name!=basename:fail("name_path_mismatch",ordinal)
        if name in names or path in paths:fail("duplicate_report",ordinal)
        names.add(name);paths.add(path)
        if path==self_path:category="self_executable";required["self_executable"]+=1
        elif name==self_name:fail("reserved_self_wrong_path",ordinal)
        elif parent==runtime or name in _NATIVE or any(name.startswith(prefix) for prefix in SEMANTICS["protected_prefixes"]):
            if name not in eligible or path!=runtime+"\\"+name:fail("protected_native_not_eligible",ordinal)
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
