"""Canonical command alias for the pinned legacy bounded-retrieval implementation."""
if __name__ == "__main__":
    from tether_engine.study.retrieval_smoke import main
    raise SystemExit(main())
else:
    from importlib import import_module
    import sys
    sys.modules[__name__] = import_module("tether_engine.study.retrieval_smoke")
