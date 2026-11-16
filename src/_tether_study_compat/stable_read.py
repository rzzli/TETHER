"""Compatibility import for shared stable reads; one implementation, no driver load."""
import sys
from tether_engine import stable_read as _implementation
sys.modules[__name__] = _implementation
