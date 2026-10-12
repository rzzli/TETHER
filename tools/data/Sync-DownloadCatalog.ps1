#Requires -Version 7.0
param(
    [string]$ProjectRoot = (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent),
    [Parameter(Mandatory)][string]$DataRoot,
    [Parameter(Mandatory)][string[]]$QueuePath,
    [string]$OutputPath
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = [IO.Path]::GetFullPath($ProjectRoot)
$DataRoot = [IO.Path]::GetFullPath($DataRoot)
if (-not $OutputPath) {
    $stamp = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')
    $OutputPath = Join-Path $ProjectRoot "data/manifests/public/$stamp-acquisition-summary.json"
}
$OutputPath = [IO.Path]::GetFullPath($OutputPath)
if (Test-Path -LiteralPath $OutputPath) { throw 'Report exists; choose a new output path.' }
$arguments = @('run','--no-sync','--directory',$ProjectRoot,'python','-m','asof.maintenance','inspect-transport',
    '--project-root',$ProjectRoot,'--catalog',(Join-Path $ProjectRoot 'data/catalog/sources.json'),
    '--raw-root',$DataRoot,'--output',$OutputPath)
foreach ($queue in $QueuePath) { $arguments += @('--queue',([IO.Path]::GetFullPath($queue))) }
& uv @arguments
if ($LASTEXITCODE -ne 0) { throw 'Acquisition inspection failed; catalog was not changed.' }
Write-Host 'Report only. Apply through asof.maintenance update-catalog with an explicit expected catalog hash.'
