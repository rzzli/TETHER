"""Trusted-code network guard permitting only Windows' exact stdlib self-pipe."""
import ipaddress
from pathlib import Path
import socket
import sys


def install_guard():
    allowed, blocked = [], []
    stdlib_socket = str(Path(socket.__file__).resolve())
    def audit(event, args):
        if event not in ("socket.connect", "socket.connect_ex", "socket.getaddrinfo", "socket.sendto", "socket.bind"):
            return
        frame, self_pipe = sys._getframe(1), False
        while frame is not None:
            if frame.f_code.co_name == "_fallback_socketpair" and str(Path(frame.f_code.co_filename).resolve()) == stdlib_socket:
                self_pipe = True
                break
            frame = frame.f_back
        if event in ("socket.connect", "socket.bind") and self_pipe and ipaddress.ip_address(args[1][0]).is_loopback:
            allowed.append({"event": event, "purpose": "stdlib_asyncio_socketpair"})
            return
        blocked.append({"event": event})
        raise PermissionError("Inspect policy worker denies external/non-self-pipe network")
    sys.addaudithook(audit)
    return {"allowed": allowed, "blocked": blocked,
            "scope": "trusted_python_audit_not_OS_sandbox"}
