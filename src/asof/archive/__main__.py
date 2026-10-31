"""Offline archive restoration and verification: python -m asof.archive."""
import argparse
import json
from .restore import materialize, verify


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command',required=True)
    restore = commands.add_parser('restore')
    for name in ('checkpoint','checkpoint-sha256','recovery','recovery-sha256','supplement','supplement-sha256','output'):
        restore.add_argument('--'+name,required=True)
    check = commands.add_parser('verify')
    for name in ('envelope','envelope-sha256','run-id'):
        check.add_argument('--'+name,required=True)
    check.add_argument('--root',action='append',required=True,help='Explicit caller-approved root_id=absolute_path')
    check.add_argument('--receipt-sha256')
    check.add_argument('--journal-sha256')
    args = vars(parser.parse_args(argv)); command = args.pop('command')
    try:
        if command == 'restore':
            result = materialize(**args)
        else:
            pairs = [value.split('=',1) for value in args.pop('root')]
            if any(len(p)!=2 for p in pairs) or len({p[0] for p in pairs}) != len(pairs):
                parser.error('Roots must be unique root_id=absolute_path assignments')
            result = verify(**args,approved_roots=dict(pairs))
        print(json.dumps(result,indent=2))
        return 0
    except Exception as exc:
        print(json.dumps(dict(status='failed',error_class=type(exc).__name__,message=str(exc))))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
