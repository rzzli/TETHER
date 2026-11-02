"""Apply only the reviewed post-P09 presentation delta; retain inverse proof."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
UPDATES = {
    "manuscript.md": {
        "before_sha256": "b01d42fccaf046ad0db52d0becd36be994eac440759f23aefaa0673bf7a9ce29",
        "edits": [{
            "old": "Current full-study wrappers bind exact local paths and environment. The local figure rebuild does not qualify installed or relocated source-inclusive reproduction. Public release qualification is unfinished at this draft: source terms, lawful file allowlisting, exact-release tests and supported replay scopes require retained evidence before a release claim. This limitation must be revised only when those checks actually pass.",
            "new": "The P06 study and its results and costs remain frozen: primary production took 203.828 seconds and its source audit took 7.125 seconds. A separately versioned, post-result P09 adapter has qualified installed, relocated reconstruction on Windows x64 with CPython 3.11.15 and PyArrow 21.0.0. The native replay used all 137 exact originals; the complete adapter reproduced 38 outputs and 90 decisions across twelve native units and fourteen constructed controls. Reconstruction took 289.938 seconds, and the separate source-inclusive independent audit passed 6,862 checks in 15.187 seconds. The minimal public catalog creates new reference fingerprints; historical equivalence removes only `method.catalog_sha256`. New G0 checks public protocol, code, input and output byte bindings under independently retained authority, without establishing publisher authenticity or verifying old private journals or sealed trees. Fresh exact-byte reacquisition of the 136 external Open Targets originals remains untested. This local technical qualification establishes neither scientific validity nor public availability; author facts remain deferred.",
        }],
    },
    "supplement.md": {
        "before_sha256": "977aba2fc3cab68513a78fde08b3cacf0a375af52c908c0fd46bbf1818337200",
        "edits": [{
            "old": "The present verified scopes are local source-inclusive study/audit and local result rebuild. Clean installed/relocated replay of the complete actual-format study is not yet qualified. Core API logical-path support alone does not qualify the stronger P05 wrapper. A lawful public fixture replay, if released, must be labeled separately from actual-source reproduction. Selected-row extracts cannot impersonate complete originals or satisfy their full-file hashes. The public package must either lawfully include required assets or state the exact external inputs and supported reconstruction steps.",
            "new": "Verified scopes now also include the separately versioned P09 installed, relocated reconstruction and its source-inclusive independent audit on Windows x64, CPython 3.11.15 and PyArrow 21.0.0. These are post-result technical qualification operations, separate from the frozen P06 study and its 203.828-second production / 7.125-second source audit. Reconstruction reproduced all 38 output hashes and 90 decisions in 289.938 seconds; the separate audit passed 6,862 checks in 15.187 seconds. All 137 exact originals remain mandatory: 136 Open Targets files are external, and the one exact CC0 HGNC file is included with its receipt. Selected-row extracts cannot replace them. The public catalog produces genuine new reference identities; equivalence removes only `method.catalog_sha256`, while new G0 does not establish publisher authenticity or old private-archive integrity. Fresh exact-byte reacquisition of the 136 external originals remains untested. Policy-session logical counters exclude repeated compiler/caller reads; total physical I/O and platform cost remain unknown. The frozen P09 runtime bundle retains its earlier paper snapshot; later P10 working-paper and PDF updates are separate versions.",
        }, {
            "old": "No public release DOI, hosted exact-release result or dataset redistribution permission is claimed in this draft. Apache-2.0 applies to project code; external provider and underlying-source terms require product-specific review. Exclude credentials, private machine paths, historical bespoke responses and their descendants, raw clinical outcomes and unreviewed model/data bytes from a public allowlist. A local artifact can contain evidence not licensed for redistribution; its presence is not clearance.",
            "new": "No public deposit, release DOI, hosted exact-release result or publication is claimed in this draft. Apache-2.0 applies to project code; external provider and underlying-source terms require product-specific review. The qualified local allowlist includes the exact CC0 HGNC original and project receipt metadata; 136 Open Targets originals remain external. This narrow inclusion is not general dataset redistribution clearance. Credentials, private machine paths, historical bespoke responses and their descendants, raw clinical outcomes and unreviewed model/data bytes are excluded. A local artifact can contain evidence not licensed for redistribution; its presence is not clearance.",
        }],
    },
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    prepared = {}
    for name, item in UPDATES.items():
        raw = (ROOT / "paper" / name).read_bytes()
        assert sha(raw) == item["before_sha256"], name
        transformed = raw
        for edit in item["edits"]:
            old, new = edit["old"].encode(), edit["new"].encode()
            assert transformed.count(old) == 1 and new not in transformed
            transformed = transformed.replace(old, new, 1)
        inverse = transformed
        for edit in reversed(item["edits"]):
            inverse = inverse.replace(edit["new"].encode(), edit["old"].encode(), 1)
        assert inverse == raw
        item["after_sha256"] = sha(transformed)
        prepared[name] = transformed
    output = HERE / "SOURCE-DELTA-v1.json"
    assert not output.exists()
    for name, raw in prepared.items():
        (ROOT / "paper" / name).write_bytes(raw)
    output.write_text(json.dumps({"schema_version": 1,
        "method": "p10.exact_inverse_release_scope_delta.v1", "status": "PASS_EXACT_INVERSE_DELTA",
        "role": "evaluation_only", "agent_visible": False, "edited_paragraphs": 3,
        "other_source_bytes_unchanged": True, "sources": UPDATES}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: item["after_sha256"] for name, item in UPDATES.items()}))


if __name__ == "__main__":
    main()
