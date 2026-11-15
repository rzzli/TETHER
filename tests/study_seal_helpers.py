"""Fault injection shared by study-driver tests; no input fixture dependencies."""
import hashlib
from pathlib import Path
from unittest.mock import patch

from tether_engine.journal import RunJournal, read_chain


def assert_seal_fault(test, output, invoke, *, after=False):
    output = Path(output).absolute()
    seal = RunJournal.seal
    calls, original_bytes = [], {}
    error = KeyboardInterrupt('after publication') if after else OSError('seal staging failed')
    def fail(journal, payload, **kwargs):
        if journal.output != output:
            return seal(journal, payload, **kwargs)
        calls.append(journal.output)
        if after:
            seal(journal, payload, **kwargs)
            original_bytes.update(receipt=(output/'receipt.json').read_bytes(),
                                  journal=journal.path.read_bytes())
        raise error
    with patch.object(RunJournal, 'seal', new=fail), test.assertRaises(type(error)) as caught:
        invoke()
    test.assertIs(caught.exception, error)
    test.assertEqual(calls, [output])
    if after:
        test.assertEqual((output/'receipt.json').read_bytes(), original_bytes['receipt'])
        test.assertEqual((output/'journal.jsonl').read_bytes(), original_bytes['journal'])
        test.assertFalse((output/'failure.json').exists())
        return hashlib.sha256(original_bytes['receipt']).hexdigest()
    test.assertFalse((output/'receipt.json').exists())
    test.assertTrue((output/'failure.json').exists())
    test.assertEqual(read_chain(output/'journal.jsonl')[-1]['event'], 'build_failed')
