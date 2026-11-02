"""TETHER recorded synthetic-study command; no native model inference."""
from __future__ import annotations

import argparse
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tether.study", description=__doc__)
    parser.add_argument("command", choices=("smoke",))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    from asof.serde import canonical
    from asof.study.__main__ import smoke
    print(canonical(smoke(args.output)).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
else:
    # Normal imports share the original module, avoiding a different __main__
    # attribute on the shared legacy parent package. The subprocess -m path
    # executes this physical wrapper under the interpreter's __main__ name.
    from importlib import import_module
    import sys
    sys.modules[__name__] = import_module("asof.study.__main__")
