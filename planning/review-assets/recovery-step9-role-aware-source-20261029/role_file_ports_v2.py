"""Role-aware injected original-file ports. No filesystem, SDK or real FFI.

Each invocation has a prebound raw carrier. Sentinel-to-original assignments
precede validation, accounting, cache updates and clocks. Generated/virtual
bindings are development fixtures and do not authenticate physical originals.
"""
from dataclasses import dataclass
import hashlib
import struct
from role_owner_v2 import (SharedOwner, SharedOwnerError, FileSpec, FileRecordRef,
    CallRef, CallState, UNOBSERVED, INVALID, APIS, uint, signed_bool, usable, path_key, sha)

FRAMES = {'GetFileInformationByHandleEx': 8,
          'GetFinalPathNameByHandleW': 8202, 'GetFileSizeEx': 8}


class AdoptionHooks:
    """A single prebound invocation; never an owner reconstructed from data."""
    __slots__ = ('owner', '_bound', '_accepting')

    def __init__(self, owner, call=None):
        if type(owner) is not SharedOwner:
            raise SharedOwnerError('FOREIGN_IDENTITY')
        owner._active()
        if call is not None:
            # Validate the carrier BEFORE the original is invoked. A caller
            # cannot construct a bound shim around another owner's live slot.
            if (type(call) is not CallState or call.owner is not owner
                or not uint(call.ordinal, len(owner.registry._calls) - 1)
                or owner.registry._calls[call.ordinal] is not call
                or call.invoked or call.stopped):
                raise SharedOwnerError('FOREIGN_IDENTITY')
        object.__setattr__(self, 'owner', owner)
        object.__setattr__(self, '_bound', call)
        object.__setattr__(self, '_accepting', call is not None)

    def __setattr__(self, name, value):
        raise TypeError('read-only invocation carrier')

    def _stop(self):
        object.__setattr__(self, '_accepting', False)

    def _carrier(self, ref):
        # Identity/lifetime tests invoke no supplied equality, type conversion,
        # callback or clock. The actual slot is fixed before binding dispatch.
        c = self._bound
        if c is None:
            # Legacy inspection/idempotence surface, not a first-return port.
            o = self.owner
            o._active()
            o._require_accounting_work()
            o.require(type(ref) is CallRef and ref._state.owner is o, 'FOREIGN_IDENTITY')
            c = ref._state
            o.require(uint(c.ordinal, len(o.registry._calls) - 1)
                and o.registry._calls[c.ordinal] is c, 'FOREIGN_IDENTITY')
            o.require(c.invoked and not c.stopped and o.primary is None, 'INVALID_INPUT')
            return c
        if not self._accepting or ref is not c.ref:
            raise SharedOwnerError('FOREIGN_IDENTITY')
        return c

    def _state(self, ref):
        c = self._carrier(ref)
        o = self.owner
        o._active()
        o.require(c.owner is o and c.invoked, 'FOREIGN_IDENTITY')
        return c

    def store_scalar(self, ref, value):
        c = self._carrier(ref)
        if c.scalar is UNOBSERVED:
            if self._bound is None:
                raise SharedOwnerError('INVALID_INPUT')
            c.scalar = value
        else:
            self.owner.require(c.scalar is value or type(c.scalar) is type(value)
                and type(value) is int and c.scalar == value, 'INVALID_INPUT')
        o = self.owner
        try:
            self._state(ref)
            valid = ((value is None or uint(value, INVALID)) if c.api == 'CreateFileW'
                else uint(value, 2**32 - 1) if c.api in ('GetFileType', 'GetFinalPathNameByHandleW')
                else signed_bool(value))
            if value is None and c.api != 'CreateFileW':
                # Observed NULL is losslessly retainable malformed data. It is
                # different from an arbitrary object/out-of-width raw value.
                raise SharedOwnerError('RAW_RETURN_UNKNOWN')
            o.require(valid, 'UNENCODABLE_RAW')
            if c.api == 'ReadFile':
                o._fold_read_fact(c)
            if c.api == 'CreateFileW':
                c.file.open_state = ('owned' if usable(value) else
                    'known_failure_no_handle' if value == INVALID else 'ownership_unknown')
            elif c.api == 'CloseHandle':
                c.file.close_state = 'returned_success' if value != 0 else 'returned_failure'
        except BaseException as error:
            o._accounting_failed(c, error, 'after_scalar_before_aux')
            raise

    def store_count(self, ref, value):
        c = self._carrier(ref)
        if c.count is UNOBSERVED:
            if self._bound is None:
                raise SharedOwnerError('INVALID_INPUT')
            c.count = value
        else:
            self.owner.require(c.count is value or type(c.count) is int
                and type(value) is int and c.count == value, 'INVALID_INPUT')
        o = self.owner
        try:
            self._state(ref)
            o.require(c.api == 'ReadFile' and uint(value, 2**32 - 1), 'UNENCODABLE_RAW')
            o._fold_read_fact(c)
        except BaseException as error:
            o._accounting_failed(c, error, 'after_count_before_aux')
            raise

    def store_error_definition(self, ref, defined):
        c = self._carrier(ref)
        if c.error_definition is UNOBSERVED:
            if self._bound is None:
                raise SharedOwnerError('INVALID_INPUT')
            c.error_definition = defined
        else:
            self.owner.require(c.error_definition is defined, 'INVALID_INPUT')
        self._state(ref)
        self.owner.require(type(defined) is bool, 'UNENCODABLE_RAW')
        if defined:
            failed = ((type(c.scalar) is int and c.scalar == INVALID)
                if c.api == 'CreateFileW' else
                (type(c.scalar) is int and c.scalar == 0))
            self.owner.require(failed, 'INVALID_INPUT')

    def store_error_value(self, ref, value):
        c = self._carrier(ref)
        if c.error is UNOBSERVED:
            if self._bound is None:
                raise SharedOwnerError('INVALID_INPUT')
            c.error = value
        else:
            self.owner.require(c.error is value or type(c.error) is int
                and type(value) is int and c.error == value, 'INVALID_INPUT')
        self._state(ref)
        self.owner.require(uint(value, 2**32 - 1), 'UNENCODABLE_RAW')

    def store_error(self, ref, value, defined):
        # Compatibility delivery has two independent first carriers. Store the
        # supplied values before validating either of the observed axes.
        c = self._carrier(ref)
        if self._bound is None and (c.error is UNOBSERVED or c.error_definition is UNOBSERVED):
            raise SharedOwnerError('INVALID_INPUT')
        if c.error is UNOBSERVED:
            c.error = value
        if c.error_definition is UNOBSERVED:
            c.error_definition = defined
        self.store_error_value(ref, value)
        self.store_error_definition(ref, defined)

    def _buffer(self, ref, buffer_ref, generation):
        c = self._state(ref)
        o = self.owner
        o.require(self._bound is not None, 'INVALID_INPUT')
        o.require(c.buffer is not None and buffer_ref is c.buffer
            and type(generation) is int and generation >= 0
            and generation == c.generation == buffer_ref._generation, 'FOREIGN_IDENTITY')
        o.require(c.scalar is UNOBSERVED, 'INVALID_INPUT')
        limit = FRAMES[c.api] if c.api in FRAMES else c.requested
        o.require(c.api in FRAMES or c.api == 'ReadFile', 'INVALID_INPUT')
        return c, limit

    def buffer_write_slice(self, ref, buffer_ref, generation, offset, data):
        """Trusted binding appends exact bytes; it receives no mutable view."""
        c, limit = self._buffer(ref, buffer_ref, generation)
        o = self.owner
        o.require(type(offset) is int and offset == c.buffer_written
            and type(data) is bytes and offset + len(data) <= limit, 'INVALID_INPUT')
        end = offset + len(data)
        memoryview(buffer_ref._data)[offset:end] = data
        # This is an observed completed copy, not an inferred native count.
        c.buffer_written = end
        object.__setattr__(buffer_ref, '_written', end)
        c.buffer_state = 'raw_retained'

    def buffer_copy_within(self, ref, buffer_ref, generation, source_offset, length):
        """Append a retained buffer region without exposing/caching its body."""
        c, limit = self._buffer(ref, buffer_ref, generation)
        o = self.owner
        o.require(type(source_offset) is int and type(length) is int
            and 0 <= source_offset and 0 < length
            and source_offset + length <= c.buffer_written
            and c.buffer_written + length <= limit, 'INVALID_INPUT')
        start = c.buffer_written
        end = start + length
        view = memoryview(buffer_ref._data)
        view[start:end] = view[source_offset:source_offset + length]
        c.buffer_written = end
        object.__setattr__(buffer_ref, '_written', end)
        c.buffer_state = 'raw_retained'

    def buffer_write(self, ref, buffer_ref, generation, data):
        c, limit = self._buffer(ref, buffer_ref, generation)
        self.owner.require(c.buffer_written == 0 and type(data) is bytes, 'INVALID_INPUT')
        if c.api in FRAMES:
            self.owner.require(len(data) == limit, 'INVALID_INPUT')
        self.buffer_write_slice(ref, buffer_ref, generation, 0, data)

    def aux(self, ref, field):
        c = self._state(ref)
        self.owner.require(self._bound is not None, 'INVALID_INPUT')
        self.owner.require(field in ('scalar_aux_ack', 'count_aux_ack', 'right_transfer_ack'), 'INVALID_INPUT')
        setattr(c, field, True)

    def raise_exception(self, ref, error, phase):
        c = self._state(ref)
        o = self.owner
        o.require(self._bound is not None, 'INVALID_INPUT')
        o.require(isinstance(error, BaseException) and type(phase) is str, 'INVALID_INPUT')
        c.stopped = True
        if not c.wrapper_return:
            c.wrapper_state = 'raised'
        o.record_error(error, phase)


