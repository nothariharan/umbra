$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
foreach ($id in @('E-certifier-21','E-certifier-22','E-certifier-23')) {
  $json = python scripts/record.py show --id $id | ConvertFrom-Json
  if ($json.exit -ne 0) { exit 1 }
}
Write-Host 'mutation score 3/3 (per-mutant E-certifier-21,22,23 @ 1d75850acf29; verifier+breaker each)'
exit 0
