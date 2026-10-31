param([Parameter(Mandatory=$true)][string]$InputPath)
$ErrorActionPreference = 'Stop'
$cases = Get-Content -Raw -LiteralPath $InputPath | ConvertFrom-Json -AsHashtable
$rows = foreach ($case in $cases) {
    $valid = Test-Json -Json $case.document_json -Schema $case.schema_json -ErrorAction SilentlyContinue
    @{id=$case.id; accepted=[bool]$valid}
}
@{powershell_version=$PSVersionTable.PSVersion.ToString(); results=@($rows)} | ConvertTo-Json -Depth 20 -Compress
