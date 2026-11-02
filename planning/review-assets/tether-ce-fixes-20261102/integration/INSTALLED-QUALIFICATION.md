# Installed release qualification — BG01 component pass

**Installed qualification passes; BG01 remains pending a clean full gate.**
This record covers AsOf 0.3.12 and TETHER 0.5.1 on Windows. It does not claim
aggregate-stage completion, benchmark performance, biological validity or public
release readiness.

The retained attempt is
`data/cache/tether-051-installed-qualification-attempt01/QUALIFICATION.json`,
SHA-256 `6ea45e6f05a4b6702a44c81f04a45813b837c88b9313fd7f1f0b66f941531a79`.
The [compact index](INSTALLED-QUALIFICATION-INDEX.json) pins 51 local artifacts:
qualification/control files, both wheels, all 28 command streams, run results,
receipts and success/failure journals. Large outputs and the environment remain
ignored; no originals were copied into this tracked report.

- All **14 commands** returned their expected outcomes: 13 exit 0 and the
  deliberately invalid unused-input case exit 2. All command-log hashes and the
  **31-event qualification hash chain** rechecked successfully.
- Both offline wheels were built from a new minimal context, preserving the
  relative core/facade layout. **115 copied inputs** remain byte-identical to
  their checkout originals; neither build used the checkout build directory.
  The qualification truthfully records the parent gate as `not_asserted` and
  aggregate integration as pending.
- Core wheel/checkout/installed namespaces agree on **66 Python files and 26
  JSON resources**; facade namespaces agree on **18 Python files**. Wheel
  RECORD hashes were checked by the qualifier, and this review independently
  rehashed namespace members, copied inputs, installed files and current sources.
- The installed-source probe reports `isolated=1`, package roots inside the new
  environment's `Lib/site-packages`, and no checkout import path. Every installed
  probe/task/verification command uses that environment's Python with `-I`.
  Checkout imports were used only by the explicitly pinned fictional-fixture
  producer. Core run receipts also match the exact installed core code inventory.
- Direct AsOf and TETHER demos both pass externally anchored, source-inclusive
  semantic verification. The valid schema-2 policy run verifies **four supplied
  inputs**. The invalid unused raw node fails specifically on receipt-time
  inconsistency during `artifact_policy_preflight`, with no engine dispatch,
  engine directory or success receipt.

[index_installed_qualification.py](index_installed_qualification.py) contains the
read-only evidence review and writes a fresh index without rerunning any build,
model, task or verification CLI. Its digest is retained in the index. These
checks are software integration evidence from fictional inputs; the full gate
and parent completion audit remain separate requirements.
