# Independent BG05 reconstruction

This directory contains an independently written standard-library reader. It does not import Inspect, the production controller, the equal-policy validators or their aggregation helpers. It does not dispatch models, providers, workers or recovery attempts.

`reconstruct.py` checks the external stage/freeze anchors, complete output inventory, frozen input/code proofs, the nine order-rotated worker recipes and receipts, all case chains, native sample/candidate/score joins, all-scheduled policy counts and recorded resources. Native pipeline completion is kept separate from the conformity of a sealed policy result. The oracle is trusted normative input; the reader does not reimplement all biomedical admission rules. Timings are independently aggregated from sealed measurements, not remeasured.

`runtime_reconstruct.py` separately reconstructs ordered reservations, dispatches, measured versus estimated usage, exact provider payloads, committed-claim order and source-row identity for the bounded scripted witnesses. It checks original packet rows against admitted fingerprints and claims, not a generalized therapeutic scheduler. Additional process interruption/concurrency witnesses require their own anchored outer reports; no result is inferred from an absent receipt.

Run the completed-stage reader only after receiving external final hashes:

```powershell
python -B reconstruct.py --stage STAGE_ROOT --seal-sha256 EXTERNAL_STAGE_SHA --freeze FROZEN_JSON --freeze-sha256 EXTERNAL_FREEZE_SHA --output FRESH_REPORT_JSON
```

The output must be fresh. A failure does not correct, omit or rerun a case. Capture stdout/stderr in a fresh log and retain the failing analyzer attempt.

Qualification consists of 15 fictional controls, with first failing evidence and subsequent successful logs retained. The controls cover tampering, identity substitution, missing/error denominators, bool/null distinctions, native unscored NaN, native ZIP/JSON parsing, attachment references, accounting contradictions and duplicate claims. `FICTIONAL-NATIVE-JOINS-03.log` additionally checks two actual-format fictional Inspect cases. Earlier attempts failed because the ad hoc probe first zipped stored sample order and then lacked attachment resolution; neither failure was a production defect.

`FICTIONAL-STAGE-01.json` then passed complete nine-batch reconstruction: 18 scheduled invented cases, all case/worker/parent receipts and chains, all three native logs, frozen input/code hashes, output inventory and every published primary count/case projection agreed. Its SHA256 is `c7e3f8deb600b7955b4280efeb24e71732365208946906ac0ab63db493ef59f2`. Source verification completed while implementation files were held; the authorized prospective controller optimization and additional process witnesses follow this checkpoint without rewriting it. Actual 981-cell reconstruction and complete retained runtime-witness analysis remain pending.

Original production code and benchmark outputs remain untouched. All reports must distinguish finite authored policy conformance, exercised execution invariants and scientific validity.
