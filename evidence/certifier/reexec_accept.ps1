$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$ids = @('E-breaker-7','E-verifier-8','E-verifier-10','E-verifier-13','E-verifier-14')
foreach ($id in $ids) {
  python scripts/lever.py reexec --evidence $id
  if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
exit 0
