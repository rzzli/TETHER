"""Canonical command alias for explicit pinned legacy diagnostic operations."""
if __name__ == "__main__":
    from tether_engine.study.native_diagnostic import main
    raise SystemExit(main())
else:
    from importlib import import_module
    import sys
    sys.modules[__name__] = import_module("tether_engine.study.native_diagnostic")
