"""Fictional policy boundaries, without original reads, network or model calls."""
from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from asof.serde import ContractError, canonical, fingerprint
from asof.provenance import catalog_index
from tether import _catalog_policy as policy


def fixture():
    """A valid fictional two-input use; no paths are accessed by this builder."""
    rows = [dict(dataset_id=key, provider_id="fixture", roles=roles, dependencies=[],
                 collection_status="planned", parse_status="not_run", validation_status="not_run")
            for key, roles in (("raw", ["agent_evidence"]), ("reference", ["reference"]),
                               ("packets", ["agent_evidence"]), ("qc", ["evaluation_only", "reference"]))]
    source = canonical(dict(schema_version=1, providers=[dict(provider_id="fixture")], datasets=rows))
    document = policy.migrate_catalog(source, source_path="data/catalog/sources.json",
                                     policy_id="fixture-v2", created_at_utc="2026-11-02T00:00:00Z")
    for row in document["products"]:
        if row["dataset_id"] in {"raw", "packets"}:
            row["dependency_review_status"] = "reviewed_for_selected_frame"
    availability = dict(first_public_at=None, release_public_at=None, record_public_at=None,
                        annotation_public_at=None, retrieved_at="2026-10-01", basis="public_download_receipt",
                        uncertainty="Fixture does not establish first publication", known_public_by="2026-10-01T00:00:00Z",
                        evidence_ref="b" * 64)
    raw = policy.artifact_record(dataset_id="raw", release_id="25.09", root_alias="raw", relative_path="raw.bin",
                                 sha256="a" * 64, bytes=7, kind="raw", parents=[], availability=availability,
                                 temporal_classification="contemporary_only", source_url="https://example.org/raw.bin",
                                 provenance=dict(kind="download_receipt", evidence=[dict(path="reports/source.json", sha256="c" * 64)],
                                                 receipt=dict(root_alias="raw", relative_path="manifests/receipt-archive/fixture.json",
                                                              sha256="b" * 64, receipt_id="fixture-receipt", url="https://example.org/raw.bin")),
                                 scope="Fictional selected original", scientific_validation="not_established")
    packet = policy.artifact_record(dataset_id="packets", release_id="fixture", root_alias="snapshot", relative_path="evidence.json",
                                    sha256="d" * 64, bytes=12, kind="packet", parents=[raw["artifact_id"]], availability=availability,
                                    temporal_classification="contemporary_only", source_url="https://example.org/fixture",
                                    provenance=dict(kind="generated", evidence=[dict(path="reports/build.json", sha256="e" * 64)], receipt=None),
                                    scope="Fictional packet", scientific_validation="not_established")
    node = dict(source_id="raw-node", dataset_id="raw", release_id="25.09", path="raw.bin", sha256="a" * 64,
                role="agent_evidence", availability=copy.deepcopy(availability), temporal_classification="contemporary_only",
                source_url="https://example.org/raw.bin", parents=[], computed_at=None, method_id=None, method_version=None,
                receipt_path="manifests/receipt-archive/fixture.json", receipt_sha256="b" * 64)
    art = dict(artifact_id="packet-node", dataset_id="packets", release_id="fixture", path="evidence.json", sha256="d" * 64,
               role="agent_evidence", availability=copy.deepcopy(availability), temporal_classification="contemporary_only",
               source_url="https://example.org/fixture", input_refs=["raw-node"], access_approved=True)
    case = dict(schema_version=2, case_id="fictional", origin="2026-10-02", origin_at="2026-10-02T00:00:00Z")
    snapshot = dict(schema_version=2, snapshot_id="fixture", profile="contemporary_assessment", origin=case["origin"],
                    origin_at=case["origin_at"], raw_root="D:/fictional/raw", sources=[node], artifacts=[art], allow_reconstructed=False)
    use = dict(use_id="fixture-use", kind="contemporary_evidence", status="allowed", profile=snapshot["profile"],
               origin_at=case["origin_at"], frame_sha256="f" * 64, case_fingerprint=fingerprint(case),
               snapshot_fingerprint=fingerprint(snapshot), raw_root_alias="raw", snapshot_root_alias="snapshot",
               grants=[dict(artifact_id=raw["artifact_id"], role="agent_evidence"),
                       dict(artifact_id=packet["artifact_id"], role="agent_evidence")], blockers=[])
    document["artifacts"] = [raw, packet]; document["uses"] = [use]
    return dict(policy=document, case=case, snapshot=snapshot, source_bytes=source,
                roots=dict(raw="D:/fictional/raw", snapshot="D:/fictional/snapshot"))


