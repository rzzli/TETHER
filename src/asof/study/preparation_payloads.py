"""Pure full-source payload rendering; neither source admission nor execution.

Only guide text and role ordering are reused from the pinned recorded contract.
Its synthetic execution allowlist and byte capacity policy remain unchanged.
"""

import copy

from asof.serde import canonical, encode, fingerprint, freeze
from .diagnostic import ACTIVE_SIMPLIFIED_SCHEMA
from .diagnostic_codec import need, quote_choices, validate_request
from .fixed_evidence import load_plan


def prepare_payloads(request, *, _actual_history=None):
    """Certify six exact hypothetical histories, never an all-history token bound.

    A coordinator must separately verify source admission and quote each payload.
    These documents cannot be handed to the recorded/native execution interfaces
    as authorization. Actual future histories would require new quotations.
    """
    request = encode(validate_request(request))
    plan = load_plan()
    aliases = encode(quote_choices(request))
    need(0 < len(aliases) <= 3, "Preparation requires one to three source aliases")
    cap = min(3, request["source_request"]["bounds"]["max_claims"])
    guide = plan["guide"]
    need(
        guide.count("Active limits: 3 claims;") == 1, "Unknown response guide revision"
    )
    guide = guide.replace("Active limits: 3 claims;", f"Active limits: {cap} claims;")
    schema = copy.deepcopy(encode(ACTIVE_SIMPLIFIED_SCHEMA))
    schema.pop("$comment", None)
    schema["properties"]["claims"]["maxItems"] = cap
    claim = schema["properties"]["claims"]["items"]["properties"]
    claim["source_ids"]["items"] = {"type": "string", "enum": list(aliases)}
    claim["quote_pointers"]["items"] = {
        "type": "string",
        "enum": sorted({p for choices in aliases.values() for p in choices}),
    }
    table = [
        dict(
            source_id=alias,
            observation_id=request["source_request"]["evidence"][index][
                "observation_id"
            ],
            pointers=list(choices),
        )
        for index, (alias, choices) in enumerate(aliases.items())
    ]
    cells = []
    for arm, stages in (
        ("asof_interpretation", plan["asof_stages"]),
        ("adapted_virtual_biotech_interpretation", plan["stage_order"]),
    ):
        for index, stage in enumerate(stages):
            data = dict(
                original_request=request,
                original_source_table=table,
                stage=stage,
                prior_source_id_feedback=(
                    encode(_actual_history[(arm, index)])
                    if _actual_history is not None and (arm, index) in _actual_history
                    else [
                        dict(stage=prior, source_ids=list(aliases))
                        for prior in stages[:index]
                    ]
                ),
                feedback_authority="untrusted_generated_selection_not_evidence",
            )
            need(
                len(canonical(data["prior_source_id_feedback"])) <= 1024,
                "Hypothetical history exceeds unchanged projection bound",
            )
            prompt = (
                "<|im_start|>system\n"
                + guide
                + "\n"
                + plan["role_guides"][stage]
                + "<|im_end|>\n<|im_start|>user\n"
                + canonical(data).decode("utf-8").replace("<|", "<\\u007c")
                + "<|im_end|>\n<|im_start|>assistant\n"
            )
            payload = dict(
                prompt=prompt,
                n_predict=1024,
                temperature=0.0,
                seed=42,
                cache_prompt=False,
                json_schema=schema,
                stop=["<|im_end|>"],
                stream=False,
            )
            need(
                len(prompt.encode("utf-8")) <= 32768
                and len(canonical(payload)) <= 65536,
                "Complete preparation payload exceeds byte limit; no source clipping",
            )
            cells.append(
                dict(
                    arm=arm,
                    stage_index=index,
                    stage_name=stage,
                    semantic_data=data,
                    payload=payload,
                    request_sha256=fingerprint(request),
                    payload_sha256=fingerprint(payload),
                    claim_limit=cap,
                    prompt_utf8_bytes=len(prompt.encode("utf-8")),
                    http_payload_bytes=len(canonical(payload)),
                    history_scope="exact_hypothetical_only_not_a_token_maximum",
                    execution_authorized=False,
                )
            )
    return freeze(cells)


def prepare_actual_payload(request, arm, index, feedback):
    """Pure exact-history rendering, never source or predecessor authorization."""
    request = freeze(encode(validate_request(request)))
    feedback = freeze(encode(feedback))
    plan = load_plan()
    arms = {
        "asof_interpretation": plan["asof_stages"],
        "adapted_virtual_biotech_interpretation": plan["stage_order"],
    }
    need(
        isinstance(arm, str)
        and arm in arms
        and type(index) is int
        and 0 <= index < len(arms[arm]),
        "Unknown actual stage",
    )
    stages = arms[arm]
    aliases = list(quote_choices(request))
    need(
        isinstance(feedback, tuple) and len(feedback) == index,
        "Actual history stage count differs",
    )
    for prior, item in zip(stages[:index], feedback):
        need(
            set(item) == {"stage", "source_ids"}
            and item["stage"] == prior
            and isinstance(item["source_ids"], tuple)
            and all(
                isinstance(alias, str) and alias in aliases
                for alias in item["source_ids"]
            )
            and list(item["source_ids"])
            == [alias for alias in aliases if alias in item["source_ids"]],
            "Actual history identity or source projection differs",
        )
    for item in prepare_payloads(request, _actual_history={(arm, index): feedback}):
        if item["arm"] == arm and item["stage_index"] == index:
            result = encode(item)
            result["history_scope"] = "exact_actual_projection_not_a_token_maximum"
            return freeze(result)
    raise AssertionError("Validated stage missing")
