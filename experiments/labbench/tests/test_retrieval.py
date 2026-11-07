import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, canonical, fingerprint
from experiments.labbench import retrieval as r


QUESTION = "Which fictional phosphorescent protein changes chlorophyll transport?"


def metadata(pmcid="PMC123", **overrides):
    return {"pmcid": pmcid, "title": "Fictional phosphorescent protein", "doi": "10.000/fiction", "isOpenAccess": "Y",
            "license": "cc by", "firstPublicationDate": "2020-01-01", **overrides}


def xml(pmcid="PMC123", *, license_url="https://creativecommons.org/licenses/by/4.0/", body="Phosphorescent protein changes chlorophyll transport."):
    return f'''<article xmlns:xlink="http://www.w3.org/1999/xlink"><front><article-meta><article-id pub-id-type="pmc">{pmcid}</article-id><permissions><license><ext-link xlink:href="{license_url}">License</ext-link></license></permissions><abstract><p>Fictional chlorophyll abstract.</p></abstract></article-meta></front><body><sec><p>{body}</p></sec></body></article>'''.encode()


def transport(url, **kwargs):
    body=canonical({"resultList":{"result":[metadata()]}}) if "/search?" in url else xml()
    return {"status":200,"body":body,"final_url":url,"headers":{"Content-Type":"application/json" if "/search?" in url else "application/xml"}}


def stalled_child(connection):
    time.sleep(30)
    connection.close()


def reseal_manifest(root, manifest):
    raw=canonical(manifest)+b"\n"; sha=r._digest(raw)
    (root/"manifest.json").write_bytes(raw)
    events=[json.loads(line) for line in (root/"journal.jsonl").read_bytes().splitlines()]
    events[-1]["details"]["manifest_sha256"]=sha
    events[-1].pop("sha256")
    events[-1]["sha256"]=fingerprint(events[-1])
    journal=b"".join(canonical(event)+b"\n" for event in events)
    (root/"journal.jsonl").write_bytes(journal)
    (root/"COMPLETE.json").write_bytes(canonical({"manifest_sha256":sha,"journal_sha256":r._digest(journal)})+b"\n")
    return sha


