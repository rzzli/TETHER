param(
    [Parameter(Mandatory)][string]$QueuePath,
    [string]$DataRoot = 'E:\projects_data\drug_target_agents_data',
    [int]$Concurrency = 4,
    [double]$MinimumFreeGiB = 373,
    [double]$MaximumBatchGiB = 300,
    [string]$StatePath
)
$ErrorActionPreference = 'Stop'
if ($Concurrency -lt 1 -or $Concurrency -gt 8) { throw 'Concurrency must be 1..8.' }
$resolvedRoot = [IO.Path]::GetFullPath($DataRoot).TrimEnd('\')
if ($resolvedRoot -notin @('E:\projects_data\drug_target_agents_data','D:\Projects\drug_target_agents\data')) { throw 'DataRoot must be an explicitly authorized storage root.' }
New-Item -ItemType Directory -Path $resolvedRoot -Force | Out-Null
if ((Get-Item -LiteralPath $resolvedRoot).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Reparse storage root is not supported.' }
$queue = Get-Content -LiteralPath $QueuePath -Raw | ConvertFrom-Json -Depth 100
$records = @($queue.files)
if (-not $records.Count) { throw 'Queue is empty.' }
$batchUpper = ($records | Measure-Object planning_upper_bytes -Sum).Sum
if ($batchUpper -gt $MaximumBatchGiB * 1GB) { throw 'Declared batch exceeds configured size cap.' }
$storageDrive = Get-PSDrive -Name ([IO.Path]::GetPathRoot($resolvedRoot).Substring(0,1))
if ($storageDrive.Free - $batchUpper -lt $MinimumFreeGiB * 1GB) { throw 'The whole batch would cross the free-space reserve.' }
$seenPaths = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($record in $records) {
    if ([IO.Path]::IsPathRooted($record.relative_path)) { throw 'Queue path must be relative.' }
    $target = [IO.Path]::GetFullPath((Join-Path $resolvedRoot $record.relative_path))
    if (-not $target.StartsWith($resolvedRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Queue path leaves storage root.' }
    if (-not $seenPaths.Add($target)) { throw 'Duplicate target path in queue.' }
    $sourceUri = [uri]$record.url
    if ($sourceUri.Scheme -ne 'https' -or $sourceUri.Host -notin @('ftp.ebi.ac.uk','raw.githubusercontent.com','storage.googleapis.com')) { throw 'Unsupported public source host.' }
    if ($null -eq $record.planning_upper_bytes -or $record.planning_upper_bytes -lt 0) { throw 'Every file needs a size bound.' }
}
$receiptsRoot = Join-Path $resolvedRoot 'manifests\receipts'
New-Item -ItemType Directory -Path $receiptsRoot -Force | Out-Null
if (-not $StatePath) { $StatePath = Join-Path $resolvedRoot ('manifests\' + $queue.batch_id + '-state.json') }
$stateFullPath = [IO.Path]::GetFullPath($StatePath)
if (-not $stateFullPath.StartsWith($resolvedRoot + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'State path leaves storage root.' }
$stateParent = [IO.Path]::GetDirectoryName($stateFullPath)
New-Item -ItemType Directory -Path $stateParent -Force | Out-Null
if (Test-Path -LiteralPath $stateFullPath -PathType Leaf) {
    $previousState = Get-Content -LiteralPath $stateFullPath -Raw | ConvertFrom-Json -Depth 100
    if ($previousState.status -eq 'running' -and (Get-Process -Id $previousState.process_id -ErrorAction SilentlyContinue)) { throw 'This batch already has a live worker; inspect status before starting another copy.' }
}
$started = [DateTimeOffset]::UtcNow.ToString('o')
$results = [Collections.Generic.List[object]]::new()
function Write-State([string]$status) {
    $state = [pscustomobject]@{
        batch_id=$queue.batch_id; status=$status; process_id=$PID; started_at_utc=$started; updated_at_utc=[DateTimeOffset]::UtcNow.ToString('o')
        total_files=$records.Count; completed_files=@($results | Where-Object status -eq 'completed').Count
        failed_files=@($results | Where-Object status -eq 'failed').Count
        completed_bytes=($results | Where-Object status -eq 'completed' | Measure-Object bytes -Sum).Sum
        planning_upper_bytes=$batchUpper; minimum_free_gib=$MinimumFreeGiB; concurrency=$Concurrency
        results=@($results)
    }
    $temporaryState = $stateFullPath + '.tmp'
    $state | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $temporaryState -Encoding utf8NoBOM
    Move-Item -LiteralPath $temporaryState -Destination $stateFullPath -Force
}
function Download-One($Record, [string]$Root, [string]$ReceiptsRoot, [double]$FreeReserve) {
    $ErrorActionPreference = 'Stop'
    $target = [IO.Path]::GetFullPath((Join-Path $Root $Record.relative_path))
    $partial = $target + '.partial'
    $receiptPath = Join-Path $ReceiptsRoot ($Record.receipt_id + '.json')
    try {
        if (-not $target.StartsWith($Root + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'Out-of-root target.' }
        $parent = [IO.Path]::GetDirectoryName($target)
        $walk = $parent
        while ($walk -and $walk.StartsWith($Root, [StringComparison]::OrdinalIgnoreCase)) {
            if ((Test-Path -LiteralPath $walk) -and ((Get-Item -LiteralPath $walk).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'Reparse target directory is not supported.' }
            if ($walk -eq $Root) { break }
            $walk = [IO.Path]::GetDirectoryName($walk)
        }
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
        $drive = Get-PSDrive -Name ([IO.Path]::GetPathRoot($target).Substring(0,1))
        if ($drive.Free - $Record.planning_upper_bytes -lt $FreeReserve * 1GB) { throw 'Free-space reserve would be crossed.' }
        $alreadyPresent = Test-Path -LiteralPath $target -PathType Leaf
        if ($alreadyPresent) {
            if (-not (Test-Path -LiteralPath $receiptPath) -and -not $Record.expected_sha256) { throw 'Existing file has no source receipt; refusing to overwrite or assume provenance.' }
            $candidate = $target
        } else {
            $partialComplete = (Test-Path -LiteralPath $partial -PathType Leaf) -and ($null -ne $Record.expected_bytes) -and ((Get-Item -LiteralPath $partial).Length -eq [long]$Record.expected_bytes)
            if (-not $partialComplete) {
                $curlArgs = @('--fail','--silent','--show-error','--location','--retry','3','--retry-all-errors','--retry-delay','2','--connect-timeout','30','--speed-time','120','--speed-limit','1024','--max-time','1800','--max-filesize',([long]$Record.planning_upper_bytes).ToString(),'--limit-rate','20M','--continue-at','-','--output',$partial,$Record.url)
                # Keep native stderr inside this worker so a single transfer error cannot terminate the parent parallel pipeline.
                $savedErrorPreference = $ErrorActionPreference
                $ErrorActionPreference = 'Continue'
                try { $transferMessages = @(& curl.exe @curlArgs 2>&1); $transferExitCode = $LASTEXITCODE }
                finally { $ErrorActionPreference = $savedErrorPreference }
                if ($transferExitCode -ne 0) { throw ('curl transfer failed with exit code ' + $transferExitCode + ': ' + (($transferMessages | ForEach-Object { [string]$_ }) -join ' ')) }
            }
            $candidate = $partial
        }
        $length = (Get-Item -LiteralPath $candidate).Length
        if ($null -ne $Record.expected_bytes -and $length -ne [long]$Record.expected_bytes) { throw 'Exact byte count mismatch.' }
        if ($length -gt [long]$Record.planning_upper_bytes) { throw 'Observed file exceeds the declared size bound.' }
        $formatCheck = 'byte_count_or_bound'
        if ($Record.format -eq 'parquet') {
            if ($length -lt 8) { throw 'Parquet too short.' }
            $stream = [IO.File]::OpenRead($candidate)
            try {
                $header = [byte[]]::new(4); $footer = [byte[]]::new(4)
                $null = $stream.Read($header,0,4); $null = $stream.Seek(-4,[IO.SeekOrigin]::End); $null = $stream.Read($footer,0,4)
                if ([Text.Encoding]::ASCII.GetString($header) -ne 'PAR1' -or [Text.Encoding]::ASCII.GetString($footer) -ne 'PAR1') { throw 'Parquet magic check failed.' }
            } finally { $stream.Dispose() }
            $formatCheck = 'PAR1_header_and_footer_only'
        } elseif ($Record.format -in @('csv','tsv')) {
            $reader = [IO.File]::OpenText($candidate)
            try { $firstLine = $reader.ReadLine() } finally { $reader.Dispose() }
            if ($Record.required_header -and (-not $firstLine -or -not $firstLine.Contains($Record.required_header))) { throw 'Expected delimited-file header missing.' }
            $formatCheck = 'expected_header_only'
        } elseif ($Record.format -eq 'gzip') {
            $stream = [IO.File]::OpenRead($candidate)
            try { if ($stream.ReadByte() -ne 31 -or $stream.ReadByte() -ne 139) { throw 'Gzip header check failed.' } } finally { $stream.Dispose() }
            $formatCheck = 'gzip_header_only'
        }
        $sha = (Get-FileHash -LiteralPath $candidate -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($Record.expected_sha256 -and $sha -ne $Record.expected_sha256.ToLowerInvariant()) { throw 'Expected SHA-256 mismatch.' }
        if ($alreadyPresent -and (Test-Path -LiteralPath $receiptPath)) {
            $oldReceipt = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json
            if ($oldReceipt.url -ne $Record.url -or $oldReceipt.sha256 -ne $sha) { throw 'Existing source receipt/hash mismatch.' }
        }
        if (-not $alreadyPresent) { Move-Item -LiteralPath $partial -Destination $target }
        $checksumOrigin = if ($Record.expected_sha256) { if ($Record.checksum_origin) { $Record.checksum_origin } else { 'unspecified_expected_hash' } } else { 'local_capture_only' }
        $result = [pscustomobject]@{receipt_id=$Record.receipt_id;dataset_id=$Record.dataset_id;release_id=$Record.release_id;relative_path=$Record.relative_path;url=$Record.url;status='completed';bytes=$length;sha256=$sha;expected_hash_verified=[bool]$Record.expected_sha256;publisher_hash_verified=([bool]$Record.expected_sha256 -and $checksumOrigin -eq 'publisher');checksum_origin=$checksumOrigin;format_check=$formatCheck;completed_at_utc=[DateTimeOffset]::UtcNow.ToString('o');cache_hit=$alreadyPresent;parse_status='not_run';scientific_validation='not_run'}
        $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $receiptPath -Encoding utf8NoBOM
        return $result
    } catch {
        return [pscustomobject]@{receipt_id=$Record.receipt_id;dataset_id=$Record.dataset_id;release_id=$Record.release_id;relative_path=$Record.relative_path;url=$Record.url;status='failed';error=$_.Exception.Message;partial_bytes=if (Test-Path -LiteralPath $partial -PathType Leaf) {(Get-Item -LiteralPath $partial).Length} else {0};updated_at_utc=[DateTimeOffset]::UtcNow.ToString('o')}
    }
}
Write-State 'running'
$workerDefinition = 'function Download-One { ' + ${function:Download-One}.ToString() + ' }'
try {
    $records | ForEach-Object -Parallel {
        Invoke-Expression $using:workerDefinition
        Download-One $_ $using:resolvedRoot $using:receiptsRoot $using:MinimumFreeGiB
    } -ThrottleLimit $Concurrency | ForEach-Object {
        $results.Add($_)
        Write-State 'running'
        Write-Host ('{0}/{1} processed; {2} {3}' -f $results.Count,$records.Count,$_.status,$_.dataset_id)
    }
    $finalStatus = if (@($results | Where-Object status -eq 'failed').Count) { 'completed_with_failures' } else { 'completed' }
    Write-State $finalStatus
} catch {
    Write-State 'interrupted'
    throw
}
