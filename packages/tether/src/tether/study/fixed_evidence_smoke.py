"""Canonical command alias for the pinned legacy fixed-evidence implementation."""
if __name__ == "__main__":
    from asof.study.fixed_evidence_smoke import main
    raise SystemExit(main())
else:
    from importlib import import_module
    import sys
    sys.modules[__name__] = import_module("asof.study.fixed_evidence_smoke")