class RetrievalTests(unittest.TestCase):
    def test_question_only_fixed_queries_and_native_routes(self):
        queries=r.make_queries(QUESTION)
        self.assertEqual(len(queries),2)
        self.assertEqual(queries,r.make_queries(QUESTION))
        self.assertIn('OPEN_ACCESS:Y',queries[0])
        with self.assertRaises(ContractError):r.make_queries({"question":QUESTION,"ideal":"hidden"})
        for url in ("http://www.ebi.ac.uk/europepmc/webservices/rest/search", "https://localhost/search", "https://www.ebi.ac.uk@evil.invalid/search", "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC123/fullTextXML?token=secret"):
            with self.assertRaises(ContractError):r._safe_url(url)

    def test_full_retrieval_verification_passage_binding_and_capture(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            root=Path(temp)/"new"
            with patch.object(r,"fetch_http",side_effect=transport) as fetch:
                manifest=r.retrieve(QUESTION,root)
            self.assertEqual(fetch.call_count,3)
            self.assertEqual(len(manifest["sources"]),1)
            sha=r._digest((root/"manifest.json").read_bytes())
            self.assertEqual(r.verify_retrieval(root,sha,QUESTION),manifest)
            packet=r.select_passages(manifest,QUESTION)
            self.assertTrue(packet["sources"])
            self.assertEqual(set(packet["sources"][0]),{"source_id","sha256","text"})
            for source in packet["sources"]: self.assertEqual(source["sha256"],r._digest(source["text"].encode()))
            with self.assertRaises(TypeError):manifest["sources"][0]["spans"][0]["text"]="bad"
            with self.assertRaises(FileExistsError):r.retrieve(QUESTION,root)
            (root/manifest["sources"][0]["original"]["path"]).write_bytes(b"corrupt")
            with self.assertRaises(ContractError):r.verify_retrieval(root,sha,QUESTION)

    def test_wrong_article_identity_and_license_do_not_enter_sources(self):
        for payload in (xml("PMC999"), xml(license_url="https://creativecommons.org/licenses/by-nc/4.0/"),
                        xml().replace(b"<license>",b"<license><p>No derivatives allowed</p>"),
                        b'<!DOCTYPE x [<!ENTITY bad "x">]>'+xml(), xml().replace(b"<body>",b"<missing>").replace(b"</body>",b"</missing>")):
            with self.assertRaises(ContractError):r.parse_article(payload,metadata())

    def test_future_unknown_rights_and_duplicate_hits(self):
        records=[metadata(),metadata(),metadata("PMC456",license="cc by-nc"),metadata("PMC789",firstPublicationDate="2099-01-01")]
        def fetch(url,**kwargs):
            value=transport(url,**kwargs)
            if "/search?" in url:value["body"]=canonical({"resultList":{"result":records}})
            return value
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            with patch.object(r,"fetch_http",side_effect=fetch):manifest=r.retrieve(QUESTION,Path(temp)/"run")
            self.assertEqual(manifest["coverage"]["eligible_metadata_articles"],1)
            self.assertEqual(len(manifest["sources"]),1)
            reasons={x.get("reason") for x in manifest["failures"]}
            self.assertIn("unsupported_or_unknown_metadata_license",reasons)
            self.assertIn("future_or_invalid_publication_date",reasons)

    def test_malformed_http_timeout_and_partial_coverage_remain_explicit(self):
        responses=[TimeoutError("fictional"), {"status":503,"body":b"unavailable","final_url":"","headers":{}}]
        def fail(url,**kwargs):
            item=responses.pop(0)
            if isinstance(item,Exception):raise item
            item["final_url"]=url;return item
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            with patch.object(r,"fetch_http",side_effect=fail):manifest=r.retrieve(QUESTION,Path(temp)/"run")
            self.assertEqual(len(manifest["requests"]),2)
            self.assertEqual(len(manifest["sources"]),0)
            self.assertFalse(manifest["coverage"]["absence_of_evidence_claim"])
            self.assertEqual(manifest["costs"]["retries"],0)
            sha=r._digest((Path(temp)/"run/manifest.json").read_bytes())
            self.assertEqual(r.verify_retrieval(Path(temp)/"run",sha,QUESTION),manifest)

    def test_interruption_leaves_terminal_failure_and_no_auto_retry(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            root=Path(temp)/"run"
            with patch.object(r,"fetch_http",side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):r.retrieve(QUESTION,root)
            self.assertTrue((root/"FAILED.json").exists())
            self.assertIn('build_interrupted',(root/"journal.jsonl").read_text())
            self.assertFalse((root/"COMPLETE.json").exists())

    def test_chunk_utf8_bounds_and_explicit_exclusions(self):
        article=r.parse_article(xml(body=("chlorophyll αβγδ protein "*1000)),metadata())
        article["original"]={"sha256":"a"*64}
        manifest={"policy":r.DEFAULT_POLICY,"question_sha256":r._digest(QUESTION.encode()),"sources":[article]}
        packet=r.select_passages(manifest,QUESTION)
        self.assertEqual(len(packet["sources"]),8)
        self.assertLessEqual(packet["coverage"]["selected_text_bytes"],8000)
        self.assertGreater(packet["coverage"]["excluded_chunks"],0)
        spans={x["evidence_id"]:x for x in article["spans"]}
        for item,binding in zip(packet["sources"],packet["bindings"]):
            self.assertLessEqual(len(item["text"].encode()),1000)
            self.assertEqual(item["text"],spans[binding["span_id"]]["text"][binding["character_start"]:binding["character_end"]])

    def test_owned_process_deadline_bounds_unresponsive_child(self):
        started=time.monotonic()
        with self.assertRaises(TimeoutError):r._bounded_child(stalled_child,(),time.monotonic()+0.4)
        self.assertLess(time.monotonic()-started,3)

    def test_direct_transport_never_reads_a_byte_beyond_reservation(self):
        class FakeResponse:
            url=r.BASE+'PMC123/fullTextXML';status=200;headers={}
            consumed=0
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,count):
                self.consumed+=count
                return b'x'*count
        response=FakeResponse()
        class FakeOpener:
            def open(self,*args,**kwargs):return response
        with patch.object(r.urllib.request,'build_opener',return_value=FakeOpener()) as factory:
            with self.assertRaises(ContractError):r._fetch_http_direct(response.url,byte_limit=19,timeout_seconds=1,deadline=time.monotonic()+1)
        self.assertEqual(response.consumed,19)
        self.assertEqual(factory.call_args.args[0].proxies,{})

    def test_child_timeout_and_sanitized_network_causes_survive(self):
        for response in ({"ok":False,"error_type":"TimeoutError"},
                         {"ok":False,"error_type":"URLError","underlying_error_type":"TimeoutError"}):
            with patch.object(r,"_bounded_child",return_value=response):
                with self.assertRaises(TimeoutError):r.fetch_http(r.BASE+'PMC123/fullTextXML',byte_limit=10,timeout_seconds=1,deadline=time.monotonic()+1)
        with patch.object(r,"_bounded_child",return_value={"ok":False,"error_type":"URLError","underlying_error_type":"gaierror"}):
            with self.assertRaises(r.HttpTransportError) as raised:r.fetch_http(r.BASE+'PMC123/fullTextXML',byte_limit=10,timeout_seconds=1,deadline=time.monotonic()+1)
        self.assertEqual(raised.exception.cause_class,"gaierror")

    def test_resealed_accounting_source_omission_and_journal_contradictions_rejected(self):
        for mutate in (lambda m:m["costs"].update(downloaded_bytes=0),
                       lambda m:m.update(sources=[]),
                       lambda m:m["requests"][0].update(byte_reservation=1),
                       lambda m:m["coverage"].update(absence_of_evidence_claim=True)):
            with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
                root=Path(temp)/"run"
                with patch.object(r,"fetch_http",side_effect=transport):r.retrieve(QUESTION,root)
                manifest=json.loads((root/"manifest.json").read_bytes());mutate(manifest)
                sha=reseal_manifest(root,manifest)
                with self.assertRaises(ContractError):r.verify_retrieval(root,sha,QUESTION)

    def test_unknown_failed_transfer_reserves_bytes_and_write_failure_is_terminal(self):
        with tempfile.TemporaryDirectory(dir=Path.cwd()/"data/cache") as temp:
            root=Path(temp)/"timeout"
            with patch.object(r,"fetch_http",side_effect=TimeoutError):manifest=r.retrieve(QUESTION,root)
            self.assertEqual(manifest["costs"]["downloaded_bytes"],0)
            self.assertEqual(manifest["costs"]["safety_accounted_bytes"],2*r.DEFAULT_POLICY["metadata_bytes"])
            self.assertEqual(manifest["costs"]["unmeasured_transfer_upper_bytes"],2*r.DEFAULT_POLICY["metadata_bytes"])
            self.assertEqual(r.verify_retrieval(root,r._digest((root/"manifest.json").read_bytes()),QUESTION),manifest)
            real_publish=r.publish_bytes
            def fail_body(path,payload):
                if str(path).endswith('.body'):raise OSError('fictional disk failure')
                return real_publish(path,payload)
            with patch.object(r,"fetch_http",side_effect=transport),patch.object(r,"publish_bytes",side_effect=fail_body):
                with self.assertRaises(OSError):r.retrieve(QUESTION,Path(temp)/"write-failure")
            self.assertTrue((Path(temp)/"write-failure/FAILED.json").exists())
            self.assertFalse((Path(temp)/"write-failure/COMPLETE.json").exists())


if __name__ == "__main__":unittest.main()
