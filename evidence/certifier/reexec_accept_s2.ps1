$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$ids = @(
  'E-verifier-53','E-verifier-54','E-verifier-55','E-verifier-56','E-verifier-57','E-verifier-59','E-verifier-60',
  'E-breaker-21','E-breaker-22','E-breaker-23','E-breaker-24','E-breaker-25','E-breaker-27',
  'E-uireviewer-6','E-uireviewer-7','E-uireviewer-8','E-uireviewer-9','E-uireviewer-10','E-uireviewer-11'
)
foreach ($id in $ids) {
  python scripts/lever.py reexec --evidence $id
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
exit 0