def authorize(f):
    return policy.authorize_snapshot(f["policy"], f["snapshot"], case=f["case"], use_id="fixture-use", root_aliases=f["roots"])


def rebind(f):
    """An adversarial author can update case pins; other invariants must survive."""
    use = f["policy"]["uses"][0]
    use["case_fingerprint"] = fingerprint(f["case"])
    use["snapshot_fingerprint"] = fingerprint(f["snapshot"])


class CatalogPolicyTests(unittest.TestCase):
    def test_valid_selection_has_exact_nodes_and_nonselected_products_denied(self):
        f = fixture(); result = authorize(f)
        self.assertEqual({x["source_id"] for x in result["binding"]["inventory"]}, {"raw-node", "packet-node"})
        self.assertEqual(result["binding"]["frame_sha256"], "f" * 64)
        rows = {r["dataset_id"]: r for r in result["projection"]["datasets"]}
        self.assertEqual(rows["raw"]["roles"], ["agent_evidence"])
        self.assertEqual(rows["reference"]["roles"], ["evaluation_only"])
        self.assertEqual(result, authorize(f))
        catalog_index(result["projection"])

    def test_migration_preserves_every_product_status_and_source_anchor(self):
        f = fixture(); original = policy.strict_json(f["source_bytes"])
        self.assertEqual(policy.validate_source_catalog(f["policy"], f["source_bytes"]), original)
        self.assertEqual([r["metadata"] for r in f["policy"]["products"]], original["datasets"])
        self.assertTrue(all(r["metadata"]["collection_status"] == "planned" for r in f["policy"]["products"]))

    def test_structural_fingerprint_cannot_replace_byte_anchor(self):
        f = fixture(); changed = f["policy"]["products"][3]
        changed["metadata"]["roles"] = ["reference"]
        changed["agent_use_policy"] = "requires_artifact_grant"
        reconstructed = policy._legacy_document(f["policy"])
        f["policy"]["source_catalog"]["document_fingerprint"] = fingerprint(reconstructed)
        policy.validate_policy(f["policy"])
        with self.assertRaisesRegex(ContractError, "metadata anchor"):
            policy.validate_source_catalog(f["policy"], f["source_bytes"])
        with self.assertRaisesRegex(ContractError, "byte anchor"):
            policy.validate_source_catalog(fixture()["policy"], f["source_bytes"] + b"\n")

    def test_schema1_compatibility_is_not_silent_schema2_acceptance(self):
        catalog_index(policy.strict_json(fixture()["source_bytes"]))
        with self.assertRaises(ContractError): catalog_index(fixture()["policy"])

    def test_strict_json_rejects_duplicates_nonfinite_and_noninteger_version(self):
        for raw in (b'{"schema_version":2,"schema_version":2}', b'{"x":NaN}', b'{"x":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(ContractError): policy.strict_json(raw)
        f=fixture(); f["policy"]["schema_version"]=2.0
        with self.assertRaises(ContractError): policy.validate_policy(f["policy"])

    def test_unknown_policy_keys_duplicate_products_and_invalid_hashes_rejected(self):
        mutations = [lambda p:p.update(allowed=True), lambda p:p["products"].append(copy.deepcopy(p["products"][0])),
                     lambda p:p["source_catalog"].update(sha256="A"*64)]
        for change in mutations:
            f=fixture(); change(f["policy"])
            with self.subTest(change=change), self.assertRaises(ContractError): policy.validate_policy(f["policy"])

    def test_input_cycles_unknown_optional_and_components_rejected(self):
        for kind in ("cycle", "unknown", "optional"):
            f=fixture(); rows=f["policy"]["products"]
            if kind=="cycle": rows[0]["input_dependencies"]=["raw"]
            elif kind=="unknown": rows[0]["input_dependencies"]=["missing"]
            else: rows[0]["conditional_input_groups"]=[dict(requirement="Optional", dataset_ids=["missing"])]
            with self.subTest(kind=kind), self.assertRaises(ContractError): policy.validate_policy(f["policy"])

    def test_genetics_edge_migration_does_not_erase_training_inputs(self):
        original=policy.strict_json(fixture()["source_bytes"])
        for name, roles, deps in [("genetics_qc_cases",["evaluation_only"],[]), ("igsr_ld_reference",["reference"],[]),
             ("genetics_results",["agent_evidence"],["raw","genetics_qc_cases","igsr_ld_reference"]),
             ("scorer_artifacts",["reference"],["qc"])]:
            original["datasets"].append(dict(dataset_id=name,provider_id="fixture",roles=roles,dependencies=deps,
                collection_status="planned",parse_status="not_run",validation_status="not_run"))
        original["datasets"][-2]["conditional_input_groups"]=[dict(requirement="LD for methods requiring it",dataset_ids=["igsr_ld_reference"])]
        migrated=policy.migrate_catalog(canonical(original),source_path="catalog.json",policy_id="fixture",created_at_utc="2026-11-02T00:00:00Z")
        rows={r["dataset_id"]:r for r in migrated["products"]}
        self.assertEqual(rows["genetics_results"]["input_dependencies"],["raw"])
        self.assertEqual(rows["genetics_results"]["validation_dependencies"],["genetics_qc_cases"])
        self.assertEqual(rows["scorer_artifacts"]["input_dependencies"],["qc"])
        self.assertEqual(rows["genetics_results"]["metadata"]["dependencies"],["raw","genetics_qc_cases","igsr_ld_reference"])

    def test_evaluator_deny_survives_reference_role_and_optional_classification(self):
        f=fixture(); row=f["policy"]["products"][3]
        row["agent_use_policy"]="requires_artifact_grant"
        with self.assertRaisesRegex(ContractError,"evaluator deny"): policy.validate_policy(f["policy"])
        f=fixture(); f["policy"]["products"][0]["validation_dependencies"]=["qc"]
        # Validation references need not be scientific parents and don't require opening answers.
        authorize(f)

    def test_mutating_returned_projection_does_not_modify_authority(self):
        f=fixture(); result=authorize(f); result["projection"]["datasets"][3]["roles"]=["reference"]
        again=authorize(f)
        self.assertEqual(again["projection"]["datasets"][3]["roles"],["evaluation_only"])
        result["binding"]["inventory"][0]["parents"].append("invented")
        self.assertEqual(authorize(f)["binding"]["inventory"][0]["parents"],[])

    def test_changed_case_snapshot_or_origin_rejected_even_without_source_read(self):
        for kind in ("case", "snapshot", "origin"):
            f=fixture()
            if kind=="case": f["case"]["case_id"]="other"
            elif kind=="snapshot": f["snapshot"]["snapshot_id"]="other"
            else:
                f["snapshot"]["origin_at"]="2026-10-03T00:00:00Z"; rebind(f)
            with self.subTest(kind=kind), self.assertRaises(ContractError): authorize(f)

    def test_undeclared_artifact_identity_field_changes_rejected(self):
        for field, value in [("dataset_id","reference"),("release_id","newer"),("path","Raw.bin"),("sha256","9"*64)]:
            f=fixture(); f["snapshot"]["sources"][0][field]=value; rebind(f)
            with self.subTest(field=field), self.assertRaises(ContractError): authorize(f)

    def test_supplied_role_changes_and_hidden_unused_nodes_rejected(self):
        f=fixture(); f["snapshot"]["sources"][0]["role"]="reference"; rebind(f)
        with self.assertRaises(ContractError): authorize(f)
        f=fixture(); extra=copy.deepcopy(f["snapshot"]["sources"][0]); extra["source_id"]="unused-evaluator"; extra["role"]="evaluation_only"
        f["snapshot"]["sources"].append(extra); rebind(f)
        with self.assertRaises(ContractError): authorize(f)

    def test_parent_removal_or_fabrication_does_not_pass_rebinding(self):
        for parents in ([], ["unknown"], ["raw-node", "raw-node"], ["packet-node"]):
            f=fixture(); f["snapshot"]["artifacts"][0]["input_refs"]=parents; rebind(f)
            with self.subTest(parents=parents), self.assertRaises(ContractError): authorize(f)

    def test_extra_grants_and_duplicate_use_rejected(self):
        f=fixture(); f["policy"]["uses"][0]["grants"].append(copy.deepcopy(f["policy"]["uses"][0]["grants"][0]))
        with self.assertRaises(ContractError): authorize(f)
        f=fixture(); f["policy"]["uses"].append(copy.deepcopy(f["policy"]["uses"][0]))
        with self.assertRaises(ContractError): authorize(f)

    def test_receipt_path_and_hash_must_equal_artifact_policy(self):
        for field,value in [("receipt_path","manifests/mutable.json"),("receipt_sha256","9"*64)]:
            f=fixture(); f["snapshot"]["sources"][0][field]=value; rebind(f)
            with self.subTest(field=field), self.assertRaises(ContractError): authorize(f)

    def test_traversal_and_root_alias_collisions_rejected(self):
        for path in ("../raw.bin","/raw.bin","a//raw.bin","a/./raw.bin","a\\raw.bin","a:raw.bin","a /raw.bin", "NUL", "a/CON.txt"):
            with self.subTest(path=path), self.assertRaises(ContractError): policy.relative_path(path)
        f=fixture(); f["roots"]["snapshot"]="d:/FICTIONAL/raw"
        with self.assertRaisesRegex(ContractError,"collision"): authorize(f)

    def test_future_or_unverified_raw_availability_rejected(self):
        f=fixture(); f["policy"]["artifacts"][0]["availability"]["known_public_by"]="2026-10-03T00:00:00Z"
        f["snapshot"]["sources"][0]["availability"]=copy.deepcopy(f["policy"]["artifacts"][0]["availability"]); rebind(f)
        with self.assertRaisesRegex(ContractError,"unavailable"): authorize(f)
        f=fixture(); f["policy"]["artifacts"][0]["temporal_classification"]="unverified"
        f["snapshot"]["sources"][0]["temporal_classification"]="unverified"; rebind(f)
        with self.assertRaises(ContractError): authorize(f)

    def test_history_cannot_be_qualified_by_contemporary_download(self):
        f=fixture(); f["snapshot"]["profile"]="historical_benchmark"; f["policy"]["uses"][0]["profile"]="historical_benchmark"; rebind(f)
        with self.assertRaisesRegex(ContractError,"historical"): authorize(f)

    def test_aact_manual_archive_is_metadata_only_and_no_invented_receipt(self):
        f=fixture(); raw=f["policy"]["artifacts"][0]
        raw["provenance"]["kind"]="manual_archive"; raw["provenance"]["receipt"]=None
        raw["availability"]=None; raw["temporal_classification"]="unverified"; raw["source_url"]=None
        use=f["policy"]["uses"][0]; use.update(status="blocked",kind="endpoint_evaluation",blockers=["Historical availability unknown"])
        use.update(case_fingerprint=None,snapshot_fingerprint=None,frame_sha256=None,grants=[])
        policy.validate_policy(f["policy"])
        with self.assertRaisesRegex(ContractError,"blocked"): authorize(f)
        use.update(status="allowed",blockers=[],case_fingerprint=fingerprint(f["case"]),snapshot_fingerprint=fingerprint(f["snapshot"]),frame_sha256="f"*64)
        with self.assertRaises(ContractError): policy.validate_policy(f["policy"])

    def test_raw_and_packet_actual_id_aliasing_rejected(self):
        f=fixture(); f["snapshot"]["artifacts"][0]["artifact_id"]="raw-node"; rebind(f)
        with self.assertRaisesRegex(ContractError,"duplicate"): authorize(f)

    def test_unreviewed_product_cannot_be_granted_and_alias_location_is_bound(self):
        f=fixture(); f["policy"]["products"][0]["dependency_review_status"]="legacy_carried_forward"
        with self.assertRaisesRegex(ContractError,"not reviewed"): authorize(f)
        f=fixture(); f["roots"]["raw"]="D:/different/root"
        with self.assertRaisesRegex(ContractError,"raw root differs"): authorize(f)

    def test_evaluator_answer_cannot_be_an_actual_ancestor_with_resealed_policy(self):
        f=fixture(); raw=f["policy"]["artifacts"][0]; packet=f["policy"]["artifacts"][1]
        previous=raw["artifact_id"]; raw["dataset_id"]="qc"; raw["artifact_id"]=policy.artifact_id(raw)
        packet["parents"]=[raw["artifact_id"]]
        f["policy"]["products"][3]["dependency_review_status"]="reviewed_for_selected_frame"
        for grant in f["policy"]["uses"][0]["grants"]:
            if grant["artifact_id"]==previous: grant.update(artifact_id=raw["artifact_id"],role="reference")
        f["snapshot"]["sources"][0].update(dataset_id="qc",role="reference"); rebind(f)
        with self.assertRaisesRegex(ContractError,"evaluator"): authorize(f)

    def test_derived_input_requires_exact_all_parent_edges_not_only_packet_edges(self):
        f=fixture(); raw=f["policy"]["artifacts"][0]; packet=f["policy"]["artifacts"][1]
        derived=policy.artifact_record(dataset_id="reference",release_id="fixture",root_alias="snapshot",
            relative_path="mapping.json",sha256="7"*64,bytes=5,kind="derived",parents=[raw["artifact_id"]],
            availability=copy.deepcopy(raw["availability"]),temporal_classification="contemporary_only",
            source_url="https://example.org/map",provenance=dict(kind="generated",evidence=[dict(path="report.json",sha256="8"*64)],receipt=None),
            scope="Fictional mapping",scientific_validation="not_established")
        f["policy"]["artifacts"].append(derived)
        f["policy"]["products"][1]["dependency_review_status"]="reviewed_for_selected_frame"
        f["policy"]["uses"][0]["grants"].append(dict(artifact_id=derived["artifact_id"],role="reference"))
        packet["parents"]=[derived["artifact_id"]]
        f["snapshot"]["artifacts"][0]["input_refs"]=["mapping"]
        f["snapshot"]["sources"].append(dict(source_id="mapping",dataset_id="reference",release_id="fixture",
            path="mapping.json",sha256="7"*64,role="reference",availability=copy.deepcopy(raw["availability"]),
            temporal_classification="contemporary_only",source_url="https://example.org/map",parents=["raw-node"],
            computed_at="2026-11-01T00:00:00Z",method_id="fixture",method_version="1",receipt_path=None,receipt_sha256=None))
        rebind(f); authorize(f)  # A new computation from old eligible information is allowed.
        f["snapshot"]["sources"][1]["parents"]=[]; rebind(f)
        with self.assertRaisesRegex(ContractError,"parent edges differ"): authorize(f)

    def test_scientific_status_promotion_and_collected_metadata_edit_denied(self):
        f=fixture(); f["policy"]["artifacts"][0]["scientific_validation"]="validated"
        with self.assertRaisesRegex(ContractError,"scientific"): policy.validate_policy(f["policy"])
        f=fixture(); f["policy"]["products"][0]["metadata"]["collection_status"]="collected"
        with self.assertRaisesRegex(ContractError,"metadata/status changed"): policy.validate_policy(f["policy"])


class ReceiptReconciliationTests(unittest.TestCase):
    def fixture(self):
        record=dict(receipt_id="ReceiptA",dataset_id="raw",release_id="ReleaseA",url="https://example.org/Raw",relative_path="Raw.bin")
        receipt=dict(record,status="completed",bytes=3,sha256="a"*64,completed_at_utc="2026-10-01T00:00:00Z")
        return record,receipt

    def test_consistent_receipt_is_a_transport_check_not_status_promotion(self):
        row,receipt=self.fixture(); result=policy.reconcile_receipt(row,receipt,observed_size=3,observed_sha256="a"*64)
        self.assertEqual(result["status"],"transport_identity_consistent")
        self.assertEqual(result["scientific_validation"],"not_established")
        self.assertNotIn("collection_status",result)

    def test_legacy_windows_separators_match_without_casefold_or_traversal_repair(self):
        row,receipt=self.fixture()
        row["relative_path"]="raw/ReleaseA/Raw.bin"
        receipt["relative_path"]="raw\\ReleaseA\\Raw.bin"
        unchanged=copy.deepcopy(receipt)
        policy.reconcile_receipt(row,receipt,observed_size=3,observed_sha256="a"*64)
        self.assertEqual(receipt,unchanged)
        for path in ("RAW\\ReleaseA\\Raw.bin", "raw\\..\\Raw.bin", "raw\\ReleaseA\\NUL", "raw\\\\ReleaseA\\Raw.bin"):
            receipt["relative_path"]=path
            with self.subTest(path=path),self.assertRaises(ContractError):
                policy.reconcile_receipt(row,receipt,observed_size=3,observed_sha256="a"*64)

    def test_every_identity_and_case_only_mutation_is_rejected(self):
        for field in ("receipt_id","dataset_id","release_id","url","relative_path"):
            for form in ("missing","wrong","case"):
                row,receipt=self.fixture()
                if form=="missing": receipt.pop(field)
                elif form=="wrong": receipt[field]="wrong"
                else: receipt[field]=receipt[field].swapcase()
                with self.subTest(field=field,form=form),self.assertRaises(ContractError):
                    policy.reconcile_receipt(row,receipt,observed_size=3,observed_sha256="a"*64)

    def test_missing_queue_identity_size_hash_status_and_source_digest_rejected(self):
        for kind in ("queue","size","hash","status","expected","timestamp"):
            row,receipt=self.fixture()
            if kind=="queue": row.pop("receipt_id")
            elif kind=="size": receipt["bytes"]=True
            elif kind=="hash": receipt["sha256"]="b"*64
            elif kind=="status": receipt["status"]="Completed"
            elif kind=="expected": row["expected_sha256"]="b"*64
            else: receipt["completed_at_utc"]="2026-10-01"
            with self.subTest(kind=kind),self.assertRaises(ContractError):
                policy.reconcile_receipt(row,receipt,observed_size=3,observed_sha256="a"*64)


if __name__ == "__main__":
    unittest.main()
