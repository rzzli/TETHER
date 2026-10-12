#Requires -Version 7.0
param([string]$DataRoot = 'E:\projects_data\drug_target_agents_data')
$ErrorActionPreference = 'Stop'
$manifestRoot = Join-Path $DataRoot 'manifests'
$states = @(Get-ChildItem -LiteralPath $manifestRoot -Filter '*-state.json' -File -ErrorAction SilentlyContinue)
$rows = foreach ($stateFile in $states) {
    $readArgs = @{Depth=100}
    if ((Get-Command ConvertFrom-Json).Parameters.ContainsKey('DateKind')) { $readArgs.DateKind = 'String' }
    $state = Get-Content -LiteralPath $stateFile.FullName -Raw | ConvertFrom-Json @readArgs
    $processAlive = [bool](Get-Process -Id $state.process_id -ErrorAction SilentlyContinue)
    $effective = if ($state.status -eq 'running' -and -not $processAlive) { 'not_running_or_interrupted' } else { $state.status }
    [pscustomobject]@{
        batch_id=$state.batch_id; status=$effective; recorded_status=$state.status; process_id=$state.process_id; process_alive=$processAlive
        completed_files=$state.completed_files; total_files=$state.total_files; failed_files=$state.failed_files
        completed_gib=[math]::Round($state.completed_bytes / 1GB,3); planning_upper_gib=[math]::Round($state.planning_upper_bytes / 1GB,3)
        updated_at_utc=$state.updated_at_utc
        errors=@($state.results | Where-Object status -eq 'failed' | Select-Object dataset_id,error)
    }
}
$rows | ConvertTo-Json -Depth 6
