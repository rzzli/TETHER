"""One-shot outer process envelope for the approved evidence-first controller.

Worker limits do not attest the enclosing controller's lifetime. This launcher
retains that separate observation, including a failed or interrupted child. It
never retries a controller or releases a permanent native-call authority.
"""
import argparse
from pathlib import Path
import sys
import time

from tether._process import ProcessLimits, validate_success_report
from tether_engine.journal import RunJournal
from tether_engine.serde import canonical, encode, freeze
from experiments.litqa_comparison.run import inventory
from . import contracts as c, run

CONTROL_RESERVE_SECONDS = 60


def launch(frame_path, expected, *, output):
    started = time.monotonic()
    fp, _ = c.capture(c.path(frame_path)); frame = c.read(fp)
    c.need(fp['sha256'] == expected and set(frame) == run.FRAME_FIELDS and
        type(frame['schema_version']) is int and frame['schema_version'] == 1 and
        frame['kind'] == run.KIND and frame['purpose'] in c.PURPOSES, 'Anchored controller frame required')
    root = c.path(output); producer = root / 'producer'
    c.need(root != c.ROOT / 'data' and root.is_relative_to(c.ROOT / 'data') and
        root.parent.is_dir() and not root.exists() and c.path(frame['output']) == producer and
        not c.path(fp['path']).is_relative_to(root), 'Fresh controller root and exact nested producer required')
    value = c.read(frame['plan']); bounds = c.budgets(frame['purpose'])
    c.need(value['purpose'] == frame['purpose'] and canonical(value['budgets']) == canonical(bounds),
           'Fixed enclosing controller budget required')
    run.protect_output(frame, value, root, fp)
    interpreter = c.capture(Path(sys.executable).resolve())[0]
    c.need(value['model']['interpreter'] == interpreter, 'Pinned controller interpreter differs')
    journal = RunJournal(root, kind='build'); watchdog = handle = None
    try:
        run.write(root / 'REQUEST.json', dict(frame=fp, output=str(root), producer_output=str(producer), automatic_retry=False))
        handle = run.contain_process_tree()
        end = started + bounds['outer_seconds']
        watchdog = run.DeadlineWatchdog(end, root / 'DEADLINE.json'); watchdog.__enter__()
        elapsed = time.monotonic() - started
        seconds = int(bounds['outer_seconds'] - elapsed - CONTROL_RESERVE_SECONDS)
        c.need(seconds > 120, 'No outer execution time remains after control/cleanup reserves')
        limits = ProcessLimits(seconds, 4 * 1024 ** 2)
        config = dict(kind='sc05_evidence_first_controller_config_v1', frame_sha256=expected,
            purpose=frame['purpose'], outer_seconds=bounds['outer_seconds'], preflight_seconds=elapsed,
            control_reserve_seconds=CONTROL_RESERVE_SECONDS, limits=limits.payload())
        run.write(root / 'CONFIG.json', config)
        command = [interpreter['path'], '-I', '-B', '-c', run.LAUNCHER, str(c.ROOT), str(c.ROOT / 'src'),
            str(c.ROOT / 'packages/tether/src'), '--frame', fp['path'], '--frame-sha256', expected, '--output', str(producer)]
        run.write(root / 'COMMAND.json', command)
        journal.append('evidence_first_controller_reserved', frame=fp, command=command, limits=limits.payload())
        result = run.process_tools.supervised(command, limits, root)
        c.need(result.returncode == 0, 'Controller failed; automatic replay is forbidden')
        validate_success_report(result.supervision, limits, len(result.stdout), len(result.stderr))
        c.need(not any((producer / name).exists() for name in
            ('FAILURE.json', 'DEADLINE.json', 'FINALIZATION-FAILED.json', 'repair-DEADLINE.json', 'removal-DEADLINE.json')),
            'Controller failure marker dominates completion')
        rp = c.capture(producer / 'ROOT-RECEIPT.json')[0]; receipt = c.read(rp)
        c.need(set(receipt) == {'kind', 'status', 'frame_sha256', 'files'} and
            receipt['kind'] == 'sc05_evidence_first_root_receipt_v1' and
            receipt['status'] == 'evidence_first_execution_complete' and receipt['frame_sha256'] == expected and
            canonical(receipt['files']) == canonical(inventory(producer, omit=('ROOT-RECEIPT.json',),
                seconds=max(.001, end - time.monotonic()))), 'Complete controller byte inventory required')
        terminal = c.read(receipt['files']['COMPLETE.json'])
        c.need(terminal['status'] == 'evidence_first_execution_complete' and
            c.finite(terminal['wall_seconds'], 'Controller wall time') <= result.supervision['execution_elapsed_seconds'],
            'Controller wall time must fit its observed process lifetime')
        c.capture(fp['path'], fp)
        c.need(time.monotonic() < end, 'Outer controller finalization exceeded its budget')
        execution = dict(root=str(producer), receipt_sha256=rp['sha256'])
        complete = dict(kind='sc05_evidence_first_controller_terminal_v1', status='complete', producer=execution,
            frame=fp, wall_seconds=time.monotonic() - started, provider_cost_usd=0,
            automatic_retry=False, scientific_scoring_performed=False)
        run.write(root / 'COMPLETE.json', complete)
        journal.append('evidence_first_controller_completed', terminal_sha256=c.fingerprint(complete)); journal.close()
        files = inventory(root, omit=('RECEIPT.json',), seconds=max(.001, end - time.monotonic()))
        c.need(time.monotonic() < end, 'Outer controller receipt exceeded its budget')
        sealed = run.write(root / 'RECEIPT.json', dict(kind='sc05_evidence_first_controller_receipt_v1',
            status='complete', frame_sha256=expected, files=files))
        return freeze(dict(execution, controller=dict(root=str(root), receipt_sha256=sealed['sha256'])))
    except BaseException as error:
        run._preserve_failure(root, error, stage_name='outer_controller', journal=journal,
            wall_seconds=time.monotonic() - started, producer_output=str(producer))
        raise
    finally:
        actions = [('Controller journal close', journal.close)]
        if watchdog is not None: actions.append(('Controller watchdog close', lambda: watchdog.__exit__(None, None, None)))
        run._cleanup(actions)
        _ = handle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frame', type=Path, required=True)
    parser.add_argument('--frame-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(encode(launch(args.frame, args.frame_sha256, output=args.output)))


if __name__ == '__main__':
    main()
