"""Update only the two current-status paragraphs in six existing repo docs."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FILES = ('README.md', 'TODO.md',
         'planning/Project Recovery and Evaluation Plan 2026-10-26.md',
         'planning/Recovery Status and Next Gates 2026-10-26.md',
         'planning/Project Progress Reassessments.md',
         'planning/R09 Unicode Coverage and Verifier Recovery Plan 2026-10-29.md')


def main():
    pending = []
    for name in FILES:
        path = ROOT / name
        rows = path.read_bytes().splitlines(keepends=True)
        checkpoint = [i for i, row in enumerate(rows)
                      if row.startswith((b'Current checkpoint:', b'Current checkpoint,'))]
        if len(checkpoint) != 1:
            raise RuntimeError('ambiguous current status: ' + name)
        next_steps = [i for i, row in enumerate(rows)
                      if i > checkpoint[0] and row.startswith(b'Next:')]
        if not next_steps or next_steps[0] != checkpoint[0] + 2:
            raise RuntimeError('current next paragraph is not adjacent: ' + name)
        link = 'Project Progress Reassessment 2026-10-30 - Entry Corrections.md'
        if not name.startswith('planning/'):
            link = 'planning/' + link
        current = ('Current checkpoint, 30 October UTC: [entry corrections](<' + link +
                   '>) are accepted for five unchanged synthetic regressions (root 0d9c42a2, '
                   'actual peer 5efc550f): five PASS in 0.203s. Source1 constructor and Source2 '
                   'stopped-close cache failures remain preserved. The actual 99,000-byte helper '
                   'prefix and separate 121,192-byte pre-entry trusted kernel are explicit. '
                   'This closes the correction slice, not the full entry gate, R09 or scientific validation.')
        onward = ('Next: finish the frozen 32 entry controls/53 literal branches; test preparation '
                  'is authorized under df44dee0. Native25 coverage/disposition, the complete real '
                  'new-84 source/import/consumer roster, physical 14-API output/readback and joint '
                  'native/resources remain open. Illustrative 19,079 pre-directory calls do not '
                  'fit original-only C16384. AsOf 0.3.11/default v2 retains 1,774 tests/327 pins; '
                  'no new full-suite run, application/default change, paid call, native experiment '
                  'or data collection. $0; downloader/stopped monitor untouched. Human reviews '
                  'and scientific readiness remain pending; original FAILED/INCOMPLETE_TIMEOUT unchanged.')
        for index, text in ((checkpoint[0], current), (next_steps[0], onward)):
            newline = b'\r\n' if rows[index].endswith(b'\r\n') else b'\n'
            rows[index] = text.encode('utf-8') + newline
        pending.append((path, b''.join(rows), name))
    for path, raw, name in pending:
        path.write_bytes(raw)
        print(name)


if __name__ == '__main__':
    main()
