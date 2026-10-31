"""Refresh only current-status paragraphs; preserve the dated prior history."""
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
        markers = [i for i, row in enumerate(rows)
                   if row.startswith((b'Current checkpoint:', b'Current checkpoint,'))]
        if len(markers) != 1:
            raise RuntimeError('ambiguous current status: ' + name)
        current = markers[0]
        if not rows[current + 2].startswith(b'Next:'):
            raise RuntimeError('current next paragraph is not adjacent: ' + name)
        link = 'Project Progress Reassessment 2026-10-30 - Entry Contract Coverage.md'
        if not name.startswith('planning/'):
            link = 'planning/' + link
        text = ('Current checkpoint, 30 October UTC: [entry contract coverage](<' + link +
                '>) is accepted in source/synthetic scope (root e54b6d55; branch peer '
                '64868e28; byte peer 5ee5dd20): 50 assertions pass and three remain '
                'explicitly deferred across 32 controls/53 branches, with no failures '
                'or unknown suffix. The 9.172s suite includes one actual procedural '
                '3,991,999,872-byte bulk stream. All 594 artifact hashes match. '
                'The complete entry gate, R09 and scientific validation remain open.')
        onward = ('Next: implement E08 external decision/output content-pin policy. '
                  'Pre-code metadata is accepted under a055dfb3 (52 literal expectations '
                  'and 15 planned integration branches); source/harness authoring only '
                  'is authorized under 29f35d62, with subject execution still unbound. '
                  'The two historical E16 invocations remain excluded/deferred. Native25, '
                  'real new84 roster, physical14/joint budgets, native/resources and '
                  'scientific/human gates remain pending. AsOf 0.3.11/default v2 retains '
                  '1,774 application tests/327 pins; no new application-suite run or '
                  'integration, native/model execution, original payload read or data '
                  'collection. $0; downloader/stopped monitor untouched. Original '
                  'FAILED/INCOMPLETE_TIMEOUT results remain unchanged.')
        for index, value in ((current, text), (current + 2, onward)):
            newline = b'\r\n' if rows[index].endswith(b'\r\n') else b'\n'
            rows[index] = value.encode() + newline
        pending.append((path, b''.join(rows), name))
    for path, raw, name in pending:
        path.write_bytes(raw)
        print(name)


if __name__ == '__main__':
    main()
