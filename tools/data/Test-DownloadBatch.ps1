#Requires -Version 7.0
param(
    [Parameter(Mandatory)][string]$QueuePath,
    [string]$DataRoot = 'E:\projects_data\drug_target_agents_data',
    [string]$OutputPath
)
$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($DataRoot).TrimEnd('\')
$readArgs = @{Depth=100}
if ((Get-Command ConvertFrom-Json).Parameters.ContainsKey('DateKind')) { $readArgs.DateKind = 'String' }
$queue = Get-Content -LiteralPath $QueuePath -Raw | ConvertFrom-Json @readArgs
$records = @($queue.files)
if (-not $records.Count) { throw 'Empty verification scope.' }

function Assert-FreshReportDestination([string]$Path) {
    # Reject link aliases, including dangling links, before touching a report.
    # Exclusive publication below remains necessary for concurrent writers.
    $cursor = $Path
    while ($cursor) {
        $item = Get-Item -LiteralPath $cursor -Force -ErrorAction Ignore
        if ($null -ne $item) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw 'Report destination must not traverse a reparse point.'
            }
            if ($cursor -eq $Path) { throw 'Report destination already exists; use a fresh path.' }
            if (-not $item.PSIsContainer) { throw 'Report parent is not a directory.' }
        }
        $cursor = [IO.Path]::GetDirectoryName($cursor)
    }
}

