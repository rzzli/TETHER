"""Pure strict byte/chunk oracle; not a vendor decoder or vocabulary recognizer.

Implements the frozen v2 fixture contract. Import/feeding performs no file,
network, native-library or codec operation. Corpus bounds belong to its runner;
this finite-bytes API makes no general streaming-resource qualification claim.
"""
from dataclasses import dataclass, replace

SPECIFICATION_SHA256 = "f4f3835481f1961c01830bf6ba37107cf270ebaad7a9321d6f1b4ee0fcdec44a"
CORPUS_SHA256 = "65428d32cc06c58836d1d541bde0e893db13cef9e5ae756e26d6e353908b302d"


@dataclass(frozen=True, slots=True)
class EncodingError:
    code: str
    byte_offset: int
    sequence_start_offset: int
    offending_byte: int | None

    def to_dict(self):
        return {"code": self.code, "byte_offset": self.byte_offset,
                "sequence_start_offset": self.sequence_start_offset,
                "offending_byte": self.offending_byte}


@dataclass(frozen=True, slots=True)
class Snapshot:
    status: str = "boundary"
    emitted_scalars: tuple[int, ...] = ()
    decoded_scalars: tuple[int, ...] = ()
    pending_hex: str = ""
    pending_width: int | None = None
    consumed_in_chunk: int = 0
    examined_in_chunk: int = 0
    consumed_total: int = 0
    examined_total: int = 0
    unconsumed_hex: str = ""
    error: EncodingError | None = None
    finalization: str = "not_requested"

    def to_dict(self):
        # Every mutable serialization container is newly allocated.
        return {"status": self.status, "emitted_scalars": list(self.emitted_scalars),
                "decoded_scalars": list(self.decoded_scalars),
                "pending_hex": self.pending_hex, "pending_width": self.pending_width,
                "consumed_in_chunk": self.consumed_in_chunk,
                "examined_in_chunk": self.examined_in_chunk,
                "consumed_total": self.consumed_total, "examined_total": self.examined_total,
                "unconsumed_hex": self.unconsumed_hex,
                "error": None if self.error is None else self.error.to_dict(),
                "finalization": self.finalization}


def _continuation_error(pending, value):
    if not 0x80 <= value <= 0xBF:
        return "invalid_continuation"
    if len(pending) == 1:
        lead = pending[0]
        if (lead == 0xE0 and value < 0xA0) or (lead == 0xF0 and value < 0x90):
            return "overlong_sequence"
        if lead == 0xED and value > 0x9F:
            return "surrogate_scalar"
        if lead == 0xF4 and value > 0x8F:
            return "out_of_range_scalar"
    return None


def _scalar(pending, width):
    value = pending[0] & {2: 0x1F, 3: 0x0F, 4: 0x07}[width]
    for byte in pending[1:]:
        value = (value << 6) | (byte & 0x3F)
    return value


class StrictUtf8Oracle:
    __slots__ = ("__state",)

    def __init__(self):
        self.__state = Snapshot()

    @property
    def snapshot(self):
        return self.__state

    def feed(self, chunk, *, final=False):
        if type(chunk) is not bytes:
            raise TypeError("chunk_must_be_bytes")
        if type(final) is not bool:
            raise TypeError("final_must_be_bool")
        prior = self.__state
        if prior.status == "finished":
            raise RuntimeError("decoder_already_finalized")
        if prior.error is not None:
            self.__state = replace(prior, emitted_scalars=(), consumed_in_chunk=0,
                                   examined_in_chunk=0, unconsumed_hex=chunk.hex(),
                                   finalization="failed" if final else "not_requested")
            return self.__state

        pending = bytes.fromhex(prior.pending_hex)
        width = prior.pending_width
        emitted = []
        consumed = examined = 0
        error = None
        unconsumed = b""
        for index, byte in enumerate(chunk):
            examined += 1
            code = None
            if pending:
                code = _continuation_error(pending, byte)
            elif 0x80 <= byte <= 0xBF:
                code = "unexpected_continuation"
            elif byte in (0xC0, 0xC1) or byte >= 0xF5:
                code = "invalid_lead"

            if code is not None:
                offset = prior.consumed_total + consumed
                error = EncodingError(code, offset, offset - len(pending), byte)
                unconsumed = chunk[index:]
                break

            consumed += 1
            if pending:
                pending += bytes((byte,))
                if len(pending) == width:
                    emitted.append(_scalar(pending, width))
                    pending, width = b"", None
            elif byte <= 0x7F:
                emitted.append(byte)
            else:
                pending = bytes((byte,))
                width = 2 if byte <= 0xDF else 3 if byte <= 0xEF else 4

        total = prior.consumed_total + consumed
        if error is None and final and pending:
            error = EncodingError("premature_eof", total, total - len(pending), None)

        status = "error" if error else "finished" if final else "pending" if pending else "boundary"
        self.__state = Snapshot(
            status=status, emitted_scalars=tuple(emitted),
            decoded_scalars=prior.decoded_scalars + tuple(emitted),
            pending_hex=pending.hex(), pending_width=width,
            consumed_in_chunk=consumed, examined_in_chunk=examined,
            consumed_total=total, examined_total=prior.examined_total + examined,
            unconsumed_hex=unconsumed.hex(), error=error,
            finalization=("failed" if error else "succeeded") if final else "not_requested")
        return self.__state
