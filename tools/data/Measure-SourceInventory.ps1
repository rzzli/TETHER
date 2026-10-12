param(
    [string]$OutputPath = 'D:\Projects\drug_target_agents\data\manifests\public\2026-10-10-download-size-inventory.json'
)
$ErrorActionPreference = 'Stop'
$rootUrls = @(
    'https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/19.11/output/',
    'https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/21.11/output/etl/parquet/',
    'https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/23.12/output/etl/parquet/',
    'https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/25.09/output/'
)
$inventories = foreach ($rootUrl in $rootUrls) {
    $releaseId = if ($rootUrl -match '/platform/([^/]+)/') { $Matches[1] } else { throw 'Invalid release URL' }
    $pending = [Collections.Generic.Queue[string]]::new()
    $pending.Enqueue($rootUrl)
    $visited = [Collections.Generic.HashSet[string]]::new()
    $files = [Collections.Generic.List[object]]::new()
    $failures = [Collections.Generic.List[object]]::new()
    while ($pending.Count -gt 0) {
        $url = $pending.Dequeue()
        if (-not $visited.Add($url)) { continue }
        if ($visited.Count -gt 1000) { throw 'Inventory directory limit reached' }
        try {
            $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 40
            $rows = [regex]::Matches($response.Content, '<tr><td.*?<a href="(?<href>[^"]+)"[^>]*>.*?</a></td><td[^>]*>(?<modified>.*?)</td><td[^>]*>(?<size>.*?)</td>.*?</tr>', 'Singleline')
            foreach ($row in $rows) {
                $href = [Net.WebUtility]::HtmlDecode($row.Groups['href'].Value)
                if ($href.StartsWith('/') -or $href.StartsWith('?') -or $href -eq '../') { continue }
                $childUrl = [uri]::new([uri]$url, $href).AbsoluteUri
                if (-not $childUrl.StartsWith($rootUrl, [StringComparison]::Ordinal)) { throw 'Out-of-scope directory link' }
                if ($href.EndsWith('/')) {
                    if ($href -notmatch 'es_snapshot|AOTF|search|errors|ebisearch') { $pending.Enqueue($childUrl) }
                    continue
                }
                $sizeText = $row.Groups['size'].Value.Trim()
                $estimatedBytes = $null
                $upperBytes = $null
                if ($sizeText -match '^(?<amount>[0-9]+(?:\.[0-9]+)?)(?<unit>[KMGT]?)$') {
                    $amountText = $Matches['amount']
                    $amount = [double]::Parse($amountText, [Globalization.CultureInfo]::InvariantCulture)
                    $unit = $Matches['unit']
                    $multiplier = switch ($unit) { 'K' { 1KB }; 'M' { 1MB }; 'G' { 1GB }; 'T' { 1TB }; default { 1 } }
                    $precision = if ($amountText.Contains('.')) { [math]::Pow(10, -($amountText.Split('.')[1].Length)) } else { 1 }
                    $estimatedBytes = [long][math]::Ceiling($amount * $multiplier)
                    $upperBytes = if ($unit) { [long][math]::Ceiling(($amount + $precision) * $multiplier) } else { $estimatedBytes }
                }
                $relative = $childUrl.Substring($rootUrl.Length)
                $files.Add([pscustomobject]@{ relative_path=$relative; url=$childUrl; listed_size=$sizeText; estimated_bytes=$estimatedBytes; planning_upper_bytes=$upperBytes; source_modified_text=$row.Groups['modified'].Value.Trim(); component=$relative.Split('/')[0] })
            }
        } catch {
            $failures.Add([pscustomobject]@{ url=$url; error=$_.Exception.Message })
        }
        if ($visited.Count % 10 -eq 0) { Write-Host ('Inventory {0}: {1} directories, {2} files' -f $releaseId,$visited.Count,$files.Count) }
    }
    $payloads = @($files | Where-Object { $_.relative_path -match '\.parquet$|\.json\.gz$|\.csv\.gz$' })
    [pscustomobject]@{
        release_id=$releaseId; root_url=$rootUrl; metadata_checked_at='2026-10-10'; directories_inspected=$visited.Count
        payload_files=$payloads.Count; estimated_payload_bytes=($payloads | Measure-Object estimated_bytes -Sum).Sum
        planning_upper_payload_bytes=($payloads | Measure-Object planning_upper_bytes -Sum).Sum
        unknown_size_files=@($payloads | Where-Object { $null -eq $_.estimated_bytes }).Count
        failures=@($failures); files=@($files)
    }
    Write-Host ('Inventory {0}: {1} payload files, estimated {2:N2} GiB' -f $releaseId,$payloads.Count,(($payloads | Measure-Object estimated_bytes -Sum).Sum / 1GB))
}
$result = [pscustomobject]@{
    checked_at='2026-10-10'; method='Recursive public Apache directory metadata; displayed sizes are rounded estimates with a conservative planning bound, not exact Content-Length.'
    exclusions='Elasticsearch snapshots, AOTF/search/error derivatives excluded; avoid counting duplicate deployment/index formats.'
    inventories=@($inventories); dataset_payloads_downloaded=$false
}
$result | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $OutputPath -Encoding utf8NoBOM
$result.inventories | Select-Object release_id,payload_files,@{Name='EstimatedGiB';Expression={[math]::Round($_.estimated_payload_bytes / 1GB,3)}},@{Name='UpperGiB';Expression={[math]::Round($_.planning_upper_payload_bytes / 1GB,3)}},unknown_size_files,@{Name='failed_directories';Expression={$_.failures.Count}} | ConvertTo-Json
