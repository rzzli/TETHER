"""AST/text assembly only; imports no harness or under-test subject."""
import ast
from pathlib import Path

here=Path(__file__).resolve().parent
path=here/'run_entry_policy_suite_v1.py'
before=path.read_text(encoding='utf-8')
main=(here/'E08_RUNNER_MAIN_FRAGMENT-v1.txt').read_text(encoding='utf-8')
after=before[:before.index('def main():')]+main
ast.parse(after)
path.write_text(after,encoding='utf-8',newline='\n')
print('Runner/context assembled and AST parsed; no execution; still unfrozen/unbound.')
