"""Canonical command alias for explicit pinned legacy diagnostic operations."""
if __name__ == "__main__":
    from asof.study.native_diagnostic import main
    raise SystemExit(main())
else:
    from importlib import import_module
    import sys
    sys.modules[__name__] = import_module("asof.study.native_diagnostic")
