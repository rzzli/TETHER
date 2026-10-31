# Accounting diagnostic v2 — corrected preparation, not execution

The v2 helper and protocol are prepared and frozen for root/independent review.
**No diagnostic worker or Windows Job/process API has run.** The original v1
helper/protocol/preparation and [three-finding peer hold](JOB-ACCOUNTING-DIAGNOSTIC-PEER-REVIEW-v1.md)
remain unchanged and unexecuted. The original sixteen OS-probe artifacts and
report `2b35761da99681ffb84995590c8199f58d45289167665905557df01ba1ce0f38`
are preserved.

| New artifact | SHA256 |
|---|---|
| `probe_job_accounting_v2.py` | `a6c91bea13a42b9c53b2c5296ff6d2bba687e34da062f1b599fc8e3ad51dff1d` |
| `JOB-ACCOUNTING-DIAGNOSTIC-PROTOCOL-v2.json` | `01aeec348630d0b1adfc76fd41ffc696e41e01e61f27cba9de84d970ba767243` |

The protocol binds **34 files**, including all 27 original file pins, the
preserved v1 hold and the new pure regression helper/report. Preparation made
zero dispatches or diagnostic Windows API calls; its new output remains absent
at `data/cache/r09-job-accounting-diagnostic-v2-20261028T184111Z`.

Three corrections address the peer findings:

- Worker `started` and `ready` markers use fsynced pending files followed by
  Windows non-overwriting, same-directory rename. Parent assignment publication
  remains atomic. An incomplete marker is not exposed under its public name.
- stdout/stderr use independent pipe drainers with `read1`, a 64 KiB retained
  cap each, observed/retained/truncated/error accounting and an abort event.
  All parent marker, metadata, snapshot and steady-wait checkpoints observe
  that event, routing overflow/error to owned-job/worker cleanup. Capture
  threads/pipes/files are finalized and their byte counts checked before a
  successful result. The whole-child cap includes capture cleanup.
- SDK excerpts use physical LF lines after newline normalization rather than
  `splitlines()`, which counted the SDK's embedded formfeeds. Exact typedef
  landmarks are asserted; the enum excerpt now includes class 9. Whole SDK
  hashes and runtime layout declarations are unchanged.

[The six pure regression checks](JOB-ACCOUNTING-V2-FAULT-CHECKS.json) passed:
interrupted pending marker remains invisible; complete publication preserves an
existing destination; below-cap capture matches bytes; overflow retains exactly
65,536 bytes and signals abort; read failure retains partial accounting and
signals abort; physical SDK line anchors include the expected class-9 entry.
These used files and in-memory streams, with zero child/network/Windows Job API
activity. They do not claim actual process-termination or kernel-query results.

Scope stays **one hidden direct-base sleep worker, five fixed snapshots,
sixteen job-returned PIDs maximum, eight seconds for the whole child and 45
seconds overall with five seconds reserved for finalization**. Only read-only
public image/creation metadata queries are allowed. Own PPID comes from its
strict marker; unexpected PPIDs remain null. There is no global process
enumeration, private process API, elevation, native target, model/GGUF access,
new source fetch or additional runtime fixture. Raw accounting differences are
retained without a causal or universal-containment claim.

After separate exact-hash root authorization, the proposed command is:

```powershell
& 'C:\Users\zzric\AppData\Roaming\uv\python\cpython-3.11.15-windows-x86_64-none\python.exe' -I -B 'D:\Projects\drug_target_agents\planning\review-assets\recovery-step9-native-recognition-20261028\probe_job_accounting_v2.py' --execute 01aeec348630d0b1adfc76fd41ffc696e41e01e61f27cba9de84d970ba767243
```

No command in this document has been executed. Accounting qualification remains
held pending root/peer review, a separately authorized finite diagnostic and
independent review of its retained observations.
