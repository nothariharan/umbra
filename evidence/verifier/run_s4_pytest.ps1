param([Parameter(Mandatory=$true)][string]$Node)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$rev = if ($env:SUBMIT_REV) { $env:SUBMIT_REV } else { '55207f5fd143' }
$boot = & $py scripts/lever.py boot --stage 4 --rev $rev 2>&1 | Out-String
if ($boot -notmatch 'BASE_URL=(\S+)') { throw "no BASE_URL" }
$env:BASE_URL = $Matches[1]
& $py -m pytest -q -p no:cacheprovider $Node
$code = $LASTEXITCODE
& $py scripts/lever.py stop | Out-Null
exit $code
