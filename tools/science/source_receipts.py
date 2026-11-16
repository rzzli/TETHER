"""Read-only interpretation of retained acquisition receipts for research audits.

This produces a provenance observation, never a replacement transport receipt or
an actor grant. Callers supply independently pinned expected identities and exact
payload bytes. Availability and source-use decisions remain separate.
"""
from datetime import datetime, timedelta
import hashlib
import re

from tether_engine.bundle_files import logical_parts
from tether_engine.serde import ContractError, parse_json


def _need(condition, message):
    if not condition:
        raise ContractError(message)


def _digest(value, length=64):
    _need(isinstance(value, str) and re.fullmatch('[0-9a-f]{'+str(length)+'}', value),
          'Invalid receipt/payload digest')
    return value


def _path(value):
    _need(isinstance(value, str), 'Invalid relative receipt path')
    return '/'.join(logical_parts(value.replace('\\', '/')))


def _utc(value):
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, TypeError, AttributeError) as error:
        raise ContractError('Receipt time must be explicit UTC') from error
    _need(stamp.tzinfo is not None and stamp.utcoffset() == timedelta(0),
          'Receipt time must be explicit UTC')
    return value  # Retain the original precision/spelling; do not backdate it.


def conservative_utc_bound(value):
    """Ceil a UTC receipt instant to microseconds without backdating availability.

    Keep the original timestamp in provenance; this value is only a conservative
    availability bound compatible with the runtime's timestamp precision.
    """
    match = re.fullmatch(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,9}))?(?:Z|\+00:00)',
                         value) if isinstance(value, str) else None
    _need(match is not None, 'Receipt bound requires an explicit UTC instant of at most nanosecond precision')
    fraction = match.group(2) or ''
    try:
        stamp = datetime.fromisoformat(match.group(1)+'.'+fraction[:6].ljust(6, '0')+'+00:00')
        if any(digit != '0' for digit in fraction[6:]):
            stamp += timedelta(microseconds=1)
    except (ValueError, OverflowError) as error:
        raise ContractError('Invalid UTC receipt bound') from error
    return stamp.isoformat(timespec='microseconds').replace('+00:00', 'Z')


def qualify_receipt(receipt_bytes, payload, expected):
    """Check two supported formats against caller-selected, pinned identities.

    Only the enclosing caller can bind ``expected`` to its anchored inventory.
    Matching a publisher digest proves consistency with that supplied value, not
    authenticity of the publisher/listing or historical publication.
    """
    _need(type(receipt_bytes) is bytes and len(receipt_bytes) <= 1024**2,
          'Receipt exceeds byte limit')
    _need(type(payload) is bytes and type(expected) is dict, 'Expected bytes and source identity')
    receipt_hash = hashlib.sha256(receipt_bytes).hexdigest()
    _need(receipt_hash == _digest(expected.get('receipt_sha256')), 'Original receipt hash differs')
    receipt = parse_json(receipt_bytes)
    _need(type(receipt) is dict, 'Receipt must be an object')
    size, digest = len(payload), hashlib.sha256(payload).hexdigest()
    _need(type(expected.get('bytes')) is int and expected['bytes'] == size and
          _digest(expected.get('sha256')) == digest, 'Observed payload differs from expected identity')
    _need(type(receipt.get('bytes')) is int and receipt['bytes'] == size and
          receipt.get('sha256') == digest, 'Receipt payload size/hash differs')
    for name in ('release', 'source', 'url'):
        _need(isinstance(expected.get(name), str) and bool(expected[name]), 'Missing expected source '+name)
    relative = _path(expected.get('relative_path'))
    algorithm = expected.get('publisher_algorithm')
    _need(algorithm in ('sha1', 'sha256'), 'Unsupported publisher digest algorithm')
    publisher_digest = _digest(expected.get('publisher_digest'), 40 if algorithm == 'sha1' else 64)
    _need(hashlib.new(algorithm, payload).hexdigest() == publisher_digest,
          'Publisher digest differs from observed payload')

    if receipt.get('status') == 'payload_verified':
        kind = 'historical_partition_v1'
        _need(type(receipt.get('schema_version')) is int and receipt['schema_version'] == 1,
              'Unsupported historical receipt version')
        entry = receipt.get('entry')
        _need(type(entry) is dict, 'Missing historical receipt entry')
        for key in ('release', 'source', 'url', 'publisher_algorithm', 'publisher_digest'):
            _need(entry.get(key) == expected[key], 'Historical receipt entry '+key+' differs')
        _need(_path(entry.get('relative_path')) == relative, 'Historical receipt relative path differs')
        _need(receipt.get('request_sha256') == _digest(expected.get('request_sha256')),
              'Historical receipt request differs')
        _need(receipt.get('publisher_hash_verified') is True and
              receipt.get('observed_publisher_digest') == publisher_digest and
              receipt.get('response_bytes_exact') is True and receipt.get('error_class') is None,
              'Historical transport receipt is not verified')
        transport = receipt.get('transport')
        _need(type(transport) is dict and transport.get('status') == 'response_complete' and
              type(transport.get('http_status')) is int and transport['http_status'] == 200 and
              type(transport.get('response_bytes_read')) is int and transport['response_bytes_read'] == size and
              (transport.get('content_length') is None or
               (type(transport['content_length']) is int and transport['content_length'] == size)) and
              transport.get('error_class') is None, 'Historical transport accounting differs')
        retrieved = _utc(receipt.get('finished_at_utc'))
    elif receipt.get('status') == 'completed':
        kind = 'download_completed_v1'
        for key, expected_key in (('receipt_id', 'receipt_id'), ('dataset_id', 'dataset_id'),
                                  ('release_id', 'release'), ('url', 'url')):
            _need(isinstance(expected.get(expected_key), str) and bool(expected[expected_key]) and
                  receipt.get(key) == expected[expected_key], 'Download receipt '+key+' differs')
        _need(_path(receipt.get('relative_path')) == relative, 'Download receipt relative path differs')
        retrieved = _utc(receipt.get('completed_at_utc'))
    else:
        raise ContractError('Unsupported or incomplete receipt status')
    role = receipt.get('role')
    _need(role is None or role in ('evaluation_only', 'agent_evidence', 'reference'),
          'Unsupported collection role')
    claimed = receipt.get('publisher_hash_verified')
    _need(claimed is None or type(claimed) is bool, 'Invalid publisher verification claim')
    return {'schema_version': 1, 'receipt_format': kind, 'receipt_sha256': receipt_hash,
            'payload_sha256': digest, 'payload_bytes': size, 'release': expected['release'],
            'source': expected['source'], 'relative_path': relative, 'source_url': expected['url'],
            'collection_role': role, 'actor_access_granted': False,
            'retrieved_at': retrieved, 'historical_available_by': None,
            'publisher_algorithm': algorithm, 'publisher_digest': publisher_digest,
            'receipt_claimed_publisher_verified': claimed, 'publisher_digest_matches_payload': True,
            'scope': 'Pinned receipt and payload consistency; no source-use or historical-availability grant'}
