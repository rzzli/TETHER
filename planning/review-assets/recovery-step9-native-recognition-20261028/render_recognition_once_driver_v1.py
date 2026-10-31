"""Pure authoring template: return successor bytes; never read/write or execute them.

Actual parent/protocol identity and permission require separate root review. This
function validates only syntax, the frozen template and the permitted byte delta.
It deliberately has no CLI, filesystem calls, import/dispatch or default bindings.
"""
import ast
import copy
import hashlib
import re

TEMPLATE_SHA256 = "a9e115317b9a3851dddf832c5c3042f511acfd9bbe91f32a5b97a4e7e8d6f092"
PHASE = r"D:\Projects\drug_target_agents\planning\review-assets\recovery-step9-native-recognition-20261028"
BINDING_KEYS = {"helper_path", "helper_sha256", "protocol_path", "protocol_sha256", "decision_path"}
ASSIGNMENTS = {"BOUND", "HELPER", "HELPER_SHA", "PROTOCOL", "PROTOCOL_SHA", "DECISION"}


def _require(value, message):
    if not value:
        raise RuntimeError(message)


def _metadata_path(value, pattern):
    _require(type(value) is str and value.startswith(PHASE + "\\"), "Exact fixed technical phase path required")
    leaf = value[len(PHASE) + 1:]
    _require(re.fullmatch(pattern, leaf) is not None, "Exact prospective technical filename required")
    return value


def _hash(value):
    _require(type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None,
             "Exact lowercase technical SHA256 required")
    return value


def _normalized(tree, template):
    result = copy.deepcopy(tree)
    baseline = {node.targets[0].id: node.value for node in template.body
                if isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id in ASSIGNMENTS}
    found = set()
    for node in result.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ASSIGNMENTS:
                _require(name not in found, "Duplicate binding assignment")
                found.add(name)
                node.value = copy.deepcopy(baseline[name])
    _require(found == ASSIGNMENTS, "Missing exact binding assignment")
    return ast.dump(result, include_attributes=False)


def render_driver(template_raw, bindings):
    """Render only BOUND and five path/hash bindings; no identity/permission claim.

    Caller must independently verify actual frozen technical bytes before using
    this result. In-memory rendering neither consumes output nor creates a driver.
    """
    _require(type(template_raw) is bytes and hashlib.sha256(template_raw).hexdigest() == TEMPLATE_SHA256,
             "Frozen reviewed unbound driver template changed")
    _require(type(bindings) is dict and set(bindings) == BINDING_KEYS, "Exact five literal bindings required")
    helper = _metadata_path(bindings["helper_path"], r"run_recognition_observation_v[1-9][0-9]*\.py")
    protocol = _metadata_path(bindings["protocol_path"], r"RECOGNITION-EXECUTION-PROTOCOL-v[1-9][0-9]*\.json")
    decision = _metadata_path(bindings["decision_path"], r"RECOGNITION-EXECUTION-ROOT-DECISION-v[1-9][0-9]*\.json")
    helper_sha = _hash(bindings["helper_sha256"])
    protocol_sha = _hash(bindings["protocol_sha256"])
    replacements = {
        "BOUND = False": "BOUND = True",
        "HELPER = None": "HELPER = Path(" + repr(helper) + ")",
        "HELPER_SHA = None": "HELPER_SHA = " + repr(helper_sha),
        "PROTOCOL = None": "PROTOCOL = Path(" + repr(protocol) + ")",
        "PROTOCOL_SHA = None": "PROTOCOL_SHA = " + repr(protocol_sha),
        "DECISION = None": "DECISION = Path(" + repr(decision) + ")",
    }
    text = template_raw.decode("utf-8", "strict")
    for before, after in replacements.items():
        # Whole assignment lines prevent accidental prefix matches such as
        # HELPER inside HELPER_SHA or an explanatory docstring.
        needle = "\n" + before + "\n"
        _require(text.count(needle) == 1, "Exact frozen assignment line missing")
        text = text.replace(needle, "\n" + after + "\n", 1)
    template = ast.parse(template_raw)
    rendered = text.encode("utf-8")
    _require(_normalized(ast.parse(rendered), template) == ast.dump(template, include_attributes=False),
             "Nonbinding driver source delta forbidden")
    return rendered
