param([string]$OutputPath = (Join-Path $PSScriptRoot 'access-audit.json'))
$ErrorActionPreference = 'Stop'
$auditCache = Join-Path $env:TEMP 'AsOf-feasibility-2026-10-09'
New-Item -ItemType Directory -Path $auditCache -Force | Out-Null
$auditHeaders = @{ 'User-Agent' = 'AsOf-feasibility-review' }
$checks = @()
$codeRoot = 'https://raw.githubusercontent.com/harrisongzhang/TheVirtualBiotech/71f9da68c95c5ee0ef4c1d9b8f45f10693de022d/'
$sourcePaths = @('src/agents/registry.py', 'src/data/loader.py', 'src/mcp_servers/association_mcp/tools.py', 'src/mcp_servers/clinicaltrials_mcp/tools.py', 'src/mcp_servers/genetics_mcp/tools.py', 'datasets/clinical_trials/clinical_trial_labels_reconciled.csv')
foreach ($sourcePath in $sourcePaths) {
    $sourceUrl = $codeRoot + $sourcePath
    $cachePath = Join-Path $auditCache ($sourcePath.Replace('/', '__'))
    try {
        Invoke-WebRequest -Uri $sourceUrl -Headers $auditHeaders -OutFile $cachePath -UseBasicParsing -TimeoutSec 40
        $checks += [pscustomobject]@{ url=$sourceUrl; status=200; bytes=(Get-Item -LiteralPath $cachePath).Length; sha256=(Get-FileHash -LiteralPath $cachePath -Algorithm SHA256).Hash; cache_file=$cachePath }
    } catch { $checks += [pscustomobject]@{ url=$sourceUrl; status='failed'; error=$_.Exception.Message } }
}
$probeUrls = @(
    'https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/',
    'https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/',
    'https://ukbiobank.opendata.sagebase.org.s3.amazonaws.com/?list-type=2&max-keys=1',
    'https://s3.amazonaws.com/ukbiobank.opendata.sagebase.org?list-type=2&max-keys=1',
    'https://www.ebi.ac.uk/eqtl/Data_access/',
    'https://www.ebi.ac.uk/eqtl/License/',
    'https://aact.ctti-clinicaltrials.org/downloads/snapshots?type=flatfiles',
    'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=EXT_ID:38632401%20AND%20SRC:MED&format=json&pageSize=1'
)
foreach ($probeUrl in $probeUrls) {
    try {
        $response = Invoke-WebRequest -Uri $probeUrl -Headers $auditHeaders -UseBasicParsing -TimeoutSec 30
        $cachePath = Join-Path $auditCache ('probe-' + $checks.Count + '.txt')
        [IO.File]::WriteAllText($cachePath, $response.Content)
        $checks += [pscustomobject]@{ url=$probeUrl; status=[int]$response.StatusCode; content_type=[string]$response.Headers['Content-Type']; response_characters=$response.Content.Length; cache_file=$cachePath }
    } catch {
        $responseStatus = $null
        if ($_.Exception.Response) { $responseStatus = [int]$_.Exception.Response.StatusCode }
        $checks += [pscustomobject]@{ url=$probeUrl; status=$responseStatus; error=$_.Exception.Message }
    }
}
$labelPath = Join-Path $auditCache 'datasets__clinical_trials__clinical_trial_labels_reconciled.csv'
$labelSummary = $null
if (Test-Path -LiteralPath $labelPath) {
    $labelRows = @(Import-Csv -LiteralPath $labelPath)
    $labelIds = [Collections.Generic.HashSet[string]]::new()
    foreach ($labelRow in $labelRows) { $null = $labelIds.Add($labelRow.nct_id) }
    $labelSummary = [pscustomobject]@{ rows=$labelRows.Count; columns=@($labelRows[0].PSObject.Properties.Name); unique_nct_ids=$labelIds.Count; primary_endpoint_counts=@($labelRows | Group-Object primary_endpoint_result | Select-Object Name,Count); phase2_progression_counts=@($labelRows | Group-Object phase2_progression | Select-Object Name,Count); phase_counts=@($labelRows | Group-Object phase | Select-Object Name,Count); status_counts=@($labelRows | Group-Object status | Select-Object Name,Count); rows_with_safety_stop_category=@($labelRows | Where-Object { $_.virtualbiotech_stop_reason_categories -match 'Safety or side effects' }).Count }
}
$result = [pscustomobject]@{ review_date='2026-10-09'; scope='Small read-only unauthenticated access probes and pinned Virtual Biotech source/label inspection. No agent execution or statistical-genetics analysis.'; virtual_biotech_commit='71f9da68c95c5ee0ef4c1d9b8f45f10693de022d'; checks=$checks; label_summary=$labelSummary }
$result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
$result | ConvertTo-Json -Depth 8
