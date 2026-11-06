# Reproduce the SC04 analysis

Run from the repository root with the qualified Python3.11 interpreter and matching source bytes. Original datasets, model-run captures and frozen inputs remain external or ignored; Git alone is insufficient.

The command reads completed captures and performs no new inference or download. Use a fresh output directory. Preserve the printed receipt hash outside the output tree.

```powershell
python -I -B experiments/litqa_analysis/run.py execute `
  --primary-root "D:\Projects\drug_target_agents\data\cache\sc04-controller-qualification-attempt01" --primary-root-sha256 8de520bfdef4dbe7b6363aeb962b8c4bb453adc475297aca2fa08d88e7c10cf0 `
  --supplied-root "D:\Projects\drug_target_agents\data\cache\sc04-supplied-controller-qualification-attempt01" --supplied-root-sha256 f9dd1f8b8d0a560730d0450cec03647ec8adcba5d23e0836c16e6af03c1cf19c `
  --fictional `
  --output data/benchmark/litqa_comparison/analysis-NEW-ATTEMPT --seconds 120
```

Then run root acceptance with the new receipt and the current retained regression record:

```powershell
python -I -B planning/review-assets/tether-semantic-20261106/sc04/accept_analysis.py `
  --analysis <completed-analysis-path> --analysis-sha256 <externally-saved-receipt-sha256> `
  --controls "D:\Projects\drug_target_agents\planning\review-assets\tether-semantic-20261106\sc04\analysis-controls-attempt12\QUALIFICATION.json" --controls-sha256 be657fcdeac1c1f8591b84a23120435d07b99ba56b806be41ba4037565fc4142 `
  --fictional `
  --output planning/review-assets/tether-semantic-20261106/sc04/acceptance-NEW-ATTEMPT
```

For production, both complete source-inclusive runs are required, including the separately labelled supplied-source diagnostic and the original199-question frozen evaluator inputs. Fictional mode accepts only the two retained fictional roots and never substitutes for production.

The analysis CLI has a supervised worker deadline and retained failure logs. This acceptance utility bounds file sizes, inventory counts and traversal duration but cannot preempt blocking OS I/O. A failed attempt must be inspected and preserved; no command resumes or retries it automatically.
