"""Fresh loopback-qualified smoke03; no external network or provider calls."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import mock_qualification_v2 as smoke

try:
    smoke.main("03")
except BaseException as exc:
    smoke.write(smoke.EVIDENCE/"MOCK-FAILED-03.json", {"error_class": type(exc).__name__,
        "message": str(exc), "automatic_retry": False})
    raise
