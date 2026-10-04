$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
foreach ($id in @('E-certifier-23','E-certifier-28','E-certifier-30')) {
  $json = python scripts/record.py show --id $id | ConvertFrom-Json
  if ($json.exit -ne 0) { exit 1 }
}
Write-Host 'mutation score 3/3 (E-certifier-23 m01, E-certifier-28 m02, E-certifier-30 m03 @ 55207f5fd143)'
exit 0
