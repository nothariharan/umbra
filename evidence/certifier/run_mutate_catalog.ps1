$ErrorActionPreference = 'Stop'
$env:PYTHONUTF8 = '1'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
python scripts/lever.py mutate --stage 1 --catalog --rev 1125eee49810
exit $LASTEXITCODE
