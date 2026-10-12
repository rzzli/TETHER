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
        if ($receipt.status -ne 'completed' -or $receipt.url -ne $record.url -or $receipt.relative_path -ne $record.relative_path) { throw 'Receipt/source/path mismatch.' }
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
if ($OutputPath) {
    $parent=[IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($OutputPath));New-Item -ItemType Directory -Path $parent -Force | Out-Null
    $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding utf8NoBOM
}
$result | ConvertTo-Json -Depth 8
if (-not $result.complete) { exit 2 }
