"""Shared fictional SciFact inputs; importing these never collects test cases."""
from datetime import datetime, timezone
import hashlib
import io
import platform
from pathlib import Path
import tarfile
import tempfile
from unittest.mock import patch

from tether_engine.serde import canonical, fingerprint
from experiments.scifact.data_views import digest, jsonl_bytes
from experiments.scifact.tether_adapter import admit_container, NativeSession, build_context, make_request

NOW = datetime(2026, 1, 2, tzinfo=timezone.utc)

def resources(**updates):
    result=dict(wall_seconds=.1,cpu_seconds=.05,peak_memory_bytes=10000,
                memory_method="fictional_measurement",input_bytes=10,output_bytes=20,examples=1,
                model_input_tokens=None,model_output_tokens=None,tokenizer_identity=None,
                provider_usage=None,token_usage_reason="not_applicable_non_llm",provider_cost_usd=0)
    result.update(updates)
    return result


class ContainerFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "original.tar.gz"
        self.archive.write_bytes(b"fictional original container")
        self.receipt = self.root / "transport.json"
        self.transport = {"status": "downloaded_not_parsed", "url": "https://example.test/data.tar.gz",
                          "path": str(self.archive), "bytes": self.archive.stat().st_size,
                          "sha256": hashlib.sha256(self.archive.read_bytes()).hexdigest(),
                          "finished_at_utc": NOW.isoformat(), "http_status": 200}
        self.receipt.write_bytes(canonical(self.transport))
        self.original = self.receipt.read_bytes()

    def tearDown(self):
        self.temp.cleanup()

    def admit(self, **kw):
        return admit_container(self.archive, self.receipt, self.root / "normalized.json",
                               workspace_root=self.root, cutoff=kw.pop("cutoff", NOW),
                               expected_archive_sha256=self.transport["sha256"],
                               expected_receipt_sha256=hashlib.sha256(self.original).hexdigest(), **kw)


class CandidateFixture(ContainerFixture):
    def setUp(self):
        ContainerFixture.setUp(self)
        self.prep=self.root/"prep";self.prep.mkdir();self.modelroot=self.root/"model";self.modelroot.mkdir()
        products={}
        def product(key,rows,kind,purposes,parents):
            raw=b"".join(canonical(row)+b"\n" for row in rows)
            relative=key+".jsonl";(self.prep/relative).write_bytes(raw)
            products[key]={"path":relative,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw),
                           "format":"jsonl","kind":kind,"purposes":purposes,"rows":len(rows),
                           "fields":list(rows[0]),"logical_parents":parents}
        product("corpus",[{"doc_id":10,"title":"Fictional","abstract":["First sentence.","Second sentence."]}],
                "public_corpus",["fit","predict"],["member:data/corpus.jsonl:doc_id,title,abstract"])
        product("queries_fit",[{"id":1,"claim":"Fitting question"}],"query_only",["fit"],["member:data/claims_train.jsonl:id,claim","split:membership"])
        product("queries_dev",[{"id":2,"claim":"Evaluation question"}],"query_only",["predict"],["member:data/claims_dev.jsonl:id,claim","split:membership"])
        product("references_fit",[{"id":1,"claim":"Fitting question","evidence":{},"cited_doc_ids":[10]}],
                "fit_supervision",["fit"],["member:data/claims_train.jsonl:id,claim,evidence,cited_doc_ids","split:membership"])
        product("fit_pairs",[{"claim_id":1,"doc_id":10,"label":"NEI"}],"fit_supervision",["fit"],["references_fit"])
        product("references_dev",[{"id":2,"claim":"Evaluation question","evidence":{},"cited_doc_ids":[10]}],
                "evaluation_reference",["evaluate"],["member:data/claims_dev.jsonl:id,claim,evidence,cited_doc_ids","split:membership"])
        self.manifest={"archive":{"path":str(self.archive),"receipt_path":str(self.receipt),
                                  "sha256":self.transport["sha256"],"receipt_sha256":hashlib.sha256(self.original).hexdigest()},"products":products}
        self.asset=self.modelroot/"numeric.json";self.asset.write_bytes(b'{"weights":[0.1]}')
        self.producer=self.root/"producer.py";self.producer.write_bytes(b'# fictional producer, never executed\n')
        self.model={"schema_version":1,"kind":"scifact_model","computed_at":"2027-01-01T00:00:00+00:00",
                    "fit_product_ids":["corpus","queries_fit","fit_pairs"],"index_input_product_ids":["corpus"],
                    "fit_claim_ids":[1],"configuration":{"k":1,"threshold":.5},
                    "files":[{"path":"numeric.json","sha256":hashlib.sha256(self.asset.read_bytes()).hexdigest(),"bytes":self.asset.stat().st_size}],
                    "producer_code":{"path":str(self.producer),"sha256":hashlib.sha256(self.producer.read_bytes()).hexdigest()},
                    "dependency_versions":{"python":platform.python_version()}}
        self.model["preparation_manifest_sha256"]="a"*64
        self.model["input_product_proofs"]={key:{name:products[key][name] for name in ("sha256","bytes")} for key in self.model["fit_product_ids"]}
        consumed={key:{"path":str(self.prep/products[key]["path"]),**proof} for key,proof in self.model["input_product_proofs"].items()}
        with NativeSession(self.root/"fit-execution",["fit"],{}) as session:
            session.begin("fit",{"inputs":consumed})
            session.finish("fit",{"files":self.model["files"]},resources())
            fitreceipt=session.finalize()
        self.model["fit_execution"]={"path":str(self.root/"fit-execution"),"receipt_sha256":fitreceipt["sha256"],"cell_id":"fit"}
        self.model["computed_at"]=datetime.now(timezone.utc).isoformat()
        self.patch=patch("experiments.scifact.data_views.verify_preparation",return_value=self.manifest)
        self.patch.start();self.addCleanup(self.patch.stop)
        self.context=self.build()

    def build(self):
        (self.prep/"manifest.json").write_bytes(canonical(self.manifest)+b"\n")
        self.modelpath=self.modelroot/"model-manifest.json";self.modelpath.write_bytes(canonical(self.model)+b"\n")
        dest=self.root/("proof-"+str(len(list(self.root.glob("proof-*")))))
        return build_context(self.prep,"a"*64,self.modelroot,hashlib.sha256(self.modelpath.read_bytes()).hexdigest(),NOW,dest,workspace_root=self.root)

    def candidate(self,label="SUPPORT"):
        request=make_request(self.context,2,self.model["configuration"])
        prediction={"id":2,"evidence":{"10":{"label":label,"sentences":[0]}}}
        envelope={"request_sha256":fingerprint(request),"prediction_sha256":fingerprint(prediction),
                  "retrieved":[{"doc_id":10,"rank":1,"score":.5,"document_sha256":self.context.document_hashes[10]}],
                  "source_bindings":[{"doc_id":10,"sentence_id":0,"text_sha256":self.context.sentence_hashes[(10,0)]}],
                  "producer_code_sha256":self.model["producer_code"]["sha256"],"resources":resources()}
        return request,prediction,envelope


