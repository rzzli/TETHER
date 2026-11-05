"""Purpose-scoped SciFact policy using TETHER provenance and journal primitives.

This is a native task extension, not therapeutic schema-2 or scientific entailment
verification. Preparation is trusted code; physical containers and logical product
permissions remain distinct. Same-user malicious code is outside this boundary.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import math
from pathlib import Path
import platform
import re
import time
from types import SimpleNamespace

from asof.atomic import publish_bytes
from asof.contracts import Availability, Profile, Snapshot, SourceNode, TemporalClass
from asof.journal import RunJournal, read_chain
from asof.provenance import InputGraph, catalog_index
from asof.serde import ContractError, Frozen, canonical, decode, fingerprint, freeze, parse_json, safe_child
from asof.study.proofs import capture_file
from asof.study.stable_read import read_file, stable_files


def need(condition, message):
    if not condition:
        raise ContractError(message)


def _hash(raw):
    return hashlib.sha256(raw).hexdigest()


def _digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _read(path, bound=64*1024*1024):
    return read_file(Path(path), time.monotonic()+120, bound)


def _date(value):
    result=value if isinstance(value,datetime) else decode(datetime,value)
    need(result.tzinfo is not None,"Timezone required")
    return result


def _relative(path, root):
    path=Path(path).absolute(); root=Path(root).absolute()
    need(path.is_relative_to(root),"Path escapes explicit workspace")
    relative=path.relative_to(root).as_posix()
    need(safe_child(root,relative)==path.resolve(),"Unsafe path")
    return relative


def _normalization(archive, receipt, root, expected_archive_sha256, expected_receipt_sha256):
    archive=Path(archive).absolute(); receipt=Path(receipt).absolute()
    root=Path(root).absolute()
    with stable_files([archive,receipt],deadline=time.monotonic()+120):
        receipt_bytes=_read(receipt,1024*1024)
        need(_hash(receipt_bytes)==expected_receipt_sha256,"Original receipt checksum mismatch")
        original=parse_json(receipt_bytes)
        proof=capture_file(archive,"scifact-container")
        need(proof["sha256"]==expected_archive_sha256,"Original archive checksum mismatch")
        need(original.get("status")=="downloaded_not_parsed" and original.get("http_status")==200,
             "Unsuccessful original transport receipt")
        need(original.get("sha256")==proof["sha256"] and original.get("bytes")==proof["bytes"],
             "Original receipt identity mismatch")
        need(Path(original.get("path","")).resolve()==archive.resolve(),"Original receipt path mismatch")
        need(isinstance(original.get("url"),str) and original["url"].startswith("https://"),
             "Original HTTPS source required")
        observed=_date(original.get("finished_at_utc"))
        normalized={"schema_version":1,"status":"completed",
                    "dataset_id":"scifact_distribution_container","release_id":expected_archive_sha256,
                    "relative_path":_relative(archive,root),"sha256":proof["sha256"],"bytes":proof["bytes"],
                    "url":original["url"],"completed_at_utc":observed.isoformat(),
                    "original_transport_receipt_path":_relative(receipt,root),
                    "original_transport_receipt_sha256":expected_receipt_sha256,
                    "normalization_method":"scifact_transport_representation_v1",
                    "allowed_purpose":"preparation",
                    "note":"Canonical representation of a verified transport event; not a new download, parse or scientific validation."}
    return normalized


def _core_admission(normalized, normalized_path, root, cutoff):
    cutoff=_date(cutoff); public=_date(normalized["completed_at_utc"])
    raw=_read(normalized_path,1024*1024)
    need(parse_json(raw)==normalized,"Normalized receipt differs from original event")
    receipt_sha=_hash(raw)
    available=Availability(None,None,None,None,public.date(),"public_download_receipt",
                           "Only present-day public-download bound is known",public,receipt_sha)
    node=SourceNode("scifact-container",normalized["dataset_id"],normalized["release_id"],
                    normalized["relative_path"],normalized["sha256"],"reference",available,
                    TemporalClass.CONTEMPORARY,normalized["url"],
                    receipt_path=_relative(normalized_path,root),receipt_sha256=receipt_sha)
    snapshot=Snapshot(2,"scifact-preparation-container",Profile.CONTEMPORARY,cutoff.date(),False,(),
                      (node,),str(Path(root).absolute()),{},cutoff)
    catalog={"schema_version":1,"datasets":[{"dataset_id":node.dataset_id,"roles":["reference"],
                                            "native_allowed_purposes":["preparation"]}]}
    graph=InputGraph(snapshot,Path(root),catalog_index(catalog))
    reason=graph.exclusion((node.source_id,),SimpleNamespace(cutoff=cutoff))
    need(reason is None,"Container eligibility: "+str(reason))
    proofs=graph.verify((node.source_id,),{})
    return freeze({"snapshot":snapshot,"catalog":catalog,"source_proofs":proofs,
                   "normalized_receipt_sha256":receipt_sha})


def admit_container(archive, original_transport_receipt, normalized_receipt_output, *, workspace_root,
                    cutoff, expected_archive_sha256, expected_receipt_sha256):
    """Admit verified original bytes for preparation only, preserving transport bytes."""
    root=Path(workspace_root).absolute(); output=Path(normalized_receipt_output).absolute()
    need(output not in {Path(archive).absolute(),Path(original_transport_receipt).absolute()},
         "Receipt normalization cannot alias input")
    _relative(output,root)
    normalized=_normalization(archive,original_transport_receipt,root,
                              expected_archive_sha256,expected_receipt_sha256)
    # Reject a future input before creating a successful normalized proof.
    need(_date(normalized["completed_at_utc"])<=_date(cutoff),"Container eligibility: available_after_origin")
    publish_bytes(output,canonical(normalized)+b"\n")
    core=_core_admission(normalized,output,root,cutoff)
    return freeze({"schema_version":1,"kind":"scifact_container_admission","allowed_purpose":"preparation",
                   "archive_path":_relative(archive,root),"archive_sha256":expected_archive_sha256,
                   "original_receipt_path":_relative(original_transport_receipt,root),
                   "original_receipt_sha256":expected_receipt_sha256,
                   "normalized_receipt_path":_relative(output,root),"cutoff":_date(cutoff).isoformat(),
                   "core":core})


def reverify_container(admission, workspace_root):
    need(admission.get("schema_version")==1 and admission.get("allowed_purpose")=="preparation",
         "Container purpose cannot be promoted")
    root=Path(workspace_root).absolute()
    normalized=_normalization(safe_child(root,admission["archive_path"]),
                              safe_child(root,admission["original_receipt_path"]),root,
                              admission["archive_sha256"],admission["original_receipt_sha256"])
    core=_core_admission(normalized,safe_child(root,admission["normalized_receipt_path"]),root,admission["cutoff"])
    need(fingerprint(core)==fingerprint(admission["core"]),"Container graph proof mismatch")
    return freeze({"status":"verified","allowed_purpose":"preparation","core":core})


def authorize_products(manifest, product_ids, purpose):
    """Follow logical data parents; preparation membership is an explicit control edge."""
    need(purpose in {"fit","tune","calibrate","predict","evaluate"},"Unknown native consumer purpose")
    need(isinstance(product_ids,(tuple,list)) and product_ids and len(set(product_ids))==len(product_ids),
         "Explicit unique logical products required")
    products=manifest["products"];active=set();visited=set()
    def visit(key):
        need(key in products,"Missing logical product parent")
        need(key not in active,"Logical product cycle")
        if key in visited:return
        active.add(key); product=products[key]
        need(purpose in product["purposes"],"Product purpose denied: "+key)
        need(not (product["kind"]=="evaluation_reference" and purpose in {"fit","predict"}),
             "Held-out reference cannot be fitting or prediction ancestor")
        for parent in product["logical_parents"]:
            if parent in products:visit(parent)
            elif parent=="split:membership":
                need(key.startswith(("queries_","references_")),"Invalid split control dependency")
            elif parent.startswith("member:"):
                if key=="corpus":expected="member:data/corpus.jsonl:doc_id,title,abstract"
                elif key.startswith("queries_"):
                    split="dev" if key=="queries_dev" else "train"
                    expected=f"member:data/claims_{split}.jsonl:id,claim"
                elif key.startswith("references_"):
                    split="dev" if key=="references_dev" else "train"
                    expected=f"member:data/claims_{split}.jsonl:id,claim,evidence,cited_doc_ids"
                else:raise ContractError("Unapproved member/field authority")
                need(parent==expected,"Unapproved member fields")
            else:raise ContractError("Unknown logical dependency")
        active.remove(key);visited.add(key)
    for product in product_ids:visit(product)
    return tuple(sorted(visited))


@dataclass(frozen=True)
class NativeContext(Frozen):
    preparation_root: Path
    preparation_manifest_sha256: str
    model_root: Path
    model_manifest_sha256: str
    model_manifest_relative: str
    workspace_root: Path
    cutoff: str
    manifest: Mapping
    model: Mapping
    corpus: Mapping
    queries: Mapping
    document_hashes: Mapping
    sentence_hashes: Mapping
    container_admission: Mapping
    policy_sha256: str


def _validate_model(model, model_root, manifest, fit_queries,preparation_manifest_sha256=None):
    required={"schema_version","kind","computed_at","fit_product_ids","index_input_product_ids",
              "fit_claim_ids","configuration","files","producer_code","dependency_versions",
              "input_product_proofs","preparation_manifest_sha256","fit_execution"}
    need(isinstance(model,Mapping) and required<=set(model)<=required|{"model_id","training_metadata"},"Model proof fields differ")
    need(model["schema_version"]==1 and model["kind"]=="scifact_model","Unsupported native model proof")
    _date(model["computed_at"])
    fit_products=tuple(model["fit_product_ids"])
    need({"corpus","queries_fit","fit_pairs"}<=set(fit_products)<={"corpus","queries_fit","fit_pairs","references_fit"},
         "Model fitting inputs differ from authorized products")
    authorize_products(manifest,fit_products,"fit")
    need(tuple(model["index_input_product_ids"])==("corpus",),"Retrieval index can fit only public corpus")
    authorize_products(manifest,model["index_input_product_ids"],"fit")
    need(_digest(model["preparation_manifest_sha256"]) and (preparation_manifest_sha256 is None or
         model["preparation_manifest_sha256"]==preparation_manifest_sha256),"Model preparation parent anchor differs")
    input_proofs=model["input_product_proofs"]
    need(isinstance(input_proofs,Mapping) and set(input_proofs)==set(fit_products)|set(model["index_input_product_ids"]),
         "Model input product proof inventory differs")
    for key,proof in input_proofs.items():
        need(isinstance(proof,Mapping) and set(proof)=={"sha256","bytes"},"Model input product proof fields differ")
        product=manifest["products"][key]
        need(proof["sha256"]==product["sha256"] and type(proof["bytes"]) is int and proof["bytes"]==product["bytes"],
             "Model input product proof parent bytes differ")
    ids=model["fit_claim_ids"]
    need(isinstance(ids,(list,tuple)) and all(type(x) is int for x in ids) and len(set(ids))==len(ids),"Invalid fitting claim IDs")
    need(set(ids)=={row["id"] for row in fit_queries},"Fitting membership differs from sealed split")
    files=model["files"]
    need(isinstance(files,(tuple,list)) and files,"Native model files required")
    names=[]
    for proof in files:
        need(isinstance(proof,Mapping) and {"path","sha256","bytes"}<=set(proof)<={"path","sha256","bytes","logical_id"},"Model file proof fields differ")
        path=safe_child(model_root,proof["path"]);names.append(proof["path"].casefold())
        need(path.suffix in {".json",".npz",".npy"},"Only explicit numeric/JSON model assets are permitted")
        actual=capture_file(path,"model-asset")
        need(actual["sha256"]==proof["sha256"] and actual["bytes"]==proof["bytes"],"Model asset checksum mismatch")
    need(len(names)==len(set(names)),"Duplicate model assets")
    fit=model["fit_execution"]
    need(isinstance(fit,Mapping) and set(fit)=={"path","receipt_sha256","cell_id"} and fit["cell_id"]=="fit",
         "Fit execution proof fields differ")
    fit_path=Path(fit["path"]).absolute()
    verify_session(fit_path,expected_receipt_sha256=fit["receipt_sha256"])
    events=read_chain(fit_path/"journal.jsonl")
    need(_date(model["computed_at"])>=_date(events[0]["details"]["created_at_utc"]),"Model computation predates its retained fitting attempt")
    dispatches=[e["details"] for e in events if e["event"]=="native_dispatch" and e["details"]["cell_id"]==fit["cell_id"]]
    terminals=[e["details"] for e in events if e["event"]=="native_terminal" and e["details"]["cell_id"]==fit["cell_id"]]
    need(len(dispatches)==len(terminals)==1 and terminals[0]["status"]=="completed","Successful unique fitting execution required")
    consumed=dispatches[0]["request"].get("inputs")
    need(isinstance(consumed,Mapping) and set(consumed)==set(input_proofs),"Fitting consumed input inventory differs")
    for key,proof in input_proofs.items():
        need(isinstance(consumed[key],Mapping) and {"path","sha256","bytes"}<=set(consumed[key]),"Fitting consumed input descriptor incomplete")
        need(consumed[key]["sha256"]==proof["sha256"] and consumed[key]["bytes"]==proof["bytes"],"Fitting consumed parent bytes differ")
    fit_record=parse_json(_read(safe_child(fit_path,terminals[0]["path"]),4*1024*1024))
    produced=fit_record["result"].get("files")
    native_files=[{k:proof[k] for k in ("path","sha256","bytes")} for proof in files]
    need(isinstance(produced,(tuple,list)) and fingerprint(produced)==fingerprint(native_files),"Model files differ from retained fitting result")
    code=model["producer_code"]
    need(isinstance(code,Mapping) and {"path","sha256"}<=set(code)<={"path","sha256","bytes"},"Producer code proof differs")
    actual=capture_file(Path(code["path"]),"native-producer")
    need(actual["sha256"]==code["sha256"] and ("bytes" not in code or actual["bytes"]==code["bytes"]),"Producer code changed")
    versions=model["dependency_versions"]
    need(isinstance(versions,Mapping) and versions.get("python")==platform.python_version(),"Python runtime differs")
    for package,expected in versions.items():
        if package!="python":
            try: actual_version=metadata.version(package)
            except metadata.PackageNotFoundError as error:raise ContractError("Missing model dependency: "+package) from error
            need(actual_version==expected,"Model dependency version differs: "+package)


def build_context(preparation_root,preparation_manifest_sha256,model_root,model_manifest_sha256,cutoff,
                  proof_directory=None,*,model_manifest_relative="model-manifest.json",workspace_root=None,
                  container_admission=None):
    """Source-inclusive preparation/model validation once, immutable views per operation."""
    from .data_views import verify_preparation, load_product
    preparation_root=Path(preparation_root).absolute();model_root=Path(model_root).absolute()
    manifest=verify_preparation(preparation_root,preparation_manifest_sha256)
    root=Path(workspace_root).absolute() if workspace_root is not None else Path.cwd().absolute()
    archive=manifest["archive"]
    if container_admission is None:
        need(proof_directory is not None,"Fresh normalized proof destination required")
        container_admission=admit_container(archive["path"],archive["receipt_path"],Path(proof_directory)/"normalized-container-receipt.json",
                                           workspace_root=root,cutoff=cutoff,expected_archive_sha256=archive["sha256"],
                                           expected_receipt_sha256=archive["receipt_sha256"])
    else:
        need(container_admission["archive_sha256"]==archive["sha256"] and container_admission["cutoff"]==_date(cutoff).isoformat(),"Container proof differs from native frame")
        reverify_container(container_admission,root)
    authorize_products(manifest,["corpus","queries_dev"],"predict")
    corpus_rows=load_product(preparation_root,manifest,"corpus","predict")
    query_rows=load_product(preparation_root,manifest,"queries_dev","predict")
    corpus={row["doc_id"]:row for row in corpus_rows};queries={row["id"]:row for row in query_rows}
    need(len(corpus)==len(corpus_rows) and len(queries)==len(query_rows),"Duplicate native identities")
    fit_queries=load_product(preparation_root,manifest,"queries_fit","fit")
    model_raw=_read(safe_child(model_root,model_manifest_relative))
    need(_hash(model_raw)==model_manifest_sha256,"Model manifest anchor mismatch")
    model=parse_json(model_raw);_validate_model(model,model_root,manifest,fit_queries,preparation_manifest_sha256)
    doc_hashes={key:fingerprint(value) for key,value in corpus.items()}
    sentence_hashes={(key,i):_hash(sentence.encode("utf-8")) for key,row in corpus.items() for i,sentence in enumerate(row["abstract"])}
    scope={"schema_version":1,"policy":"scifact_native_purpose_policy_v1","preparation_manifest_sha256":preparation_manifest_sha256,
           "model_manifest_sha256":model_manifest_sha256,"cutoff":_date(cutoff).isoformat(),
           "container_admission_sha256":fingerprint(container_admission),"adapter_code_sha256":capture_file(Path(__file__),"native-policy")["sha256"]}
    return NativeContext(preparation_root,preparation_manifest_sha256,model_root,model_manifest_sha256,model_manifest_relative,
                         root,_date(cutoff).isoformat(),manifest,model,corpus,queries,doc_hashes,sentence_hashes,container_admission,fingerprint(scope))


def reverify_context(context):
    fresh=build_context(context.preparation_root,context.preparation_manifest_sha256,context.model_root,
                        context.model_manifest_sha256,context.cutoff,model_manifest_relative=context.model_manifest_relative,
                        workspace_root=context.workspace_root,container_admission=context.container_admission)
    need(fresh.policy_sha256==context.policy_sha256 and fresh.document_hashes==context.document_hashes,
         "Native context changed during operation")
    return fresh


def make_request(context,claim_id,configuration):
    need(type(claim_id) is int and claim_id in context.queries,"Unscheduled native claim")
    return freeze({"schema_version":1,"benchmark_id":"scifact","release_sha256":context.manifest["archive"]["sha256"],
                   "claim_id":claim_id,"claim_sha256":fingerprint(context.queries[claim_id]),
                   "corpus_sha256":context.manifest["products"]["corpus"]["sha256"],"model_sha256":context.model_manifest_sha256,
                   "configuration_sha256":fingerprint(configuration)})


def verify_candidate(context,request,prediction,envelope,*,configuration=None):
    """Check source/request bindings; scientific support and correctness remain unjudged."""
    from .native_contract import validate_prediction
    config=context.model["configuration"] if configuration is None else configuration
    need(fingerprint(config)==fingerprint(context.model["configuration"]),"Configuration is not the frozen model configuration")
    expected=make_request(context,request.get("claim_id"),config)
    need(fingerprint(request)==fingerprint(expected),"Native request/model/configuration binding mismatch")
    prediction=validate_prediction(prediction,context.corpus,expected_claim_id=request["claim_id"])
    required={"request_sha256","prediction_sha256","retrieved","source_bindings","producer_code_sha256","resources"}
    need(isinstance(envelope,Mapping) and set(envelope)==required,"Native envelope fields differ")
    need(envelope["request_sha256"]==fingerprint(request) and envelope["prediction_sha256"]==fingerprint(prediction),"Native response request/prediction fingerprint mismatch")
    need(envelope["producer_code_sha256"]==context.model["producer_code"]["sha256"],"Native producer identity mismatch")
    validate_resources(envelope["resources"])
    retrieved=envelope["retrieved"]
    need(isinstance(retrieved,(tuple,list)),"Retrieved source list required")
    ids=[]
    for rank,item in enumerate(retrieved,1):
        need(isinstance(item,Mapping) and set(item)=={"doc_id","rank","score","document_sha256"},"Retrieved source fields differ")
        doc=item["doc_id"];score=item["score"]
        need(type(doc) is int and doc in context.corpus and type(item["rank"]) is int and item["rank"]==rank,"Invalid retrieval identity/rank")
        need(type(score) in (int,float) and math.isfinite(score),"Invalid retrieval score")
        need(item["document_sha256"]==context.document_hashes[doc],"Retrieved document checksum mismatch")
        ids.append(doc)
    need(len(ids)==len(set(ids)),"Duplicate retrieved document")
    bindings=envelope["source_bindings"]
    need(isinstance(bindings,(tuple,list)),"Source sentence bindings required")
    actual={}
    for item in bindings:
        need(isinstance(item,Mapping) and set(item)=={"doc_id","sentence_id","text_sha256"},"Sentence binding fields differ")
        key=(item["doc_id"],item["sentence_id"])
        need(all(type(x) is int for x in key) and key not in actual and key in context.sentence_hashes,"Invalid or duplicate sentence locator")
        need(item["text_sha256"]==context.sentence_hashes[key],"Source sentence checksum mismatch")
        actual[key]=item["text_sha256"]
    needed={(int(doc),sentence) for doc,value in prediction["evidence"].items() for sentence in value["sentences"]}
    need(set(actual)==needed,"Selected source sentence coverage differs")
    need({int(doc) for doc in prediction["evidence"]}<=set(ids),"Native prediction references unretrieved source")
    return freeze({"kind":"accepted_candidate","policy_sha256":context.policy_sha256,"request":request,
                   "prediction":prediction,"envelope":envelope,"scientific_validation":"not_performed"})


RESOURCE_KEYS={"wall_seconds","cpu_seconds","peak_memory_bytes","memory_method","input_bytes",
               "output_bytes","examples","model_input_tokens","model_output_tokens","tokenizer_identity",
               "provider_usage","token_usage_reason","provider_cost_usd"}


def validate_resources(resources):
    need(isinstance(resources,Mapping) and set(resources)==RESOURCE_KEYS,"Native resource fields differ")
    for name in ("wall_seconds","cpu_seconds"):
        value=resources[name]
        need(value is None or (type(value) in (int,float) and math.isfinite(value) and value>=0),
             "Invalid native time: "+name)
    for name in ("peak_memory_bytes","input_bytes","output_bytes","examples"):
        value=resources[name]
        need(value is None or (type(value) is int and value>=0),"Invalid native count: "+name)
    need(isinstance(resources["memory_method"],str) and resources["memory_method"],"Memory method required")
    need(all(resources[name] is None for name in ("model_input_tokens","model_output_tokens","tokenizer_identity","provider_usage")),
         "Non-LLM execution cannot fabricate token/provider usage")
    need(resources["token_usage_reason"]=="not_applicable_non_llm" and
         type(resources["provider_cost_usd"]) in (int,float) and resources["provider_cost_usd"]==0,
         "Native task must retain zero provider charges and inapplicable tokens")
    return freeze(resources)


def _unknown_resources():
    return dict(wall_seconds=None,cpu_seconds=None,peak_memory_bytes=None,memory_method="unavailable_after_failure",
                input_bytes=None,output_bytes=None,examples=None,model_input_tokens=None,model_output_tokens=None,
                tokenizer_identity=None,provider_usage=None,token_usage_reason="not_applicable_non_llm",provider_cost_usd=0)


def _totals(records):
    keys=("wall_seconds","cpu_seconds","input_bytes","output_bytes","examples")
    return {**{key:sum(record["resources"][key] or 0 for record in records) for key in keys},
            "unknown_measurements":{key:sum(record["resources"][key] is None for record in records) for key in keys},
            "provider_cost_usd":0,"model_input_tokens":None,"model_output_tokens":None}


def _validate_schedule(schedule):
    need(isinstance(schedule,(list,tuple)) and schedule and all(isinstance(x,str) and x.strip() for x in schedule),
         "Explicit nonempty cell schedule required")
    need(len(set(schedule))==len(schedule),"Duplicate scheduled cell")
    return tuple(schedule)


class NativeSession:
    """Exclusive one-attempt cells with boundary budget checks, not kernel limits.

    Byte budget counts reported producer response bytes; journal/artifact overhead
    is separate. The supervising runner enforces time and monitors memory.
    """
    def __init__(self,output,schedule,configuration,*,max_calls=None,max_wall_seconds=14400,max_output_bytes=64*1024*1024):
        schedule=_validate_schedule(schedule)
        need(type(max_calls) is int and max_calls>0 if max_calls is not None else True,"Invalid call budget")
        need(type(max_wall_seconds) in (int,float) and math.isfinite(max_wall_seconds) and max_wall_seconds>0,"Invalid time budget")
        need(type(max_output_bytes) is int and max_output_bytes>0,"Invalid byte budget")
        self.schedule=tuple(schedule);self.configuration=freeze(configuration);self.output=Path(output).absolute()
        self.max_calls=max_calls or len(schedule);self.max_wall_seconds=max_wall_seconds;self.max_output_bytes=max_output_bytes
        self.started=time.perf_counter();self.active=None;self.attempted=set();self.records={};self.stopped=False;self.closed=False
        self.journal=RunJournal(self.output)
        self.journal.append("native_configured",schedule=self.schedule,configuration=self.configuration,
                            budgets={"max_calls":self.max_calls,"max_wall_seconds":max_wall_seconds,"max_output_bytes":max_output_bytes})

    def __enter__(self):return self

    def __exit__(self,kind,error,tb):
        if error is not None:
            self.stopped=True
            try:self.journal.append("native_interrupted" if isinstance(error,KeyboardInterrupt) else "native_failed",
                                    error_type=type(error).__name__,message=str(error),active_cell=self.active)
            finally:self.close()
        else:self.close()
        return False

    def begin(self,cell_id,request):
        need(not self.closed and not self.stopped and self.active is None,"Native session cannot dispatch later work")
        need(cell_id in self.schedule and cell_id not in self.attempted,"Unscheduled or duplicate dispatch")
        elapsed=time.perf_counter()-self.started
        if len(self.attempted)>=self.max_calls or elapsed>=self.max_wall_seconds:
            self.stopped=True
            self.journal.append("native_budget_denied",cell_id=cell_id,session_elapsed_seconds=elapsed)
            raise ContractError("Native execution budget exhausted")
        self.journal.append("native_dispatch",cell_id=cell_id,request=freeze(request),request_sha256=fingerprint(request))
        self.attempted.add(cell_id);self.active=cell_id
        return cell_id

    def finish(self,cell_id,result,resources,*,status="completed"):
        need(not self.closed and not self.stopped and self.active==cell_id and cell_id not in self.records,"No matching native attempt")
        need(status in {"completed","accepted","rejected","failed","timeout","interrupted"},"Unknown native terminal state")
        measured=None
        try:
            measured=validate_resources(resources)
            if status in {"completed","accepted","rejected"}:
                need(all(measured[k] is not None for k in ("wall_seconds","cpu_seconds","input_bytes","output_bytes","examples")),"Successful native operation requires measured time/counts")
            elapsed=time.perf_counter()-self.started
            prior=sum(r["resources"]["output_bytes"] or 0 for r in self.records.values())
            breach=elapsed>self.max_wall_seconds or prior+(measured["output_bytes"] or 0)>self.max_output_bytes
            if breach:status="budget_exceeded";self.stopped=True
            record=freeze({"schema_version":1,"cell_id":cell_id,"status":status,"result":result,
                           "resources":measured,"session_elapsed_seconds":elapsed})
            payload=canonical(record)+b"\n"
            need(len(payload)<=4*1024*1024,"Native cell artifact exceeds limit")
            relative="cells/"+_hash(cell_id.encode())+".json"
            publish_bytes(self.output/relative,payload)
            self.journal.append("native_terminal",cell_id=cell_id,status=status,path=relative,
                                record_sha256=_hash(payload),record_fingerprint=fingerprint(record),resources=measured)
            self.records[cell_id]=record;self.active=None
            if status in {"failed","timeout","interrupted"}:self.stopped=True
            return record
        except BaseException as error:
            self.stopped=True
            self.journal.append("native_commit_failed",cell_id=cell_id,error_type=type(error).__name__,message=str(error),resources=measured)
            raise

    def fail(self,cell_id,error,resources=None):
        return self.finish(cell_id,{"error_type":type(error).__name__,"message":str(error)},
                           resources or _unknown_resources(),
                           status="interrupted" if isinstance(error,KeyboardInterrupt) else "timeout" if isinstance(error,TimeoutError) else "failed")

    def mark_not_run(self,cell_id,reason):
        """Account unattempted scheduled cells after an observed terminal stop."""
        need(not self.closed and self.stopped and self.active is None,"No completed stop permits unexecuted accounting")
        need(cell_id in self.schedule and cell_id not in self.attempted and cell_id not in self.records,"Cell was attempted or already accounted")
        need(isinstance(reason,str) and reason.strip(),"Unexecuted reason required")
        resources=_unknown_resources()
        resources.update(wall_seconds=0,cpu_seconds=0,input_bytes=0,output_bytes=0,examples=0,memory_method="not_executed")
        record=freeze({"schema_version":1,"cell_id":cell_id,"status":"not_run","result":{"reason":reason},
                       "resources":resources,"session_elapsed_seconds":time.perf_counter()-self.started})
        payload=canonical(record)+b"\n";relative="cells/"+_hash(cell_id.encode())+".json"
        publish_bytes(self.output/relative,payload)
        self.journal.append("native_unexecuted",cell_id=cell_id,path=relative,record_sha256=_hash(payload),
                            record_fingerprint=fingerprint(record),resources=resources,reason=reason)
        self.records[cell_id]=record
        return record

    def finalize(self):
        need(not self.closed and self.active is None and set(self.records)==set(self.schedule),"Native schedule is incomplete")
        need(not (self.output/"receipt.json").exists(),"Native run already finalized")
        totals=_totals(list(self.records.values()))
        self.journal.append("native_finalized",terminal_cells=len(self.records),totals=totals)
        outputs={p.relative_to(self.output).as_posix():capture_file(p,"native-output")["sha256"]
                 for p in sorted(self.output.rglob("*.json"))}
        outputs["journal.jsonl"]=capture_file(self.output/"journal.jsonl","native-journal")["sha256"]
        receipt={"schema_version":1,"kind":"scifact_native_session","schedule":self.schedule,
                 "configuration":self.configuration,"terminal_cells":len(self.records),"totals":totals,"outputs":outputs}
        payload=canonical(receipt)+b"\n";publish_bytes(self.output/"receipt.json",payload)
        self.stopped=True
        return freeze({"sha256":_hash(payload),"receipt":receipt})

    def close(self):
        if not self.closed:self.journal.close();self.closed=True


def inspect_session(output):
    events=read_chain(Path(output)/"journal.jsonl",allow_incomplete_tail=True)
    attempts=[e["details"]["cell_id"] for e in events if e["event"]=="native_dispatch"]
    terminal=[e["details"]["cell_id"] for e in events if e["event"] in {"native_terminal","native_unexecuted"}]
    failed_usage=[e["details"] for e in events if e["event"]=="native_commit_failed" and e["details"].get("resources") is not None]
    return {"last_event":events[-1]["event"],"attempted_cells":attempts,"terminal_cells":len(terminal),
            "uncommitted_measured_resources":failed_usage,
            "unresolved_cells":[x for x in attempts if x not in terminal],
            "recovery_action":"inspect only; never automatically retry"}


def verify_session(output,*,expected_receipt_sha256,context=None):
    if context is not None:
        context=reverify_context(context)
    output=Path(output).absolute();raw=_read(output/"receipt.json")
    need(_hash(raw)==expected_receipt_sha256,"Native receipt anchor mismatch")
    receipt=parse_json(raw)
    need(receipt.get("schema_version")==1 and receipt.get("kind")=="scifact_native_session","Wrong native receipt")
    actual={p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file() and p.name!="receipt.json"}
    need(actual==set(receipt["outputs"]),"Native output inventory differs")
    for relative,digest in receipt["outputs"].items():
        need(capture_file(safe_child(output,relative),"native-output")["sha256"]==digest,"Native output checksum mismatch")
    events=read_chain(output/"journal.jsonl")
    need(events[0]["event"]=="run_reserved" and events[1]["event"]=="native_configured","Native journal header differs")
    configured=events[1]["details"]
    budgets=configured["budgets"]
    need(set(budgets)=={"max_calls","max_wall_seconds","max_output_bytes"} and type(budgets["max_calls"]) is int and budgets["max_calls"]>0
         and type(budgets["max_output_bytes"]) is int and budgets["max_output_bytes"]>0
         and type(budgets["max_wall_seconds"]) in (int,float) and math.isfinite(budgets["max_wall_seconds"]) and budgets["max_wall_seconds"]>0,"Invalid native budgets")
    schedule=_validate_schedule(configured["schedule"])
    need(schedule==_validate_schedule(receipt["schedule"]),"Native schedule mismatch")
    need(fingerprint(configured["configuration"])==fingerprint(receipt["configuration"]),"Native configuration mismatch")
    attempts={};records={};active=None;stopped=False;last_elapsed=0;producer_bytes=0
    for event in events[2:]:
        detail=event["details"];kind=event["event"]
        if kind=="native_dispatch":
            cell=detail["cell_id"]
            need(not stopped and active is None and cell in schedule and cell not in attempts,"Invalid native dispatch sequence")
            need(fingerprint(detail["request"])==detail["request_sha256"],"Native request fingerprint mismatch")
            attempts[cell]=detail;active=cell
            need(len(attempts)<=budgets["max_calls"],"Native call budget exceeded")
        elif kind=="native_budget_denied":
            elapsed=detail["session_elapsed_seconds"]
            need(active is None and not stopped and detail["cell_id"] in schedule and detail["cell_id"] not in attempts,"Invalid budget denial sequence")
            need(type(elapsed) in (int,float) and math.isfinite(elapsed) and elapsed>=last_elapsed,"Invalid budget-denial time")
            need(len(attempts)>=budgets["max_calls"] or elapsed>=budgets["max_wall_seconds"],"Native budget denial without exhausted budget")
            stopped=True;last_elapsed=elapsed
        elif kind in {"native_terminal","native_unexecuted"}:
            cell=detail["cell_id"]
            need(cell not in records and cell in schedule,"Unscheduled or duplicate native terminal")
            if kind=="native_terminal":need(active==cell,"Native terminal has no unique attempt")
            else:need(stopped and active is None and cell not in attempts,"Unexecuted cell was dispatched or not stopped")
            rawrecord=_read(safe_child(output,detail["path"]),4*1024*1024);record=parse_json(rawrecord)
            need(_hash(rawrecord)==detail["record_sha256"] and fingerprint(record)==detail["record_fingerprint"],"Journal/record fingerprint mismatch")
            need(record["cell_id"]==cell and record["status"]==detail.get("status","not_run") and
                 fingerprint(record["resources"])==fingerprint(detail["resources"]),"Journal/cell resource or identity mismatch")
            validate_resources(record["resources"])
            elapsed=record["session_elapsed_seconds"]
            need(type(elapsed) in (int,float) and math.isfinite(elapsed) and elapsed>=last_elapsed,"Native elapsed timeline invalid")
            last_elapsed=elapsed
            if kind=="native_terminal":
                need(record["status"] in {"completed","accepted","rejected","failed","timeout","interrupted","budget_exceeded"},"Unknown native terminal status")
                if record["status"] in {"completed","accepted","rejected"}:
                    need(all(record["resources"][k] is not None for k in ("wall_seconds","cpu_seconds","input_bytes","output_bytes","examples")),"Successful native accounting is incomplete")
                producer_bytes+=record["resources"]["output_bytes"] or 0
                breach=elapsed>budgets["max_wall_seconds"] or producer_bytes>budgets["max_output_bytes"]
                need(breach==(record["status"]=="budget_exceeded"),"Native budget breach/status disagreement")
            if record["status"] in {"accepted","rejected"}:
                need(context is not None,"Source-inclusive candidate context required")
                value=record["result"]
                need(fingerprint(value["request"])==attempts[cell]["request_sha256"],"Candidate differs from dispatched request")
                if record["status"]=="accepted":
                    verified=verify_candidate(context,value["request"],value["prediction"],value["envelope"])
                    need(fingerprint(verified)==fingerprint(value),"Accepted native candidate differs on replay")
                else:
                    need(value.get("kind")=="rejected_candidate" and value.get("error_type")=="ContractError","Unrecognized policy rejection")
                    try:verify_candidate(context,value["request"],value["prediction"],value["envelope"])
                    except ContractError as error:need(str(error)==value.get("message"),"Policy rejection reason differs")
                    else:raise ContractError("Rejected native candidate passes the declared policy")
            if kind=="native_unexecuted":
                need(record["result"]=={"reason":detail["reason"]} and all(record["resources"][k]==0 for k in ("wall_seconds","cpu_seconds","input_bytes","output_bytes","examples")),"Unexecuted resource/meaning mismatch")
            records[cell]=record;active=None
            if record["status"] in {"failed","timeout","interrupted","budget_exceeded"}:stopped=True
        elif kind=="native_finalized":
            need(event is events[-1],"Final native event must be last")
            need(active is None and set(records)==set(schedule),"Native finalization omits scheduled cells")
            need(detail["terminal_cells"]==len(records) and fingerprint(detail["totals"])==fingerprint(_totals(list(records.values()))),"Journal native accounting mismatch")
        else:raise ContractError("Unexpected event in finalized native session: "+kind)
    need(events[-1]["event"]=="native_finalized" and receipt["terminal_cells"]==len(records),"Missing native finalization")
    totals=_totals(list(records.values()))
    need(fingerprint(totals)==fingerprint(receipt["totals"]),"Receipt native accounting mismatch")
    need(len(attempts)<=configured["budgets"]["max_calls"],"Native call count exceeds budget")
    return freeze({"status":"verified","terminal_cells":len(records),"totals":totals,
                   "scientific_validation":"not_performed"})
