"""Example safety controls; no acquired datasets or model calls."""
import json
import hashlib
import io
import time
from email.message import Message
from urllib.response import addinfourl
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.examples import audit_il6r, prepare_il6r, fetch_il6r, qualify_ci
from tether_engine.journal import read_chain
from tether_engine.serde import ContractError

try:
    import pyarrow
except ImportError:
    pyarrow = None


class ExampleReadingTests(unittest.TestCase):
    def model(self):
        return dict(statement='<img src=x onerror="alert(1)"> & literal',
                    facts={'<script>':'<svg onload="alert(1)">'},
                    missingness={'tissue':'unknown <b>literal</b>'},
                    rows=[dict(source_id='row <unsafe>',row_group=0,row_in_group=1,
                        source_url='https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/25.09/source')])

    def test_source_text_remains_literal_and_document_denies_scripts(self):
        result=audit_il6r.render(self.model())
        self.assertNotIn('<img',result)
        self.assertNotIn('<script>',result)
        self.assertNotIn('<svg',result)
        self.assertIn('&lt;img',result)
        self.assertIn("default-src 'none'",result)
        self.assertIn('Clinical probability is withheld',result)

    def test_non_provider_and_script_urls_are_denied(self):
        for url in ('javascript:alert(1)','https://ftp.ebi.ac.uk.evil.invalid/file','file:///secret'):
            model=self.model(); model['rows'][0]['source_url']=url
            with self.subTest(url=url), self.assertRaisesRegex(ContractError,'unexpected source URL'):
                audit_il6r.render(model)

    def test_pinned_selection_stays_small_and_nonclinical(self):
        pinned=json.loads(Path(prepare_il6r.__file__).with_name('il6r_ot2509.json').read_bytes())
        self.assertEqual(len(pinned['sources']),3)
        self.assertEqual(sum(s['bytes'] for s in pinned['sources']),15010826)
        self.assertEqual([r['row_in_group'] for r in pinned['rows']],[4563,1017,25744])
        self.assertEqual(pinned['rows'][0]['values']['datatypeId'],'genetic_association')
        for source in pinned['sources']:
            self.assertFalse({'clinicalPhase','clinicalStatus','clinicalSignificances','studyStopReason'} & set(source['projected_columns']))


class ExampleRetrievalTests(unittest.TestCase):
    def response(self, data, url=None, status=200):
        class Response(io.BytesIO):
            def geturl(self):
                return url or fetch_il6r.PREFIX+'fixture'
        response=Response(data)
        response.status=status
        return response

    def test_explicit_network_choice_required_before_output(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(fetch_il6r, '_open_original') as open_url:
            output=Path(temp)/'new'
            with self.assertRaisesRegex(ContractError,'explicit'):
                fetch_il6r.fetch(output)
            with self.assertRaisesRegex(ValueError,'Supply existing'):
                qualify_ci.qualify(output)
            open_url.assert_not_called()
            self.assertFalse(output.exists())

    def test_exact_payload_accepted_without_real_network(self):
        data=b'fictional source'
        with patch.object(fetch_il6r, '_open_original', return_value=self.response(data)):
            result=fetch_il6r.fetch_one(fetch_il6r.PREFIX+'fixture',hashlib.sha256(data).hexdigest(),len(data),time.monotonic()+5)
        self.assertEqual(result,data)

    def test_oversize_hash_redirect_and_expired_requests_rejected(self):
        url=fetch_il6r.PREFIX+'fixture'
        digest=hashlib.sha256(b'abc').hexdigest()
        for response,reason in ((self.response(b'abcd'),'exceeds pinned size'),
                                (self.response(b'xyz'),'differs from pinned bytes'),
                                (self.response(b'abc',url='https://example.invalid'),'redirect')):
            with self.subTest(reason=reason), patch.object(fetch_il6r, '_open_original', return_value=response):
                with self.assertRaisesRegex(ContractError,reason):
                    fetch_il6r.fetch_one(url,digest,3,time.monotonic()+5)
        with patch.object(fetch_il6r, '_open_original') as open_url, self.assertRaises(TimeoutError):
            fetch_il6r.fetch_one(url,digest,3,time.monotonic()-1)
        open_url.assert_not_called()

    def test_redirect_is_rejected_before_requesting_its_destination(self):
        pinned = fetch_il6r.PREFIX + 'fixture'
        other = 'https://example.invalid/substitute'
        requested = []

        def transport(_handler, request):
            requested.append(request.full_url)
            headers = Message()
            if request.full_url == pinned:
                headers['Location'] = other
                status = 302
            else:
                status = 200
            response = addinfourl(io.BytesIO(b'abc'), headers, request.full_url, status)
            response.msg = 'fixture'
            return response

        with patch.object(fetch_il6r.urllib.request.HTTPSHandler, 'https_open', transport):
            with self.assertRaisesRegex(ContractError, 'redirect'):
                fetch_il6r.fetch_one(pinned, hashlib.sha256(b'abc').hexdigest(), 3, time.monotonic() + 5)
        self.assertEqual(requested, [pinned])

    def test_archived_witnesses_match_all_pins(self):
        root=Path(fetch_il6r.__file__).parent
        manifest=json.loads((root/'il6r_ot2509.json').read_bytes())
        for source in manifest['sources']:
            raw=(root/'receipts'/(source['receipt_sha256']+'.json')).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),source['receipt_sha256'])
            witness=json.loads(raw)
            self.assertEqual(witness['sha256'],source['sha256'])
            self.assertEqual(witness['url'],source['source_url'])


@unittest.skipUnless(pyarrow is not None, 'install the ingest extra for adapter tests')
class ExamplePreparationTests(unittest.TestCase):
    def test_changed_manifest_denied_before_original_access(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            (base/'il6r_ot2509.json').write_text('{"schema_version":1,"sources":[]}',encoding='utf-8')
            with patch.object(prepare_il6r,'HERE',base), patch.object(prepare_il6r,'read_file') as read:
                with self.assertRaisesRegex(ContractError,'Pinned example contract differs'):
                    prepare_il6r.build(base/'output',base/'raw',base/'catalog')
                read.assert_not_called()
                self.assertFalse((base/'output').exists())

    def test_failed_input_read_retains_build_journal(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            with patch.object(prepare_il6r,'read_file',side_effect=OSError('fixture unavailable')):
                with self.assertRaisesRegex(OSError,'fixture unavailable'):
                    prepare_il6r.build(base/'output',base/'raw',base/'catalog')
            events=read_chain(base/'output/journal.jsonl')
            self.assertEqual(events[0]['event'],'build_reserved')
            self.assertEqual(events[-1]['event'],'build_failed')
            self.assertFalse((base/'output/build-report.json').exists())
            with self.assertRaisesRegex(ContractError,'Refusing to reuse'):
                prepare_il6r.build(base/'output',base/'raw',base/'catalog')
