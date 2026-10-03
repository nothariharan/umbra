Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent)
$env:UMBRA_SEAT = 'breaker'
$py = 'C:\Users\HARIHARAN\Desktop\Band\dark-factory-wearedevs\.venv\Scripts\python.exe'
$rev = '19249355fbc8'
$boot = & $py scripts/lever.py boot --stage 1 --rev $rev 2>&1 | Out-String
if ($boot -notmatch 'BASE_URL=(\S+)') { throw "no BASE_URL in boot output" }
$env:BASE_URL = $Matches[1]
& $py -m pytest -q -p no:cacheprovider attacks/stage-1/test_balance.py::test_private_payment_does_not_hide_an_earlier_public_one
$code = $LASTEXITCODE
& $py scripts/lever.py stop | Out-Null
exit $code
