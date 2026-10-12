param([string]$OutputPath = (Join-Path $PSScriptRoot 'capacity-planning.json'))
$ErrorActionPreference = 'Stop'
function Get-AucVariance([double]$Auc, [double]$Positives, [double]$Negatives) {
    $q1 = $Auc / (2 - $Auc)
    $q2 = 2 * $Auc * $Auc / (1 + $Auc)
    return ($Auc * (1 - $Auc) + ($Positives - 1) * ($q1 - $Auc * $Auc) + ($Negatives - 1) * ($q2 - $Auc * $Auc)) / ($Positives * $Negatives)
}
$variance0 = Get-AucVariance 0.65 80 320
$variance1 = Get-AucVariance 0.70 80 320
$scenarios = foreach ($estimatorCorrelation in @(0.3, 0.5, 0.8)) {
    $differenceVariance = $variance0 + $variance1 - 2 * $estimatorCorrelation * [math]::Sqrt($variance0 * $variance1)
    $approximateN = 400 * $differenceVariance * [math]::Pow(1.644853626951 + 0.841621233573, 2) / [math]::Pow(0.05, 2)
    [pscustomobject]@{ auc_estimator_correlation=$estimatorCorrelation; se_auc_difference_N400=[math]::Sqrt($differenceVariance); independent_pairs_80pct_power=[math]::Ceiling($approximateN); pairs_with_design_effect_2=[math]::Ceiling(2 * $approximateN) }
}
$result = [pscustomobject]@{
    review_date='2026-10-09'
    method='Illustrative Hanley-McNeil AUC variance with an assumed covariance between paired AUC estimators; normal approximation and 1/N scaling. This is not a pilot power simulation.'
    reference='https://doi.org/10.1148/radiology.143.1.7063747'
    assumptions=[pscustomobject]@{ baseline_auc=0.65; alternative_auc=0.70; prevalence=0.20; alpha_one_sided=0.05; power=0.80; starting_N=400; estimator_correlation_is_not_raw_score_correlation=$true }
    scenarios=@($scenarios)
    limitations=@('No observed pilot predictions or eligible label counts.', 'No empirical cluster structure, censoring or co-primary Brier-score power.', 'Design effect 2 is a sensitivity assumption.', 'The finite-sample approximation is not the registered analysis.')
}
$result | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
$result | ConvertTo-Json -Depth 6
