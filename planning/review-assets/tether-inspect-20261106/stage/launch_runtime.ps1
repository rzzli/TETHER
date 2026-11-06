$ErrorActionPreference = 'Stop'
$tetherRuntimeRoot = 'D:\Projects\drug_target_agents\data\cache\tether-inspect-runtime-witnesses-20261106-attempt01'
$tetherRuntimeEvidence = 'D:\Projects\drug_target_agents\planning\review-assets\tether-inspect-20261106\stage'
$tetherRuntimeReady = "$tetherRuntimeRoot\freeze\READY.json"
if ((Get-FileHash -LiteralPath $tetherRuntimeReady -Algorithm SHA256).Hash.ToLowerInvariant() -ne '4366005009b3599cc50ed43b7381a114e90f27bd68f94273e1e748d6efb3f7e9') { throw 'Runtime readiness anchor differs' }
$tetherRuntimePlan = Get-Content -LiteralPath $tetherRuntimeReady -Raw | ConvertFrom-Json
$tetherRuntimePython = [string]$tetherRuntimePlan.command[0]
$tetherRuntimeArgs = @($tetherRuntimePlan.command | Select-Object -Skip 1)
foreach ($tetherRuntimePath in @("$tetherRuntimeRoot\runtime-stage", "$tetherRuntimeRoot\runtime-parent-import-cache", "$tetherRuntimeEvidence\RUNTIME-LAUNCH-01.json", "$tetherRuntimeEvidence\RUNTIME-CONSOLE-01.log", "$tetherRuntimeEvidence\RUNTIME-OUTER-TIMING-01.json")) {
    if (Test-Path -LiteralPath $tetherRuntimePath) { throw "Fresh runtime destination exists: $tetherRuntimePath" }
}
function Write-TetherRuntimeJson($Path, $Value) {
    $tetherRuntimeBytes = [System.Text.UTF8Encoding]::new($false).GetBytes(($Value | ConvertTo-Json -Depth 12) + "`n")
    $tetherRuntimeStream = [System.IO.File]::Open($Path, [System.IO.FileMode]::CreateNew)
    try { $tetherRuntimeStream.Write($tetherRuntimeBytes, 0, $tetherRuntimeBytes.Length); $tetherRuntimeStream.Flush($true) } finally { $tetherRuntimeStream.Dispose() }
}
Write-TetherRuntimeJson "$tetherRuntimeEvidence\RUNTIME-LAUNCH-01.json" @{
    schema_version = 1
    at_utc = [DateTimeOffset]::UtcNow.ToString('o')
    command = $tetherRuntimePlan.command
    freeze_sha256 = $tetherRuntimePlan.freeze.sha256
    launcher_sha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
    automatic_retry = $false
}
$tetherRuntimeWatch = [Diagnostics.Stopwatch]::StartNew()
$tetherRuntimeExit = $null
$tetherRuntimeError = $null
try {
    & $tetherRuntimePython @tetherRuntimeArgs 2>&1 | Out-File -LiteralPath "$tetherRuntimeEvidence\RUNTIME-CONSOLE-01.log" -Encoding utf8
    $tetherRuntimeExit = $LASTEXITCODE
} catch { $tetherRuntimeError = $_.Exception.GetType().FullName } finally {
    $tetherRuntimeWatch.Stop()
    Write-TetherRuntimeJson "$tetherRuntimeEvidence\RUNTIME-OUTER-TIMING-01.json" @{
        schema_version = 1
        completed_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
        exit_code = $tetherRuntimeExit
        launcher_error_type = $tetherRuntimeError
        wall_seconds = $tetherRuntimeWatch.Elapsed.TotalSeconds
        scope = 'Parent launch through command return, including native stage sealing and console redirection when successful; excludes this timing record publication. A launcher error leaves process exit unknown.'
        automatic_retry = $false
    }
}
if ($null -ne $tetherRuntimeError) { throw "Runtime launch failed; inspect retained records. $tetherRuntimeError" }
Write-Output "Runtime witness stage exited $tetherRuntimeExit in $($tetherRuntimeWatch.Elapsed.TotalSeconds) seconds."
exit $tetherRuntimeExit
