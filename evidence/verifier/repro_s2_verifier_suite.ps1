Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'verifier'
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$rev = if ($env:SUBMIT_REV) { $env:SUBMIT_REV } else { 'b013f5e17143' }
$boot = & $py scripts/lever.py boot --stage 2 --rev $rev 2>&1 | Out-String
if ($boot -notmatch 'BASE_URL=(\S+)') { throw "no BASE_URL in boot output" }
$env:BASE_URL = $Matches[1]
& $py -m pytest -q verify/stage-1 verify/stage-2 -p no:cacheprovider
$code = $LASTEXITCODE
& $py scripts/lever.py stop | Out-Null
exit $code
