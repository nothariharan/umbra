Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'uireviewer'
$run = 'python scripts/lever.py checks --suite uireviewer --stage 2 --rev b013f5e17143'
$checks = @(
  'S2-UI-C1','S2-UI-C2','S2-UI-C3','S2-UI-C4','S2-UI-C5','S2-UI-C6','S2-UI-C7','S2-UI-C8',
  'S2-UI-C9','S2-UI-C10','S2-UI-C11','S2-UI-C12','S2-UI-C13'
)
foreach ($c in $checks) {
  Write-Host "=== recording $c ==="
  & python scripts/record.py evidence --seat uireviewer --check $c --run $run
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
& python scripts/record.py status --stage 2 --rev b013f5e17143