$reportPath = $null
if ($OutputPath) {
    $reportPath = [IO.Path]::GetFullPath($OutputPath)
    $reportRoot = [IO.Path]::GetPathRoot($reportPath)
    if ($reportPath.Substring($reportRoot.Length).Contains(':')) {
        throw 'Report destination must not use an alternate data stream.'
    }
    $protectedPaths = [Collections.Generic.List[string]]::new()
    $protectedPaths.Add([IO.Path]::GetFullPath($QueuePath))
    foreach ($record in $records) {
        # Protect even missing originals/receipts: a failed report must not be
        # mistaken for a newly collected input. Invalid paths remain per-record
        # failures in the verifier below.
        try {
            if ($record.relative_path -is [string]) {
                $protectedPaths.Add([IO.Path]::GetFullPath((Join-Path $root $record.relative_path)))
            }
        } catch { }
        try {
            if ($record.receipt_id -is [string]) {
                $protectedPaths.Add([IO.Path]::GetFullPath((Join-Path $root ('manifests\receipts\'+$record.receipt_id+'.json'))))
            }
        } catch { }
    }
    foreach ($protectedPath in $protectedPaths) {
        if ([string]::Equals($protectedPath, $reportPath, [StringComparison]::OrdinalIgnoreCase)) {
            throw 'Report destination aliases a queue, original or receipt input.'
        }
    }
    Assert-FreshReportDestination $reportPath
}
$failures = [Collections.Generic.List[object]]::new()
$verified = 0
$bytes = [long]0
foreach ($record in $records) {
    $problem = $null
    try {
        if ([IO.Path]::IsPathRooted($record.relative_path)) { throw 'Absolute path in queue.' }
        $path = [IO.Path]::GetFullPath((Join-Path $root $record.relative_path))
        if (-not $path.StartsWith($root+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Path outside verification root.' }
        if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw 'Queued file is missing.' }
        $receiptPath = Join-Path $root ('manifests\receipts\'+$record.receipt_id+'.json')
        if (-not (Test-Path -LiteralPath $receiptPath -PathType Leaf)) { throw 'Source receipt is missing.' }
        $receipt = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json @readArgs
        if ($receipt.status -cne 'completed' -or
            $receipt.receipt_id -cne $record.receipt_id -or
            $receipt.dataset_id -cne $record.dataset_id -or
            $receipt.release_id -cne $record.release_id -or
            $receipt.url -cne $record.url -or $receipt.relative_path -cne $record.relative_path) {
            throw 'Receipt/dataset/release/source/path identity mismatch.'
        }
        $length = (Get-Item -LiteralPath $path).Length
        if ($length -ne [long]$receipt.bytes) { throw 'Receipt byte count mismatch.' }
        if ($null -ne $record.expected_bytes -and $length -ne [long]$record.expected_bytes) { throw 'Exact source byte count mismatch.' }
        if ($length -gt [long]$record.planning_upper_bytes) { throw 'Size bound exceeded.' }
        $sha = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($sha -ne $receipt.sha256.ToLowerInvariant()) { throw 'Current bytes no longer match the source receipt SHA-256.' }
        if ($record.expected_sha256 -and $sha -ne $record.expected_sha256.ToLowerInvariant()) { throw 'Known source SHA-256 mismatch.' }
        if ($record.format -eq 'parquet') {
            if ($length -lt 8) { throw 'Parquet too short.' }
            $stream = [IO.File]::OpenRead($path)
            try {
                $header=[byte[]]::new(4);$footer=[byte[]]::new(4)
                $null=$stream.Read($header,0,4);$null=$stream.Seek(-4,[IO.SeekOrigin]::End);$null=$stream.Read($footer,0,4)
                if ([Text.Encoding]::ASCII.GetString($header) -ne 'PAR1' -or [Text.Encoding]::ASCII.GetString($footer) -ne 'PAR1') { throw 'Parquet signatures invalid.' }
            } finally { $stream.Dispose() }
        } elseif ($record.format -eq 'gzip') {
            $stream=[IO.File]::OpenRead($path)
            try { if ($stream.ReadByte() -ne 31 -or $stream.ReadByte() -ne 139) { throw 'Gzip signature invalid.' } } finally { $stream.Dispose() }
        } elseif ($record.format -in @('csv','tsv') -and $record.required_header) {
            $reader=[IO.File]::OpenText($path)
            try { $header=$reader.ReadLine() } finally { $reader.Dispose() }
            if (-not $header -or -not $header.Contains($record.required_header)) { throw 'Delimited header invalid.' }
        }
        $verified++
        $bytes += $length
    } catch { $problem = $_.Exception.Message }
    if ($problem) { $failures.Add([pscustomobject]@{receipt_id=$record.receipt_id;dataset_id=$record.dataset_id;relative_path=$record.relative_path;problem=$problem}) }
    if (($verified+$failures.Count) % 100 -eq 0) { Write-Host ('Verified {0}/{1}; failures {2}' -f $verified,$records.Count,$failures.Count) }
}
$result=[pscustomobject]@{
    batch_id=$queue.batch_id; checked_at_utc=[DateTimeOffset]::UtcNow.ToString('o'); scope='Every queued file, current bytes, source receipt identity, SHA-256, size and basic format signature.'
    expected_files=$records.Count;verified_files=$verified;failed_files=$failures.Count;verified_bytes=$bytes
    complete=($verified -eq $records.Count -and $failures.Count -eq 0);failures=@($failures)
    limitations='Transport/content integrity only; no scientific/schema/temporal-validity claim.'
}
$resultJson = $result | ConvertTo-Json -Depth 8
if ($reportPath) {
    $parent = [IO.Path]::GetDirectoryName($reportPath)
    $null = [IO.Directory]::CreateDirectory($parent)
    Assert-FreshReportDestination $reportPath
    $temporaryPath = Join-Path $parent ('.verify-report-'+[Guid]::NewGuid().ToString('N')+'.tmp')
    $created = $false
    $stream = $null
    try {
        $stream = [IO.File]::Open($temporaryPath, [IO.FileMode]::CreateNew,
                                 [IO.FileAccess]::Write, [IO.FileShare]::None)
        $created = $true
        $content = [Text.UTF8Encoding]::new($false).GetBytes($resultJson+[Environment]::NewLine)
        $stream.Write($content, 0, $content.Length)
        $stream.Flush($true)
        $stream.Dispose()
        $stream = $null
        # This overload never replaces an existing destination. Only a fully
        # written report becomes visible, and concurrent publishers cannot win
        # by truncating a report or source created since preflight.
        [IO.File]::Move($temporaryPath, $reportPath)
    } finally {
        if ($null -ne $stream) { $stream.Dispose() }
        if ($created -and [IO.File]::Exists($temporaryPath)) { [IO.File]::Delete($temporaryPath) }
    }
}
$resultJson
if (-not $result.complete) { exit 2 }
