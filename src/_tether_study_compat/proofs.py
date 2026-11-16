"""Compatibility import for shared file proofs; one implementation, no driver load."""
import sys
from tether_engine import file_proofs as _implementation
sys.modules[__name__] = _implementation
