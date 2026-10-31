"""Qualify local PID visibility using only this process's temporary loopback listener.

No HTTP, model, remote requests or foreign process operations. The coordinating
agent chooses the execution context; this script contains no elevation/fallback.
"""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import struct
import sys


def probe():
    report = dict(schema_version=1, observed_at_utc=datetime.now(timezone.utc).isoformat(),
                  pid=os.getpid(), api="GetExtendedTcpTable", table_class="TCP_TABLE_OWNER_PID_LISTENER",
                  remote_requests=0, http_requests=0, model_calls=0, listener_created=False,
                  own_listener_closed=False, ownership_confirmed=False, execution_context="caller_supplied")
    listener = None
    try:
        if os.name != "nt":
            raise RuntimeError("This qualification is explicitly Windows-only")
        function = ctypes.WinDLL("iphlpapi", use_last_error=True).GetExtendedTcpTable
        function.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), wintypes.BOOL,
                             wintypes.ULONG, ctypes.c_int, wintypes.ULONG]
        function.restype = wintypes.DWORD
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        host, port = listener.getsockname()
        report.update(listener_created=True, host=host, port=port)
        size = wintypes.DWORD(0)
        status = function(None, ctypes.byref(size), False, socket.AF_INET, 3, 0)
        report.update(size_query_status=int(status), required_bytes=int(size.value))
        if status not in (0, 122):
            raise OSError(int(status), "GetExtendedTcpTable size query failed")
        if not 4 <= size.value <= 1024 * 1024:
            raise ValueError("Listener table exceeds fixed inspection bound")
        data = ctypes.create_string_buffer(size.value)
        status = function(data, ctypes.byref(size), False, socket.AF_INET, 3, 0)
        report.update(table_read_status=int(status), returned_bytes=int(size.value))
        if status != 0:
            raise OSError(int(status), "GetExtendedTcpTable read failed; no fallback")
        count = struct.unpack_from("<I", data.raw)[0]
        if 4 + 24 * count > min(len(data), size.value):
            raise ValueError("Incomplete IPv4 owner PID listener table")
        matching = []
        for index in range(count):
            state, local_address, local_port, _, _, pid = struct.unpack_from("<6I", data.raw, 4 + 24 * index)
            candidate_port = socket.ntohs(local_port & 0xffff)
            if candidate_port == port:
                # Only this newly selected port is retained; foreign table entries are discarded.
                address = socket.inet_ntoa(struct.pack("<I", local_address))
                matching.append(dict(state=state, host=address, port=candidate_port, pid=pid))
        report["own_port_rows"] = matching
        report["ownership_confirmed"] = matching == [dict(state=2, host=host, port=port, pid=os.getpid())]
        if not report["ownership_confirmed"]:
            raise RuntimeError("Exact temporary listener/PID ownership not established")
        report["status"] = "qualified_for_this_execution_context_only"
    except Exception as error:
        report.update(status="not_qualified", error_class=type(error).__name__, error=str(error))
    finally:
        if listener is not None:
            try:
                listener.close()
                report["own_listener_closed"] = listener.fileno() == -1
            except Exception as error:
                report.update(status="not_qualified", cleanup_error=type(error).__name__)
        if not report["own_listener_closed"]:
            report["ownership_confirmed"] = False
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = probe()
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
    print(encoded)
    sys.exit(0 if result["ownership_confirmed"] and result["own_listener_closed"] else 1)