def fictional():
    corpus = {
        2: {"doc_id": 2, "title": "Example alpha", "abstract": ["The active signal was observed.", "A neutral methods sentence.", "A neutral limitation sentence."]},
        10: {"doc_id": 10, "title": "Example beta", "abstract": ["The active signal was observed.", "A neutral methods sentence.", "A neutral limitation sentence."]},
    }
    queries, pairs = [], []
    for i, label in enumerate(("SUPPORT", "CONTRADICT", "NEI")):
        for j in range(12):
            cid = i * 12 + j + 1
            queries.append({"id": cid, "claim": f"{label.lower()}cue signal relationship querytoken"})
            pairs.append({"claim_id": cid, "doc_id": 2 if j % 2 else 10, "label": label,
                          "rationale_sentences": [] if label == "NEI" else [0]})
    return corpus, queries, pairs


def fixture_rows():
    corpus = [{"doc_id": i, "title": f"Document {i}", "abstract": [f"Sentence {i} a", f"Sentence {i} b"], "structured": False}
              for i in range(1, 43)]
    train = [{"id": i, "claim": f"Claim {i}", "evidence": {str(i): [{"label": "SUPPORT" if i % 2 else "CONTRADICT", "sentences": [0]}]}, "cited_doc_ids": [i]}
             for i in range(1, 31)]
    dev = [{"id": 100, "claim": "Development statement", "evidence": {}, "cited_doc_ids": [40]}]
    test = [{"id": 200, "claim": "Unlabelled test statement"}]
    return corpus, train, dev, test

def write_tar(path, rows=None, extras=(), replacements=None):
    rows = rows or fixture_rows()
    names = ["data/corpus.jsonl", "data/claims_train.jsonl", "data/claims_dev.jsonl", "data/claims_test.jsonl"]
    contents = {name: jsonl_bytes(value) for name, value in zip(names, rows)}
    contents.update(replacements or {})
    with tarfile.open(path, "w:gz") as archive:
        for name, raw in contents.items():
            member = tarfile.TarInfo(name); member.size = len(raw)
            archive.addfile(member, io.BytesIO(raw))
        for member, raw in extras:
            archive.addfile(member, io.BytesIO(raw) if raw is not None else None)
    return path

def acquisition(root, archive):
    raw = archive.read_bytes()
    receipt = archive.with_suffix(".receipt.json")
    data = {"status": "downloaded_not_parsed", "sha256": digest(raw), "bytes": len(raw), "path": str(archive.resolve()),
            "url": "https://example.invalid/public.tar.gz", "finished_at_utc": "2026-01-02T00:00:00+00:00"}
    receipt.write_bytes(canonical(data)+b"\n")
    record = root / "acquisition.json"
    # Acquisition lookup deliberately uses the official basename, so use that name in fixtures.
    record.write_bytes(canonical({"originals": [{"file": str(archive.resolve()), "bytes": len(raw), "sha256": digest(raw),
                     "receipt_file": str(receipt.resolve()), "receipt_sha256": digest(receipt.read_bytes()), "source_url": data["url"]}]}))
    return record