@dataclass(frozen=True, eq=False)
class FilePortView:
    owner: object
    injected_binding: object

    def __post_init__(self):
        if type(self.owner) is not SharedOwner or not callable(getattr(self.injected_binding, 'invoke', None)):
            raise SharedOwnerError('INVALID_INPUT')

    def _file(self, ref):
        return self.owner.file_state(ref)

    def _call(self, api, file, args, requested=None):
        o = self.owner
        o._active()
        cleanup = api == 'CloseHandle'
        o.require(o.port is self and api in APIS and o._plan is not None, 'FOREIGN_IDENTITY')
        o.require(o.primary is None or cleanup, 'INVALID_INPUT')
        if api == 'ReadFile':
            limit = (file.spec.size // o.profile.chunk
                + int(file.spec.size % o.profile.chunk != 0) + 16) if file.spec.size else 0
            # A quota refusal precedes creating another reserved row. The
            # owner's index independently checks and charges the accepted row.
            o.require(uint(file._read_reservations, limit - 1), 'JOINT_CAP_EXCEEDED')
        buffer = o._read_buffer if api == 'ReadFile' else o._query_buffer if api in FRAMES else None
        c = o.reserve_call(api, file, requested, buffer)
        # The input carrier is an actual argument delivered to this invocation.
        if 'handle' in args:
            c.input_handle = args['handle']
        hooks = AdoptionHooks(o, c)
        try:
            with o.operation_guard(cleanup=cleanup):
                invoke = self.injected_binding.invoke
                call_ref = c.ref
                if buffer is not None:
                    object.__setattr__(buffer, '_written', 0)
                if api in ('GetFileType', 'GetFileInformationByHandleEx', 'GetFinalPathNameByHandleW', 'GetFileSizeEx'):
                    file.identity_queries.append(c.ordinal)
                o.call_clock(c, 'pre', cleanup)
                if api == 'CreateFileW':
                    file.open_state = 'entered_return_unknown'
                if cleanup:
                    file.close_state = 'entered_return_unknown'
                c.invoked = True
                invoke(call_ref, args, hooks)
                c.wrapper_return = True
                c.wrapper_state = 'returned'
                hooks._stop()
                if c.stopped or o.primary is not None and not cleanup:
                    raise o.primary or SharedOwnerError('RAW_RETURN_UNKNOWN')
                o.call_clock(c, 'post', cleanup)
                o.require(c.scalar is not UNOBSERVED, 'RAW_RETURN_UNKNOWN')
                if api in FRAMES:
                    o.require(c.buffer_written == FRAMES[api], 'IDENTITY_INCOMPLETE')
                    o.charge_raw(FRAMES[api])
                    c.query_bytes = bytes(memoryview(buffer._data)[:FRAMES[api]])
                    c.buffer_state = 'defined'
                    object.__setattr__(buffer, '_generation', buffer._generation + 1)
                return c
        except BaseException as error:
            c.stopped = True
            if not c.wrapper_return:
                c.wrapper_state = 'raised'
            o.record_error(error, 'original_close' if cleanup else 'binding_invoke')
            raise
        finally:
            hooks._stop()

    def acquire(self, spec):
        o = self.owner
        o._active()
        o.check()
        o.require(o._owned and o.port is self and type(spec) is FileSpec, 'FOREIGN_IDENTITY')
        file = o.registry._file_by_exact_path.get(spec.path)
        o.require(file is not None and file.spec == spec, 'FOREIGN_IDENTITY')
        o.require(file.open_state == 'unopened', 'INVALID_INPUT')
        prefix = 'source' if file.early else 'file'
        o.emit(prefix + '_open_reserved', {'file_id': file.id})
        c = self._call('CreateFileW', file, dict(path=spec.path, desired_access=2147483648,
            share_mode=1, security=None, creation=3, flags=2097280, template=None))
        o.require(usable(c.scalar), 'RAW_RETURN_UNKNOWN')
        o.emit(prefix + '_open_returned', {'file_id': file.id})
        return file.ref

    def inspect(self, ref):
        o = self.owner
        o._active()
        file = self._file(ref)
        o.check()
        o.require(o.port is self and usable(o.handle(file)) and not file.close_reserved
            and file.identity_state == 'not_attempted', 'IDENTITY_INCOMPLETE')
        file.identity_state = 'in_progress'
        handle = o.handle(file)
        if file.early:
            o.emit('source_identity_reserved', {'file_id': file.id})
        try:
            values = []
            calls = [('GetFileType', dict(handle=handle)),
                ('GetFileInformationByHandleEx', dict(handle=handle, info_class=9, buffer_bytes=8)),
                ('GetFinalPathNameByHandleW', dict(handle=handle, capacity=4101, flags=0)),
                ('GetFileSizeEx', dict(handle=handle))]
            for api, args in calls:
                values.append(self._call(api, file, args))
                o.check()
            typ, attrs, path, size = values
            o.require(type(typ.scalar) is int and typ.scalar == 1, 'IDENTITY_INCOMPLETE')
            o.require(attrs.scalar != 0 and attrs.query_bytes is not None, 'IDENTITY_INCOMPLETE')
            attributes, tag = struct.unpack('<II', attrs.query_bytes)
            o.require(not attributes & (16 | 1024), 'IDENTITY_INCOMPLETE')
            n = path.scalar
            o.require(uint(n, 4100) and n > 0 and path.query_bytes[2*n:2*n+2] == b'\0\0', 'IDENTITY_INCOMPLETE')
            text = path.query_bytes[:2*n].decode('utf-16-le', 'strict')
            if text.startswith('\\\\?\\'):
                text = text[4:]
            o.require(path_key(text) == path_key(file.spec.path), 'IDENTITY_INCOMPLETE')
            o.require(size.scalar != 0 and struct.unpack('<q', size.query_bytes)[0] == file.spec.size, 'IDENTITY_INCOMPLETE')
            o.check()
            file.identity_witness = (o, o.nonce, file.ref, handle, tuple(values))
            file.identity_state = 'verified'
            if file.early:
                o.emit('source_identity_returned', {'file_id': file.id})
        except BaseException as error:
            file.identity_state = 'unknown' if file.identity_state != 'refused' else 'refused'
            o.record_error(error, 'identity_query')
            raise

    def hash_capture(self, ref):
        o = self.owner
        o._active()
        file = self._file(ref)
        o.check()
        witness = file.identity_witness
        o.require(witness is not None and witness[0] is o and witness[1] is o.nonce
            and witness[2] is ref and witness[3] == o.handle(file)
            and not file.close_reserved and not file.hash_attempted, 'IDENTITY_INCOMPLETE')
        file.hash_attempted = True
        file.hasher = hashlib.sha256()
        prefix = 'source' if file.early else 'file'
        o.emit(prefix + '_hash_reserved', {'file_id': file.id})
        c = None
        try:
            if file.spec.capture:
                o.begin_capture(file)
            while o.read_known(file) < file.spec.size:
                o.check()
                n = min(o.profile.chunk, file.spec.size - o.read_known(file))
                c = self._call('ReadFile', file, dict(handle=o.handle(file), requested=n, overlapped=None), n)
                o.require(o.defined(c), 'READ_COUNT_UNKNOWN')
                o.require(c.count > 0 and c.buffer_written >= c.count, 'READ_PROGRESS_INCOMPLETE')
                with o.operation_guard():
                    o.check()
                    o.hook('hash_update', c.ref)
                    o.check()
                    update = file.hasher.update
                    hash_view = memoryview(c.buffer._data)[:c.count]
                    c.hash_attempted = True
                    c.hash_return = update(hash_view)
                    del hash_view, update
                    try:
                        c._hash_fold_phase = 'applying'
                        file.hashed += c.count
                        c._hash_fold_phase = 'applied'
                    except BaseException as error:
                        o._accounting_failed(c, error, 'hash_return_fold')
                        raise
                    o.check()
                if file.spec.capture:
                    with o.operation_guard():
                        o.hook('copy_bytes', c.ref)
                        o.check()
                        offset = file.captured
                        copy_into = memoryview(file.assembly).__setitem__
                        copy_span = slice(offset, offset + c.count)
                        copy_view = memoryview(c.buffer._data)[:c.count]
                        c.copy_attempted = True
                        c.copy_return = copy_into(copy_span, copy_view)
                        del copy_into, copy_span, copy_view
                        try:
                            c._copy_fold_phase = 'applying'
                            file.captured += c.count
                            c._copy_fold_phase = 'applied'
                        except BaseException as error:
                            o._accounting_failed(c, error, 'copy_return_fold')
                            raise
                        o.check()
                object.__setattr__(c.buffer, '_generation', c.buffer._generation + 1)
            with o.operation_guard():
                digest = file.hasher.hexdigest
                file.actual_sha = digest()
                del digest
                o.check()
            o.require(file.actual_sha == file.spec.sha256, 'INVALID_INPUT')
            file.hash_complete = True
            if file.spec.capture:
                blob = bytes(file.assembly)
                o.finish_capture(file, blob)
            else:
                blob = None
            o.emit(prefix + '_hash_returned', {'file_id': file.id})
            return blob
        except BaseException as error:
            if c is not None:
                c.stopped = True
            if file.spec.capture and not file.capture_complete:
                file.capture_state = 'FAILED'
            o.record_error(error, 'hash_update')
            raise

    def close(self, ref):
        o = self.owner
        o._active()
        file = self._file(ref)
        o.require(o.port is self, 'FOREIGN_IDENTITY')
        o.require(not file.close_reserved, 'INVALID_INPUT')
        if not usable(o.handle(file)):
            return
        try:
            o.check(cleanup=True)
        except BaseException:
            file.close_state = 'not_dispatched_deadline'
            raise
        file.close_reserved = True
        file.close_state = 'reserved'
        try:
            o.emit('original_close_reserved', {'file_id': file.id}, cleanup=True)
        except BaseException:
            pass
        try:
            c = self._call('CloseHandle', file, dict(handle=o.handle(file)))
            o.require(c.scalar != 0, 'INVALID_INPUT')
        finally:
            try:
                o.emit('original_close_returned_or_unknown', {'file_id': file.id}, cleanup=True)
            except BaseException:
                pass
