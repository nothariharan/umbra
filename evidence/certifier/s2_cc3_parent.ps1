$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
foreach ($id in @('E-certifier-10','E-certifier-11','E-certifier-12')) {
  $json = python scripts/record.py show --id $id | ConvertFrom-Json
  if ($json.exit -ne 0) { exit 1 }
}
Write-Host 'mutation score 3/3 (per-mutant E-certifier-10,11,12 @ b013f5e17143; verifier+breaker each)'
exit 0
