"""Independent policy counterexamples; no provider rows or model execution."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from fixture import build, ROOT, HERE
from tether import _catalog_policy as p
from asof.serde import ContractError, fingerprint
from asof.provenance import catalog_index


def main():
    fixture=build("policy-probes",with_mapping=True)
    checks=[]
    def check(name, condition):
        checks.append(dict(name=name,passed=bool(condition)))
        if not condition: raise AssertionError(name)
    def authorize(doc=None,snapshot=None,case=None,use_id="fictional-use"):
        return p.authorize_snapshot(doc or fixture["policy"], snapshot or fixture["snapshot"],
            case=case or fixture["case"],use_id=use_id,root_aliases=fixture["roots"])
    def denied(name, callback):
        try: callback()
        except ContractError as error:
            checks.append(dict(name=name,passed=True,error=str(error)))
        else: raise AssertionError(name+": accepted")
    def rebind(doc,snapshot):
        doc["uses"][0]["snapshot_fingerprint"]=fingerprint(snapshot)
    def replace_id(doc,record,**changes):
        old=record["artifact_id"];record.update(changes);new=p.artifact_id(record);record["artifact_id"]=new
        for item in doc["artifacts"]: item["parents"]=[new if x==old else x for x in item["parents"]]
        for use in doc["uses"]:
            for grant in use["grants"]:
                if grant["artifact_id"]==old:grant["artifact_id"]=new
    try:
        first=authorize()
        check("nested mapping computed after cutoff remains eligible",len(first["binding"]["inventory"])==3)
        check("deterministic projection and binding",first==authorize())
        check("schema1 reader accepts execution projection",bool(catalog_index(first["projection"])))
        denied("legacy reader rejects schema2",lambda:catalog_index(fixture["policy"]))
        check("nonselected products denied",all(x["roles"]==["evaluation_only"] for x in first["projection"]["datasets"] if x["dataset_id"]!="synthetic_fixture"))
        first["projection"]["datasets"][0]["roles"]=["evaluation_only"]
        check("mutated returned grant is not reused",authorize()["projection"]["datasets"][0]["roles"]==["agent_evidence"])
        denied("unknown use cannot pick permissive alternative",lambda:authorize(use_id="origin-alternative"))

        doc,snapshot=deepcopy(fixture["policy"]),deepcopy(fixture["snapshot"])
        snapshot["sources"][0]["path"]="different-file.json";rebind(doc,snapshot)
        denied("same product unregistered artifact denied",lambda:authorize(doc,snapshot))

        doc,snapshot=deepcopy(fixture["policy"]),deepcopy(fixture["snapshot"])
        extra=deepcopy(doc["artifacts"][0]);extra.update(dataset_id="genetics_qc_cases",relative_path="unused-qc.json");extra["artifact_id"]=p.artifact_id(extra)
        doc["artifacts"].append(extra)
        node=deepcopy(snapshot["sources"][0]);node.update(source_id="unused-qc",dataset_id="genetics_qc_cases",path="unused-qc.json")
        snapshot["sources"].append(node);rebind(doc,snapshot)
        denied("unused evaluator node is still checked",lambda:authorize(doc,snapshot))

        for dataset,role in (("genetics_qc_cases","reference"),("vbt_linkage","reference"),("dated_outcomes","agent_evidence")):
            doc,snapshot=deepcopy(fixture["policy"]),deepcopy(fixture["snapshot"])
            replace_id(doc,doc["artifacts"][0],dataset_id=dataset)
            doc["uses"][0]["grants"][0]["role"]=role
            snapshot["sources"][0].update(dataset_id=dataset,role=role);rebind(doc,snapshot)
            denied(dataset+": actual evaluator ancestry cannot become validation/reference",lambda:authorize(doc,snapshot))

        doc,snapshot=deepcopy(fixture["policy"]),deepcopy(fixture["snapshot"])
        replace_id(doc,doc["artifacts"][0],dataset_id="scorer_artifacts")
        next(x for x in doc["products"] if x["dataset_id"]=="scorer_artifacts")["dependency_review_status"]="reviewed_for_selected_frame"
        snapshot["sources"][0]["dataset_id"]="scorer_artifacts";rebind(doc,snapshot)
        denied("scorer inference ancestry contract remains unsupported",lambda:authorize(doc,snapshot))

        doc=deepcopy(fixture["policy"])
        next(x for x in doc["products"] if x["dataset_id"]=="synthetic_fixture")["dependency_review_status"]="legacy_carried_forward"
        denied("unreviewed selected frame requirements denied",lambda:authorize(doc))

        doc,snapshot=deepcopy(fixture["policy"]),deepcopy(fixture["snapshot"])
        snapshot["sources"][1]["parents"]=[];rebind(doc,snapshot)
        denied("omitted actual mapping parent denied",lambda:authorize(doc,snapshot))
        doc=deepcopy(fixture["policy"])
        doc["artifacts"][1]["parents"]=[doc["artifacts"][1]["artifact_id"]]
        denied("artifact ancestry cycle denied",lambda:p.validate_policy(doc))
        doc=deepcopy(fixture["policy"]);doc["uses"][0]["grants"]=doc["uses"][0]["grants"][1:]
        denied("omitted actual ancestor grant denied",lambda:p.validate_policy(doc))

        doc,snapshot=deepcopy(fixture["policy"]),deepcopy(fixture["snapshot"])
        for availability in (doc["artifacts"][0]["availability"],snapshot["sources"][0]["availability"]):availability["annotation_public_at"]="2025-01-01"
        rebind(doc,snapshot)
        denied("future annotation denied despite granted path/hash",lambda:authorize(doc,snapshot))
        doc,snapshot=deepcopy(fixture["policy"]),deepcopy(fixture["snapshot"])
        snapshot["sources"][0]["availability"]["annotation_public_at"]="2018-01-01";rebind(doc,snapshot)
        denied("snapshot cannot substitute permissive availability",lambda:authorize(doc,snapshot))
        doc=deepcopy(fixture["policy"]);doc["uses"][0]["kind"]="endpoint_evaluation"
        denied("endpoint use cannot authorize origin evidence",lambda:authorize(doc))
        doc=deepcopy(fixture["policy"]);doc["uses"][0]["origin_at"]="2025-01-01T23:59:59.999999+00:00"
        denied("different origin requires separately bound use",lambda:authorize(doc))
        doc=deepcopy(fixture["policy"]);doc["artifacts"][0]["provenance"].update(kind="manual_archive",receipt=None)
        denied("manual origin archive remains unqualified",lambda:p.validate_policy(doc))

        source_bytes=(fixture["root"]/"catalog.json").read_bytes()
        p.validate_source_catalog(fixture["policy"],source_bytes)
        check("source catalog exact anchor accepted",True)
        doc=deepcopy(fixture["policy"])
        product=next(x for x in doc["products"] if x["dataset_id"]=="vbt_linkage")
        product["metadata"]["roles"]=["reference"];product["agent_use_policy"]="requires_artifact_grant"
        reconstructed={**deepcopy(doc["catalog_metadata"]),"datasets":[deepcopy(x["metadata"]) for x in doc["products"]]}
        doc["source_catalog"]["document_fingerprint"]=fingerprint(reconstructed)
        p.validate_policy(doc)
        denied("structurally resealed legacy deny edit fails exact source anchor",lambda:p.validate_source_catalog(doc,source_bytes))
        doc=deepcopy(fixture["policy"]);doc["invented_permission"]=True
        denied("unknown policy field denied",lambda:p.validate_policy(doc))
        denied("duplicate JSON keys denied",lambda:p.strict_json(b'{"schema_version":2,"schema_version":1}'))

        receipt=json.loads((fixture["root"]/"raw/receipts/source.json").read_text())
        queue={k:receipt[k] for k in ("receipt_id","dataset_id","release_id","url","relative_path")}
        kwargs=dict(observed_size=receipt["bytes"],observed_sha256=receipt["sha256"])
        check("exact receipt accepted",p.reconcile_receipt(queue,receipt,**kwargs)["status"]=="transport_identity_consistent")
        for field in queue:
            changed=deepcopy(receipt);changed[field]=changed[field].upper()
            denied(field+": case-only identity change denied",lambda:p.reconcile_receipt(queue,changed,**kwargs))
        status="passed"
    except BaseException as error:
        status="failed";checks.append(dict(name="unexpected",passed=False,error_class=type(error).__name__,error=str(error)))
        raise
    finally:
        record=dict(schema_version=1,status=locals().get("status","failed"),fixture_root=str(fixture["root"]),
            checks=checks,recorded_at_utc=datetime.now(timezone.utc).isoformat(),
            code_sha256=hashlib.sha256((ROOT/'packages/tether/src/tether/_catalog_policy.py').read_bytes()).hexdigest())
        name="POLICY-PROBES-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")+".json"
        (HERE/name).write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps(dict(status=record['status'],checks=len(checks),report=str(HERE/name))))


if __name__=="__main__":main()
