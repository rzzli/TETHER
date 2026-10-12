#Requires -Version 7.0
param(
    [string]$DataRoot = 'E:\projects_data\drug_target_agents_data',
    [Parameter(Mandatory)][string]$QueuePath,
    [ValidateRange(1,60)][int]$IntervalMinutes = 15,
    [switch]$ValidateOnly
)
$ErrorActionPreference = 'Stop'
$queueFullPath = [IO.Path]::GetFullPath($QueuePath)
$queue = Get-Content -LiteralPath $queueFullPath -Raw | ConvertFrom-Json -Depth 100
$BatchId = [string]$queue.batch_id
if ($BatchId -notmatch '^[a-zA-Z0-9_-]+$') { throw 'Invalid explicit queue batch identity.' }
if ($ValidateOnly) { @{batch_id=$BatchId;queue_path=$queueFullPath;monitor_started=$false} | ConvertTo-Json; return }
$root = [IO.Path]::GetFullPath($DataRoot).TrimEnd('\')
$statePath = Join-Path $root ('manifests\' + $BatchId + '-state.json')
$monitorPath = Join-Path $root ('manifests\' + $BatchId + '-monitor.json')
$historyPath = Join-Path $root ('manifests\' + $BatchId + '-monitor-history.jsonl')
$readArgs = @{Depth=100}
if ((Get-Command ConvertFrom-Json).Parameters.ContainsKey('DateKind')) { $readArgs.DateKind = 'String' }
$previousIdentity = $null
while ($true) {
    $checked = [DateTimeOffset]::UtcNow
    $observation = $null
    try {
        $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json @readArgs
        $process = Get-CimInstance Win32_Process -Filter ('ProcessId = ' + [int]$state.process_id) -ErrorAction Stop
        $identityMatches = $process -and $process.CommandLine -like '*Start-DownloadBatch.ps1*' -and $process.CommandLine.Contains($queueFullPath, [StringComparison]::OrdinalIgnoreCase)
        $identity = if ($identityMatches) { [pscustomobject]@{pid=$process.ProcessId;created_at_utc=$process.CreationDate.ToUniversalTime().ToString('o')} } else { $null }
        if ($identity) { $previousIdentity = $identity }
        $effective = if ($state.status -eq 'running' -and -not $identityMatches) { 'worker_absent_or_identity_mismatch' } else { $state.status }
        $observation = [pscustomobject]@{
            batch_id=$BatchId; checked_at_utc=$checked.ToString('o'); interval_minutes=$IntervalMinutes
            status=$effective; recorded_status=$state.status; worker_identity=$identity
            completed_files=$state.completed_files; total_files=$state.total_files; failed_files=$state.failed_files
            completed_bytes=$state.completed_bytes; updated_at_utc=$state.updated_at_utc
            errors=@($state.results | Where-Object status -eq 'failed' | Select-Object dataset_id,relative_path,error)
            next_check_at_utc=$checked.AddMinutes($IntervalMinutes).ToString('o')
        }
    } catch {
        # An observation error is not evidence that the worker stopped. Retain identity and re-observe without restarting it.
        $observation = [pscustomobject]@{
            batch_id=$BatchId; checked_at_utc=$checked.ToString('o'); interval_minutes=$IntervalMinutes
            status='observation_failed'; error=$_.Exception.Message; last_confirmed_worker_identity=$previousIdentity
            next_check_at_utc=$checked.AddMinutes($IntervalMinutes).ToString('o')
        }
    }
    $observation | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath ($monitorPath+'.tmp') -Encoding utf8NoBOM
    Move-Item -LiteralPath ($monitorPath+'.tmp') -Destination $monitorPath -Force
    $observation | ConvertTo-Json -Depth 8 -Compress | Add-Content -LiteralPath $historyPath -Encoding utf8NoBOM
    $observation | ConvertTo-Json -Depth 8 -Compress | Write-Output
    if ($observation.status -in @('completed','completed_with_failures','interrupted','worker_absent_or_identity_mismatch')) { break }
    $deadline = $checked.AddMinutes($IntervalMinutes)
    while ([DateTimeOffset]::UtcNow -lt $deadline) {
        $remaining = ($deadline-[DateTimeOffset]::UtcNow).TotalSeconds
        Start-Sleep -Seconds ([math]::Min(60,[math]::Max(1,[int][math]::Ceiling($remaining))))
    }
}
