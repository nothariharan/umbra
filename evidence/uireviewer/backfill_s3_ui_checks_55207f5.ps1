Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'uireviewer'
$run = 'python scripts/lever.py checks --suite uireviewer --stage 3 --rev 55207f5fd143'
$checks = @(
  'S3-UI-C1','S3-UI-C2','S3-UI-C3','S3-UI-C5','S3-UI-C6','S3-UI-C7','S3-UI-C8',
  'S3-UI-C9','S3-UI-C10','S3-UI-C11','S3-UI-C12','S3-UI-C13'
)
function Record-Check($id) {
  foreach ($attempt in 1..2) {
    Write-Host "=== $id attempt $attempt ==="
    & python scripts/record.py evidence --seat uireviewer --check $id --run $run
    if ($LASTEXITCODE -eq 0) { return }
    if ($attempt -eq 1) { Start-Sleep -Seconds 45 }
  }
  throw "failed to record $id"
}
foreach ($c in $checks) { Record-Check $c }
& python scripts/record.py status --stage 3 --rev 55207f5fd143
