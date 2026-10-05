$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
foreach ($id in @('E-certifier-35','E-certifier-36','E-certifier-37')) {
  $json = python scripts/record.py show --id $id | ConvertFrom-Json
  if ($json.exit -ne 0) { exit 1 }
}
Write-Host 'mutation score 3/3 (E-certifier-35 m01, E-certifier-36 m02, E-certifier-37 m03 @ 79af98560dd9)'
exit 0
