"""Canonical command alias for the pinned legacy comparison implementation."""
if __name__ == "__main__":
    from asof.study.authority_four_arm import main
    raise SystemExit(main())
else:
    from importlib import import_module
    import sys
    sys.modules[__name__] = import_module("asof.study.authority_four_arm")
