param(
    [string]$ProjectRoot = 'D:\Projects\drug_target_agents',
    [string]$DataRoot = 'E:\projects_data\drug_target_agents_data'
)
$ErrorActionPreference = 'Stop'
$catalogPath = Join-Path $ProjectRoot 'data\catalog\sources.json'
$readArgs = @{Depth=100; AsHashtable=$true}
if ((Get-Command ConvertFrom-Json).Parameters.ContainsKey('DateKind')) { $readArgs.DateKind = 'String' }
$catalog = Get-Content -LiteralPath $catalogPath -Raw | ConvertFrom-Json @readArgs
$clientZone = [TimeZoneInfo]::FindSystemTimeZoneById('Pacific Standard Time')
$snapshotDate = [TimeZoneInfo]::ConvertTime([DateTimeOffset]::UtcNow,$clientZone).ToString('yyyy-MM-dd')
$catalog.last_updated = $snapshotDate
$catalog.scope = 'Data requirements inventory with authorized initial public acquisition snapshots. Resumable transport is implemented; scientific ingestion, model execution and benchmark validation are not.'
$catalog.status_definitions.collection_status = @('planned','queued','downloading','partial','collected','failed','blocked')
$queueRoot = Join-Path $ProjectRoot 'data\manifests\private'
$summary = [Collections.Generic.List[object]]::new()
foreach ($queuePath in Get-ChildItem -LiteralPath $queueRoot -Filter '*-queue.json' -File) {
    $queue = Get-Content -LiteralPath $queuePath.FullName -Raw | ConvertFrom-Json @readArgs
    foreach ($group in @($queue.files | Group-Object dataset_id)) {
        $dataset = $catalog.datasets | Where-Object dataset_id -eq $group.Name
        if (-not $dataset) { throw ('Unknown acquisition dataset: ' + $group.Name) }
        $completed = [Collections.Generic.List[object]]::new()
        $partialFiles = 0
        foreach ($file in $group.Group) {
            $receiptPath = Join-Path $DataRoot ('manifests\receipts\' + $file.receipt_id + '.json')
            if (Test-Path -LiteralPath $receiptPath -PathType Leaf) {
                $receipt = Get-Content -LiteralPath $receiptPath -Raw | ConvertFrom-Json @readArgs
                if ($receipt.status -eq 'completed') { $completed.Add($receipt) }
            }
            if (Test-Path -LiteralPath (Join-Path $DataRoot ($file.relative_path + '.partial')) -PathType Leaf) { $partialFiles++ }
        }
        $status = if ($completed.Count -eq $group.Count) { 'collected' } elseif ($completed.Count) { 'partial' } elseif ($partialFiles) { 'downloading' } else { 'queued' }
        $dataset.collection_status = $status
        $dataset['acquisition_snapshot'] = @{
            snapshot_date=$snapshotDate; batch_id=$queue.batch_id; storage_role='external_bulk_E'
            expected_files=$group.Count; completed_files=$completed.Count; in_progress_files=$partialFiles
            completed_bytes=($completed | Measure-Object bytes -Sum).Sum
            release_ids=@($group.Group.release_id | Sort-Object -Unique)
            relative_paths=@($group.Group.relative_path)
            status=$status; authority='Live receipts/state under the authorized E storage root; catalog is a point-in-time snapshot.'
            integrity_note='Byte/format signatures and SHA-256 receipts; publisher checksum only where supplied. Parsing and scientific validation remain not_run.'
        }
        if ($completed.Count) {
            $dataset.temporal.unknowns = @($dataset.temporal.unknowns | Where-Object { $_ -ne 'No acquired artifact in this scaffold.' })
            $dataset.blockers = @($dataset.blockers | ForEach-Object { $_.Replace('No full payload was downloaded, parsed or validated; selected release/date and transformation coverage remain unverified.','Raw acquisition is recorded; source-date, schema/field transformation and scientific validation remain unverified.') })
            $dataset.verification.level = 'sample_inspected'
            $dataset.verification.checked_at = $snapshotDate
            $dataset.verification.evidence = @($dataset.verification.evidence | Where-Object { $_.kind -ne 'acquisition_receipts' }) + @{kind='acquisition_receipts';checked_at=$snapshotDate;workspace_path='data/manifests/public/2026-10-10-acquisition-summary.json';result='Completed-file counts and integrity receipts recorded; no field/schema or scientific validation claim.'}
        }
        if ($dataset.dataset_id -eq 'hgnc_symbols') { $dataset.temporal.classification = 'contemporary_only'; $dataset.temporal.eligibility_note = 'A checksum-backed retrieval snapshot collected October 10; not verified as an earlier-origin gene annotation.'; $dataset.profile_policy.historical_benchmark = 'excluded' }
        $summary.Add([pscustomobject]@{dataset_id=$dataset.dataset_id;batch_id=$queue.batch_id;status=$status;expected_files=$group.Count;completed_files=$completed.Count;completed_bytes=($completed | Measure-Object bytes -Sum).Sum;in_progress_files=$partialFiles})
    }
}
$catalog | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $catalogPath -Encoding utf8NoBOM
$public = [pscustomobject]@{date=$snapshotDate;updated_at_utc=[DateTimeOffset]::UtcNow.ToString('o');timezone='America/Los_Angeles';scope='Authorized initial public acquisition; point-in-time progress snapshot, not scientific validation.';storage_role='external_bulk_E';datasets=@($summary);parsed_products=0;scientifically_validated_products=0;note='Live worker state and source receipts are outside version control. No credentials, label values, signed URLs or private absolute paths are published here.'}
$public | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $ProjectRoot 'data\manifests\public\2026-10-10-acquisition-summary.json') -Encoding utf8NoBOM
$summary | Group-Object status | Select-Object Name,Count | ConvertTo-Json
