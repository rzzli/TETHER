"""Literal Markdown rendering of source data; never alters evidence contracts.

ASCII punctuation is escaped in prose and table cells. Embedded JSON uses a
CommonMark code span whose delimiter cannot occur in the serialized value.
The fixed dossier template alone supplies document structure.
"""
from collections.abc import Mapping
import math
import re
import string

from .serde import ContractError, MAX_NORMALIZED_JSON_BYTES, canonical


def mapping(value):
    if not isinstance(value, Mapping):
        raise ContractError("Dossier rendering requires a mapping")
    if not all(isinstance(key, str) for key in value):
        raise ContractError("Dossier rendering requires string keys")
    return value


def sequence(value):
    if not isinstance(value, (tuple, list)):
        raise ContractError("Dossier rendering requires a sequence")
    return value


def _string(value):
    if not isinstance(value, str):
        raise ContractError("Dossier rendering requires text")
    if any((ord(character) < 32 and character not in "\t\n\r") or
           0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ContractError("Dossier text contains an unsupported Unicode character")
    return value.replace("\r\n", "\n").replace("\r", "\n")


def markdown_text(value, *, multiline=False):
    """Preserve Unicode text while making source punctuation literal Markdown."""
    value = _string(value)
    escaped = []
    for character in value:
        if character in "&<>":
            escaped.append({"&": "&amp;", "<": "&lt;", ">": "&gt;"}[character])
        elif character == "\n" and not multiline:
            escaped.append("&#10;")
        elif character in string.punctuation:
            escaped.append("\\" + character)
        else:
            escaped.append(character)
    return "".join(escaped)


def markdown_quote(value):
    return "> " + markdown_text(value, multiline=True).replace("\n", "\n> ")


def markdown_code(value):
    """Source cannot terminate its own CommonMark inline code delimiter."""
    value = _string(value)
    if "\n" in value:
        raise ContractError("Dossier inline code requires a single line")
    runs = re.findall(r"`+", value)
    delimiter = "`" * (max(map(len, runs), default=0) + 1)
    if runs or value.startswith(" ") or value.endswith(" "):
        return delimiter + " " + value + " " + delimiter
    return delimiter + value + delimiter


def _json_value(value, depth=0):
    if depth > 32:
        raise ContractError("Dossier metadata exceeds its nesting bound")
    if isinstance(value, Mapping):
        for key, item in mapping(value).items():
            _string(key)
            _json_value(item, depth + 1)
    elif isinstance(value, (tuple, list)):
        for item in value:
            _json_value(item, depth + 1)
    elif isinstance(value, str):
        _string(value)
    elif value is not None and type(value) not in (bool, int, float):
        raise ContractError("Dossier metadata must contain JSON values")
    elif type(value) is float and not math.isfinite(value):
        raise ContractError("Dossier metadata requires finite numbers")


def json_code_span(value):
    mapping(value)
    _json_value(value)
    try:
        payload = canonical(value)
    except (ValueError, TypeError, UnicodeError, OverflowError) as error:
        raise ContractError("Invalid dossier JSON metadata") from error
    if len(payload) > MAX_NORMALIZED_JSON_BYTES:
        raise ContractError("Dossier metadata exceeds the 64 MiB bound")
    return markdown_code(payload.decode("utf-8"))


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ContractError("Dossier numeric field requires a finite number")
    return value


def count(value):
    if type(value) is not int or value < 0:
        raise ContractError("Dossier count requires a nonnegative integer")
    return value
