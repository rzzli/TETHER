$ErrorActionPreference = 'Stop'
$tetherStudyRoot = 'D:\Projects\drug_target_agents\data\benchmark\tether-inspect-20261106-attempt01'
$tetherEvidenceRoot = 'D:\Projects\drug_target_agents\planning\review-assets\tether-inspect-20261106\stage'
$tetherPython = 'D:\Projects\drug_target_agents\data\cache\tether-inspect-env-attempt02\environment\Scripts\python.exe'
$tetherArgv = @('-I', '-B', '-X', "pycache_prefix=$tetherStudyRoot\parent-import-cache01", 'D:\Projects\drug_target_agents\experiments\inspect_policy\controller.py', 'run', '--freeze', "$tetherStudyRoot\freeze\FROZEN.json", '--sha', 'dd2e5e3d07cac7e966a02bff34b9b2e2fb1ea30507d6d861630d76b57244e6b4', '--output', "$tetherStudyRoot\run")
foreach ($tetherNewPath in @("$tetherStudyRoot\run", "$tetherStudyRoot\parent-import-cache01", "$tetherEvidenceRoot\PRIMARY-LAUNCH-01.json", "$tetherEvidenceRoot\PRIMARY-CONSOLE-01.log", "$tetherEvidenceRoot\PRIMARY-OUTER-TIMING-01.json")) {
    if (Test-Path -LiteralPath $tetherNewPath) { throw "Fresh primary launch destination exists: $tetherNewPath" }
}
function Write-TetherNewJson($Path, $Value) {
    $tetherBytes = [System.Text.UTF8Encoding]::new($false).GetBytes(($Value | ConvertTo-Json -Depth 12) + "`n")
    $tetherFile = [System.IO.File]::Open($Path, [System.IO.FileMode]::CreateNew)
    try { $tetherFile.Write($tetherBytes, 0, $tetherBytes.Length); $tetherFile.Flush($true) } finally { $tetherFile.Dispose() }
}
Write-TetherNewJson "$tetherEvidenceRoot\PRIMARY-LAUNCH-01.json" @{
    schema_version = 1
    at_utc = [DateTimeOffset]::UtcNow.ToString('o')
    command = @($tetherPython) + $tetherArgv
    freeze_sha256 = 'dd2e5e3d07cac7e966a02bff34b9b2e2fb1ea30507d6d861630d76b57244e6b4'
    ready_sha256 = '335d31305e2df50337bef763a1b1073e6aca2cfa311bc1fce283fd0e3b842b39'
    implementation_commit = 'e8e40af'
    launcher_sha256 = (Get-FileHash -LiteralPath $PSCommandPath -Algorithm SHA256).Hash.ToLowerInvariant()
    parent_bytecode_note = 'Adds a fresh parent cache prefix to READY argv; workers already use fresh prefixes. No experiment source, policy, schedule or budget changed.'
    automatic_retry = $false
}
$tetherWatch = [Diagnostics.Stopwatch]::StartNew()
$tetherExitCode = $null
$tetherLaunchError = $null
try {
    & $tetherPython @tetherArgv 2>&1 | Out-File -LiteralPath "$tetherEvidenceRoot\PRIMARY-CONSOLE-01.log" -Encoding utf8
    $tetherExitCode = $LASTEXITCODE
} catch {
    $tetherLaunchError = $_.Exception.GetType().FullName
} finally {
    $tetherWatch.Stop()
    Write-TetherNewJson "$tetherEvidenceRoot\PRIMARY-OUTER-TIMING-01.json" @{
    schema_version = 1
    completed_at_utc = [DateTimeOffset]::UtcNow.ToString('o')
    exit_code = $tetherExitCode
    launcher_error_type = $tetherLaunchError
    wall_seconds = $tetherWatch.Elapsed.TotalSeconds
    scope = 'Python parent launch through command return, including final stage seal when present and console redirection; excludes this timing record publication. A launcher error leaves process-exit status unknown.'
    seal_exists = (Test-Path -LiteralPath "$tetherStudyRoot\run\SEALED.json")
    console_sha256 = $(if (Test-Path -LiteralPath "$tetherEvidenceRoot\PRIMARY-CONSOLE-01.log") { (Get-FileHash -LiteralPath "$tetherEvidenceRoot\PRIMARY-CONSOLE-01.log" -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null })
    automatic_retry = $false
    }
}
if ($null -ne $tetherLaunchError) { throw "Primary launch failed; inspect retained records. $tetherLaunchError" }
Write-Output "Primary comparison exited $tetherExitCode in $($tetherWatch.Elapsed.TotalSeconds) seconds."
exit $tetherExitCode
