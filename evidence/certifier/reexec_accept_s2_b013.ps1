$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$ids = @(
  'E-verifier-61','E-verifier-56','E-verifier-53','E-verifier-54','E-verifier-55',
  'E-verifier-57','E-verifier-59','E-verifier-60',
  'E-uireviewer-12',
  'E-breaker-32','E-breaker-28','E-breaker-31','E-breaker-29','E-breaker-33','E-breaker-30'
)
foreach ($id in $ids) {
  python scripts/lever.py reexec --evidence $id
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
exit 0
