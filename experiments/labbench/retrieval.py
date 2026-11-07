"""Question-only, bounded Europe PMC acquisition and reproducible passage views.

No answer key, choices, benchmark source hint or reference manifest is accepted.
The retrieval manifest is supervisor evidence; workers receive selected text only.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
import hashlib
import multiprocessing
from pathlib import Path
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal, read_chain
from tether_engine.serde import ContractError, canonical, freeze, parse_json, safe_child

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest/"
DEFAULT_POLICY = freeze({"schema_version": 1, "query_algorithm": "longest_unique_question_tokens_v1",
    "cutoff_date": "2026-11-06", "max_queries": 2, "hits_per_query": 10, "max_articles": 3,
    "metadata_bytes": 1024 * 1024, "article_bytes": 2 * 1024 * 1024,
    "total_bytes": 8 * 1024 * 1024, "request_seconds": 20.0, "question_seconds": 120.0,
    "retries": 0, "licenses": ["cc by", "cc0"], "max_passages": 8,
    "passage_bytes": 1000, "selected_bytes": 8000})
STOP = frozenset("a an and are as at be been being by can could did do does for from had has have how in into is it its may more most not of on or other reported shown than that the their these they this those to under using was were what when where which while who why will with would according study studies paper authors following respectively found result results demonstrate demonstrated identify identified research researchers shown show whether".split())


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _digest(payload):
    return hashlib.sha256(payload).hexdigest()


def _read(path, cap):
    path = Path(path)
    _need(path.is_file() and not path.is_symlink(), "Missing or symlinked retrieval proof")
    with path.open("rb") as stream:
        payload = stream.read(cap + 1)
    _need(len(payload) <= cap, "Retrieval proof exceeds byte bound")
    return payload


def validate_policy(policy):
    _need(isinstance(policy, Mapping) and set(policy) == set(DEFAULT_POLICY), "Unknown retrieval policy fields")
    for name in ("schema_version", "query_algorithm", "max_queries", "hits_per_query", "max_articles", "retries", "licenses"):
        _need(canonical(policy[name]) == canonical(DEFAULT_POLICY[name]), "Unsupported retrieval method setting")
    try:
        date.fromisoformat(policy["cutoff_date"])
    except (ValueError, TypeError) as exc:
        raise ContractError("Invalid acquisition cutoff") from exc
    for name in ("metadata_bytes", "article_bytes", "total_bytes", "max_passages", "passage_bytes", "selected_bytes"):
        _need(type(policy[name]) is int and 0 < policy[name] <= DEFAULT_POLICY[name], "Invalid retrieval byte/count bound")
    for name in ("request_seconds", "question_seconds"):
        _need(type(policy[name]) in (int, float) and 0 < policy[name] <= DEFAULT_POLICY[name], "Invalid retrieval time bound")
    return freeze(policy)


def question_tokens(question):
    _need(isinstance(question, str) and question.strip() and len(question.encode("utf-8")) <= 64000,
          "Invalid question-only retrieval input")
    tokens = []
    for value in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", question):
        word = value.casefold().strip("-")
        if word not in STOP and word not in tokens:
            tokens.append(word)
    return tuple(tokens)


def make_queries(question, policy=DEFAULT_POLICY):
    policy = validate_policy(policy)
    tokens = question_tokens(question)
    ranked = sorted(enumerate(tokens), key=lambda item: (-len(item[1]), item[0]))
    selected = [word for _, word in ranked[:8]]
    if not selected:
        return ()
    terms = [" AND ".join('"' + word + '"' for word in selected[:3]),
             " OR ".join('"' + word + '"' for word in selected)]
    suffix = ' AND OPEN_ACCESS:Y AND (LICENSE:"cc by" OR LICENSE:"cc0") AND FIRST_PDATE:[0001-01-01 TO ' + policy["cutoff_date"] + "]"
    queries = []
    for term in terms:
        query = "(" + term + ")" + suffix
        if query not in queries:
            queries.append(query)
    return tuple(queries)


def _safe_url(url):
    parts = urllib.parse.urlsplit(url)
    _need(parts.scheme == "https" and parts.netloc == "www.ebi.ac.uk" and not parts.username
          and not parts.password and not parts.fragment, "Unapproved retrieval origin")
    _need(parts.path == "/europepmc/webservices/rest/search" or
          re.fullmatch(r"/europepmc/webservices/rest/PMC[0-9]+/fullTextXML", parts.path), "Unapproved retrieval route")
    if not parts.path.endswith("/search"):
        _need(not parts.query, "Unexpected fulltext URL query")
    return url


class _RedirectGuard(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        _safe_url(new_url)
        return super().redirect_request(request, file_pointer, code, message, headers, new_url)


class HttpTransportError(ContractError):
    def __init__(self, cause_class):
        self.cause_class = cause_class if isinstance(cause_class,str) and cause_class.isidentifier() and len(cause_class)<=64 else "UnknownError"
        super().__init__("HTTP child failed: " + self.cause_class)


def _fetch_http_direct(url, *, byte_limit, timeout_seconds, deadline):
    """Child-only GET. A parent process supplies the absolute wall-clock bound."""
    _safe_url(url)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _RedirectGuard())
    request = urllib.request.Request(url, headers={"User-Agent": "TETHER-LitQA2-public-research/1.0", "Accept-Encoding": "identity"})
    try:
        response = opener.open(request, timeout=timeout_seconds)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        _safe_url(response.url)
        chunks, size = [], 0
        while True:
            _need(time.monotonic() < deadline, "Retrieval deadline exceeded")
            _need(size < byte_limit, "HTTP body reached reserved cap without EOF")
            chunk = response.read(min(65536, byte_limit - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            _need(size <= byte_limit, "HTTP body exceeds bound")
        _need(time.monotonic() < deadline, "Retrieval deadline exceeded")
        return {"status": response.status, "body": b"".join(chunks), "final_url": response.url,
                "headers": {name: response.headers.get(name) for name in ("Content-Type", "Content-Length", "ETag", "Last-Modified")}}


def _http_child(connection, url, byte_limit, timeout_seconds, deadline):
    try:
        result = _fetch_http_direct(url, byte_limit=byte_limit, timeout_seconds=timeout_seconds, deadline=deadline)
        connection.send({"ok": True, "result": result})
    except BaseException as exc:
        underlying = getattr(exc,"reason",None)
        connection.send({"ok": False, "error_type": type(exc).__name__,
                         "underlying_error_type": type(underlying).__name__ if isinstance(underlying,BaseException) else None})
    finally:
        connection.close()


def _bounded_child(target, arguments, deadline):
    """Bound DNS/connect/read and IPC stalls; terminate only this owned child."""
    _need(time.monotonic() < deadline, "HTTP deadline exhausted before dispatch")
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    result = []
    def receive():
        try:
            result.append(receiver.recv())
        except (EOFError, OSError):
            pass
    process = context.Process(target=target, args=(sender, *arguments), daemon=True)
    reader = threading.Thread(target=receive, daemon=True)
    started = False
    try:
        process.start()
        started = True
        sender.close()
        reader.start()
        process.join(max(0.0, deadline-time.monotonic()))
        if process.is_alive():
            raise TimeoutError("HTTP process absolute deadline exceeded")
        reader.join(max(0.0, deadline-time.monotonic()))
        _need(not reader.is_alive() and len(result) == 1 and process.exitcode == 0, "HTTP child ended without a complete result")
        _need(time.monotonic() < deadline, "HTTP deadline exceeded after completion")
        return result[0]
    finally:
        if started and process.is_alive():
            process.terminate()
            process.join(2.0)
            if process.is_alive():
                process.kill()
                process.join(2.0)
        sender.close()
        receiver.close()
        if reader.is_alive():
            reader.join(0.2)
        if started and not process.is_alive():
            process.close()


def fetch_http(url, *, byte_limit, timeout_seconds, deadline):
    """One owned process and one GET, with no automatic retry or proxy inheritance."""
    _safe_url(url)
    deadline = min(deadline, time.monotonic()+timeout_seconds)
    result = _bounded_child(_http_child, (url, byte_limit, timeout_seconds, deadline), deadline)
    if not result.get("ok"):
        if "TimeoutError" in (result.get("error_type"),result.get("underlying_error_type")):
            raise TimeoutError("HTTP child socket timeout")
        raise HttpTransportError(result.get("underlying_error_type") or result.get("error_type"))
    return result["result"]


def _candidate(record, policy):
    if not isinstance(record, dict):
        return None, "invalid_metadata_record"
    pmcid, license_name = record.get("pmcid"), record.get("license")
    if not isinstance(pmcid, str) or not re.fullmatch(r"PMC[0-9]+", pmcid):
        return None, "missing_or_invalid_pmcid"
    if record.get("isOpenAccess") != "Y" or license_name not in policy["licenses"]:
        return None, "unsupported_or_unknown_metadata_license"
    publication = record.get("firstPublicationDate")
    if publication is not None:
        try:
            _need(date.fromisoformat(publication) <= date.fromisoformat(policy["cutoff_date"]), "future publication")
        except (ValueError, TypeError, ContractError):
            return None, "future_or_invalid_publication_date"
    return {"pmcid": pmcid, "title": record.get("title"), "doi": record.get("doi"),
            "firstPublicationDate": publication, "license": license_name}, None


def _xml_license(root, metadata_license):
    records, permitted = [], set()
    for element in root.findall(".//license"):
        text = " ".join(" ".join(element.itertext()).split())
        links = [value for node in element.iter() for key, value in node.attrib.items() if key.endswith("href")]
        records.append({"text": text, "links": links})
        all_text = (text + " " + " ".join(links)).casefold()
        if any(value in all_text for value in ("noncommercial", "non-commercial", "no derivatives", "noderivatives", "sharealike", "share-alike", "/by-nc", "/by-nd", "/by-sa")):
            raise ContractError("Restricted XML license")
        if any(re.search(r"creativecommons\.org/licenses/by/[0-9.]+/?$", link.casefold()) for link in links) or "creative commons attribution license" in all_text or "creative commons attribution (cc by) license" in all_text:
            permitted.add("cc by")
        if any("creativecommons.org/publicdomain/zero/" in link.casefold() for link in links) or "creative commons cc0" in all_text:
            permitted.add("cc0")
    _need(metadata_license in permitted and len(permitted) == 1, "Missing or ambiguous XML reuse license")
    return records


def parse_article(payload, candidate):
    _need(len(payload) <= DEFAULT_POLICY["article_bytes"], "XML exceeds bound")
    _need(b"<!ENTITY" not in payload.upper(), "XML entity declaration forbidden")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise ContractError("Malformed article XML") from exc
    pmc_ids = ["".join(node.itertext()).strip() for node in root.findall(".//article-id") if node.get("pub-id-type") in ("pmc", "pmcid")]
    _need(any(value.removeprefix("PMC") == candidate["pmcid"].removeprefix("PMC") for value in pmc_ids), "XML article identity mismatch")
    license_records = _xml_license(root, candidate["license"])
    spans = []
    counts = {}
    for section, xpath in (("abstract", ".//abstract//p"), ("body", ".//body//p")):
        nodes = root.findall(xpath)
        counts[section + "_paragraphs"] = len(nodes)
        _need(len(nodes) <= 10000, "XML paragraph-count bound exceeded")
        for index, node in enumerate(nodes):
            text = " ".join(" ".join(node.itertext()).split())
            if not text:
                continue
            spans.append({"evidence_id": f"{candidate['pmcid']}:{section}:p{index:04d}", "source_id": candidate["pmcid"],
                          "text": text, "text_sha256": _digest(text.encode("utf-8")),
                          "locator": {"xml_path": xpath, "paragraph_index": index}})
    _need(root.find(".//body") is not None, "Article body unavailable")
    _need(spans, "No extractable article paragraphs")
    return {"source_id": candidate["pmcid"], "title": candidate["title"], "doi": candidate["doi"],
            "publication_date": candidate["firstPublicationDate"], "publication_date_unknown": candidate["firstPublicationDate"] is None,
            "metadata_license": candidate["license"], "xml_license": license_records,
            "spans": spans, "extraction": {"method": "ElementTree_abstract_and_body_paragraphs_itertext_whitespace_v1",
                **counts, "table_cells_without_paragraph_markup_included": False, "figure_images_included": False,
                "supplement_files_included": False, "original_fulltext_retained": True}}


def retrieve(question, output, *, policy=DEFAULT_POLICY):
    """Acquire sources for one question; a reserved directory is never resumed."""
    policy = validate_policy(policy)
    queries = make_queries(question, policy)
    journal = RunJournal(Path(output), kind="build")
    root, started = journal.output, time.monotonic()
    deadline = started + policy["question_seconds"]
    requests, sources, failures, candidates, seen = [], [], [], [], set()
    total_bytes, accounted_bytes = 0, 0

    def request(url, kind, cap):
        nonlocal total_bytes, accounted_bytes
        _need(time.monotonic() < deadline, "Question retrieval time exhausted")
        remaining = policy["total_bytes"] - accounted_bytes
        if remaining <= 0:
            failures.append({"stage": kind, "reason": "byte_budget_before_dispatch"})
            return None, None
        reservation = min(cap, remaining)
        request_id = f"{len(requests):03d}"
        entry = {"request_id": request_id, "url": _safe_url(url), "kind": kind, "status": "started", "byte_reservation": reservation}
        requests.append(entry)
        journal.append("retrieval_request_started", **entry)
        recording_started = False
        try:
            response = fetch_http(url, byte_limit=reservation, timeout_seconds=min(policy["request_seconds"], deadline-time.monotonic()), deadline=deadline)
            body = response["body"]
            _need(isinstance(body, bytes) and len(body) <= reservation, "HTTP body exceeds configured bound")
            _safe_url(response["final_url"])
            total_bytes += len(body)
            accounted_bytes += len(body)
            entry.update({"accounted_bytes": len(body), "byte_accounting_basis": "retained_response_body"})
            body_path = f"requests/{request_id}.body"
            receipt_path = f"requests/{request_id}.receipt.json"
            recording_started = True
            publish_bytes(safe_child(root, body_path), body)
            receipt = {"status": "completed", "dataset_id": "labbench_retrieved_literature", "release_id": _digest(body),
                       "relative_path": body_path, "sha256": _digest(body), "bytes": len(body),
                       "url": url, "source_url": url, "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                       "http_status": response["status"], "headers": response["headers"], "final_url": response["final_url"]}
            receipt_bytes = canonical(receipt) + b"\n"
            publish_bytes(safe_child(root, receipt_path), receipt_bytes)
            entry.update({"status": "completed", "body_path": body_path, "body_sha256": _digest(body), "bytes": len(body),
                          "http_status": response["status"], "receipt_path": receipt_path, "receipt_sha256": _digest(receipt_bytes)})
            journal.append("retrieval_request_completed", **entry)
            _need(200 <= response["status"] < 300, "HTTP non-success response")
            _need(time.monotonic() < deadline, "Question retrieval deadline exceeded after response")
            return request_id, body
        except (OSError, TimeoutError, ContractError, ValueError) as exc:
            if recording_started and isinstance(exc, OSError):
                raise
            if entry["status"] == "started":
                entry["status"] = "failed"
            if "accounted_bytes" not in entry:
                accounted_bytes += reservation
                entry.update({"accounted_bytes": reservation, "byte_accounting_basis": "conservative_unmeasured_reservation"})
            entry["error_type"] = type(exc).__name__
            entry["failure_cause"] = getattr(exc,"cause_class",type(exc).__name__)
            journal.append("retrieval_request_failed", **entry)
            failures.append({"request_id": request_id, "stage": kind, "error_type": type(exc).__name__, "failure_cause":entry["failure_cause"]})
            return None, None

    try:
        for query in queries:
            if time.monotonic() >= deadline:
                failures.append({"stage": "search", "reason": "question_deadline_before_dispatch"})
                break
            url = BASE + "search?" + urllib.parse.urlencode({"query": query, "format": "json", "pageSize": policy["hits_per_query"], "resultType": "core"})
            request_id, payload = request(url, "search", policy["metadata_bytes"])
            if payload is None:
                continue
            try:
                value = parse_json(payload)
                records = value["resultList"]["result"]
                _need(isinstance(records, list) and len(records) <= policy["hits_per_query"], "Invalid search-result cardinality")
                for rank, record in enumerate(records):
                    candidate, reason = _candidate(record, policy)
                    if candidate is None:
                        failures.append({"stage": "metadata", "request_id": request_id, "rank": rank, "reason": reason})
                    elif candidate["pmcid"] not in seen:
                        seen.add(candidate["pmcid"])
                        candidates.append({"candidate": candidate, "request_id": request_id, "rank": rank})
            except (KeyError, TypeError, ContractError) as exc:
                failures.append({"stage": "metadata_parse", "request_id": request_id, "error_type": type(exc).__name__})
        for item in candidates[:policy["max_articles"]]:
            if time.monotonic() >= deadline:
                failures.append({"stage": "fulltext", "reason": "question_deadline_before_dispatch"})
                break
            candidate = item["candidate"]
            request_id, payload = request(BASE + candidate["pmcid"] + "/fullTextXML", "fulltext", policy["article_bytes"])
            if payload is None:
                continue
            try:
                article = parse_article(payload, candidate)
                record = next(x for x in requests if x["request_id"] == request_id)
                article.update({"original": {"path": record["body_path"], "sha256": record["body_sha256"], "bytes": record["bytes"], "receipt_path": record["receipt_path"]},
                                "discovery_request_id": item["request_id"], "discovery_rank": item["rank"]})
                sources.append(article)
            except ContractError as exc:
                failures.append({"stage": "fulltext_parse", "request_id": request_id, "error_type": type(exc).__name__})
        manifest = {"schema_version": 1, "kind": "labbench_retrieval", "question_sha256": _digest(question.encode("utf-8")),
                    "policy": policy, "queries": queries, "requests": requests, "sources": sources, "failures": failures,
                    "coverage": {"eligible_metadata_articles": len(candidates), "attempted_fulltext_articles": sum(x["kind"] == "fulltext" for x in requests),
                                 "retained_articles": len(sources), "article_limit_exclusions": max(0, len(candidates)-policy["max_articles"]),
                                 "absence_of_evidence_claim": False, "source_access": "bounded_selected_subset"},
                    "costs": {"wall_seconds": time.monotonic()-started, "downloaded_bytes": total_bytes,
                              "downloaded_bytes_basis": "retained_complete_response_bodies_only", "safety_accounted_bytes": accounted_bytes,
                              "unmeasured_transfer_upper_bytes": accounted_bytes-total_bytes,
                              "wire_bytes_including_headers_and_tls": None, "provider_usd": 0.0, "retries": 0},
                    "retriever_sha256": _digest(_read(Path(__file__), 1024*1024))}
        payload = canonical(manifest) + b"\n"
        publish_bytes(root / "manifest.json", payload)
        journal.append("build_completed", manifest_sha256=_digest(payload), sources=len(sources))
        publish_bytes(root / "COMPLETE.json", canonical({"manifest_sha256": _digest(payload), "journal_sha256": _digest(_read(journal.path, 1024*1024))}) + b"\n")
        return freeze(manifest)
    except BaseException as exc:
        journal.fail(exc, "retrieval")
        publish_bytes(root / "FAILED.json", canonical({"error_type": type(exc).__name__, "request_count": len(requests), "downloaded_bytes": total_bytes}) + b"\n")
        raise
    finally:
        journal.close()


def select_passages(manifest, question):
    """Return tiny task-facing sources plus private, exact character bindings."""
    policy = validate_policy(manifest["policy"])
    _need(manifest["question_sha256"] == _digest(question.encode("utf-8")), "Question binding mismatch")
    tokens = set(question_tokens(question))
    chunks = []
    for source in manifest["sources"]:
        for span in source["spans"]:
            text = span["text"]
            _need(span["text_sha256"] == _digest(text.encode("utf-8")), "Span text binding mismatch")
            start = 0
            while start < len(text):
                end = min(len(text), start+policy["passage_bytes"])
                while len(text[start:end].encode("utf-8")) > policy["passage_bytes"]:
                    end -= 1
                _need(end > start, "UTF8 chunk cannot fit bound")
                if end < len(text):
                    boundary = text.rfind(" ", start, end)
                    if boundary > start:
                        end = boundary + 1
                passage = text[start:end]
                words = set(re.findall(r"[a-z][a-z0-9-]{2,}", passage.casefold()))
                score = len(words & tokens)
                evidence_id = span["evidence_id"] + f":c{start}-{end}"
                chunks.append({"task": {"source_id": evidence_id, "sha256": _digest(passage.encode("utf-8")), "text": passage},
                               "binding": {"source_id": evidence_id, "document_id": source["source_id"], "span_id": span["evidence_id"],
                                           "character_start": start, "character_end": end, "parent_text_sha256": span["text_sha256"],
                                           "original_sha256": source["original"]["sha256"]}, "score": score})
                start = end
    ranked = sorted(enumerate(chunks), key=lambda pair: (-pair[1]["score"], pair[0]))
    selected, used = [], 0
    for _, chunk in ranked:
        size = len(chunk["task"]["text"].encode("utf-8"))
        if len(selected) >= policy["max_passages"] or used+size > policy["selected_bytes"]:
            continue
        selected.append(chunk)
        used += size
    return freeze({"sources": [x["task"] for x in selected], "bindings": [x["binding"] for x in selected],
                   "coverage": {"available_chunks": len(chunks), "selected_chunks": len(selected), "excluded_chunks": len(chunks)-len(selected),
                                "available_text_bytes": sum(len(x["task"]["text"].encode("utf-8")) for x in chunks),
                                "selected_text_bytes": used, "segmentation": "bounded_utf8_contiguous_character_spans_v1",
                                "ranking": "unique_question_token_overlap_then_original_order", "full_article_in_prompt": False}})


def verify_retrieval(root, expected_manifest_sha256, question):
    root = Path(root).resolve()
    raw = _read(safe_child(root, "manifest.json"), 32*1024*1024)
    _need(_digest(raw) == expected_manifest_sha256, "Retrieval manifest mismatch")
    manifest = parse_json(raw)
    _need(manifest.get("schema_version") == 1 and manifest.get("kind") == "labbench_retrieval", "Unknown retrieval manifest")
    policy = validate_policy(manifest["policy"])
    _need(manifest["question_sha256"] == _digest(question.encode("utf-8")) and manifest["queries"] == list(make_queries(question, policy)), "Question-only query binding mismatch")
    _need(manifest["retriever_sha256"] == _digest(_read(Path(__file__), 1024*1024)), "Retriever source changed")
    complete = parse_json(_read(safe_child(root, "COMPLETE.json"), 4096))
    _need(complete == {"manifest_sha256": expected_manifest_sha256, "journal_sha256": _digest(_read(safe_child(root, "journal.jsonl"), 1024*1024))}, "Retrieval completion mismatch")
    events = read_chain(root / "journal.jsonl")
    _need(events[-1]["event"] == "build_completed" and events[-1]["details"]["manifest_sha256"] == expected_manifest_sha256, "Incomplete retrieval journal")
    by_id, bodies, total, accounted, search_urls = {}, {}, 0, 0, []
    start_events = [e["details"] for e in events if e["event"] == "retrieval_request_started"]
    _need(len(start_events) == len(manifest["requests"]), "Request count/journal mismatch")
    for index, entry in enumerate(manifest["requests"]):
        _need(entry["request_id"] == f"{index:03d}" and entry["request_id"] not in by_id, "Duplicate or reordered request")
        _safe_url(entry["url"])
        by_id[entry["request_id"]] = entry
        _need(canonical(start_events[index]) == canonical({"request_id": entry["request_id"], "url": entry["url"], "kind": entry["kind"],
              "status": "started", "byte_reservation": entry["byte_reservation"]}), "Request/journal identity mismatch")
        _need(type(entry["byte_reservation"]) is int and 0 < entry["byte_reservation"] <= policy["total_bytes"]-accounted,
              "Request reservation exceeds remaining budget")
        cap = policy["metadata_bytes"] if entry["kind"] == "search" else policy["article_bytes"]
        _need(entry["byte_reservation"] == min(cap, policy["total_bytes"]-accounted), "Incorrect byte reservation")
        _need(type(entry["accounted_bytes"]) is int and 0 <= entry["accounted_bytes"] <= entry["byte_reservation"], "Invalid request accounting")
        accounted += entry["accounted_bytes"]
        if entry["kind"] == "search":
            search_urls.append(entry["url"])
        else:
            _need(entry["kind"] == "fulltext", "Unknown request kind")
        if entry["status"] == "completed":
            body = _read(safe_child(root, entry["body_path"]), policy["metadata_bytes"] if entry["kind"] == "search" else policy["article_bytes"])
            bodies[entry["request_id"]] = body
            receipt_raw = _read(safe_child(root, entry["receipt_path"]), 65536)
            receipt = parse_json(receipt_raw)
            _need(entry["body_sha256"] == _digest(body) and entry["bytes"] == len(body) and entry["receipt_sha256"] == _digest(receipt_raw), "Raw HTTP proof mismatch")
            _need(entry["accounted_bytes"] == len(body) and entry["byte_accounting_basis"] == "retained_response_body", "Measured transfer accounting mismatch")
            _need(receipt["status"] == "completed" and receipt["sha256"] == _digest(body) and receipt["bytes"] == len(body)
                  and receipt["relative_path"] == entry["body_path"] and receipt["source_url"] == entry["url"] and receipt["url"] == entry["url"]
                  and receipt["http_status"] == entry["http_status"] and receipt["dataset_id"] == "labbench_retrieved_literature"
                  and receipt["release_id"] == _digest(body), "HTTP receipt mismatch")
            _safe_url(receipt["final_url"])
            completed = [e["details"] for e in events if e["event"] == "retrieval_request_completed" and e["details"]["request_id"] == entry["request_id"]]
            _need(len(completed) == 1 and canonical(completed[0]) == canonical({k:v for k,v in entry.items() if k not in ("error_type","failure_cause")}), "Completed request journal mismatch")
            total += len(body)
        else:
            _need(entry["status"] == "failed", "Unresolved request in completed retrieval")
            _need(entry["accounted_bytes"] == entry["byte_reservation"] and entry["byte_accounting_basis"] == "conservative_unmeasured_reservation", "Unmeasured transfer reservation missing")
        if "error_type" in entry:
            failed = [e["details"] for e in events if e["event"] == "retrieval_request_failed" and e["details"]["request_id"] == entry["request_id"]]
            _need(len(failed) == 1 and canonical(failed[0]) == canonical(entry), "Failed request journal mismatch")
    expected_urls = [BASE + "search?" + urllib.parse.urlencode({"query": q, "format": "json", "pageSize": policy["hits_per_query"], "resultType": "core"}) for q in manifest["queries"]]
    _need(search_urls == expected_urls[:len(search_urls)], "Search recipe substitution")
    _need(total <= accounted <= policy["total_bytes"] and total == manifest["costs"]["downloaded_bytes"]
          and accounted == manifest["costs"]["safety_accounted_bytes"] and accounted-total == manifest["costs"]["unmeasured_transfer_upper_bytes"], "Retrieval byte accounting mismatch")
    _need(len(manifest["sources"]) <= policy["max_articles"] and sum(x["kind"] == "fulltext" for x in by_id.values()) <= policy["max_articles"], "Article count exceeded")
    eligible, eligible_seen = [], set()
    for entry in manifest["requests"]:
        if entry["kind"] != "search" or entry["status"] != "completed" or not 200 <= entry["http_status"] < 300 or "error_type" in entry:
            continue
        try:
            records = parse_json(bodies[entry["request_id"]])["resultList"]["result"]
            _need(isinstance(records,list) and len(records)<=policy["hits_per_query"], "Invalid metadata cardinality")
            for rank, record in enumerate(records):
                candidate, _ = _candidate(record,policy)
                if candidate is not None and candidate["pmcid"] not in eligible_seen:
                    eligible_seen.add(candidate["pmcid"])
                    eligible.append({"candidate":candidate,"request_id":entry["request_id"],"rank":rank})
        except (KeyError,TypeError,ContractError):
            continue
    full_requests = [entry for entry in manifest["requests"] if entry["kind"] == "fulltext"]
    _need([entry["url"] for entry in full_requests] == [BASE+x["candidate"]["pmcid"]+"/fullTextXML" for x in eligible[:len(full_requests)]], "Fulltext selection changed from first eligible results")
    expected_sources = []
    for item, entry in zip(eligible,full_requests):
        if entry["status"] != "completed" or not 200 <= entry["http_status"] < 300 or "error_type" in entry:
            continue
        try:
            rebuilt = parse_article(bodies[entry["request_id"]],item["candidate"])
        except ContractError:
            continue
        rebuilt.update({"original":{"path":entry["body_path"],"sha256":entry["body_sha256"],"bytes":entry["bytes"],"receipt_path":entry["receipt_path"]},
                        "discovery_request_id":item["request_id"],"discovery_rank":item["rank"]})
        expected_sources.append(rebuilt)
    _need(canonical(expected_sources) == canonical(manifest["sources"]), "Retained source schedule/content mismatch")
    _need(canonical(manifest["coverage"]) == canonical({"eligible_metadata_articles":len(eligible),"attempted_fulltext_articles":len(full_requests),
          "retained_articles":len(expected_sources),"article_limit_exclusions":max(0,len(eligible)-policy["max_articles"]),
          "absence_of_evidence_claim":False,"source_access":"bounded_selected_subset"}), "Coverage reconstruction mismatch")
    seen = set()
    for source in manifest["sources"]:
        _need(source["source_id"] not in seen, "Duplicate retained article")
        seen.add(source["source_id"])
        discovery = by_id[source["discovery_request_id"]]
        _need(discovery["kind"] == "search" and 200 <= discovery["http_status"] < 300, "Invalid discovery parent")
        search = parse_json(bodies[discovery["request_id"]])
        candidates = search["resultList"]["result"]
        rank = source["discovery_rank"]
        _need(type(rank) is int and 0 <= rank < min(len(candidates), policy["hits_per_query"]), "Invalid discovery locator")
        candidate, _ = _candidate(candidates[rank], policy)
        _need(candidate is not None and candidate["pmcid"] == source["source_id"], "Unqualified article parent")
        original = source["original"]
        matches = [entry for entry in by_id.values() if entry.get("body_path") == original["path"]]
        _need(len(matches) == 1 and matches[0]["kind"] == "fulltext" and matches[0]["url"] == BASE+source["source_id"]+"/fullTextXML"
              and 200 <= matches[0]["http_status"] < 300, "Unqualified fulltext request")
        payload = bodies[matches[0]["request_id"]]
        _need(original["sha256"] == _digest(payload) and original["bytes"] == len(payload) and original["receipt_path"] == matches[0]["receipt_path"], "Original document binding mismatch")
        rebuilt = parse_article(payload, candidate)
        rebuilt.update({"original": original, "discovery_request_id": source["discovery_request_id"], "discovery_rank": rank})
        _need(canonical(rebuilt) == canonical(source), "Parsed source or span mismatch")
    return freeze(manifest)
