# BG01 historical preservation and old-version smoke

`PRESERVATION-20261102T192818Z.json` passes 196 checks. The accompanying
`PRESERVATION-20261102T192818Z-READBACK.json` checks the retained success states and
rehashes all 110 installed wheel payloads after the fresh demo.

- The qualified TETHER 0.5.0 wheel retains Q02's
  `b28f2680c675b6266c6ea6cc9cfd2002191af9f7d20396b5b2ec629a9909f8d8` hash.
- All 66 old engine Python source pins match the earlier runtime inventory.
  The old engine wheel matches its exact member inside the unchanged P09 release;
  installed TETHER and engine payloads match their wheels.
- The P09, TETHER 0.4.0 and corrected TETHER 0.5.0 archive hashes match their release
  authorities. The original TETHER and corrected working-paper PDFs, plus the
  corrected qualification record, retain their expected hashes.
- `Start-DownloadBatch.ps1`, `Watch-DownloadBatch.ps1`, `Get-DownloadStatus.ps1`
  and `Sync-DownloadCatalog.ps1` match tracked baseline `114fecf`; tracked paper
  files are unchanged. The separately authorized CE01 verifier correction is
  explicitly outside this preserved worker/monitor list.
- Current monitor configuration says disabled, with null process/session IDs.
  This is a configuration observation, not an attestation of historical or live
  process state.

One new offline demonstration used
`data/cache/tether-050-qualified-build/env/Scripts/python.exe -I -B`, from a fresh
ignored directory. TETHER 0.5.0 / AsOf 0.3.11 imported from that installed
environment. The demo completed; subsequent externally anchored verification
returned source-inclusive semantic verification and matching old-version code.
The receipt is
`4e6ad7f38aa5cfee403b95168d91b522f3b196f18c15045ddc319311529d7fe6`.

This establishes that the retained environment remains usable within its original
version-specific scope. It does not backport CE01–CE03, qualify scientific results,
or imply that old software lacks the newly identified defects. No old run was
restarted or rewritten; no new wheels were built. Protected human returns and
clinical adjudicated outcome payloads were not accessed. No model, network,
download or paid-provider action occurred.

`check_preservation.py` is the retained checker and fresh-demo recipe;
`validate_readback.py` checks the produced record without invoking another demo.
