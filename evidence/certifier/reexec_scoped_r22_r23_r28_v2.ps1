$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$ids = @(
  'E-verifier-140','E-verifier-141','E-verifier-143',
  'E-uireviewer-12',
  'E-breaker-32','E-breaker-28','E-breaker-31','E-breaker-29','E-breaker-33','E-breaker-30'
)
foreach ($id in $ids) {
  python scripts/lever.py reexec --evidence $id
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
exit 0
